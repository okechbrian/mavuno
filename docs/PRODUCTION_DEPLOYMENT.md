# Mavuno Yield: Final Production Deployment Guide

This guide provides the step-by-step instructions required to deploy the complete Mavuno Yield platform to production. This covers the Backend (FastAPI), Database (PostgreSQL), and Android Mobile ecosystem (Farmer, Agent, and Buyer apps).

---

## 1. Pre-Deployment Verification Checklist

Before initiating the deployment, verify the following:

- [ ] **Code Scub Complete**: Zero references to "ECT", "kWh", or "Solar Pump" remain in code or logs.
- [ ] **GitHub Secrets**: All secrets listed in `docs/CICD_SETUP.md` are configured in the repository.
- [ ] **PostgreSQL Status**: Production Supabase instance is active and accessible via `PROD_DATABASE_URL`.
- [ ] **Environment Variables**:
    - `HMAC_SECRET` is set to a cryptographically secure 48-char string.
    - `PUBLIC_BASE_URL` is set to the final production domain.
    - `GROQ_API_KEY` is configured for the AI Advisor.
- [ ] **Keystore Verified**: `mavuno-release.jks` is generated and its Base64 string is stored in GitHub Secrets.

---

## 2. Database Deployment & Seeding

The database must be initialized before the backend goes live.

### Step 2.1: Run Migrations
Run the Alembic upgrade locally (or via the CI/CD pipeline by pushing a tag):
```bash
# Locally
export DATABASE_URL="your-production-postgres-url"
alembic upgrade head
```

### Step 2.2: Execute Production Seeding
Populate the production database with mandatory system data (Training modules, default hubs):
```bash
python scripts/prod_seed.py
```

### Step 2.3: Verify Data Integrity
Connect to your Postgres instance (via Supabase SQL Editor) and verify:
- `users` table contains the `admin` account.
- `training_modules` contains TM-01 through TM-04.
- `yield_priorities` table exists with the updated schema (kg_allocated, aggregation_point).

---

## 3. Backend Deployment (Vercel)

The backend is deployed automatically via the `Backend CI/CD` workflow.

### Step 3.1: Trigger Deployment
Push a version tag to the `main` branch to trigger a production build:
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Step 3.2: Verify Health
- Visit `https://api.mavuno.app/health` (should return `{"ok": True}`).
- Check the Vercel logs for any "ModuleNotFoundError" or "Database Connection Failed" errors.
- **End-to-End Test**: Log in to the production dashboard using the admin credentials.

---

## 4. Android App Deployment (Play Store)

### Step 4.1: Upload Artifacts
1. Download the signed AABs from the GitHub Action "release" job.
2. Log in to the [Google Play Console](https://play.google.com/console).
3. Navigate to each app (Farmer, Agent, Buyer) and upload the AAB to the **Internal Testing Track**.

### Step 4.2: Store Listing & Privacy
- **Privacy Policy**: Use the template at `docs/PRIVACY_POLICY.md` (ensure BLE and Location disclosures are clear).
- **Screenshots**: Upload the high-resolution device frames from the `/assets/marketing` folder.
- **Data Safety**: Disclose that the app collects Soil Data (Biometrics) and Location (GPS verification).

### Step 4.3: Staged Rollout
Submit for Production review with the following staged rollout:
- **Day 1**: 5% of users (Internal pilot group).
- **Day 3**: 20% (Region-specific expansion).
- **Day 7**: 100% (National rollout).

---

## 5. Post-Deployment Monitoring & Alerts

### Step 5.1: Firebase Monitoring
- **Crashlytics**: Set alert threshold to >1% crash-free session drop.
- **Analytics**: Monitor the `issue_priority` and `redeem_priority` events to track protocol velocity.

### Step 5.2: Backend Monitoring
- **Vercel Alerts**: Enable email notifications for 5xx status codes.
- **Supabase Logs**: Monitor for slow queries on the `immutable_ledger` table.

---

## 6. Rollback Procedures

### Backend Rollback (Vercel)
If a critical API failure occurs:
1. Go to Vercel Project Dashboard.
2. Select the previous successful deployment.
3. Click **Instant Rollback**.

### Database Rollback (Alembic)
If a schema change causes data corruption:
```bash
alembic downgrade -1
```
*Note: Always perform a manual backup in Supabase before running migrations.*

### Android Rollback
Google Play does not support direct rollbacks. To "rollback":
1. Revert the code to the previous stable tag.
2. Increment the `versionCode` in `build.gradle.kts`.
3. Build and upload a new AAB to the production track for immediate review.

---

## Final Review Complete
**Status**: Ready for Execution.
**Lead Engineer**: Gemini CLI Agent
**Date**: April 28, 2026
