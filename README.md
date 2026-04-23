# Mavuno - Prototype v2

**Live Prototype:** [https://mavuno-prototype.vercel.app](https://mavuno-prototype.vercel.app)

This is the interactive prototype for the **Future Makers Hackathon 2026**. It demonstrates how soil data, when linked to an immutable SQLite ledger and cryptographically secured tokens, can power Uganda to a $500B economy by unlocking smallholder agricultural finance.

## Getting Started

Because standard Python installations can have conflicting dependency packages, we have provided a foolproof startup script.

1. Open your terminal.
2. Navigate into the prototype directory:
   ```bash
   cd mavuno-prototype
   ```
3. Make the startup script executable (if it isn't already):
   ```bash
   chmod +x start.sh
   ```
4. Run the server:
   ```bash
   ./start.sh
   ```

The server will automatically start on **Port 8001** (to avoid conflicts with any other running apps).
Open your browser and visit: **http://localhost:8001**

## Features Overview

### 1. Multi-User Login Portal
The root address (`http://localhost:8001`) now features a secure, multi-role landing page where:
- **Agents** can log into the main operations cockpit (Password: `mavuno2026`).
- **Farmers** can log in using their Farm ID (e.g. `UG-MBL-0001`) or phone number and PIN (`1234`) to access their personalized dashboard, YPS score, and the AI agronomist.
- **Buyers** can log in using their Buyer ID (e.g. `BY-001`) or phone number and PIN (`1234`) to view a live, filtered marketplace of crops matching their pre-verified floor prices.

### 2. The Agent Cockpit (Decision Support System)
The main dashboard serves as an operations center for SACCOs and Co-ops. It features:
- **Biometric Analytics:** Live Nitrogen, Phosphorus, and Potassium (NPK) sparklines.
- **Credit Health Gauges:** Visual indicators of a farmer's credit-worthiness based on their Yield Probability Score (YPS).
- **Macro-Analytics:** The left sidebar displays real-time Credit Velocity, System Risk, and Ledger Verification status.

### 2. Buyer Network & CRP Marketplace
The system operates a live Community Resource Platform (CRP) marketplace connecting smallholders with pre-verified institutional off-takers.
- **The Buyer Network List:** Visible in the left sidebar, showing registered SACCOs and regional cooperatives.
- **How to Onboard:** Click the **"+ Onboard Buyer"** button in the sidebar. Enter the institution's name, their operating region, floor price, and the crops they purchase. Once registered, they are instantly available to be matched with farmers on the USSD interface via the CRP engine.

### 3. Multi-Language USSD Simulator & CRP Advisor
Visit **http://localhost:8001/phone** to simulate the farmer's experience on a 2G feature phone.
- The simulator is fully functional in both **English and Luganda**.
- Farmers can check market prices, sell produce (which auto-matches against the Buyer Network), and ask the CRP AI Agronomist for specific advice based on their live soil readings.

### 4. Dirt-to-Ledger IoT Telemetry (The 7 Crucial Signals)
Mavuno is not just software; it is an IoT-integrated protocol. Real physical hardware in the field captures 7 distinct environmental and agronomic signals:
1. **Soil Moisture (%)**
2. **Soil Temperature (°C)**
3. **Nitrogen (mg/kg)**
4. **Phosphorus (mg/kg)**
5. **Potassium (mg/kg)**
6. **Ambient Humidity (%)**
7. **Rainfall (mm)**

**How to deploy this practically and affordably?**
Please read the [Hardware & Practical Deployment Strategy](docs/HARDWARE_DEPLOYMENT.md) document to see how we use **Sentinel Nodes** to drop the hardware cost to **~$4.00 per farmer**, and how we use shared solar hubs to distribute water without putting farmers in asset debt.

**How to demo this to judges:**
- Click the golden **"Ping Sensor"** button on any farm card in the dashboard.
- This simulates the physical hardware waking up and transmitting a payload of these 7 signals over 2G/GSM to the `/sensor/telemetry` endpoint.
- Watch as the Nitrogen, Phosphorus, and Potassium **Sparklines instantly update** on the dashboard, the Yield Probability Score (YPS) dynamically recalculates, and the ledger securely logs the "SENSOR_PING" hash.

### 5. Cryptographic Security & Offline Verification
Tokens are signed using HMAC-SHA256. To demonstrate that remote solar pumps can verify these tokens *without* an internet connection, run the offline verification script:
```bash
python3 offline_pump_demo.py
```
This script proves that the system remains resilient to rural infrastructure failures.
