# TransferAtlas

A web-based soccer transfer intelligence tool that visualizes how money flows through club football. This is a project I've wanted to build for a long time, following soccer has been a passion of mine since the 2006 World Cup, and I wanted a way to actually *see* the money move between countries and clubs across transfer windows.

![TransferAtlas map view showing transfer flows between European countries](screenshots/MapViewWithDetails.png)

## What it does

TransferAtlas ingests real transfer data from [Transfermarkt Datasets](https://github.com/dcaribou/transfermarkt-datasets) and presents it through three views:

**Map View** — An interactive geographic map where arc lines between countries represent transfer spending. Arc thickness encodes money volume, and country nodes are colored by net spend position (red for net spenders, green for net receivers). Click a country or arc to open a detail panel showing top buying/selling clubs and a sortable transfer table. Arc clicks show a country-pair breakdown with a direction toggle.

**Network Graph View** — A force-directed graph centered on a single club, showing its transfer relationships. Country nodes radiate outward and can be expanded to reveal individual club-to-club connections. Click any node to open a detail sidebar; click the "View network" button to re-center on a different club.

![Network graph centered on Benfica with expanded country nodes showing individual clubs](screenshots/NetworkViewExpanded.png)

**Player View** — Search for any player to see their career path as a visual timeline, market value history as a chart with transfer fee markers, and full transfer history table.

![Player view showing Kevin De Bruyne's career path, market value chart, and transfer history](screenshots/PlayerView.png)

All views share global filters for time range, transfer type, fee range, player position, player age, and country.

## Tech Stack

- **Frontend:** React 19, Vite, TypeScript, Tailwind CSS, deck.gl, MapLibre GL, react-force-graph-2d, Recharts
- **Backend:** Python 3.13, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL 15
- **Infrastructure:** Docker Compose

## Getting Started

### Prerequisites

- **Docker Desktop** — runs the database, API, and web containers
- **Python 3.13+** — `python3.13` must be on your PATH (needed for the local venv that runs migrations and the data pipeline)
- **[just](https://github.com/casey/just)** — recommended task runner (`brew install just`). All commands below use it; a manual fallback is in the last subsection.
- **Node.js 20+** — only required if you want to run the frontend outside Docker

### 1. Clone and configure

```bash
git clone https://github.com/sam-lohnes/transfer-atlas.git
cd transfer-atlas
cp .env.example .env
```

Open `.env` and set a value for `POSTGRES_PASSWORD`. Update `DATABASE_URL` to use the same password so the in-container API can connect.

### 2. Start the Docker services

```bash
docker compose up --build -d
docker compose ps
```

Wait until the `db` service reports `healthy` before moving on — host-side commands in the next step connect to Postgres on `localhost:5432` and will fail if it isn't up yet.

### 3. Install Python deps and run migrations

```bash
cd api
just setup                  # creates .venv, installs requirements.txt
source .venv/bin/activate
just migrate                # alembic upgrade head
```

`just` reads credentials from the repo-root `.env` automatically.

### 4. Load the data

```bash
just pipeline               # ~60MB download, ~1 minute on a warm connection
```

This downloads CSVs from Transfermarkt Datasets and populates every table. You only need to re-run it when upstream data changes (the pipeline exits early otherwise — use `just pipeline-force` to override).

### 5. Open the app

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

If the map view loads with country arcs, you're done.

### Stopping

```bash
docker compose down         # stop containers, keep the database volume
docker compose down -v      # …and wipe the database (forces a full re-ingest next time)
```

### Manual commands (without `just`)

If you'd rather not install `just`, the same steps as raw commands — substitute `<password>` with the `POSTGRES_PASSWORD` value you set in `.env`:

```bash
cd api
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

DATABASE_URL=postgresql://transfer_atlas:<password>@localhost:5432/transfer_atlas alembic upgrade head
DATABASE_URL=postgresql://transfer_atlas:<password>@localhost:5432/transfer_atlas python -m pipeline.run
```

## Testing

The backend has a pytest suite covering the ingestion pipeline — per-function unit tests, schema validation, change detection, and end-to-end tests that exercise the full ingest chain against fixture CSVs. Tests run against an in-memory SQLite database, so no Docker or external services are required.

```bash
cd api

# Run the full suite (~0.5s)
python3 -m pytest tests/ -v

# Run only the end-to-end pipeline tests
python3 -m pytest tests/test_ingest.py::TestFullPipelineE2E -v

# Run a single test
python3 -m pytest tests/test_ingest.py::TestFullPipelineE2E::test_rerun_is_idempotent -v
```

The aggregation rebuild (`rebuild_country_flows`, `rebuild_club_summaries`) uses PostgreSQL-specific SQL that SQLite can't execute, so it's validated through live pipeline runs rather than unit tests.

## Data

TransferAtlas tracks transfers across 15 leagues in 12 countries:

- **England:** Premier League, Championship
- **Spain:** La Liga, Segunda División
- **Germany:** Bundesliga, 2. Bundesliga
- **Italy:** Serie A
- **France:** Ligue 1
- **Portugal:** Primeira Liga
- **Netherlands:** Eredivisie
- **Belgium:** Pro League
- **Turkey:** Süper Lig
- **Scotland:** Premiership
- **Argentina:** Primera División
- **Brazil:** Série A

The pipeline is designed to run monthly to pick up new transfer data. All monetary values are stored in EUR cents to avoid floating-point issues.

## Data Source & Attribution

All transfer data, player information, club data, and market valuations shown in TransferAtlas originate from [**Transfermarkt**](https://www.transfermarkt.com), the authoritative source for football transfer and market value data. I consume this data via the [Transfermarkt Datasets](https://github.com/dcaribou/transfermarkt-datasets) project by [@dcaribou](https://github.com/dcaribou), which publishes periodic snapshots as CSVs.

TransferAtlas is a **non-commercial personal project** built for learning and as a showcase of data pipeline design and building responsive user interfaces backed by larger datasets. I don't claim ownership of any data shown here — Transfermarkt remains the authoritative source, and player/club references throughout the app deep-link back to Transfermarkt's website.

If you represent Transfermarkt and have concerns about this project, please open a GitHub issue and I'll respond promptly.

