"""
AUCA Big Data Analytics Final Project
Part 1 — MongoDB Data Loading Script
Loads: users, categories, products, transactions into MongoDB
"""

import json
from pymongo import MongoClient, ASCENDING

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["ecommerce_db"]

# ─────────────────────────────────────────
# LOAD USERS
# ─────────────────────────────────────────
print("Loading users...")
with open("users.json") as f:
    users = json.load(f)
db.users.drop()
db.users.insert_many(users)
db.users.create_index([("user_id", ASCENDING)], unique=True)
print(f"  ✓ {db.users.count_documents({})} users loaded")

# ─────────────────────────────────────────
# LOAD CATEGORIES
# ─────────────────────────────────────────
print("Loading categories...")
with open("categories.json") as f:
    categories = json.load(f)
db.categories.drop()
db.categories.insert_many(categories)
db.categories.create_index([("category_id", ASCENDING)], unique=True)
print(f"  ✓ {db.categories.count_documents({})} categories loaded")

# ─────────────────────────────────────────
# LOAD PRODUCTS
# ─────────────────────────────────────────
print("Loading products...")
with open("products.json") as f:
    products = json.load(f)
db.products.drop()
db.products.insert_many(products)
db.products.create_index([("product_id", ASCENDING)], unique=True)
db.products.create_index([("category_id", ASCENDING)])
print(f"  ✓ {db.products.count_documents({})} products loaded")

# ─────────────────────────────────────────
# LOAD TRANSACTIONS
# ─────────────────────────────────────────
print("Loading transactions...")
with open("transactions.json") as f:
    transactions = json.load(f)
db.transactions.drop()
db.transactions.insert_many(transactions)
db.transactions.create_index([("transaction_id", ASCENDING)], unique=True)
db.transactions.create_index([("user_id", ASCENDING)])
db.transactions.create_index([("timestamp", ASCENDING)])
print(f"  ✓ {db.transactions.count_documents({})} transactions loaded")

print("\nAll collections loaded into 'ecommerce_db'")
client.close()