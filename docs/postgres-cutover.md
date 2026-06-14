# Conwo — PostgreSQL Cutover & DevOps Handoff

Conwo migrated from per-instance SQLite files to **one PostgreSQL database**
(`wis_conwo`). This is required because production runs **multiple load-balanced
replicas with no shared writable disk** — SQLite files can't be shared/refreshed
across replicas. All five former SQLite stores (auth, conversations, traces, the
Jira mirror, the PMS config catalog) are now tables in `wis_conwo`.

This doc is the cutover runbook + the operational requirements for DevOps.

---

## 1. Environment variables (required)

The backend (and the cron/ingest scripts) connect to PostgreSQL via these:

| Var | Prod value | Notes |
|-----|-----------|-------|
| `CONWO_DB_HOST` | `servicesdb3.moveinsync.com` | RDS endpoint |
| `CONWO_DB_PORT` | `5432` | |
| `CONWO_DB_NAME` | `wis_conwo` | dedicated DB |
| `CONWO_DB_USER` | `wis_conwo` | |
| `CONWO_DB_PASSWORD` | **secret — provided separately** | never commit; set via secret store |
| `CONWO_DB_SSLMODE` | `require` | RDS needs TLS (see §6) |
| `CONWO_DB_POOL_MIN` | `1` | |
| `CONWO_DB_POOL_MAX` | `10` | per replica — see §5 |
| `CONWO_RUN_MIGRATIONS` | `true` (default) | see §3 |
| `CONWO_DEV_LOGIN` | **never set in prod** | ⚠️ DEV-ONLY: enables email/password bypass (`POST /auth/dev-login` + login-page box). MUST NOT be set in production — Google OAuth is the only permitted login path in prod. |

Existing non-DB env vars are unchanged (`ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID`,
`ALLOWED_ORIGINS`, `JIRA_*`, `PMS_*`, `TRACE_USER_HASH_SALT`). Full list in `.env.example`.

> The DB password was shared in a chat during setup — please **rotate it** after go-live.

---

## 2. Persistent volume (`CONWO_DATA_DIR`)

`wiki/` and `raw/` are still file-based. Set **`CONWO_DATA_DIR=/app/data`** and mount
a persistent volume at **`/app/data`** — the app then reads/writes
`/app/data/wiki` and `/app/data/raw` (instead of the repo root). Sizing: ~5 GB is
plenty (real usage ~120 MB).

- **Seeding is automatic — no init container.** The image bakes the `wiki/`
  baseline (~700 KB); on first boot, if the volume's `wiki/` is empty, the app
  copies the baseline in (`api.py` `_seed_wiki_if_empty`). It never overwrites an
  already-populated volume. `raw/` subdirs (feedback, uploads, logs) are created
  on demand.
- The old `.sqlite` files are **not** on this volume and are no longer needed at
  runtime (data is in Postgres). Keep an archived copy for rollback (§7).

**Volume type vs replicas:**
- **Single replica (gp3 / ReadWriteOnce):** fine — the StatefulSet pattern (PVC at
  `/app/data`) works as-is.
- **Multiple replicas:** gp3/EBS is single-attach, so each pod gets its own copy →
  `wiki/` ingests and `raw/feedback/` writes would NOT be shared across pods. For
  >1 replica use **EFS (ReadWriteMany)** for `/app/data` instead. (The RDS is shared
  regardless, so auth/chat/traces/tickets/configs stay consistent either way.)

> Follow-up (not blocking): the in-memory wiki index is per-replica, so after an
> ingest the writing pod is fresh and others are stale until they rebuild.
> Acceptable for the pilot.

---

## 3. Schema migrations (automatic)

Schema is created/updated at backend startup by the FastAPI lifespan
(`backend.db.init_db()`) from `migrations/postgres/*.sql`. It is **idempotent and
advisory-locked**, so concurrent replica boots are safe.

- Default (`CONWO_RUN_MIGRATIONS=true`): every replica runs migrations on boot (safe).
- Optional: set `CONWO_RUN_MIGRATIONS=false` on replicas and run migrations once as
  a separate init/job container (`python -c "from backend import db; db.init_pool(); db.init_db()"`).

**One prerequisite:** the `pg_trgm` extension (fuzzy config lookup). `050_configs.sql`
runs `CREATE EXTENSION IF NOT EXISTS pg_trgm;`. If the `wis_conwo` role lacks
`CREATE EXTENSION`, run it once as a privileged user before first deploy:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## 4. First-time data load (one-time ETL)

To carry existing data from the SQLite files into Postgres (run once, from a host
that has both the `.sqlite` files and DB access):

```bash
venv/bin/python scripts/migrate_sqlite_to_postgres.py --all
venv/bin/python scripts/migrate_sqlite_to_postgres.py --all --verify-only   # row-count check
```
Idempotent (`ON CONFLICT DO NOTHING`). Migrates auth, conversations, traces,
tickets (~37k), configs, and the classifier/link tables.

Going forward, the Jira mirror is kept fresh by the existing cron
(`scripts/jira_daily_sync.py`) — now writing to Postgres. It needs the same
`CONWO_DB_*` env. Run it as its own container / k8s CronJob.

---

## 5. Connection pool sizing

`wis_conwo` is dedicated to Conwo, so the pool size is our choice. Each replica
opens up to `CONWO_DB_POOL_MAX` (default 10) connections. Total connections ≈
`replicas × CONWO_DB_POOL_MAX` + cron. Keep that under the RDS instance's
`max_connections`. Start at 10/replica; tune if needed.

---

## 6. TLS

`CONWO_DB_SSLMODE=require` is assumed. If RDS requires server-cert verification,
set `verify-full` and provide the RDS CA bundle (mount it and add `sslrootcert`
to the connection — tell me and I'll wire it into `backend/db.py`).

---

## 7. Rollback

The cutover commits are additive and the old `.sqlite` files are untouched. To
roll back: redeploy the pre-migration image/commit (everything before the Phase 0
commit). Any conversations/traces written to Postgres after cutover would not be
in the SQLite files — acceptable for an internal pilot. Don't delete the `.sqlite`
files until you're confident.

---

## 8. Open items to confirm with DevOps

- Postgres major version (assumed **15** — pins the local Docker image; confirm RDS).
- `pg_trgm` available / creatable on the RDS (§3).
- Shared RWX volume for `wiki/` + `raw/feedback/` (§2).
- Where the cron pipeline runs + that it gets `CONWO_DB_*` (§4).
- Rotate the DB password (§1).
