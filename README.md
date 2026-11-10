# Roster Automation

A full-stack application that generates fair monthly shift rosters for teams split into groups.

Rosters are built by a **constraint solver** (Google OR-Tools CP-SAT): the team lead enters each member's requests, and the solver produces a roster that meets every hard rule, breaks as few requests as possible, and balances shifts fairly across the team. Rosters are stored in PostgreSQL and can be downloaded and uploaded as Excel files in the team's official format.

---

## Features

- **Constraint-based roster generation** (OR-Tools CP-SAT)
  - Hard rules are always met (coverage, C-shift limits, rest rules, weekend and G limits, previous-month history)
  - Member requests are honoured unless a hard rule makes that impossible; the ones that had to be dropped are listed
  - Fair distribution: C shifts in one run per person and spread evenly, balanced A/B shifts, 2–3 weekly offs per 7 days, offs kept in pairs
- **Multiple groups**: each member belongs to one group; rosters, history and Excel files are per group
- **Final rule check** before saving; a generated roster that breaks a rule is never saved
- **Excel download** in the official roster format (colours, per-member totals, daily counts, legend)
- **Excel upload** of edited or existing rosters (creates or overwrites)
- **Roster delete** with confirmation
- **Team and group management**: add, move and deactivate members; add, rename, activate and deactivate groups
- FastAPI Swagger/OpenAPI documentation
- Automated solver tests
- Docker Compose-based local development

---

## Contents

1. [Getting Started (from a brand-new computer)](#getting-started-from-a-brand-new-computer)
2. [Using the Application](#using-the-application)
3. [How Roster Generation Works](#how-roster-generation-works)
4. [Tech Stack](#tech-stack) and [Project Structure](#project-structure)
5. [Running Tests](#running-tests) and [Development](#development)
6. [Troubleshooting](#troubleshooting)

---

# Getting Started (from a brand-new computer)

These steps assume a computer with **nothing installed**: no Python, no Node.js, no database, no Docker. You only need to install two programs, **Git** and **Docker Desktop**. Docker then runs everything else (Python, Node.js, PostgreSQL) inside containers, so you never install those yourself.

Total time: about 20–30 minutes, most of it waiting for downloads.

## What you need

- Windows 10/11 (64-bit), macOS 12 or newer, or Linux
- At least 8 GB of RAM and about 5 GB of free disk space
- An internet connection for the first setup

---

## Step 1: Install Git

Git downloads the project from GitHub.

**Windows**
1. Go to https://git-scm.com/download/win; the download starts automatically.
2. Run the installer and click **Next** on every screen (the defaults are fine).

**macOS**
1. Open **Terminal** (press `Cmd + Space`, type `Terminal`, press Enter).
2. Type `git --version` and press Enter.
3. If Git isn't installed, macOS offers to install the "command line developer tools". Click **Install** and wait for it to finish.

**Linux (Ubuntu/Debian)**
```bash
sudo apt update && sudo apt install -y git
```

> **No Git?** You can skip this step: on the project's GitHub page, click the green **Code** button → **Download ZIP**, then unzip it. In Step 4, use the unzipped folder instead of cloning.

---

## Step 2: Install Docker Desktop

Docker Desktop runs the database, backend and frontend.

**Windows**
1. Go to https://www.docker.com/products/docker-desktop/ and download **Docker Desktop for Windows**.
2. Run the installer and keep **"Use WSL 2"** ticked.
3. Restart the computer when asked.
4. Open **Docker Desktop** from the Start menu and accept the terms. If it asks you to install or update WSL, follow its instructions and restart again.

**macOS**
1. Go to https://www.docker.com/products/docker-desktop/.
2. Download the version for your chip: **Apple Silicon** (M1/M2/M3/M4) or **Intel**. To check: Apple menu → **About This Mac**.
3. Open the downloaded `.dmg`, drag **Docker** into **Applications**, then open Docker from Applications.

**Linux:** install Docker Desktop for Linux, or Docker Engine with the Compose plugin, following https://docs.docker.com/engine/install/.

**Before continuing:** Docker Desktop must be **open and running**. The whale icon appears in the taskbar (Windows) or menu bar (Mac), and the app shows "Engine running".

---

## Step 3: Open a terminal and check the installs

- **Windows:** press the Windows key, type `PowerShell`, press Enter.
- **macOS:** open **Terminal**.

Run these one at a time:

```bash
git --version
docker --version
docker compose version
```

Each should print a version number. If `docker` isn't found, make sure Docker Desktop is open, then close and reopen the terminal.

---

## Step 4: Download the project

In the terminal, go to the folder where you want the project, for example your Desktop:

```bash
cd Desktop
```

Then download it:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd roster-automation
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with the repository's address (green **Code** button on GitHub → copy the HTTPS link). If the folder has a different name, use that name in the `cd` command.

> **Downloaded the ZIP instead?** Unzip it, then `cd` into the unzipped folder (it may be called `roster-automation-main`).

If the project contains a file called `.env.example`, create your own settings file from it:

- Windows (PowerShell): `copy .env.example .env`
- macOS/Linux: `cp .env.example .env`

---

## Step 5: Start the application

Make sure Docker Desktop is running, then in the project folder run:

```bash
docker compose up -d --build
```

The **first run takes 5–10 minutes**: Docker downloads PostgreSQL, Python and Node.js and installs the project's packages. Later starts take a few seconds.

When it finishes, check that all three parts are running:

```bash
docker compose ps
```

You should see `roster-postgres`, `roster-backend` and `roster-frontend` with the status **Up** or **running**.

---

## Step 6: Create the database tables

Only needed the first time (and after updates that add migrations):

```bash
docker compose exec backend alembic upgrade head
```

---

## Step 7: Open the app

Open a web browser and go to: **http://localhost:5173**

Other addresses:

| What | Address |
|---|---|
| The app | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API documentation (Swagger) | http://localhost:8000/docs |

---

## Step 8: First-time use

The database starts empty. To generate your first roster:

1. Scroll to **Team Members**.
2. Under **Groups**, add a group, for example number `08`.
3. Under **Add Member**, add the team members (employee ID and name) to that group. A group needs **7 to 10 members** for a full month (see [Team size](#team-size)).
4. Scroll back up to **Create Monthly Roster**, pick the month, year and group, enter any requests, and click **Generate Roster**.
5. Download it as Excel from **Download / Upload / Delete Roster**.

---

## Stopping and starting later

Stop the app (your data is kept):

```bash
docker compose down
```

Start it again later. Open Docker Desktop first, then in the project folder:

```bash
docker compose up -d
```

To get the latest version of the project:

```bash
git pull
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

---

## Setup problems

| Problem | Fix |
|---|---|
| `docker: command not found` / `'docker' is not recognized` | Docker Desktop isn't installed or isn't running. Open it, wait until it says "Engine running", then reopen the terminal. |
| `Cannot connect to the Docker daemon` | Same: start Docker Desktop and wait for it to finish starting. |
| Windows: Docker asks for WSL | Follow its prompt (or run `wsl --update` in PowerShell as administrator) and restart. |
| `port is already allocated` (5173, 8000 or 5432) | Another program uses that port, often another PostgreSQL. Close it, or stop other containers with `docker ps` and `docker stop <name>`. |
| The page at localhost:5173 doesn't load | Wait a minute after starting, then refresh. Check `docker compose ps` and `docker compose logs -f frontend`. |
| `relation ... does not exist` / missing tables | Run Step 6 again. |
| The first build fails while downloading | Check your internet connection and run `docker compose up -d --build` again. |

---

# Using the Application

## Groups and team members

In the **Team Members** section:

- **Groups**: add a group (number `01`–`99`, optional name), rename it, or deactivate/activate it. A group with active members can't be deactivated.
- **Members**: add a member to a group, move a member to another group, or deactivate a member. Positions are kept per group.

The group number is fixed once created, because roster names and Excel files refer to it. Rosters saved before a member moved stay under the old group.

## Create a monthly roster

In **Create Monthly Roster**, choose the month, year, group and number of public holidays, then enter each member's requests as comma-separated days (for example `2,5,8`) under the shift they want (A, B, C, G, L or W).

The frontend checks for invalid days, days outside the month and the same day under two shifts. The backend validates the request and the group, runs the solver (up to 60 seconds), checks the result against every hard rule, and saves it.

After generation, the page shows any requests that could not be met, for example *"Geetanjali Chivukula: B shift on 4 Aug 2026 could not be given."*

Rosters are named:

```text
YYYY-MM-Group-GROUP_NUMBER      e.g. 2026-08-Group-08
```

## Download, upload and delete

In **Download / Upload / Delete Roster**, choose the month, year and group (inactive groups are listed too, so their old rosters stay reachable).

- **Download**: an `.xlsx` in the official format, with live formulas for the totals and daily counts.
- **Upload**: reads cell A1 (`Group = 08`), the member names in column C from row 3 down, and one shift code per day from column D. Names are matched against the selected group's members. An existing roster is overwritten in a single transaction.
- **Delete**: removes the roster after confirmation.

> Uploaded rosters are not checked against the scheduling rules. They are saved as they are and used as history for the next month.

---

# How Roster Generation Works

## Shifts

| Code | Meaning |
|---|---|
| A | Morning shift (6:30 AM – 3:30 PM) |
| B | Afternoon shift (2:00 PM – 11:00 PM) |
| C | Night shift (10:00 PM – 7:00 AM) |
| G | General shift (9:00 AM – 6:00 PM) |
| W | Weekly off |
| H | Public holiday |
| L | Leave |

## Hard rules (always met)

- At least 1 member in A, B and C every day, and exactly 1 in C
- Each member does 3–5 C shifts per month
- The day after a C shift is C or a day off
- At most 5 working days in a row
- Each member gets exactly as many W as the month has weekend days, and as many H as the public holidays entered
- At most 2 members in each of A, B and G on Saturdays and Sundays
- At most 4 G shifts per member per month
- The last 5 days of the previous month count towards these rules

## Soft rules (best effort, in priority order)

The solver works in four phases. Each phase locks in its result, so a later phase can never undo an earlier one.

1. **Requests and leave**: meet member requests; give L only when requested or unavoidable. When requests must be broken, the solver breaks as few as possible and picks at random between equal options.
2. **C shifts**: one consecutive run of C per member, spread evenly across the team.
3. **Fairness**: balanced A/B shifts per member, 2–3 W in every 7 days, W kept in pairs, one member per shift on weekends where possible.
4. **Polish**: equal A and B each day with any odd person on G, at least 2 in A and B on weekdays, as few shift switches as possible.

## Team size

Every day needs exactly one C shift and each member does 3–5 C shifts, so a group needs **7–10 active members** for a 31-day month (6–10 for 30 days, 6–9 for 28–29 days). Outside this range no valid roster exists and the app explains why.

## Configuration

Rule limits live in `backend/app/scheduler/config.py`:

| Setting | Default | Meaning |
|---|---|---|
| `MAX_CONTINUOUS_WORKING_DAYS` | 5 | Max working days in a row |
| `MIN_C_PER_MEMBER` / `MAX_C_PER_MEMBER` | 3 / 5 | C shifts per member per month |
| `MAX_C_PER_DAY` | 1 | Members in C per day |
| `MAX_G_PER_MEMBER` | 4 | G shifts per member per month |
| `WEEKEND_MAX_PER_SHIFT` | 2 | Max members per shift on weekends |
| `SOLVER_TIME_LIMIT_SECONDS` | 60 | Max time per generation |

---

# Tech Stack

### Backend

- Python, FastAPI, Uvicorn
- Google OR-Tools (CP-SAT solver)
- SQLAlchemy, Alembic, PostgreSQL 17, Psycopg
- openpyxl (Excel import/export)
- Pytest

### Frontend

- React, Vite
- Axios
- Material UI (MUI), Lucide React

### Infrastructure

- Docker, Docker Compose

---

# Project Structure

```text
roster-automation/
│
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routes: rosters, team members, groups
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── scheduler/      # CP-SAT solver, rule validator, config
│   │   └── services/       # Excel import/export, persistence, history, groups
│   ├── alembic/            # Database migrations
│   ├── tests/              # Solver tests
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/     # RosterSetup, TeamMembers
│   │   ├── services/       # API clients
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── Dockerfile
│
└── docker-compose.yml
```

---

# Running Tests

Inside the backend container:

```bash
docker compose exec backend pytest -v
```

Or locally from `backend/` (with the dependencies installed):

```bash
python3 -m pytest tests/test_cp_solver.py
```

The suite checks every hard rule, previous-month history, request handling and relaxation, and the soft rules. It takes about 2–3 minutes because each test runs the solver.

---

# Development

## Backend

Backend source is mounted into the container. After changing Python dependencies in `backend/requirements.txt`:

```bash
docker compose up -d --build backend
```

If a code change seems to have no effect, force a restart:

```bash
docker compose up -d --build --force-recreate backend
```

## Frontend

The frontend runs through Vite inside Docker. To add a dependency:

```bash
docker compose exec frontend npm install <package-name>
docker compose up -d --build frontend
```

## Database migrations

```bash
docker compose exec backend alembic upgrade head      # apply migrations
docker compose exec backend alembic current           # current version
docker compose exec backend alembic history           # history
docker compose exec backend alembic revision --autogenerate -m "describe change"
```

Review autogenerated migrations before applying them.

## PostgreSQL shell

```bash
docker compose exec postgres psql -U postgres -d roster_db
```

Useful commands: `\dt` (list tables), `\d groups`, `\d team_members`, `\d rosters`, `\d roster_assignments`, `\q` (exit).

---

# Docker Commands Cheat Sheet

| Action | Command |
|---|---|
| Start everything | `docker compose up -d --build` |
| Start without rebuilding | `docker compose up -d` |
| Stop (keep data) | `docker compose down` |
| Stop and **delete the database** | `docker compose down -v` |
| Rebuild backend | `docker compose up -d --build backend` |
| Rebuild frontend | `docker compose up -d --build frontend` |
| Follow logs | `docker compose logs -f` |
| Backend logs | `docker compose logs -f backend` |
| Check containers | `docker compose ps` |

> **Warning:** `docker compose down -v` deletes the PostgreSQL volume and all data. Back up first with:
> `docker compose exec postgres pg_dump -U postgres roster_db > backup.sql`

---

# Troubleshooting

**Frontend not loading:** check `docker compose ps` and `docker compose logs -f frontend`. If dependencies changed, rebuild with `docker compose up -d --build frontend`.

**Backend not loading or code changes ignored:** check `docker compose logs -f backend`, then run `docker compose up -d --build --force-recreate backend`.

**Database tables missing:** run `docker compose exec backend alembic upgrade head`.

**"Roster could not be generated"**: usually the group has too few or too many active members for the month (see [Team size](#team-size)).

**Upload fails with "not a member of group"**: the names in the Excel file must match members of the selected group (capitals and extra spaces are ignored).

**Upload complains about multipart:** make sure `python-multipart` is in `backend/requirements.txt` and rebuild the backend.

---

# Author

**Developed by Siddharth Chaudhari**