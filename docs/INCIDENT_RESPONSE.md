# Mavuno Yield: Incident Response Runbook

This document outlines the procedures for identifying, escalating, and resolving production incidents for the Mavuno Yield platform.

## 1. Escalation Path

| Level | Contact | Role | Response Time |
| :--- | :--- | :--- | :--- |
| **P1** | Lead Engineer (Gemini CLI) | Infrastructure & Backend | < 30 mins |
| **P2** | Product Designer | UI/UX & Mobile Flow | < 2 hours |
| **P3** | Regional Operations | Hardware Hub Verification | < 4 hours |

---

## 2. Common Incident Runbooks

### 2.1 Backend 5xx Errors / Downtime
*   **Detection**: Vercel Alert or Health Check Failure.
*   **Immediate Action**: Check Vercel Logs for stack traces.
*   **Resolution**:
    1. If a recent deployment caused it: **Execute Instant Rollback** via Vercel Dashboard.
    2. If DB connection error: Check Supabase connection pooler status.
    3. If rate-limited: Verify Groq API limits.

### 2.2 Database Connection Issues
*   **Detection**: Supabase Alert (Connection Pool Exhaustion).
*   **Immediate Action**: Check Supabase "Database Health" dashboard.
*   **Resolution**:
    1. Ensure `pgbouncer=true` is in the `DATABASE_URL`.
    2. Check for long-running transactions (Idle in transaction).
    3. Kill offending queries via Supabase SQL Editor if necessary.

### 2.3 Android Crash Spike
*   **Detection**: Firebase Crashlytics Alert (>1% crash rate).
*   **Immediate Action**: Identify the "Top Issue" in Crashlytics.
*   **Resolution**:
    1. If related to a specific Android OS version or device, toggle off affected feature via Remote Config (if applicable).
    2. Patch and release new version; increment `versionCode` and promote to Production track in Play Store.

### 2.4 Ledger Integrity Failure
*   **Detection**: `/ledger/verify` endpoint returns `false`.
*   **Immediate Action**: Freeze all marketplace transactions.
*   **Resolution**:
    1. Identify the first broken hash in the chain.
    2. Investigate unauthorized database writes (check Supabase audit logs).
    3. Restore from point-in-time backup if corruption is detected.

---

## 3. Rollback Procedures

### Vercel Instant Rollback
1. Navigate to [Vercel Project Dashboard](https://vercel.com).
2. Go to **Deployments**.
3. Locate the last stable deployment (green).
4. Click the "..." menu and select **Instant Rollback**.

### Alembic Database Downgrade
If a migration corrupted the schema:
```bash
# Move back one version
alembic downgrade -1
```

### Play Store Rollout Pause
1. Go to [Google Play Console](https://play.google.com/console).
2. Select the app and go to **Production**.
3. Under "Releases", click **Halt Rollout** to stop the update from reaching more users.
