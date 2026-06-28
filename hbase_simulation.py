"""
AUCA Big Data Analytics Final Project
Part 1 — HBase Simulation (Wide-Column Model)
Simulates HBase storage for:
  - User session data (row key: user_id + timestamp)
  - Product performance metrics (row key: product_id + date)
"""

import json
from collections import defaultdict

# ─────────────────────────────────────────
# HBase Wide-Column Store Simulation
# Row structure: { row_key: { column_family: { qualifier: value } } }
# ─────────────────────────────────────────

class HBaseSimulator:
    def __init__(self):
        self.tables = {}

    def create_table(self, table_name, column_families):
        self.tables[table_name] = {
            "column_families": column_families,
            "rows": {}
        }
        print(f"  ✓ Table '{table_name}' created with column families: {column_families}")

    def put(self, table_name, row_key, column_family, qualifier, value):
        table = self.tables[table_name]["rows"]
        if row_key not in table:
            table[row_key] = {}
        if column_family not in table[row_key]:
            table[row_key][column_family] = {}
        table[row_key][column_family][qualifier] = value

    def get(self, table_name, row_key):
        return self.tables[table_name]["rows"].get(row_key, None)

    def scan(self, table_name, start_row=None, end_row=None, limit=None):
        rows = self.tables[table_name]["rows"]
        keys = sorted(rows.keys())
        if start_row:
            keys = [k for k in keys if k >= start_row]
        if end_row:
            keys = [k for k in keys if k <= end_row]
        if limit:
            keys = keys[:limit]
        return {k: rows[k] for k in keys}

    def count(self, table_name):
        return len(self.tables[table_name]["rows"])


# ─────────────────────────────────────────
# INITIALIZE HBASE
# ─────────────────────────────────────────
hbase = HBaseSimulator()

print("=" * 55)
print("Creating HBase Tables")
print("=" * 55)

# Table 1: user_sessions
# Row key: user_id + reverse_timestamp (for recent-first retrieval)
hbase.create_table(
    "user_sessions",
    ["session_info", "device", "geo", "activity"]
)

# Table 2: product_performance
# Row key: product_id + date
hbase.create_table(
    "product_performance",
    ["metrics"]
)


# ─────────────────────────────────────────
# LOAD SESSION DATA INTO user_sessions
# ─────────────────────────────────────────
print("\nLoading session data into HBase 'user_sessions' table...")

import glob
session_files = sorted(glob.glob("sessions_*.json"))
total_loaded = 0

for sf in session_files:
    with open(sf) as f:
        sessions = json.load(f)
    for s in sessions:
        # Row key: user_id + start_time (sortable)
        row_key = f"{s['user_id']}_{s['start_time']}"

        # Column family: session_info
        hbase.put("user_sessions", row_key, "session_info", "session_id", s["session_id"])
        hbase.put("user_sessions", row_key, "session_info", "start_time", s["start_time"])
        hbase.put("user_sessions", row_key, "session_info", "end_time", s["end_time"])
        hbase.put("user_sessions", row_key, "session_info", "duration_seconds", s["duration_seconds"])
        hbase.put("user_sessions", row_key, "session_info", "referral_source", s["referral_source"])

        # Column family: device
        hbase.put("user_sessions", row_key, "device", "type", s["device_profile"]["type"])
        hbase.put("user_sessions", row_key, "device", "os", s["device_profile"]["os"])
        hbase.put("user_sessions", row_key, "device", "browser", s["device_profile"]["browser"])

        # Column family: geo
        hbase.put("user_sessions", row_key, "geo", "city", s["geo_data"]["city"])
        hbase.put("user_sessions", row_key, "geo", "state", s["geo_data"]["state"])
        hbase.put("user_sessions", row_key, "geo", "ip_address", s["geo_data"]["ip_address"])

        # Column family: activity
        hbase.put("user_sessions", row_key, "activity", "viewed_products", ",".join(s["viewed_products"]))
        hbase.put("user_sessions", row_key, "activity", "page_view_count", len(s["page_views"]))

        total_loaded += 1

print(f"  ✓ {total_loaded} sessions loaded into 'user_sessions'")


# ─────────────────────────────────────────
# LOAD PRODUCT PERFORMANCE METRICS
# ─────────────────────────────────────────
print("\nBuilding product performance metrics...")

# Aggregate views per product per date from sessions
product_daily = defaultdict(lambda: defaultdict(int))

for sf in session_files:
    with open(sf) as f:
        sessions = json.load(f)
    for s in sessions:
        date = s["start_time"][:10]   # extract YYYY-MM-DD
        for pv in s["page_views"]:
            if pv["page_type"] == "product_detail" and pv["product_id"]:
                product_daily[pv["product_id"]][date] += 1

# Load into product_performance table
for product_id, daily_views in product_daily.items():
    for date, views in daily_views.items():
        row_key = f"{product_id}_{date}"
        hbase.put("product_performance", row_key, "metrics", "view_count", views)

print(f"  ✓ {hbase.count('product_performance')} product-date records loaded")


# ─────────────────────────────────────────
# QUERY 1: Get all sessions for a specific user
# ─────────────────────────────────────────
print("\n" + "=" * 55)
print("QUERY 1: All sessions for user_000042")
print("=" * 55)

target_user = "user_000042"
user_sessions = hbase.scan(
    "user_sessions",
    start_row=f"{target_user}_",
    end_row=f"{target_user}_9999"
)

if user_sessions:
    for row_key, data in user_sessions.items():
        print(f"\n  Row Key : {row_key}")
        print(f"  Session : {data['session_info']['session_id']}")
        print(f"  Start   : {data['session_info']['start_time']}")
        print(f"  Duration: {data['session_info']['duration_seconds']}s")
        print(f"  Device  : {data['device']['type']} / {data['device']['os']}")
        print(f"  Referral: {data['session_info']['referral_source']}")
        print(f"  Pages   : {data['activity']['page_view_count']}")
else:
    print(f"  No sessions found for {target_user}")


# ─────────────────────────────────────────
# QUERY 2: Product view trend for a specific product
# ─────────────────────────────────────────
print("\n" + "=" * 55)
print("QUERY 2: Daily view trend for prod_00059")
print("=" * 55)

target_product = "prod_00059"
product_trend = hbase.scan(
    "product_performance",
    start_row=f"{target_product}_2025-01-01",
    end_row=f"{target_product}_2025-03-31",
    limit=10
)

if product_trend:
    for row_key, data in product_trend.items():
        date = row_key[len(target_product)+1:]
        views = data["metrics"]["view_count"]
        print(f"  {date} | Views: {views}")
else:
    print(f"  No performance data found for {target_product}")

print("\nHBase simulation complete.")