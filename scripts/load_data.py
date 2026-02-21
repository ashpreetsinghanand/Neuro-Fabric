"""
Neuro-Fabric: Olist Dataset Loader

Loads the Brazilian E-Commerce CSV files into Supabase (PostgreSQL).

Usage:
    1. Download the Olist dataset from Kaggle:
       https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
    2. Extract CSVs into ./data/olist/ folder
    3. Run the SQL in scripts/create_olist_tables.sql via Supabase SQL Editor
    4. Set DATABASE_URL in .env
    5. Run: python scripts/load_data.py

Alternative: If you have the CSVs, you can also use Supabase Dashboard > Table Editor
to import CSVs directly into each table.
"""

import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    print("Get it from: Supabase Dashboard > Settings > Database > Connection string (URI)")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    os.system(f"{sys.executable} -m pip install psycopg2-binary")
    import psycopg2

DATA_DIR = Path(__file__).parent.parent / "data" / "olist"

# Order matters: load tables without FK dependencies first
TABLE_CSV_MAP = [
    ("olist_customers", "olist_customers_dataset.csv"),
    ("olist_geolocation", "olist_geolocation_dataset.csv"),
    ("olist_sellers", "olist_sellers_dataset.csv"),
    ("product_category_name_translation", "product_category_name_translation.csv"),
    ("olist_products", "olist_products_dataset.csv"),
    ("olist_orders", "olist_orders_dataset.csv"),
    ("olist_order_items", "olist_order_items_dataset.csv"),
    ("olist_order_payments", "olist_order_payments_dataset.csv"),
    ("olist_order_reviews", "olist_order_reviews_dataset.csv"),
]


def load_csv_to_table(conn, table_name: str, csv_filename: str):
    csv_path = DATA_DIR / csv_filename
    if not csv_path.exists():
        print(f"  ⚠ Skipping {table_name}: {csv_path} not found")
        return 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        cols = ", ".join(f'"{h}"' for h in headers)
        placeholders = ", ".join(["%s"] * len(headers))

        cur = conn.cursor()
        count = 0
        batch = []
        batch_size = 1000

        for row in reader:
            # Convert empty strings to None
            cleaned = [None if v == "" else v for v in row]
            batch.append(cleaned)
            count += 1

            if len(batch) >= batch_size:
                try:
                    args = ",".join(
                        cur.mogrify(f"({placeholders})", r).decode()
                        for r in batch
                    )
                    cur.execute(
                        f'INSERT INTO "{table_name}" ({cols}) VALUES {args} ON CONFLICT DO NOTHING'
                    )
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f"  ⚠ Batch error at row {count}: {e}")
                batch = []

        # Insert remaining
        if batch:
            try:
                args = ",".join(
                    cur.mogrify(f"({placeholders})", r).decode()
                    for r in batch
                )
                cur.execute(
                    f'INSERT INTO "{table_name}" ({cols}) VALUES {args} ON CONFLICT DO NOTHING'
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"  ⚠ Final batch error: {e}")

        cur.close()
    return count


def main():
    print("🧠 Neuro-Fabric: Olist Data Loader")
    print(f"Data directory: {DATA_DIR}")
    print()

    if not DATA_DIR.exists():
        print(f"ERROR: Data directory not found: {DATA_DIR}")
        print("Please download the Olist dataset from Kaggle and extract CSVs into ./data/olist/")
        print("URL: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    print("✓ Connected to database\n")

    for table_name, csv_file in TABLE_CSV_MAP:
        print(f"Loading {table_name}...")
        count = load_csv_to_table(conn, table_name, csv_file)
        print(f"  ✓ {count:,} rows loaded\n")

    conn.close()
    print("✅ All data loaded successfully!")


if __name__ == "__main__":
    main()
