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
  - Forex OHLC data using `yfinance` Python package.
  - 5 years of global news metadata using the `GDELT API`.

- **Processing & Transformation**
  - Data cleaned, enriched, and structured using Python scripts.
  - Stored in dedicated Snowflake schemas for raw and transformed data.

- **Automation**
  - DAGs scheduled and monitored in Airflow.
  - Retry policies and logging ensure robust workflows.

---

## 🧊 Data Architecture

```plaintext
[Yahoo Finance / GDELT APIs]
         ↓
   [Airflow DAGs]
         ↓
     [Snowflake]
 Raw → Transformed → Modeled
         ↓
   [Power BI Dashboards]
