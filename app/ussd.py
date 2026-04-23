"""USSD State Machine for Prototype (Multi-language & Marketplace)."""
from .database import get_db
from . import scorer, ect, crp

def route(phone: str, text: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM farms WHERE phone = ?", (phone,))
    farm = cur.fetchone()
    conn.close()
    if not farm: return "END Number not registered."

    parts = [p for p in text.split("*") if p]
    if not parts: return "CON Mavuno\n1. English\n2. Luganda"
    
    lang = "en" if parts[0] == "1" else "lg"
    S = {
        "en": {
            "wel": "Welcome {n}\n1. Score\n2. Credit\n3. Bal\n4. Price\n5. Sell\n6. Ask Mavuno\n7. Exit",
            "res": "YPS: {y}\nTier: {t}",
            "ask": "Enter question:",
            "sell": "Enter kg to sell:",
            "price": "Enter floor price (UGX/kg):"
        },
        "lg": {
            "wel": "Kulaba {n}\n1. Ekibalo\n2. Ebibanja\n3. Balansi\n4. Omuwendo\n5. Tunda\n6. Buuza Mavuno\n7. Fuluma",
            "res": "YPS: {y}\nTier: {t}",
            "ask": "Wandiika ekibuuzo kyo:",
            "sell": "Oyingize kilo:",
            "price": "Omuwendo gwa wansi (UGX/kg):"
        }
    }[lang]

    if len(parts) == 1: return "CON " + S["wel"].format(n=farm['farmer_name'].split()[0])
    
    cmd = parts[1]
    
    if cmd == "1":
        s = scorer.score_farm(farm['id'])
        return f"END " + S["res"].format(y=s['yps'], t=s['tier_label'].upper())
        
    if cmd == "2":
        s = scorer.score_farm(farm['id'])
        t = ect.issue(farm['id'], s['yps'], s['kwh_allocated'])
        if "error" in t:
            return f"END Issue failed: {t['error']}"
        return f"END Token: {t.get('token_id')}\nkWh: {t.get('kwh')}\nPump: {t.get('pump')}"
        
    if cmd == "3":
        b = ect.farm_balance(farm['id'])
        return f"END Bal: {b['kwh_remaining']} kWh\nTokens: {b['active_tokens']}"
        
    if cmd == "4":
        p = crp.market_prices(farm['crop'], farm['district'])
        if "error" in p:
            return f"END Price unknown for {farm['crop']}."
        return f"END {farm['crop'].upper()} Prices\nToday: UGX {p['today']['ugx']}/kg\n7d Avg: UGX {p['last7_avg']}/kg"
        
    if cmd == "5":
        if len(parts) == 2:
            return "CON " + S["sell"]
        if len(parts) == 3:
            return "CON " + S["price"]
        if len(parts) == 4:
            try:
                kg = int(parts[2])
                floor = int(parts[3])
                o = crp.list_offer(farm['id'], farm['crop'], kg, floor)
                m = crp.match_buyers(o['offer_id'])
                matches = len(m.get('matches', []))
                return f"END Offer {o['offer_id']} listed.\nMatches found: {matches}\nBuyers will contact you."
            except ValueError:
                return "END Invalid numbers."
                
    if cmd == "6":
        if len(parts) == 2:
            return "CON " + S["ask"]
        question = " ".join(parts[2:])
        a = crp.advisor(farm['id'], question)
        # Cap length to 140 chars for USSD safety
        ans = a['answer'] if len(a['answer']) <= 140 else a['answer'][:137] + "..."
        return f"END Mavuno:\n{ans}"
    
    return "END Webale. Grow strong."
