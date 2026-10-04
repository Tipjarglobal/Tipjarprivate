# BACKEND MAP — TipJar GLOBAL · 5-Schalen-Fundament

Stand: 2026-06. Backend von 23 Root-`.py` → **1 Root (`server.py`) + 4 Pakete + 1 legacy**. Import-Graph-geprüft, keine toten Imports, `uvicorn server:app` startet sauber, `/api/` = 200.

## Struktur
| Ort | Dateien | Inhalt |
|-----|---------|--------|
| **Root** | `server.py` (einziger Entry) + requirements.txt, Dockerfile, .env, assets/ | FastAPI, importiert NUR aus core/scrapers/render |
| **core/** | engine (war core.py), models, betting, learning, odds, tasks, settlement, glitch | gesamte Tipp-/Rechen-Logik |
| **scrapers/** | autopost, collector, forebet, statarea, predictz, footballpredictions, emptips_watch, match_stats | aktive Scraper |
| **render/** | ticket (war ticket_render), poster (war poster_tz) | was Frontend sieht (Ticket-Bilder) |
| **legacy_scrapers/** | dedupe, recategorize, seed_picks, seed_reports + seed_assets/ + tests/ | TOT (von niemandem importiert), bleibt aufbewahrt |

## Wichtige Fixes beim Move (sonst Crash)
- `core/engine.py`: `ROOT_DIR = Path(__file__).parent.parent` (lädt `.env` aus backend/ — vorher .parent → .env nicht gefunden → Crash)
- `render/ticket.py`: `FONT_DIR = .../"..","assets","fonts"` (ein Ordner hoch, da assets/ im Root bleibt)
- Alle Cross-Imports auf absolute Paket-Pfade: `from core.engine import …`, `from core.odds import …`, `from render.poster import …`, `from scrapers.forebet import …`

## Regeln (wie Frontend-Raster)
1. Kein neues `.py` im Root ausser server.py/requirements/Dockerfile.
2. `server.py` importiert NIE aus `legacy_scrapers/`. Wenn ein Modul von niemandem importiert wird → legacy.
3. `emergentintegrations` ist die **pip-Library**, KEIN lokaler Ordner — nicht anfassen.
4. Nach jedem Move: `python -m py_compile server.py core/*.py scrapers/*.py render/*.py` muss OK sein.

## Import-Graph (zum Zeitpunkt des Umbaus, TOT = safe legacy)
TOT: dedupe_hq_tips, recategorize_tips, seed_curated_picks, seed_smart_reports.
AKTIV (alle anderen) — forebet/statarea/predictz/footballpredictions/emptips_watch/match_stats sind AKTIV (Ticket hielt sie fälschlich für tot).
