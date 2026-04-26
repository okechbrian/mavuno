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
            "wel": "Welcome {n}\n1. Score\n2. Credit\n3. Bal\n4. Price\n5. Sell\n6. Community\n7. Market\n8. Ask Mavuno\n9. Exit",
            "res": "YPS: {y}\nTier: {t}",
            "ask": "Enter question:",
            "sell": "Enter kg to sell:",
            "price": "Enter floor price (UGX/kg):",
            "feed": "{i}/{n} {u}:\n{b}\n0. Next",
            "feed_empty": "Feed is empty.",
            "mkt": "{i}/{n} {u}:\n{k}kg {c}\nUGX {p}/kg\n0. Next",
            "mkt_empty": "Market is empty."
        },
        "lg": {
            "wel": "Kulaba {n}\n1. Ekibalo\n2. Ebibanja\n3. Balansi\n4. Omuwendo\n5. Tunda\n6. Feed\n7. Akatale\n8. Buuza Mavuno\n9. Fuluma",
            "res": "YPS: {y}\nTier: {t}",
            "ask": "Wandiika ekibuuzo kyo:",
            "sell": "Oyingize kilo:",
            "price": "Omuwendo gwa wansi (UGX/kg):",
            "feed": "{i}/{n} {u}:\n{b}\n0. Next",
            "feed_empty": "Feed ekalu.",
            "mkt": "{i}/{n} {u}:\n{k}kg {c}\nUGX {p}/kg\n0. Next",
            "mkt_empty": "Akatale kakalu."
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
        from . import social
        # Handle simple paging via "0" input
        page_depth = parts[2:].count("0")
        posts = social.feed(limit=5)
        if not posts:
            return "END " + S["feed_empty"]
        
        idx = page_depth % len(posts)
        p = posts[idx]
        body = p['body'] if len(p['body']) <= 80 else p['body'][:77] + "..."
        # If it's a public query, simplify for USSD
        if body.startswith("🌱 Public Query:"):
            body = body.replace("🌱 Public Query:\n", "Q: ")
            
        return "CON " + S["feed"].format(
            i=idx + 1, n=len(posts), u=p['farmer_name'].split()[0], b=body
        )

    if cmd == "7":
        # Marketplace Browsing
        page_depth = parts[2:].count("0")
        offers = crp.list_open_offers(limit=10).get('offers', [])
        if not offers:
            return "END " + S["mkt_empty"]
        
        idx = page_depth % len(offers)
        o = offers[idx]
        return "CON " + S["mkt"].format(
            i=idx + 1, n=len(offers), u=o['farmer_name'].split()[0], 
            k=o['kg'], c=o['crop'].upper(), p=o['floor_ugx']
        )

    if cmd == "8":
        if len(parts) == 2:
            return "CON " + S["ask"]
        question = " ".join(parts[2:])
        a = crp.advisor(farm['id'], question)
        # Cap length to 140 chars for USSD safety
        ans = a['answer'] if len(a['answer']) <= 140 else a['answer'][:137] + "..."
        return f"END Mavuno:\n{ans}"
    
    return "END Webale. Grow strong."
