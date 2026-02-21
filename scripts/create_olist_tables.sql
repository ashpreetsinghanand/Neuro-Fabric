-- ============================================================
-- Neuro-Fabric: Olist Brazilian E-Commerce Dataset
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor)
-- ============================================================

-- 1. Customers
CREATE TABLE IF NOT EXISTS olist_customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    customer_zip_code_prefix TEXT,
    customer_city TEXT,
    customer_state TEXT
);

-- 2. Geolocation
CREATE TABLE IF NOT EXISTS olist_geolocation (
    geolocation_zip_code_prefix TEXT,
    geolocation_lat DOUBLE PRECISION,
    geolocation_lng DOUBLE PRECISION,
    geolocation_city TEXT,
    geolocation_state TEXT
);

-- 3. Sellers
CREATE TABLE IF NOT EXISTS olist_sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix TEXT,
    seller_city TEXT,
    seller_state TEXT
);

-- 4. Product Category Name Translation
CREATE TABLE IF NOT EXISTS product_category_name_translation (
    product_category_name TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

-- 5. Products
CREATE TABLE IF NOT EXISTS olist_products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT REFERENCES product_category_name_translation(product_category_name),
    product_name_length INTEGER,
    product_description_length INTEGER,
    product_photos_qty INTEGER,
    product_weight_g INTEGER,
    product_length_cm INTEGER,
    product_height_cm INTEGER,
    product_width_cm INTEGER
);

-- 6. Orders
CREATE TABLE IF NOT EXISTS olist_orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT REFERENCES olist_customers(customer_id),
    order_status TEXT,
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

-- 7. Order Items
CREATE TABLE IF NOT EXISTS olist_order_items (
    order_id TEXT REFERENCES olist_orders(order_id),
    order_item_id INTEGER,
    product_id TEXT REFERENCES olist_products(product_id),
    seller_id TEXT REFERENCES olist_sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price DOUBLE PRECISION,
    freight_value DOUBLE PRECISION,
    PRIMARY KEY (order_id, order_item_id)
);

-- 8. Order Payments
CREATE TABLE IF NOT EXISTS olist_order_payments (
    order_id TEXT REFERENCES olist_orders(order_id),
    payment_sequential INTEGER,
    payment_type TEXT,
    payment_installments INTEGER,
    payment_value DOUBLE PRECISION,
    PRIMARY KEY (order_id, payment_sequential)
);

-- 9. Order Reviews
CREATE TABLE IF NOT EXISTS olist_order_reviews (
    review_id TEXT,
    order_id TEXT REFERENCES olist_orders(order_id),
    review_score INTEGER,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (review_id, order_id)
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_orders_customer ON olist_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON olist_orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_purchase ON olist_orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON olist_order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_seller ON olist_order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON olist_products(product_category_name);
CREATE INDEX IF NOT EXISTS idx_payments_order ON olist_order_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_order ON olist_order_reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_geolocation_zip ON olist_geolocation(geolocation_zip_code_prefix);
