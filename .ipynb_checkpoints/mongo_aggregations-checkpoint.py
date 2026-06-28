"""
AUCA Big Data Analytics Final Project
Part 1 — MongoDB Aggregation Pipelines
Pipeline 1: Top-selling products by revenue
Pipeline 2: Total revenue by category
"""

from pymongo import MongoClient
import json

client = MongoClient("mongodb://localhost:27017/")
db = client["ecommerce_db"]

# ─────────────────────────────────────────
# PIPELINE 1: Top 10 Products by Revenue
# ─────────────────────────────────────────
print("=" * 50)
print("PIPELINE 1: Top 10 Products by Revenue")
print("=" * 50)

pipeline1 = [
    { "$match": { "status": "completed" } },
    { "$unwind": "$items" },
    {
        "$group": {
            "_id": "$items.product_id",
            "total_revenue": { "$sum": "$items.line_total" },
            "total_quantity_sold": { "$sum": "$items.quantity" },
            "num_transactions": { "$sum": 1 }
        }
    },
    { "$sort": { "total_revenue": -1 } },
    { "$limit": 10 }
]

results1 = list(db.transactions.aggregate(pipeline1))
for i, r in enumerate(results1, 1):
    print(f"  {i}. {r['_id']} | Revenue: ${r['total_revenue']:.2f} | "
          f"Qty Sold: {r['total_quantity_sold']} | Transactions: {r['num_transactions']}")

# ─────────────────────────────────────────
# PIPELINE 2: Total Revenue by Category
# ─────────────────────────────────────────
print()
print("=" * 50)
print("PIPELINE 2: Total Revenue by Category")
print("=" * 50)

pipeline2 = [
    { "$match": { "status": "completed" } },
    { "$unwind": "$items" },
    {
        "$group": {
            "_id": "$items.category_id",
            "total_revenue": { "$sum": "$items.line_total" },
            "total_orders": { "$sum": 1 },
            "avg_order_value": { "$avg": "$items.line_total" }
        }
    },
    { "$sort": { "total_revenue": -1 } }
]

results2 = list(db.transactions.aggregate(pipeline2))
for r in results2:
    print(f"  {r['_id']} | Revenue: ${r['total_revenue']:.2f} | "
          f"Orders: {r['total_orders']} | Avg Order Value: ${r['avg_order_value']:.2f}")

print("\nDone.")
client.close()