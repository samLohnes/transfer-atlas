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

- Docker Desktop
- Node.js 20+
- Python 3.13+

### Setup

```bash
# Clone the repo
git clone https://github.com/sam-lohnes/transfer-atlas.git
cd transfer-atlas

# Copy environment config
cp .env.example .env

# Start all services
docker compose up --build -d

# Run database migrations
cd api
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql://transfer_atlas:your_password_here@localhost:5432/transfer_atlas alembic upgrade head

# Run the data pipeline (downloads ~60MB of CSV data, can take a few minues on initial setup)
DATABASE_URL=postgresql://transfer_atlas:your_password_here@localhost:5432/transfer_atlas python -m pipeline.run
```

The app will be available at:
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

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

