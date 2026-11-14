// `apparatus(env, {kind, label, channels})`: one reusable piece of lab apparatus on the bench (W16, D-66). The catalogue (`apparatus_catalogue.ts`) says which parts exist and what
// channels each has; a Plan places up to four parts and binds every channel to a control or a science model's output, with a drawing scale. A part DRAWS the numbers it is given and
// never prints one: its words are the Kit's (a level, a strength, a pH band), its label is the Plan's.
//
// What is drawn follows the numbers and nothing else. Each part's moving attributes are computed from its channels, the audit keeps every attribute of every element and the elements
// inside the drawing, and the verifier checks each channel's source, unit and scale (one widget per channel). Motion is the Kit stylesheet's: a flame flickers, bubbles rise, charge
// flows, a planet goes round, a wave travels, particles jostle, a pendulum swings. It never changes a number, its speed follows a channel in five steps, and it stops under reduced motion.
//
// The bench is hands-on (W17, D-69, D-70). A channel bound to a slider gets a grip where the catalogue says (the top of the liquid, the plunger, the trolley): dragging it moves the
// slider, snapped to its steps, so the slider stays the one source of the number and the keyboard path; the grip is a pointer surface hidden from assistive technology, like the dial's
// knob. A part may also take a `drop`: a tray of items the student drags onto the drawing, each one step of a slider, with the mass hanger's contract (every item a Kit button, Enter
// or Space moves it, the verifier drags every one on and off).

import { event } from "./bridge";
import { all, attr, contains, effectiveOpacity, hasAttribute, hitAt, layoutAvailable, parentOf, rectOf, style, tagOf } from "./dom";
import type { Environment } from "./environment";
import { kt, ktWord } from "./i18n";
import type { Observable } from "./observable";
import { quiet } from "./handles";
import { guard } from "./parts";
import { controls, copy, isObservable, markKitSvg, markOwnStyle, nodeOf, own, ownAttr, registerAction, widgets, type ControlRecord } from "./provenance";
import { APPARATUS, MAX_APPARATUS_PARTS, type ChannelType, type Grab } from "./apparatus_catalogue";

const NS = "http://www.w3.org/2000/svg";
const W = 120;
const H = 140;

type Attrs = Record<string, string>;
type State = Record<string, number>;
type Dyn = (s: State) => Attrs;

const f = (v: number): string => v.toFixed(1);
const clamp = (v: number, lo = 0, hi = 1): number => Math.min(hi, Math.max(lo, v));
/** Five motion steps: 0 is still, 4 is fastest. */
export const speedStep = (fr: number): number => (fr < 0.02 ? 0 : 1 + Math.min(3, Math.floor(fr * 4)));
const sp = (fr: number): string => `syn-sp${speedStep(fr)}`;
/** Five word bands for an amount: none, low, medium, high, very high. */
export const band = (fr: number): number => (fr < 0.02 ? 0 : fr < 0.3 ? 1 : fr < 0.6 ? 2 : fr < 0.9 ? 3 : 4);
export function phBand(ph: number): number {
  return ph < 3 ? 0 : ph < 6.5 ? 1 : ph <= 7.5 ? 2 : ph < 11 ? 3 : 4;
}
/** Universal indicator: the colour of a solution of this pH. */
export function phColour(ph: number): string {
  const stops = ["#c62828", "#e64a19", "#f57c00", "#f9a825", "#fdd835", "#c0ca33", "#7cb342", "#43a047", "#26a69a", "#1e88e5", "#3949ab", "#5e35b1", "#7b1fa2", "#6a1b9a", "#4a148c"];
  return stops[Math.round(clamp(ph, 0, 14))] as string;
}

interface Builder {
  el<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Attrs, dyn?: Dyn, parent?: Element): SVGElementTagNameMap[K];
}

type Draw = (b: Builder) => void;

// Fixed scatter positions (deterministic: the same picture every time the numbers are the same).
const SCATTER: [number, number][] = Array.from({ length: 40 }, (_, i) => [14 + ((i * 37) % 92), 30 + ((i * 53) % 96)]);

const LINE = "var(--syn-line)";
const LIQ = "var(--syn-liquid)";
const HOT = "var(--syn-indicator)";
const ACC = "var(--syn-accent)";

function bubbleSet(b: Builder, xs: number[], bottom: number, channel = "bubbles"): void {
  xs.forEach((x, i) =>
    b.el("circle", { cx: String(x), cy: String(bottom - (i % 3) * 6), fill: "var(--syn-card)", stroke: LINE, "stroke-width": "1" }, (s) => {
      const on = (s[channel] ?? 0) > 0.02 && i < Math.max(1, Math.round((s[channel] ?? 0) * xs.length));
      return { r: on ? "2.6" : "0", class: `syn-a-rise syn-d${i % 4} ${sp(s[channel] ?? 0)}` };
    }),
  );
}

const DRAW: Record<string, Draw> = {
  beaker(b) {
    b.el("rect", { x: "25", width: "70", fill: LIQ, "fill-opacity": "0.55" }, (s) => {
      const top = 130 - clamp(s.level ?? 0) * 92;
      return { y: f(top), height: f(130 - top) };
    });
    bubbleSet(b, [38, 50, 62, 74, 86], 124);
    b.el("path", { d: "M20 30 L24 128 Q24 134 30 134 L90 134 Q96 134 96 128 L100 30", fill: "none", stroke: LINE, "stroke-width": "3", "stroke-linejoin": "round" });
    for (const y of [56, 80, 104]) b.el("line", { x1: "28", y1: String(y), x2: "38", y2: String(y), stroke: LINE, "stroke-width": "1.5" });
  },
  flask(b) {
    const hw = (y: number): number => 10 + ((y - 50) / 84) * 33;
    b.el("polygon", { fill: LIQ, "fill-opacity": "0.55" }, (s) => {
      const top = 132 - clamp(s.level ?? 0) * 80;
      return { points: `${f(60 - hw(top))},${f(top)} ${f(60 + hw(top))},${f(top)} 103,132 17,132` };
    });
    bubbleSet(b, [44, 54, 64, 74], 126);
    b.el("path", { d: "M50 16 L50 50 L15 134 L105 134 L70 50 L70 16", fill: "none", stroke: LINE, "stroke-width": "3", "stroke-linejoin": "round" });
  },
  test_tube(b) {
    b.el("rect", { x: "50", width: "20", rx: "9", fill: LIQ, "fill-opacity": "0.55" }, (s) => {
      const top = 126 - clamp(s.level ?? 0) * 96;
      return { y: f(top), height: f(128 - top) };
    });
    bubbleSet(b, [55, 60, 65], 118);
    b.el("path", { d: "M47 12 L47 120 A13 13 0 0 0 73 120 L73 12", fill: "none", stroke: LINE, "stroke-width": "3" });
  },
  cylinder(b) {
    b.el("rect", { x: "45", width: "30", fill: LIQ, "fill-opacity": "0.55" }, (s) => {
      const top = 126 - clamp(s.level ?? 0) * 110;
      return { y: f(top), height: f(126 - top) };
    });
    b.el("path", { d: "M44 10 L44 126 L76 126 L76 10", fill: "none", stroke: LINE, "stroke-width": "3" });
    b.el("rect", { x: "34", y: "126", width: "52", height: "6", rx: "2", fill: LINE });
    for (let y = 20; y < 126; y += 11) b.el("line", { x1: "44", y1: String(y), x2: y % 22 === 9 ? "56" : "52", y2: String(y), stroke: LINE, "stroke-width": "1.2" });
  },
  solution(b) {
    b.el("rect", { x: "25", width: "70", fill: LIQ, "fill-opacity": "0.4" }, (s) => {
      const top = 130 - (s.level === undefined ? 0.8 : clamp(s.level)) * 92;
      return { y: f(top), height: f(130 - top) };
    });
    SCATTER.slice(0, 30).forEach(([x, y], i) =>
      b.el("circle", { cx: f(28 + (x - 14) * 0.7), cy: f(50 + (y - 30) * 0.8), fill: HOT }, (s) => ({ r: i < Math.round(clamp(s.concentration ?? 0) * 30) ? "2.4" : "0" })),
    );
    b.el("path", { d: "M20 30 L24 128 Q24 134 30 134 L90 134 Q96 134 96 128 L100 30", fill: "none", stroke: LINE, "stroke-width": "3", "stroke-linejoin": "round" });
  },
  indicator(b) {
    b.el("rect", { x: "50", y: "40", width: "20", height: "88", rx: "9" }, (s) => ({ fill: phColour(s.ph ?? 7) }));
    b.el("path", { d: "M47 12 L47 120 A13 13 0 0 0 73 120 L73 12", fill: "none", stroke: LINE, "stroke-width": "3" });
    const scale = ["#c62828", "#f57c00", "#fdd835", "#43a047", "#1e88e5", "#5e35b1"];
    scale.forEach((c, i) => b.el("rect", { x: "86", y: String(30 + i * 15), width: "14", height: "15", fill: c }));
    b.el("polygon", { fill: "var(--syn-fg)" }, (s) => {
      const y = 30 + (clamp(s.ph ?? 7, 0, 14) / 14) * 90;
      return { points: `80,${f(y - 4)} 85,${f(y)} 80,${f(y + 4)}` };
    });
  },
  syringe(b) {
    b.el("rect", { x: "12", y: "54", height: "22", fill: LIQ, "fill-opacity": "0.3" }, (s) => ({ width: f(4 + clamp(s.volume ?? 0) * 78) }));
    b.el("rect", { x: "10", y: "50", width: "84", height: "30", rx: "3", fill: "none", stroke: LINE, "stroke-width": "3" });
    for (let x = 20; x < 94; x += 9) b.el("line", { x1: String(x), y1: "50", x2: String(x), y2: "57", stroke: LINE, "stroke-width": "1.2" });
    b.el("rect", { y: "52", width: "5", height: "26", fill: LINE }, (s) => ({ x: f(14 + clamp(s.volume ?? 0) * 78) }));
    b.el("line", { y1: "65", x2: "114", y2: "65", stroke: LINE, "stroke-width": "3" }, (s) => ({ x1: f(19 + clamp(s.volume ?? 0) * 78) }));
    b.el("line", { x1: "2", y1: "65", x2: "10", y2: "65", stroke: LINE, "stroke-width": "3" });
  },
  burner(b) {
    b.el("path", { fill: HOT, "fill-opacity": "0.85", class: "syn-a-flicker" }, (s) => {
      const fr = clamp(s.heat ?? 0);
      const h = 10 + fr * 54;
      const w = 6 + fr * 9;
      return { d: `M60 ${f(86 - h)} C ${f(60 + w)} ${f(86 - h * 0.45)} ${f(60 + w)} 86 60 86 C ${f(60 - w)} 86 ${f(60 - w)} ${f(86 - h * 0.45)} 60 ${f(86 - h)} Z`, opacity: fr < 0.02 ? "0" : "1", class: `syn-a-flicker ${sp(fr)}` };
    });
    b.el("rect", { x: "52", y: "86", width: "16", height: "38", fill: "none", stroke: LINE, "stroke-width": "3" });
    b.el("rect", { x: "34", y: "124", width: "52", height: "8", rx: "3", fill: LINE });
    b.el("line", { x1: "68", y1: "112", x2: "100", y2: "112", stroke: LINE, "stroke-width": "3" });
  },
  thermometer(b) {
    b.el("rect", { x: "56", width: "8", fill: HOT }, (s) => {
      const top = 112 - clamp(s.temperature ?? 0) * 94;
      return { y: f(top), height: f(118 - top) };
    });
    b.el("rect", { x: "53", y: "10", width: "14", height: "106", rx: "7", fill: "none", stroke: LINE, "stroke-width": "2.5" });
    b.el("circle", { cx: "60", cy: "122", r: "11", fill: HOT, stroke: LINE, "stroke-width": "2.5" });
    for (let y = 20; y < 112; y += 12) b.el("line", { x1: "67", y1: String(y), x2: "74", y2: String(y), stroke: LINE, "stroke-width": "1.2" });
  },
  balance(b) {
    b.el("rect", { fill: ACC, "fill-opacity": "0.8", rx: "3" }, (s) => {
      const fr = clamp(s.mass ?? 0);
      const w = 14 + fr * 46;
      const h = 6 + fr * 34;
      return { x: f(60 - w / 2), y: f(96 - h), width: f(w), height: f(h) };
    });
    b.el("line", { x1: "24", y1: "98", x2: "96", y2: "98", stroke: LINE, "stroke-width": "4", "stroke-linecap": "round" });
    b.el("rect", { x: "12", y: "104", width: "96", height: "28", rx: "5", fill: "none", stroke: LINE, "stroke-width": "3" });
    b.el("rect", { x: "24", y: "112", width: "72", height: "12", rx: "2", fill: "var(--syn-card)", stroke: LINE, "stroke-width": "1.5" });
    b.el("rect", { x: "26", y: "114", height: "8", fill: ACC }, (s) => ({ width: f(clamp(s.mass ?? 0) * 68) }));
  },
  gauge(b) {
    b.el("path", { d: "M14 96 A46 46 0 0 1 106 96", fill: "none", stroke: LINE, "stroke-width": "4" });
    for (let i = 0; i <= 8; i++) {
      const a = Math.PI - (i / 8) * Math.PI;
      b.el("line", { x1: f(60 + 40 * Math.cos(a)), y1: f(96 - 40 * Math.sin(a)), x2: f(60 + 46 * Math.cos(a)), y2: f(96 - 46 * Math.sin(a)), stroke: LINE, "stroke-width": "2" });
    }
    b.el("line", { x1: "60", y1: "96", stroke: HOT, "stroke-width": "3.5", "stroke-linecap": "round" }, (s) => {
      const a = Math.PI - clamp(s.value ?? 0) * Math.PI;
      return { x2: f(60 + 38 * Math.cos(a)), y2: f(96 - 38 * Math.sin(a)) };
    });
    b.el("circle", { cx: "60", cy: "96", r: "5", fill: LINE });
    b.el("rect", { x: "10", y: "104", width: "100", height: "26", rx: "6", fill: "none", stroke: LINE, "stroke-width": "2" });
    b.el("rect", { x: "16", y: "112", height: "10", rx: "2", fill: ACC }, (s) => ({ width: f(clamp(s.value ?? 0) * 88) }));
  },
  weights(b) {
    b.el("path", { d: "M60 6 L60 22 M54 22 L66 22 L66 28", fill: "none", stroke: LINE, "stroke-width": "3" });
    b.el("line", { x1: "60", y1: "28", x2: "60", y2: "128", stroke: LINE, "stroke-width": "2.5" });
    for (let i = 0; i < 8; i++) {
      b.el("rect", { x: "36", width: "48", height: "10", rx: "3", fill: ACC, stroke: LINE, "stroke-width": "1.5", y: String(122 - i * 12) }, (s) => ({ opacity: i < Math.round(clamp(s.load ?? 0) * 8) ? "1" : "0" }));
    }
    b.el("rect", { x: "30", y: "130", width: "60", height: "5", rx: "2", fill: LINE });
  },
  spring(b) {
    b.el("line", { x1: "34", y1: "10", x2: "86", y2: "10", stroke: "var(--syn-fg)", "stroke-width": "5", "stroke-linecap": "round" });
    b.el("polyline", { fill: "none", stroke: ACC, "stroke-width": "3.5", "stroke-linejoin": "round" }, (s) => {
      const len = 40 + clamp(s.extension ?? 0) * 70;
      const pts = ["60,10", "60,20"];
      for (let i = 1; i <= 10; i++) pts.push(`${i % 2 ? 46 : 74},${f(20 + ((len - 20) * (i - 0.5)) / 10)}`);
      pts.push(`60,${f(len)}`, `60,${f(len + 8)}`);
      return { points: pts.join(" ") };
    });
    b.el("rect", { x: "44", width: "32", height: "14", rx: "3", fill: LINE }, (s) => ({ y: f(48 + clamp(s.extension ?? 0) * 70) }));
  },
  trolley(b) {
    b.el("line", { x1: "4", y1: "112", x2: "116", y2: "112", stroke: LINE, "stroke-width": "3" });
    b.el("rect", { y: "84", width: "38", height: "18", rx: "4", fill: ACC, stroke: LINE, "stroke-width": "2" }, (s) => ({ x: f(4 + clamp(s.position ?? 0) * 74) }));
    for (const dx of [9, 29]) {
      b.el("circle", { cy: "106", r: "5.5", fill: "var(--syn-card)", stroke: LINE, "stroke-width": "2.5", "stroke-dasharray": "4 3" }, (s) => ({ cx: f(4 + dx + clamp(s.position ?? 0) * 74), class: `syn-a-spin ${sp(s.speed ?? 0)}` }));
    }
  },
  ramp(b) {
    b.el("polygon", { fill: "var(--syn-bench)", stroke: LINE, "stroke-width": "2.5", "stroke-linejoin": "round" }, (s) => {
      const a = (clamp(s.angle ?? 0, 0, 60) * Math.PI) / 180;
      return { points: `10,126 110,126 110,${f(126 - Math.min(100, 100 * Math.tan(a)))}` };
    });
    b.el("rect", { width: "24", height: "16", rx: "2", fill: ACC, stroke: LINE, "stroke-width": "2" }, (s) => {
      const deg = clamp(s.angle ?? 0, 0, 60);
      const a = (deg * Math.PI) / 180;
      const d = 55;
      const x = 10 + d * Math.cos(a);
      const y = 126 - d * Math.sin(a);
      return { x: f(x - 12), y: f(y - 16), transform: `rotate(${f(-deg)} ${f(x)} ${f(y)})` };
    });
  },
  pendulum(b) {
    b.el("line", { x1: "30", y1: "10", x2: "90", y2: "10", stroke: "var(--syn-fg)", "stroke-width": "5", "stroke-linecap": "round" });
    b.el("g", { class: "syn-a-swing" }, (s) => ({ class: `syn-a-swing ${sp(1 - clamp(s.length ?? 0) * 0.75)}` }));
    b.el("line", { x1: "60", y1: "12", x2: "60", stroke: LINE, "stroke-width": "2" }, (s) => ({ y2: f(30 + clamp(s.length ?? 0) * 84) }));
    b.el("circle", { cx: "60", r: "9", fill: ACC, stroke: LINE, "stroke-width": "2" }, (s) => ({ cy: f(39 + clamp(s.length ?? 0) * 84) }));
  },
  bulb(b) {
    b.el("circle", { cx: "60", cy: "52", fill: "var(--syn-gold)" }, (s) => {
      const fr = clamp(s.brightness ?? 0);
      return { r: f(26 + fr * 26), opacity: f(fr * 0.55) };
    });
    b.el("circle", { cx: "60", cy: "52", r: "24", fill: "var(--syn-card)", "fill-opacity": "0.6", stroke: LINE, "stroke-width": "3" });
    b.el("path", { d: "M52 66 L52 52 Q56 44 60 52 Q64 44 68 52 L68 66", fill: "none", stroke: HOT, "stroke-width": "2" });
    b.el("rect", { x: "48", y: "76", width: "24", height: "22", rx: "3", fill: LINE });
  },
  circuit(b) {
    b.el("rect", { x: "18", y: "28", width: "84", height: "82", rx: "6", fill: "none", stroke: LINE, "stroke-width": "3" });
    b.el("rect", { x: "18", y: "28", width: "84", height: "82", rx: "6", fill: "none", stroke: ACC, "stroke-width": "3", "stroke-dasharray": "3 9" }, (s) => ({ class: `syn-a-flow ${sp(s.current ?? 0)}` }));
    b.el("rect", { x: "8", y: "58", width: "20", height: "22", fill: "var(--syn-bench)" });
    b.el("line", { x1: "10", y1: "64", x2: "26", y2: "64", stroke: LINE, "stroke-width": "3" });
    b.el("line", { x1: "13", y1: "72", x2: "23", y2: "72", stroke: LINE, "stroke-width": "5" });
    b.el("rect", { x: "46", y: "102", width: "28", height: "14", fill: "var(--syn-bench)", stroke: LINE, "stroke-width": "2.5" });
    b.el("circle", { cx: "60", cy: "28", fill: "var(--syn-gold)" }, (s) => ({ r: f(9 + clamp(s.current ?? 0) * 14), opacity: f(clamp(s.current ?? 0) * 0.6) }));
    b.el("circle", { cx: "60", cy: "28", r: "9", fill: "var(--syn-card)", stroke: LINE, "stroke-width": "2.5" });
    b.el("path", { d: "M54 22 L66 34 M66 22 L54 34", stroke: LINE, "stroke-width": "2" });
  },
  coils(b) {
    b.el("rect", { x: "26", y: "24", width: "68", height: "92", rx: "4", fill: "none", stroke: LINE, "stroke-width": "8" });
    for (let i = 0; i < 8; i++) {
      b.el("ellipse", { cx: "30", cy: String(36 + i * 9), rx: "11", ry: "4", fill: "none", stroke: ACC, "stroke-width": "2.5" }, (s) => ({ opacity: i < 1 + Math.round(clamp(s.primary ?? 0) * 7) ? "1" : "0" }));
      b.el("ellipse", { cx: "90", cy: String(36 + i * 9), rx: "11", ry: "4", fill: "none", stroke: HOT, "stroke-width": "2.5" }, (s) => ({ opacity: i < 1 + Math.round(clamp(s.secondary ?? 0) * 7) ? "1" : "0" }));
    }
  },
  wave(b) {
    b.el("line", { x1: "0", y1: "70", x2: "120", y2: "70", stroke: LINE, "stroke-width": "1", "stroke-dasharray": "4 4" });
    const path = b.el("path", { fill: "none", stroke: ACC, "stroke-width": "3", "stroke-linecap": "round" }, (s) => {
      const lambda = 20 + clamp(s.wavelength ?? 0) * 60;
      const amp = 4 + (s.amplitude === undefined ? 0.5 : clamp(s.amplitude)) * 40;
      const pts: string[] = [];
      for (let x = -lambda; x <= 120 + lambda; x += 3) pts.push(`${f(x)},${f(70 - amp * Math.sin((2 * Math.PI * x) / lambda))}`);
      return { d: `M ${pts.join(" L ")}`, class: `syn-a-travel ${sp(s.frequency ?? 0.5)}`, style: `--syn-wl:${f(-lambda)}px` };
    });
    markOwnStyle(path);
  },
  orbit(b) {
    b.el("circle", { cx: "60", cy: "70", r: "11", fill: "var(--syn-gold)", stroke: LINE, "stroke-width": "2" });
    const radius = (s: State): number => 24 + (s.radius === undefined ? 0.7 : clamp(s.radius)) * 30;
    const group = b.el("g", {}, (s) => ({ class: `syn-a-orbit ${sp(s.speed ?? 0)}` }));
    b.el("circle", { cx: "60", cy: "70", fill: "none", stroke: LINE, "stroke-width": "1.2", "stroke-dasharray": "3 4" }, (s) => ({ r: f(radius(s)) }), group);
    b.el("circle", { cy: "70", r: "6", fill: LIQ, stroke: LINE, "stroke-width": "2" }, (s) => ({ cx: f(60 + radius(s)) }), group);
    // An unpainted twin on the far side keeps the group's box centred on the star, so the turn is about the star.
    b.el("circle", { cy: "70", r: "6", fill: "none", stroke: "none" }, (s) => ({ cx: f(60 - radius(s)) }), group);
  },
  particles(b) {
    b.el("rect", { x: "10", y: "22", width: "100", height: "100", rx: "6", fill: "none", stroke: LINE, "stroke-width": "3" });
    SCATTER.slice(0, 14).forEach(([x, y], i) => b.el("circle", { cx: f(x * 0.9 + 8), cy: f(y * 0.8 + 6), r: "4", fill: i % 3 ? ACC : HOT }, (s) => ({ class: `syn-a-jig${i % 3} ${sp(s.speed ?? 0)}` })));
  },
  nuclei(b) {
    for (let i = 0; i < 25; i++) {
      const x = 20 + (i % 5) * 20;
      const y = 28 + Math.floor(i / 5) * 20;
      b.el("circle", { cx: String(x), cy: String(y), r: "7", stroke: LINE, "stroke-width": "2" }, (s) => ({ fill: i < Math.round(clamp(s.remaining ?? 0) * 25) ? HOT : "var(--syn-card)" }));
    }
  },
  leaf(b) {
    // The sun is the grip (W17): it slides from the top corner down towards the plant as the light rises, along the line the catalogue gives (`grabs.light`).
    const sunAt = (s: Record<string, number>): [number, number] => {
      const t = clamp(s.light ?? 0);
      return [18 + t * 40, 14 + t * 24];
    };
    b.el("circle", { r: "11", fill: "var(--syn-gold)" }, (s) => {
      const [x, y] = sunAt(s);
      return { cx: f(x), cy: f(y) };
    });
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * 2 * Math.PI;
      b.el("line", { stroke: "var(--syn-gold)", "stroke-width": "2.5" }, (s) => {
        const [x, y] = sunAt(s);
        return { x1: f(x + 14 * Math.cos(a)), y1: f(y + 14 * Math.sin(a)), x2: f(x + 22 * Math.cos(a)), y2: f(y + 22 * Math.sin(a)), opacity: f(0.1 + clamp(s.light ?? 0) * 0.9) };
      });
    }
    b.el("rect", { x: "30", y: "52", width: "64", height: "80", rx: "6", fill: LIQ, "fill-opacity": "0.3", stroke: LINE, "stroke-width": "2.5" });
    b.el("path", { d: "M62 128 Q50 100 56 80 Q70 92 64 128 Z M62 116 Q78 96 82 84 Q70 104 66 120 Z", fill: "#43a047", stroke: LINE, "stroke-width": "1.5" });
    bubbleSet(b, [58, 63, 68, 73], 84, "rate");
  },
  cell(b) {
    b.el("circle", { cx: "60", cy: "70", fill: "#a5d6a7", "fill-opacity": "0.6", stroke: LINE, "stroke-width": "3" }, (s) => ({ r: f(10 + clamp(s.size ?? 0) * 48) }));
    b.el("circle", { cx: "60", cy: "70", fill: "#7e57c2", "fill-opacity": "0.7" }, (s) => ({ r: f(3 + clamp(s.size ?? 0) * 10) }));
  },
  field(b) {
    b.el("rect", { x: "6", y: "10", width: "108", height: "120", rx: "6", fill: "#c5e1a5", "fill-opacity": "0.5", stroke: LINE, "stroke-width": "2" });
    b.el("rect", { x: "40", y: "46", width: "40", height: "40", fill: "none", stroke: HOT, "stroke-width": "2.5", "stroke-dasharray": "5 3" });
    SCATTER.forEach(([x, y], i) => b.el("circle", { cx: String(x), cy: String(y), fill: "#2e7d32" }, (s) => ({ r: i < Math.round(clamp(s.density ?? 0) * 40) ? "2.8" : "0" })));
  },
};


export interface ChannelBinding {
  value: Observable<number>;
  /** fraction channels: the value drawn as full. */
  full?: number;
}

export interface DropBinding {
  /** A slider with 2 to 8 steps: each item dropped onto the part is one step. */
  value: Observable<number>;
  /** What one item is ("Spoon of salt"). The Plan's words. */
  item: string;
}

export interface ApparatusOptions {
  kind: string;
  /** What this part is in the experiment ("Water", "Tube A"). The Plan's words. */
  label: string;
  channels: Record<string, ChannelBinding>;
  drop?: DropBinding;
}

export const MAX_DROP_ITEMS = 8;
const LETTERS = "ABCDEFGH";
const DRAG_THRESHOLD = 6;
/** The grip's pointer area, in drawing units: about 44 px across on the narrowest bench column. */
export const GRIP_RADIUS = 26;

/** Where a grip is drawn for a channel's drawn value (a fraction 0 to 1, or an angle in degrees). */
export function gripPoint(g: Grab, v: number): [number, number] {
  if ("pivot" in g) {
    const a = (clamp(v, 0, 60) * Math.PI) / 180;
    return [g.pivot[0] + g.radius * Math.cos(a), g.pivot[1] - g.radius * Math.sin(a)];
  }
  const t = clamp(v);
  return [g.from[0] + t * (g.to[0] - g.from[0]), g.from[1] + t * (g.to[1] - g.from[1])];
}

/** The drawn value a point on the drawing stands for: the inverse of `gripPoint` (projected onto the line, or the angle about the pivot). */
export function gripValue(g: Grab, x: number, y: number): number {
  if ("pivot" in g) return clamp((Math.atan2(g.pivot[1] - y, x - g.pivot[0]) * 180) / Math.PI, 0, 60);
  const dx = g.to[0] - g.from[0];
  const dy = g.to[1] - g.from[1];
  return clamp(((x - g.from[0]) * dx + (y - g.from[1]) * dy) / (dx * dx + dy * dy));
}

/** A value moved to the nearest step of a control, inside its range (the same rule a snapped slider uses). */
function onStep(rec: ControlRecord, v: number): number {
  const c = Math.min(rec.max, Math.max(rec.min, v));
  return Math.min(rec.max, Number((rec.min + Math.round((c - rec.min) / rec.step) * rec.step).toPrecision(12)));
}

/** How many parts are on the bench already: one apparatus widget per channel, named `<kind>-<index>.<channel>`. */
function partsSoFar(): number {
  return new Set(widgets.filter((w) => w.kind === "apparatus").map((w) => w.id.split(".")[0])).size;
}

function benchOf(env: Environment): HTMLDivElement {
  const existing = Array.from(env.stage.children).find((c) => c.classList.contains("syn-app-bench"));
  if (existing) return existing as HTMLDivElement;
  const bench = document.createElement("div");
  bench.className = "syn-app-bench";
  bench.setAttribute("role", "group");
  bench.setAttribute("aria-label", kt("appBench"));
  env.stage.appendChild(bench);
  return bench;
}

function channelWords(kind: string, channel: string, type: ChannelType, v: number): string {
  const name = ktWord(`appch_${channel}`);
  if (type === "ph") return `${name} ${ktWord(`appph${phBand(v)}`)}`;
  if (type === "angle") return `${name} ${ktWord(`applv${band(v / 60)}`)}`;
  void kind;
  return `${name} ${ktWord(`applv${band(v)}`)}`;
}

export function apparatus(env: Environment, options: ApparatusOptions): SVGSVGElement {
  const kind = String(options.kind);
  const info = APPARATUS[kind];
  const draw = DRAW[kind];
  if (!info || !draw) throw new TypeError(`apparatus: there is no part '${kind}'`);
  const label = String(options.label ?? "");
  if (label.trim() === "" || label.length > 60) throw new RangeError(`apparatus ${kind}: needs a label of 1 to 60 characters`);
  const given = options.channels ?? {};
  for (const name of Object.keys(given)) if (!info.channels[name]) throw new TypeError(`apparatus ${kind}: it has no channel '${name}'`);
  const bound: { name: string; type: ChannelType; obs: Observable<number>; full?: number }[] = [];
  for (const [name, ch] of Object.entries(info.channels)) {
    const b = given[name];
    if (!b) {
      if (ch.optional) continue;
      throw new TypeError(`apparatus ${kind}: the channel '${name}' must be bound`);
    }
    if (!isObservable(b.value)) throw new TypeError(`apparatus ${kind}.${name}: the value must be a Kit observable`);
    const node = nodeOf(b.value as object);
    if (!node || (node.kind !== "control" && node.kind !== "model" && node.kind !== "convert")) throw new TypeError(`apparatus ${kind}.${name}: the value must be a control or a science model's output`);
    if (ch.type === "fraction" && !(typeof b.full === "number" && Number.isFinite(b.full) && b.full > 0)) throw new RangeError(`apparatus ${kind}.${name}: full must be a positive number`);
    bound.push({ name, type: ch.type, obs: b.value, full: b.full });
  }
  const index = partsSoFar();
  if (index >= MAX_APPARATUS_PARTS) throw new RangeError(`apparatus: at most ${MAX_APPARATUS_PARTS} parts on one bench`);
  const controlOf = (obs: Observable<number>): ControlRecord | undefined => controls.find((c) => c.obs === obs);
  let dropRec: ControlRecord | undefined;
  let dropItem = "";
  if (options.drop !== undefined) {
    const d = options.drop;
    dropRec = isObservable(d.value) ? controlOf(d.value) : undefined;
    if (!dropRec) throw new TypeError(`apparatus ${kind}: a drop must be bound to a slider`);
    dropItem = String(d.item ?? "");
    if (dropItem.trim() === "" || dropItem.length > 40) throw new RangeError(`apparatus ${kind}: a drop needs an item of 1 to 40 characters`);
    if (!Number.isInteger(dropRec.grid) || dropRec.grid < 2 || dropRec.grid > MAX_DROP_ITEMS) throw new RangeError(`apparatus ${kind}: a drop's slider needs 2 to ${MAX_DROP_ITEMS} steps`);
    const at = (dropRec.default - dropRec.min) / ((dropRec.max - dropRec.min) / dropRec.grid);
    if (!(Math.abs(at - Math.round(at)) < 1e-9)) throw new RangeError(`apparatus ${kind}: a drop's slider must start on a step`);
    const taken = dropRec.id;
    if (widgets.some((w) => w.kind === "masses" && w.id === taken)) throw new RangeError(`apparatus ${kind}: the slider '${taken}' already has items to drag`);
  }

  const state = (): State => {
    const s: State = {};
    for (const c of bound) {
      const v = c.obs.get();
      s[c.name] = c.type === "fraction" ? clamp(v / (c.full as number)) : c.type === "angle" ? clamp(v, 0, 60) : clamp(v, 0, 14);
    }
    return s;
  };
  const describe = (): string => {
    const s = state();
    const parts = bound.map((c) => channelWords(kind, c.name, c.type, s[c.name] as number));
    return kt("appSentence", ktWord(`app_${kind}`), label, parts.join("; "));
  };

  const figure = document.createElement("figure");
  figure.className = `syn-app syn-app-${kind}`;
  const root = document.createElementNS(NS, "svg") as SVGSVGElement;
  root.setAttribute("viewBox", `0 0 ${W} ${H}`);
  root.setAttribute("class", "syn-scene syn-app-svg");
  root.setAttribute("role", "img");
  root.setAttribute("preserveAspectRatio", "xMidYMid meet");
  markKitSvg(root);
  const dynamic: [Element, Dyn][] = [];
  const builder: Builder = {
    el(tag, attrs, dyn, parent) {
      const e = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
      (parent ?? lastGroup ?? root).appendChild(e);
      if (dyn) dynamic.push([e, dyn]);
      return e;
    },
  };
  // A `g` made with no parent becomes the parent of the elements made after it in the same part, until the part ends (the trolley's body, the pendulum's arm).
  let lastGroup: Element | null = null;
  const plainEl = builder.el;
  builder.el = (tag, attrs, dyn, parent) => {
    const e = plainEl(tag, attrs, dyn, parent);
    if (tag === "g" && !parent) lastGroup = e;
    return e;
  };
  draw(builder);
  lastGroup = null;

  // Grips: one per channel that the catalogue says can be grabbed and that is bound to a slider (a model's output cannot be dragged).
  const grips: { name: string; rec: ControlRecord; obs: Observable<number>; grab: Grab; hit: SVGCircleElement; full?: number; type: ChannelType }[] = [];
  for (const c of bound) {
    const g = info.grabs?.[c.name];
    const rec = g ? controlOf(c.obs) : undefined;
    // W20: a control the part takes drops for is worked by dropping items; a grip on the same control would sit under the dropped items and fight them.
    if (!g || !rec || rec === dropRec) continue;
    const at = (st: State): Attrs => {
      const [x, y] = gripPoint(g, st[c.name] ?? 0);
      return { cx: f(x), cy: f(y) };
    };
    builder.el("circle", { r: "10", fill: "none", stroke: ACC, "stroke-width": "2", class: "syn-app-ring syn-a-pulse" }, at);
    builder.el("circle", { r: "5.5", fill: ACC, stroke: "var(--syn-card)", "stroke-width": "2" }, at);
    const hit = builder.el("circle", { r: String(GRIP_RADIUS), fill: "#000", "fill-opacity": "0", class: "syn-app-grip", "aria-hidden": "true", "data-synapse-handle": `${kind}-${index}.${c.name}` }, at);
    grips.push({ name: c.name, rec, obs: c.obs, grab: g, hit, full: c.full, type: c.type });
    quiet(rec); // the drawing is what the student drags; the bar is drawn only with focus (W18)
  }
  const toDrawing = (clientX: number, clientY: number): [number, number] | null => {
    const r = root.getBoundingClientRect(); // the student's own pointer, so the element's own method; the audit's reads go through the captured one
    const k = Math.min(r.width / W, r.height / H);
    if (!(k > 0)) return null;
    return [(clientX - (r.left + (r.width - W * k) / 2)) / k, (clientY - (r.top + (r.height - H * k) / 2)) / k];
  };
  for (const g of grips) {
    let held = false;
    const follow = (e: PointerEvent): void => {
      const p = toDrawing(e.clientX, e.clientY);
      if (!p) return;
      const drawn = gripValue(g.grab, p[0], p[1]);
      g.obs.set(onStep(g.rec, g.type === "fraction" ? drawn * (g.full as number) : drawn));
      event(g.rec.id, g.obs.get());
    };
    g.hit.addEventListener("pointerdown", (e: PointerEvent) => {
      if (e.button !== undefined && e.button !== 0) return;
      held = true;
      try {
        g.hit.setPointerCapture?.(e.pointerId);
      } catch {
        /* a pointer that cannot be captured still drags by its move events */
      }
      e.preventDefault();
    });
    g.hit.addEventListener("pointermove", (e: PointerEvent) => {
      if (held) follow(e);
    });
    g.hit.addEventListener("pointerup", (e: PointerEvent) => {
      if (!held) return;
      held = false;
      follow(e);
      try {
        g.hit.releasePointerCapture?.(e.pointerId);
      } catch {
        /* nothing was captured */
      }
    });
    g.hit.addEventListener("pointercancel", () => {
      held = false;
    });
    // `touch-action` is not honoured on an SVG shape, so a finger on the grip would scroll the page and cancel the drag. Only a touch that starts on the grip is kept from
    // scrolling; the rest of the drawing scrolls as usual.
    const still = (e: TouchEvent): void => e.preventDefault();
    g.hit.addEventListener("touchstart", still, { passive: false });
    g.hit.addEventListener("touchmove", still, { passive: false });
  }
  const caption = own(document.createElement("figcaption"), () => label);
  caption.textContent = label;
  caption.className = "syn-app-label";
  copy.push(label);
  const drop = dropRec && options.drop ? buildDrop(dropRec, options.drop.value, dropItem, label) : null;
  if (dropRec && drop) quiet(dropRec); // the items are what the student drags; the bar is drawn only with focus
  if (drop) {
    drop.zone.prepend(root);
    figure.append(drop.zone, caption);
  } else figure.append(root, caption);

  const paint = (): void => {
    const s = state();
    for (const [el, dyn] of dynamic) for (const [k, v] of Object.entries(dyn(s))) el.setAttribute(k, v);
    root.setAttribute("aria-label", describe());
  };
  for (const c of bound) c.obs.subscribe(paint);
  paint();
  ownAttr(root, "aria-label", describe); // the label is Plan copy and may hold a number ("chlorine-35"); the sentence is the Kit's
  const bench = benchOf(env);
  bench.appendChild(figure);
  if (drop) bench.appendChild(drop.tray); // a full row under the bench (the stylesheet orders it after the parts), so eight items fit on a phone
  if (grips.length > 0 && !Array.from(bench.children).some((c) => c.classList.contains("syn-app-hint"))) {
    const hint = own(document.createElement("p"), () => kt("appGrab"));
    hint.className = "syn-app-hint";
    hint.textContent = kt("appGrab");
    bench.appendChild(hint);
  }

  const kept = guard();
  for (const [el, dyn] of dynamic) kept.part(el, () => dyn(state()));
  kept.part(root, () => ({ "aria-label": describe() }));
  const moving = new Set(dynamic.map(([el]) => el));
  for (const el of [figure, caption, ...all(root, "*")]) if (!moving.has(el)) kept.part(el);
  kept.tree(drop ? root : figure); // with a drop the items move between the tray and the drawing, and the drop checks them itself
  const holder = drop ? drop.zone : figure;
  const check = (): string[] => {
    const out: string[] = [];
    if (parentOf(root) !== holder || parentOf(caption) !== figure || parentOf(figure) === null || (drop !== null && parentOf(drop.zone) !== figure)) out.push(`the ${kind} was taken apart`);
    if (style(figure, "display") === "none" || style(figure, "visibility") === "hidden" || style(root, "display") === "none" || style(root, "visibility") === "hidden") out.push(`the ${kind} is hidden`);
    if (attr(root, "aria-label") !== describe()) out.push(`the ${kind}'s description was changed by the page`);
    return out;
  };
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const box = rectOf(root);
    if (!(box.width > 0 && box.height > 0)) return [`the ${kind} is not drawn`];
    return effectiveOpacity(root) < 0.5 ? [`the ${kind} is faded out`] : [];
  };
  bound.forEach((c, i) =>
    widgets.push({
      kind: "apparatus",
      id: `${kind}-${index}.${c.name}`,
      part: kind,
      channel: c.name,
      channelType: c.type,
      units: info.channels[c.name]?.units ?? [],
      obs: c.obs,
      full: c.full,
      check: i === 0 ? check : () => [],
      layout: i === 0 ? layout : () => [],
      exact: i === 0 ? () => kept.problems() : () => [],
    }),
  );
  for (const g of grips) {
    const gripCheck = (): string[] => {
      const out: string[] = [];
      if (parentOf(g.hit) !== root) out.push(`the handle on the ${kind} was taken off`);
      if (style(g.hit, "display") === "none" || style(g.hit, "visibility") === "hidden" || style(g.hit, "pointer-events") === "none") out.push(`the handle on the ${kind} cannot be grabbed`);
      return out;
    };
    const gripLayout = (): string[] => {
      if (!layoutAvailable()) return [];
      const r = rectOf(g.hit);
      const out: string[] = [];
      if (r.width < 40 || r.height < 40) out.push(`the handle on the ${kind} is too small to grab`);
      const hit = hitAt(r.left + r.width / 2, r.top + r.height / 2);
      if (hit && hit !== g.hit && !contains(g.hit, hit)) out.push(`the handle on the ${kind} is covered by something else`);
      return out;
    };
    widgets.push({
      kind: "handle",
      id: `${kind}-${index}.${g.name}`,
      control: g.rec.id,
      grab: g.grab,
      obs: g.obs,
      part: kind,
      channel: g.name,
      channelType: g.type,
      units: info.channels[g.name]?.units ?? [],
      full: g.full,
      check: gripCheck,
      layout: gripLayout,
    });
  }
  if (drop && dropRec) widgets.push({ kind: "masses", id: dropRec.id, masses: dropRec.grid, check: drop.check, layout: drop.layout });
  return root;
}

function div(className: string): HTMLDivElement {
  const el = document.createElement("div");
  el.className = className;
  return el;
}

/** A tray of items and the drawing as the place they go: the mass hanger's contract on a bench part (W17, D-70). The control's value is min plus one step per item added. */
function buildDrop(rec: ControlRecord, value: Observable<number>, item: string, label: string): { zone: HTMLDivElement; tray: HTMLDivElement; check: () => string[]; layout: () => string[] } {
  const id = rec.id;
  const grid = rec.grid;
  const step = (rec.max - rec.min) / grid;
  const countOf = (v: number): number => Math.max(0, Math.min(grid, Math.round((v - rec.min) / step)));
  const added = new Set<number>();
  for (let i = 0; i < countOf(value.get()); i++) added.add(i);

  const zone = div("syn-app-zone");
  zone.setAttribute("role", "group");
  zone.setAttribute("data-synapse-dropzone", id);
  const zoneName = (): string => kt("dropZone", label, kt("dropCount", added.size));
  ownAttr(zone, "aria-label", zoneName);
  const row = div("syn-app-added");
  // A screen reader hears what was added here, since a label that changes on a button is not announced.
  const status = own(document.createElement("span"), () => zoneName());
  status.className = "syn-sr";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  zone.append(row, status);
  const tray = div("syn-app-tray");
  tray.setAttribute("role", "group");
  tray.setAttribute("data-synapse-tray", id);
  const trayName = kt("dropTray", item);
  tray.setAttribute("aria-label", trayName);
  ownAttr(tray, "aria-label", () => trayName);
  const cap = own(document.createElement("span"), () => item);
  cap.className = "syn-cap";
  cap.textContent = item;
  copy.push(item);

  const tokens: HTMLButtonElement[] = [];
  const nameOf = (i: number): string => kt("dropName", item, LETTERS[i] as string, added.has(i));
  for (let i = 0; i < grid; i++) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "syn-mass syn-app-item";
    b.textContent = LETTERS[i] as string;
    b.setAttribute("data-synapse-action", "drag");
    b.setAttribute("data-synapse-drag", id);
    ownAttr(b, "aria-label", () => nameOf(i));
    registerAction(b, "drag", `${item} ${LETTERS[i]}`);
    markOwnStyle(b);
    tokens.push(b);
  }
  const render = (focus?: HTMLElement | null): void => {
    tray.replaceChildren(cap, ...tokens.filter((_, i) => !added.has(i)));
    row.replaceChildren(...tokens.filter((_, i) => added.has(i)));
    tokens.forEach((b, i) => {
      b.setAttribute("aria-label", nameOf(i));
      b.dataset.state = added.has(i) ? "hung" : "tray"; // the mass hanger's states, so the verifier drives both the same way
    });
    zone.setAttribute("aria-label", zoneName());
    status.textContent = zoneName();
    focus?.focus();
  };
  const commit = (): void => {
    value.set(Number((rec.min + added.size * step).toPrecision(12)));
    event(id, value.get());
  };
  const toggle = (i: number): void => {
    if (added.has(i)) added.delete(i);
    else added.add(i);
    commit();
    render(tokens[i]);
  };
  const inside = (x: number, y: number): boolean => {
    const r = zone.getBoundingClientRect();
    return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
  };
  let dragsInFlight = 0;
  tokens.forEach((b, i) => {
    let start: { x: number; y: number } | null = null;
    let dragging = false;
    let suppressClick = false;
    b.addEventListener("pointerdown", (e: PointerEvent) => {
      if (e.button !== undefined && e.button !== 0) return;
      start = { x: e.clientX, y: e.clientY };
      dragging = false;
      try {
        b.setPointerCapture?.(e.pointerId);
      } catch {
        /* a pointer that cannot be captured still drags by its move events */
      }
    });
    b.addEventListener("pointermove", (e: PointerEvent) => {
      if (!start) return;
      const dx = e.clientX - start.x;
      const dy = e.clientY - start.y;
      if (!dragging && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
      if (!dragging) dragsInFlight += 1;
      dragging = true;
      b.classList.add("syn-dragging");
      b.style.transform = `translate(${dx}px, ${dy}px)`;
      zone.classList.toggle("syn-over", inside(e.clientX, e.clientY));
    });
    const finish = (e: PointerEvent, cancelled: boolean): void => {
      if (!start) return;
      const wasDragging = dragging;
      if (wasDragging) dragsInFlight -= 1;
      start = null;
      dragging = false;
      try {
        b.releasePointerCapture?.(e.pointerId);
      } catch {
        /* nothing was captured */
      }
      b.classList.remove("syn-dragging");
      b.style.removeProperty("transform");
      zone.classList.remove("syn-over");
      if (!wasDragging) return; // a tap: the click that follows does the work
      suppressClick = true; // the click some browsers send after a drag must not toggle a second time
      setTimeout(() => {
        suppressClick = false;
      }, 50);
      if (!cancelled && inside(e.clientX, e.clientY) !== added.has(i)) toggle(i);
    };
    b.addEventListener("pointerup", (e: PointerEvent) => finish(e, false));
    b.addEventListener("pointercancel", (e: PointerEvent) => finish(e, true));
    b.addEventListener("click", (e: MouseEvent) => {
      if (suppressClick) {
        e.preventDefault();
        return;
      }
      toggle(i);
    });
  });
  // The other direction: the range input, a grip, a sweep or Reset moved the control, so the items follow it.
  value.subscribe((v) => {
    const n = countOf(v);
    if (n === added.size) return;
    while (added.size < n) added.add(tokens.findIndex((_, k) => !added.has(k)));
    while (added.size > n) added.delete(Math.max(...added));
    render();
  });

  const hidden = (el: Element): boolean => style(el, "display") === "none" || style(el, "visibility") === "hidden" || style(el, "opacity") === "0";
  const check = (): string[] => {
    const out: string[] = [];
    if (added.size !== countOf(value.get())) out.push(`the items for "${id}" disagree with the control`);
    if (parentOf(row) !== zone || parentOf(tray) === null || parentOf(zone) === null) out.push(`the items for "${id}" were taken apart`);
    for (const part of [zone, tray]) if (hidden(part)) out.push(`the items for "${id}" are hidden`);
    tokens.forEach((b, i) => {
      const name = `item ${LETTERS[i]}`;
      if (parentOf(b) !== (added.has(i) ? row : tray)) out.push(`${name} of "${id}" is not where the control says`);
      if (hidden(b) || tagOf(b) !== "button") out.push(`${name} of "${id}" is hidden`);
      const position = style(b, "position");
      if (position === "absolute" || position === "fixed") out.push(`${name} of "${id}" was taken out of the layout`);
      if (hasAttribute(b, "hidden") || (dragsInFlight === 0 && attr(b, "style") !== "")) out.push(`${name} of "${id}" was moved or hidden`);
    });
    return out;
  };
  // The layout half, read only by the verifier: the tray and the drawing have room, each item sits inside its place, is visible, and nothing is drawn over it.
  const layout = (): string[] => {
    if (!layoutAvailable() || dragsInFlight > 0) return [];
    const out: string[] = [];
    for (const [name, part] of [["tray", tray], ["drop place", zone]] as const) {
      const r = rectOf(part);
      if (r.width < 44 || r.height < 44) out.push(`the ${name} for "${id}" is too small to use`);
      if (effectiveOpacity(part) < 0.5) out.push(`the ${name} for "${id}" is faded out`);
    }
    tokens.forEach((b, i) => {
      const name = `item ${LETTERS[i]}`;
      const r = rectOf(b);
      const home = parentOf(b);
      if (r.width < 40 || r.height < 40) out.push(`${name} of "${id}" is too small to press`);
      if (home) {
        const c = rectOf(home);
        if (r.left < c.left - 2 || r.right > c.right + 2 || r.top < c.top - 2 || r.bottom > c.bottom + 2) out.push(`${name} of "${id}" is outside its place`);
      }
      if (effectiveOpacity(b) < 0.5) out.push(`${name} of "${id}" is faded out`);
      const hit = hitAt(r.left + r.width / 2, r.top + r.height / 2);
      if (hit && hit !== b && !contains(b, hit)) out.push(`${name} of "${id}" is covered by something else`);
    });
    return out;
  };
  render();
  return { zone, tray, check, layout };
}
