"""
AUCA Big Data Analytics Final Project
Part 2 — Spark Batch Processing + Spark SQL
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *
import os

# Suppress verbose logs
os.environ["PYSPARK_SUBMIT_ARGS"] = "--conf spark.driver.extraJavaOptions=-Dlog4j.logLevel=ERROR pyspark-shell"

spark = SparkSession.builder \
    .appName("AUCA_BigData_Part2") \
    .master("local[*]") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

print("=" * 55)
print("PART 2 — Spark Batch Processing")
print("=" * 55)

# ─────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────
print("\nLoading data...")
transactions_df = spark.read.option("multiLine", "true").json("transactions.json")
products_df     = spark.read.option("multiLine", "true").json("products.json")
users_df        = spark.read.option("multiLine", "true").json("users.json")
sessions_df     = spark.read.option("multiLine", "true").json("sessions_*.json")

print(f"  ✓ Transactions : {transactions_df.count()}")
print(f"  ✓ Products     : {products_df.count()}")
print(f"  ✓ Users        : {users_df.count()}")
print(f"  ✓ Sessions     : {sessions_df.count()}")

# ─────────────────────────────────────────
# STEP 1: CLEAN & NORMALIZE TRANSACTIONS
# ─────────────────────────────────────────
print("\n--- Step 1: Clean & Normalize Transactions ---")

# Explode items array so each row = one product in one transaction
txn_items = transactions_df \
    .filter(F.col("status") == "completed") \
    .select(
        "transaction_id",
        "user_id",
        "timestamp",
        "payment_method",
        "total_amount",
        F.explode("items").alias("item")
    ) \
    .select(
        "transaction_id",
        "user_id",
        "timestamp",
        "payment_method",
        "total_amount",
        F.col("item.product_id").alias("product_id"),
        F.col("item.category_id").alias("category_id"),
        F.col("item.quantity").alias("quantity"),
        F.col("item.unit_price").alias("unit_price"),
        F.col("item.discount").alias("discount"),
        F.col("item.line_total").alias("line_total")
    )

print(f"  ✓ Completed transaction items: {txn_items.count()}")

# ─────────────────────────────────────────
# STEP 2: CO-PURCHASE INDICATORS
# ─────────────────────────────────────────
print("\n--- Step 2: Co-Purchase Indicators ---")

# Find products that appear together in the same transaction
txn_a = txn_items.select("transaction_id", F.col("product_id").alias("product_a"))
txn_b = txn_items.select("transaction_id", F.col("product_id").alias("product_b"))

copurchase = txn_a.join(txn_b, "transaction_id") \
    .filter(F.col("product_a") < F.col("product_b")) \
    .groupBy("product_a", "product_b") \
    .agg(F.count("*").alias("co_purchase_count")) \
    .orderBy(F.desc("co_purchase_count"))

print("  Top 5 co-purchased product pairs:")
copurchase.show(5, truncate=False)

# ─────────────────────────────────────────
# STEP 3: SPARK SQL QUERIES
# ─────────────────────────────────────────
print("\n--- Step 3: Spark SQL Queries ---")

# Register temp views
txn_items.createOrReplaceTempView("txn_items")
products_df.createOrReplaceTempView("products")
users_df.createOrReplaceTempView("users")
sessions_df.createOrReplaceTempView("sessions")

# SQL Query 1: Revenue by category
print("\n  SQL Q1: Total revenue by category (top 5):")
q1 = spark.sql("""
    SELECT category_id,
           ROUND(SUM(line_total), 2) AS total_revenue,
           COUNT(DISTINCT transaction_id)  AS num_transactions,
           ROUND(AVG(unit_price), 2)       AS avg_unit_price
    FROM   txn_items
    GROUP  BY category_id
    ORDER  BY total_revenue DESC
    LIMIT  5
""")
q1.show(truncate=False)

# SQL Query 2: Top 5 users by spending
print("  SQL Q2: Top 5 users by total spending:")
q2 = spark.sql("""
    SELECT t.user_id,
           ROUND(SUM(t.line_total), 2) AS total_spent,
           COUNT(DISTINCT t.transaction_id) AS num_transactions
    FROM   txn_items t
    GROUP  BY t.user_id
    ORDER  BY total_spent DESC
    LIMIT  5
""")
q2.show(truncate=False)

# SQL Query 3: Most popular payment methods
print("  SQL Q3: Payment method distribution:")
q3 = spark.sql("""
    SELECT payment_method,
           COUNT(DISTINCT transaction_id) AS num_transactions,
           ROUND(SUM(line_total), 2)      AS total_revenue
    FROM   txn_items
    GROUP  BY payment_method
    ORDER  BY num_transactions DESC
""")
q3.show(truncate=False)

# SQL Query 4: Session device breakdown
print("  SQL Q4: Device type usage from sessions:")
q4 = spark.sql("""
    SELECT device_profile.type AS device_type,
           COUNT(*) AS session_count,
           ROUND(AVG(duration_seconds), 0) AS avg_duration_secs
    FROM   sessions
    GROUP  BY device_profile.type
    ORDER  BY session_count DESC
""")
q4.show(truncate=False)

print("\nPart 2 complete.")
spark.stop()