// The Kit's one stylesheet, as a module of its own so that `audit.ts` can compare the stylesheet in the page with it. The audit skips its CSS rules for a
// stylesheet only when that element is one `environment()` created AND its text is exactly this string; any other stylesheet, including one a page gave the
// id `syn-style`, or this one after a page edited it, gets the full CSS check (kit-guardian W3: a page-made `syn-style` used to skip it).

export const STYLE = `
:root{--syn-bg:#ffffff;--syn-fg:#2f3a34;--syn-muted:#4f5d57;--syn-accent:#0a776b;--syn-edge:#075247;--syn-line:#075247;--syn-card:#f7f8f4;--syn-border:#d3dace;--syn-radius:18px;--syn-indicator:#d6336c;--syn-liquid:#7cc4d8;--syn-cloud:#d9d4c4;--syn-yeast:#e8d9a8;--syn-oil:#e0a43a;--syn-gold:#8f6100;--syn-goldsoft:#fff8e6;--syn-goldborder:#ecd9a6;--syn-try:#8a3340;--syn-step:#6b4aa0;--syn-bench:#fbfcf8}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--syn-bg:#16201c;--syn-fg:#e9efea;--syn-muted:#a4b2ab;--syn-accent:#16b6a3;--syn-edge:#063f38;--syn-line:#8fd9cb;--syn-card:#0e1512;--syn-border:#34403a;--syn-indicator:#f06595;--syn-liquid:#3b8fa6;--syn-cloud:#8f8a7a;--syn-yeast:#8a7a3f;--syn-oil:#b9822a;--syn-gold:#e8b84a;--syn-goldsoft:#2a2414;--syn-goldborder:#5a4a1c;--syn-try:#f0a3ad;--syn-step:#b9a0e6;--syn-bench:#121a16}}
:root[data-theme="dark"]{--syn-bg:#16201c;--syn-fg:#e9efea;--syn-muted:#a4b2ab;--syn-accent:#16b6a3;--syn-edge:#063f38;--syn-line:#8fd9cb;--syn-card:#0e1512;--syn-border:#34403a;--syn-indicator:#f06595;--syn-liquid:#3b8fa6;--syn-cloud:#8f8a7a;--syn-yeast:#8a7a3f;--syn-oil:#b9822a;--syn-gold:#e8b84a;--syn-goldsoft:#2a2414;--syn-goldborder:#5a4a1c;--syn-try:#f0a3ad;--syn-step:#b9a0e6;--syn-bench:#121a16}
*{box-sizing:border-box}
body{margin:0;background:var(--syn-bg);color:var(--syn-fg);font:16px/1.5 system-ui,sans-serif}
.syn-env{max-width:1440px;margin:0 auto;padding:10px 14px 16px;display:grid;gap:8px}
.syn-head{display:grid;gap:4px}
.syn-kicker{font:700 .72rem/1.2 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--syn-accent)}
.syn-env h1{font:700 1.6rem/1.15 Georgia,"Times New Roman",serif;margin:0;color:var(--syn-gold)}
.syn-try{margin:0;font-weight:600;color:var(--syn-try)}
.syn-keyidea{background:var(--syn-goldsoft);border:2px solid var(--syn-goldborder);border-radius:14px;padding:6px 12px;color:var(--syn-fg);font-size:.95rem}
.syn-keyidea strong{color:var(--syn-gold);margin-right:.4em}
.syn-note{display:inline;color:var(--syn-fg)}
.syn-head .syn-steps{list-style:decimal inside;margin:2px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px}
.syn-head .syn-steps li{background:var(--syn-card);border:2px solid var(--syn-border);border-radius:14px;padding:6px 10px;font-size:.85rem;line-height:1.35;color:var(--syn-fg)}
.syn-head .syn-steps li::marker{color:var(--syn-step);font-weight:800}
.syn-main{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:14px;align-items:start}
.syn-main:has(>.syn-stage>.syn-app-bench){align-items:stretch}
.syn-stage{overflow-anchor:none;min-height:120px;border:2px solid var(--syn-border);border-radius:var(--syn-radius);padding:12px;display:grid;gap:8px;background:var(--syn-bench)}
.syn-stage:has(>.syn-app-bench){align-content:center}
.syn-stage:empty{display:none}
.syn-panel{display:grid;gap:10px;align-content:start}
.syn-controls,.syn-readouts{display:grid;gap:10px}
.syn-readouts{grid-template-columns:repeat(2,minmax(0,1fr))}
.syn-readouts:empty{display:none}
.syn-extras{display:grid;gap:12px;grid-template-columns:repeat(2,minmax(0,1fr));align-items:start}
.syn-extras:empty{display:none}
.syn-control{display:grid;gap:4px;background:var(--syn-card);border:2px solid var(--syn-border);border-radius:var(--syn-radius);padding:8px 14px}
.syn-control label{font-weight:600}
.syn-control input[type=range]{width:100%;min-height:44px;accent-color:var(--syn-accent)}
.syn-readout{display:grid;gap:2px;align-content:center;min-height:64px;background:var(--syn-card);border:2px solid var(--syn-border);border-radius:var(--syn-radius);padding:8px 14px}
.syn-readout:last-child:nth-child(odd){grid-column:1/-1}
.syn-readout span{font:700 .7rem/1.2 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--syn-muted)}
.syn-readout output{font-size:1.5rem;font-weight:800;line-height:1.1;color:var(--syn-accent);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.syn-btn{min-height:44px;min-width:44px;padding:0 16px;border-radius:var(--syn-radius);border:2px solid var(--syn-border);background:var(--syn-card);color:var(--syn-fg);font:inherit;font-weight:600;box-shadow:0 3px 0 var(--syn-border)}
.syn-btn:active{transform:translateY(2px);box-shadow:0 1px 0 var(--syn-border)}
.syn-text{margin:0;color:var(--syn-muted)}
.syn-steps{margin:0;padding-left:1.4rem;display:grid;gap:4px}
.syn-card{background:var(--syn-card);border:2px solid var(--syn-border);border-radius:var(--syn-radius);padding:8px 16px}
.syn-card p{margin:6px 0}
.syn-card>div[role=group]{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
@media (max-width:820px){.syn-stage:has(>.syn-masses){grid-template-columns:1fr}.syn-main,.syn-extras{grid-template-columns:1fr}.syn-env h1{font-size:1.4rem}.syn-card>div[role=group]{grid-template-columns:1fr}}
.syn-card dl{display:grid;gap:2px;margin:0}
.syn-card dt{font-weight:600}
.syn-card dd{margin:0 0 6px;color:var(--syn-muted)}
.syn-sr{position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.syn-graph{width:100%;height:auto;max-height:260px}
.syn-table-wrap{overflow-x:auto;max-width:100%}
.syn-table{border-collapse:collapse;width:100%;table-layout:fixed;font-variant-numeric:tabular-nums}
.syn-table th,.syn-table td{border:1px solid var(--syn-border);padding:4px 6px;text-align:right;overflow-wrap:anywhere;font-size:.875rem}
.syn-masses{display:grid;gap:8px}
.syn-stage>.syn-masses{order:1}
.syn-stage:has(>.syn-masses){grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);align-items:center}
.syn-tray,.syn-hanger{display:flex;flex-wrap:wrap;align-items:center;gap:8px;min-height:64px;padding:8px;border-radius:var(--syn-radius)}
.syn-tray{border:2px dashed var(--syn-border)}
.syn-hanger{border:2px solid var(--syn-border);background:var(--syn-card)}
.syn-hanger.syn-over{border-color:var(--syn-accent)}
.syn-cap{flex:0 0 100%;font-size:.75rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--syn-muted)}
.syn-mass{min-width:44px;min-height:44px;padding:0;border-radius:12px;border:2px solid var(--syn-edge);background:var(--syn-accent);color:var(--syn-bg);font:inherit;font-weight:800;cursor:grab;touch-action:none;box-shadow:0 3px 0 var(--syn-edge);user-select:none}
.syn-mass.syn-dragging{position:relative;z-index:2;cursor:grabbing;opacity:.9}
.syn-stage>.syn-masses{grid-column:1/-1}
.syn-masses:has(>.syn-scene){grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);grid-template-areas:"spring tray" "hanger tray";align-items:start;column-gap:12px;row-gap:0}
.syn-masses>.syn-scene{grid-area:spring;max-height:300px;justify-self:center}
.syn-masses>.syn-tray{grid-area:tray;align-content:flex-start}
.syn-masses>.syn-hanger{grid-area:hanger;flex-direction:column;flex-wrap:nowrap;align-items:center;justify-self:center;width:min(100%,160px);gap:3px;border-top:5px solid var(--syn-line);border-radius:4px 4px 16px 16px}
.syn-masses .syn-mass{border-radius:8px;border-color:#262e33;background:#48525a;color:#eef3f6;box-shadow:0 3px 0 #262e33}
.syn-hanger .syn-mass{width:100%;min-height:44px}
.syn-hanger .syn-mass:last-of-type{animation:syn-drop-in .45s cubic-bezier(.34,1.5,.5,1)}
@keyframes syn-drop-in{0%{transform:translateY(-18px);opacity:.4}60%{transform:translateY(4px);opacity:1}100%{transform:none}}
.syn-control-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
.syn-control-value{font-weight:800;color:var(--syn-accent);font-variant-numeric:tabular-nums}
.syn-control-quiet{padding:6px 14px}
.syn-control-quiet input[type=range]:not(:focus){position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.syn-planets{display:grid;gap:6px;grid-column:1/-1;width:100%}
.syn-planets .syn-scene{max-height:none;display:block}
.syn-planets-hint{text-align:center;font-size:.9rem}
.syn-planet{cursor:pointer}
.syn-a-bubble{animation:syn-bubble 1.3s ease-in-out infinite}
@keyframes syn-bubble{0%{transform:translateY(3px);opacity:.55}50%{opacity:1}100%{transform:translateY(-5px);opacity:.55}}
.syn-titr-drop{opacity:0}
.syn-titr-flask{cursor:grab;touch-action:none;transform-box:fill-box;transform-origin:50% 100%}
.syn-titr-flask:active{cursor:grabbing}
.syn-titr-frame>.syn-valves{position:absolute;left:30.5%;top:66%;transform:translateY(-50%)}
.syn-env:has(.syn-valve.syn-open) .syn-titr-drop{animation:syn-drip .5s linear infinite}
@keyframes syn-drip{0%{transform:translateY(-6px);opacity:1}100%{transform:translateY(26px);opacity:0}}
.syn-scene{width:100%;max-height:360px;height:auto}
.syn-valves{display:flex;align-items:center;gap:8px}
.syn-valve{min-width:88px;min-height:44px;padding:0 16px;border-radius:999px;border:2px solid var(--syn-edge);background:var(--syn-card);color:var(--syn-fg);font:inherit;font-weight:800;cursor:pointer;touch-action:none;user-select:none;box-shadow:0 3px 0 var(--syn-edge)}
.syn-valve.syn-open{background:var(--syn-accent);color:var(--syn-bg)}
.syn-dials{display:flex;justify-content:center}
.syn-dial{position:relative;width:96px;height:96px;border-radius:50%;border:3px solid var(--syn-edge);background:var(--syn-card);box-shadow:0 4px 0 var(--syn-edge);touch-action:none;user-select:none;cursor:grab}
.syn-dial-mark{position:absolute;left:50%;top:6px;width:6px;height:38px;margin-left:-3px;border-radius:3px;background:var(--syn-accent);transform-origin:50% 39px}
.syn-ferment{display:grid;gap:6px;max-width:440px;margin:0 auto;width:100%}
.syn-ferment .syn-scene{max-height:none;display:block}
.syn-orbit{display:grid;gap:6px;max-width:480px;margin:0 auto;width:100%}
.syn-orbit .syn-scene{max-height:none;display:block}
.syn-titr{display:grid;gap:6px;max-width:340px;margin:0 auto;width:100%}
.syn-titr-frame{position:relative}
.syn-titr-frame .syn-scene{max-height:none;display:block}
.syn-eye{position:absolute;left:55.4%;transform:translateY(-50%);min-width:44px;min-height:44px;padding:0 10px;border-radius:999px;border:2px solid var(--syn-edge);background:var(--syn-card);color:var(--syn-fg);font:inherit;font-weight:800;cursor:grab;touch-action:none;user-select:none;box-shadow:0 3px 0 var(--syn-edge)}
.syn-app-bench{display:flex;flex-wrap:wrap;justify-content:center;gap:10px;align-items:flex-end;width:100%}
.syn-app{flex:0 1 140px;max-width:140px;margin:0;display:grid;justify-items:center;gap:2px;background:var(--syn-card);border:2px solid var(--syn-border);border-radius:14px;padding:6px 6px 8px}
.syn-app-svg{width:100%;max-width:170px;height:auto;max-height:200px;overflow:hidden}
@media (min-width:821px){.syn-app-bench>figure.syn-app:only-of-type{flex:0 1 340px;max-width:340px}.syn-app-bench>figure.syn-app:only-of-type .syn-app-svg{max-width:300px;max-height:280px}}
.syn-app-label{font-size:.85rem;font-weight:700;color:var(--syn-fg);text-align:center;line-height:1.25}
.syn-a-rise,.syn-a-flicker,.syn-a-spin,.syn-a-swing,.syn-a-orbit,.syn-a-jig0,.syn-a-jig1,.syn-a-jig2,.syn-a-travel{transform-box:fill-box}
.syn-a-rise{animation:syn-rise 2.4s linear infinite}
@keyframes syn-rise{0%{transform:translateY(0);opacity:1}100%{transform:translateY(-46px);opacity:0}}
.syn-a-flicker{transform-origin:50% 100%;animation:syn-flicker .9s ease-in-out infinite alternate}
@keyframes syn-flicker{from{transform:scale(1,1)}to{transform:scale(.9,1.08)}}
.syn-a-spin{transform-origin:50% 50%;animation:syn-spin 1.6s linear infinite}
.syn-a-orbit{transform-origin:50% 50%;animation:syn-spin 6s linear infinite}
@keyframes syn-spin{to{transform:rotate(360deg)}}
.syn-a-swing{transform-origin:50% 0;animation:syn-swing 2s ease-in-out infinite alternate}
@keyframes syn-swing{from{transform:rotate(-16deg)}to{transform:rotate(16deg)}}
.syn-a-flow{animation:syn-flow 1.6s linear infinite}
@keyframes syn-flow{to{stroke-dashoffset:-24}}
.syn-a-jig0{animation:syn-jig0 1s ease-in-out infinite alternate}
.syn-a-jig1{animation:syn-jig1 1.1s ease-in-out infinite alternate}
.syn-a-jig2{animation:syn-jig2 .9s ease-in-out infinite alternate}
@keyframes syn-jig0{to{transform:translate(7px,-5px)}}
@keyframes syn-jig1{to{transform:translate(-6px,5px)}}
@keyframes syn-jig2{to{transform:translate(5px,7px)}}
.syn-a-travel{animation:syn-travel 2s linear infinite}
@keyframes syn-travel{to{transform:translateX(var(--syn-wl))}}
.syn-d1{animation-delay:-.6s}.syn-d2{animation-delay:-1.2s}.syn-d3{animation-delay:-1.8s}
.syn-sp0{animation:none!important}
.syn-sp1{animation-duration:4.2s}.syn-sp2{animation-duration:2.7s}.syn-sp3{animation-duration:1.7s}.syn-sp4{animation-duration:.9s}
.syn-app-grip{cursor:grab;touch-action:none}.syn-app-grip:active{cursor:grabbing}
.syn-a-pulse{transform-box:fill-box;transform-origin:center;animation:syn-pulse 1.8s ease-in-out infinite}
@keyframes syn-pulse{0%,100%{transform:scale(1);opacity:.9}50%{transform:scale(1.35);opacity:.35}}
.syn-app-hint{grid-column:1/-1;flex:0 0 100%;order:2;margin:2px 0 0;font-size:.85rem;color:var(--syn-muted);text-align:center}
.syn-app-zone{display:grid;justify-items:center;gap:4px;width:100%;border:2px dashed transparent;border-radius:12px}
.syn-app-zone.syn-over{border-color:var(--syn-accent);background:var(--syn-bench)}
.syn-app-added{display:flex;flex-wrap:wrap;justify-content:center;gap:6px}
.syn-app-tray{grid-column:1/-1;flex:0 0 100%;order:1;display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:6px;width:100%;min-height:56px;padding:6px;border:2px dashed var(--syn-border);border-radius:12px}
.syn-app-item{background:var(--syn-liquid);color:var(--syn-fg)}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
`;
