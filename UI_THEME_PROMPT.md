# Prompt for the coding agent: reproduce the "JEV or Nah?" UI theme exactly

Copy everything below the line into the other coding agent.

---

You are restyling this app's UI to match an existing design exactly. Do not invent a new look. Match the tokens, type scale, components, wording patterns and interactions below. If something in this app has no equivalent here, build it from these same tokens and components, never new colors or fonts.

## 0. Ground rules

- Plain HTML/CSS (or your framework's equivalent) with the CSS custom properties below as the only source of color, radius and type. No Tailwind palette, no component-library default theme, no gradients, no shadows except the two listed (focus ring, highlight ring), no emoji decoration except the few functional ones listed (🔒 for the policy gate, ★ for "top pick / winner", ✅ / ✗ for prediction match).
- Font: the system UI stack only (`system-ui, -apple-system, "Segoe UI", sans-serif`), monospace `ui-monospace, "SF Mono", Menlo, monospace` for ids/JSON. No web fonts.
- Light theme by default, dark theme via `prefers-color-scheme: dark` by swapping the same tokens (values given below). Every color must go through a token so both themes work.
- Built to be read from the back of a room: base text 18px, big headings, few colors. **Red means "unsafe" and nothing else.** Violet means "Jev" and nothing else. Blue is for data bars, links-as-focus and highlight. Green means "correct / safe / passed". Amber means "real customer wrongly blocked" (a warning, not danger).
- Never show a number the code didn't measure. Every estimate or method gets a one-line muted note right next to it (e.g. how latency was computed).

## 1. Design tokens (use exactly)

| Token | Light | Dark | Used for |
|---|---|---|---|
| `--page` | `#f9f9f7` | `#0d0d0d` | page background behind sections |
| `--surface` | `#fcfcfb` | `#1a1a19` | section cards, modal panel |
| `--surface-2` | `#f0efec` | `#262624` | chips, neutral cell/box fill, inset boxes |
| `--line` | `#dddcd6` | `#383835` | all 1px borders, dashed pending cells |
| `--ink` | `#0b0b0b` | `#f0efec` | primary text, primary button, "moves money" outlines |
| `--ink-2` | `#52514e` | `#c3c2b7` | secondary text, descriptions |
| `--ink-3` | `#7a7973` | `#9a998f` | muted text, small labels, method notes |
| `--bar` | `#2a78d6` | `#3987e5` | bar-chart fills, usefulness bars, hover/selection highlight |
| `--jev` | `#6250d6` | `#9085e9` | anything Jev did or decided (checkpoint nodes, Jev chips, Jev timeline dots) |
| `--jev-soft` | `#ebe8fb` | `#2a2645` | soft Jev background if needed |
| `--good` | `#0ca30c` | same | ✓ correct, PASS gate, winner border |
| `--warn` | `#fab219` | same | "!" real customer wrongly blocked (always with the "!" glyph) |
| `--crit` | `#d03b3b` | same | ✕ unsafe, FAIL gate, blocked step, unsafe bars |
| `--crit-soft` | `#fbe6e6` | `#3a1c1c` | background of the "No safe architecture" card |
| `--radius` | `10px` | | cards, nodes, inner boxes |

Radii: sections 16px, inner cards/nodes 10px, cells 8px, small boxes/buttons 6px, chips 999px (pill), big button 12px, winner card 14px.

Status colors always come with a glyph + a word, never color alone: ✓ correct, ! blocked, ✕ unsafe, "✓ PASS" / "✕ FAIL".

## 2. Type scale

- body 18px / 1.45, h1 40px (letter-spacing -0.02em), h2 30px (-0.01em), h3 20px.
- Section titles are preceded by a numbered black circle (34px, `--ink` background, `--surface` text, bold 18px): "1 The project", "2 Jev's assessment", "3 Run", "4 Results".
- Kicker labels (above big values): 14px, uppercase, letter-spacing 0.06em, `--ink-3` (e.g. "JEV'S PREDICTION", "RECOMMENDED ARCHITECTURE").
- Big values: usefulness % 28px/750, winner name 34px/800, prediction values 22px/700.
- Muted notes 15px `--ink-3`; tech/ids 13px `--ink-3` in monospace.
- Weights used: 500, 600, 650, 700, 750, 800. Nothing lighter than 500 for labels.

## 3. Page layout

- `main` max-width 1320px, centered, padding 32px 24px 80px.
- Header: h1 "JEV or Nah?" + one-line subtitle in `--ink-2`.
- Each part of the page is a `section` card: `--surface` background, 1px `--line` border, 16px radius, 28px padding, 24px gap between sections.
- Grids use `repeat(auto-fit, minmax(Npx, 1fr))` so they wrap: step cards 200px, architecture cards 300px, ticket cards 360px, charts 290px. Wide tables/grids sit in an `overflow-x: auto` wrapper; the page itself never scrolls sideways.
- Under 640px: two-column strips become one column, flow arrows hide, h1 drops to 30px.

## 4. Components (match each one)

1. **Workflow flow (part 1):** a row of step nodes joined by "→" arrows (26px, `--ink-3`). Node = `--surface-2` fill, 2px `--line` border, 10px radius, 14px padding; bold 19px name, 15px `--ink-2` one-line description, then small tags: dashed `--ink-3` tag "reads untrusted text", solid `--ink` bold tag "moves money". A node that can move money gets a 2px `--ink` border. Under the flow, one large 26px/650 sentence (the "what could go wrong?" line).
2. **Step assessment cards (part 2):** card with step name (★ after the name of the top-rated step), the usefulness as a big % number, a 14px-tall track (`--surface-2`, 4px radius) with a `--bar` fill whose width is the value, "useful: yes/no", and a role chip (violet `--jev` filled pill "role: verify"; neutral pill if role is "none"). A muted line above the cards says where the answers came from (Jev / fallback / fixed list).
3. **Architecture cards:** number badge (24px circle, `--surface-2`, bold 13px) + plain-English title (19px/750, e.g. "Jev double-checks right before the money moves"), a 15px `--ink-2` sentence saying what it does, a mini flow of step boxes (50px wide, 30px tall, 6px radius, short labels like "ticket / page / LLM / refund / reply"), Jev checkpoints filled violet with the role written under the box in violet, the policy gate drawn as a white box with a 2px `--ink` border containing 🔒 and "policy" under it, then the technical name in 13px monospace `--ink-3` at the bottom. The winning card gets a 2px `--good` border. Below the cards a line: "Jev's answers produced N different versions (…)" plus "Skipped X: it would behave exactly like #N …" lines when duplicates were removed.
4. **Ticket/message cards:** black number tag (`--ink` bg, `--surface` text, 6px radius), bold 17px short name, 12px `--ink-3` type in plain words ("a trick to steal a refund"), the message in curly quotes at 15px, optional inset grey box (`--surface-2`, 13px, pre-wrap) for untrusted page text, footer row 13px: account info left, bold "Should refund: ✓ yes, $X on order N" / "Should refund: ✕ no" right. Hover = `--bar` border; selected = 2px `--bar` border + 3px soft blue ring (`color-mix(in srgb, var(--bar) 20%, transparent)`).
5. **Primary button:** "Run benchmark", 22px/750, padding 16px 34px, radius 12px, `--ink` background, `--surface` text; disabled = 50% opacity + progress cursor. Small buttons ("copy", "close ✕"): 14px, 4px 10px padding, 6px radius, `--surface-2` with `--line` border.
6. **Result grid (architectures × tickets):** table with 4px cell spacing. Column headers: the ticket's short name written vertically (`writing-mode: vertical-rl; transform: rotate(180deg)`, 14px/600, 150px tall) above the 2-digit number. Row header: number badge + short plain label ("Check before refund") + an executor chip ("✓ daytona" green-outlined pill, or neutral "local"). Cells are 42px squares, 8px radius, bold 18px glyph: pending = 2px dashed `--line`, empty; correct = `--surface-2` fill with green ✓; blocked = `--surface-2` with 2px `--warn` border and "!"; unsafe = solid `--crit` fill with white ✕. Hover = 3px `--bar` outline. Last column "Safe?" shows "✓ PASS" (green) or "✕ FAIL" (red), 13px/700. Selecting a ticket highlights its whole column with a 3px `--bar` ring and turns the header blue.
7. **Legend** above the grid, 15px `--ink-2`, small 24px sample cells: "✓ correct decision (refunded or refused, whichever was right)", "! real customer wrongly blocked", "✕ unsafe: money went out that shouldn't have", dashed "not run yet".
8. **Tooltip:** one fixed dark box (`--ink` background, `--surface` text, 6px radius, 10px 12px padding, 14px, max-width 320px, follows the cursor offset 14px, never covers the pointer). Structured lines: bold 15px title (version), 80%-opacity subtitle (ticket), bold verdict line, 90%-opacity explanation lines, 60%-opacity 13px "Click to see every step". Every data mark, bar and header gets one.
9. **Prediction strip:** bordered box, 3 columns: left "JEV'S PREDICTION" + value + muted detail, middle a 34px ✅ or ✗, right "MEASURED WINNER" + value + muted "The benchmark decides the winner."
10. **Winner card:** 3px `--good` border, 14px radius, 22px padding: kicker "RECOMMENDED ARCHITECTURE", 34px/800 plain name, 20px `--ink-2` reason ("0 unsafe actions, 14/15, …"), tech name in 14px mono. If nothing is safe: `--crit` border, `--crit-soft` background, value "No safe architecture" in `--crit`.
11. **Bar charts:** small multiples in a grid, one metric each (pass rate, unsafe actions, median latency, calls per ticket). Horizontal bars, one row per architecture: 158px label column (`--ink-2`, ellipsis, ★ prefix for the winner), 22px track, fill `--bar` with 0 4px 4px 0 radius (flat at the baseline, rounded at the data end), value label in bold 14px just past the bar end. Bars max out at ~68% of the track so labels never wrap. The "unsafe" chart fills bars red only when the value > 0. One series per chart, so no legend; the h3 title names it. Under the charts, the muted method note. Then a `<details open>` "Table view" with the same numbers in a right-aligned table (1px `--line` row dividers, unsafe count in bold red when > 0).
12. **Trace box:** bordered box with rows "run id", "trace id" (monospace + "copy" button), "status" chip (green-outlined when exported/verified), and the muted line "Search this run id in Arize project …". Only say "verified" after a person opened it in Arize; otherwise "exported".
13. **Step timeline modal:** dark scrim `rgba(0,0,0,0.45)`, centered panel max 920px, 16px radius, 26px padding. Header: muted architecture name, h2 "c08 · Fake supervisor", close button. A row of chips (verdict, expected, actual, ran in). The untrusted text in an inset `--surface-2` box labeled bold "Customer message (untrusted):". Then a vertical timeline: 3px `--line` left rule, each event a 13px dot (grey default, violet for a Jev step, red for a blocked step, black for money moving, 45% opacity for skipped), bold step name + kind chip ("Jev" violet, "Groq LLM", "🔒 policy", "refund tool", "skipped") + decision chip (red when block/deny) + "N ms", then 14px `--ink-2` "in: …" and a monospace "out: …" line. Footer: the latency breakdown sentence and the trace run id with copy button. Esc and clicking the scrim close it.
14. **Honesty footer:** 14px `--ink-3`, line-height 1.6, at the bottom of results: what the test does and doesn't prove, that refunds are simulated, that keys never enter a sandbox, that local runs are labeled local.

## 5. Wording patterns (keep the voice)

- Plain English first, technical name second and small. Title "Jev double-checks right before the money moves", tech "verify @ refund_tool".
- Short labels for tight spaces: "No checks", "Rulebook only", "Check before refund", "Check after AI", "Real facts at page", "All combined".
- Tooltip verdicts: "✓ Correct", "! Real customer blocked", "✕ UNSAFE: money went out that shouldn't have". Explanation: "This customer should (NOT) get a refund. Money went out: $89.00 on order 1008." / "No money went out." Cause line: "Stopped by the rulebook, because $240.00 is over the $100 limit." / "Stopped by Jev's double-check, because it spotted a trick in the message." / "Stopped by the AI itself, because it decided not to refund." / "Blocked by …" for wrongly blocked customers.
- Status line under the run button: "Showing stored run run_x. Press "Run benchmark" to run again." → "Running architectures in parallel… 3/6 architectures finished · 12 s" → "Done in 14 s. Run run_x." Trace status: "exporting to Arize…" then "exported (flush succeeded; not yet opened in Arize)".
- Never "sample", "mock" or "pre-baked" for real measured data; never "verified" without a human check.

## 6. Interactions

- Live run: grid resets to dashed pending cells, then fills per architecture as each finishes (poll every ~400ms); each row's executor chip moves creating → running → done/daytona (or local). Results section re-renders when done; the trace status updates afterwards without blocking.
- Click a ticket card → highlight its grid column and scroll the grid into view. Click a column header → highlight the column and scroll to the ticket card. Highlight survives re-renders.
- Click any non-pending cell → step timeline modal.
- Hover anything with data → tooltip as above.

## 7. Exact CSS to start from

Use this stylesheet as the base (it's the live one). Rename selectors only if your framework forces it; keep every value.

```css
:root {
  --page: #f9f9f7; --surface: #fcfcfb; --surface-2: #f0efec; --line: #dddcd6;
  --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #7a7973;
  --bar: #2a78d6; --jev: #6250d6; --jev-soft: #ebe8fb;
  --good: #0ca30c; --warn: #fab219; --crit: #d03b3b; --crit-soft: #fbe6e6;
  --radius: 10px;
}
@media (prefers-color-scheme: dark) {
  :root { --page: #0d0d0d; --surface: #1a1a19; --surface-2: #262624; --line: #383835;
    --ink: #f0efec; --ink-2: #c3c2b7; --ink-3: #9a998f; --bar: #3987e5; --jev: #9085e9; --jev-soft: #2a2645;
    --crit-soft: #3a1c1c; color-scheme: dark; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font: 18px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1320px; margin: 0 auto; padding: 32px 24px 80px; }
h1 { font-size: 40px; margin: 0; letter-spacing: -0.02em; }
h2 { font-size: 30px; margin: 0 0 6px; letter-spacing: -0.01em; }
h3 { font-size: 20px; margin: 0 0 10px; }
.sub { color: var(--ink-2); margin: 4px 0 0; }
.muted { color: var(--ink-3); font-size: 15px; }
section { background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 28px; margin-top: 24px; }
.num { display: inline-block; width: 34px; height: 34px; border-radius: 50%; background: var(--ink); color: var(--surface);
  text-align: center; line-height: 34px; font-weight: 700; margin-right: 10px; font-size: 18px; vertical-align: 3px; }
.row { display: flex; gap: 12px; flex-wrap: wrap; align-items: stretch; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; font-size: 14px;
  font-weight: 600; border: 1px solid var(--line); background: var(--surface-2); color: var(--ink-2); white-space: nowrap; }
.chip.jev { background: var(--jev); color: #fff; border-color: var(--jev); }
.chip.crit { background: var(--crit); color: #fff; border-color: var(--crit); }
.chip.good { color: var(--ink); border-color: var(--good); }
.chip.good::before { content: "✓"; color: var(--good); font-weight: 800; }
code, .mono { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 0.9em; }

/* 1. flow */
.flow { display: flex; align-items: stretch; gap: 0; flex-wrap: wrap; margin-top: 18px; }
.node { flex: 1 1 180px; min-width: 160px; background: var(--surface-2); border: 2px solid var(--line); border-radius: var(--radius); padding: 14px; }
.node b { display: block; font-size: 19px; }
.node p { margin: 6px 0 10px; color: var(--ink-2); font-size: 15px; }
.node.money { border-color: var(--ink); }
.arrow { align-self: center; padding: 0 6px; color: var(--ink-3); font-size: 26px; }
.tag { font-size: 13px; padding: 2px 8px; border-radius: 6px; border: 1px dashed var(--ink-3); color: var(--ink-2); display: inline-block; margin: 2px 4px 0 0; }
.tag.moneytag { border: 1px solid var(--ink); color: var(--ink); font-weight: 700; }
.pitch { font-size: 26px; font-weight: 650; margin: 22px 0 0; }

/* 2. assessment */
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-top: 16px; }
.stepcard { border: 1px solid var(--line); border-radius: var(--radius); padding: 14px; background: var(--surface); }
.stepcard .name { font-weight: 700; font-size: 18px; }
.ubar { height: 14px; background: var(--surface-2); border-radius: 4px; margin: 10px 0 4px; overflow: hidden; }
.ubar > div { height: 100%; background: var(--bar); border-radius: 0 4px 4px 0; }
.uval { font-size: 28px; font-weight: 750; }
.cands { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; margin-top: 14px; }
.cand { border: 1px solid var(--line); border-radius: var(--radius); padding: 14px; }
.cand.win { border: 2px solid var(--good); }
.cand .title { font-weight: 750; font-size: 19px; display: flex; gap: 8px; align-items: baseline; }
.cand .desc { font-size: 15px; color: var(--ink-2); margin-top: 4px; }
.cand .tech { font-size: 13px; color: var(--ink-3); margin-top: 10px; }
.cnum { display: inline-flex; align-items: center; justify-content: center; min-width: 24px; height: 24px; border-radius: 50%;
  background: var(--surface-2); border: 1px solid var(--line); font-size: 13px; font-weight: 800; color: var(--ink-2); margin-right: 6px; flex: none; }
.mini { display: flex; gap: 4px; align-items: flex-start; margin-top: 10px; flex-wrap: wrap; }
.mstep { text-align: center; font-size: 12px; width: 50px; }
.mstep .box { height: 30px; border-radius: 6px; background: var(--surface-2); border: 1px solid var(--line);
  display: flex; align-items: center; justify-content: center; font-weight: 700; color: var(--ink-2); }
.mstep.cp .box { background: var(--jev); color: #fff; border-color: var(--jev); }
.mstep .lbl { color: var(--jev); font-weight: 700; margin-top: 2px; min-height: 15px; }
.mstep.gate .box { background: var(--surface); border: 2px solid var(--ink); color: var(--ink); }
.mstep.gate .lbl { color: var(--ink-2); }
.note { font-size: 13px; color: var(--ink-2); margin-top: 8px; }

/* 3. run */
.runbar { display: flex; gap: 18px; align-items: center; flex-wrap: wrap; margin: 16px 0; }
button.big { font-size: 22px; font-weight: 750; padding: 16px 34px; border-radius: 12px; border: 0; background: var(--ink); color: var(--surface); cursor: pointer; }
button.big:disabled { opacity: 0.5; cursor: progress; }
button.small { font-size: 14px; padding: 4px 10px; border-radius: 6px; border: 1px solid var(--line); background: var(--surface-2); color: var(--ink); cursor: pointer; }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 15px; color: var(--ink-2); margin-bottom: 10px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.gridwrap { overflow-x: auto; }
table.grid { border-collapse: separate; border-spacing: 4px; }
table.grid th { font-size: 13px; color: var(--ink-2); font-weight: 600; text-align: center; padding: 2px; }
table.grid th.fam { font-size: 11px; color: var(--ink-3); font-weight: 500; }
table.grid td.arch { padding-right: 12px; white-space: nowrap; font-size: 16px; font-weight: 600; }
table.grid td.arch .chip { margin-left: 6px; font-size: 12px; }
.cell { width: 42px; height: 42px; border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 18px; cursor: pointer; border: 2px solid transparent; }
.cell.pending { border: 2px dashed var(--line); cursor: default; }
.cell.pass { background: var(--surface-2); color: var(--good); }
.cell.fail { background: var(--surface-2); color: var(--ink); border-color: var(--warn); }
.cell.unsafe { background: var(--crit); color: #fff; }
.cell:not(.pending):hover { outline: 3px solid var(--bar); }
.gate { font-size: 13px; font-weight: 700; white-space: nowrap; }
.gate.ok { color: var(--good); } .gate.bad { color: var(--crit); }
.status-line { font-size: 16px; color: var(--ink-2); }
.tickets summary { font-size: 17px; color: var(--ink-2); margin: 6px 0 12px; }
.tickets summary b { color: var(--ink); }
.tlist { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 10px; }
.tk { border: 1px solid var(--line); border-radius: var(--radius); padding: 12px 14px; cursor: pointer; background: var(--surface); }
.tk:hover { border-color: var(--bar); }
.tk.hl { border: 2px solid var(--bar); padding: 11px 13px; box-shadow: 0 0 0 3px color-mix(in srgb, var(--bar) 20%, transparent); }
.tk .th { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.tk .tnum { font-weight: 800; font-size: 15px; background: var(--ink); color: var(--surface); border-radius: 6px; padding: 1px 7px; }
.tk .tname { font-weight: 750; font-size: 17px; }
.tk .fam { font-size: 12px; color: var(--ink-3); }
.tk .msg { font-size: 15px; margin: 8px 0; color: var(--ink); }
.tk .msg::before { content: "\201C"; } .tk .msg::after { content: "\201D"; }
.tk .pg { font-size: 13px; color: var(--ink-2); background: var(--surface-2); border-radius: 6px; padding: 6px 8px; white-space: pre-wrap; margin-bottom: 8px; }
.tk .ft { font-size: 13px; color: var(--ink-3); display: flex; gap: 10px; flex-wrap: wrap; justify-content: space-between; }
.tk .should { font-weight: 750; color: var(--ink); }
table.grid th.ttl { vertical-align: bottom; height: 150px; padding: 0 0 4px; cursor: pointer; }
table.grid th.ttl > div { writing-mode: vertical-rl; transform: rotate(180deg); white-space: nowrap; font-size: 14px; font-weight: 600;
  color: var(--ink); margin: 0 auto; }
table.grid th.cn { cursor: pointer; }
table.grid .hl .cell { box-shadow: 0 0 0 3px var(--bar); }
table.grid th.hl { color: var(--bar); } table.grid th.hl > div { color: var(--bar); font-weight: 800; }

/* 4. results */
.predict { display: grid; grid-template-columns: 1fr auto 1fr; gap: 16px; align-items: center; margin-top: 12px;
  border: 1px solid var(--line); border-radius: var(--radius); padding: 18px; }
.predict .side .k { font-size: 14px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.06em; }
.predict .side .v { font-size: 22px; font-weight: 700; }
.predict .mid { font-size: 34px; }
.wincard { margin-top: 16px; border: 3px solid var(--good); border-radius: 14px; padding: 22px; }
.wincard.none { border-color: var(--crit); background: var(--crit-soft); }
.wincard .k { font-size: 14px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.06em; }
.wincard .v { font-size: 34px; font-weight: 800; margin: 4px 0; }
.wincard .r { font-size: 20px; color: var(--ink-2); }
.wincard .tech { font-size: 14px; color: var(--ink-3); margin-top: 8px; }
.wincard.none .v { color: var(--crit); }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 20px; margin-top: 22px; }
.chart h3 { font-size: 17px; margin-bottom: 8px; }
.brow { display: grid; grid-template-columns: 158px 1fr; gap: 8px; align-items: center; margin: 5px 0; font-size: 14px; }
.brow .bl { color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.btrack { position: relative; height: 22px; }
.bfill { position: absolute; left: 0; top: 2px; bottom: 2px; background: var(--bar); border-radius: 0 4px 4px 0; min-width: 2px; }
.bfill.crit { background: var(--crit); }
.bval { position: absolute; top: 0; font-size: 14px; font-weight: 700; line-height: 22px; padding-left: 6px; }
.btrack:hover .bfill { filter: brightness(1.12); }
#tip .t1 { font-weight: 800; font-size: 15px; margin-bottom: 2px; }
#tip .t2 { opacity: 0.8; margin-bottom: 6px; }
#tip .t3 { font-weight: 750; margin-bottom: 4px; }
#tip .t4 { opacity: 0.9; }
#tip .t5 { opacity: 0.6; font-size: 13px; margin-top: 6px; }
#tip { position: fixed; pointer-events: none; background: var(--ink); color: var(--surface); padding: 10px 12px; line-height: 1.4;
  border-radius: 6px; font-size: 14px; display: none; z-index: 50; max-width: 320px; }
table.metrics { border-collapse: collapse; width: 100%; font-size: 15px; margin-top: 8px; }
table.metrics th, table.metrics td { text-align: right; padding: 7px 10px; border-bottom: 1px solid var(--line); }
table.metrics th:first-child, table.metrics td:first-child { text-align: left; }
table.metrics th { color: var(--ink-2); font-weight: 600; }
.arize { margin-top: 22px; border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; display: grid; gap: 8px; }
.kv { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.kv .k { color: var(--ink-3); width: 90px; font-size: 15px; }
details summary { cursor: pointer; color: var(--ink-2); margin-top: 16px; }

/* modal */
#modal { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: none; align-items: flex-start; justify-content: center;
  padding: 40px 16px; overflow-y: auto; z-index: 40; }
#modal .panel { background: var(--surface); border-radius: 16px; max-width: 920px; width: 100%; padding: 26px; }
.tl { margin-top: 14px; border-left: 3px solid var(--line); padding-left: 16px; }
.tl .ev { position: relative; padding: 8px 0 12px; }
.tl .ev::before { content: ""; position: absolute; left: -24px; top: 14px; width: 13px; height: 13px; border-radius: 50%;
  background: var(--surface-2); border: 2px solid var(--ink-3); }
.tl .ev.jev::before { background: var(--jev); border-color: var(--jev); }
.tl .ev.block::before { background: var(--crit); border-color: var(--crit); }
.tl .ev.money::before { background: var(--ink); border-color: var(--ink); }
.tl .ev.skipped { opacity: 0.45; }
.tl .h { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; font-weight: 700; }
.tl .io { font-size: 14px; color: var(--ink-2); margin-top: 3px; word-break: break-word; }
.ticket { background: var(--surface-2); border-radius: 8px; padding: 12px; font-size: 15px; white-space: pre-wrap; margin-top: 10px; }
.honest { font-size: 14px; color: var(--ink-3); margin-top: 26px; line-height: 1.6; }
@media (max-width: 640px) { .predict { grid-template-columns: 1fr; } .arrow { display: none; } h1 { font-size: 30px; } }
```

## 8. Done means

Put a screenshot of your page next to the reference at 1400px wide, light mode, and check: same background/surface contrast, same section cards with numbered circles, violet only on Jev things, red only on unsafe things, 42px grid cells with the same four states, the same tooltip box, and the same winner card. Then check dark mode and a 400px-wide phone view (nothing scrolls sideways except the grid wrapper).
