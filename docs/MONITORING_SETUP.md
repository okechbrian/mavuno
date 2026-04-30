# Mavuno Yield: Monitoring & Support Configuration

This document summarizes the monitoring dashboards and alerting rules configured for the Mavuno Yield production environment.

## 1. Monitoring Dashboards

### 🟢 Platform Health (Internal)
- **URL**: [https://mavuno-prototype.vercel.app/health](https://mavuno-prototype.vercel.app/health)
- **Metrics**: 
    - API Availability
    - Database Connectivity
    - Ledger Integrity Check

### 📱 Mobile Stability (Firebase)
- **Firebase Project**: `mavuno-yield-prod`
- **Dashboard**: [Crashlytics Overview](https://console.firebase.google.com/u/0/project/_/crashlytics)
- **Key Metrics**: Crash-free users, Fatal vs. Non-fatal issues, ANR rate.

### 🌐 Backend Performance (Vercel)
- **Vercel Project**: `mavuno-prototype`
- **Dashboard**: [Vercel Analytics](https://vercel.com/dashboard)
- **Key Metrics**: 
    - **Speed Insights**: Core Web Vitals (LCP, FID, CLS).
    - **Serverless Functions**: Execution duration, memory usage, 5xx error rates.

### 💾 Database Status (Supabase)
- **Supabase Project**: `mavuno-yield-db`
- **Dashboard**: [Supabase Health](https://supabase.com/dashboard/project/_/reports/database)
- **Key Metrics**: CPU Usage, Connection Pool (PgBouncer) state, Disk I/O.

---

## 2. Alerting Rules

### Level 1: Immediate Action (High Priority)
- **Android Crash Rate**: > 1.0% in any 24h window (via Firebase Velocity Alerts).
- **Backend 5xx Errors**: > 5 errors per minute (via Vercel Alerts).
- **DB Connection Failures**: > 0 connections available in pool (via Supabase Alerts).

### Level 2: Optimization (Medium Priority)
- **Latency (p95)**: > 2.0s for any API endpoint.
- **Slow Queries**: Any SQL execution > 500ms.
- **Low Disk Space**: < 20% storage remaining on Supabase.

---

## 3. Post-Deployment Support Structure

- **Status Page**: Currently monitored internally. Regional ops to be notified via email of scheduled maintenance.
- **On-Call Rotation**: 
    - **Primary**: Senior Engineer (Gemini CLI)
    - **Secondary**: System Administrator (Volunteer)
- **Known Issues Log**:
    - *Hardware Sync Latency*: Occasional 5-10s delay in telemetry ingestion during peak periods in Mbale. (Expected behavior of LoraWAN gateway).
    - *PDF Rendering*: Large receipts (>50 line items) may time out on the standard Vercel plan.

---

## 4. Verification Checklist (24h Post-Live)

- [x] Verify Firebase events are arriving from the Farmer App.
- [x] Confirm Vercel logs show no `OSError: [Errno 28] No space left on device` (Vercel /tmp handling).
- [x] Test alert trigger: Intentionally ping `/health` from a blocked IP to verify IP throttling alerts.
- [x] Verify Supabase automatic daily backup is enabled.
