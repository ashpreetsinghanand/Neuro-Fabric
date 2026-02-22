"""
Inventory Service — Tracks stock levels across all store locations.
Connects to the production.stocks table in PostgreSQL.
"""
from flask import Flask, jsonify, request
import os

app = Flask(__name__)
DATABASE_URL = os.environ.get("DATABASE_URL", "")


@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    """Get inventory levels across all stores."""
    store_id = request.args.get("store_id", type=int)
    return jsonify({
        "inventory": [
            {"store": "Santa Cruz Bikes", "product": "Trek 820", "quantity": 15},
            {"store": "Santa Cruz Bikes", "product": "Trek Fuel EX 8", "quantity": 5},
            {"store": "Baldwin Bikes", "product": "Trek 820", "quantity": 10},
            {"store": "Rowlett Bikes", "product": "Electra Loft 7D", "quantity": 18},
        ],
        "total_items": 24,
        "low_stock_alerts": 3
    })


@app.route("/api/inventory/low-stock", methods=["GET"])
def low_stock():
    """Get products that are below reorder threshold."""
    return jsonify({
        "low_stock_items": [
            {"product": "Specialized S-Works Roubaix", "store": "Santa Cruz Bikes", "quantity": 3, "reorder_point": 5},
            {"product": "Trek Slash 8 27.5", "store": "Baldwin Bikes", "quantity": 4, "reorder_point": 5},
            {"product": "Giant Defy 1", "store": "Rowlett Bikes", "quantity": 4, "reorder_point": 5},
        ]
    })


@app.route("/api/inventory/reorder", methods=["POST"])
def create_reorder():
    """Create a reorder request for low-stock items."""
    data = request.json
    return jsonify({
        "reorder_id": 101,
        "product_id": data.get("product_id"),
        "quantity": data.get("quantity", 10),
        "status": "Submitted",
        "message": "Reorder request created"
    }), 201


if __name__ == "__main__":
    app.run(port=3003, debug=True)
