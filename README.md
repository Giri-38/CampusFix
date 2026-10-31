# CampusFix - Hostel Complaint & Maintenance Tracker

A full-stack web application where hostel residents raise maintenance complaints and the
warden triages, updates and analyses them.

| Layer    | Technology                                                        |
|----------|-------------------------------------------------------------------|
| Frontend | React 18, React Router 6, Recharts, Vite                          |
| Backend  | Python Flask REST API, SQLite, JWT (PyJWT), Flask-CORS            |
| Testing  | pytest (16 API tests), Vitest (4 unit tests)                      |

## Features

**Students** - register and log in, raise complaints (category, priority, room), follow each
one through `Open -> In Progress -> Resolved` on a timeline, comment, and rate the fix (1-5).

**Warden** - dashboard with totals, resolution rate, average hours to resolve and average
rating; charts for status, category and unresolved-by-priority; searchable, filterable
complaint list (high priority first); update status with a note the student can see.

**Security** - hashed passwords, signed JWT bearer tokens with 8-hour expiry, roles
re-checked against the database on every request (a forged role claim is ignored),
parameterised SQL, React's built-in output escaping, server-side validation of every field,
students can only access their own complaints.

## Architecture

```
React SPA (Vite)  --/api/* JSON + Bearer JWT-->  Flask REST API  -->  SQLite
  pages, routing,                                  auth, RBAC,
  charts, AuthContext                              validation, analytics
```

## Project structure

```
campusfix/
├── backend/
│   ├── app.py              # Flask app factory, schema, REST endpoints, JWT auth
│   ├── seed.py             # demo data generator
│   ├── requirements.txt
│   └── tests/test_app.py   # API tests: auth, RBAC, workflow, validation, injection
└── frontend/
    ├── index.html, vite.config.js, package.json
    └── src/
        ├── main.jsx, App.jsx        # entry point and routes
        ├── api.js, auth.jsx         # fetch wrapper, AuthContext (login/logout/session restore)
        ├── utils.js, utils.test.js  # helpers + Vitest tests
        ├── components/              # Navbar, ProtectedRoute, Pill
        └── pages/                   # Login, Register, StudentDashboard, NewComplaint,
                                     # ComplaintDetail, AdminDashboard
```

## Run it (development)

Open two terminals.

**Terminal 1 - backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed.py                    # optional demo data
python app.py                     # API on http://127.0.0.1:5000
```

**Terminal 2 - frontend**
```bash
cd frontend
npm install
npm run dev                       # open http://localhost:5173
```

The Vite dev server proxies `/api` to the Flask backend, so no extra configuration is needed.

Demo logins created by `seed.py`:

| Role    | Email                  | Password    |
|---------|------------------------|-------------|
| Warden  | warden@campusfix.test  | Warden@123  |
| Student | aarav@campusfix.test   | Student@123 |

Create your own warden: `cd backend && python -m flask --app app create-warden`.

## Run it (single server, production-style)

```bash
cd frontend && npm install && npm run build      # creates frontend/dist
cd ../backend && python app.py                   # Flask now also serves the React build
```
Open http://127.0.0.1:5000. Before deploying anywhere public set `CAMPUSFIX_SECRET` to a long
random string and `CAMPUSFIX_CORS` to your site's origin.

## Tests

```bash
cd backend && python -m pytest -q       # API tests
cd frontend && npm test                 # frontend unit tests
```

## REST API

| Method & route                          | Access         | Purpose                               |
|-----------------------------------------|----------------|---------------------------------------|
| `POST /api/auth/register`               | public         | Create a student account              |
| `POST /api/auth/login`                  | public         | Returns `{token, user}`               |
| `GET  /api/auth/me`                     | any user       | Current user from token               |
| `GET  /api/meta`                        | public         | Categories, priorities, statuses      |
| `GET  /api/complaints`                  | student/warden | Own (student) or all (warden); `q`, `status`, `category` filters |
| `POST /api/complaints`                  | student        | Raise a complaint                     |
| `GET  /api/complaints/<id>`             | owner/warden   | Complaint plus timeline               |
| `POST /api/complaints/<id>/comments`    | owner/warden   | Add a comment                         |
| `POST /api/complaints/<id>/status`      | warden         | Change status with optional note      |
| `POST /api/complaints/<id>/rating`      | owner          | Rate a resolved complaint (1-5)       |
| `GET  /api/stats`                       | warden         | Aggregate analytics                   |

## Database schema

`users` (name, email unique, password hash, role, room) ·
`complaints` (title, description, category, priority, status, room, rating, created/updated/resolved timestamps) ·
`updates` (timeline: comments and status changes per complaint)

## Known limitations / future work

- The JWT is kept in `localStorage`; a production deployment would prefer an HttpOnly cookie.
- Photo attachments, e-mail/SMS notifications, assigning complaints to named staff, SLA timers.
