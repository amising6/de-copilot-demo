# DE Copilot

Enterprise Metadata Intelligence Platform

Transform Source-to-Target Mappings (STTM) into production-ready data engineering artifacts through a Canonical Metadata Model.

Website:
https://dataengineeringcopilot.com

---

## Why DE Copilot?

Data engineering teams repeatedly recreate the same metadata across multiple deliverables:

* Technical Specifications
* Data Dictionaries
* SQL Development
* DDL Scripts
* Data Quality Rules
* ER Diagrams
* Design Documentation

The business logic rarely changes.

The documentation does.

DE Copilot transforms STTM metadata into a Canonical Metadata Model that acts as a single source of truth for engineering delivery.

Build metadata once. Generate engineering artifacts everywhere.

---

## What Works Today

Upload a CSV or Excel STTM and automatically generate:

✅ Canonical Metadata Model

✅ Entity Relationship Diagram (ERD)

✅ Snowflake DDL

✅ Snowflake SQL

✅ Data Dictionary

✅ Technical Specifications

✅ Data Quality Rules

✅ AI-Powered Metadata Analysis

✅ Downloadable Project Package (ZIP)

---

## Architecture

STTM
↓
Metadata Discovery Engine
↓
Canonical Metadata Model
↓
Artifact Factory

The Canonical Metadata Model serves as the platform's metadata abstraction layer.

Once metadata is normalized, multiple engineering deliverables can be generated consistently from the same metadata representation.

---

## Current Platform Capabilities

### Metadata Discovery

* CSV STTM ingestion
* Multi-sheet Excel ingestion
* Alternate column name detection
* Rule-based metadata discovery
* LLM-assisted metadata interpretation

### Relationship-Aware Metadata

Supports metadata capture for:

* Primary Keys
* Foreign Keys
* Lookup Tables
* Join Conditions
* Transformation Logic
* Data Quality Rules

These relationships can be translated into generated SQL and downstream engineering artifacts.

### Artifact Factory

Current generators include:

* Snowflake DDL
* Snowflake SQL
* Data Dictionary
* Technical Specifications
* Data Quality Rules
* ER Diagrams
* AI Analysis
* ZIP Project Package

---

## Technology Stack

Frontend

* Streamlit

Backend

* Python
* Pandas

AI Layer

* OpenAI

Visualization

* Graphviz

Deployment

* Streamlit Community Cloud

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
ZIP Package

---

## Roadmap

Planned Metadata Generators:

🚀 dbt Models

🚀 Airflow DAGs

🚀 Databricks Asset Bundles

🚀 PySpark Pipelines

🚀 Power BI Semantic Models

🚀 Sigma Semantic Models

🚀 Automated Test Case Generation

🚀 Metadata Lineage & Impact Analysis

🚀 Data Contract Generation

---


## Articles

- [From STTM to Snowflake SQL: Building a Metadata-Driven Data Engineering Copilot](https://dev.to/amising6/from-sttm-to-snowflake-sql-building-a-metadata-driven-data-engineering-copilot-n4)
- [Why I Started Building Data Engineering Copilot](https://dataengineeringcopilot.hashnode.dev/why-i-started-building-data-engineering-copilot)

---

## Disclaimer

This project uses synthetic metadata and demonstration datasets only.

No employer, client, customer, or proprietary information is included.

---

## Author

Amit Singh

Creator, DE Copilot

https://dataengineeringcopilot.com
