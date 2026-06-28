"""
AUCA Big Data Analytics Final Project
Part 3 — Integrated Analytics: Customer Lifetime Value (CLV)
Combines MongoDB transactions + HBase sessions via Spark
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pymongo import MongoClient
import json
import os

os.environ["PYSPARK_SUBMIT_ARGS"] = "--conf spark.driver.extraJavaOptions=-Dlog4j.logLevel=ERROR pyspark-shell"

spark = SparkSession.builder \
    .appName("AUCA_CLV_Analysis") \
    .master("local[*]") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

print("=" * 60)
print("PART 3 — Integrated Analytics: Customer Lifetime Value (CLV)")
print("=" * 60)

# ─────────────────────────────────────────
# LOAD TRANSACTIONS FROM MONGODB
# ─────────────────────────────────────────
print("\n--- Loading data from MongoDB ---")

client = MongoClient("mongodb://localhost:27017/")
db = client["ecommerce_db"]

# Read transactions from MongoDB
# Read transactions from MongoDB
transactions_cursor = db.transactions.find({})
transactions_list = list(transactions_cursor)
client.close()

print(f"  ✓ Loaded {len(transactions_list)} transactions from MongoDB")

# Convert ObjectId to string and remove _id for Spark serialization
for t in transactions_list:
    if '_id' in t:
        del t['_id']

# Convert to JSON strings for Spark
transactions_json = [json.dumps(t) for t in transactions_list]

# Create Spark DataFrame from MongoDB data
txn_rdd = spark.sparkContext.parallelize(transactions_json)
txn_df = spark.read.json(txn_rdd)

# ─────────────────────────────────────────
# LOAD SESSIONS DATA (FROM JSON)
# ─────────────────────────────────────────
print("  ✓ Loading sessions data...")
sessions_df = spark.read.option("multiLine", "true").json("sessions_*.json")
print(f"  ✓ Loaded {sessions_df.count()} sessions")

# ─────────────────────────────────────────
# CLEAN TRANSACTIONS
# ─────────────────────────────────────────
print("\n--- Step 1: Transaction Aggregation ---")

# Only completed transactions
txn_clean = txn_df.filter(F.col("status") == "completed") \
    .select(
        "transaction_id",
        "user_id",
        "timestamp",
        "total_amount"
    )

txn_clean.createOrReplaceTempView("transactions")

print(f"  ✓ {txn_clean.count()} completed transactions")

# ─────────────────────────────────────────
# COMPUTE CUSTOMER LIFETIME VALUE (CLV)
# ─────────────────────────────────────────
print("\n--- Step 2: CLV Calculation ---")

clv_query = """
    SELECT 
        user_id,
        COUNT(DISTINCT transaction_id)     AS purchase_frequency,
        ROUND(SUM(total_amount), 2)        AS total_revenue,
        ROUND(AVG(total_amount), 2)        AS avg_transaction_value,
        ROUND(MAX(total_amount), 2)        AS max_transaction_value,
        ROUND(MIN(total_amount), 2)        AS min_transaction_value
    FROM transactions
    GROUP BY user_id
    ORDER BY total_revenue DESC
"""

clv_df = spark.sql(clv_query)
clv_df.createOrReplaceTempView("clv_metrics")

print(f"  ✓ CLV computed for {clv_df.count()} customers")

# ─────────────────────────────────────────
# INTEGRATE WITH SESSION DATA
# ─────────────────────────────────────────
print("\n--- Step 3: Session Engagement Integration ---")

sessions_df.createOrReplaceTempView("sessions")

engagement_query = """
    SELECT 
        user_id,
        COUNT(DISTINCT session_id)        AS total_sessions,
        ROUND(AVG(duration_seconds), 0)   AS avg_session_duration,
        COUNT(DISTINCT referral_source)   AS referral_sources_used
    FROM sessions
    GROUP BY user_id
"""

engagement_df = spark.sql(engagement_query)
engagement_df.createOrReplaceTempView("engagement_metrics")

print(f"  ✓ Engagement metrics for {engagement_df.count()} users")

# ─────────────────────────────────────────
# MERGED CLV + ENGAGEMENT ANALYSIS
# ─────────────────────────────────────────
print("\n--- Step 4: Integrated CLV + Engagement Analysis ---")

merged_query = """
    SELECT 
        c.user_id,
        c.purchase_frequency,
        c.total_revenue,
        c.avg_transaction_value,
        e.total_sessions,
        e.avg_session_duration,
        ROUND(c.total_revenue / e.total_sessions, 2) AS revenue_per_session,
        ROUND(c.total_revenue / c.purchase_frequency, 2) AS clv_score
    FROM clv_metrics c
    LEFT JOIN engagement_metrics e ON c.user_id = e.user_id
    WHERE e.total_sessions IS NOT NULL
    ORDER BY c.total_revenue DESC
"""

clv_integrated = spark.sql(merged_query)

print("\n  Top 10 Customers by CLV + Engagement:")
clv_integrated.limit(10).show(truncate=False)

# ─────────────────────────────────────────
# CUSTOMER SEGMENTATION BY CLV SCORE
# ─────────────────────────────────────────
print("\n--- Step 5: Customer Segmentation ---")

segmentation_query = """
    SELECT 
        CASE 
            WHEN clv_score >= 2000 THEN 'Premium'
            WHEN clv_score >= 1200 THEN 'High Value'
            WHEN clv_score >= 600 THEN 'Medium Value'
            ELSE 'Low Value'
        END AS segment,
        COUNT(*) AS customer_count,
        ROUND(AVG(clv_score), 2) AS avg_clv_score,
        ROUND(SUM(total_revenue), 2) AS segment_revenue
    FROM (
        SELECT 
            c.user_id,
            c.purchase_frequency,
            c.total_revenue,
            c.avg_transaction_value,
            e.total_sessions,
            e.avg_session_duration,
            ROUND(c.total_revenue / e.total_sessions, 2) AS revenue_per_session,
            ROUND(c.total_revenue / c.purchase_frequency, 2) AS clv_score
        FROM clv_metrics c
        LEFT JOIN engagement_metrics e ON c.user_id = e.user_id
        WHERE e.total_sessions IS NOT NULL
    )
    GROUP BY segment
    ORDER BY avg_clv_score DESC
"""

segmentation_df = spark.sql(segmentation_query)

print("\n  Customer Segmentation by CLV:")
segmentation_df.show(truncate=False)

# ─────────────────────────────────────────
# SUMMARY STATISTICS
# ─────────────────────────────────────────
print("\n--- Summary Statistics ---")

summary_query = """
    SELECT 
        ROUND(AVG(clv_score), 2) AS avg_clv,
        ROUND(MAX(clv_score), 2) AS max_clv,
        ROUND(MIN(clv_score), 2) AS min_clv,
        ROUND(AVG(total_revenue), 2) AS avg_customer_revenue,
        ROUND(AVG(purchase_frequency), 1) AS avg_purchases_per_customer
    FROM (
        SELECT 
            c.user_id,
            c.purchase_frequency,
            c.total_revenue,
            c.avg_transaction_value,
            e.total_sessions,
            ROUND(c.total_revenue / c.purchase_frequency, 2) AS clv_score
        FROM clv_metrics c
        LEFT JOIN engagement_metrics e ON c.user_id = e.user_id
        WHERE e.total_sessions IS NOT NULL
    )
"""

summary_df = spark.sql(summary_query)
summary_df.show(truncate=False)

print("\nPart 3 complete.")
spark.stop()