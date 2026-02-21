#!/usr/bin/env python3
"""
Standalone script to initialize Supabase tables for Neuro-Fabric.
Run this directly: python3 scripts/init_supabase.py
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from core.db_connectors import _build_supabase_url, test_connection
from core.config import SUPABASE_URL, SUPABASE_KEY

def init_supabase():
    """Create all required tables in Supabase."""
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        print(f"   SUPABASE_URL: {'Set' if SUPABASE_URL else 'Missing'}")
        print(f"   SUPABASE_KEY: {'Set' if SUPABASE_KEY else 'Missing'}")
        return False
    
    print(f"🔗 Connecting to Supabase: {SUPABASE_URL[:30]}...")
    
    try:
        url = _build_supabase_url()
        engine = create_engine(url, pool_pre_ping=True)
        
        if not test_connection(engine):
            print("❌ Error: Could not connect to Supabase")
            return False
        
        print("✅ Connected to Supabase")
        print("📊 Creating tables...")
        
        # SQL statements to create tables
        sql_statements = [
            # 1. Data Dictionary Table
            """
            CREATE TABLE IF NOT EXISTS data_dictionary (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                db_name VARCHAR(100) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                business_summary TEXT,
                column_descriptions JSONB DEFAULT '{}',
                usage_recommendations TEXT[] DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(db_name, table_name)
            )
            """,
            # 2. Chat History Table
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id VARCHAR(255) NOT NULL,
                db_name VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                sql_query TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            # 3. Quality Metrics Table
            """
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                db_name VARCHAR(100) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                row_count BIGINT,
                overall_completeness FLOAT,
                column_quality JSONB DEFAULT '[]',
                analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(db_name, table_name)
            )
            """,
            # 4. Schema Cache Table
            """
            CREATE TABLE IF NOT EXISTS schema_cache (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                db_name VARCHAR(100) NOT NULL,
                schema_hash VARCHAR(64),
                schema_data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(db_name)
            )
            """,
            # Index
            "CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id, created_at DESC)",
        ]
        
        # Execute table creation
        with engine.connect() as conn:
            for i, sql in enumerate(sql_statements, 1):
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"   ✅ Statement {i}/{len(sql_statements)} executed")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"   ⚠️  Statement {i}: Already exists (skipping)")
                    else:
                        print(f"   ❌ Statement {i} failed: {e}")
        
        print("\n🔒 Enabling Row Level Security...")
        
        # Enable RLS
        rls_statements = [
            "ALTER TABLE data_dictionary ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE quality_metrics ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE schema_cache ENABLE ROW LEVEL SECURITY",
        ]
        
        with engine.connect() as conn:
            for sql in rls_statements:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"   ⚠️  RLS: {e}")
        
        print("🔓 Creating access policies...")
        
        # Create policies
        policy_statements = [
            'CREATE POLICY "Allow public access" ON data_dictionary FOR ALL USING (true) WITH CHECK (true)',
            'CREATE POLICY "Allow public access" ON chat_history FOR ALL USING (true) WITH CHECK (true)',
            'CREATE POLICY "Allow public access" ON quality_metrics FOR ALL USING (true) WITH CHECK (true)',
            'CREATE POLICY "Allow public access" ON schema_cache FOR ALL USING (true) WITH CHECK (true)',
        ]
        
        with engine.connect() as conn:
            for sql in policy_statements:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    if "already exists" in str(e).lower():
                        pass  # Expected
                    else:
                        print(f"   ⚠️  Policy: {e}")
        
        print("\n🌱 Inserting sample data...")
        
        # Insert sample data
        sample_data_sql = [
            """
            INSERT INTO data_dictionary (db_name, table_name, business_summary, column_descriptions, usage_recommendations) 
            VALUES 
            ('olist', 'orders', 'The orders table contains all customer purchase transactions in the Olist e-commerce platform. It tracks order status, timestamps, and customer-seller relationships.', 
             '{"order_id": "Unique identifier for each order", "customer_id": "Reference to the customer who placed the order", "order_status": "Current status of the order (delivered, shipped, etc.)", "order_purchase_timestamp": "When the order was placed"}',
             ARRAY['Join with customers table using customer_id', 'Use order_status to filter active vs completed orders', 'Analyze order_purchase_timestamp for temporal trends'])
            ON CONFLICT (db_name, table_name) DO NOTHING
            """,
            """
            INSERT INTO data_dictionary (db_name, table_name, business_summary, column_descriptions, usage_recommendations) 
            VALUES 
            ('olist', 'customers', 'The customers table stores unique customer information including location data (geolocation). Each customer can have multiple orders.',
             '{"customer_id": "Unique customer identifier", "customer_unique_id": "Hashed unique customer ID", "customer_zip_code_prefix": "First 3 digits of customer zip code", "customer_city": "Customer city", "customer_state": "Customer state (UF)"}',
             ARRAY['Join with orders table to analyze customer behavior', 'Use geolocation data for regional analysis'])
            ON CONFLICT (db_name, table_name) DO NOTHING
            """,
            """
            INSERT INTO data_dictionary (db_name, table_name, business_summary, column_descriptions, usage_recommendations) 
            VALUES 
            ('olist', 'products', 'The products table contains product catalog information including categories, dimensions, and weight.',
             '{"product_id": "Unique product identifier", "product_category_name": "Product category in Portuguese", "product_weight_g": "Product weight in grams", "product_length_cm": "Product length", "product_height_cm": "Product height"}',
             ARRAY['Join with order_items to analyze product performance', 'Use category for filtering and grouping'])
            ON CONFLICT (db_name, table_name) DO NOTHING
            """,
            """
            INSERT INTO quality_metrics (db_name, table_name, row_count, overall_completeness, column_quality)
            VALUES 
            ('olist', 'orders', 99441, 0.95, '[{"column_name": "order_id", "null_rate": 0, "distinct_count": 99441}, {"column_name": "customer_id", "null_rate": 0, "distinct_count": 99441}]'),
            ('olist', 'customers', 99441, 0.98, '[{"column_name": "customer_id", "null_rate": 0, "distinct_count": 99441}, {"column_name": "customer_city", "null_rate": 0.01, "distinct_count": 4119}]'),
            ('olist', 'products', 32951, 0.92, '[{"column_name": "product_id", "null_rate": 0, "distinct_count": 32951}, {"column_name": "product_category_name", "null_rate": 0.02, "distinct_count": 74}]')
            ON CONFLICT (db_name, table_name) DO NOTHING
            """,
        ]
        
        with engine.connect() as conn:
            for sql in sample_data_sql:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    print(f"   ⚠️  Sample data: {e}")
        
        # Verify tables created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('data_dictionary', 'chat_history', 'quality_metrics', 'schema_cache')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
        
        print(f"\n✅ Setup complete! Created {len(tables)} tables:")
        for table in tables:
            print(f"   • {table}")
        
        # Show row counts
        print("\n📊 Table row counts:")
        with engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"   • {table}: {count} rows")
                except Exception as e:
                    print(f"   • {table}: Error - {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_supabase()
    sys.exit(0 if success else 1)
