# Design Decisions

Key trade-offs for the Doctor Appointment System demo. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full plan.

1. **Soft delete vs hard delete**
   - Chosen: soft delete (`deleted_at`), so mistakes are recoverable and there is an audit trail.
   - Alternatives: hard delete (simplest, no filter on every query, but irreversible); status-only `cancelled` (but cancel and delete mean different things).
   - Consequences: every query needs `deleted_at IS NULL`, which is why the indexes are partial. A restore endpoint is not in scope.
2. **Plain SQLAlchemy over the Supabase client**
   - Chosen: connect to Supabase as ordinary Postgres through the pooled string, with Alembic migrations.
   - Alternatives: supabase-py or PostgREST (less code, but bypasses our service layer and ties us to Supabase); a direct non-pooled connection (simpler, but IPv6-only and connection-limited).
   - Consequences: portable to any Postgres, and the layered architecture is intact. We must enable RLS to close the REST API, use `prepare_threshold=None`, and use the session-pooler URL for migrations.
3. **Partial unique index + fixed 30-min slots vs app-level check or exclusion constraint**
   - Chosen: DB-enforced uniqueness on `(doctor_id, start_time)` for active rows, plus aligned slots, and a 409 from the `IntegrityError`.
   - Alternatives: check-then-insert in the service (race-prone); an `EXCLUDE USING gist` constraint on time ranges (supports variable durations, but needs `btree_gist` and more complex tests).
   - Consequences: race-free and simple. Slot length is fixed, and 45-minute-offset time zones are awkward. Variable durations would need a migration to the exclusion constraint.
4. **Own JWT auth with a users table vs Supabase Auth, and browser token storage**
   - Chosen: users + argon2 + 30-min HS256 JWT in `sessionStorage`.
   - Alternatives: Supabase Auth (more features, but a second source of truth and ties the API to Supabase); an httpOnly cookie (safer against XSS, but cross-site Vercel to Render needs SameSite=None, CSRF protection and more setup).
   - Consequences: XSS exposure is mitigated, not eliminated. There are no refresh tokens, so users re-login after 30 minutes.
5. **Sync SQLAlchemy and native Postgres enums**
   - Chosen: sync SQLAlchemy 2 with psycopg 3 (FastAPI runs the sync endpoints in a threadpool), and native enum types.
   - Alternatives: async SQLAlchemy with asyncpg (better concurrency, but needs `statement_cache_size=0` on the pooler and async fixtures); `text` + `CHECK` instead of native enums (easier to add values).
   - Consequences: simpler code and tests, and enough for a demo. Adding an enum value needs a migration (`ALTER TYPE ... ADD VALUE`), and moving to async later would touch the repositories.

6. **Anonymous booking with optional sign-in**
   - Chosen: `POST /appointments`, `GET /doctors`, `GET /hospitals` and availability are public. Sign-in (staff roles `admin` and `doctor`) is optional and gives a pre-filled booking form plus list/edit/delete.
   - Alternatives: require an account for every booking (more friction for a public e-channeling flow); patient accounts (more scope: registration, "my bookings").
   - Consequences: a public write endpoint, so a per-IP in-process rate limiter, forced `status = scheduled` and `created_by = NULL` for anonymous bookings. Anonymous patients cannot view or cancel their booking afterwards, and no contact details are stored.
7. **Doctors visit many hospitals (many-to-many)**
   - Chosen: a `doctor_hospitals` link table, and `appointments.hospital_id` with a composite foreign key `(doctor_id, hospital_id)`. The anti-double-booking index stays on `(doctor_id, start_time)` only.
   - Alternatives: `doctors.hospital_id` (wrong for a public multi-hospital system, since a doctor visiting two hospitals would need duplicate rows); a free-text hospital name on the appointment (no integrity, no filtering).
   - Consequences: one extra table and join for the doctor and hospital pickers. A doctor cannot be booked at two hospitals at the same time. Links are seeded, with no editing API yet.
8. **Tests run on Supabase in a throwaway schema**
   - Chosen: one Supabase project for the app and the tests. Tests create and drop a `test_<random>` schema through the session pooler, and abort if the active schema is not a test schema.
   - Alternatives: a separate test database or project (full isolation from real data); running tests in the real schema (rejected: tests run destructive downgrades).
   - Consequences: nothing extra to install, and CI needs only a secret. Tests are slower (network) and the free tier can pause an idle project. The schema guard is the only protection for real data, so it has its own test. Extensions such as `pg_trgm` are database-wide and shared.
