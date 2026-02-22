-- ============================================
-- Bike Store Sample Data Seed
-- ============================================

INSERT INTO production.categories (category_name) VALUES 
('Mountain Bikes'), ('Road Bikes'), ('Cruisers Bikes'), ('Hybrid Bikes'), 
('Electric Bikes'), ('Children Bikes'), ('Comfort Bicycles'), ('Cyclocross Bicycles')
ON CONFLICT DO NOTHING;

INSERT INTO production.brands (brand_name) VALUES 
('Trek'), ('Giant'), ('Specialized'), ('Cannondale'), ('BMC'), 
('Surly'), ('Salsa'), ('Kona'), ('Electra'), ('Heller')
ON CONFLICT DO NOTHING;

INSERT INTO sales.stores (store_name, phone, email, street, city, state, zip_code) VALUES
('Santa Cruz Bikes', '(831) 476-4321', 'santacruz@bikes.shop', '3700 Portola Drive', 'Santa Cruz', 'CA', '95060'),
('Baldwin Bikes', '(516) 379-8888', 'baldwin@bikes.shop', '4200 Chestnut Lane', 'Baldwin', 'NY', '11410'),
('Rowlett Bikes', '(972) 530-5555', 'rowlett@bikes.shop', '8000 Fairway Avenue', 'Rowlett', 'TX', '75088')
ON CONFLICT DO NOTHING;

INSERT INTO production.products (product_name, brand_id, category_id, model_year, list_price) VALUES
('Trek 820 - 2016', 1, 1, 2016, 379.99),
('Surly Wednesday Frameset', 6, 1, 2016, 469.99),
('Trek Fuel EX 8 29', 1, 1, 2016, 2899.99),
('Specialized S-Works Roubaix', 3, 2, 2016, 4499.99),
('Giant Defy 1', 2, 2, 2016, 1199.99),
('Trek Madone 9.2', 1, 2, 2016, 4999.99),
('Electra Townie Original 7D', 9, 3, 2016, 489.99),
('Trek Conduit+', 1, 5, 2016, 2799.99)
ON CONFLICT DO NOTHING;

INSERT INTO sales.customers (first_name, last_name, phone, email, street, city, state, zip_code) VALUES
('John', 'Smith', '(212) 555-1234', 'john.smith@gmail.com', '123 Main St', 'New York', 'NY', '10001'),
('Sarah', 'Johnson', '(310) 555-5678', 'sarah.j@gmail.com', '456 Oak Ave', 'Los Angeles', 'CA', '90001'),
('Michael', 'Williams', '(512) 555-9012', 'mwills@yahoo.com', '789 Pine Rd', 'Austin', 'TX', '78701'),
('Emily', 'Brown', '(305) 555-3456', 'emily.brown@outlook.com', '321 Elm St', 'Miami', 'FL', '33101')
ON CONFLICT DO NOTHING;
