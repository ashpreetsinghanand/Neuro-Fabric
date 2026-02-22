-- ============================================
-- Bike Store Database Schema
-- Migration: 001_initial_schema
-- Created: 2026-02-15
-- ============================================

-- Create schemas
CREATE SCHEMA IF NOT EXISTS sales;
CREATE SCHEMA IF NOT EXISTS production;

-- 1. Production Tables
CREATE TABLE IF NOT EXISTS production.categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS production.brands (
    brand_id SERIAL PRIMARY KEY,
    brand_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS production.products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    brand_id INT NOT NULL REFERENCES production.brands(brand_id) ON DELETE CASCADE,
    category_id INT NOT NULL REFERENCES production.categories(category_id) ON DELETE CASCADE,
    model_year SMALLINT NOT NULL,
    list_price DECIMAL(10, 2) NOT NULL
);

-- 2. Sales Tables
CREATE TABLE IF NOT EXISTS sales.stores (
    store_id SERIAL PRIMARY KEY,
    store_name VARCHAR(255) NOT NULL,
    phone VARCHAR(25),
    email VARCHAR(255),
    street VARCHAR(255),
    city VARCHAR(255),
    state VARCHAR(10),
    zip_code VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS sales.staffs (
    staff_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(25),
    active INT NOT NULL DEFAULT 1,
    store_id INT NOT NULL REFERENCES sales.stores(store_id) ON DELETE CASCADE,
    manager_id INT REFERENCES sales.staffs(staff_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sales.customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    phone VARCHAR(25),
    email VARCHAR(255) NOT NULL,
    street VARCHAR(255),
    city VARCHAR(255),
    state VARCHAR(25),
    zip_code VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS sales.orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES sales.customers(customer_id) ON DELETE SET NULL,
    order_status INT NOT NULL, -- 1=Pending, 2=Processing, 3=Rejected, 4=Completed
    order_date DATE NOT NULL,
    required_date DATE,
    shipped_date DATE,
    store_id INT NOT NULL REFERENCES sales.stores(store_id) ON DELETE CASCADE,
    staff_id INT NOT NULL REFERENCES sales.staffs(staff_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sales.order_items (
    order_id INT REFERENCES sales.orders(order_id) ON DELETE CASCADE,
    item_id INT,
    product_id INT NOT NULL REFERENCES production.products(product_id) ON DELETE CASCADE,
    quantity INT NOT NULL,
    list_price DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(4, 2) NOT NULL DEFAULT 0,
    PRIMARY KEY (order_id, item_id)
);

-- 3. Inventory
CREATE TABLE IF NOT EXISTS production.stocks (
    store_id INT REFERENCES sales.stores(store_id) ON DELETE CASCADE,
    product_id INT REFERENCES production.products(product_id) ON DELETE CASCADE,
    quantity INT,
    PRIMARY KEY (store_id, product_id)
);
