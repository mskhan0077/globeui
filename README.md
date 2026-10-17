# BlueGrid (globeui)

Interactive globe for exploring Lakshadweep (and other places) plus a hybrid
renewable microgrid planner: click an island's circle and its optimization
window opens over a translucent view of the island.

```
globeui/
├── frontend/                # Globe UI (served by Flask at /)
│   ├── index.html
│   ├── css/
│   │   ├── main.css         # Page, overlay, embedded planner
│   │   ├── map-credits.css  # Imagery credit, shared with the planner pages
│   │   ├── help.css         # "How to use" box (left)
│   │   ├── facts.css        # "Why renewables" comic speech bubbles (right)
│   │   ├── opening.css      # Intro + day/night island shown before the globe
│   │   └── menubar.css      # Menu bar, shared with the planner pages
│   ├── js/
│   │   ├── main.js          # Entry point
│   │   ├── config.js        # Settings: API URLs, imagery, zoom, regions, places
│   │   ├── globe.js         # Cesium viewer setup, zoom limits, auto-rotate
│   │   ├── countries.js     # Clickable countries/regions/places, zoom, Back/Forward, globe:* events
│   │   ├── markers.js       # Named circles for places in assets/data/places/
│   │   ├── overlay.js       # Translucent layer when an island/place is selected
│   │   ├── planner.js       # Embeds the planner page (/planner?embed=1) over a selected island
│   │   ├── help.js          # "How to use" box: folded by default on phones
│   │   ├── facts.js         # Speech bubbles coming out of the Earth: follow the globe, tails drawn to its edge (FACTS in config.js)
│   │   └── story/           # Opening before the globe (from BlenderEarth, Three.js):
│   │       ├── opening.js       #   intro → day/night island → globe
│   │       ├── island-scene.js  #   renderer, day/night split, draggable divider target
│   │       └── island-world.js  #   island + energy kit (converted from buildIslandWorld.ts)
│   └── assets/
│       ├── data/            # GeoJSON click areas + places/*.json (circled places)
│       └── models/          # blue-grid-energy-kit.glb (Blender energy kit for the island)
├── backend/                 # Flask app + optimization engine (uv project)
│   ├── run.py               # Entry point
│   ├── app/
│   │   ├── __init__.py      # App factory: loads data/processed, registers routes
│   │   ├── config.py        # Planner defaults (slider bounds, weights, LPSP target)
│   │   ├── data_loader.py
│   │   ├── engine/          # generation, BESS dispatch, economics, carbon, scoring, LP + grid optimizer
│   │   ├── references.py    # Independent sources for site facts: /references page + /api/references, cited author–date like (IRENA, 2024)
│   │   ├── reports/         # PDF report: pdf.py (data → WeasyPrint), charts.py (static SVG charts)
│   │   ├── routes/          # api.py (/api), export.py (/export), main.py (/planner), frontend.py (/)
│   │   ├── templates/       # Planner page (/planner, also embedded in the globe), /about, /references, report/report.html (PDF)
│   │   └── static/
│   │       ├── css/
│   │       │   ├── base.css     # Layout and components
│   │       │   ├── glass.css    # Dark glass theme (standalone + embedded)
│   │       │   ├── busy.css     # "Optimizing…" loading screen
│   │       │   ├── info.css     # (i) buttons and info box
│   │       │   ├── page.css     # Standalone page: globe backdrop, menu-bar spacing
│   │       │   └── report.css   # PDF report (print layout, light theme)
│   │       ├── fonts/           # Inter (OFL licence), embedded in the PDF
│   │       └── js/
│   │           ├── planner.js       # Planner logic: sliders, API calls, KPIs, tables, exports
│   │           ├── theme.js         # Plotly glass theme (BlueGrid.plot)
│   │           ├── info.js          # (i) buttons: technology parameters (/api/tech) and explanations
│   │           ├── info-content.js  # Text for the chart and KPI (i) boxes
│   │           ├── backdrop.js      # Standalone page: live globe behind the panels, flies to the picked place
│   │           └── embed-bridge.js  # Embedded: tells the globe which island was picked
│   └── tests/
├── data/
│   ├── source/              # BlueGrid Lakshadweep dataset workbook
│   └── processed/           # CSV/JSON the backend loads (+ hourly/ 8760 files per island)
├── scripts/
│   ├── build_places.py      # Workbook → frontend/assets/data/places/lakshadweep.json
│   ├── extract_csvs.py      # Workbook → data/processed/
│   ├── fetch_real_data.py   # Open-Meteo hourly data → data/processed/hourly/
│   └── fetch_extra_places.py # Non-workbook places (data/source/extra_places.csv, e.g. Brest) → data/processed/
└── docs/                    # LP formulation and core formulas
```

## Run

```bash
cd backend
uv sync
uv run flask --app run:app run
```

Open http://localhost:5000. That serves the globe at `/`, the API at `/api`,
CSV/PDF exports at `/export`, and the classic planner page at `/planner`.

Tests: `cd backend && uv run pytest`.

## Using the planner

Click an island's circle (inside an atoll, click the atoll first). Once the
camera arrives, the BlueGrid planner opens over a translucent view of the island,
with that island preselected and a 1000 kW load. Use **Evaluate**, **Find optimal
mix** (LP + grid search, ~30–60 s), **Compare all islands**, Reset, and CSV/PDF
export as on the standalone page. Close with × or the browser's Back button.

The planner needs the Flask server: open the app at http://localhost:5000, not
from a static file server.

Places without data show a message instead. Places outside the workbook (e.g.
Brest) are listed in `data/source/extra_places.csv`; their hourly data is
`data/processed/hourly/<name>.csv` (Brest's comes from the BoobWorld team's
`brest_france.csv`). Run `(cd backend && uv run python ../scripts/fetch_extra_places.py)`
to rebuild their monthly rows (add `--fetch` to re-download from Open-Meteo); they
then appear in the planner's island dropdown. Costs and finance parameters are the
dataset's Lakshadweep/INR values.

## Data

> **Cost data matches BoobWorld.** `data/processed/tech_params.csv`, `finance_params.json`
> and `turbine_curve.csv` are copied from the team's BoobWorld repo so both apps give the
> same results. Running `extract_csvs.py` regenerates them from the workbook in
> `data/source/`, whose newer costs BoobWorld doesn't use yet. Only do that once the team
> has regenerated theirs.

After changing the workbook in `data/source/`, regenerate what depends on it
(from the repo root):

```bash
uv run scripts/build_places.py                              # globe circles
(cd backend && uv run python ../scripts/extract_csvs.py)    # backend CSVs
(cd backend && uv run python ../scripts/fetch_real_data.py) # hourly data (network)
```

## Circled places

Each file in `frontend/assets/data/places/` lists places drawn as a named circle:

```json
{ "id": "brest", "name": "Brest", "lat": 48.39, "lng": -4.486, "parent": "FRA", "zoomHeight": 25000 }
```

`parent` is the country code, region or place it belongs to; the circle shows while
viewing that parent. `zoomHeight` (metres) is optional. For the planner to work for a
place, its `name` must match an island name in the dataset.

- `lakshadweep.json` is generated from the workbook's *Islands* sheet; don't edit it by hand.
- `other.json` is hand-written: add any other place there.
- A new places file must also be listed in `PLACE_FILES` in `frontend/js/config.js`.
# globeui
