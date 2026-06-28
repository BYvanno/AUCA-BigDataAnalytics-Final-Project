# AUCA Big Data Analytics Final Project
**Author:** BYIRINGIRO Elie Yvan | **Reg:** 101219

## Stack
MongoDB • HBase • Apache Spark (PySpark) • Python 3.14 • Ubuntu WSL2

## Project Structure
- dataset_generator.py — Synthetic e-commerce dataset generator
- mongo_load.py — MongoDB data loading
- mongo_aggregations.py — MongoDB aggregation pipelines
- hbase_simulation.py — HBase wide-column simulation
- spark_batch.py — Spark batch processing + SQL queries
- spark_clv.py — Integrated CLV analytics (Part 3)
- spark_visualizations.py — 4 visualization plots (Part 4)

## How to Run
1. Start MongoDB: sudo service mongod start
2. Run scripts in order: dataset_generator → mongo_load → mongo_aggregations → hbase_simulation → spark_batch → spark_clv → spark_visualizations