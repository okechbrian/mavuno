# Mavuno Hardware & Practical Deployment Strategy

To achieve national scale in Uganda and prove to the Future Makers Hackathon that Mavuno is economically viable, the physical IoT and irrigation infrastructure must be affordable, durable, and highly optimized for rural conditions.

Mavuno is built on two hardware pillars:
1. **The "Sentinel Node" IoT Soil Sensors** (The brain of the Yield Probability Score).
2. **The EASP Solar Pump Hubs** (The redemption points for Energy Credit Tokens).

---

## 1. The "Sentinel Node" IoT Strategy

A common misconception is that every single smallholder farm requires its own $50 sensor node. In Uganda, smallholder farm plots (typically 1-2 acres) are often clustered closely together. Soil composition and weather patterns do not vary drastically within a 500m to 1km radius.

**The Mavuno Solution:**
We deploy **Sentinel Nodes**. One IoT soil sensor cluster is installed securely at the center of a "Parish Block" (e.g., a localized farming cooperative or a cluster of 10-15 farmers growing the same crop). 
- That single node captures the 7 crucial signals (Moisture, Temp, Humidity, Rain, N, P, K).
- The Mavuno backend associates those signals with all registered farmers within that specific micro-zone.
- This drops the hardware cost from ~$50 per farmer to **~$3.50 - $5.00 per farmer**.

### IoT Bill of Materials (BOM) & Costs
The Sentinel Nodes are built from rugged, off-the-shelf, modular industrial components.

| Component | Purpose | Estimated Cost (USD) | Example Vendor Link |
| :--- | :--- | :--- | :--- |
| **7-in-1 RS485 Modbus Soil Probe** | An industrial metal-pronged sensor stuck into the ground. It measures Nitrogen, Phosphorus, Potassium, Moisture, Temperature, pH, and Electrical Conductivity. | ~$25 - $40 | [Alibaba Link](https://www.alibaba.com/trade/search?SearchText=RS485+7+in+1+soil+sensor) |
| **ESP32 or Arduino w/ SIM800L Module** | The "Brain". Reads the Modbus sensor data and transmits the JSON payload via a standard 2G/GSM cellular connection. | ~$8 - $12 | [Amazon/AliExpress](https://www.amazon.com/s?k=SIM800L+ESP32) |
| **5W Solar Panel & 18650 Lithium Battery** | Because the node "sleeps" for 23 hours a day and only wakes up to transmit telemetry, a tiny 5W panel provides infinite runtime. | ~$10 - $15 | [Alibaba Link](https://www.alibaba.com/trade/search?SearchText=5v+solar+panel+18650) |
| **Weatherproof Enclosure (IP67)** | Protects the microcontroller and battery from heavy rains and heat. | ~$5 | Local / Hardware Store |

**Total Hardware Cost per Sentinel Node: ~$50 to $70 USD.**
*If 1 Sentinel Node covers 15 clustered farmers, the capital expenditure is roughly **$4.00 per farmer**.*

---

## 2. Practical Deployment of Irrigation Systems

The Energy Credit Token (ECT) allows the farmer to buy water. But how does the physical water get to the farm? 

We are not installing individual pumps for individual farmers (which is too expensive). Mavuno rides on top of Uganda's **Electricity Access Scale-up Project (EASP)**, a $638M World Bank initiative currently deploying mini-grids and solar infrastructure.

### The "Hub and Spoke" Irrigation Layout
1. **The Pump Hub:** A large, shared Solar Water Pump is installed at a reliable water source (e.g., a river, borehole, or community reservoir) covering a multi-acre agricultural zone.
2. **The IoT Controller (The DRM):** Connected to this pump is a secure relay controller. This controller is what the farmer communicates with when they redeem their Energy Credit Token via USSD.
3. **The Spokes (Water Distribution):** The central pump feeds a network of cheap, gravity-fed PVC pipes or localized water pans. 
   - When a farmer types `*165#` and redeems 10 kWh of their Energy Credit, the central pump unlocks and pushes water through the manifold specifically to their plot's irrigation drip-lines or reservoir tank.

### Why this structure scales:
- **Zero Asset Debt for the Farmer:** The farmer is not taking out a $500 loan to buy a personal solar pump. They are using an Energy Credit to *rent* output from community infrastructure.
- **Maximized Pump Utilization:** A solar pump sitting on one smallholder farm is idle 90% of the time. By making it a shared Hub activated by Mavuno Tokens, the pump runs all day, servicing multiple farmers sequentially, maximizing the Return on Investment for the EASP infrastructure deployment.
- **Offline Cryptographic Verification:** The pump controller has a copy of the `HMAC_SECRET` (the cryptographic key). When the farmer receives an Energy Credit SMS from the cloud, they input the token ID at the pump. The pump mathematically verifies the token offline, ensuring that farmers deep in rural areas without 4G internet can still access water. 

---

## Summary for the Judges
Mavuno is a software-defined marketplace layered over modular, community-shared hardware. By using Sentinel IoT nodes to drastically cut sensor costs, and Hub-and-Spoke solar pumps to share heavy infrastructure, we create a $500B scalable model that provides precision agriculture to the poorest farmers without burdening them with asset debt.
