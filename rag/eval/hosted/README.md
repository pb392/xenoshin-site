Hosted evaluation runs are committed here by the "Hosted check" workflow, one folder per run (UTC time), so no run overwrites another.

| Run | App commit | Questions | Links | Keyboard / phone | Notes |
|---|---|---|---|---|---|
| [2026-11-19](2026-11-19/results.md) | 84876ad | 9/9 | (not run yet) | (not run yet) | Build stage |
| [2026-11-23T1646Z](2026-11-23T1646Z/results.md) | d6ae784 | 17/17 | (not run yet) | (not run yet) | First run with the Nov 21 Premier and R1-R8 |
| [2026-11-23T1736Z](2026-11-23T1736Z/results.md) | d6ae784 | 16/17 | [19 links, 0 broken](2026-11-23T1736Z/links.md) | [1 page failed](2026-11-23T1736Z/ui.md) | Same app as the previous run. R1 ("Who won...?") was refused this time: no player names are stored, and the model sometimes treated that as missing evidence. Fixed with prompt rule 8. The phone-width failure was already fixed in CI but not yet deployed. |
| [2026-11-23T1851Z](2026-11-23T1851Z/results.md) | fa65c38 | 16/17 | [23 links, 0 broken](2026-11-23T1851Z/links.md) | [10/10 pages ok](2026-11-23T1851Z/ui.md) | Q1 got HTTP 502: the server's first automatic update after the deploy-script fix restarted the app during the run (import run 4 at 18:52:15Z). R1 answered but ended with a stray "[8]" (the model cited prompt rule 8); fixed in d196dc7. |
| **[2026-11-23T1904Z](2026-11-23T1904Z/results.md)** | **d196dc7** | **17/17** | [23 links, 0 broken](2026-11-23T1904Z/links.md) | [10/10 pages ok](2026-11-23T1904Z/ui.md) | **Release v1.0.0.** [Workflow run](https://github.com/pb392/xenoshin-site/actions/runs/45245096132) |
