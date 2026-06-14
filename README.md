# DE Copilot

Enterprise Metadata Intelligence Platform

Transform Source-to-Target Mappings (STTM) into production-ready data engineering artifacts through a Canonical Metadata Model.

Website:
https://dataengineeringcopilot.com

---

## Vision

Data engineering teams spend significant time manually creating technical specifications, DDL, SQL, data dictionaries, DQ rules, lineage documentation, and onboarding artifacts.

DE Copilot accelerates this process by converting metadata into reusable engineering assets.

Core Principle:

STTM → Metadata Discovery Engine → Canonical Metadata Model → Artifact Factory

Build once. Generate everywhere.

---

## Current Capabilities

Upload CSV or Excel STTM files and automatically generate:

✅ Canonical Metadata Model

✅ Entity Relationship Diagram (ERD)

✅ Snowflake DDL

✅ Snowflake SQL

✅ Data Dictionary

✅ Technical Specifications

✅ Data Quality Rules

✅ AI-Powered Metadata Analysis

---

## Architecture

### Metadata Discovery Engine

Automatically discovers and maps metadata from various STTM formats.

Supports:

* CSV STTM
* Multi-sheet Excel STTM
* Alternate column naming conventions
* Rule-based metadata discovery
* LLM-assisted metadata interpretation

### Canonical Metadata Model

The Canonical Metadata Model serves as the platform's metadata abstraction layer.

Once metadata is normalized, downstream artifact generation becomes technology agnostic.

### Artifact Factory

Generates engineering deliverables directly from the Canonical Metadata Model.

Current Generators:

* Snowflake DDL
* Snowflake SQL
* Data Dictionary
* Technical Specifications
* DQ Rules
* ER Diagram
* AI Analysis

---

## Technology Stack

Frontend

* Streamlit

Backend

* Python
* Pandas

AI Layer

* OpenAI

Metadata Processing

* Canonical Metadata Model
* Rule-Based Discovery Engine
* LLM Metadata Interpreter

Visualization

* Graphviz

Deployment

* Streamlit Community Cloud

---

## Roadmap

Planned Artifact Generators:

🚀 dbt Models

🚀 Airflow DAGs

🚀 Databricks Notebooks

🚀 PySpark Pipelines

🚀 Power BI Semantic Models

🚀 Sigma Semantic Models

🚀 Monte Carlo Data Quality Rules

🚀 Automated Test Case Generation

🚀 Metadata Lineage & Impact Analysis

---

## Example Workflow

Upload STTM
↓
Metadata Discovery Engine
↓
Canonical Metadata Model
↓
ER Diagram
Snowflake DDL
Snowflake SQL
Data Dictionary
Technical Specifications
DQ Rules
AI Analysis

---

## Disclaimer

This project uses synthetic sample metadata for demonstration purposes.

No employer, client, customer, or proprietary information is included.

---

## Articles

- [From STTM to Snowflake SQL: Building a Metadata-Driven Data Engineering Copilot](https://dev.to/amising6/from-sttm-to-snowflake-sql-building-a-metadata-driven-data-engineering-copilot-n4)

## Author

Amit Singh

Creator, DE Copilot

https://dataengineeringcopilot.com