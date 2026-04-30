# PostgreSQL & Alembic Setup for Mavuno Yield

This document outlines how to set up the production database for Mavuno Yield.

## 1. Database Hosting (Supabase)

We recommend using **Supabase** for PostgreSQL hosting.

1.  Create a project at [supabase.com](https://supabase.com).
2.  Navigate to **Project Settings > Database**.
3.  Copy the **Connection String** (use the "Transaction" mode with port 6543 for pooling if using Vercel).
4.  Add the `DATABASE_URL` to your environment variables.

## 2. Environment Variables

Ensure the following is set in your `.env` or CI/CD platform:

```bash
# Example for Supabase (Transaction Pooler)
DATABASE_URL=postgresql://postgres:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

## 3. Database Migrations (Alembic)

Mavuno uses Alembic for schema management.

### Initialize/Sync Database
To apply all migrations to a new database:
```bash
alembic upgrade head
```

### Create a New Migration
If you modify `app/models.py`, generate a new migration:
```bash
alembic revision --autogenerate -m "Describe your changes"
```

### Rollback
To undo the last migration:
```bash
alembic downgrade -1
```

## 4. Initial Seeding

To populate the database with default training modules and demo users:
```bash
python scripts/prod_seed.py
```

## 5. Development Fallback

If `DATABASE_URL` is not provided, the application defaults to a local SQLite database at `app/data/mavuno.db`.
