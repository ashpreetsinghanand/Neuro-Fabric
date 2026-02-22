"""
Order Service — Handles order creation, status updates, and checkout flow.
Connects to the sales schema in PostgreSQL.
"""
from flask import Flask, jsonify, request
import os

app = Flask(__name__)
DATABASE_URL = os.environ.get("DATABASE_URL", "")


@app.route("/api/orders", methods=["GET"])
def list_orders():
    """List all orders with customer and store info."""
    return jsonify({
        "orders": [
            {"order_id": 1, "customer": "John Smith", "store": "Santa Cruz Bikes", "status": "Completed", "total": 5359.97},
            {"order_id": 2, "customer": "Sarah Johnson", "store": "Santa Cruz Bikes", "status": "Completed", "total": 1449.97},
            {"order_id": 3, "customer": "Michael Williams", "store": "Baldwin Bikes", "status": "Completed", "total": 3599.99},
        ]
    })


@app.route("/api/orders", methods=["POST"])
def create_order():
    """Create a new order."""
    data = request.json
    return jsonify({"order_id": 9, "status": "Pending", "message": "Order created successfully"}), 201


@app.route("/api/orders/<int:order_id>/status", methods=["PATCH"])
def update_status(order_id):
    """Update order status (1=Pending, 2=Processing, 3=Rejected, 4=Completed)."""
    data = request.json
    return jsonify({"order_id": order_id, "new_status": data.get("status"), "message": "Status updated"})


@app.route("/api/revenue/summary", methods=["GET"])
def revenue_summary():
    """Get revenue summary by store."""
    return jsonify({
        "total_revenue": 28457.82,
        "by_store": [
            {"store": "Santa Cruz Bikes", "revenue": 12479.93, "orders": 4},
            {"store": "Baldwin Bikes", "revenue": 7019.40, "orders": 2},
            {"store": "Rowlett Bikes", "revenue": 8958.49, "orders": 2},
        ]
    })


if __name__ == "__main__":
    app.run(port=3001, debug=True)
