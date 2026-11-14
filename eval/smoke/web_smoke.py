"""Real-browser smoke for the web shell (P0 task 8). Starts the real API (fakes) and the built Next.js app, then drives headless
Chromium through the whole path and prints one line per check. Exit code 1 if any check fails.

    uv run python eval/smoke/web_smoke.py            # builds the web app first
    uv run python eval/smoke/web_smoke.py --no-build

It asserts, in a real browser: the iframe's `sandbox` attribute is exactly `allow-scripts`; the slider changes the readout; a
`fetch` from inside the frame is blocked (by the CSP, with a violation as the evidence); the console has no errors before that
deliberate fetch; Peek opens to Stage and back; 360 px has no horizontal scroll and 44 px targets. Two crafted streams then prove
the host's own defences: a block with a wrong hash is never rendered, and a frame that navigates away is torn down.
Screenshots go to test-results/web-smoke/ (gitignored).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, Route, sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.kit import latest_version  # noqa: E402

SHOTS = REPO / "test-results" / "web-smoke"
API_PORT = int(os.environ.get("SMOKE_API_PORT", "8000"))
WEB_PORT = int(os.environ.get("SMOKE_WEB_PORT", "3000"))
API = f"http://localhost:{API_PORT}"
WEB = f"http://localhost:{WEB_PORT}"
TITLE = "Hooke's law: how does a spring stretch?"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)


def spawn(cmd: list[str], env: dict[str, str], cwd: Path = REPO) -> subprocess.Popen:
    """Start a server in its own process group so `terminate` can take down the whole tree (`pnpm start` spawns node)."""
    options: dict = {"cwd": cwd, "env": env, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    return subprocess.Popen(cmd, **options)


def terminate(proc: subprocess.Popen) -> None:
    if sys.platform == "win32":
        # No process groups to signal on Windows: ask taskkill to end the process and every child it started.
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def require_free_port(port: int) -> None:
    """The smoke starts its own servers on fixed ports. If something already answers there (a server left over from an
    earlier run), `wait_http` would succeed against it and every later check would test the wrong process."""
    with socket.socket() as probe:
        probe.settimeout(0.5)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"port {port} is already in use: stop whatever is listening there and run the smoke again")


def wait_http(url: str, seconds: float = 60) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"{url} did not come up")


def sse(events: list[dict]) -> str:
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events)


def crafted_block(html: str, sha: str | None = None) -> dict:
    return {
        "type": "Environment",
        "id": "crafted-1",
        "meta": {"status": "ready", "error": None},
        "title": "Crafted",
        "lane": "instantiate",
        "label": "model-checked",
        "kitVersion": "0.0.1",
        "htmlSha256": sha or hashlib.sha256(html.encode()).hexdigest(),
        "html": html,
        "citations": [{"source": "UNVERIFIED", "page": None, "quote": None, "verified": False}],
        "checked": {
            "layers": ["scan"],
            "controlsExercised": 0,
            "gridPoints": 0,
            "referenceCases": 0,
            "readouts": 0,
            "models": [],
            "limits": "A crafted block used only by the smoke test.",
        },
        "planSummary": "A crafted block used only by the smoke test.",
    }


def serve_crafted(page: Page, block: dict) -> None:
    body = sse(
        [
            {"type": "meta", "requestId": "r", "lane": "instantiate", "label": "model-checked", "kitVersion": "0.0.1"},
            {"type": "text_delta", "text": "crafted"},
            {"type": "environment", "block": block},
            {"type": "done"},
        ]
    )

    def handle(route: Route) -> None:
        if route.request.method == "OPTIONS":
            route.fulfill(
                status=204,
                headers={
                    "access-control-allow-origin": WEB,
                    "access-control-allow-methods": "POST",
                    "access-control-allow-headers": "content-type",
                },
            )
        else:
            route.fulfill(
                status=200,
                content_type="text/event-stream",
                headers={"access-control-allow-origin": WEB},
                body=body,
            )

    page.route(f"{API}/ask", handle)


def main() -> int:
    build = "--no-build" not in sys.argv
    pnpm = shutil.which("pnpm") or "pnpm"
    SHOTS.mkdir(parents=True, exist_ok=True)
    procs: list[subprocess.Popen] = []
    require_free_port(API_PORT)
    require_free_port(WEB_PORT)
    tmp = Path(tempfile.mkdtemp(prefix="synapse-smoke-"))
    try:
        # A private data directory: /ask runs the whole pipeline on fakes and verifies the Environment in a real browser.
        env = {
            **os.environ,
            "SYNAPSE_LLM_MODE": "fake",
            "DATA_DIR": str(tmp),
            "PUBLIC_ORIGIN": WEB,
            "NEXT_PUBLIC_API_BASE_URL": API,
            "VERIFY_INTERACTION_SECONDS": "3",
            "KIT_DIST_DIR": str(REPO / "packages" / "kit" / "dist"),
        }
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CORPUS_DIR", None)

        if build:
            subprocess.run([pnpm, "--filter", "web", "build"], cwd=REPO, env=env, check=True, capture_output=True)
        # The API runs from a scratch directory so it cannot find the developer's .env: the smoke checks the corpus-free product (labels, wording),
        # whatever CORPUS_DIR, keys or caps the machine has configured. The app directory and the Kit path are absolute for the same reason.
        procs.append(
            spawn([sys.executable, "-m", "uvicorn", "api.main:app", "--app-dir", str(REPO), "--port", str(API_PORT)], env, cwd=tmp)
        )
        procs.append(spawn([pnpm, "--filter", "web", "exec", "next", "start", "--port", str(WEB_PORT)], env))
        wait_http(f"{API}/health")
        wait_http(WEB)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 360, "height": 780})
            page = context.new_page()
            console_errors: list[str] = []
            page_errors: list[str] = []
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: page_errors.append(str(e)))

            # ── the real path: ask, Peek, controls ──────────────────────────────────────────────────────────────────────
            page.goto(WEB)
            page.fill("#q", "Why does a spring stretch when I hang a weight on it?")
            page.click("button[type=submit]")
            # The loading skeleton is drawn from the streamed plan before the Environment is verified (D-23).
            page.wait_for_selector(f'article[aria-label="{TITLE} (draft)"]', timeout=30_000)
            check(
                "the loading skeleton appears before the Environment",
                page.query_selector("iframe") is None,
                "draft card, no frame yet",
            )
            page.wait_for_selector(f'iframe[title="{TITLE}"]', timeout=60_000)
            check(
                "the skeleton is replaced by the verified Environment",
                page.query_selector('article[aria-label$="(draft)"]') is None,
            )
            text = page.inner_text('[data-testid="answer"]')
            check("a streamed explanation appears", text.startswith("[fake:explain:"), text[:40])

            sandbox_attr = page.get_attribute("iframe", "sandbox")
            sandbox_prop = page.evaluate("document.querySelector('iframe').sandbox.value")
            allow_attr = page.get_attribute("iframe", "allow")
            check(
                "iframe sandbox attribute is exactly 'allow-scripts'",
                sandbox_attr == "allow-scripts" and sandbox_prop == "allow-scripts",
                f"{sandbox_attr!r}",
            )
            check(
                "iframe has no allow= permissions and no allow-same-origin",
                allow_attr is None and "allow-same-origin" not in (sandbox_attr or ""),
            )

            frame = page.frame_locator("iframe").first
            readout = frame.locator("[data-synapse-readout]")
            readout.wait_for(timeout=15_000)
            before = readout.inner_text()
            slider = frame.locator("input[data-synapse-control='load']")
            slider.focus()
            page.keyboard.press("End")
            page.wait_for_timeout(300)
            after = readout.inner_text()
            check("moving the slider changes the readout", before != after, f"{before!r} -> {after!r}")
            check("readout is the Hooke's law value at 10 N and 50 N/m", after.strip() == "0.200 m", after)

            kit_loaded = page.evaluate(
                "v => fetch('/vendor/kit/' + v + '/core.js').then(r => r.status)",
                latest_version(REPO / "packages" / "kit" / "dist"),
            )
            check("the Kit is same-origin through the /vendor rewrite", kit_loaded == 200, str(kit_loaded))
            page.screenshot(path=str(SHOTS / "01-peek-360.png"), full_page=True)

            # ── phone-first: 360 px wide, 44 px targets ────────────────────────────────────────────────────────────────
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check("no horizontal scroll at 360 px", overflow <= 0, f"{overflow}px")
            heights = page.evaluate(
                # Only controls that are on screen can be tapped: the study rail is in the page but `display:none` below the wide breakpoint.
                "[...document.querySelectorAll('button, input')].filter(e => e.getClientRects().length > 0).map(e => Math.round(e.getBoundingClientRect().height))"
            )
            check("every page-level control is at least 44 px tall", all(h >= 44 for h in heights), str(heights))

            # ── Provenance is visible ──────────────────────────────────────────────────────────────────────────────────
            body = page.inner_text("body")
            check(
                "provenance shows label, lane, source and limits",
                all(
                    s in body
                    for s in (
                        "Checked by code",
                        "Compose",
                        "Source:",
                        "What was checked",
                        "Limits:",
                        "not verified",
                    )
                ),
            )

            # ── A concept-check answer is remembered on this device only ───────────────────────────────────────────────────────────
            choices = page.frame_locator("iframe").first.locator("[data-synapse-action=choose]")
            if choices.count() > 0:
                choices.first.click()
                page.click("button[aria-controls=progress-menu]")  # "My progress" opens from the top bar
                page.wait_for_function(
                    "[...document.querySelectorAll('#progress-menu h2')].some(h => h.textContent.includes('My progress (1)'))",
                    timeout=5000,
                )
                page.click("button[aria-controls=progress-menu]")
                stored = page.evaluate("localStorage.getItem('synapse.progress.v1')")
                check(
                    "the first concept-check answer is kept in this browser's storage and counted in My progress",
                    bool(stored) and '"tries":1' in stored,
                )
            else:
                check("the Environment has a concept check to answer", False)

            # ── A shared link opens the stored Environment through the gate ───────────────────────────────────────────────────────────
            import json as _json
            import urllib.request as _url

            with _url.urlopen(f"{API}/library", timeout=10) as resp:  # noqa: S310 - our own local API
                stored = _json.loads(resp.read())["environments"]
            if stored:
                shared = page.context.new_page()
                shared.goto(f"{WEB}/e/{stored[0]['id']}")
                shared.wait_for_selector("iframe", timeout=20000)
                sandbox = shared.eval_on_selector("iframe", "e => e.getAttribute('sandbox')")
                body_text = shared.inner_text("body")
                copy_h = shared.eval_on_selector(
                    "button:has-text('Copy link')", "e => Math.round(e.getBoundingClientRect().height)"
                )
                check(
                    "a shared link shows the Environment in the exact sandbox with its provenance and a 44 px copy button",
                    sandbox == "allow-scripts" and "Source:" in body_text and copy_h >= 44,
                    f"sandbox={sandbox} copy_h={copy_h}",
                )
                shared.goto(f"{WEB}/e/not-a-real-environment-000000000000")
                shared.wait_for_selector("[role=alert]", timeout=10000)
                check("a link to nothing says so and shows no frame", shared.query_selector("iframe") is None)
                shared.close()
            else:
                check("the library holds the Environment that was just made", False)

            # ── the exam mirror (W5c): marked in the browser, shown in words, answer never sent ─────────────────────────
            page.wait_for_selector("[data-testid=exam]", timeout=30_000)
            exam_requests: list[str] = []
            page.on("request", lambda r: exam_requests.append(r.url) if r.method == "POST" else None)
            page.fill("[data-testid=exam] textarea", "The extension is directly proportional to the load. The graph is a straight line through the origin. The spring returns to its original length.")
            page.click("button:has-text('Mark my answer')")
            score = page.inner_text("[data-testid=exam-score]")
            check("the exam answer is marked in words", score == "3 of 3 marks", score)
            check("the exam answer is not sent to any server", not exam_requests, str(exam_requests))
            exam_heights = page.eval_on_selector_all("[data-testid=exam] button", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
            check("the exam card's controls are at least 44 px tall", bool(exam_heights) and all(h >= 44 for h in exam_heights), str(exam_heights))
            check("the exam card does not widen the page at 360 px", page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0)

            # ── Stage ─────────────────────────────────────────────────────────────────────────────────────────────────
            page.click("button:has-text('Open')")
            page.wait_for_selector("[role=dialog]")
            stage_sandbox = page.get_attribute("[role=dialog] iframe", "sandbox")
            check(
                "Stage opens full viewport with the same exact sandbox",
                stage_sandbox == "allow-scripts",
                f"{stage_sandbox!r}",
            )
            page.screenshot(path=str(SHOTS / "02-stage-360.png"))
            # ── the lab report (W5b): rows recorded inside the frame reach the host's report ────────────────────────────
            stage_frame = page.frame_locator("[role=dialog] iframe")
            stage_frame.locator("[data-synapse-action='record']").first.wait_for(timeout=10_000)
            check("the report asks for a row before any is recorded", "No rows yet" in page.inner_text("[data-testid=lab-report]"))
            stage_frame.locator("[data-synapse-action='record']").first.click()
            stage_frame.locator("input[data-synapse-control='load']").first.focus()
            page.keyboard.press("End")
            # The mass bench draws its range bar only while the bar has focus. A mouse press on Record takes the focus away, the bar collapses, Record moves up and the click is lost
            # (a known Kit defect, carried to v5: CHANGELOG 2026-11-14). So the test lets go of the bar first, as a person would by pressing Tab or clicking elsewhere.
            stage_frame.locator("body").evaluate("() => (document.activeElement instanceof HTMLElement) && document.activeElement.blur()")
            page.wait_for_timeout(300)
            stage_frame.locator("[data-synapse-action='record']").first.click()
            page.wait_for_function("document.querySelectorAll('[data-testid=lab-report] tbody tr').length === 2", timeout=5_000)
            report_text = page.inner_text("[data-testid=lab-report]")
            check("two recorded rows appear in the lab report", "Procedure" in report_text and "Aim" in report_text)
            report_heights = page.eval_on_selector_all("[data-testid=lab-report] button", "els => els.map(e => Math.round(e.getBoundingClientRect().height))")
            check("the report's buttons are at least 44 px tall", bool(report_heights) and all(h >= 44 for h in report_heights), str(report_heights))
            check("the report does not widen the page at 360 px", page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0)
            page.screenshot(path=str(SHOTS / "02b-lab-report-360.png"), full_page=True)
            # ── Present mode (D-39): large, still labelled, still sourced, and reversible ─────────────────────────────────
            normal_h = page.eval_on_selector("[role=dialog] iframe", "e => Math.round(e.getBoundingClientRect().height)")
            page.click("button:has-text('Present')")
            page.wait_for_selector("[data-testid=present-source]", timeout=5_000)
            present_h = page.eval_on_selector("[role=dialog] iframe", "e => Math.round(e.getBoundingClientRect().height)")
            check("Present mode shows a Presenting chip and a larger frame", present_h > normal_h and page.locator("text=Presenting").count() >= 1, f"{normal_h} -> {present_h}")
            check("Present mode keeps the label, the lane and the source on screen", page.locator("[role=dialog] .study-badge").count() >= 2 and page.locator("[data-testid=present-source]").is_visible())
            page.click("button:has-text('Stop presenting')")
            check("Stop presenting brings the provenance and the report back", page.locator("[data-testid=lab-report]").is_visible() and page.locator("section[aria-label='Where this Environment comes from']").is_visible())
            page.locator("[role=dialog] button", has_text="Back").focus()  # focus was inside the frame, where Escape is the frame's
            page.keyboard.press("Escape")
            page.wait_for_selector("[role=dialog]", state="detached")
            check("Escape returns from Stage to Peek", page.locator("article").count() == 1)

            # ── the theme toggle (W3): 44 px, reaches the Environment's frame, and does not trip the Kit's self-check ────────────────────
            toggle = page.locator("button[aria-label='Switch to dark mode']")
            check("the theme toggle is at least 44 px", toggle.evaluate("e => Math.round(e.getBoundingClientRect().height)") >= 44)
            toggle.click()
            page.wait_for_function("document.documentElement.dataset.theme === 'dark'", timeout=5000)
            page.wait_for_timeout(1100)  # the circular reveal takes 820 ms; a screenshot before it ends shows both themes at once
            frame_theme = None
            for _ in range(30):
                frame_theme = next(f for f in page.frames if f != page.main_frame).evaluate("document.documentElement.getAttribute('data-theme')")
                if frame_theme == "dark":
                    break
                page.wait_for_timeout(100)
            check("the host's dark theme reaches the Environment's frame", frame_theme == "dark", str(frame_theme))
            slider_dark = page.frame_locator("iframe").first.locator("input[data-synapse-control='load']")
            slider_dark.focus()
            page.keyboard.press("Home")
            page.wait_for_timeout(400)
            check(
                "after the theme change the frame is still there and still works (the Kit's self-check did not close it)",
                page.locator("iframe").count() == 1 and page.frame_locator("iframe").first.locator("[data-synapse-readout]").inner_text().strip() == "0.000 m",
            )
            page.screenshot(path=str(SHOTS / "03-peek-360-dark.png"), full_page=True)
            page.click("button[aria-label='Switch to light mode']")
            page.wait_for_function("document.documentElement.dataset.theme === 'light'", timeout=5000)

            # ── wide screens: the rail, the conversation and ONE lab bench frame ───────────────────────────────────────────────────────────
            wide = browser.new_context(viewport={"width": 1280, "height": 800}).new_page()
            wide.goto(WEB)
            check("a wide screen shows the study rail and its quick starts", wide.locator("aside[aria-label='Study guide'] button").count() >= 3)
            wide.fill("#q", "Why does a spring stretch when I hang a weight on it?")
            wide.click("button[type=submit]")
            wide.wait_for_selector(f'aside[aria-label="Lab bench"] iframe[title="{TITLE}"]', timeout=60_000)
            check(
                "on a wide screen exactly one frame is mounted, inside the lab bench",
                wide.locator("iframe").count() == 1 and wide.locator("aside[aria-label='Lab bench'] iframe").count() == 1,
            )
            check("no horizontal scroll at 1280 px", wide.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0)
            # The visual standard (D-60): the lab takeover, one frame, one header row, the title once.
            share = wide.evaluate("document.querySelector(\"aside[aria-label='Lab bench']\").getBoundingClientRect().width / window.innerWidth")
            check("after a question the lab pane takes at least three quarters of the width", share >= 0.75, f"{share:.2f}")
            check("the study rail folds away during the takeover", wide.locator("aside[aria-label='Study guide']").count() == 0)
            tool_names = wide.evaluate(
                "[...document.querySelectorAll(\"aside[aria-label='Lab bench'] [aria-label='Lab tools'] button, aside[aria-label='Lab bench'] [aria-label='Lab tools'] a\")].map(e => e.textContent.trim())"
            )
            check("one compact tool group: Present, Share, Save offline and Full screen (the EN/BM switch sits in the top bar)", tool_names == ["Present", "Share", "Save offline", "Full screen"], str(tool_names))
            check("the lab is one bordered frame (one article in the lab pane)", wide.locator("aside[aria-label='Lab bench'] article").count() == 1)
            visible_titles = wide.evaluate(
                "[...document.querySelectorAll(\"aside[aria-label='Lab bench'] h1, aside[aria-label='Lab bench'] h2\")].filter(e => e.getBoundingClientRect().width > 4 && e.textContent.includes(\"Hooke\")).length"
            )
            check("the lab title is not repeated by the host (the Environment page shows it)", visible_titles == 0, str(visible_titles))
            inner_title = wide.frame_locator("iframe").first.locator("h1").inner_text()
            check("the Environment page shows its title once, in the Kit's heading", "Hooke" in inner_title, inner_title[:50])
            check("the Kit page has the kicker, the Try this line and the key idea", all(wide.frame_locator("iframe").first.locator(sel).count() == 1 for sel in (".syn-kicker", ".syn-try", ".syn-keyidea")))
            wide.screenshot(path=str(SHOTS / "04-wide-1280.png"))
            wide.click("aside[aria-label='Lab bench'] >> text=Present")
            wide.wait_for_selector("[role=dialog] >> text=Stop presenting", timeout=5000)
            check("Present opens the lab full screen and already presenting", wide.locator("[role=status] >> text=Presenting").count() == 1)
            wide.keyboard.press("Escape")
            wide.wait_for_selector("aside[aria-label='Lab bench'] article", timeout=5000)
            wide.click("button[aria-label='Switch to dark mode']")
            wide.wait_for_function("document.documentElement.dataset.theme === 'dark'", timeout=5000)
            wide.wait_for_timeout(500)
            wide.screenshot(path=str(SHOTS / "05-wide-1280-dark.png"))
            wide.context.close()

            errors_before_fetch = list(console_errors) + list(page_errors)
            check(
                "no console errors and no page errors so far",
                not errors_before_fetch,
                "; ".join(errors_before_fetch)[:200],
            )

            # ── a fetch from inside the frame is blocked ───────────────────────────────────────────────────────────────
            frame_obj = next(f for f in page.frames if f != page.main_frame)
            outcome = frame_obj.evaluate(
                "fetch('" + API + "/health').then(() => 'ALLOWED', (e) => 'blocked: ' + e.name)"
            )
            page.wait_for_timeout(300)
            violation = [m for m in console_errors if "Content Security Policy" in m]
            check("a fetch from inside the frame is blocked", outcome.startswith("blocked"), outcome)
            check(
                "the block is the CSP's doing (a violation was reported)",
                bool(violation),
                (violation[0][:90] if violation else "none"),
            )

            # ── the misconception probe (W5a): an optional card, plain text, answered once ──────────────────────────────
            quick = context.new_page()
            quick.goto(WEB)
            quick.fill("#q", "Is osmosis when water moves to where there is more water?")
            quick.click("button[type=submit]")
            quick.wait_for_selector("[data-testid=probe]", timeout=60_000)
            probe_heights = quick.eval_on_selector_all(
                "[data-testid=probe] button", "els => els.map(e => Math.round(e.getBoundingClientRect().height))"
            )
            check("the quick check appears for a matching question", quick.locator("[data-testid=probe]").count() == 1)
            check("every quick-check control is at least 44 px tall", bool(probe_heights) and all(h >= 44 for h in probe_heights), str(probe_heights))
            check("the quick check shows no answer before one is chosen", "What this rests on" not in quick.inner_text("[data-testid=probe]"))
            quick.get_by_role("button", name="Water moves out of the cells", exact=False).click()
            probe_text = quick.inner_text("[data-testid=probe]")
            check("a right answer is said in words and the basis is shown", "Yes, that is right." in probe_text and "What this rests on" in probe_text)
            check(
                "the quick check does not widen the page at 360 px",
                quick.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0,
            )
            quick.close()

            # ── keyboard only, visible focus and reduced motion (W9, hard constraint 10) ────────────────────────────────────
            kb_context = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce")
            kb = kb_context.new_page()
            kb.goto(WEB)
            reached = False
            for _ in range(25):
                kb.keyboard.press("Tab")
                if kb.evaluate("document.activeElement && document.activeElement.id") == "q":
                    reached = True
                    break
            check("the question box is reachable with Tab alone", reached)
            if reached:
                focus_visible = kb.evaluate(
                    "(() => { const s = getComputedStyle(document.activeElement); return (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none'; })()"
                )
                check("the focused question box shows a visible focus indicator", bool(focus_visible))
                kb.keyboard.type("Why does a spring stretch when I hang a weight on it?")
                kb.keyboard.press("Enter")
                kb.wait_for_selector("article[aria-label]:not([aria-label$='(draft)'])", timeout=60_000)
                opened = False
                for _ in range(60):
                    kb.keyboard.press("Tab")
                    if (kb.evaluate("document.activeElement && document.activeElement.textContent") or "").strip() == "Open":
                        opened = True
                        break
                check("the Open button for the Environment is reachable with Tab alone", opened)
                if opened:
                    kb.keyboard.press("Enter")
                    kb.wait_for_selector("[role=dialog]", timeout=5_000)
                    first = (kb.evaluate("document.activeElement && document.activeElement.textContent") or "").strip()
                    check("Stage puts keyboard focus on Back when it opens", first == "Back", first)
                    kb.keyboard.press("Escape")
                    kb.wait_for_selector("[role=dialog]", state="detached", timeout=5_000)
                    check("Escape closes Stage from the keyboard", kb.locator("[role=dialog]").count() == 0)
            looping = kb.evaluate("document.getAnimations().filter(a => a.effect && a.effect.getComputedTiming().iterations === Infinity).length")
            check("with reduced motion on, no animation on the page loops forever", looping == 0, str(looping))
            frame_looping = 0
            for f in kb.frames:
                if f != kb.main_frame:
                    frame_looping += f.evaluate("document.getAnimations().filter(a => a.effect && a.effect.getComputedTiming().iterations === Infinity).length")
            check("with reduced motion on, no animation in the Environment loops forever", frame_looping == 0, str(frame_looping))
            unnamed = kb.evaluate(
                "Array.from(document.querySelectorAll('button, a[href], input, textarea, select')).filter(e => !(e.getAttribute('aria-label') || e.textContent.trim() || e.labels && e.labels.length || e.getAttribute('title') || e.getAttribute('aria-labelledby'))).length"
            )
            check("every button, link and field on the page has an accessible name", unnamed == 0, str(unnamed))
            kb_context.close()

            # ── the host's own defences, on crafted streams ───────────────────────────────────────────────────────────
            page.unroute_all()
            wrong = context.new_page()
            serve_crafted(wrong, crafted_block("<!doctype html><p>tampered</p>", sha="0" * 64))
            wrong.goto(WEB)
            wrong.fill("#q", "x")
            wrong.click("button[type=submit]")
            wrong.wait_for_selector("main [role=alert]", timeout=10_000)
            check(
                "a block with a wrong hash is never rendered",
                wrong.locator("iframe").count() == 0,
                wrong.inner_text("main [role=alert]")[:70],
            )

            nav = context.new_page()
            navigating = "<!doctype html><html><body><p>hi</p><script>setTimeout(function(){window['loc'+'ation']='/vendor/kit/0.0.1/manifest.json'},200)</script></body></html>"
            serve_crafted(nav, crafted_block(navigating))
            nav.goto(WEB)
            nav.fill("#q", "x")
            nav.click("button[type=submit]")
            nav.wait_for_selector("iframe", timeout=10_000)
            # Not "[role=alert]": Next.js has its own empty route announcer with that role, which would match at once.
            nav.wait_for_selector("main [role=alert]", timeout=10_000)
            nav.wait_for_selector("iframe", state="detached", timeout=10_000)
            if os.environ.get("SMOKE_DEBUG"):
                print("DEBUG iframes:", nav.locator("iframe").count(), "| main:", nav.inner_html("main")[:500])
            check(
                "a frame that navigates away is torn down by the host",
                nav.locator("iframe").count() == 0,
                nav.inner_text("main [role=alert]")[:70],
            )
            browser.close()
    finally:
        for proc in procs:
            terminate(proc)
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
