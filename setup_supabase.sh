#!/bin/bash
# One-click Supabase setup script

echo "🚀 Neuro-Fabric Supabase Setup"
echo "================================"
echo ""

# Create temp SQL file
cat > /tmp/supabase_setup.sql << 'SQLEOF'
-- Create tables
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

CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    db_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sql_query TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id, created_at DESC);

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

CREATE TABLE IF NOT EXISTS schema_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    db_name VARCHAR(100) NOT NULL,
    schema_hash VARCHAR(64),
    schema_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(db_name)
);

ALTER TABLE data_dictionary ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE quality_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public access" ON data_dictionary;
DROP POLICY IF EXISTS "Allow public access" ON chat_history;
DROP POLICY IF EXISTS "Allow public access" ON quality_metrics;
DROP POLICY IF EXISTS "Allow public access" ON schema_cache;

CREATE POLICY "Allow public access" ON data_dictionary FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public access" ON chat_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public access" ON quality_metrics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public access" ON schema_cache FOR ALL USING (true) WITH CHECK (true);

INSERT INTO data_dictionary (db_name, table_name, business_summary, column_descriptions, usage_recommendations) 
VALUES 
('olist', 'orders', 'The orders table contains all customer purchase transactions...', 
 '{"order_id": "Unique identifier"}',
 ARRAY['Join with customers', 'Filter by status'])
ON CONFLICT (db_name, table_name) DO NOTHING;
SQLEOF

echo "🔌 Connecting to Supabase..."

export PGPASSWORD="i39CloFp4kpuP5Si"
psql "postgresql://postgres.cckosatubrluezidmxda:i39CloFp4kpuP5Si@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres" -f /tmp/supabase_setup.sql 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Tables created successfully!"
    echo "   • data_dictionary"
    echo "   • chat_history"
    echo "   • quality_metrics"
    echo "   • schema_cache"
    rm -f /tmp/supabase_setup.sql
else
    echo ""
    echo "❌ Failed. SQL saved at: /tmp/supabase_setup.sql"
fi
