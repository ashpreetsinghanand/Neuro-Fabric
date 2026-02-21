"""
Neuro-Fabric: Database Seeder

Creates all tables and loads realistic e-commerce sample data
directly into Supabase — no CSV download required.

Multi-schema design:
  - public:     Core e-commerce tables (orders, customers, products)
  - analytics:  Aggregated metrics and KPIs
  - staging:    Raw ingestion zone

Usage: python3 scripts/seed_database.py
"""

import os
import sys
import random
import uuid
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    os.system(f"{sys.executable} -m pip install psycopg2-binary")
    import psycopg2
    import psycopg2.extras


# ── Schemas ──────────────────────────────────────────────────────────────────

DDL = """
-- Create schemas
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS staging;

-- ═══════════════════════════════════════════════════
-- PUBLIC SCHEMA: Core E-Commerce Tables
-- ═══════════════════════════════════════════════════

-- Customers
CREATE TABLE IF NOT EXISTS public.customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    zip_code TEXT,
    city TEXT,
    state TEXT,
    country TEXT DEFAULT 'Brazil',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sellers
CREATE TABLE IF NOT EXISTS public.sellers (
    seller_id TEXT PRIMARY KEY,
    business_name TEXT,
    contact_email TEXT,
    zip_code TEXT,
    city TEXT,
    state TEXT,
    rating DOUBLE PRECISION DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    joined_at TIMESTAMP DEFAULT NOW()
);

-- Product Categories
CREATE TABLE IF NOT EXISTS public.product_categories (
    category_id SERIAL PRIMARY KEY,
    category_name TEXT UNIQUE NOT NULL,
    category_name_english TEXT,
    parent_category TEXT
);

-- Products
CREATE TABLE IF NOT EXISTS public.products (
    product_id TEXT PRIMARY KEY,
    category_id INTEGER REFERENCES public.product_categories(category_id),
    product_name TEXT,
    description TEXT,
    weight_g INTEGER,
    length_cm INTEGER,
    height_cm INTEGER,
    width_cm INTEGER,
    photos_qty INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Orders
CREATE TABLE IF NOT EXISTS public.orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT REFERENCES public.customers(customer_id),
    order_status TEXT CHECK (order_status IN ('created','approved','shipped','delivered','canceled','returned')),
    purchase_timestamp TIMESTAMP,
    approved_at TIMESTAMP,
    delivered_carrier_date TIMESTAMP,
    delivered_customer_date TIMESTAMP,
    estimated_delivery_date TIMESTAMP
);

-- Order Items
CREATE TABLE IF NOT EXISTS public.order_items (
    order_id TEXT REFERENCES public.orders(order_id),
    item_seq INTEGER,
    product_id TEXT REFERENCES public.products(product_id),
    seller_id TEXT REFERENCES public.sellers(seller_id),
    price DOUBLE PRECISION,
    freight_value DOUBLE PRECISION,
    quantity INTEGER DEFAULT 1,
    PRIMARY KEY (order_id, item_seq)
);

-- Payments
CREATE TABLE IF NOT EXISTS public.payments (
    payment_id SERIAL PRIMARY KEY,
    order_id TEXT REFERENCES public.orders(order_id),
    payment_seq INTEGER,
    payment_type TEXT,
    installments INTEGER DEFAULT 1,
    payment_value DOUBLE PRECISION
);

-- Reviews
CREATE TABLE IF NOT EXISTS public.reviews (
    review_id TEXT,
    order_id TEXT REFERENCES public.orders(order_id),
    score INTEGER CHECK (score BETWEEN 1 AND 5),
    title TEXT,
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    answered_at TIMESTAMP,
    PRIMARY KEY (review_id, order_id)
);

-- Geolocation
CREATE TABLE IF NOT EXISTS public.geolocation (
    id SERIAL PRIMARY KEY,
    zip_code TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    city TEXT,
    state TEXT
);

-- ═══════════════════════════════════════════════════
-- ANALYTICS SCHEMA: Aggregated Metrics
-- ═══════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.daily_revenue (
    date DATE PRIMARY KEY,
    total_orders INTEGER,
    total_revenue DOUBLE PRECISION,
    avg_order_value DOUBLE PRECISION,
    total_items_sold INTEGER,
    unique_customers INTEGER
);

CREATE TABLE IF NOT EXISTS analytics.seller_performance (
    seller_id TEXT PRIMARY KEY,
    total_orders INTEGER,
    total_revenue DOUBLE PRECISION,
    avg_review_score DOUBLE PRECISION,
    avg_delivery_days DOUBLE PRECISION,
    cancellation_rate DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS analytics.product_metrics (
    product_id TEXT PRIMARY KEY,
    total_sold INTEGER,
    total_revenue DOUBLE PRECISION,
    avg_price DOUBLE PRECISION,
    avg_review_score DOUBLE PRECISION,
    return_rate DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS analytics.customer_segments (
    segment_name TEXT PRIMARY KEY,
    customer_count INTEGER,
    avg_order_value DOUBLE PRECISION,
    avg_orders_per_customer DOUBLE PRECISION,
    total_revenue DOUBLE PRECISION,
    description TEXT
);

-- ═══════════════════════════════════════════════════
-- STAGING SCHEMA: Raw Ingestion Zone
-- ═══════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS staging.raw_events (
    event_id SERIAL PRIMARY KEY,
    event_type TEXT,
    entity_id TEXT,
    payload JSONB,
    source TEXT,
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.data_quality_log (
    id SERIAL PRIMARY KEY,
    table_name TEXT,
    check_type TEXT,
    check_result TEXT,
    details JSONB,
    checked_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer ON public.orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_purchase ON public.orders(purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON public.order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_seller ON public.order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON public.products(category_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON public.payments(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_order ON public.reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_geo_zip ON public.geolocation(zip_code);
CREATE INDEX IF NOT EXISTS idx_daily_rev_date ON analytics.daily_revenue(date);
CREATE INDEX IF NOT EXISTS idx_raw_events_type ON staging.raw_events(event_type);
"""


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
    ('fashion_bags_accessories', 'Fashion Bags & Accessories', 'Fashion'),
    ('pet_shop', 'Pet Shop', 'Lifestyle'),
    ('office_furniture', 'Office Furniture', 'Office'),
    ('books_general_interest', 'Books', 'Media'),
]

PAYMENT_TYPES = ['credit_card', 'boleto', 'debit_card', 'voucher']
ORDER_STATUSES = ['delivered', 'delivered', 'delivered', 'delivered', 'delivered',
                  'shipped', 'shipped', 'approved', 'canceled', 'returned']  # weighted

REVIEW_TITLES = ['Great!', 'Good product', 'Love it', 'OK', 'Not bad', 'Excellent', 'Average', 'Poor quality',
                 'Fast delivery', 'Perfect', 'As expected', 'Would buy again', None, None, None]
REVIEW_COMMENTS = [
    'Excellent product, arrived on time!',
    'Good quality for the price.',
    'Product was exactly as described.',
    'Delivery took longer than expected.',
    'Very happy with my purchase!',
    'Product did not match description.',
    'Would recommend to friends.',
    'Average quality, nothing special.',
    'Great customer service!',
    'Product arrived damaged.',
    None, None, None, None, None,
]

PRODUCT_NAMES = {
    'bed_bath_table': ['Cotton Sheet Set', 'Memory Foam Pillow', 'Bath Towel Set', 'Duvet Cover', 'Table Runner'],
    'health_beauty': ['Moisturizing Cream', 'Vitamin C Serum', 'Hair Dryer Pro', 'Electric Toothbrush', 'Face Mask Set'],
    'sports_leisure': ['Yoga Mat', 'Resistance Bands', 'Running Shoes', 'Camping Tent', 'Fitness Tracker'],
    'computers_accessories': ['Wireless Mouse', 'USB-C Hub', 'Laptop Stand', 'Mechanical Keyboard', 'Monitor Arm'],
    'electronics': ['Bluetooth Speaker', 'Smart Watch', 'Wireless Earbuds', 'Power Bank', 'LED Strip Lights'],
}


def uid():
    return uuid.uuid4().hex[:24]


def rand_date(start_year=2023, end_year=2025):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def seed_data(conn):
    cur = conn.cursor()

    # ── Categories ──
    print("  Seeding product_categories...")
    cat_ids = {}
    for i, (name, eng, parent) in enumerate(CATEGORIES, 1):
        cur.execute(
            "INSERT INTO public.product_categories (category_id, category_name, category_name_english, parent_category) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (i, name, eng, parent)
        )
        cat_ids[name] = i
    conn.commit()

    # ── Customers (500) ──
    print("  Seeding customers (500)...")
    customer_ids = []
    for _ in range(500):
        cid = uid()
        customer_ids.append(cid)
        state = random.choice(STATES)
        city = random.choice(CITIES[state])
        fn, ln = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        cur.execute(
            "INSERT INTO public.customers (customer_id, customer_unique_id, first_name, last_name, email, zip_code, city, state, created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (cid, uid(), fn, ln, f"{fn.lower()}.{ln.lower()}@email.com",
             f"{random.randint(10000,99999)}", city, state, rand_date(2022, 2024))
        )
    conn.commit()

    # ── Sellers (50) ──
    print("  Seeding sellers (50)...")
    seller_ids = []
    for _ in range(50):
        sid = uid()
        seller_ids.append(sid)
        state = random.choice(STATES)
        city = random.choice(CITIES[state])
        cur.execute(
            "INSERT INTO public.sellers (seller_id, business_name, contact_email, zip_code, city, state, rating, joined_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (sid, f"{random.choice(LAST_NAMES)} {random.choice(['Store','Shop','Market','Outlet'])}",
             f"seller{random.randint(1,999)}@business.com", f"{random.randint(10000,99999)}",
             city, state, round(random.uniform(3.0, 5.0), 1), rand_date(2021, 2023))
        )
    conn.commit()

    # ── Products (200) ──
    print("  Seeding products (200)...")
    product_ids = []
    for _ in range(200):
        pid = uid()
        product_ids.append(pid)
        cat_key = random.choice(list(cat_ids.keys()))
        names = PRODUCT_NAMES.get(cat_key, ['Product Item', 'Quality Product', 'Premium Item'])
        cur.execute(
            "INSERT INTO public.products (product_id, category_id, product_name, description, weight_g, length_cm, height_cm, width_cm, photos_qty) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (pid, cat_ids[cat_key], f"{random.choice(names)} {random.choice(['Pro','Plus','Lite','Max',''])}".strip(),
             f"High quality {cat_key.replace('_',' ')} product with excellent features.",
             random.randint(100, 15000), random.randint(5, 80),
             random.randint(2, 50), random.randint(5, 60), random.randint(1, 6))
        )
    conn.commit()

    # ── Orders (2000) + Items + Payments + Reviews ──
    print("  Seeding orders (2000) + items + payments + reviews...")
    order_batch = []
    item_batch = []
    payment_batch = []
    review_batch = []

    for _ in range(2000):
        oid = uid()
        cid = random.choice(customer_ids)
        status = random.choice(ORDER_STATUSES)
        purchase = rand_date(2023, 2025)
        approved = purchase + timedelta(hours=random.randint(1, 48)) if status != 'canceled' else None
        carrier = approved + timedelta(days=random.randint(1, 5)) if approved and status in ('shipped','delivered') else None
        delivered = carrier + timedelta(days=random.randint(2, 15)) if carrier and status == 'delivered' else None
        estimated = purchase + timedelta(days=random.randint(7, 30))

        order_batch.append((oid, cid, status, purchase, approved, carrier, delivered, estimated))

        # 1-4 items per order
        n_items = random.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]
        for seq in range(1, n_items + 1):
            pid = random.choice(product_ids)
            sid = random.choice(seller_ids)
            price = round(random.uniform(15.0, 800.0), 2)
            freight = round(random.uniform(5.0, 60.0), 2)
            item_batch.append((oid, seq, pid, sid, price, freight, random.randint(1, 3)))

        # Payment
        ptype = random.choice(PAYMENT_TYPES)
        installments = random.choices([1, 2, 3, 6, 10, 12], weights=[40, 15, 10, 15, 10, 10])[0] if ptype == 'credit_card' else 1
        total_val = sum(ib[4] + ib[5] for ib in item_batch if ib[0] == oid)
        payment_batch.append((oid, 1, ptype, installments, round(total_val, 2)))

        # Review (80% chance for delivered)
        if status == 'delivered' and random.random() < 0.8:
            score = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 15, 30, 40])[0]
            review_batch.append((uid(), oid, score, random.choice(REVIEW_TITLES),
                                random.choice(REVIEW_COMMENTS),
                                delivered + timedelta(days=random.randint(0, 14)) if delivered else purchase + timedelta(days=20),
                                delivered + timedelta(days=random.randint(1, 30)) if delivered else None))

    # Batch inserts
    psycopg2.extras.execute_values(cur,
        "INSERT INTO public.orders (order_id,customer_id,order_status,purchase_timestamp,approved_at,delivered_carrier_date,delivered_customer_date,estimated_delivery_date) VALUES %s ON CONFLICT DO NOTHING",
        order_batch)
    conn.commit()

    psycopg2.extras.execute_values(cur,
        "INSERT INTO public.order_items (order_id,item_seq,product_id,seller_id,price,freight_value,quantity) VALUES %s ON CONFLICT DO NOTHING",
        item_batch)
    conn.commit()

    psycopg2.extras.execute_values(cur,
        "INSERT INTO public.payments (order_id,payment_seq,payment_type,installments,payment_value) VALUES %s ON CONFLICT DO NOTHING",
        payment_batch)
    conn.commit()

    psycopg2.extras.execute_values(cur,
        "INSERT INTO public.reviews (review_id,order_id,score,title,comment,created_at,answered_at) VALUES %s ON CONFLICT DO NOTHING",
        review_batch)
    conn.commit()

    # ── Geolocation (300) ──
    print("  Seeding geolocation (300)...")
    geo_batch = []
    for _ in range(300):
        state = random.choice(STATES)
        city = random.choice(CITIES[state])
        geo_batch.append((
            f"{random.randint(10000,99999)}", round(random.uniform(-33.7, -1.0), 6),
            round(random.uniform(-73.9, -34.8), 6), city, state
        ))
    psycopg2.extras.execute_values(cur,
        "INSERT INTO public.geolocation (zip_code,latitude,longitude,city,state) VALUES %s",
        geo_batch)
    conn.commit()

    # ── Analytics: Daily Revenue ──
    print("  Seeding analytics.daily_revenue...")
    cur.execute("""
        INSERT INTO analytics.daily_revenue (date, total_orders, total_revenue, avg_order_value, total_items_sold, unique_customers)
        SELECT
            purchase_timestamp::date AS date,
            COUNT(DISTINCT o.order_id) AS total_orders,
            COALESCE(SUM(oi.price + oi.freight_value), 0) AS total_revenue,
            COALESCE(AVG(oi.price + oi.freight_value), 0) AS avg_order_value,
            COUNT(oi.*) AS total_items_sold,
            COUNT(DISTINCT o.customer_id) AS unique_customers
        FROM public.orders o
        JOIN public.order_items oi ON o.order_id = oi.order_id
        GROUP BY purchase_timestamp::date
        ON CONFLICT (date) DO UPDATE SET
            total_orders = EXCLUDED.total_orders,
            total_revenue = EXCLUDED.total_revenue,
            avg_order_value = EXCLUDED.avg_order_value
    """)
    conn.commit()

    # ── Analytics: Seller Performance ──
    print("  Seeding analytics.seller_performance...")
    cur.execute("""
        INSERT INTO analytics.seller_performance (seller_id, total_orders, total_revenue, avg_review_score, avg_delivery_days, cancellation_rate)
        SELECT
            oi.seller_id,
            COUNT(DISTINCT oi.order_id) AS total_orders,
            SUM(oi.price) AS total_revenue,
            AVG(r.score) AS avg_review_score,
            AVG(EXTRACT(EPOCH FROM (o.delivered_customer_date - o.purchase_timestamp)) / 86400) AS avg_delivery_days,
            SUM(CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) AS cancellation_rate
        FROM public.order_items oi
        JOIN public.orders o ON o.order_id = oi.order_id
        LEFT JOIN public.reviews r ON r.order_id = o.order_id
        GROUP BY oi.seller_id
        ON CONFLICT (seller_id) DO UPDATE SET
            total_orders = EXCLUDED.total_orders,
            total_revenue = EXCLUDED.total_revenue
    """)
    conn.commit()

    # ── Analytics: Customer Segments ──
    print("  Seeding analytics.customer_segments...")
    segments = [
        ('VIP', 'Top 10% spenders with 3+ orders and high engagement'),
        ('Regular', 'Recurring customers with 2+ orders in the last year'),
        ('New', 'First-time buyers within the last 90 days'),
        ('At Risk', 'Customers with no orders in the last 6 months'),
        ('Churned', 'No activity in over 1 year'),
    ]
    for seg_name, desc in segments:
        cur.execute(
            "INSERT INTO analytics.customer_segments (segment_name, customer_count, avg_order_value, avg_orders_per_customer, total_revenue, description) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (seg_name, random.randint(20, 200), round(random.uniform(80, 400), 2),
             round(random.uniform(1.2, 5.5), 1), round(random.uniform(5000, 80000), 2), desc)
        )
    conn.commit()

    # ── Staging: Raw Events ──
    print("  Seeding staging.raw_events (100)...")
    import json
    event_types = ['order_created', 'payment_received', 'item_shipped', 'review_submitted', 'cart_abandoned']
    event_batch = []
    for _ in range(100):
        etype = random.choice(event_types)
        event_batch.append((
            etype, uid(),
            json.dumps({"action": etype, "value": round(random.uniform(10, 500), 2), "source": random.choice(["web", "mobile", "api"])}),
            random.choice(["webapp", "mobile_app", "api_gateway"]),
            rand_date(2024, 2025)
        ))
    psycopg2.extras.execute_values(cur,
        "INSERT INTO staging.raw_events (event_type, entity_id, payload, source, ingested_at) VALUES %s",
        event_batch)
    conn.commit()

    # ── Staging: Quality Log ──
    print("  Seeding staging.data_quality_log...")
    import json
    tables = ['customers', 'orders', 'order_items', 'products', 'payments', 'reviews']
    checks = ['null_check', 'uniqueness_check', 'freshness_check', 'referential_integrity']
    for t in tables:
        for c in checks:
            result = random.choice(['pass', 'pass', 'pass', 'warning', 'fail'])
            cur.execute(
                "INSERT INTO staging.data_quality_log (table_name, check_type, check_result, details) VALUES (%s,%s,%s,%s)",
                (t, c, result, json.dumps({"table": t, "check": c, "issues": random.randint(0, 10) if result != 'pass' else 0}))
            )
    conn.commit()

    cur.close()


def main():
    print("🧠 Neuro-Fabric: Database Seeder")
    print(f"   Connecting to: {DATABASE_URL[:50]}...")
    print()

    conn = psycopg2.connect(DATABASE_URL)
    print("✓ Connected to Supabase PostgreSQL\n")

    print("Creating schemas and tables...")
    cur = conn.cursor()
    cur.execute(DDL)
    conn.commit()
    cur.close()
    print("✓ All tables created\n")

    print("Seeding data...")
    seed_data(conn)
    print()

    # Summary
    cur = conn.cursor()
    for schema in ['public', 'analytics', 'staging']:
        cur.execute(f"""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"📁 {schema} schema: {len(tables)} tables")
        for t in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{t}"')
            cnt = cur.fetchone()[0]
            print(f"   └── {t}: {cnt:,} rows")
    cur.close()

    conn.close()
    print("\n✅ Database seeded successfully!")


if __name__ == "__main__":
    main()
