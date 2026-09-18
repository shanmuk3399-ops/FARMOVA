from pathlib import Path
import sqlite3
BASE_DIR=Path(__file__).resolve().parents[1]
DB_PATH=BASE_DIR/"farmdirect.db"
def get_db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
def add_column_if_missing(conn,table,column,definition):
    cols={row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
def init_db():
    conn=get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('FARMER','BUYER','FPO')),
        location TEXT DEFAULT '',
        language TEXT DEFAULT 'English',
        fpo_id INTEGER,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS produce(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER,
        crop_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT DEFAULT 'Qtl',
        quality_grade TEXT NOT NULL,
        expected_price REAL NOT NULL,
        location TEXT NOT NULL,
        available_date TEXT,
        created_at TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(farmer_id) REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS offers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produce_id INTEGER NOT NULL,
        buyer_id INTEGER NOT NULL,
        buyer_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        offered_price REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        created_at TEXT NOT NULL,
        FOREIGN KEY(produce_id) REFERENCES produce(id) ON DELETE CASCADE,
        FOREIGN KEY(buyer_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produce_id INTEGER NOT NULL,
        buyer_id INTEGER NOT NULL,
        farmer_id INTEGER,
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        tracking_status TEXT NOT NULL DEFAULT 'ORDERED',
        source_type TEXT DEFAULT 'DIRECT',
        offer_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(produce_id) REFERENCES produce(id),
        FOREIGN KEY(buyer_id) REFERENCES users(id),
        FOREIGN KEY(farmer_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS fpos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT DEFAULT '',
        created_by INTEGER,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS fpo_members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fpo_id INTEGER NOT NULL,
        farmer_id INTEGER NOT NULL UNIQUE,
        joined_at TEXT NOT NULL,
        FOREIGN KEY(fpo_id) REFERENCES fpos(id) ON DELETE CASCADE,
        FOREIGN KEY(farmer_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS aggregations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fpo_id INTEGER NOT NULL,
        crop_name TEXT NOT NULL,
        required_quantity REAL NOT NULL,
        total_quantity REAL NOT NULL DEFAULT 0,
        unit TEXT DEFAULT 'Qtl',
        location TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'OPEN',
        created_at TEXT NOT NULL,
        FOREIGN KEY(fpo_id) REFERENCES fpos(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS aggregation_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aggregation_id INTEGER NOT NULL,
        farmer_id INTEGER NOT NULL,
        produce_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(aggregation_id) REFERENCES aggregations(id) ON DELETE CASCADE,
        FOREIGN KEY(farmer_id) REFERENCES users(id),
        FOREIGN KEY(produce_id) REFERENCES produce(id)
    );
    CREATE TABLE IF NOT EXISTS price_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop_name TEXT NOT NULL,
        location TEXT DEFAULT '',
        price REAL NOT NULL,
        recorded_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS demand_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop_name TEXT NOT NULL,
        location TEXT DEFAULT '',
        demand REAL NOT NULL,
        month INTEGER NOT NULL,
        recorded_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bulk_pools(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pool_name TEXT NOT NULL,
        target_quantity REAL NOT NULL,
        target_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        selected_products TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS transportation_costs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        distance_km REAL NOT NULL,
        fuel_used_l REAL NOT NULL,
        fuel_cost REAL NOT NULL,
        driver_cost REAL NOT NULL,
        toll_cost REAL NOT NULL,
        additional_cost REAL NOT NULL,
        total_cost REAL NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS cost_allocations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        farmer_id TEXT NOT NULL,
        farmer_name TEXT NOT NULL,
        quantity_kg REAL NOT NULL,
        share_percentage REAL NOT NULL,
        allocated_cost REAL NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS routes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL UNIQUE,
        route_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    add_column_if_missing(conn,"orders","source_type","TEXT DEFAULT 'DIRECT'")
    add_column_if_missing(conn,"orders","offer_id","INTEGER")
    conn.execute("UPDATE orders SET source_type='DIRECT' WHERE source_type IS NULL OR source_type=''" )
    conn.execute("UPDATE orders SET tracking_status='ACCEPTED' WHERE status='ACCEPTED' AND (tracking_status='ORDERED' OR tracking_status IS NULL OR tracking_status='')")
    conn.execute("UPDATE orders SET tracking_status='PROCESSING' WHERE status='PROCESSING' AND (tracking_status IS NULL OR tracking_status='' OR tracking_status='ORDERED')")
    conn.execute("UPDATE orders SET tracking_status='SHIPPED' WHERE status='SHIPPED' AND (tracking_status IS NULL OR tracking_status='' OR tracking_status='ORDERED')")
    conn.execute("UPDATE orders SET tracking_status='DELIVERED' WHERE status='DELIVERED' AND (tracking_status IS NULL OR tracking_status='' OR tracking_status='ORDERED')")
    conn.commit()
    conn.close()
