"""
Neuro-Fabric: DuckDB Local Database Setup

Creates a local DuckDB database with realistic e-commerce data.
This is the LOCAL-FIRST approach — no cloud dependency needed.

Usage: python3 scripts/seed_duckdb.py
"""

import os
import sys
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Ensure duckdb is available
try:
    import duckdb
except ImportError:
    os.system(f"{sys.executable} -m pip install duckdb")
    import duckdb

DB_PATH = Path(__file__).parent.parent / "data" / "neuro_fabric.duckdb"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── Data Generators ──────────────────────────────────────────────────────────

STATES = ['SP', 'RJ', 'MG', 'BA', 'PR', 'RS', 'PE', 'CE', 'PA', 'SC', 'MA', 'GO', 'AM', 'ES', 'PB', 'RN', 'AL', 'MT', 'DF', 'MS']
CITIES = {
    'SP': ['Sao Paulo', 'Campinas', 'Santos', 'Guarulhos', 'Osasco'],
    'RJ': ['Rio de Janeiro', 'Niteroi', 'Petropolis', 'Duque de Caxias'],
    'MG': ['Belo Horizonte', 'Uberlandia', 'Juiz de Fora'],
    'BA': ['Salvador', 'Feira de Santana', 'Vitoria da Conquista'],
    'PR': ['Curitiba', 'Londrina', 'Maringa'],
    'RS': ['Porto Alegre', 'Caxias do Sul', 'Pelotas'],
}
for s in STATES:
    if s not in CITIES:
        CITIES[s] = [f'{s} City', f'{s} Town']

FIRST_NAMES = ['Ana', 'Maria', 'Jose', 'Carlos', 'Lucas', 'Pedro', 'Joao', 'Paulo', 'Rafael', 'Gabriel',
               'Fernanda', 'Julia', 'Beatriz', 'Mariana', 'Camila', 'Larissa', 'Bruno', 'Diego', 'Marcos', 'Thiago']
LAST_NAMES = ['Silva', 'Santos', 'Oliveira', 'Souza', 'Rodrigues', 'Ferreira', 'Alves', 'Pereira', 'Lima', 'Gomes',
              'Costa', 'Ribeiro', 'Martins', 'Carvalho', 'Araujo', 'Melo', 'Barbosa', 'Rocha', 'Dias', 'Nascimento']

CATEGORIES = [
    ('bed_bath_table', 'Bed, Bath & Table', 'Home'),
    ('health_beauty', 'Health & Beauty', 'Personal Care'),
    ('sports_leisure', 'Sports & Leisure', 'Lifestyle'),
    ('furniture_decor', 'Furniture & Decor', 'Home'),
    ('computers_accessories', 'Computers & Accessories', 'Technology'),
    ('housewares', 'Housewares', 'Home'),
    ('watches_gifts', 'Watches & Gifts', 'Fashion'),
    ('telephony', 'Telephony', 'Technology'),
    ('garden_tools', 'Garden Tools', 'Home'),
    ('auto', 'Auto', 'Automotive'),
    ('toys', 'Toys', 'Kids'),
    ('cool_stuff', 'Cool Stuff', 'Lifestyle'),
    ('perfumery', 'Perfumery', 'Personal Care'),
    ('baby', 'Baby', 'Kids'),
    ('electronics', 'Electronics', 'Technology'),
    ('stationery', 'Stationery', 'Office'),
    ('fashion_bags', 'Fashion Bags & Accessories', 'Fashion'),
    ('pet_shop', 'Pet Shop', 'Lifestyle'),
    ('office_furniture', 'Office Furniture', 'Office'),
    ('books', 'Books', 'Media'),
]

PAYMENT_TYPES = ['credit_card', 'boleto', 'debit_card', 'voucher']
ORDER_STATUSES = ['delivered'] * 5 + ['shipped'] * 2 + ['approved', 'canceled', 'returned']

PRODUCT_NAMES = {
    'bed_bath_table': ['Cotton Sheet Set', 'Memory Foam Pillow', 'Bath Towel Set', 'Duvet Cover', 'Table Runner'],
    'health_beauty': ['Moisturizing Cream', 'Vitamin C Serum', 'Hair Dryer Pro', 'Electric Toothbrush', 'Face Mask Set'],
    'sports_leisure': ['Yoga Mat', 'Resistance Bands', 'Running Shoes', 'Camping Tent', 'Fitness Tracker'],
    'computers_accessories': ['Wireless Mouse', 'USB-C Hub', 'Laptop Stand', 'Mechanical Keyboard', 'Monitor Arm'],
    'electronics': ['Bluetooth Speaker', 'Smart Watch', 'Wireless Earbuds', 'Power Bank', 'LED Strip Lights'],
    'furniture_decor': ['Bookshelf', 'Wall Art Canvas', 'Plant Stand', 'Coffee Table', 'Floor Lamp'],
    'toys': ['Building Blocks Set', 'RC Car', 'Board Game', 'Puzzle 1000pc', 'Stuffed Animal'],
    'fashion_bags': ['Leather Backpack', 'Tote Bag', 'Crossbody Bag', 'Wallet', 'Travel Duffel'],
}

REVIEW_COMMENTS = [
    'Excellent product, arrived on time!', 'Good quality for the price.',
    'Product was exactly as described.', 'Delivery took longer than expected.',
    'Very happy with my purchase!', 'Product did not match description.',
    'Would recommend to friends.', 'Average quality, nothing special.',
    'Great customer service!', 'Product arrived damaged.',
    None, None, None,
]

def uid():
    return uuid.uuid4().hex[:24]

def rand_ts(start_year=2023, end_year=2025):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta), hours=random.randint(0, 23), minutes=random.randint(0, 59))


def create_tables(con):
    """Create all tables in the DuckDB database."""
    con.execute("""
        CREATE SCHEMA IF NOT EXISTS ecommerce;
        CREATE SCHEMA IF NOT EXISTS analytics;
        CREATE SCHEMA IF NOT EXISTS staging;
    """)

    # ── Public schema (main) ──
    con.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id VARCHAR PRIMARY KEY,
            customer_unique_id VARCHAR,
            first_name VARCHAR,
            last_name VARCHAR,
            email VARCHAR,
            zip_code VARCHAR,
            city VARCHAR,
            state VARCHAR,
            country VARCHAR DEFAULT 'Brazil',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sellers (
            seller_id VARCHAR PRIMARY KEY,
            business_name VARCHAR,
            contact_email VARCHAR,
            zip_code VARCHAR,
            city VARCHAR,
            state VARCHAR,
            rating DOUBLE DEFAULT 0,
            active BOOLEAN DEFAULT TRUE,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS product_categories (
            category_id INTEGER PRIMARY KEY,
            category_name VARCHAR UNIQUE NOT NULL,
            category_name_english VARCHAR,
            parent_category VARCHAR
        );

        CREATE TABLE IF NOT EXISTS products (
            product_id VARCHAR PRIMARY KEY,
            category_id INTEGER REFERENCES product_categories(category_id),
            product_name VARCHAR,
            description VARCHAR,
            weight_g INTEGER,
            length_cm INTEGER,
            height_cm INTEGER,
            width_cm INTEGER,
            photos_qty INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR PRIMARY KEY,
            customer_id VARCHAR REFERENCES customers(customer_id),
            order_status VARCHAR,
            purchase_timestamp TIMESTAMP,
            approved_at TIMESTAMP,
            delivered_carrier_date TIMESTAMP,
            delivered_customer_date TIMESTAMP,
            estimated_delivery_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS order_items (
            order_id VARCHAR REFERENCES orders(order_id),
            item_seq INTEGER,
            product_id VARCHAR REFERENCES products(product_id),
            seller_id VARCHAR REFERENCES sellers(seller_id),
            price DOUBLE,
            freight_value DOUBLE,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (order_id, item_seq)
        );

        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY,
            order_id VARCHAR REFERENCES orders(order_id),
            payment_seq INTEGER,
            payment_type VARCHAR,
            installments INTEGER DEFAULT 1,
            payment_value DOUBLE
        );

        CREATE TABLE IF NOT EXISTS reviews (
            review_id VARCHAR,
            order_id VARCHAR REFERENCES orders(order_id),
            score INTEGER,
            title VARCHAR,
            comment VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            answered_at TIMESTAMP,
            PRIMARY KEY (review_id, order_id)
        );

        CREATE TABLE IF NOT EXISTS geolocation (
            id INTEGER PRIMARY KEY,
            zip_code VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            city VARCHAR,
            state VARCHAR
        );
    """)

    # ── Analytics schema ──
    con.execute("""
        CREATE TABLE IF NOT EXISTS analytics.daily_revenue (
            date DATE PRIMARY KEY,
            total_orders INTEGER,
            total_revenue DOUBLE,
            avg_order_value DOUBLE,
            total_items_sold INTEGER,
            unique_customers INTEGER
        );

        CREATE TABLE IF NOT EXISTS analytics.seller_performance (
            seller_id VARCHAR PRIMARY KEY,
            total_orders INTEGER,
            total_revenue DOUBLE,
            avg_review_score DOUBLE,
            avg_delivery_days DOUBLE,
            cancellation_rate DOUBLE
        );

        CREATE TABLE IF NOT EXISTS analytics.product_metrics (
            product_id VARCHAR PRIMARY KEY,
            total_sold INTEGER,
            total_revenue DOUBLE,
            avg_price DOUBLE,
            avg_review_score DOUBLE,
            return_rate DOUBLE
        );

        CREATE TABLE IF NOT EXISTS analytics.customer_segments (
            segment_name VARCHAR PRIMARY KEY,
            customer_count INTEGER,
            avg_order_value DOUBLE,
            avg_orders_per_customer DOUBLE,
            total_revenue DOUBLE,
            description VARCHAR
        );
    """)

    # ── Staging schema ──
    con.execute("""
        CREATE TABLE IF NOT EXISTS staging.raw_events (
            event_id INTEGER PRIMARY KEY,
            event_type VARCHAR,
            entity_id VARCHAR,
            payload VARCHAR,
            source VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS staging.data_quality_log (
            id INTEGER PRIMARY KEY,
            table_name VARCHAR,
            check_type VARCHAR,
            check_result VARCHAR,
            details VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)


def seed_data(con):
    """Insert realistic e-commerce data."""

    # ── Categories ──
    print("  → Categories (20)...")
    for i, (name, eng, parent) in enumerate(CATEGORIES, 1):
        con.execute("INSERT OR IGNORE INTO product_categories VALUES (?, ?, ?, ?)", [i, name, eng, parent])

    # ── Customers (500) ──
    print("  → Customers (500)...")
    customer_ids = []
    for _ in range(500):
        cid = uid()
        customer_ids.append(cid)
        state = random.choice(STATES)
        city = random.choice(CITIES[state])
        fn, ln = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        con.execute("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [cid, uid(), fn, ln, f"{fn.lower()}.{ln.lower()}{random.randint(1,99)}@email.com",
                     f"{random.randint(10000,99999)}", city, state, 'Brazil', rand_ts(2022, 2024)])

    # ── Sellers (50) ──
    print("  → Sellers (50)...")
    seller_ids = []
    for _ in range(50):
        sid = uid()
        seller_ids.append(sid)
        state = random.choice(STATES)
        city = random.choice(CITIES[state])
        con.execute("INSERT OR IGNORE INTO sellers VALUES (?,?,?,?,?,?,?,?,?)",
                    [sid, f"{random.choice(LAST_NAMES)} {random.choice(['Store','Shop','Market','Outlet'])}",
                     f"seller{random.randint(1,999)}@biz.com", f"{random.randint(10000,99999)}",
                     city, state, round(random.uniform(3.0, 5.0), 1), True, rand_ts(2021, 2023)])

    # ── Products (200) ──
    print("  → Products (200)...")
    product_ids = []
    cat_keys = [c[0] for c in CATEGORIES]
    for _ in range(200):
        pid = uid()
        product_ids.append(pid)
        cat_key = random.choice(cat_keys)
        cat_id = cat_keys.index(cat_key) + 1
        names = PRODUCT_NAMES.get(cat_key, ['Quality Product', 'Premium Item', 'Standard Item'])
        con.execute("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [pid, cat_id, f"{random.choice(names)} {random.choice(['Pro','Plus','Lite','Max',''])}".strip(),
                     f"High quality {cat_key.replace('_',' ')} product.",
                     random.randint(100, 15000), random.randint(5, 80),
                     random.randint(2, 50), random.randint(5, 60), random.randint(1, 6),
                     rand_ts(2022, 2024)])

    # ── Orders (2000) + Items + Payments + Reviews ──
    print("  → Orders (2000) + items + payments + reviews...")
    payment_counter = 1
    review_list = []

    for order_num in range(2000):
        oid = uid()
        cid = random.choice(customer_ids)
        status = random.choice(ORDER_STATUSES)
        purchase = rand_ts(2023, 2025)
        approved = purchase + timedelta(hours=random.randint(1, 48)) if status != 'canceled' else None
        carrier = approved + timedelta(days=random.randint(1, 5)) if approved and status in ('shipped','delivered') else None
        delivered = carrier + timedelta(days=random.randint(2, 15)) if carrier and status == 'delivered' else None
        estimated = purchase + timedelta(days=random.randint(7, 30))

        con.execute("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?,?)",
                    [oid, cid, status, purchase, approved, carrier, delivered, estimated])

        # Items (1-4)
        n_items = random.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]
        total_val = 0
        for seq in range(1, n_items + 1):
            pid = random.choice(product_ids)
            sid = random.choice(seller_ids)
            price = round(random.uniform(15.0, 800.0), 2)
            freight = round(random.uniform(5.0, 60.0), 2)
            qty = random.randint(1, 3)
            total_val += price + freight
            con.execute("INSERT OR IGNORE INTO order_items VALUES (?,?,?,?,?,?,?)",
                        [oid, seq, pid, sid, price, freight, qty])

        # Payment
        ptype = random.choice(PAYMENT_TYPES)
        installments = random.choices([1, 2, 3, 6, 10, 12], weights=[40, 15, 10, 15, 10, 10])[0] if ptype == 'credit_card' else 1
        con.execute("INSERT OR IGNORE INTO payments VALUES (?,?,?,?,?,?)",
                    [payment_counter, oid, 1, ptype, installments, round(total_val, 2)])
        payment_counter += 1

        # Review (80% for delivered)
        if status == 'delivered' and random.random() < 0.8:
            score = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 15, 30, 40])[0]
            rev_date = delivered + timedelta(days=random.randint(0, 14)) if delivered else purchase + timedelta(days=20)
            ans_date = delivered + timedelta(days=random.randint(1, 30)) if delivered else None
            review_list.append((uid(), oid, score, random.choice(['Great!', 'Good product', 'OK', 'Love it', 'Not bad', None]),
                               random.choice(REVIEW_COMMENTS), rev_date, ans_date))

    for r in review_list:
        con.execute("INSERT OR IGNORE INTO reviews VALUES (?,?,?,?,?,?,?)", list(r))

    # ── Geolocation (300) ──
    print("  → Geolocation (300)...")
    for i in range(300):
        state = random.choice(STATES)
        city = random.choice(CITIES[state])
        con.execute("INSERT OR IGNORE INTO geolocation VALUES (?,?,?,?,?,?)",
                    [i + 1, f"{random.randint(10000,99999)}", round(random.uniform(-33.7, -1.0), 6),
                     round(random.uniform(-73.9, -34.8), 6), city, state])

    # ── Analytics: Aggregate from raw data ──
    print("  → Analytics aggregations...")

    con.execute("""
        INSERT OR REPLACE INTO analytics.daily_revenue
        SELECT
            CAST(o.purchase_timestamp AS DATE) AS date,
            COUNT(DISTINCT o.order_id) AS total_orders,
            COALESCE(SUM(oi.price + oi.freight_value), 0) AS total_revenue,
            COALESCE(AVG(oi.price + oi.freight_value), 0) AS avg_order_value,
            COUNT(*) AS total_items_sold,
            COUNT(DISTINCT o.customer_id) AS unique_customers
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY CAST(o.purchase_timestamp AS DATE)
    """)

    con.execute("""
        INSERT OR REPLACE INTO analytics.seller_performance
        SELECT
            oi.seller_id,
            COUNT(DISTINCT oi.order_id),
            SUM(oi.price),
            AVG(r.score),
            AVG(EXTRACT(EPOCH FROM (o.delivered_customer_date - o.purchase_timestamp)) / 86400),
            SUM(CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END)::DOUBLE / NULLIF(COUNT(*), 0)
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        LEFT JOIN reviews r ON r.order_id = o.order_id
        GROUP BY oi.seller_id
    """)

    con.execute("""
        INSERT OR REPLACE INTO analytics.product_metrics
        SELECT
            oi.product_id,
            SUM(oi.quantity),
            SUM(oi.price * oi.quantity),
            AVG(oi.price),
            AVG(r.score),
            SUM(CASE WHEN o.order_status = 'returned' THEN 1 ELSE 0 END)::DOUBLE / NULLIF(COUNT(*), 0)
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        LEFT JOIN reviews r ON r.order_id = o.order_id
        GROUP BY oi.product_id
    """)

    # Customer segments
    segments = [
        ('VIP', random.randint(30, 80), 'Top 10% spenders with 3+ orders'),
        ('Regular', random.randint(100, 200), 'Recurring customers with 2+ orders'),
        ('New', random.randint(80, 150), 'First-time buyers within last 90 days'),
        ('At Risk', random.randint(40, 100), 'No orders in last 6 months'),
        ('Churned', random.randint(20, 60), 'No activity in over 1 year'),
    ]
    for name, count, desc in segments:
        con.execute("INSERT OR REPLACE INTO analytics.customer_segments VALUES (?,?,?,?,?,?)",
                    [name, count, round(random.uniform(80, 400), 2),
                     round(random.uniform(1.2, 5.5), 1), round(random.uniform(5000, 80000), 2), desc])

    # ── Staging events ──
    print("  → Staging data...")
    import json
    event_types = ['order_created', 'payment_received', 'item_shipped', 'review_submitted', 'cart_abandoned']
    for i in range(100):
        etype = random.choice(event_types)
        con.execute("INSERT OR IGNORE INTO staging.raw_events VALUES (?,?,?,?,?,?)",
                    [i + 1, etype, uid(),
                     json.dumps({"action": etype, "value": round(random.uniform(10, 500), 2), "source": random.choice(["web", "mobile", "api"])}),
                     random.choice(["webapp", "mobile_app", "api_gateway"]),
                     rand_ts(2024, 2025)])

    tables_checks = ['customers', 'orders', 'order_items', 'products', 'payments', 'reviews']
    checks = ['null_check', 'uniqueness_check', 'freshness_check', 'referential_integrity']
    counter = 1
    for t in tables_checks:
        for c in checks:
            result = random.choice(['pass', 'pass', 'pass', 'warning', 'fail'])
            con.execute("INSERT OR IGNORE INTO staging.data_quality_log VALUES (?,?,?,?,?,?)",
                        [counter, t, c, result,
                         json.dumps({"table": t, "check": c, "issues": random.randint(0, 10) if result != 'pass' else 0}),
                         rand_ts(2024, 2025)])
            counter += 1


def main():
    print("🧠 Neuro-Fabric: DuckDB Local Database Setup")
    print(f"   Database: {DB_PATH}")
    print()

    # Remove existing DB to start fresh
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("  Removed existing database")

    con = duckdb.connect(str(DB_PATH))
    print("✓ Connected to DuckDB\n")

    print("Creating schemas and tables...")
    create_tables(con)
    print("✓ All tables created\n")

    print("Seeding data...")
    seed_data(con)
    print()

    # Summary
    schemas = {'main': ['customers', 'sellers', 'product_categories', 'products', 'orders', 'order_items', 'payments', 'reviews', 'geolocation'],
               'analytics': ['daily_revenue', 'seller_performance', 'product_metrics', 'customer_segments'],
               'staging': ['raw_events', 'data_quality_log']}

    total_rows = 0
    for schema, tables in schemas.items():
        print(f"📁 {schema} schema:")
        for t in tables:
            full_name = f"{schema}.{t}" if schema != 'main' else t
            count = con.execute(f"SELECT COUNT(*) FROM {full_name}").fetchone()[0]
            total_rows += count
            print(f"   └── {t}: {count:,} rows")

    print(f"\n📊 Total: {total_rows:,} rows across {sum(len(v) for v in schemas.values())} tables")
    print(f"💾 Database size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    con.close()
    print("\n✅ DuckDB database created successfully!")
    print(f"   Path: {DB_PATH}")


if __name__ == "__main__":
    main()
