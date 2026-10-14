# Architecture and Implementation Plan

## Context
The repo is an empty uv scaffold (root `main.py`, `pyproject.toml`; no code). The goal is a **demo-only** web app (synthetic data) where doctors manage appointments: create/view/edit/delete, search and filter. Each appointment has patient name, date/time, doctor, the hospital the doctor is visiting, type and status. This is a **public, multi-hospital system (e-channeling style)**, not a system for one hospital, so a doctor can visit several hospitals. Stack and layering are fixed by the brief and `CLAUDE.md`. This plan is **text only**. Nothing is built or installed until approved. On approval it is written to `docs/ARCHITECTURE.md` (sections 1-7) and `docs/DECISIONS.md` (section 8).

Answers to my clarifying questions (now fixed):
- **Auth (optional sign-in):** anyone can book an appointment **without signing in**. Signing in is optional. A `users` table with seeded demo accounts has roles `admin` (manages everything) and `doctor` (manages only their own appointments, and booking is pre-filled for their own doctor profile). Anonymous visitors can only browse hospitals and doctors, check availability and create a booking. Listing, viewing, editing and deleting appointments requires sign-in.
- **Slots:** fixed 30-minute slots, so the partial unique index fully prevents double booking.
- **DB access:** sync SQLAlchemy 2 + psycopg 3. Supabase Postgres is the database. Tests run in a throwaway schema.
- **Python layout:** `backend/pyproject.toml` managed by uv. The root `main.py`, `pyproject.toml`, `.python-version` and `requirements.txt` are removed or moved into `/backend`.

---

## 0. Things I think are wrong or risky (please review)

| # | Issue | Why it matters | Resolution in this plan |
|---|---|---|---|
| 1 | The unique index on `(doctor_id, start_time)` only blocks *identical* start times. | 09:00 and 09:15 would both be accepted. | Fixed 30-min slots, enforced by Pydantic **and** a DB `CHECK`. |
| 2 | The partial index predicate says only `status != 'cancelled'`. | A soft-deleted appointment would still block its slot forever. | Predicate is `status <> 'cancelled' AND deleted_at IS NULL`. |
| 3 | The Supabase pooled string (pgbouncer, transaction mode, port 6543) breaks prepared statements and DDL. The direct host is IPv6-only on the free tier. | Random `prepared statement does not exist` errors, and Alembic failing from IPv4-only hosts. | App uses the pooled URL with `prepare_threshold=None`. Alembic uses the **session-pooler** URL (IPv4, port 5432) via a separate `DATABASE_URL_MIGRATIONS`. |
| 4 | Supabase auto-exposes `public` tables through its REST (PostgREST) API with the anon key. | Our tables would be publicly readable and writable, even though we only use plain Postgres. | Migration runs `ENABLE ROW LEVEL SECURITY` on every table with **no policies**. The app's `postgres` role bypasses RLS. |
| 5 | Auth is not in your milestone list, but every endpoint is protected and `CLAUDE.md` requires authorization checks. | CRUD can't be tested or built correctly without it. | Added **M2: Auth**, between models and CRUD. |
| 6 | Search terms travel in the query string (`?q=jane`). Hosting access logs would record them. | PII in logs, which contradicts "no PII in logs". | Disable uvicorn's access log. Use our own middleware, which logs the method, the route *template*, the status and the duration (never the query string or the body). Accept the residual risk on the hosts' logs, since the data is synthetic. |
| 7 | JWT in `localStorage` is readable by any XSS. | Token theft. | Short expiry (30 min), token kept in `sessionStorage`, no `dangerouslySetInnerHTML`, strict CORS. Not an httpOnly cookie, because a cross-site Vercel-to-Render cookie adds SameSite/CSRF complexity. Recorded in DECISIONS. |
| 8 | Supabase free tier pauses after about 7 days of inactivity. | The first demo request after a pause fails or is slow. | README note plus a `/health` DB ping. Optional: an external uptime pinger. |
| 9 | `CLAUDE.md` is inconsistent: it lists root `main.py`, `pyproject.toml` and `requirements.txt`, and "Maintain the log file" is undefined. | Future sessions would follow conflicting instructions. | M0 rewrites its structure section. I **assume** the log file is `docs/WORKLOG.md`, with one entry per milestone. Tell me if you meant something else. |
| 10 | `CLAUDE.md` says to ask before adding any dependency. | Prompting per package would be tedious. | Section 9 lists every dependency up front for one approval. |
| 11 | The error shape `{error:{code,message}}` has no place for field-level validation errors. | The form can't highlight fields. | Add an optional `details: [{field, message}]` to the shape. |
| 12 | "Slot on :00 or :30 UTC" is wrong for time zones with 45-minute offsets (e.g. Nepal). | Slots would look odd there. | Acceptable for a demo. Noted in DECISIONS. There is no clinic time zone, so there are **no business-hours rules**. |
| 13 | Anonymous booking means `POST /appointments` is a public write endpoint. | Spam bookings can fill a doctor's slots, and a bot can enumerate availability. Anonymous users also can't see, edit or cancel their booking afterwards. | A small in-process per-IP rate limiter (429 `rate_limited`, no new dependency; limits are per instance, which is fine for a single demo instance). Anonymous bookings are forced to `status = scheduled` and `created_by = NULL`. The availability endpoint returns only taken start times, never patient names. The booking confirmation shows a reference id. Cancelling or changing a booking is done by staff. Open point: no contact details are collected (PII), so staff can't reach an anonymous patient. |

---

## 1. Milestones

Conventions for every milestone:
- Write the tests first and watch them fail, then implement.
- The gate is `ruff check && ruff format --check && mypy app && pytest --cov=app --cov-fail-under=80` for the backend, and `npm run lint && npm test && npm run build` for the frontend.
- Each milestone is one PR-sized commit (or a few), and `docs/WORKLOG.md` gets an entry.
- The clock is injected (`app/core/clock.py: utcnow()`, overridden through FastAPI dependencies in tests), so no freezegun is needed.

### M0: Repo restructure and backend foundation
- **Goal / DoD:** `GET /health` works. A typed config loads from `.env`. Every error uses the standard shape. Logging has no PII. Tooling runs green. The app connects to Supabase through `DATABASE_URL`.
- **Files:**
  - `backend/pyproject.toml` (ruff, mypy, pytest config), `backend/.python-version`
  - `backend/app/main.py` (`create_app()`), `backend/app/core/{config.py, errors.py, logging.py, clock.py}`, `backend/app/api/v1/{__init__.py, router.py, health.py}`
  - `backend/tests/{conftest.py, api/test_health.py, api/test_error_shape.py, unit/test_config.py}`
  - `backend/.env.example`, `.gitignore` (update)
  - `docs/WORKLOG.md`
  - Remove the root `main.py`, `pyproject.toml` and `.python-version`
  - Update `CLAUDE.md` (structure and commands)
- **Tests first:**
  - `/health` returns 200 `{status:"ok"}` and 503 when the DB is unreachable.
  - An unknown route returns 404 in the standard shape. A body validation failure returns 422 with `details`. An unhandled exception returns 500 `internal_error` with no stack trace.
  - Config rejects a `JWT_SECRET` shorter than 32 chars, and rejects a CORS origin of `*`.
  - A log-capture test asserts that the query string and body never appear in logs.
- **Risks / questions:** Needs `uv` installed and a Supabase project with its connection strings.
- **Commit:** `chore: restructure into backend/ and add FastAPI foundation`

### M1: Models and migrations
- **Goal / DoD:** `alembic upgrade head` and `downgrade base` both work on a fresh Postgres. Constraints and indexes are verified by tests. A seed script loads synthetic data.
- **Files:**
  - `backend/app/db/{base.py, session.py}`
  - `backend/app/models/{enums.py, hospital.py, doctor.py, doctor_hospital.py, user.py, appointment.py}`
  - `backend/alembic.ini`, `backend/alembic/env.py`
  - `backend/alembic/versions/0001_extensions_enums_hospitals_doctors_users.py`
  - `backend/alembic/versions/0002_appointments_indexes.py`
  - `backend/scripts/seed.py` (10 hospitals, about 20 doctors where some visit 2-3 hospitals, 1 admin and two user per doctor, about 50 synthetic appointments from a hard-coded fake-name list and a seeded `random`)
  - `backend/tests/db/{conftest.py, test_migrations.py, test_constraints.py, test_indexes.py}`
- **Test schema:** `tests/db/conftest.py` connects with `DATABASE_URL_MIGRATIONS`, creates a unique `test_<random>` schema, sets `search_path` to it on every connection, and drops it at teardown. It aborts if the active schema does not start with `test_`, which a test verifies. Migrations must not hard-code `public.`.
- **Tests first** (real Postgres on Supabase, per-test transaction rollback inside the test schema):
  - Upgrade/downgrade round-trip.
  - The same doctor + start time is rejected. It is allowed after the first appointment is `cancelled`. It is also allowed after a soft delete.
  - A 09:15 start is rejected by the `CHECK`.
  - A doctor can be linked to several hospitals. An appointment at a hospital the doctor does not visit is rejected by the composite foreign key. A doctor cannot have two active appointments at the same start time even at different hospitals. An appointment may have `created_by = NULL`.
  - RLS is enabled on all tables.
  - `EXPLAIN` with `enable_seqscan=off` shows the trigram GIN index used for `ILIKE '%ann%'`.
- **Risks / questions:**
  - Alembic autogenerate misses partial indexes and `gin_trgm_ops`, so I write those migrations by hand.
  - Native PG enums mean adding a value later needs a migration (DECISIONS #5).
  - `CREATE EXTENSION pg_trgm` is allowed on Supabase, but the advisor may warn about extensions in `public`.
- **Commit:** `feat(db): add models, migrations, indexes and seed script`

### M2: Auth, optional sign-in (added)
- **Goal / DoD:** `POST /auth/login` returns a JWT. `GET /auth/me` works. Dependencies `get_optional_user` (returns `None` for anonymous requests), `get_current_user` (401 if missing) and `require_role` exist. Passwords are hashed with argon2. A per-IP rate limiter protects login and anonymous booking.
- **Files:**
  - `backend/app/core/security.py` (hash, verify, encode/decode JWT)
  - `backend/app/core/ratelimit.py`
  - `backend/app/schemas/auth.py`
  - `backend/app/repositories/user_repository.py`
  - `backend/app/services/auth_service.py`
  - `backend/app/api/v1/{auth.py, deps.py}`
  - `backend/tests/unit/test_security.py`, `backend/tests/api/test_auth.py`
- **Tests first:**
  - Valid login returns 200. A wrong password and an unknown email return the **same** 401 `invalid_credentials` (no user enumeration).
  - An expired token, a tampered token, a missing header and an inactive user all return 401. The wrong role returns 403.
  - Tokens carry only `sub`, `role`, `exp` and `iat`. Tokens are never logged.
  - `get_optional_user` returns `None` with no header, but an **invalid or expired** token still returns 401 (it is not silently treated as anonymous).
  - The rate limiter returns 429 `rate_limited` with `Retry-After` after the limit, and is reset between tests.
- **Risks / questions:** No refresh tokens (30-min access token, then log in again). The rate limiter is in-process, so limits are per instance and reset on restart. Both are noted as demo limitations.
- **Commit:** `feat(auth): JWT login, current-user and role dependencies`

### M3: Appointment CRUD (TDD)
- **Goal / DoD:** public create (no sign-in needed), signed-in get/patch/soft-delete, and public `GET /hospitals`, `GET /doctors` and doctor availability work with authorization, validation and 409 on conflict. Routers contain no SQL.
- **Files:**
  - `backend/app/schemas/{appointment.py, doctor.py, hospital.py, common.py}`
  - `backend/app/repositories/{appointment_repository.py, doctor_repository.py, hospital_repository.py}`
  - `backend/app/services/{appointment_service.py, doctor_service.py, hospital_service.py}`
  - `backend/app/api/v1/{appointments.py, doctors.py, hospitals.py}`
  - `backend/app/core/errors.py` (extend with domain exceptions)
  - `backend/tests/unit/test_appointment_schemas.py`, `backend/tests/unit/test_appointment_service.py`, `backend/tests/api/test_appointments_crud.py`
- **Tests first:**
  - Schema rules (section 2).
  - Creating a duplicate slot returns 409 `slot_conflict`. Two concurrent creates for the same slot give exactly one 201 (the DB index is authoritative: the repository maps `IntegrityError` on `uq_appointments_doctor_slot`).
  - An **anonymous** create succeeds (201) with `created_by = NULL` and `status = scheduled`. An anonymous request that sends `status` other than `scheduled` is a 422. Anonymous GET, PATCH, DELETE and list return 401.
  - A signed-in doctor's create defaults `doctor_id` to their own and gets 403 for another doctor. An admin can book for any doctor.
  - `GET /doctors/{id}/availability?date=` returns taken start times only (no patient data), is public, and excludes cancelled and soft-deleted rows.
  - `GET /doctors` is public, includes the list of hospitals each doctor visits and filters by `hospital_id`. `GET /hospitals` is public and filters by `doctor_id`. Inactive doctors are excluded.
  - Booking a doctor at a hospital they don't visit is a 422 on `hospital_id`.
  - A doctor reading another doctor's appointment gets 404, so existence isn't leaked.
  - DELETE returns 204, and the row is then gone from GET and from the list, but still present in the DB with `deleted_at`.
  - Past start on create returns 422. Editing only the status of a past appointment is allowed.
- **Risks / questions:** The cancelled-to-scheduled reactivation can hit 409, which is intended.
- **Commit:** `feat(api): appointment CRUD with soft delete and conflict detection`

### M4: Search, filter, sort, pagination
- **Goal / DoD:** `GET /appointments` supports every parameter in section 2 with correct totals. Performance is acceptable at 10k seeded rows.
- **Files:** extend `appointment_repository.py` (query builder), `appointment_service.py`, `schemas/appointment.py` (`AppointmentListQuery`, `Page[T]`), `api/v1/appointments.py`; add `backend/tests/api/test_appointments_list.py`, `backend/tests/unit/test_list_query.py`.
- **Tests first:**
  - Each filter alone and combined. Multi-value `status` and `type`.
  - `q` is case-insensitive and substring-based, and `%`, `_` and `\` are treated literally.
  - Inclusive `date_from`, exclusive `date_to`, and the half-open boundary at midnight.
  - Sort whitelist with a stable tie-break on `id`. Page 2, the last page and a page beyond the end (empty `items`, correct `total`).
  - `page_size=101` gives 422. Doctor-role scoping applies to totals.
  - No N+1: the query count is asserted with a SQLAlchemy event counter.
- **Risks / questions:** Offset pagination is fine for a demo. Keyset pagination would be the production answer (DECISIONS note).
- **Commit:** `feat(api): searchable, filterable, sortable paginated appointment list`

### M5: Frontend scaffold
- **Goal / DoD:** `npm run dev` shows the public home (booking entry point) with the demo banner and a "Sign in" link. Sign-in is optional. After login, the protected staff area appears. Lint, test and build are green.
- **Routes:** public `/` (home), `/book`, `/book/confirmed`, `/login`. Protected `/appointments`, `/appointments/:id` (from M6/M7).
- **Files:**
  - `frontend/{package.json, vite.config.js, eslint.config.js, .prettierrc, index.html, .env.example}`
  - `frontend/src/{main.jsx, App.jsx, routes.jsx}`
  - `frontend/src/api/{client.js, auth.js, doctors.js, appointments.js}` (a thin `fetch` wrapper that attaches the token, parses the error shape and logs out on 401)
  - `frontend/src/components/{Layout.jsx, DemoBanner.jsx, ProtectedRoute.jsx, ErrorState.jsx, EmptyState.jsx, Spinner.jsx}`
  - `frontend/src/hooks/AuthContext.jsx`, `frontend/src/pages/{LoginPage.jsx, NotFoundPage.jsx}`
  - `frontend/src/utils/{datetime.js, errors.js}`
  - `frontend/src/__tests__/{setup.js, mocks/handlers.js}` plus tests
- **Tests first:**
  - `ProtectedRoute` redirects an unauthenticated user from staff pages only. Public pages render without a token, and the header shows "Sign in" or the user menu.
  - Login success stores the token and redirects. Login failure shows an accessible error.
  - The API client maps the error shape and clears the session on 401.
  - `datetime.js` round-trips local to UTC to local, including a DST-gap time.
  - No demo banner is rendered on any page.
- **Risks / questions:** Plain JS has no type safety, so a JSDoc `@typedef` for the API shapes in `api/` is the mitigation.
- **Commit:** `feat(frontend): Vite React scaffold with routing, auth and API client`

### M6: Appointments list page
- **Goal / DoD:** a list with search, filters, sort and pagination, all kept in the URL. Loading, empty and error states are present.
- **Files:**
  - `frontend/src/pages/AppointmentsPage.jsx`
  - `frontend/src/components/{AppointmentTable.jsx, AppointmentFilters.jsx, Pagination.jsx, StatusBadge.jsx}`
  - `frontend/src/hooks/{useAppointments.js, useDoctors.js, useDebouncedValue.js, useUrlFilters.js}`
  - tests in `frontend/src/__tests__/`
- **Tests first:**
  - Typing in search is debounced (300 ms, one request).
  - Filters round-trip through the URL and survive a reload.
  - The empty state shows "No appointments match your filters" with a clear-filters button. The error state has a retry button.
  - Pagination controls disable at the edges.
  - Changing a filter resets to page 1.
- **Risks / questions:** `placeholderData: keepPreviousData` keeps the table from flashing while paging.
- **Commit:** `feat(frontend): appointments list with search, filters and pagination`

### M7: Booking, edit and delete UI
- **Goal / DoD:** a public booking form (React Hook Form) that works without sign-in: choose a doctor and one of the hospitals that doctor visits (or pick a hospital first to see its doctors), then a free slot (from the availability endpoint), then type and patient name. A signed-in doctor gets themselves pre-selected with a choice among their own hospitals, and an admin can pick any. After booking, a confirmation page shows the reference id. Signed-in staff can edit and delete. 409 shows a message on the time field. Delete goes through a confirm dialog.
- **Files:**
  - `frontend/src/pages/{BookingPage.jsx, BookingConfirmedPage.jsx, AppointmentFormPage.jsx}`
  - `frontend/src/components/{AppointmentForm.jsx, SlotPicker.jsx, ConfirmDialog.jsx}`
  - `frontend/src/hooks/useAvailability.js`
  - `frontend/src/hooks/useAppointmentMutations.js`
  - tests
- **Tests first:**
  - Client-side validation messages. A 409 from the server sets the field error. A 422 `details` entry maps to its field.
  - An anonymous visitor can complete a booking with no token and sees the confirmation. The doctor dropdown only lists doctors of the chosen hospital, and taken slots are disabled in the picker.
  - A signed-in doctor sees themselves pre-selected, and only their own hospitals are offered.
  - A 429 shows a "too many attempts, try again shortly" message.
  - Submit is disabled while pending, to prevent double submit.
  - Delete only fires after confirmation, and focus returns sensibly afterwards.
  - After a mutation, the list query is invalidated.
  - Edit pre-fills the form with the local-time conversion.
- **Risks / questions:** `<input type="datetime-local" step="1800">` support varies by browser, so a minute `<select>` (00/30) is the fallback.
- **Commit:** `feat(frontend): appointment form, edit and confirmed delete`

### M8: Extras (see section 7 for the ranking)
- **Goal / DoD:** status quick-change in the table, dashboard count tiles, and a doctor day view.
- **Files:**
  - Backend: `GET /appointments/stats` in `appointments.py`, `appointment_service.py` and `appointment_repository.py`, plus `tests/api/test_appointments_stats.py`.
  - Frontend: `frontend/src/components/{StatusSelect.jsx, StatsTiles.jsx, DayView.jsx}` and `frontend/src/pages/DayViewPage.jsx`.
- **Tests first:**
  - Stats respect the filters and the role scoping.
  - Quick-change calls PATCH and updates optimistically, then rolls back on error.
  - The day view groups by doctor and renders the local time zone.
- **Risks / questions:** keep the day view a simple agenda list, not a full calendar library.
- **Commit:** `feat: status quick-change, dashboard counts and day view`

### M9: CI and hooks
- **Goal / DoD:** a PR runs lint, types, tests and build on both sides. Local hooks block a bad commit.
- **Files:**
  - `.github/workflows/ci.yml` (backend job with `DATABASE_URL_MIGRATIONS` from a GitHub secret, then `uv sync`, ruff, mypy, pytest with `--cov-fail-under=80`; the run-specific `test_<random>` schema keeps concurrent runs apart; frontend job with lint, test and build)
  - `.pre-commit-config.yaml` (ruff, eslint, prettier, a secret scan, `check-added-large-files`)
  - `.claude/settings.json` (an optional hook that runs ruff or eslint after edits)
- **Tests first:** push a deliberately failing commit on a throwaway branch and confirm CI goes red. Run the hooks against a staged fake secret.
- **Risks / questions:** the "hooks" in your brief could mean git hooks or Claude Code hooks. I plan both, with Claude hooks optional.
- **Commit:** `ci: add GitHub Actions workflow and pre-commit hooks`

### M10: Deployment (optional)
- **Goal / DoD:** the API runs on Render, the frontend on Vercel, both against Supabase, with the seed data loaded.
- **Files:**
  - `render.yaml` (build `uv sync`, pre-deploy `alembic upgrade head`, start `uvicorn app.main:create_app --factory --no-access-log --host 0.0.0.0 --port $PORT`)
  - `frontend/vercel.json` (SPA rewrite)
  - `docs/DEPLOYMENT.md` (env var table)
- **Tests first:** a post-deploy smoke checklist, which is manual: `/health`, login, create, conflict, delete, CORS from the Vercel origin only.
- **Risks / questions:**
  - Render's free tier cold-starts in about 30 s.
  - `CORS_ORIGINS` must contain the exact Vercel URL.
  - Preview deployments get new origins.
- **Commit:** `chore(deploy): add Render and Vercel configuration`

### M11: README and docs
- **Goal / DoD:** a new developer can run the app from the README alone.
- **Files:** `README.md` (overview, demo-data notice, local setup, env vars, seeded credentials, commands, API summary), final `docs/ARCHITECTURE.md` and `docs/DECISIONS.md`, `CLAUDE.md` refresh.
- **Tests first:** follow the README on a clean checkout (manual).
- **Commit:** `docs: complete README, architecture and decisions`

---

## 2. API contract (`/api/v1`)

**Common**
- JSON only. Timestamps are ISO-8601 UTC with a `Z` suffix. IDs are UUIDs. Request bodies use `extra="forbid"`.
- Auth is `Authorization: Bearer <jwt>`. **Public (no token):** `/health`, `POST /auth/login`, `GET /hospitals`, `GET /doctors`, `GET /doctors/{id}/availability` and `POST /appointments`. Everything else requires sign-in.
- **Error shape:** `{"error":{"code":"...","message":"...","details":[{"field":"start_time","message":"..."}]}}`. `details` is optional and only used for 422.

| Code | HTTP | When |
|---|---|---|
| `validation_error` | 422 | Any body, query or path validation failure |
| `invalid_credentials` | 401 | Wrong email or password (same response for both) |
| `unauthorized` | 401 | Missing, invalid or expired token, or an inactive user |
| `forbidden` | 403 | Authenticated but not allowed (e.g. a doctor creating for another doctor) |
| `not_found` | 404 | Unknown id, soft-deleted, or another doctor's appointment (for doctor role) |
| `slot_conflict` | 409 | The doctor already has an active appointment in that slot |
| `rate_limited` | 429 | Too many login or anonymous booking attempts from one IP (`Retry-After` header) |
| `internal_error` | 500 | Anything unhandled (no details leaked) |

**Endpoints**

| Method + path | Request | Success response | Errors |
|---|---|---|---|
| `GET /health` (outside `/api/v1`) | none | 200 `{status:"ok"}` | 503 if the DB is down |
| `POST /auth/login` | `{email, password}` | 200 `{access_token, token_type:"bearer", expires_in, user:{id,email,role,doctor_id}}` | 401 `invalid_credentials`, 422 |
| `GET /auth/me` | none | 200 `{id,email,role,doctor_id}` | 401 |
| `GET /hospitals` (public) | `doctor_id?` | 200 `[{id, name}]` | 422 |
| `GET /doctors` (public) | `hospital_id?` | 200 `[{id, full_name, specialty, hospitals:[{id,name}]}]` (active only) | 422 |
| `GET /doctors/{id}/availability` (public) | `date` (aware instants `date_from`, `date_to`, max 7 days) | 200 `{doctor_id, taken:[start_time,...]}` | 404, 422 |
| `POST /appointments` (public; token optional) | `{patient_name, doctor_id, hospital_id, start_time, appointment_type, status?}` (`status` only for signed-in users) | 201 + `Location`, body = Appointment | 401 (invalid token), 403, 404 (doctor not found), 409, 422, 429 |
| `GET /appointments` | query params below | 200 `Page<Appointment>` | 401, 422 |
| `GET /appointments/stats` | `date_from?, date_to?, doctor_id?` | 200 `{total, by_status:{scheduled,...}}` | 401, 422 |
| `GET /appointments/{id}` | none | 200 Appointment | 401, 404 |
| `PATCH /appointments/{id}` | any subset of the create fields (at least one) | 200 Appointment | 401, 403, 404, 409, 422 |
| `DELETE /appointments/{id}` | none | 204 (soft delete) | 401, 404 |

`/appointments/stats` is declared before `/{id}` to avoid route shadowing.

**Appointment** = `{id, patient_name, doctor:{id,full_name,specialty}, hospital:{id,name}, start_time, appointment_type, status, created_at, updated_at}`.

**Page<T>** = `{items:[T], total, page, page_size, pages}`.

**Validation rules (create/patch)**
- `patient_name`: trimmed, 2-100 chars, no control characters. Null is invalid on PATCH.
- `doctor_id`: an existing, active doctor. A user with the `doctor` role must use their own id (defaulted if omitted). Anonymous visitors and admins may choose any active doctor.
- `hospital_id`: an existing hospital that the chosen doctor visits (otherwise 422 on `hospital_id`).
- `status`: anonymous creates are always `scheduled` (sending any other value is a 422).
- `start_time`:
  - Timezone-aware (a naive datetime is a 422).
  - Normalized to UTC.
  - Seconds and microseconds must be 0, and the minute must be 0 or 30.
  - Must be in the future and no more than 2 years ahead. This is checked on create, and on PATCH only when `start_time` or `doctor_id` actually changes.
- `appointment_type`: `consultation | follow_up | check_up | procedure | vaccination`.
- `status`: `scheduled | confirmed | completed | cancelled | no_show` (default `scheduled`).

**List query params**

| Param | Rule |
|---|---|
| `q` | Optional, max 100 chars. Case-insensitive substring match on `patient_name`. `%`, `_` and `\` are escaped. Empty is ignored. |
| `doctor_id` | UUID. Ignored/overridden for the doctor role (always their own). |
| `hospital_id` | UUID. Filters by the hospital of the appointment. |
| `status`, `type` | Repeatable (`status=scheduled&status=confirmed`), validated against the enums. |
| `date_from`, `date_to` | Aware instants. `date_from` is inclusive and `date_to` exclusive. 422 if `date_from > date_to`. The UI converts the user's local day boundaries to UTC. |
| `sort` | One of `start_time, -start_time, patient_name, -patient_name, created_at, -created_at`. Default `start_time`. A tie-break on `id` keeps pages stable. |
| `page` | Integer >= 1, default 1. |
| `page_size` | Integer 1-100, default 20. Over-limit gives 422, it is not clamped. |

---

## 3. Data model

**hospitals**: `id uuid PK default gen_random_uuid()`, `name text NOT NULL`, `created_at timestamptz NOT NULL default now()`. `UNIQUE (lower(name))`.

**doctors**: `id uuid PK default gen_random_uuid()`, `full_name text NOT NULL`, `specialty text NOT NULL`, `is_active boolean NOT NULL default true`, `created_at timestamptz NOT NULL default now()`.

**doctor_hospitals** (which hospitals a doctor visits, many-to-many): `doctor_id uuid NOT NULL FK doctors(id) ON DELETE RESTRICT`, `hospital_id uuid NOT NULL FK hospitals(id) ON DELETE RESTRICT`, `PRIMARY KEY (doctor_id, hospital_id)`, index `ix_doctor_hospitals_hospital (hospital_id, doctor_id)`. Rows are seeded; there are no endpoints to edit them in this version.

**users**: `id uuid PK`, `email text NOT NULL`, `password_hash text NOT NULL`, `role user_role NOT NULL` (`admin | doctor`), `doctor_id uuid NULL FK doctors(id)`, `is_active boolean NOT NULL default true`, `created_at timestamptz`.
- `UNIQUE (lower(email))`, `UNIQUE (doctor_id)`.
- `CHECK (role <> 'doctor' OR doctor_id IS NOT NULL)`.

**appointments**:

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | `gen_random_uuid()` |
| `patient_name` | varchar(100) NOT NULL | `CHECK (char_length(btrim(patient_name)) >= 2)` |
| `doctor_id` | uuid NOT NULL | FK doctors(id) `ON DELETE RESTRICT` |
| `hospital_id` | uuid NOT NULL | Composite FK `(doctor_id, hospital_id)` to `doctor_hospitals`, so a doctor can only be booked at a hospital they visit |
| `start_time` | timestamptz NOT NULL | UTC |
| `appointment_type` | enum NOT NULL | `appointment_type` |
| `status` | enum NOT NULL | `appointment_status`, default `scheduled` |
| `created_by` | uuid NULL | FK users(id); `NULL` means booked anonymously |
| `created_at`, `updated_at` | timestamptz NOT NULL | default `now()`, `updated_at` maintained on update by SQLAlchemy `onupdate` |
| `deleted_at` | timestamptz NULL | soft delete marker |

Constraint `ck_appointments_slot_aligned`: `date_part('minute', start_time AT TIME ZONE 'UTC') IN (0,30) AND date_part('second', start_time AT TIME ZONE 'UTC') = 0`.

**Indexes**
1. `uq_appointments_doctor_slot`: `UNIQUE (doctor_id, start_time) WHERE status <> 'cancelled' AND deleted_at IS NULL`. This is the anti-double-booking guarantee. It deliberately ignores `hospital_id`, because a doctor cannot be at two hospitals at the same time.
2. `ix_appointments_start_time`: `(start_time) WHERE deleted_at IS NULL`, for date range and default sort.
3. `ix_appointments_doctor_start`: `(doctor_id, start_time) WHERE deleted_at IS NULL`, for doctor filter and the day view (includes cancelled rows, which index 1 excludes).
4. `ix_appointments_status_start`: `(status, start_time) WHERE deleted_at IS NULL`, for status filter and dashboard counts.
5. `ix_appointments_hospital_start`: `(hospital_id, start_time) WHERE deleted_at IS NULL`, for the hospital filter.
6. `ix_appointments_patient_name_trgm`: `GIN (patient_name gin_trgm_ops)`, created after `CREATE EXTENSION IF NOT EXISTS pg_trgm`. It serves `ILIKE '%term%'`. Terms under 3 characters fall back to a scan, which is fine at demo size.

**Security:** `ENABLE ROW LEVEL SECURITY` on all five tables, with no policies (see risk #4).

**Enums:** native Postgres types `user_role`, `appointment_type`, `appointment_status`.

---

## 4. Quality gates

| Gate | Backend | Frontend |
|---|---|---|
| Lint / format | `ruff check .`, `ruff format --check .` | `npm run lint`, `prettier --check` |
| Types | `mypy app` | JSDoc typedefs only (no TS) |
| Tests | `pytest -q --cov=app --cov-fail-under=80` against Supabase in a throwaway test schema | `npm test` (Vitest + RTL + MSW) |
| Build | `alembic upgrade head` on empty DB | `npm run build` |
| Hooks / CI | pre-commit locally, GitHub Actions on PRs (from M9) | same |

Per-milestone manual checks:

| Milestone | Manual check |
|---|---|
| M0 | `uvicorn` starts; `/docs` loads; stop the DB and `/health` returns 503. |
| M1 | `psql \d+ appointments` shows every index and constraint; run the seed twice and confirm it's idempotent. |
| M2-M4 | Walk through every endpoint in the Swagger UI; exercise a 409 with two browser tabs. |
| M5-M7 | Click-through of login, search, filter, create, conflict, edit, delete; keyboard-only pass; 375 px viewport. |
| M8 | Compare the dashboard counts with the filtered list totals. |
| M10 | Smoke checklist against the deployed URLs. |

---

## 5. Cross-cutting concerns

**Security and privacy**
- No PII in logs: log method, route template, status, duration and a request id only. Never log bodies, query strings, tokens or names. A test enforces this.
- CORS uses an allowlist from `CORS_ORIGINS`, and the app refuses to start if it contains `*`.
- Secrets live in `.env` (gitignored) with a committed `.env.example`. `JWT_SECRET` must be at least 32 chars. The secret scan runs in pre-commit and CI.
- The login page shows the seeded demo credentials. There is no demo banner in the UI; the README states that all data is synthetic.
- Parameterized queries only (SQLAlchemy). React escapes output. Pydantic validates at the boundary.
- Argon2 password hashing. Identical 401 for unknown user and bad password.
- RLS on, so Supabase's public REST API is closed.
- Security headers via a small middleware (`X-Content-Type-Options`, `Referrer-Policy`), and `vercel.json` headers on the frontend.

**Performance**
- The indexes above, server-side pagination with a 100-row cap, and eager loading of `doctor` to avoid N+1 (asserted in a test).
- A debounced search (300 ms), TanStack Query `staleTime` 30 s and `keepPreviousData` for paging.
- SQLAlchemy pool of 5 + 5 overflow with `pool_pre_ping=True`, deliberately small because the Supabase pooler multiplexes. psycopg `prepare_threshold=None` for transaction pooling.
- The count query is a separate `COUNT(*)` with the same filters.

**Usability and accessibility**
- Loading (skeleton or spinner), empty (with a clear-filters action) and error (with retry) states for every data view.
- A confirm dialog before delete (focus trap, Esc to close, focus returns to the trigger).
- Labeled form controls, `aria-invalid` plus `aria-describedby` for errors, and `role="status"`/`aria-live` for toasts and results counts.
- Full keyboard support, visible focus, and no color-only status (badge text plus icon).
- Mobile layout: the table collapses to cards under about 640 px, and the filters sit in a collapsible panel.
- The browser time zone is shown next to times.

**Error handling and edge cases**
- **Past dates:** rejected on create and on time/doctor change. Status-only edits of past appointments are allowed.
- **Time zones:** the UI converts local to UTC for sending and for day-boundary filters. DST-gap and DST-overlap times are tested in `datetime.js`. The backend rejects naive datetimes.
- **Double booking:** the DB index decides, so races are safe. The API returns 409 and the form shows it on the time field. Cancelled and soft-deleted rows free the slot.
- **Empty filters:** empty `q` is ignored, and no results shows the empty state, not an error. A page beyond the end returns an empty `items` with a correct `total`.
- **Invalid combinations:** `date_from > date_to` is a 422. Unknown sort is a 422.
- **Doctor deactivated:** can't be chosen for new appointments, and existing ones remain visible.
- **Token expiry mid-session:** the next 401 clears the session and redirects to login with a message.
- **Double submit:** the submit button is disabled while the mutation is pending.

---

## 6. Repository layout (target)

```
backend/
  pyproject.toml  alembic.ini  .env.example
  app/ main.py core/{config,errors,logging,security,clock,ratelimit}.py
       db/{base,session}.py models/ schemas/ repositories/ services/ api/v1/
  alembic/versions/   scripts/seed.py
  tests/ unit/ api/ db/ conftest.py
frontend/ src/{api,components,pages,hooks,utils,__tests__}  vite.config.js ...
docs/ ARCHITECTURE.md DECISIONS.md WORKLOG.md DEPLOYMENT.md
.github/workflows/ci.yml   .pre-commit-config.yaml
.claude/settings.json   CLAUDE.md   README.md   .gitignore
```

Layering: routers parse and authorize and call **services**, which hold business rules, own the transaction and raise domain exceptions. **Repositories** hold all SQL and return models. Domain exceptions are translated to the error shape in `core/errors.py`.

---

## 7. Extras: ranked by value vs effort

| Extra | Value | Effort | Verdict |
|---|---|---|---|
| **Status quick-change** (inline select in table) | High: the most common daily action | Low: reuses PATCH | **Include** |
| **Dashboard counts** (tiles by status) | Medium-high: makes the demo feel real | Low: one `GROUP BY` endpoint | **Include** |
| **Calendar day view** (agenda list per doctor and day) | High for a doctor workflow | Medium: reuses the list endpoint with a date range, no calendar library | **Include** (as a simple agenda, not a grid) |
| CSV export | Low-medium | Low, but CSV formula injection and PII export need care | Skip (stretch only) |
| Supabase Auth login | Low: duplicates our JWT, and RLS plus the Supabase client change the architecture | High | **Skip** |

---

## 9. Dependencies requiring your approval (one-time, per CLAUDE.md)

- **Backend runtime:** `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2`, `psycopg[binary]`, `alembic`, `pydantic>=2` (with email support), `pydantic-settings`, `pyjwt`, `pwdlib[argon2]`.
- **Backend dev:** `pytest`, `pytest-cov`, `httpx`, `ruff`, `mypy`, `pre-commit`.
- **Frontend runtime:** `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `react-hook-form`.
- **Frontend dev:** `vite`, `@vitejs/plugin-react`, `vitest`, `jsdom`, `@testing-library/{react,user-event,jest-dom}`, `msw`, `eslint` (+ react plugins), `prettier`.
- **Tooling outside the repo:** `uv`, Node 20+, and a Supabase project (free tier).

## 10. Remaining assumptions (tell me if wrong)
- The log file in CLAUDE.md is `docs/WORKLOG.md`.
- "Hooks" means git pre-commit hooks, plus an optional Claude Code hook.
- Seeded demo accounts: one admin and a doctor account per seeded doctor, with documented demo passwords.
- Browser time zone is the display time zone (no per-clinic time zone setting).
- No patients table: `patient_name` is a free-text field, as in your spec.
- "User" in "sign-in is optional" means a visitor/patient. Signed-in accounts are staff roles (`admin`, `doctor`), so signing in gives a pre-filled booking form for a doctor, plus the ability to manage appointments. There are no patient accounts.
- A hospital is just a name (no address or city, no hospital-level users). Tell me if you want more fields, e.g. a city for search.
- Doctor-to-hospital links are seeded, not editable through the API in this version.
- The in-process rate limiter replaces a dependency such as `slowapi`.

## Verification (end-to-end, after all milestones)
1. Set `backend/.env` for Supabase, then `alembic upgrade head` and `python -m scripts.seed`.
2. Run the backend gate and the frontend gate (section 4). Both must be green with backend coverage >= 80%.
3. Start both apps. First, **without signing in**, book an appointment (hospital, doctor, slot) and confirm the reference page appears and the list pages require sign-in. Then log in as the admin and as a doctor (booking is pre-filled). Create an appointment, then try the same slot again (expect the conflict message). Edit it, change its status inline, delete it with confirmation, search for a partial name and combine filters. Check the dashboard counts and the day view.
4. Confirm that the uvicorn output contains no patient names.
5. After deployment, run the smoke checklist (M10) and confirm CORS only works from the Vercel origin.
