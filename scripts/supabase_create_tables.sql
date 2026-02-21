-- ══════════════════════════════════════════════════════════════════════════
-- NEURO-FABRIC: Supabase Table Creation Script
-- Run this in your Supabase Dashboard → SQL Editor
-- https://supabase.com/dashboard/project/cckosatubrluezidmxda/sql
-- ══════════════════════════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── 1. Product Categories ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS product_categories (
    category_id SERIAL PRIMARY KEY,
    category_name TEXT NOT NULL,
    category_name_english TEXT NOT NULL
);

INSERT INTO product_categories (category_name, category_name_english) VALUES
('beleza_saude', 'health_beauty'),
('informatica_acessorios', 'computers_accessories'),
('esporte_lazer', 'sports_leisure'),
('moveis_decoracao', 'furniture_decor'),
('utilidades_domesticas', 'housewares'),
('brinquedos', 'toys'),
('telefonia', 'telephony'),
('automotivo', 'auto'),
('eletronicos', 'electronics'),
('ferramentas_jardim', 'garden_tools'),
('livros_interesse_geral', 'books'),
('alimentos_bebidas', 'food_drink'),
('cool_stuff', 'cool_stuff'),
('papelaria', 'stationery'),
('fashion_bolsas_e_acessorios', 'fashion_bags_accessories'),
('pet_shop', 'pet_shop'),
('cama_mesa_banho', 'bed_bath_table'),
('relogios_presentes', 'watches_gifts'),
('construcao_ferramentas', 'construction_tools'),
('bebes', 'baby')
ON CONFLICT DO NOTHING;

-- ── 2. Customers ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    customer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_name TEXT NOT NULL,
    email TEXT UNIQUE,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 3. Sellers ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sellers (
    seller_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_name TEXT NOT NULL,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    joined_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 4. Products ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    product_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_name TEXT NOT NULL,
    category_id INTEGER REFERENCES product_categories(category_id),
    description TEXT,
    weight_g DOUBLE PRECISION,
    length_cm DOUBLE PRECISION,
    height_cm DOUBLE PRECISION,
    width_cm DOUBLE PRECISION,
    photo_count INTEGER DEFAULT 1
);

-- ── 5. Orders ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(customer_id),
    order_status TEXT NOT NULL DEFAULT 'created',
    purchase_timestamp TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    delivered_carrier_date TIMESTAMPTZ,
    delivered_customer_date TIMESTAMPTZ,
    estimated_delivery_date TIMESTAMPTZ
);

-- ── 6. Order Items ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_items (
    item_id SERIAL PRIMARY KEY,
    order_id UUID REFERENCES orders(order_id),
    product_id UUID REFERENCES products(product_id),
    seller_id UUID REFERENCES sellers(seller_id),
    price DOUBLE PRECISION NOT NULL,
    freight_value DOUBLE PRECISION DEFAULT 0
);

-- ── 7. Payments ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    payment_id SERIAL PRIMARY KEY,
    order_id UUID REFERENCES orders(order_id),
    payment_type TEXT NOT NULL,
    payment_installments INTEGER DEFAULT 1,
    payment_value DOUBLE PRECISION NOT NULL
);

-- ── 8. Reviews ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    review_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES orders(order_id),
    score INTEGER NOT NULL CHECK (score >= 1 AND score <= 5),
    comment_title TEXT,
    comment_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 9. Geolocation ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS geolocation (
    zip_code TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

-- ══════════════════════════════════════════════════════════════════════════
-- SEED DATA (sample — 20 rows each for quick verification)
-- ══════════════════════════════════════════════════════════════════════════

-- Seed Customers (20 sample)
INSERT INTO customers (customer_name, email, city, state, zip_code) VALUES
('Ana Silva', 'ana.silva@email.com', 'São Paulo', 'SP', '01000'),
('Carlos Santos', 'carlos.santos@email.com', 'Rio de Janeiro', 'RJ', '20000'),
('Maria Oliveira', 'maria.oliveira@email.com', 'Belo Horizonte', 'MG', '30000'),
('João Costa', 'joao.costa@email.com', 'Curitiba', 'PR', '80000'),
('Fernanda Lima', 'fernanda.lima@email.com', 'Porto Alegre', 'RS', '90000'),
('Pedro Souza', 'pedro.souza@email.com', 'Salvador', 'BA', '40000'),
('Beatriz Rocha', 'beatriz.rocha@email.com', 'Recife', 'PE', '50000'),
('Lucas Almeida', 'lucas.almeida@email.com', 'Fortaleza', 'CE', '60000'),
('Juliana Pereira', 'juliana.pereira@email.com', 'Brasília', 'DF', '70000'),
('Rafael Ribeiro', 'rafael.ribeiro@email.com', 'Manaus', 'AM', '69000'),
('Camila Fernandes', 'camila.fernandes@email.com', 'Goiânia', 'GO', '74000'),
('Bruno Barbosa', 'bruno.barbosa@email.com', 'Campinas', 'SP', '13000'),
('Larissa Carvalho', 'larissa.carvalho@email.com', 'Florianópolis', 'SC', '88000'),
('Diego Martins', 'diego.martins@email.com', 'Natal', 'RN', '59000'),
('Amanda Gomes', 'amanda.gomes@email.com', 'Campo Grande', 'MS', '79000'),
('Gustavo Araújo', 'gustavo.araujo@email.com', 'Vitória', 'ES', '29000'),
('Patrícia Correia', 'patricia.correia@email.com', 'João Pessoa', 'PB', '58000'),
('Thiago Dias', 'thiago.dias@email.com', 'Maceió', 'AL', '57000'),
('Aline Nascimento', 'aline.nascimento@email.com', 'Aracaju', 'SE', '49000'),
('Roberto Cardoso', 'roberto.cardoso@email.com', 'Teresina', 'PI', '64000')
ON CONFLICT DO NOTHING;

-- Seed Sellers (10 sample)
INSERT INTO sellers (business_name, city, state, zip_code) VALUES
('Tech Solutions Ltda', 'São Paulo', 'SP', '01001'),
('Casa & Conforto', 'Rio de Janeiro', 'RJ', '20001'),
('EsportiMais', 'Belo Horizonte', 'MG', '30001'),
('Beleza Natural', 'Curitiba', 'PR', '80001'),
('InfoWorld', 'Porto Alegre', 'RS', '90001'),
('AutoPeças Brasil', 'Salvador', 'BA', '40001'),
('Jardim Verde', 'Recife', 'PE', '50001'),
('FashionUp', 'Fortaleza', 'CE', '60001'),
('PetLove Store', 'Brasília', 'DF', '70001'),
('Brinquedos Top', 'Manaus', 'AM', '69001')
ON CONFLICT DO NOTHING;

-- Seed Products (20 sample)
INSERT INTO products (product_name, category_id, description, weight_g) VALUES
('Wireless Bluetooth Headphones', 9, 'High quality wireless headphones', 250),
('Ergonomic Office Chair', 4, 'Comfortable ergonomic office chair', 15000),
('Running Shoes Pro', 3, 'Professional running shoes', 400),
('Organic Face Cream', 1, 'Natural organic face cream', 120),
('USB-C Laptop Charger', 2, 'Fast charging USB-C adapter', 200),
('Car Phone Mount', 8, 'Universal car phone holder', 150),
('Garden Tool Set', 10, 'Complete 5-piece garden tool set', 2500),
('Leather Handbag', 15, 'Genuine leather handbag', 800),
('Dog Food Premium', 16, 'Premium organic dog food', 5000),
('Building Blocks Set', 6, 'Creative building blocks for kids', 1200),
('Cotton Bed Sheet Set', 17, 'Egyptian cotton 400TC bed sheets', 1500),
('Sports Watch', 18, 'Waterproof sports watch', 85),
('Hammer Drill', 19, 'Professional power hammer drill', 3200),
('Baby Stroller', 20, 'Lightweight foldable baby stroller', 8500),
('Smart Phone Case', 7, 'Shockproof smartphone case', 50),
('Novel Collection', 11, 'Best-selling novel collection', 600),
('Coffee Beans Premium', 12, 'Colombian Arabica coffee beans', 1000),
('LED Desk Lamp', 13, 'Adjustable LED desk lamp', 700),
('Ceramic Cookware Set', 5, 'Non-stick ceramic cookware 8pc', 4500),
('Vintage Record Player', 13, 'Retro vinyl record player', 5000)
ON CONFLICT DO NOTHING;

-- ══════════════════════════════════════════════════════════════════════════
-- Enable Row Level Security (RLS) with public read access
-- ══════════════════════════════════════════════════════════════════════════
ALTER TABLE product_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE sellers ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE geolocation ENABLE ROW LEVEL SECURITY;

-- Create public read policies
CREATE POLICY "Allow public read" ON product_categories FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON customers FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON sellers FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON products FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON orders FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON order_items FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON payments FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON reviews FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON geolocation FOR SELECT USING (true);

-- ══════════════════════════════════════════════════════════════════════════
-- DONE! Tables created with sample data and public read policies.
-- Verify: SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- ══════════════════════════════════════════════════════════════════════════
