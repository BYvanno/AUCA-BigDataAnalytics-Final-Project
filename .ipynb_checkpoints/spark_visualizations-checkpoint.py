"""
AUCA Big Data Analytics Final Project
Part 4 — Visualizations: CLV, Revenue, Payments, Devices
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pymongo import MongoClient
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

os.environ["PYSPARK_SUBMIT_ARGS"] = "--conf spark.driver.extraJavaOptions=-Dlog4j.logLevel=ERROR pyspark-shell"

spark = SparkSession.builder \
    .appName("AUCA_Visualizations") \
    .master("local[*]") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

print("=" * 60)
print("PART 4 — Visualizations")
print("=" * 60)

# ─────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────
print("\nLoading data...")

# MongoDB transactions
client = MongoClient("mongodb://localhost:27017/")
db = client["ecommerce_db"]
transactions_cursor = db.transactions.find({})
transactions_list = list(transactions_cursor)
client.close()

for t in transactions_list:
    if '_id' in t:
        del t['_id']

transactions_json = [json.dumps(t) for t in transactions_list]
txn_rdd = spark.sparkContext.parallelize(transactions_json)
txn_df = spark.read.json(txn_rdd)

# Sessions
sessions_df = spark.read.option("multiLine", "true").json("sessions_*.json")

# Products
products_df = spark.read.option("multiLine", "true").json("products.json")

# Filter completed transactions
txn_clean = txn_df.filter(F.col("status") == "completed")

print(f"  ✓ Transactions: {txn_clean.count()}")
print(f"  ✓ Sessions: {sessions_df.count()}")
print(f"  ✓ Products: {products_df.count()}")

# ─────────────────────────────────────────
# PLOT 1: CLV Distribution by Customer
# ─────────────────────────────────────────
print("\nGenerating Plot 1: CLV Distribution...")

txn_clean.createOrReplaceTempView("transactions")
sessions_df.createOrReplaceTempView("sessions")

clv_query = """
    SELECT 
        c.user_id,
        ROUND(c.total_revenue / c.purchase_frequency, 2) AS clv_score,
        c.total_revenue
    FROM (
        SELECT 
            user_id,
            COUNT(DISTINCT transaction_id) AS purchase_frequency,
            SUM(total_amount) AS total_revenue
        FROM transactions
        GROUP BY user_id
    ) c
    JOIN (
        SELECT DISTINCT user_id FROM sessions
    ) s ON c.user_id = s.user_id
"""

clv_data = spark.sql(clv_query).toPandas()

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.hist(clv_data['clv_score'], bins=30, color='steelblue', edgecolor='black', alpha=0.7)
plt.xlabel('CLV Score ($)', fontsize=11)
plt.ylabel('Number of Customers', fontsize=11)
plt.title('Distribution of Customer Lifetime Value (CLV)', fontsize=12, fontweight='bold')
plt.grid(axis='y', alpha=0.3)

plt.subplot(1, 2, 2)
plt.scatter(clv_data['clv_score'], clv_data['total_revenue'], alpha=0.6, s=50, color='coral')
plt.xlabel('CLV Score ($)', fontsize=11)
plt.ylabel('Total Revenue ($)', fontsize=11)
plt.title('CLV Score vs Total Revenue', fontsize=12, fontweight='bold')
plt.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('plot_1_clv_distribution.png', dpi=150, bbox_inches='tight')
print("  ✓ Saved: plot_1_clv_distribution.png")
plt.close()

# ─────────────────────────────────────────
# PLOT 2: Revenue by Category
# ─────────────────────────────────────────
print("\nGenerating Plot 2: Revenue by Category...")

revenue_query = """
    SELECT 
        item.category_id as category_id,
        ROUND(SUM(item.line_total), 2) AS total_revenue
    FROM (
        SELECT 
            explode(items) as item
        FROM transactions
    )
    WHERE item IS NOT NULL
    GROUP BY item.category_id
    ORDER BY total_revenue DESC
"""

revenue_data = spark.sql(revenue_query).toPandas()

plt.figure(figsize=(12, 6))
sns.barplot(data=revenue_data, x='category_id', y='total_revenue', palette='Blues_r')
plt.xlabel('Category', fontsize=11)
plt.ylabel('Total Revenue ($)', fontsize=11)
plt.title('Total Revenue by Product Category', fontsize=12, fontweight='bold')
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('plot_2_revenue_by_category.png', dpi=150, bbox_inches='tight')
print("  ✓ Saved: plot_2_revenue_by_category.png")
plt.close()

# ─────────────────────────────────────────
# PLOT 3: Payment Method Distribution
# ─────────────────────────────────────────
print("\nGenerating Plot 3: Payment Method Distribution...")

payment_query = """
    SELECT 
        payment_method,
        COUNT(DISTINCT transaction_id) AS num_transactions,
        ROUND(SUM(total_amount), 2) AS total_revenue
    FROM transactions
    GROUP BY payment_method
    ORDER BY num_transactions DESC
"""

payment_data = spark.sql(payment_query).toPandas()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Pie chart for transaction count
colors = sns.color_palette('Set2', len(payment_data))
ax1.pie(payment_data['num_transactions'], labels=payment_data['payment_method'], 
        autopct='%1.1f%%', colors=colors, startangle=90)
ax1.set_title('Transaction Count by Payment Method', fontsize=12, fontweight='bold')

# Bar chart for revenue
sns.barplot(data=payment_data, x='payment_method', y='total_revenue', palette='Greens_r', ax=ax2)
ax2.set_xlabel('Payment Method', fontsize=11)
ax2.set_ylabel('Total Revenue ($)', fontsize=11)
ax2.set_title('Revenue by Payment Method', fontsize=12, fontweight='bold')
ax2.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('plot_3_payment_methods.png', dpi=150, bbox_inches='tight')
print("  ✓ Saved: plot_3_payment_methods.png")
plt.close()

# ─────────────────────────────────────────
# PLOT 4: Device Type Usage & Session Stats
# ─────────────────────────────────────────
print("\nGenerating Plot 4: Device Type Usage...")

device_query = """
    SELECT 
        device_profile.type AS device_type,
        COUNT(*) AS session_count,
        ROUND(AVG(duration_seconds), 0) AS avg_duration_secs
    FROM sessions
    GROUP BY device_profile.type
    ORDER BY session_count DESC
"""

device_data = spark.sql(device_query).toPandas()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Device usage
sns.barplot(data=device_data, x='device_type', y='session_count', palette='Oranges_r', ax=ax1)
ax1.set_xlabel('Device Type', fontsize=11)
ax1.set_ylabel('Number of Sessions', fontsize=11)
ax1.set_title('Session Count by Device Type', fontsize=12, fontweight='bold')
ax1.grid(axis='y', alpha=0.3)

# Average session duration
sns.barplot(data=device_data, x='device_type', y='avg_duration_secs', palette='Purples_r', ax=ax2)
ax2.set_xlabel('Device Type', fontsize=11)
ax2.set_ylabel('Avg Duration (seconds)', fontsize=11)
ax2.set_title('Average Session Duration by Device', fontsize=12, fontweight='bold')
ax2.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('plot_4_device_usage.png', dpi=150, bbox_inches='tight')
print("  ✓ Saved: plot_4_device_usage.png")
plt.close()

# ─────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────
print("\n" + "=" * 60)
print("All 4 visualizations generated successfully:")
print("  1. plot_1_clv_distribution.png")
print("  2. plot_2_revenue_by_category.png")
print("  3. plot_3_payment_methods.png")
print("  4. plot_4_device_usage.png")
print("=" * 60)

spark.stop()