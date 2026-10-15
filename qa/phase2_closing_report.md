# Phase 2 closing report — stopped at the project’s request

This report uses the last completed full `python3 qa/run_all.py --fast` run: 76 jobs, 2529 PASS, 24 FAIL, 164 SKIP. It is not a green run. No new full run or investigation was started after the stop instruction. The already-running final production build and lint both finished successfully.

The baseline is the frozen pre-Phase-2 QA suite against the same application: 51 jobs, 652 PASS, 78 FAIL, no SKIPs. Data-only baseline suites were rerun with the repository scripts/data available; the original temporary snapshot omitted those directories. The old harness also silently accepted an s28 process crash after one PASS; the new harness records that crash as FAIL. These are counts of emitted PASS/FAIL outcomes, including reported exceptions, rather than a claim that every planned assertion reached execution.

## 1. Before and after

Cells are **PASS / FAIL / SKIP**. The after column sums the default and `?toc=two` jobs for each rewritten suite/device. A per-mode table follows. Unchanged suites retain their original single job.

| Suite | Device | Before | After |
|---|---|---:|---:|
| lint | data / engine | 29 / 0 / 0 | 29 / 0 / 0 |
| s00 | iphone14 | 7 / 1 / 0 | 7 / 1 / 0 |
| s00 | pixel7 | 7 / 1 / 0 | 7 / 1 / 0 |
| s01 | iphone14 | 18 / 3 / 0 | 122 / 2 / 0 |
| s01 | pixel7 | 18 / 3 / 0 | 122 / 2 / 0 |
| s02 | iphone14 | 9 / 0 / 0 | 9 / 0 / 0 |
| s02 | pixel7 | 9 / 0 / 0 | 9 / 0 / 0 |
| s03 | iphone14 | 11 / 3 / 0 | 109 / 0 / 4 |
| s03 | pixel7 | 11 / 3 / 0 | 111 / 0 / 4 |
| s04 | iphone14 | 1 / 3 / 0 | 105 / 0 / 0 |
| s04 | pixel7 | 1 / 3 / 0 | 105 / 0 / 0 |
| s05 | iphone14 | 3 / 6 / 0 | 46 / 1 / 0 |
| s05 | pixel7 | 3 / 6 / 0 | 58 / 0 / 0 |
| s06 | iphone14 | 102 / 0 / 0 | 102 / 0 / 0 |
| s06 | pixel7 | 102 / 0 / 0 | 102 / 0 / 0 |
| s07 | iphone14 | 7 / 4 / 0 | 7 / 4 / 0 |
| s07 | pixel7 | 16 / 4 / 0 | 16 / 4 / 0 |
| s071 | iphone14 | 17 / 3 / 0 | 92 / 0 / 0 |
| s071 | pixel7 | 2 / 0 / 0 | 92 / 0 / 0 |
| s12 | iphone14 | 2 / 0 / 0 | 2 / 0 / 0 |
| s12 | pixel7 | 2 / 0 / 0 | 2 / 0 / 0 |
| s13 | iphone14 | 18 / 0 / 0 | 18 / 0 / 0 |
| s13 | pixel7 | 18 / 0 / 0 | 18 / 0 / 0 |
| s14 | iphone14 | 4 / 0 / 0 | 4 / 0 / 0 |
| s14 | pixel7 | 5 / 0 / 0 | 5 / 0 / 0 |
| s20 | data / engine | 3 / 0 / 0 | 3 / 0 / 0 |
| s22 | iphone14 | 15 / 0 / 0 | 15 / 0 / 0 |
| s22 | pixel7 | 15 / 0 / 0 | 15 / 0 / 0 |
| s23 | desktop | 4 / 2 / 0 | 74 / 0 / 0 |
| s23 | ipad-portrait | 4 / 2 / 0 | 74 / 0 / 0 |
| s23 | iphone14 | 4 / 2 / 0 | 74 / 0 / 0 |
| s23 | pixel7 | 4 / 2 / 0 | 74 / 0 / 0 |
| s24 | desktop | 3 / 2 / 0 | 52 / 0 / 0 |
| s24 | ipad-portrait | 3 / 2 / 0 | 50 / 2 / 0 |
| s24 | iphone14 | 3 / 2 / 0 | 28 / 1 / 0 |
| s24 | pixel7 | 3 / 2 / 0 | 52 / 0 / 0 |
| s25 | desktop | 3 / 2 / 0 | 82 / 0 / 0 |
| s25 | ipad-portrait | 3 / 2 / 0 | 82 / 0 / 0 |
| s25 | iphone14 | 3 / 2 / 0 | 82 / 0 / 0 |
| s25 | pixel7 | 3 / 2 / 0 | 82 / 0 / 0 |
| s26 | ipad-portrait | 3 / 1 / 0 | 3 / 1 / 0 |
| s26 | iphone14 | 15 / 2 / 0 | 15 / 2 / 0 |
| s26 | pixel7 | 19 / 2 / 0 | 19 / 2 / 0 |
| s27 | data / engine | 13 / 0 / 0 | 13 / 0 / 0 |
| s28 | data / engine | 1 / 0 / 0 | 1 / 1 / 0 |
| s29 | data / engine | 8 / 0 / 0 | 8 / 0 / 0 |
| s30 | desktop | 0 / 2 / 0 | 78 / 0 / 52 |
| s30 | iphone14 | 0 / 2 / 0 | 78 / 0 / 52 |
| s30 | pixel7 | 0 / 2 / 0 | 78 / 0 / 52 |
| s32 | desktop | 49 / 0 / 0 | 49 / 0 / 0 |
| s32 | pixel7 | 49 / 0 / 0 | 49 / 0 / 0 |

| Total | Before | After |
|---|---:|---:|
| PASS | 652 | 2529 |
| FAIL | 78 | 24 |
| Executed outcomes (PASS + FAIL) | **730** | **2553** |
| SKIP (excluded from executed total) | 0 | 164 |
| Recorded outcomes including SKIP | 730 | 2717 |
| Jobs | 51 | 76 |

The higher count comes from both modes, explicit step-by-step history assertions, and scenarios that now complete instead of aborting. Counts alone do not prove that every old acceptance condition was retained; the skip inventory below records the exceptions explicitly.

| Suite | Device | Default PASS / FAIL / SKIP | ?toc=two PASS / FAIL / SKIP |
|---|---|---:|---:|
| s01 | iphone14 | 59 / 1 / 0 | 63 / 1 / 0 |
| s01 | pixel7 | 59 / 1 / 0 | 63 / 1 / 0 |
| s03 | iphone14 | 52 / 0 / 4 | 57 / 0 / 0 |
| s03 | pixel7 | 53 / 0 / 4 | 58 / 0 / 0 |
| s04 | iphone14 | 50 / 0 / 0 | 55 / 0 / 0 |
| s04 | pixel7 | 50 / 0 / 0 | 55 / 0 / 0 |
| s05 | iphone14 | 17 / 1 / 0 | 29 / 0 / 0 |
| s05 | pixel7 | 29 / 0 / 0 | 29 / 0 / 0 |
| s071 | iphone14 | 44 / 0 / 0 | 48 / 0 / 0 |
| s071 | pixel7 | 44 / 0 / 0 | 48 / 0 / 0 |
| s23 | desktop | 35 / 0 / 0 | 39 / 0 / 0 |
| s23 | ipad-portrait | 35 / 0 / 0 | 39 / 0 / 0 |
| s23 | iphone14 | 35 / 0 / 0 | 39 / 0 / 0 |
| s23 | pixel7 | 35 / 0 / 0 | 39 / 0 / 0 |
| s24 | desktop | 24 / 0 / 0 | 28 / 0 / 0 |
| s24 | ipad-portrait | 22 / 2 / 0 | 28 / 0 / 0 |
| s24 | iphone14 | 0 / 1 / 0 | 28 / 0 / 0 |
| s24 | pixel7 | 24 / 0 / 0 | 28 / 0 / 0 |
| s25 | desktop | 39 / 0 / 0 | 43 / 0 / 0 |
| s25 | ipad-portrait | 39 / 0 / 0 | 43 / 0 / 0 |
| s25 | iphone14 | 39 / 0 / 0 | 43 / 0 / 0 |
| s25 | pixel7 | 39 / 0 / 0 | 43 / 0 / 0 |
| s30 | desktop | 37 / 0 / 26 | 41 / 0 / 26 |
| s30 | iphone14 | 37 / 0 / 26 | 41 / 0 / 26 |
| s30 | pixel7 | 37 / 0 / 26 | 41 / 0 / 26 |

The shared cover → part I → chapter 4 → subsection 4.2 path explicitly asserts **4 Back and 4 Forward presses in default mode; 7 Back and 7 Forward presses in ?toc=two**. Each step also checks URL, highlighted row, open lists, and history pushes; chapter entry checks the top and expanded subsection list, and collapse checks no navigation. Native browser history and the on-screen controls are both exercised. A physical iOS edge-swipe gesture was not performed.

Changes already committed after this full run received focused checks, not another full run:

- s04: restored every original legacy Back checkpoint; 218 PASS, 0 FAIL, 4 additional SKIP across both phones/modes. The four skips are the two highlight-only predecessor IDs below on both phones: `(a) back3 -> chapter 1 lit, collapsed (the 1st-tap step)` and `(a) back4 -> Contents as opened (chapter 1 collapsed, not lit)`. They cannot represent default-mode history entries; they remain asserted in legacy mode. These four are **not included in the requested 164-skip snapshot**.
- s05: closed the menu left by the preceding case before reader-control measurements; 60 PASS, 0 FAIL across both iPhone modes. This resolves the one s05 failure listed in the full-run snapshot.
- s24: made blocked leaf checks report failure explicitly and retained a fresh-context history round trip even after setup fails. This last reporting change has not received another browser run; the quota defect remains open.

## 2. All 164 skip instances

**158 instances cannot mean anything in the model being tested; 6 instances were skipped for convenience.** There are 28 unique original check IDs. No footer check is in this 164-skip list.

The convenience exception is s30 `C2 setup: a second contents row linking to another page`, repeated on three devices in both modes. A second row still exists in a continuous book; retaining this as SKIP was an incomplete rewrite, not a necessary deviation. It remains documented rather than being fixed after the stop instruction.

For the other s30 IDs, the original scenario specifically requires a chapter fetch to remain pending, fail, or be cancelled. Both Contents modes now navigate within the already-rendered continuous book. Immediate navigation, the unchanged 100 ms budget, history, final loading/accessibility cleanup, and absence of old-page flashes have active assertions; the pending-fetch scenarios are kept as explicit obsolete IDs.

### Cannot mean anything: s03 default highlight-only history (8 instances)

| Instance | Suite | Device | Mode | Original check ID | One-line reason |
|---:|---|---|---|---|---|
| 001 | s03 | iphone14 | default | (b) back1b -> chapter, contents as opened | Highlighting alone has no separate default-mode history entry; real-action predecessors are asserted. |
| 002 | s03 | iphone14 | default | (b) back3b -> part + chapter expanded (chapter lit) | Highlighting alone has no separate default-mode history entry; real-action predecessors are asserted. |
| 003 | s03 | iphone14 | default | (b) back4b -> part expanded (part lit) | Highlighting alone has no separate default-mode history entry; real-action predecessors are asserted. |
| 004 | s03 | iphone14 | default | (b) back5b -> contents as opened | Highlighting alone has no separate default-mode history entry; real-action predecessors are asserted. |
| 005 | s03 | pixel7 | default | (b) back1b -> chapter, contents as opened | Highlighting alone has no separate default-mode history entry; real-action predecessors are asserted. |
| 006 | s03 | pixel7 | default | (b) back3b -> part + chapter expanded (chapter lit) | Highlighting alone has no separate default-mode history entry; real-action predecessors are asserted. |
| 007 | s03 | pixel7 | default | (b) back4b -> part expanded (part lit) | Highlighting alone has no separate default-mode history entry; real-action predecessors are asserted. |
| 008 | s03 | pixel7 | default | (b) back5b -> contents as opened | Highlighting alone has no separate default-mode history entry; real-action predecessors are asserted. |

### Cannot mean anything: s30 pending-fetch scenarios (150 instances)

| Instance | Suite | Device | Mode | Original check ID | One-line reason |
|---:|---|---|---|---|---|
| 009 | s30 | desktop | default | 1 at once (≤100 ms) after the 2nd tap: loading bar at the top | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 010 | s30 | desktop | default | 1 at once (≤100 ms) after the 2nd tap: the tapped row says «загружается…» | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 011 | s30 | desktop | default | 2 repeated taps while loading: loading signs stay (navigation not restarted / not broken) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 012 | s30 | desktop | default | B 3 slow load: the old page never flashed; contents closed together with the new page | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 013 | s30 | desktop | default | B 9.5 s into a 12 s load: still the contents with the loading signs (not the old page) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 014 | s30 | desktop | default | C 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 015 | s30 | desktop | default | C repeated tap after 8 s: history +1 only, final URL = the tapped (last) target | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 016 | s30 | desktop | default | C repeated tap after 8 s: no second navigation (no new page-data request, page came with the 1st load) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 017 | s30 | desktop | default | C repeated tap after 8 s: the loading signs stay (nothing restarted, menu not unlocked) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 018 | s30 | desktop | default | C2 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 019 | s30 | desktop | default | C2 another row after 8 s: history +1 only, the LAST choice opened and stays (the replaced load never lands) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 020 | s30 | desktop | default | C2 «Назад» from it: the contents on the page before | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 021 | s30 | desktop | default | D page data failed: the loading state is cleared (page opened another way, or menu not busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 022 | s30 | desktop | default | D2 page data + page load failed: after 25 s the loading state is cleared (no bar, no row sign, nothing busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 023 | s30 | desktop | default | D2 setup: page data and document aborted — the loading signs are shown first | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 024 | s30 | desktop | default | D2 the row says «не удалось загрузить — коснитесь ещё раз» (and the live region) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 025 | s30 | desktop | default | F 3 no flash of the old page after «Назад» (contents stay) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 026 | s30 | desktop | default | F «Назад» while loading: loading signs cleared at once, the step before (contents) shown | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 027 | s30 | desktop | default | F «Назад» while loading: the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 028 | s30 | desktop | default | F2 fast «Назад»→«Вперёд» while loading: contents (the highlighted step), no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 029 | s30 | desktop | default | F2 the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 030 | s30 | desktop | default | F3 the pending load adds no history entry later and nothing reopens | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 031 | s30 | desktop | default | F3 «Вперёд» while loading: the forward page shown, contents closed, no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 032 | s30 | desktop | default | G a11y: «загружается» in a live region (role=status) outside aria-busy, ≤100 ms, present before the tap | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 033 | s30 | desktop | default | setup: the network delay really intercepted the page data (counter > 0) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 034 | s30 | desktop | two | 1 at once (≤100 ms) after the 2nd tap: loading bar at the top | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 035 | s30 | desktop | two | 1 at once (≤100 ms) after the 2nd tap: the tapped row says «загружается…» | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 036 | s30 | desktop | two | 2 repeated taps while loading: loading signs stay (navigation not restarted / not broken) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 037 | s30 | desktop | two | B 3 slow load: the old page never flashed; contents closed together with the new page | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 038 | s30 | desktop | two | B 9.5 s into a 12 s load: still the contents with the loading signs (not the old page) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 039 | s30 | desktop | two | C 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 040 | s30 | desktop | two | C repeated tap after 8 s: history +1 only, final URL = the tapped (last) target | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 041 | s30 | desktop | two | C repeated tap after 8 s: no second navigation (no new page-data request, page came with the 1st load) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 042 | s30 | desktop | two | C repeated tap after 8 s: the loading signs stay (nothing restarted, menu not unlocked) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 043 | s30 | desktop | two | C2 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 044 | s30 | desktop | two | C2 another row after 8 s: history +1 only, the LAST choice opened and stays (the replaced load never lands) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 045 | s30 | desktop | two | C2 «Назад» from it: the contents on the page before | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 046 | s30 | desktop | two | D page data failed: the loading state is cleared (page opened another way, or menu not busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 047 | s30 | desktop | two | D2 page data + page load failed: after 25 s the loading state is cleared (no bar, no row sign, nothing busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 048 | s30 | desktop | two | D2 setup: page data and document aborted — the loading signs are shown first | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 049 | s30 | desktop | two | D2 the row says «не удалось загрузить — коснитесь ещё раз» (and the live region) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 050 | s30 | desktop | two | F 3 no flash of the old page after «Назад» (contents stay) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 051 | s30 | desktop | two | F «Назад» while loading: loading signs cleared at once, the step before (contents) shown | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 052 | s30 | desktop | two | F «Назад» while loading: the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 053 | s30 | desktop | two | F2 fast «Назад»→«Вперёд» while loading: contents (the highlighted step), no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 054 | s30 | desktop | two | F2 the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 055 | s30 | desktop | two | F3 the pending load adds no history entry later and nothing reopens | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 056 | s30 | desktop | two | F3 «Вперёд» while loading: the forward page shown, contents closed, no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 057 | s30 | desktop | two | G a11y: «загружается» in a live region (role=status) outside aria-busy, ≤100 ms, present before the tap | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 058 | s30 | desktop | two | setup: the network delay really intercepted the page data (counter > 0) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 059 | s30 | iphone14 | default | 1 at once (≤100 ms) after the 2nd tap: loading bar at the top | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 060 | s30 | iphone14 | default | 1 at once (≤100 ms) after the 2nd tap: the tapped row says «загружается…» | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 061 | s30 | iphone14 | default | 2 repeated taps while loading: loading signs stay (navigation not restarted / not broken) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 062 | s30 | iphone14 | default | B 3 slow load: the old page never flashed; contents closed together with the new page | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 063 | s30 | iphone14 | default | B 9.5 s into a 12 s load: still the contents with the loading signs (not the old page) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 064 | s30 | iphone14 | default | C 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 065 | s30 | iphone14 | default | C repeated tap after 8 s: history +1 only, final URL = the tapped (last) target | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 066 | s30 | iphone14 | default | C repeated tap after 8 s: no second navigation (no new page-data request, page came with the 1st load) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 067 | s30 | iphone14 | default | C repeated tap after 8 s: the loading signs stay (nothing restarted, menu not unlocked) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 068 | s30 | iphone14 | default | C2 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 069 | s30 | iphone14 | default | C2 another row after 8 s: history +1 only, the LAST choice opened and stays (the replaced load never lands) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 070 | s30 | iphone14 | default | C2 «Назад» from it: the contents on the page before | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 071 | s30 | iphone14 | default | D page data failed: the loading state is cleared (page opened another way, or menu not busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 072 | s30 | iphone14 | default | D2 page data + page load failed: after 25 s the loading state is cleared (no bar, no row sign, nothing busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 073 | s30 | iphone14 | default | D2 setup: page data and document aborted — the loading signs are shown first | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 074 | s30 | iphone14 | default | D2 the row says «не удалось загрузить — коснитесь ещё раз» (and the live region) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 075 | s30 | iphone14 | default | F 3 no flash of the old page after «Назад» (contents stay) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 076 | s30 | iphone14 | default | F «Назад» while loading: loading signs cleared at once, the step before (contents) shown | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 077 | s30 | iphone14 | default | F «Назад» while loading: the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 078 | s30 | iphone14 | default | F2 fast «Назад»→«Вперёд» while loading: contents (the highlighted step), no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 079 | s30 | iphone14 | default | F2 the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 080 | s30 | iphone14 | default | F3 the pending load adds no history entry later and nothing reopens | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 081 | s30 | iphone14 | default | F3 «Вперёд» while loading: the forward page shown, contents closed, no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 082 | s30 | iphone14 | default | G a11y: «загружается» in a live region (role=status) outside aria-busy, ≤100 ms, present before the tap | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 083 | s30 | iphone14 | default | setup: the network delay really intercepted the page data (counter > 0) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 084 | s30 | iphone14 | two | 1 at once (≤100 ms) after the 2nd tap: loading bar at the top | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 085 | s30 | iphone14 | two | 1 at once (≤100 ms) after the 2nd tap: the tapped row says «загружается…» | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 086 | s30 | iphone14 | two | 2 repeated taps while loading: loading signs stay (navigation not restarted / not broken) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 087 | s30 | iphone14 | two | B 3 slow load: the old page never flashed; contents closed together with the new page | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 088 | s30 | iphone14 | two | B 9.5 s into a 12 s load: still the contents with the loading signs (not the old page) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 089 | s30 | iphone14 | two | C 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 090 | s30 | iphone14 | two | C repeated tap after 8 s: history +1 only, final URL = the tapped (last) target | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 091 | s30 | iphone14 | two | C repeated tap after 8 s: no second navigation (no new page-data request, page came with the 1st load) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 092 | s30 | iphone14 | two | C repeated tap after 8 s: the loading signs stay (nothing restarted, menu not unlocked) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 093 | s30 | iphone14 | two | C2 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 094 | s30 | iphone14 | two | C2 another row after 8 s: history +1 only, the LAST choice opened and stays (the replaced load never lands) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 095 | s30 | iphone14 | two | C2 «Назад» from it: the contents on the page before | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 096 | s30 | iphone14 | two | D page data failed: the loading state is cleared (page opened another way, or menu not busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 097 | s30 | iphone14 | two | D2 page data + page load failed: after 25 s the loading state is cleared (no bar, no row sign, nothing busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 098 | s30 | iphone14 | two | D2 setup: page data and document aborted — the loading signs are shown first | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 099 | s30 | iphone14 | two | D2 the row says «не удалось загрузить — коснитесь ещё раз» (and the live region) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 100 | s30 | iphone14 | two | F 3 no flash of the old page after «Назад» (contents stay) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 101 | s30 | iphone14 | two | F «Назад» while loading: loading signs cleared at once, the step before (contents) shown | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 102 | s30 | iphone14 | two | F «Назад» while loading: the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 103 | s30 | iphone14 | two | F2 fast «Назад»→«Вперёд» while loading: contents (the highlighted step), no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 104 | s30 | iphone14 | two | F2 the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 105 | s30 | iphone14 | two | F3 the pending load adds no history entry later and nothing reopens | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 106 | s30 | iphone14 | two | F3 «Вперёд» while loading: the forward page shown, contents closed, no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 107 | s30 | iphone14 | two | G a11y: «загружается» in a live region (role=status) outside aria-busy, ≤100 ms, present before the tap | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 108 | s30 | iphone14 | two | setup: the network delay really intercepted the page data (counter > 0) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 109 | s30 | pixel7 | default | 1 at once (≤100 ms) after the 2nd tap: loading bar at the top | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 110 | s30 | pixel7 | default | 1 at once (≤100 ms) after the 2nd tap: the tapped row says «загружается…» | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 111 | s30 | pixel7 | default | 2 repeated taps while loading: loading signs stay (navigation not restarted / not broken) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 112 | s30 | pixel7 | default | B 3 slow load: the old page never flashed; contents closed together with the new page | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 113 | s30 | pixel7 | default | B 9.5 s into a 12 s load: still the contents with the loading signs (not the old page) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 114 | s30 | pixel7 | default | C 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 115 | s30 | pixel7 | default | C repeated tap after 8 s: history +1 only, final URL = the tapped (last) target | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 116 | s30 | pixel7 | default | C repeated tap after 8 s: no second navigation (no new page-data request, page came with the 1st load) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 117 | s30 | pixel7 | default | C repeated tap after 8 s: the loading signs stay (nothing restarted, menu not unlocked) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 118 | s30 | pixel7 | default | C2 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 119 | s30 | pixel7 | default | C2 another row after 8 s: history +1 only, the LAST choice opened and stays (the replaced load never lands) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 120 | s30 | pixel7 | default | C2 «Назад» from it: the contents on the page before | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 121 | s30 | pixel7 | default | D page data failed: the loading state is cleared (page opened another way, or menu not busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 122 | s30 | pixel7 | default | D2 page data + page load failed: after 25 s the loading state is cleared (no bar, no row sign, nothing busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 123 | s30 | pixel7 | default | D2 setup: page data and document aborted — the loading signs are shown first | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 124 | s30 | pixel7 | default | D2 the row says «не удалось загрузить — коснитесь ещё раз» (and the live region) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 125 | s30 | pixel7 | default | F 3 no flash of the old page after «Назад» (contents stay) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 126 | s30 | pixel7 | default | F «Назад» while loading: loading signs cleared at once, the step before (contents) shown | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 127 | s30 | pixel7 | default | F «Назад» while loading: the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 128 | s30 | pixel7 | default | F2 fast «Назад»→«Вперёд» while loading: contents (the highlighted step), no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 129 | s30 | pixel7 | default | F2 the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 130 | s30 | pixel7 | default | F3 the pending load adds no history entry later and nothing reopens | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 131 | s30 | pixel7 | default | F3 «Вперёд» while loading: the forward page shown, contents closed, no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 132 | s30 | pixel7 | default | G a11y: «загружается» in a live region (role=status) outside aria-busy, ≤100 ms, present before the tap | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 133 | s30 | pixel7 | default | setup: the network delay really intercepted the page data (counter > 0) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 134 | s30 | pixel7 | two | 1 at once (≤100 ms) after the 2nd tap: loading bar at the top | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 135 | s30 | pixel7 | two | 1 at once (≤100 ms) after the 2nd tap: the tapped row says «загружается…» | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 136 | s30 | pixel7 | two | 2 repeated taps while loading: loading signs stay (navigation not restarted / not broken) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 137 | s30 | pixel7 | two | B 3 slow load: the old page never flashed; contents closed together with the new page | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 138 | s30 | pixel7 | two | B 9.5 s into a 12 s load: still the contents with the loading signs (not the old page) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 139 | s30 | pixel7 | two | C 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 140 | s30 | pixel7 | two | C repeated tap after 8 s: history +1 only, final URL = the tapped (last) target | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 141 | s30 | pixel7 | two | C repeated tap after 8 s: no second navigation (no new page-data request, page came with the 1st load) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 142 | s30 | pixel7 | two | C repeated tap after 8 s: the loading signs stay (nothing restarted, menu not unlocked) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 143 | s30 | pixel7 | two | C2 3 the old page never flashed | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 144 | s30 | pixel7 | two | C2 another row after 8 s: history +1 only, the LAST choice opened and stays (the replaced load never lands) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 145 | s30 | pixel7 | two | C2 «Назад» from it: the contents on the page before | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 146 | s30 | pixel7 | two | D page data failed: the loading state is cleared (page opened another way, or menu not busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 147 | s30 | pixel7 | two | D2 page data + page load failed: after 25 s the loading state is cleared (no bar, no row sign, nothing busy) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 148 | s30 | pixel7 | two | D2 setup: page data and document aborted — the loading signs are shown first | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 149 | s30 | pixel7 | two | D2 the row says «не удалось загрузить — коснитесь ещё раз» (and the live region) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 150 | s30 | pixel7 | two | F 3 no flash of the old page after «Назад» (contents stay) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 151 | s30 | pixel7 | two | F «Назад» while loading: loading signs cleared at once, the step before (contents) shown | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 152 | s30 | pixel7 | two | F «Назад» while loading: the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 153 | s30 | pixel7 | two | F2 fast «Назад»→«Вперёд» while loading: contents (the highlighted step), no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 154 | s30 | pixel7 | two | F2 the cancelled page never opens later (URL, history unchanged) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 155 | s30 | pixel7 | two | F3 the pending load adds no history entry later and nothing reopens | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 156 | s30 | pixel7 | two | F3 «Вперёд» while loading: the forward page shown, contents closed, no loading signs, nothing busy | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 157 | s30 | pixel7 | two | G a11y: «загружается» in a live region (role=status) outside aria-busy, ≤100 ms, present before the tap | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |
| 158 | s30 | pixel7 | two | setup: the network delay really intercepted the page data (counter > 0) | The original scenario requires a pending chapter fetch; this target is already rendered in the continuous book in both modes. |

### Convenience: s30 second-row setup still has meaning (6 instances)

| Instance | Suite | Device | Mode | Original check ID | One-line reason |
|---:|---|---|---|---|---|
| 159 | s30 | desktop | default | C2 setup: a second contents row linking to another page | A second distinct Contents row still exists; this setup assertion was not rewritten, so this is a convenience skip. |
| 160 | s30 | desktop | two | C2 setup: a second contents row linking to another page | A second distinct Contents row still exists; this setup assertion was not rewritten, so this is a convenience skip. |
| 161 | s30 | iphone14 | default | C2 setup: a second contents row linking to another page | A second distinct Contents row still exists; this setup assertion was not rewritten, so this is a convenience skip. |
| 162 | s30 | iphone14 | two | C2 setup: a second contents row linking to another page | A second distinct Contents row still exists; this setup assertion was not rewritten, so this is a convenience skip. |
| 163 | s30 | pixel7 | default | C2 setup: a second contents row linking to another page | A second distinct Contents row still exists; this setup assertion was not rewritten, so this is a convenience skip. |
| 164 | s30 | pixel7 | two | C2 setup: a second contents row linking to another page | A second distinct Contents row still exists; this setup assertion was not rewritten, so this is a convenience skip. |

## 3. All 24 failures from the completed full run

The list preserves each red outcome separately. One QA setup failure has since passed a focused rerun; the full-run snapshot was not rewritten to hide it. No further root-cause investigation was started after the stop instruction.

### App defects — 7 red outcomes

| ID | Suite / device / mode | Failure and status |
|---|---|---|
| A01 | s01 / iphone14 / default | First-visit hint is not shown on the deep-loaded chapter; the previously observed continuous-book transition cancels the hint after its seen flag is written; open app defect. |
| A02 | s01 / iphone14 / two | The same first-visit hint assertion fails in legacy mode; open app defect. |
| A03 | s01 / pixel7 / default | The same first-visit hint assertion fails in default mode; open app defect. |
| A04 | s01 / pixel7 / two | The same first-visit hint assertion fails in legacy mode; open app defect. |
| A05 | s24 / iphone14 / default | All-lists setup times out on caturmasya-purusottama-masa after WebKit rejects history writes; the requested chapter navigation did not complete; open app defect. |
| A06 | s24 / ipad-portrait / default | All-lists setup finds only 98 leaves / 94 subsections, below the unchanged ≥100 requirements, after interrupted history/navigation; open app defect. |
| A07 | s24 / ipad-portrait / default | The no-page-errors assertion reports history.replaceState more than 100 times per 10 seconds; open app defect. |

### Out-of-scope pre-existing failures — 15 red outcomes

| ID | Suite / device | Failure and status |
|---|---|---|
| O01 | s07 / pixel7 | `D first tap on Введение only highlights`: asserts the old default two-tap expectation; deliberate interaction deviation, suite outside Phase 2 scope. |
| O02 | s07 / pixel7 | `D second tap Введение expands`: the default second tap now collapses; deliberate interaction deviation, suite outside scope. |
| O03 | s07 / pixel7 | `D second tap on Введение collapses`: the old sequence has already moved to the opposite state; deliberate interaction deviation, suite outside scope. |
| O04 | s07 / pixel7 | `EXCEPTION scroll_into_view_if_needed`: the old two-tap sequence leaves the expected row absent and the suite times out; pre-existing QA sequence failure. |
| O05 | s07 / iphone14 | `D first tap on Введение only highlights`: asserts the old default two-tap expectation; deliberate interaction deviation, suite outside Phase 2 scope. |
| O06 | s07 / iphone14 | `D second tap Введение expands`: the default second tap now collapses; deliberate interaction deviation, suite outside scope. |
| O07 | s07 / iphone14 | `D second tap on Введение collapses`: the old sequence has already moved to the opposite state; deliberate interaction deviation, suite outside scope. |
| O08 | s07 / iphone14 | `EXCEPTION scroll_into_view_if_needed`: the old two-tap sequence leaves the expected row absent and the suite times out; pre-existing QA sequence failure. |
| O09 | s00 / pixel7 | `old /ru/<chapter> redirect (hash kept)`: URL/hash are correct, but the old assertion requires exactly one article h1 in a continuous-book document; pre-existing QA probe defect. |
| O10 | s00 / iphone14 | `old /ru/<chapter> redirect (hash kept)`: URL/hash are correct, but the old assertion requires exactly one article h1 in a continuous-book document; pre-existing QA probe defect. |
| O11 | s26 / pixel7 | `suite crashed`: times out looking for .reader-panel [data-reader-switch=wbw]; pre-existing outside-scope locator/setup failure, underlying cause not further investigated. |
| O12 | s26 / iphone14 | `suite crashed`: times out looking for .reader-panel [data-reader-switch=wbw]; pre-existing outside-scope locator/setup failure, underlying cause not further investigated. |
| O13 | s26 / ipad-portrait | `suite crashed`: times out looking for .reader-panel [data-reader-switch=wbw]; pre-existing outside-scope locator/setup failure, underlying cause not further investigated. |
| O14 | s26 / pixel7 | `14 second tap opens every contents row type`: still asserts the old default interaction; deliberate interaction deviation, suite outside scope. |
| O15 | s26 / iphone14 | `14 second tap opens every contents row type`: still asserts the old default interaction; deliberate interaction deviation, suite outside scope. |

### Environment or test configuration — 2 red outcomes

| ID | Suite / device / mode | Failure and status |
|---|---|---|
| E01 | s28 / data | Importing night_sync aborts with KeyError: anymodel because the translation credential/config section is absent; environment/config failure, newly exposed by correct crash accounting; no external translation request was made. |
| E02 | s05 / iphone14 / default | Reader-control tap timed out because the preceding test left the persisted Contents drawer open; QA fixture configuration error, already corrected and verified by the subsequent 60-PASS focused run. |

## 4. Separate open item: WebKit history quota in s24

Observed in default mode during real Contents clicks on the exported site with the installed WebKit engine: the saved diagnostic records **17 row clicks and 84 replaceState calls within approximately 9.3 seconds from page load**, and both native exceptions: `Attempt to use history.pushState() more than 100 times per 10 seconds` and `Attempt to use history.replaceState() more than 100 times per 10 seconds`. The replace-only diagnostic does not record a complete pushState count, so no exact combined write count is claimed.

The correct main-worship-sixteen-items row was clicked, but navigation failed and the URL stayed at prayers-forgiveness while the drawer closed. A later caturmasya row lookup consequently timed out. The iPad run also failed the unchanged all-rows minimum and recorded the replaceState exception. Legacy mode passed the corresponding s24 jobs.

Rules touched: **UI-10.1** (a row performs its function), **UI-10.2 / UI-9.2** (only real actions push entries and Back restores the same state), and **UI-9.3** (Forward retraces those actions). Highlight updates may replace an existing entry, but redundant persistence from several listeners must not exhaust the browser quota or leave menu and URL inconsistent.

Proposed follow-up, not implemented: consolidate the history-state writer, deduplicate identical replaceState snapshots, and coalesce reading-position persistence while preserving each real navigation/expand/collapse push. Keep the action’s URL/menu/highlight update consistent if a history write fails; do not silently discard an action or hide the defect by slowing the suite. Re-run s24 on WebKit and the explicit Back/Forward checks afterward. The quota issue is intentionally left unfixed at this stop.

## Delivered changes and stop point

All implementation commits affect qa/ only; application source, data/, public/transcripts/, dependencies, and section IDs are unchanged in Phase 2. The shared two-mode helper, explicit history fixture, rewritten scoped suites, rule-registry deviations, and crash/skip accounting are committed. Build and lint are clean. Phase 3 has not started; nothing has been pushed.

Implementation commits: 4cef5e5, 0cf8be7, 32b240b, ab5d19a, 364299a, a738c97, cda8837, d5bf963.

Full-run evidence remains in qa/.results/phase2/before/ and qa/.results/phase2/fast-first/; focused verification and final build/lint logs are in qa/.results/phase2/. These generated artifacts are ignored by Git.
