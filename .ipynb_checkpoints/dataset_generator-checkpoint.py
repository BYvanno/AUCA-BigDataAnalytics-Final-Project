"""
AUCA Big Data Analytics Final Project
Dataset Generator — E-Commerce Synthetic Data
Generates: users.json, categories.json, products.json,
           sessions_0.json ... sessions_N.json, transactions.json
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

# ─────────────────────────────────────────
# CONFIG — adjust sizes here if needed
# ─────────────────────────────────────────
NUM_USERS        = 500
NUM_CATEGORIES   = 20
NUM_SUBCATS_EACH = 4
NUM_PRODUCTS     = 500
NUM_SESSIONS     = 3000
NUM_TRANSACTIONS = 2000
SESSIONS_PER_FILE = 500          # sessions split across multiple files
START_DATE       = datetime(2025, 1, 1)
END_DATE         = datetime(2025, 3, 31)   # 90 days of activity

OUTPUT_DIR = "."   # writes files in the same folder as this script


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def random_date(start=START_DATE, end=END_DATE):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


# ─────────────────────────────────────────
# 1. USERS
# ─────────────────────────────────────────
def generate_users(n):
    users = []
    for i in range(n):
        reg = random_date(datetime(2024, 10, 1), datetime(2024, 12, 31))
        last = random_date(reg, END_DATE)
        users.append({
            "user_id": f"user_{i:06d}",
            "name": fake.name(),
            "email": fake.email(),
            "age": random.randint(18, 65),
            "gender": random.choice(["M", "F", "Other"]),
            "geo_data": {
                "city": fake.city(),
                "state": fake.state_abbr(),
                "country": "US"
            },
            "registration_date": fmt(reg),
            "last_active": fmt(last)
        })
    return users


# ─────────────────────────────────────────
# 2. CATEGORIES
# ─────────────────────────────────────────
def generate_categories(n, num_subcats):
    categories = []
    for i in range(n):
        subcats = []
        for j in range(num_subcats):
            subcats.append({
                "subcategory_id": f"sub_{i:03d}_{j:02d}",
                "name": fake.bs().title(),
                "profit_margin": round(random.uniform(0.10, 0.45), 2)
            })
        categories.append({
            "category_id": f"cat_{i:03d}",
            "name": fake.company(),
            "subcategories": subcats
        })
    return categories


# ─────────────────────────────────────────
# 3. PRODUCTS
# ─────────────────────────────────────────
def generate_products(n, categories):
    products = []
    for i in range(n):
        cat = random.choice(categories)
        sub = random.choice(cat["subcategories"])
        base_price = round(random.uniform(9.99, 499.99), 2)
        stock = random.randint(0, 200)
        creation = random_date(datetime(2024, 12, 1), datetime(2025, 1, 15))

        # build a small price history (1–3 price changes)
        price_history = []
        ph_date = creation
        ph_price = round(base_price * random.uniform(0.85, 1.20), 2)
        for _ in range(random.randint(1, 3)):
            price_history.append({"price": ph_price, "date": fmt(ph_date)})
            ph_date = random_date(ph_date, END_DATE)
            ph_price = round(ph_price * random.uniform(0.90, 1.15), 2)
        price_history.append({"price": base_price, "date": fmt(ph_date)})

        products.append({
            "product_id": f"prod_{i:05d}",
            "name": fake.catch_phrase().title(),
            "category_id": cat["category_id"],
            "subcategory_id": sub["subcategory_id"],
            "base_price": base_price,
            "current_stock": stock,
            "is_active": stock > 0,
            "price_history": price_history,
            "creation_date": fmt(creation)
        })
    return products


# ─────────────────────────────────────────
# 4. SESSIONS  (split into multiple files)
# ─────────────────────────────────────────
PAGE_TYPES = ["home", "category_listing", "product_detail", "cart", "checkout", "search"]

def generate_sessions(n, users, products):
    sessions = []
    for _ in range(n):
        user = random.choice(users)
        start = random_date()
        duration = random.randint(60, 1800)
        end = start + timedelta(seconds=duration)

        # pick 1–6 products this user viewed
        viewed = random.sample(products, k=random.randint(1, 6))
        viewed_ids = [p["product_id"] for p in viewed]

        # build page_views
        page_views = []
        ts = start
        page_views.append({
            "timestamp": fmt(ts),
            "page_type": "home",
            "product_id": None,
            "category_id": None,
            "view_duration": random.randint(10, 90)
        })
        for prod in viewed:
            ts += timedelta(seconds=random.randint(30, 180))
            page_views.append({
                "timestamp": fmt(ts),
                "page_type": "product_detail",
                "product_id": prod["product_id"],
                "category_id": prod["category_id"],
                "view_duration": random.randint(30, 300)
            })
        # maybe add a cart page
        if random.random() < 0.4:
            ts += timedelta(seconds=random.randint(10, 60))
            page_views.append({
                "timestamp": fmt(ts),
                "page_type": "cart",
                "product_id": None,
                "category_id": None,
                "view_duration": random.randint(20, 120)
            })

        sessions.append({
            "session_id": "sess_" + uuid.uuid4().hex[:10],
            "user_id": user["user_id"],
            "start_time": fmt(start),
            "end_time": fmt(end),
            "duration_seconds": duration,
            "geo_data": {
                "city": user["geo_data"]["city"],
                "state": user["geo_data"]["state"],
                "country": "US",
                "ip_address": fake.ipv4()
            },
            "device_profile": {
                "type": random.choice(["mobile", "desktop", "tablet"]),
                "os": random.choice(["iOS", "Android", "Windows", "macOS"]),
                "browser": random.choice(["Chrome", "Safari", "Firefox", "Edge"])
            },
            "referral_source": random.choice(["organic", "paid_search", "social", "email", "direct"]),
            "viewed_products": viewed_ids,
            "page_views": page_views
        })
    return sessions


# ─────────────────────────────────────────
# 5. TRANSACTIONS
# ─────────────────────────────────────────
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]
STATUSES        = ["completed", "pending", "returned", "cancelled"]

def generate_transactions(n, users, products):
    # only active (in-stock) products can be purchased
    active_products = [p for p in products if p["is_active"]]
    transactions = []
    for i in range(n):
        user = random.choice(users)
        ts   = random_date()
        # 1–4 items per transaction
        num_items = random.randint(1, 4)
        items_pool = random.sample(active_products, k=min(num_items, len(active_products)))
        items = []
        total = 0.0
        for prod in items_pool:
            qty = random.randint(1, 3)
            price = prod["base_price"]
            discount = round(random.uniform(0, 0.20), 2)
            line_total = round(price * qty * (1 - discount), 2)
            total += line_total
            items.append({
                "product_id": prod["product_id"],
                "category_id": prod["category_id"],
                "quantity": qty,
                "unit_price": price,
                "discount": discount,
                "line_total": line_total
            })
        transactions.append({
            "transaction_id": f"txn_{i:06d}",
            "user_id": user["user_id"],
            "timestamp": fmt(ts),
            "items": items,
            "total_amount": round(total, 2),
            "payment_method": random.choice(PAYMENT_METHODS),
            "status": random.choice(STATUSES),
            "shipping_address": {
                "city": user["geo_data"]["city"],
                "state": user["geo_data"]["state"],
                "country": "US"
            }
        })
    return transactions


# ─────────────────────────────────────────
# MAIN — generate & write all files
# ─────────────────────────────────────────
if __name__ == "__main__":
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating users...")
    users = generate_users(NUM_USERS)
    with open(f"{OUTPUT_DIR}/users.json", "w") as f:
        json.dump(users, f, indent=2)
    print(f"  ✓ users.json  ({len(users)} records)")

    print("Generating categories...")
    categories = generate_categories(NUM_CATEGORIES, NUM_SUBCATS_EACH)
    with open(f"{OUTPUT_DIR}/categories.json", "w") as f:
        json.dump(categories, f, indent=2)
    print(f"  ✓ categories.json  ({len(categories)} records)")

    print("Generating products...")
    products = generate_products(NUM_PRODUCTS, categories)
    with open(f"{OUTPUT_DIR}/products.json", "w") as f:
        json.dump(products, f, indent=2)
    print(f"  ✓ products.json  ({len(products)} records)")

    print("Generating sessions...")
    sessions = generate_sessions(NUM_SESSIONS, users, products)
    file_index = 0
    for start in range(0, len(sessions), SESSIONS_PER_FILE):
        chunk = sessions[start:start + SESSIONS_PER_FILE]
        fname = f"{OUTPUT_DIR}/sessions_{file_index}.json"
        with open(fname, "w") as f:
            json.dump(chunk, f, indent=2)
        print(f"  ✓ sessions_{file_index}.json  ({len(chunk)} records)")
        file_index += 1

    print("Generating transactions...")
    transactions = generate_transactions(NUM_TRANSACTIONS, users, products)
    with open(f"{OUTPUT_DIR}/transactions.json", "w") as f:
        json.dump(transactions, f, indent=2)
    print(f"  ✓ transactions.json  ({len(transactions)} records)")

    print("\nAll done! Files written to:", os.path.abspath(OUTPUT_DIR))
