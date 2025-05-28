# Forex Trading Analysis 🚀

This project presents a full-fledged **ETL pipeline** and **interactive dashboard** for analyzing historical **forex market trends** using modern data engineering tools.

## 🛠 Tech Stack

- **Airflow** – for ETL orchestration (DAGs)
- **Snowflake** – for raw and transformed data storage
- **Python** – for API integration and data transformation
- **Power BI** – for creating interactive dashboards
- **APIs** – [Yahoo Finance](https://pypi.org/project/yfinance/) & [GDELT](https://www.gdeltproject.org/)

---

## 🔄 ETL Pipeline (Airflow DAGs)

- **Daily Data Ingestion**
  - Forex OHLC (Open, High, Low, Close) data using `yfinance` Python package.
  - 5 years of global news metadata using the `GDELT API`.

- **Processing & Transformation**
  - Data cleaned, enriched, and structured using Python scripts.
  - Stored in dedicated Snowflake schemas for raw and transformed data.

- **Automation**
  - DAGs scheduled and monitored in Airflow.
  - Retry policies and logging ensure robust workflows.

---

## 🧊 Data Architecture

```
[Yahoo Finance / GDELT APIs]
         ↓
   [Airflow DAGs]
         ↓
     [Snowflake]
 Raw → Transformed → Modeled
         ↓
   [Power BI Dashboards]
```
---

## 🔄 Project Overview

- Developed **Airflow DAGs** to automate the ingestion of:
  - Daily **OHLC forex data** from Yahoo Finance.
  - **Five years of news metadata** from the GDELT API.
- Built a modular ETL pipeline using Python to:
  - Clean and transform data.
  - Store both raw and processed data in Snowflake.
- Connected **Power BI** directly to Snowflake to build a professional analytics dashboard including:
  - **Trend line charts** for various time frames (YoY, MoM, 5Y, 1Y, 6M, 3M, 1M, 1W).
  - **Candlestick charts** showing open, high, low, and close values per currency pair.
  - **Volatility heatmaps** across timeframes and currency pairs.
  - **Drill-through features** to explore deeper insights like daily metrics or pair-specific history.
