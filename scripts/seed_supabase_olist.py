import os
import random
import uuid
from datetime import datetime, timedelta
import pandas as pd
from faker import Faker
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Initialize Faker with Brazilian Portuguese locale
fake = Faker('pt_BR')

def generate_mock_data():
    print("Generating mock Olist dataset...")
    
    # 1. Product Categories
    categories_data = [
        ('beleza_saude', 'health_beauty'), ('informatica_acessorios', 'computers_accessories'),
        ('esporte_lazer', 'sports_leisure'), ('moveis_decoracao', 'furniture_decor'),
        ('utilidades_domesticas', 'housewares'), ('brinquedos', 'toys'),
        ('telefonia', 'telephony'), ('automotivo', 'auto'),
        ('eletronicos', 'electronics'), ('ferramentas_jardim', 'garden_tools'),
        ('livros_interesse_geral', 'books'), ('alimentos_bebidas', 'food_drink'),
        ('cool_stuff', 'cool_stuff'), ('papelaria', 'stationery'),
        ('fashion_bolsas_e_acessorios', 'fashion_bags_accessories'),
        ('pet_shop', 'pet_shop'), ('cama_mesa_banho', 'bed_bath_table'),
        ('relogios_presentes', 'watches_gifts'), ('construcao_ferramentas', 'construction_tools'),
        ('bebes', 'baby')
    ]
    df_categories = pd.DataFrame(categories_data, columns=['category_name', 'category_name_english'])
    df_categories['category_id'] = range(1, len(categories_data) + 1)
    
    # 2. Customers (1000)
    customer_ids = [str(uuid.uuid4()) for _ in range(1000)]
    customers = []
    for cid in customer_ids:
        customers.append({
            'customer_id': cid,
            'customer_name': fake.name(),
            'email': fake.unique.email(),
            'city': fake.city(),
            'state': fake.estado_sigla(),
            'zip_code': fake.postcode(),
            'created_at': fake.date_time_between(start_date='-2y', end_date='now')
        })
    df_customers = pd.DataFrame(customers)
    
    # 3. Sellers (100)
    seller_ids = [str(uuid.uuid4()) for _ in range(100)]
    sellers = []
    for sid in seller_ids:
        sellers.append({
            'seller_id': sid,
            'business_name': fake.company(),
            'city': fake.city(),
            'state': fake.estado_sigla(),
            'zip_code': fake.postcode(),
            'latitude': float(fake.latitude()),
            'longitude': float(fake.longitude()),
            'joined_at': fake.date_time_between(start_date='-3y', end_date='-1y')
        })
    df_sellers = pd.DataFrame(sellers)

    # 4. Products (500)
    product_ids = [str(uuid.uuid4()) for _ in range(500)]
    products = []
    for pid in product_ids:
        products.append({
            'product_id': pid,
            'product_name': fake.catch_phrase(),
            'category_id': random.choice(df_categories['category_id']),
            'description': fake.text(max_nb_chars=200),
            'weight_g': random.uniform(100, 5000),
            'length_cm': random.uniform(10, 100),
            'height_cm': random.uniform(5, 50),
            'width_cm': random.uniform(10, 80),
            'photo_count': random.randint(1, 6)
        })
    df_products = pd.DataFrame(products)

    # 5. Orders (5000)
    order_ids = [str(uuid.uuid4()) for _ in range(5000)]
    orders = []
    order_statuses = ['delivered'] * 4500 + ['shipped'] * 200 + ['canceled'] * 150 + ['processing'] * 100 + ['invoiced'] * 50
    random.shuffle(order_statuses)
    
    for i, oid in enumerate(order_ids):
        purchased = fake.date_time_between(start_date='-1y', end_date='now')
        approved = purchased + timedelta(hours=random.randint(1, 48))
        status = order_statuses[i]
        
        delivered_carrier = None
        delivered_cust = None
        if status in ['shipped', 'delivered']:
            delivered_carrier = approved + timedelta(days=random.randint(1, 3))
        if status == 'delivered':
            delivered_cust = delivered_carrier + timedelta(days=random.randint(2, 10))
            
        orders.append({
            'order_id': oid,
            'customer_id': random.choice(customer_ids),
            'order_status': status,
            'purchase_timestamp': purchased,
            'approved_at': approved,
            'delivered_carrier_date': delivered_carrier,
            'delivered_customer_date': delivered_cust,
            'estimated_delivery_date': purchased + timedelta(days=15)
        })
    df_orders = pd.DataFrame(orders)

    # 6. Order Items (approx 6000)
    order_items = []
    item_id_counter = 1
    for oid in order_ids:
        num_items = random.choices([1, 2, 3, 4], weights=[0.7, 0.2, 0.08, 0.02])[0]
        for _ in range(num_items):
            order_items.append({
                'item_id': item_id_counter,
                'order_id': oid,
                'product_id': random.choice(product_ids),
                'seller_id': random.choice(seller_ids),
                'price': round(random.uniform(10.0, 1500.0), 2),
                'freight_value': round(random.uniform(5.0, 50.0), 2)
            })
            item_id_counter += 1
    df_order_items = pd.DataFrame(order_items)

    # 7. Payments (approx 5200)
    payments = []
    payment_id_counter = 1
    payment_types = ['credit_card'] * 3800 + ['boleto'] * 1000 + ['voucher'] * 300 + ['debit_card'] * 100
    for oid in order_ids:
        # Most orders have 1 payment, some have 2 (voucher + credit card)
        num_payments = random.choices([1, 2], weights=[0.95, 0.05])[0]
        for _ in range(num_payments):
            ptype = random.choice(payment_types)
            installments = random.randint(1, 12) if ptype == 'credit_card' else 1
            payments.append({
                'payment_id': payment_id_counter,
                'order_id': oid,
                'payment_type': ptype,
                'payment_installments': installments,
                'payment_value': round(random.uniform(20.0, 2000.0), 2)
            })
            payment_id_counter += 1
    df_payments = pd.DataFrame(payments)

    # 8. Reviews (5000)
    reviews = []
    scores = [5]*2800 + [4]*1000 + [1]*600 + [3]*400 + [2]*200
    for oid in order_ids:
        score = random.choice(scores)
        has_comment = random.random() < 0.4
        reviews.append({
            'review_id': str(uuid.uuid4()),
            'order_id': oid,
            'score': score,
            'comment_title': fake.sentence(nb_words=3) if has_comment else None,
            'comment_message': fake.text(max_nb_chars=150) if has_comment else None,
            'created_at': fake.date_time_between(start_date='-1y', end_date='now')
        })
    df_reviews = pd.DataFrame(reviews)

    # 9. Geolocation (500)
    geos = []
    for _ in range(500):
        geos.append({
            'zip_code': fake.unique.postcode(),
            'city': fake.city(),
            'state': fake.estado_sigla(),
            'latitude': float(fake.latitude()),
            'longitude': float(fake.longitude())
        })
    df_geolocation = pd.DataFrame(geos)

    return {
        'product_categories': df_categories,
        'customers': df_customers,
        'sellers': df_sellers,
        'products': df_products,
        'orders': df_orders,
        'order_items': df_order_items,
        'payments': df_payments,
        'reviews': df_reviews,
        'geolocation': df_geolocation
    }

def seed_supabase():
    url = os.getenv('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL not found in .env")
        
    engine = create_engine(url)
    
    print("1. Recreating tables in Supabase...")
    with engine.begin() as conn:
        # Read the SQL creation script
        script_path = os.path.join(os.path.dirname(__file__), 'supabase_create_tables.sql')
        with open(script_path, 'r') as f:
            sql_script = f.read()
            
        # We only want to execute up to the SEED DATA section to avoid 
        # inserting the 20 dummy rows, then run the RLS policies
        create_part = sql_script.split('-- SEED DATA')[0]
        rls_part = sql_script.split('Enable Row Level Security (RLS)')[1]
        
        # Drop existing tables to start fresh
        tables = ['reviews', 'payments', 'order_items', 'orders', 'products', 'sellers', 'customers', 'product_categories', 'geolocation']
        for t in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE;"))
            
        print("2. Running DDLs...")
        conn.execute(text(create_part))
        conn.execute(text("-- Enable Row Level Security (RLS)" + rls_part))
        
    # Generate datasets
    datasets = generate_mock_data()
    
    print("3. Pushing data to Supabase...")
    # Order matters for foreign keys
    insertion_order = [
         'customers', 'sellers', 'products', 
        'orders', 'order_items', 'payments', 'reviews', 'geolocation'
    ]
    
    with engine.begin() as conn:
        for table_name in insertion_order:
            df = datasets[table_name]
            print(f"   -> Inserting {len(df)} rows into {table_name}...")
            df.to_sql(table_name, con=conn, if_exists='append', index=False)
            
    print("✅ Supabase Seed Complete! Connected live to Neuro-Fabric.")
    
if __name__ == "__main__":
    seed_supabase()
