"""SQLite database management for Mavuno Prototype."""
import sqlite3
import json
import time
import random
from pathlib import Path

# In prototype, we'll keep data in app/data
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "app" / "data"
DB_PATH = DATA_DIR / "mavuno.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute('''CREATE TABLE IF NOT EXISTS farms (
        id TEXT PRIMARY KEY, farmer_name TEXT, district TEXT, crop TEXT, phone TEXT UNIQUE,
        acres REAL, lat REAL, lng REAL, pump_lat REAL, pump_lng REAL, pump_name TEXT,
        discipline REAL, drought_factor REAL
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS sensor_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, farm_id TEXT, timestamp INTEGER,
        soil_moisture REAL, temp_c REAL, rainfall_mm REAL, humidity_pct REAL,
        n_mg_kg REAL, p_mg_kg REAL, k_mg_kg REAL,
        FOREIGN KEY (farm_id) REFERENCES farms (id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS tokens (
        id TEXT PRIMARY KEY, farm_id TEXT, yps INTEGER, kwh_allocated INTEGER,
        kwh_remaining INTEGER, pump_node TEXT, status TEXT DEFAULT 'active',
        created_at INTEGER, expires_at INTEGER, signature TEXT,
        FOREIGN KEY (farm_id) REFERENCES farms (id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT, prev_hash TEXT, curr_hash TEXT,
        type TEXT, payload TEXT, timestamp INTEGER
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS offers (
        id TEXT PRIMARY KEY, farm_id TEXT, farmer_name TEXT, crop TEXT, kg INTEGER,
        floor_ugx INTEGER, region TEXT, lat REAL, lng REAL, status TEXT DEFAULT 'open',
        created_at INTEGER
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS buyers (
        id TEXT PRIMARY KEY, name TEXT, region TEXT, crops_json TEXT,
        floor_ugx INTEGER, radius_km REAL, lat REAL, lng REAL, contact TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        offer_id TEXT NOT NULL,
        buyer_id TEXT NOT NULL,
        farm_id TEXT NOT NULL,
        amount_ugx INTEGER NOT NULL,
        method TEXT NOT NULL,
        msisdn TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        hmac_sig TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        settled_at INTEGER,
        FOREIGN KEY (offer_id) REFERENCES offers (id),
        FOREIGN KEY (buyer_id) REFERENCES buyers (id),
        FOREIGN KEY (farm_id) REFERENCES farms (id)
    )''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_payments_offer ON payments(offer_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_payments_farm ON payments(farm_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_payments_buyer ON payments(buyer_id)')

    cur.execute('''CREATE TABLE IF NOT EXISTS chat_threads (
        id TEXT PRIMARY KEY,
        farm_id TEXT NOT NULL,
        buyer_id TEXT NOT NULL,
        offer_id TEXT,
        created_at INTEGER NOT NULL,
        last_msg_at INTEGER NOT NULL,
        FOREIGN KEY (farm_id)  REFERENCES farms  (id),
        FOREIGN KEY (buyer_id) REFERENCES buyers (id),
        FOREIGN KEY (offer_id) REFERENCES offers (id)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        thread_id TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        sender_id TEXT NOT NULL,
        body TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY (thread_id) REFERENCES chat_threads (id)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS chat_read_cursors (
        thread_id TEXT NOT NULL,
        role TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        last_read_at INTEGER NOT NULL,
        PRIMARY KEY (thread_id, role, subject_id)
    )''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_msgs_thread   ON chat_messages(thread_id, created_at)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_threads_farm  ON chat_threads(farm_id,  last_msg_at DESC)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_threads_buyer ON chat_threads(buyer_id, last_msg_at DESC)')

    cur.execute('''CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        farm_id TEXT NOT NULL,
        body TEXT NOT NULL,
        photo_url TEXT,
        is_verified INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL,
        hidden INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (farm_id) REFERENCES farms (id)
    )''')
    try:
        cur.execute("ALTER TABLE posts ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists
    cur.execute('''CREATE TABLE IF NOT EXISTS reactions (
        post_id TEXT NOT NULL,
        reactor_role TEXT NOT NULL,
        reactor_id TEXT NOT NULL,
        emoji TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        PRIMARY KEY (post_id, reactor_role, reactor_id, emoji)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS post_flags (
        post_id TEXT NOT NULL,
        flagger_role TEXT NOT NULL,
        flagger_id TEXT NOT NULL,
        reason TEXT,
        created_at INTEGER NOT NULL,
        PRIMARY KEY (post_id, flagger_role, flagger_id)
    )''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_reactions_post ON reactions(post_id)')

    conn.commit()
    conn.close()

def migrate_seed_data():
    init_db()
    conn = get_db()
    cur = conn.cursor()
    
    # Farms
    f_path = DATA_DIR / "farms.json"
    if f_path.exists():
        data = json.loads(f_path.read_text())
        for fid, f in data.items():
            cur.execute('''INSERT OR REPLACE INTO farms VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (fid, f['farmer_name'], f['district'], f['crop'], f['phone'], f['acres'],
                 f['gps']['lat'], f['gps']['lng'], f['pump']['lat'], f['pump']['lng'],
                 f['pump']['name'], f['discipline'], f['drought_factor']))

    # Sensor History + NPK Synthesis
    s_path = DATA_DIR / "sensor_history.json"
    if s_path.exists():
        data = json.loads(s_path.read_text())
        farm_npk = {}
        for r in data:
            fid = r['farm_id']
            if fid not in farm_npk:
                farm_npk[fid] = [random.uniform(20, 50), random.uniform(10, 25), random.uniform(150, 300)]
            farm_npk[fid] = [v * random.uniform(0.98, 1.02) for v in farm_npk[fid]]
            n, p, k = farm_npk[fid]
            ts = int(time.mktime(time.strptime(r['date'], "%Y-%m-%d")))
            cur.execute('''INSERT INTO sensor_history 
                (farm_id, timestamp, soil_moisture, temp_c, rainfall_mm, humidity_pct, n_mg_kg, p_mg_kg, k_mg_kg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (fid, ts, r['soil_moisture'], r['temp_c'], r['rainfall_mm'], r['humidity_pct'], n, p, k))

    # Buyers
    b_path = DATA_DIR / "buyers.json"
    if b_path.exists():
        data = json.loads(b_path.read_text())
        for b in data['buyers']:
            cur.execute('''INSERT OR REPLACE INTO buyers VALUES (?,?,?,?,?,?,?,?,?)''',
                (b['buyer_id'], b['name'], b['region'], json.dumps(b['crops']),
                 b['floor_ugx_per_kg'], b['radius_km'], b['gps']['lat'], b['gps']['lng'], b['contact']))
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_seed_data()
    print(f"Prototype Database Ready at {DB_PATH}")
