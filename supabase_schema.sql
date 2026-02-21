-- Neuro-Fabric Supabase Schema
-- Run this in your Supabase SQL Editor to create metadata tables

-- 1. Data Dictionary Table - stores AI-generated documentation
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
);

-- 2. Chat History Table - stores conversation history
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    db_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sql_query TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id, created_at DESC);

-- 3. Quality Metrics Table - stores data quality analysis
CREATE TABLE IF NOT EXISTS quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    db_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    row_count BIGINT,
    overall_completeness FLOAT,
    column_quality JSONB DEFAULT '[]',
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(db_name, table_name)
);

-- 4. Schema Cache Table - stores schema snapshots
CREATE TABLE IF NOT EXISTS schema_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    db_name VARCHAR(100) NOT NULL,
    schema_hash VARCHAR(64),
    schema_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(db_name)
);

-- Enable Row Level Security (optional - disable if not needed)
ALTER TABLE data_dictionary ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE quality_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_cache ENABLE ROW LEVEL SECURITY;

-- Create policies for public access (adjust as needed)
CREATE POLICY "Allow public access" ON data_dictionary FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public access" ON chat_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public access" ON quality_metrics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public access" ON schema_cache FOR ALL USING (true) WITH CHECK (true);

-- Insert sample data dictionary entries for Olist (example)
INSERT INTO data_dictionary (db_name, table_name, business_summary, column_descriptions, usage_recommendations) 
VALUES 
('olist', 'orders', 'The orders table contains all customer purchase transactions in the Olist e-commerce platform. It tracks order status, timestamps, and customer-seller relationships.', 
 '{"order_id": "Unique identifier for each order", "customer_id": "Reference to the customer who placed the order", "order_status": "Current status of the order (delivered, shipped, etc.)", "order_purchase_timestamp": "When the order was placed"}',
 ARRAY['Join with customers table using customer_id', 'Use order_status to filter active vs completed orders', 'Analyze order_purchase_timestamp for temporal trends']),
('olist', 'customers', 'The customers table stores unique customer information including location data (geolocation). Each customer can have multiple orders.',
 '{"customer_id": "Unique customer identifier", "customer_unique_id": "Hashed unique customer ID", "customer_zip_code_prefix": "First 3 digits of customer zip code", "customer_city": "Customer city", "customer_state": "Customer state (UF)"}',
 ARRAY['Join with orders table to analyze customer behavior', 'Use geolocation data for regional analysis']),
('olist', 'products', 'The products table contains product catalog information including categories, dimensions, and weight.',
 '{"product_id": "Unique product identifier", "product_category_name": "Product category in Portuguese", "product_weight_g": "Product weight in grams", "product_length_cm": "Product length", "product_height_cm": "Product height"}',
 ARRAY['Join with order_items to analyze product performance', 'Use category for filtering and grouping'])
ON CONFLICT (db_name, table_name) DO NOTHING;

-- Insert sample quality metrics
INSERT INTO quality_metrics (db_name, table_name, row_count, overall_completeness, column_quality)
VALUES 
('olist', 'orders', 99441, 0.95, '[{"column_name": "order_id", "null_rate": 0, "distinct_count": 99441}, {"column_name": "customer_id", "null_rate": 0, "distinct_count": 99441}]'),
('olist', 'customers', 99441, 0.98, '[{"column_name": "customer_id", "null_rate": 0, "distinct_count": 99441}, {"column_name": "customer_city", "null_rate": 0.01, "distinct_count": 4119}]'),
('olist', 'products', 32951, 0.92, '[{"column_name": "product_id", "null_rate": 0, "distinct_count": 32951}, {"column_name": "product_category_name", "null_rate": 0.02, "distinct_count": 74}]')
ON CONFLICT (db_name, table_name) DO NOTHING;
