# 📦 Warehouse Product Verification System (PVS)

A full-stack application for bulk product data ingestion, on-floor product validation, and quality assurance reporting for warehouse operations.

---

## 🏗 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                  │
│  ┌────────────────┐     /api/*      ┌──────────────────────┐    │
│  │   Frontend     │ ─────proxy────► │   Backend (FastAPI)  │    │
│  │  Nginx:Alpine  │                 │   Python 3.12 + uv   │    │
│  │   Port 3000    │                 │      Port 8000       │    │
│  └────────────────┘                 └──────────┬───────────┘    │
│                                                │ SQLAlchemy     │
│  ┌────────────────┐                 ┌──────────▼───────────┐    │
│  │   pgAdmin 4    │                 │   PostgreSQL 17       │    │
│  │   Port 5050    │                 │      Port 5432        │    │
│  └────────────────┘                 └──────────────────────┘    │
│                                                                  │
│         Shared Docker Volume: validation_uploads                 │
│         (backend writes images → frontend serves them)           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🗂 Project Structure

```
flipkart-assignment/
├── frontend/                   # Static frontend (HTML/CSS/JS)
│   ├── index.html              # Landing / navigation hub
│   ├── pages/
│   │   ├── ingestion.html      # Bulk CSV ingestion screen
│   │   ├── operator.html       # On-floor product validation (mobile-first)
│   │   └── report.html         # QA verification reporting
│   ├── assets/
│   │   ├── css/style.css       # Shared design system
│   │   └── js/api.js           # Shared fetch wrapper
│   ├── nginx/
│   │   └── nginx.conf          # Nginx reverse proxy config
│   └── Dockerfile              # Nginx:Alpine image
│
├── routes/
│   └── api.py                  # All FastAPI endpoints
├── models/
│   ├── product.py              # Product ORM model
│   ├── verification_log.py     # VerificationLog ORM model
│   └── user.py                 # User ORM model
├── services/
│   └── api.py                  # Business logic (CSV ingestion)
├── database/
│   ├── db.py                   # SQLAlchemy engine + Base
│   ├── startup.py              # DB init + seeding
│   └── seed.py                 # User seeding logic
├── main.py                     # FastAPI app entry point
├── Dockerfile                  # Backend Python image
├── docker-compose.yml          # All services orchestration
├── pyproject.toml              # Python dependencies (uv)
└── .env.docker                 # Environment variables for Docker
```

---

## ⚡ Quick Start with Docker

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)

### 1. Clone the repository
```bash
git clone <repo-url>
cd flipkart-assignment
```

### 2. Build and start all services
```bash
docker compose up --build
```

This starts four services:
| Service | URL | Purpose |
|---|---|---|
| **Frontend** | http://localhost:3000 | Web UI (Nginx) |
| **Backend API** | http://localhost:8000 | FastAPI + Swagger docs |
| **PostgreSQL** | localhost:5432 | Database |
| **pgAdmin** | http://localhost:5050 | DB admin UI |

### 3. Open the application
Navigate to **http://localhost:3000** in your browser.

> The database is automatically initialized and seeded with test users on first startup.

### 4. Stop the application
```bash
docker compose down
```

To also remove the database volume (full reset):
```bash
docker compose down -v
```

---

## 👥 Seeded Users

The system is pre-seeded with the following users:

| Username | Role | Screen |
|---|---|---|
| `manager_1`, `manager_2` | `warehouse-manager` | Ingestion |
| `operator_1` … `operator_6` | `warehouse-operator` | Validation |
| `qa_1`, `qa_2` | `quality-assurance-manager` | Reports |

---

## 📱 Screens & Features

### 1. Bulk Ingestion (`/pages/ingestion.html`)
- **Role**: Warehouse Manager
- Drag-and-drop or click to upload a CSV file
- Configurable batch size (100–10,000 rows per DB commit)
- **Live progress panel**: polls the backend every 1.5 seconds to show:
  - Job status: Queued → Running → Succeeded / Failed
  - Rows ingested so far
  - Total rows in the table
  - Scrollable timestamped log stream

**Expected CSV format:**
```csv
WID,EAN,Manufacturing_Date,Expiry_Date
WID-001,4006381333931,2024-01-15,2026-01-15
WID-002,4006381333931,2024-02-10,2026-02-10
```

### 2. Product Validation (`/pages/operator.html`)
- **Role**: Warehouse Operator
- **Mobile-first**, touch-optimized layout
- WID text field (compatible with USB/Bluetooth barcode scanners — acts as keyboard)
- Native camera capture via `<input capture="environment">` (works on iOS/Android)
- Submits WID + image → displays EAN, Manufacturing Date, Expiry Date
- Color-coded expiry status: green (valid) / amber (≤30 days) / red (expired)
- "Validate Another" button resets form for rapid sequential scanning

### 3. Verification Report (`/pages/report.html`)
- **Role**: Quality Assurance Manager
- Native date range picker with **quick shortcuts** (Last 7/30/90 days, This month)
- Paginated table (25 rows/page) with scroll
- **Download CSV** button — generates the full report as a `.csv` file in-browser (no extra endpoint needed)
- Shows: Log ID, WID, Operator, Verified At, Image link

---

## 🔌 API Reference

All API endpoints are prefixed with `/api`. Full interactive docs available at **http://localhost:8000/docs**.

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `POST` | `/api/ingest` | warehouse-manager | Upload CSV; returns `task_id` |
| `GET` | `/api/ingest/status/{task_id}` | warehouse-manager | Poll ingestion job progress |
| `POST` | `/api/products/validate` | warehouse-operator | Validate product by WID + capture image |
| `GET` | `/api/reports/verification` | quality-assurance-manager | Date-range verification report |

---

## 🧱 Technical Stack

| Layer | Technology | Reason |
|---|---|---|
| **Frontend** | HTML5 + Vanilla CSS + Vanilla JS | Zero build tools, instant load, maximum compatibility |
| **CSS Framework** | Custom design system (dark theme, CSS variables) | Full visual control, no framework constraints |
| **Web Server** | Nginx Alpine | Battle-tested static server + reverse proxy in one |
| **Backend** | FastAPI (Python 3.12) | Async-capable, auto Swagger docs, type-safe |
| **Package Manager** | uv | 10–100× faster than pip, lockfile-based reproducibility |
| **ORM** | SQLAlchemy 2.x | Mature, flexible, supports bulk operations |
| **Database** | PostgreSQL 17 | ACID compliance, scalable, strong JSON/index support |
| **Containerization** | Docker Compose | Single-command local setup, environment parity |

---

## 🏗 Architectural Decisions

### Scalability: Chunked CSV Ingestion with Background Tasks
Large CSV files (millions of rows) are processed in a **FastAPI BackgroundTask** that runs in a separate thread, so the HTTP response returns immediately with a `task_id`. The frontend polls `GET /api/ingest/status/{task_id}` every 1.5 seconds.

Within the background job, rows are inserted in configurable **batches** (default: 1,000). Each batch is committed independently, meaning:
- Memory usage is bounded regardless of file size
- Progress is visible incrementally
- A failure mid-file doesn't roll back already-committed data

### Data Integrity: WID as Primary Key
The `wid` column is the primary key of the `products` table. PostgreSQL enforces uniqueness at the DB level — no application-layer checks needed. Duplicate WIDs in a CSV will trigger a constraint error that is caught and reported to the job status.

### Performance: Database Indexing
- `products.ean` — indexed for fast lookup by EAN
- `verification_logs.verified_at` — indexed for fast date-range queries
- `verification_logs.id` — primary key (auto-indexed)

### Usability: Nginx Reverse Proxy
The frontend and backend are separate containers but exposed through a single Nginx server on port 3000. Requests to `/api/*` are proxied to the backend. This means:
- No CORS issues (same origin)
- Frontend JS never needs to know the backend's URL
- Swappable backends without frontend changes

### Image Storage: Shared Named Volume
Product validation images are saved by the backend to `/app/data/uploads/validations`. A shared Docker named volume (`validation_uploads`) mounts this same directory in the Nginx container at `/app/uploads`, allowing Nginx to serve images directly at `/uploads/<filename>` without going through the FastAPI backend.

---

## 🛠 Local Development (without Docker)

### Backend
```bash
# Install uv
pip install uv

# Create venv and install dependencies
uv sync

# Start PostgreSQL (or update .env with your DB URL)
# Edit .env: DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/flipkart

# Run the backend
uv run uvicorn main:app --reload --port 8000
```

### Frontend
The frontend is plain HTML/JS — just open any page in a browser. For API calls to work during local dev, either:
- Run the backend locally (above) and open `frontend/pages/ingestion.html` directly in a browser (some API calls may face CORS; use the Docker setup for full integration)
- Or use the Docker setup which routes everything through Nginx

---

## 🗄 Database Admin (pgAdmin)

Access pgAdmin at **http://localhost:5050**
- Email: `admin@admin.com`
- Password: `admin`

Add a new server with:
- Host: `postgres`
- Port: `5432`
- Username: `postgres`
- Password: `postgres`
- Database: `flipkart`

---

## 📋 DB Backup & Restore

**Backup:**
```bash
docker exec flipkart-postgres pg_dump -U postgres -d flipkart -F c > flipkart_backup.backup
```

**Restore:**
```bash
docker cp flipkart_backup.backup flipkart-postgres:/tmp/flipkart.backup
docker exec flipkart-postgres pg_restore -U postgres -d flipkart /tmp/flipkart.backup
```
