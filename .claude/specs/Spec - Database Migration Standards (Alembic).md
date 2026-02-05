---
uid: SPEC-DB-001
title: Spec - Database Migration Standards (Alembic)
status: active
created: 2026-02-03T23:30:00+02:00
pinned: true
tags:
  - database
  - alembic
  - migration
  - schema
  - governance
modified: Tue, 3rd February 2026 23:55
---

# Spec: Database Migration Standards (Alembic)

## 1. The Philosophy: Immutable Evolutionary History

In the Soma ecosystem, the database schema is not a static artifact; it is the **genetic code** of the Organism. Just as biological DNA updates must be transcribed precisely to avoid mutation failures, database changes must be version-controlled, linear, and reproducible.

**The Golden Rule:**

> **The Database Schema MUST only be modified via Alembic Migrations.** > Manual execution of DDL statements (CREATE, ALTER, DROP) via SQL clients (DBeaver, PGAdmin) is **STRICTLY FORBIDDEN** in any environment beyond local scratchpads.

## 2. The Mandate (Zero Drift)

To prevent incidents like `EVT-START-FAIL-01` (Migration Block) and `EVT-50N42` (Config Drift), the following rules apply to all services (`InGress`, `InGest`, `OmegaKG`, `memOS`):

1. **Code First, DB Second:** The `models.py` (SQLAlchemy/SQLModel) definitions are the Source of Truth. The database is a reflection of the code, not the other way around.
2. **One Tool to Rule Them All:** `Alembic` is the sole authorized mechanism for applying schema changes.
3. **Commitment to Version Control:** Every migration script (`versions/*.py`) must be committed to Git. A PR that changes `models.py` **MUST** include the corresponding Alembic revision file.

## 3. The Workflow (Evolutionary Cycle)

### Step 1: Mutation (Modify Code)

Modify your SQLAlchemy/SQLModel classes in `src/{service}/models.py`.

### Step 2: Transcription (Generate Revision)

Use Alembic to auto-detect the delta between your code and the current database state.

```
# From the service directory (e.g., InGress)
poetry run alembic revision --autogenerate -m "describe_biological_change"
```

### Step 3: Audit (Review Script)

**CRITICAL:** Open the generated file in `alembic/versions/`.

- Verify that it only changes what you intended.
- Check for accidental drops (e.g., dropping a table because the model wasn't imported in `env.py`).

### Step 4: Expression (Apply Upgrade)

Apply the change to your local "Organism".

```
poetry run alembic upgrade head
```

### Step 5: Persistence (Git Commit)

Commit both the model change and the migration file together.

## 4. The Constraints (Mirmir Protocols)

### CST-DB-001: The "No Ghost Tables" Rule

- **Constraint:** Every table in the database must have a corresponding model in the codebase.
- **Enforcement:** Periodic forensic audits will drop any table not tracked by Alembic.

### CST-DB-002: The "Sync Driver" Ban

- **Constraint:** While Alembic runs synchronously (during startup), the application code must **NEVER** use synchronous drivers for runtime queries (per `CST-ASYNC-001`).
- **Clarification:** It is acceptable for `alembic.ini` to use a sync `psycopg2` driver, provided the main app uses `asyncpg`.

### CST-DB-003: The "Down Revision" Requirement

- **Constraint:** Every `upgrade()` function must have a valid, non-destructive `downgrade()` counterpart whenever logically possible.
- **Reasoning:** This allows the Organism to heal (rollback) if a mutation proves fatal.

## 5. Troubleshooting & Recovery

### Scenario: "Divergent Heads"

- **Symptom:** Two developers created migrations at the same time.
- **Fix:**
    ```
    poetry run alembic merge heads -m "merge_divergent_evolution"
    poetry run alembic upgrade head
    ```

### Scenario: "Validation Failed / Target Database is not up to date"

- **Symptom:** `start_ecosystem.ps1` fails with Exit Code 1.
- **Fix:**
    1. Check `alembic_version` table in DB: `SELECT * FROM alembic_version;`
    2. Check `alembic history` in CLI.
    3. If the DB is "ahead" of code (rare): You are on an old branch. Pull `beta`.
    4. If the DB is "behind" code: Run `poetry run alembic upgrade head`.
