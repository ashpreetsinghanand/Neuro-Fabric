# 🚲 Bike Store — Microservices Platform

A modern e-commerce platform for bicycle retail built with microservices architecture.

## Architecture

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Frontend   │──▶│ Order Svc   │──▶│  PostgreSQL  │
│  (React)    │   │ (Python)    │   │  (Supabase)  │
└─────────────┘   └──────┬──────┘   └──────────────┘
                         │
                  ┌──────▼──────┐
                  │ Product Svc │
                  │ (Python)    │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │ Inventory   │
                  │ Service     │
                  └─────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `order-service` | 3001 | Order management, checkout, payments |
| `product-service` | 3002 | Product catalog, categories, brands |
| `inventory-service` | 3003 | Stock tracking, reorder alerts |
| `frontend` | 3000 | React SPA storefront |

## Database

PostgreSQL on Supabase with schemas:
- `production` — Products, brands, categories, stock
- `sales` — Orders, customers, stores, staff

## Quick Start

```bash
# 1. Set up database
psql $DATABASE_URL -f database/migrations/001_initial_schema.sql
psql $DATABASE_URL -f database/seeds/sample_data.sql

# 2. Start services
cd backend && pip install -r requirements.txt
python services/order_service.py &
python services/product_service.py &
python services/inventory_service.py &

# 3. Start frontend
cd frontend && npm install && npm run dev
```

## Team

- **Ashpreet Singh** — Lead Developer
- Product & Engineering

## License

MIT
