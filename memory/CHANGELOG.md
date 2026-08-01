# TipJar Global — CHANGELOG

## 2026-08-01 — Codemining: glatter Sieg-Code → Draw No Bet (DNB)
- **New owner rule (Cobresal/Liberec):** A plain 1X2 WIN code no longer becomes "Underdog +1.5 / verzichten".
  - **Fall A** — code backs a team to WIN (S1/S2/Heimsieg/Auswärtssieg/"gewinnt") → OUR pick = `<that team> Draw No Bet (DNB)` (they won't lose; a draw returns the stake). Pattern `straightwin_dnb`.
  - **Fall B** — pure Double Chance (1X / X2 / Doppelte Chance / "gewinnt nicht") → **NO BET** (gegen X2 zu gehen ist Risiko). Unchanged, via `_code_read_interpret` (e)-branch.
- **Grading (`_grade_code_our_market`):** DNB → team wins = `won`, draw = `push` (Einsatz zurück), team loses = `lost`. `settle_code_reads` now treats `push` as a terminal outcome.
- **Frontend (`CodeReading.jsx`):** new `push` verdict chip "EINSATZ ZURÜCK" (sky/blue); Check icon for CORRECT/push, X only for UNCORRECT; DE/EN/EL example texts updated to DNB; fixed duplicate closing lines that broke the ESLint build.
- The **7 finished (Beendet)** code_reads from yesterday were **NOT touched** (they have `outcome` set → skipped by settler & sweep). No demo data is seeded into the active feed.
- Files: `/app/backend/server.py` (`_code_straightwin_decision`, `_grade_code_our_market`, `settle_code_reads`), `/app/frontend/src/components/CodeReading.jsx`.
- Tested: Python unit tests (interpret + grading won/push/lost) all pass; DC→NoBet confirmed; frontend compiles & Codemining page renders.
