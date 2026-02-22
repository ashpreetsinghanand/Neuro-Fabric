"""
Product Service — Manages the product catalog, categories, and brands.
Connects to the production schema in PostgreSQL.
"""
from flask import Flask, jsonify, request
import os

app = Flask(__name__)
DATABASE_URL = os.environ.get("DATABASE_URL", "")


@app.route("/api/products", methods=["GET"])
def list_products():
    """List all products with brand and category info."""
    category = request.args.get("category")
    brand = request.args.get("brand")
    return jsonify({
        "products": [
            {"product_id": 1, "name": "Trek 820 - 2016", "brand": "Trek", "category": "Mountain Bikes", "price": 379.99},
            {"product_id": 4, "name": "Trek Fuel EX 8 29", "brand": "Trek", "category": "Mountain Bikes", "price": 2899.99},
            {"product_id": 8, "name": "Specialized S-Works Roubaix", "brand": "Specialized", "category": "Road Bikes", "price": 4499.99},
            {"product_id": 10, "name": "Trek Madone 9.2", "brand": "Trek", "category": "Road Bikes", "price": 4999.99},
        ],
        "total": 16,
        "filters": {"category": category, "brand": brand}
    })


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Get detailed product information."""
    return jsonify({
        "product_id": product_id,
        "name": "Trek 820 - 2016",
        "brand": {"id": 1, "name": "Trek"},
        "category": {"id": 1, "name": "Mountain Bikes"},
        "model_year": 2016,
        "list_price": 379.99,
        "stock": [
            {"store": "Santa Cruz Bikes", "quantity": 15},
            {"store": "Baldwin Bikes", "quantity": 10},
        ]
    })


@app.route("/api/categories", methods=["GET"])
def list_categories():
    """List all product categories."""
    return jsonify({
        "categories": [
            {"id": 1, "name": "Mountain Bikes", "product_count": 7},
            {"id": 2, "name": "Road Bikes", "product_count": 3},
            {"id": 3, "name": "Cruisers Bikes", "product_count": 1},
            {"id": 4, "name": "Hybrid Bikes", "product_count": 1},
            {"id": 5, "name": "Electric Bikes", "product_count": 1},
        ]
    })


@app.route("/api/brands", methods=["GET"])
def list_brands():
    """List all brands."""
    return jsonify({
        "brands": [
            {"id": 1, "name": "Trek", "product_count": 6},
            {"id": 2, "name": "Giant", "product_count": 2},
            {"id": 3, "name": "Specialized", "product_count": 2},
            {"id": 9, "name": "Electra", "product_count": 3},
        ]
    })


if __name__ == "__main__":
    app.run(port=3002, debug=True)
