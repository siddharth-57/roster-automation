# Roster Automation

A full-stack roster management application for creating, storing, uploading, and downloading monthly employee rosters.

The application provides:

- Monthly roster generation
- Employee/member management
- Employee activation/deactivation
- Shift/date requirement validation
- Roster persistence in PostgreSQL
- Excel roster upload
- Excel roster download
- Existing-roster overwrite support
- FastAPI Swagger/OpenAPI documentation
- Automated backend tests
- Docker Compose-based local development

---

## Tech Stack

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- PostgreSQL 17
- Psycopg
- Alembic
- Pytest

### Frontend

- React
- Vite
- Axios
- Material UI (MUI)
- Lucide React

### Infrastructure

- Docker
- Docker Compose

---

## Project Structure

```text
Roster Automation/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── Dockerfile
│
└── docker-compose.yml
```

---

# Getting Started

## Prerequisites

Install the following on your machine:

- Git
- Docker Desktop
- Docker Compose

Docker Desktop includes Docker Compose.

You do not need to install Python, Node.js, or PostgreSQL locally when running the project through Docker Compose.

---

# 1. Clone the Repository

Clone the repository:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
```

Enter the project directory:

```bash
cd "Roster Automation"
```

If your repository uses a different directory name, `cd` into that directory instead.

---

# 2. Start the Application

Build and start all services:

```bash
docker compose up -d --build
```

The project contains three services:

```text
PostgreSQL
    ↓
Backend (FastAPI)
    ↓
Frontend (React/Vite)
```

The current Docker Compose configuration exposes:

| Service | URL / Port |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

The PostgreSQL database is named:

```text
roster_db
```

The configured PostgreSQL credentials are:

```text
Username: postgres
Password: password
Database: roster_db
```

The backend connects to PostgreSQL through the Docker service name:

```text
postgresql+psycopg://postgres:password@postgres:5432/roster_db
```

---

# 3. Check Running Containers

Run:

```bash
docker compose ps
```

You should see the three services running:

```text
roster-postgres
roster-backend
roster-frontend
```

You can also use:

```bash
docker ps
```

---

# 4. Run Database Migrations

After starting the containers, apply the Alembic migrations:

```bash
docker compose exec backend alembic upgrade head
```

This creates/updates the PostgreSQL tables according to the project's migration history.

Run this when setting up the project for the first time or whenever new migrations have been added.

---

# 5. Open the Application

Open the frontend in your browser:

```text
http://localhost:5173
```

The backend API is available at:

```text
http://localhost:8000
```

FastAPI Swagger UI:

```text
http://localhost:8000/docs
```

FastAPI OpenAPI JSON:

```text
http://localhost:8000/openapi.json
```

---

# 6. Verify the Backend Health

You can test the backend health endpoint with:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

---

# PostgreSQL

## Connect to PostgreSQL

To open a PostgreSQL shell inside the running PostgreSQL container:

```bash
docker compose exec postgres psql -U postgres -d roster_db
```

You should then see a PostgreSQL prompt:

```text
roster_db=#
```

Useful commands:

```sql
\dt
```

List tables.

```sql
\d team_members
```

Describe the `team_members` table.

```sql
\d rosters
```

Describe the `rosters` table.

```sql
\d roster_assignments
```

Describe the `roster_assignments` table.

Exit PostgreSQL:

```sql
\q
```

---

# Database Persistence

PostgreSQL uses a Docker volume:

```text
postgres_data
```

This means that stopping/restarting the containers does not normally delete the database.

To stop the application without removing the database:

```bash
docker compose down
```

Start it again:

```bash
docker compose up -d
```

## WARNING: Removing the Database Volume

This command removes the PostgreSQL container **and its persisted database volume**:

```bash
docker compose down -v
```

This will delete the database data stored in the Docker volume.

Only use it when you intentionally want to reset the database.

After doing so, start the application again:

```bash
docker compose up -d --build
```

and run:

```bash
docker compose exec backend alembic upgrade head
```

---

# Running Tests

Backend tests can be run inside the backend container:

```bash
docker compose exec backend pytest -v
```

To run a specific test file:

```bash
docker compose exec backend pytest backend/tests/test_c_scheduler.py -v
```

If your tests are mounted at `/app/tests`, use the path appropriate to the current repository structure.

The project's backend test suite has been used to verify functionality such as:

- Health endpoint
- Roster creation
- Idempotency
- Metrics
- Transaction/roster-related behavior

---

# Frontend Development

The frontend runs through Vite inside Docker.

The Docker Compose configuration mounts the frontend source into the container and keeps `node_modules` inside the container.

If you install a new frontend dependency, install it in the frontend container:

```bash
docker compose exec frontend npm install <package-name>
```

For example:

```bash
docker compose exec frontend npm install lucide-react
```

After dependency changes, restart the frontend if necessary:

```bash
docker compose restart frontend
```

For a complete frontend rebuild:

```bash
docker compose up -d --build frontend
```

---

# Backend Development

Backend source code is mounted into the backend container.

If Python dependencies are added or changed, update:

```text
backend/requirements.txt
```

Then rebuild the backend image:

```bash
docker compose up -d --build backend
```

---

# Alembic Migrations

The project uses Alembic for database schema migrations.

Apply all pending migrations:

```bash
docker compose exec backend alembic upgrade head
```

Check the current migration:

```bash
docker compose exec backend alembic current
```

Show migration history:

```bash
docker compose exec backend alembic history
```

When creating a new migration after changing SQLAlchemy models:

```bash
docker compose exec backend alembic revision --autogenerate -m "describe your change"
```

Then apply it:

```bash
docker compose exec backend alembic upgrade head
```

Review autogenerated migrations before applying them.

---

# Application Features

## Create Monthly Roster

The Create Monthly Roster section allows the user to specify:

- Month
- Year
- Group number
- Public holidays
- Member-specific shift requirements

The supported shifts are:

```text
A
B
C
G
L
W
```

Dates are entered as comma-separated values, for example:

```text
2,5,8
```

The frontend validates:

- Invalid dates
- Dates outside the selected month
- Duplicate dates
- Conflicting shift requirements for the same employee

The roster is then validated by the backend and generated/persisted.

---

## Roster Naming

Rosters are deterministically named using:

```text
YYYY-MM-Group-GROUP_NUMBER
```

For example:

```text
2026-08-Group-1
```

The same year, month, and group number identify the roster.

---

# Team Members

The Team Members section allows users to:

- View team members
- Add a member
- Deactivate a member

Each employee has an employee ID and name.

Deactivation is performed through the backend and the employee is removed from the active-member workflow while existing roster assignments can still be associated with the employee where supported by the database design.

---

# Excel Upload

The Download / Upload Roster section allows a roster to be uploaded from an `.xlsx` Excel file.

The user selects:

- Month
- Year
- Group number
- Excel file

The uploaded Excel file is converted into the application's internal roster representation.

Employee names in the Excel file are matched against employees in the database. The roster assignments are stored using the employee ID rather than the employee's name.

If the specified roster does not already exist:

```text
Roster → Created
Assignments → Inserted
```

If the roster already exists:

```text
Existing assignments → Deleted
New assignments → Inserted
Existing roster record → Reused
```

The database operation is committed as one transaction.

If the upload cannot be saved, the transaction is rolled back so that the database is not left partially updated.

---

# Excel Download

The Download Roster feature uses:

```text
Year
Month
Group Number
```

to identify the requested roster.

If the roster exists, the backend generates the Excel response and the browser downloads it.

The generated filename follows:

```text
YYYY-MM-Group-GROUP_NUMBER.xlsx
```

For example:

```text
2026-08-Group-1.xlsx
```

If the roster does not exist, the frontend displays an appropriate status message instead of downloading a file.

---

# Docker Commands Cheat Sheet

## Start everything

```bash
docker compose up -d --build
```

## Start without rebuilding

```bash
docker compose up -d
```

## Stop everything

```bash
docker compose down
```

## Stop and delete database volume

```bash
docker compose down -v
```

## Rebuild everything

```bash
docker compose up -d --build
```

## Rebuild only backend

```bash
docker compose up -d --build backend
```

## Rebuild only frontend

```bash
docker compose up -d --build frontend
```

## Restart frontend

```bash
docker compose restart frontend
```

## Restart backend

```bash
docker compose restart backend
```

## View all logs

```bash
docker compose logs
```

## Follow all logs

```bash
docker compose logs -f
```

## Backend logs

```bash
docker compose logs -f backend
```

## Frontend logs

```bash
docker compose logs -f frontend
```

## PostgreSQL logs

```bash
docker compose logs -f postgres
```

## Check containers

```bash
docker compose ps
```

---

# Fresh Setup From Scratch

For a completely fresh machine:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd "Roster Automation"
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose ps
```

Then open:

```text
http://localhost:5173
```

and verify the backend through:

```text
http://localhost:8000/docs
```

---

# Troubleshooting

## Frontend is not loading

Check:

```bash
docker compose ps
```

Then:

```bash
docker compose logs -f frontend
```

If dependencies have changed:

```bash
docker compose up -d --build frontend
```

---

## Backend is not loading

Check:

```bash
docker compose logs -f backend
```

Then rebuild:

```bash
docker compose up -d --build backend
```

---

## Swagger is not opening

Check that the backend container is running:

```bash
docker compose ps
```

Then:

```bash
curl http://localhost:8000/health
```

If the health endpoint works, open:

```text
http://localhost:8000/docs
```

---

## Database tables are missing

Run:

```bash
docker compose exec backend alembic upgrade head
```

Then inspect the database:

```bash
docker compose exec postgres psql -U postgres -d roster_db
```

and:

```sql
\dt
```

---

## Upload endpoint complains about multipart

FastAPI file-upload endpoints require the `python-multipart` package.

If a fresh environment reports:

```text
Form data requires "python-multipart" to be installed.
```

install it in the backend environment:

```bash
docker compose exec backend pip install python-multipart
```

For a permanent project setup, make sure `python-multipart` is included in `backend/requirements.txt` and rebuild the backend image.

---

# Stopping the Project

To stop the application while keeping the PostgreSQL data:

```bash
docker compose down
```

To start it again later:

```bash
docker compose up -d
```

---

# Author

**Developed By Siddharth Chaudhari**
