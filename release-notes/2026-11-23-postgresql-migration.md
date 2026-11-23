# PostgreSQL Migration — 2026-11-23

## Summary

The application now supports both SQLite and PostgreSQL. SQLite remains the
default for new local setups; PostgreSQL can be selected with `DATABASE_URL`.
The existing local SQLite data was copied to PostgreSQL and verified. No
database files, passwords, or other credentials are included in this release
note or the repository.

## What changed

- Added Alembic and the Psycopg 3 PostgreSQL driver.
- Added an initial Alembic schema migration for users, products, orders, order
  items, tickets, ticket messages, and ticket status history.
- Made SQLAlchemy engine setup dialect-aware, retaining SQLite's
  thread-compatible connection setting and supporting PostgreSQL URLs.
- Removed schema creation and ad hoc ticket-number changes from application
  startup. Schema changes are now applied explicitly with
  `python -m app.database.init_db`.
- Added a safety check for existing SQLite databases without Alembic history.
  After backing up and verifying such a database, mark its existing schema
  with `python -m alembic stamp head` before applying migrations.
- Added `backend/migrate_sqlite_to_postgres.py` to copy a verified SQLite
  backup into an empty PostgreSQL database. The utility checks the source
  integrity and foreign keys, preserves IDs, copies data in dependency order,
  verifies row counts and content hashes in a transaction, and resets
  PostgreSQL ID sequences. It refuses to overwrite a populated target.
- Updated root and backend documentation with PostgreSQL configuration,
  migrations, safe data-copy instructions, and SQLite/PostgreSQL switching
  behavior.

## Migration verification

The verified SQLite source contained:

| Table | Rows |
|---|---:|
| `users` | 11 |
| `products` | 15 |
| `orders` | 30 |
| `order_items` | 63 |
| `tickets` | 22 |
| `ticket_messages` | 40 |
| `ticket_status_history` | 8 |

The PostgreSQL copy matched these counts and the source content hashes for all
seven application tables. The SQLite backup passed `PRAGMA integrity_check`
with no foreign-key violations. PostgreSQL Alembic schema validation reported
no outstanding differences, and its application tables and ID sequences were
checked after copying.

## Application and AI verification

- The PostgreSQL-backed API health endpoint returned HTTP 200.
- Support login and a support-only endpoint succeeded.
- The orders endpoint returned all 30 migrated orders.
- Live authenticated calls to the Ollama-backed ticket-preview, product
  lookup, product-recommendation, and order-lookup Assistant features returned
  HTTP 200 with the expected response fields.
- The configured Ollama service was reachable and the `llama3.2:1b` model was
  available during the live checks.
- Backend test suite: **40 passed**.
- `pip check`: no broken requirements.

AI features require Ollama and the configured model to be running locally.

## Switching databases

Set `DATABASE_URL` in the private `backend/.env`, apply migrations, then
restart the backend. The running app uses one configured database at a time.
Switching the URL does not synchronize data between SQLite and PostgreSQL.
Keep local environment files and database backups private and out of source
control.

## Repository

Implementation commit: `f1d253d` — **Add PostgreSQL database migration**.
