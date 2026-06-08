# Mavuno Protocol - Project Instructions

## Overview
Mavuno is a FastAPI-based agricultural operating system designed for smallholder farmers in Uganda. It uses a "Dirt-to-Ledger" protocol integrating IoT telemetry with an immutable SQLite/Postgres ledger.

## Core Mandates
- **PII Protection:** Never log or share raw Phone Numbers or Farm IDs. Always use `app.crp._redact_pii()`.
- **Ledger Integrity:** All state-changing actions (Offers, Payments, Chat, Social) MUST write to the ledger via `app.ledger.write()`.
- **Role-Based Access:** 
  - Farmers see only their own data.
  - Buyers see their own data and open marketplace offers.
  - Agents have audit access to all records.

## Recent Fixes & Critical Gaps
- **Buyer Dashboard:** Requires the `/api/buyers` route (restored in `app/main.py`).
- **Verified Harvest:** Depends on `Pillow` for WebP processing. Ensure `Pillow==11.0.0` is installed.
- **Vercel Persistence:** SQLite in `/app/data/mavuno.db` is ephemeral on Vercel. Migrations to Neon/Postgres are planned for Q2.

## Development Workflow
- **Migrations:** Use Alembic for all schema changes.
- **Dashboards:** Static HTML files in `app/static/` using Vanilla JS + Lucide icons.
- **USSD:** Simulator available at `/phone`. Gateway for AfricasTalking at `/ussd/gateway`.

## Q1 Stabilization Tasks (Completed)
- [x] Restore missing `/buyers` routes.
- [x] Add missing `Pillow` dependency.
- [x] Implement Point-in-Time recovery scripts for SQLite backups.
- [x] Fix 404 errors on "Verified Gallery" with failsafe rendering.

## Q2 Intelligence & Mobile (In Progress)
- [x] Mavuno ML v1: Predictive Yield & Maturity modeling.
- [x] Geospatial Supply Clusters (KMeans optimization for collection).
- [x] Unified Push Notification Engine (Web + SMS Fallback).
- [x] Hardware Audit Log (Sentinel Node firmware & health tracking).
- [ ] Native Mobile App (React Native bridge to FastAPI).
