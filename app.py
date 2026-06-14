import json
import re
from typing import Dict, List, Optional, Tuple
import graphviz

import pandas as pd
import streamlit as st
from openai import OpenAI

# ==================================================
# STREAMLIT CONFIG
# ==================================================
st.set_page_config(
    page_title="DE Copilot",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ DE Copilot")

st.markdown(
"""

### Enterprise Metadata Intelligence Platform

**Architecture**

STTM → Metadata Discovery Engine → Canonical Metadata Model → Artifact Factory

Transform complex source-to-target mappings into production-ready data engineering assets in minutes.

Upload a CSV or Excel STTM and automatically generate:

✅ Canonical Metadata Model

✅ Entity Relationship Diagram (ERD)

✅ Snowflake DDL

✅ Snowflake SQL

✅ Data Dictionary

✅ Technical Specifications

✅ Data Quality Rules

✅ AI-Powered Metadata Analysis

---

### Why DE Copilot?

A technology-agnostic metadata platform that transforms STTM metadata into reusable engineering artifacts through a Canonical Metadata Model.

Build once. Generate everywhere.

A Canonical Metadata Model enables consistent generation of engineering artifacts from a single source of truth.

"""
)
# ==================================================
# Sample STTM
# ==================================================

st.subheader("📂 Sample STTM Files")

st.markdown("""
Use the sample files below to explore DE Copilot capabilities before uploading your own STTM.

**Available Samples**

📄 Basic STTM  
- Single table example
- Canonical Metadata Model
- Snowflake DDL
- Snowflake SQL
- DQ Rules

🛒 Retail Multi-Table STTM  
- Customer, Product, Order model
- ER Diagram
- Multi-table DDL
- SQL Generation

🏦 Banking Multi-Sheet STTM  
- Customer, Account, Transaction, Branch
- Multi-sheet ingestion
- Canonical Metadata Model
- ER Diagram
- Technical Specifications

🔗 Join Example STTM
- Lookup tables
- Join conditions
- Relationship metadata
- Future SQL generation
""")

from pathlib import Path

sample_files = {
    "📄 Download Basic STTM":
        "samples/sample_sttm_basic.csv",

    "🛒 Download Retail STTM":
        "samples/sample_sttm_retail.xlsx",

    "🏦 Download Banking STTM":
        "samples/sample_sttm_banking_multisheet.xlsx",

    "🔗 Download Join Example STTM":
        "samples/sample_sttm_join_example.xlsx"
}

for label, file_path in sample_files.items():

    path = Path(file_path)

    if path.exists():

        with open(path, "rb") as f:

            st.download_button(
                label=label,
                data=f,
                file_name=path.name
            )
# ==================================================
# OPENAI CLIENT
# ==================================================
def get_openai_client():
    try:
        return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except Exception:
        return None


client = get_openai_client()

# ==================================================
# CANONICAL MODEL
# ==================================================
CANONICAL_FIELDS = [
    "source_system",
    "source_database",
    "source_schema",
    "source_table",
    "source_column",
    "source_datatype",
    "source_nullable",
    "source_pk",
    "source_fk",
    "target_system",
    "target_database",
    "target_schema",
    "target_table",
    "target_column",
    "target_datatype",
    "target_length",
    "target_precision",
    "target_scale",
    "target_nullable",
    "target_pk",
    "target_fk",
    "business_definition",
    "transformation_type",
    "transformation_logic",
    "lookup_table",
    "lookup_join_condition",
    "filter_condition",
    "dq_rule",
    "dq_severity",
    "dq_action",
    "scd_type",
    "effective_date_column",
    "end_date_column",
    "current_flag_column",
    "pii_flag",
    "data_masking_rule",
    "owner",
    "approval_status",
    "release",
    "notes",
    "lookup_column",
    "join_type",
]

REQUIRED_CANONICAL_FIELDS = [
    "target_table",
    "target_column",
]

RECOMMENDED_CANONICAL_FIELDS = [
    "source_table",
    "source_column",
    "target_datatype",
]

COLUMN_ALIASES: Dict[str, List[str]] = {
    "source_system": ["SOURCE_SYSTEM", "SOURCE_SYSTEM_NAME", "SRC_SYSTEM", "ORIGIN_SYSTEM"],
    "source_database": ["SOURCE_DATABASE", "SRC_DATABASE", "ORIGIN_DATABASE"],
    "source_schema": ["SOURCE_SCHEMA", "SRC_SCHEMA", "ORIGIN_SCHEMA"],
    "source_table": [
        "SOURCE_TABLE", "SOURCE_TABLE_NAME", "SOURCE_TABLE_VIEW", "SOURCE_TABLE_PHYSICAL_NAME",
        "SRC_TABLE", "SRC_TABLE_NAME", "SRC_ENTITY", "SOURCE_ENTITY", "ORIGIN_ENTITY",
        "FROM_TABLE", "INPUT_TABLE", "SOURCE_OBJECT", "SRC_OBJECT",
    ],
    "source_column": [
        "SOURCE_COLUMN", "SOURCE_COLUMN_NAME", "SOURCE_COLUMN_PHYSICAL_NAME",
        "SRC_COLUMN", "SRC_COLUMN_NAME", "SOURCE_FIELD", "SRC_FIELD", "SOURCE_ATTRIBUTE",
        "SRC_ATTRIBUTE", "ORIGIN_ATTRIBUTE", "ORIGIN_FIELD", "FROM_COLUMN", "INPUT_COLUMN",
    ],
    "source_datatype": [
        "SOURCE_DATA_TYPE", "SOURCE_DATATYPE", "SRC_DATA_TYPE", "SRC_DATATYPE", "SOURCE_TYPE",
    ],
    "source_nullable": ["SOURCE_NULLABLE", "SOURCE_IS_NULLABLE", "SRC_NULLABLE", "SRC_IS_NULLABLE"],
    "source_pk": ["SOURCE_PK", "SOURCE_IS_PK", "SRC_PK", "SRC_PRIMARY_KEY"],
    "source_fk": ["SOURCE_FK", "SOURCE_IS_FK", "SRC_FK", "SRC_FOREIGN_KEY"],
    "target_system": ["TARGET_SYSTEM", "TARGET_SYSTEM_NAME", "TGT_SYSTEM", "DESTINATION_SYSTEM"],
    "target_database": ["TARGET_DATABASE", "TGT_DATABASE", "DESTINATION_DATABASE"],
    "target_schema": ["TARGET_SCHEMA", "TGT_SCHEMA", "DESTINATION_SCHEMA"],
    "target_table": [
        "TARGET_TABLE", "TARGET_TABLE_NAME", "TARGET_TABLE_PHYSICAL_NAME", "TARGET_TABLE_LOGICAL_NAME",
        "TGT_TABLE", "TGT_TABLE_NAME", "DESTINATION_TABLE", "DEST_TABLE", "DESTINATION_ENTITY",
        "TARGET_ENTITY", "OUTPUT_TABLE", "TO_TABLE", "TARGET_OBJECT", "TGT_OBJECT",
    ],
    "target_column": [
        "TARGET_COLUMN", "TARGET_COLUMN_NAME", "TARGET_COLUMN_PHYSICAL_NAME",
        "TGT_COLUMN", "TGT_COLUMN_NAME", "TARGET_FIELD", "TGT_FIELD", "DESTINATION_COLUMN",
        "DEST_COLUMN", "DESTINATION_ATTRIBUTE", "TARGET_ATTRIBUTE", "OUTPUT_COLUMN", "TO_COLUMN",
    ],
    "target_datatype": [
        "TARGET_DATA_TYPE", "TARGET_DATATYPE", "TGT_DATA_TYPE", "TGT_DATATYPE",
        "DATA_TYPE", "DATATYPE", "TARGET_TYPE", "COLUMN_TYPE",
    ],
    "target_length": ["TARGET_LENGTH", "LENGTH", "TARGET_COLUMN_LENGTH", "COLUMN_LENGTH", "SIZE"],
    "target_precision": ["TARGET_PRECISION", "PRECISION", "NUMERIC_PRECISION"],
    "target_scale": ["TARGET_SCALE", "SCALE", "NUMERIC_SCALE"],
    "target_nullable": ["TARGET_NULLABLE", "TARGET_IS_NULLABLE", "NULLABLE", "IS_NULLABLE", "TGT_NULLABLE"],
    "target_pk": ["TARGET_PK", "TARGET_IS_PK", "PRIMARY_KEY", "IS_PK", "TGT_PK"],
    "target_fk": ["TARGET_FK", "TARGET_IS_FK", "FOREIGN_KEY", "IS_FK", "TGT_FK"],
    "business_definition": [
        "BUSINESS_DEFINITION", "BUSINESS_RULE_DESCRIPTION", "SOURCE_DESCRIPTION", "TARGET_DESCRIPTION",
        "COLUMN_DESCRIPTION", "DESCRIPTION", "BUSINESS_DESCRIPTION", "DEFINITION",
    ],
    "transformation_type": ["TRANSFORMATION_TYPE", "TRANSFORM_TYPE", "MAPPING_TYPE", "RULE_TYPE"],
    "transformation_logic": [
        "TRANSFORMATION_LOGIC", "TRANSFORMATION_RULE", "RULE", "LOGIC", "DERIVATION_LOGIC",
        "BUSINESS_RULE", "EXPRESSION", "CALCULATION", "FORMULA", "MAPPING_RULE",
    ],
    "lookup_table": ["LOOKUP_TABLE", "LOOKUP_TABLE_NAME", "REFERENCE_TABLE", "REF_TABLE"],
    "lookup_join_condition": ["LOOKUP_JOIN_CONDITION", "LOOKUP_CONDITION", "JOIN_CONDITION", "JOIN_RULE"],
    "filter_condition": ["FILTER_CONDITION", "WHERE_CONDITION", "FILTER", "WHERE_CLAUSE"],
    "dq_rule": ["DQ_RULE", "DATA_QUALITY_RULE", "DATA_QUALITY_RULE_DESCRIPTION", "VALIDATION_RULE", "QUALITY_RULE"],
    "dq_severity": ["DQ_SEVERITY", "SEVERITY", "ERROR_SEVERITY"],
    "dq_action": ["DQ_ACTION", "DQ_FAILURE_ACTION", "ERROR_ACTION", "FAILURE_ACTION"],
    "scd_type": ["SCD_TYPE", "SCD", "SLOWLY_CHANGING_DIMENSION_TYPE"],
    "effective_date_column": ["EFFECTIVE_DATE_COLUMN", "SCD_EFFECTIVE_DATE_COLUMN", "EFF_DATE_COLUMN"],
    "end_date_column": ["END_DATE_COLUMN", "SCD_END_DATE_COLUMN", "EXPIRY_DATE_COLUMN"],
    "current_flag_column": ["CURRENT_FLAG_COLUMN", "SCD_CURRENT_FLAG_COLUMN", "ACTIVE_FLAG_COLUMN"],
    "pii_flag": ["PII_FLAG", "IS_PII", "IS_PII_TARGET", "IS_PII_SOURCE", "SENSITIVE_FLAG"],
    "data_masking_rule": ["DATA_MASKING_RULE", "MASKING_RULE", "MASK_RULE"],
    "owner": ["OWNER", "MAPPING_OWNER", "TECHNICAL_LEAD", "DATA_OWNER"],
    "approval_status": ["APPROVAL_STATUS", "STTM_STATUS", "QA_STATUS", "STATUS"],
    "release": ["RELEASE", "PHASE_RELEASE", "SPRINT_ID", "VERSION"],
    "notes": ["NOTES", "NOTES_COMMENTS", "COMMENTS", "COMMENT", "REMARKS"],
}

# ==================================================
# NORMALIZATION HELPERS
# ==================================================
def normalize_column_name(col: str) -> str:
    col = str(col).strip().upper()
    col = re.sub(r"[^A-Z0-9]+", "_", col)
    col = re.sub(r"_+", "_", col).strip("_")
    return col


def normalize_input_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [normalize_column_name(col) for col in normalized.columns]
    return normalized


def clean_value(value, default: str = "") -> str:
    if pd.isna(value):
        return default
    value = str(value).strip()
    if value.lower() in ["nan", "none", "null"]:
        return default
    return value


def safe_cell(row: pd.Series, col: Optional[str], default: str = "") -> str:
    if col and col in row.index:
        return clean_value(row[col], default)
    return default


def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    cols = set(df.columns)
    for alias in aliases:
        alias_normalized = normalize_column_name(alias)
        if alias_normalized in cols:
            return alias_normalized
    return None


def rule_based_column_mapping(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    return {field: find_column(df, aliases) for field, aliases in COLUMN_ALIASES.items()}


def mapping_score(mapping: Dict[str, Optional[str]]) -> Tuple[float, List[str], List[str]]:
    required_missing = [field for field in REQUIRED_CANONICAL_FIELDS if not mapping.get(field)]
    recommended_missing = [field for field in RECOMMENDED_CANONICAL_FIELDS if not mapping.get(field)]
    total_important = len(REQUIRED_CANONICAL_FIELDS) + len(RECOMMENDED_CANONICAL_FIELDS)
    matched = total_important - len(required_missing) - len(recommended_missing)
    score = matched / total_important if total_important else 1.0
    return score, required_missing, recommended_missing


def extract_json_object(text: str) -> Dict:
    text = text.strip()
    if text.startswith("```json"):
        text = text.replace("```json", "", 1).replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))

# ==================================================
# LLM COLUMN INTERPRETER - PRODUCTION SAFE
# ==================================================
def llm_assisted_column_mapping(df: pd.DataFrame, base_mapping: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """
    LLM only maps uploaded column names to canonical field names.
    It does NOT generate row-level canonical records.
    Python remains responsible for building every canonical row.
    """
    if client is None:
        return base_mapping

    unresolved_fields = [field for field in CANONICAL_FIELDS if not base_mapping.get(field)]
    if not unresolved_fields:
        return base_mapping

    metadata_sample = {
        "uploaded_columns": list(df.columns),
        "row_count": int(len(df)),
        "sample_rows": df.head(5).astype(str).to_dict(orient="records"),
        "canonical_fields_to_map": unresolved_fields,
    }

    prompt = f"""
You are an enterprise data engineering metadata interpreter.

Your job is ONLY to map uploaded STTM column names to canonical metadata field names.
Do NOT create row-level mappings.
Do NOT invent values.
Only return uploaded column names that exist in uploaded_columns.

Canonical fields:
{CANONICAL_FIELDS}

Uploaded STTM metadata:
{json.dumps(metadata_sample, indent=2)}

Return ONLY valid JSON object in this exact shape:
{{
  "source_table": "UPLOADED_COLUMN_NAME_OR_NULL",
  "source_column": "UPLOADED_COLUMN_NAME_OR_NULL",
  "target_table": "UPLOADED_COLUMN_NAME_OR_NULL",
  "target_column": "UPLOADED_COLUMN_NAME_OR_NULL",
  "target_datatype": "UPLOADED_COLUMN_NAME_OR_NULL"
}}

Rules:
1. Keys must be canonical field names.
2. Values must be uploaded column names from uploaded_columns or null.
3. Include all canonical fields, even if value is null.
4. Return JSON only.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You map messy STTM column names to a canonical metadata schema."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        parsed = extract_json_object(response.choices[0].message.content)
        merged = base_mapping.copy()
        available_cols = set(df.columns)

        for field in CANONICAL_FIELDS:
            if merged.get(field):
                continue
            raw_value = parsed.get(field)
            if raw_value is None or raw_value == "":
                continue
            normalized_value = normalize_column_name(raw_value)
            if normalized_value in available_cols:
                merged[field] = normalized_value

        return merged
    except Exception as exc:
        st.warning(f"LLM column interpretation failed. Continuing with rule-based mapping. Details: {exc}")
        return base_mapping

# ==================================================
# CANONICAL MODEL BUILDER
# ==================================================
def build_canonical_model(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]], str, List[str], List[str]]:
    rule_mapping = rule_based_column_mapping(df)
    score_before, required_missing_before, _ = mapping_score(rule_mapping)

    mapping_source = "Rule-Based Metadata Discovery"
    final_mapping = rule_mapping

    if required_missing_before or score_before < 0.85:
        final_mapping = llm_assisted_column_mapping(df, rule_mapping)
        mapping_source = "Rule-Based + LLM Metadata Interpreter"

    normalized_df = build_normalized_sttm(df, final_mapping)
    _, required_missing, recommended_missing = mapping_score(final_mapping)

    return normalized_df, final_mapping, mapping_source, required_missing, recommended_missing


def build_normalized_sttm(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    rows = []

    for _, row in df.iterrows():
        normalized_row = {}
        for field in CANONICAL_FIELDS:
            source_col = mapping.get(field)
            normalized_row[field] = safe_cell(row, source_col)
        rows.append(normalized_row)

    normalized_df = pd.DataFrame(rows)

    for field in CANONICAL_FIELDS:
        if field not in normalized_df.columns:
            normalized_df[field] = ""

    normalized_df = normalized_df[CANONICAL_FIELDS]
    normalized_df = normalized_df[normalized_df["target_column"].astype(str).str.strip() != ""]
    normalized_df = normalized_df.drop_duplicates().reset_index(drop=True)

    return normalized_df

# ==================================================
# VALIDATION ENGINE
# ==================================================
def validate_canonical_model(normalized_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, int]:
    errors = []
    warnings = []

    if normalized_df.empty:
        errors.append({"Severity": "ERROR", "Issue": "Canonical model is empty", "Recommendation": "Check target table/column mapping."})
        return pd.DataFrame(errors), pd.DataFrame(warnings), 0

    for field in REQUIRED_CANONICAL_FIELDS:
        missing_count = int((normalized_df[field].astype(str).str.strip() == "").sum())
        if missing_count > 0:
            errors.append({
                "Severity": "ERROR",
                "Issue": f"Missing required field: {field}",
                "Count": missing_count,
                "Recommendation": f"Map a valid STTM column to {field}.",
            })

    for field in RECOMMENDED_CANONICAL_FIELDS:
        missing_count = int((normalized_df[field].astype(str).str.strip() == "").sum())
        if missing_count > 0:
            warnings.append({
                "Severity": "WARNING",
                "Issue": f"Missing recommended field: {field}",
                "Count": missing_count,
                "Recommendation": f"Add or map {field} for better generated artifacts.",
            })

    duplicate_count = int(normalized_df.duplicated(subset=["target_table", "target_column"]).sum())
    if duplicate_count > 0:
        warnings.append({
            "Severity": "WARNING",
            "Issue": "Duplicate target table/column mappings found",
            "Count": duplicate_count,
            "Recommendation": "Review duplicate target mappings before production deployment.",
        })

    invalid_dtype_count = int((normalized_df["target_datatype"].astype(str).str.strip() == "").sum())
    if invalid_dtype_count > 0:
        warnings.append({
            "Severity": "WARNING",
            "Issue": "Missing target datatype",
            "Count": invalid_dtype_count,
            "Recommendation": "Default VARCHAR will be used where datatype is missing.",
        })

    total_checks = len(REQUIRED_CANONICAL_FIELDS) + len(RECOMMENDED_CANONICAL_FIELDS) + 2
    failed_checks = len(errors) + len(warnings)
    quality_score = max(0, int(((total_checks - failed_checks) / total_checks) * 100))

    return pd.DataFrame(errors), pd.DataFrame(warnings), quality_score

# ==================================================
# GENERATORS
# ==================================================
def quote_identifier(identifier: str) -> str:
    identifier = clean_value(identifier)
    if not identifier:
        return identifier
    return identifier


def snowflake_type(row: pd.Series) -> str:
    dtype = safe_cell(row, "target_datatype", "VARCHAR").upper()
    length = safe_cell(row, "target_length")
    precision = safe_cell(row, "target_precision")
    scale = safe_cell(row, "target_scale")

    if dtype in ["VARCHAR2", "STRING", "TEXT", "CHAR", "CHARACTER"]:
        dtype = "VARCHAR"

    if dtype == "VARCHAR":
        if length and length.upper() not in ["0", "N/A", "NA", "NONE", "NULL"]:
            return f"VARCHAR({length})"
        return "VARCHAR"

    if dtype in ["NUMBER", "NUMERIC", "DECIMAL"]:
        if precision and scale and precision.upper() not in ["0", "N/A", "NA", "NONE", "NULL"]:
            return f"NUMBER({precision},{scale})"
        if precision and precision.upper() not in ["0", "N/A", "NA", "NONE", "NULL"]:
            return f"NUMBER({precision})"
        return "NUMBER"

    if dtype in ["DATE"]:
        return "DATE"

    if dtype in ["TIMESTAMP", "DATETIME", "TIMESTAMP_NTZ"]:
        return "TIMESTAMP_NTZ"

    if dtype in ["BOOLEAN", "BOOL"]:
        return "BOOLEAN"

    if not dtype:
        return "VARCHAR"

    return dtype

def generate_er_diagram(normalized_df):

    tables = {}

    for target_table, group in normalized_df.groupby("target_table"):

        columns = []

        for _, row in group.iterrows():

            col_name = safe_cell(row, "target_column")

            pk = safe_cell(row, "target_pk").upper()
            fk = safe_cell(row, "target_fk").upper()

            prefix = ""

            if pk in ["Y", "YES", "TRUE", "1"]:
                prefix = "PK "

            elif fk in ["Y", "YES", "TRUE", "1"]:
                prefix = "FK "

            columns.append(f"{prefix}{col_name}")

        tables[target_table] = columns

    output = []

    for table, cols in tables.items():

        output.append(f"\n[{table}]")

        for col in cols:
            output.append(f"  - {col}")

    return "\n".join(output)

def generate_graphviz_erd(normalized_df):

    lines = [
        "digraph ERD {",
        "rankdir=LR;",
        'node [shape=box];'
    ]

    tables = sorted(
        normalized_df["target_table"]
        .dropna()
        .astype(str)
        .unique()
    )

    # Create nodes
    for table in tables:
        if table.strip():
            lines.append(f'"{table}";')

    # Build FK relationships
    for _, row in normalized_df.iterrows():

        fk_flag = safe_cell(row, "target_fk").upper()

        if fk_flag not in ["Y", "YES", "TRUE", "1"]:
            continue

        parent_table = safe_cell(row, "source_table")
        child_table = safe_cell(row, "target_table")

        if parent_table and child_table:
            lines.append(
                f'"{parent_table}" -> "{child_table}";'
            )

    lines.append("}")

    return "\n".join(lines)


def generate_ddl(normalized_df: pd.DataFrame) -> str:
    if normalized_df.empty:
        return "-- No valid target columns found."

    ddl_blocks = []

    for target_table, group in normalized_df.groupby("target_table", dropna=False):
        target_table = quote_identifier(target_table) or "TARGET_TABLE"
        column_lines = []
        seen_columns = set()

        for _, row in group.iterrows():
            col_name = quote_identifier(safe_cell(row, "target_column"))
            if not col_name or col_name in seen_columns:
                continue
            seen_columns.add(col_name)

            data_type = snowflake_type(row)
            nullable = safe_cell(row, "target_nullable").upper()
            not_null = " NOT NULL" if nullable in ["N", "NO", "FALSE", "0"] else ""
            column_lines.append(f"    {col_name} {data_type}{not_null}")

        if not column_lines:
            continue

        ddl = f"""CREATE OR REPLACE TABLE {target_table}
(
{",\n".join(column_lines)}
);"""
        ddl_blocks.append(ddl)

    return "\n\n".join(ddl_blocks) if ddl_blocks else "-- No valid DDL could be generated."


def generate_sql(normalized_df: pd.DataFrame) -> str:
    if normalized_df.empty:
        return "-- No valid mappings found."

    sql_blocks = []

    for target_table, group in normalized_df.groupby("target_table", dropna=False):

        target_table = quote_identifier(target_table) or "TARGET_TABLE"

        source_table_values = (
            group["source_table"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        source_table_values = source_table_values[source_table_values != ""]

        source_table_name = (
            quote_identifier(source_table_values.iloc[0])
            if not source_table_values.empty
            else "SOURCE_TABLE"
        )

        select_lines = []
        seen_targets = set()

        for _, row in group.iterrows():

            source_col = quote_identifier(
                safe_cell(row, "source_column")
            )

            target_col = quote_identifier(
                safe_cell(row, "target_column")
            )

            logic = safe_cell(
                row,
                "transformation_logic"
            )

            if not target_col or target_col in seen_targets:
                continue

            seen_targets.add(target_col)

            if logic and logic.upper() not in [
                "DIRECT",
                "DIRECT MAPPING",
                "N/A",
                "NA",
                "NONE",
                "NULL"
            ]:
                select_expr = logic

            elif source_col:
                select_expr = source_col

            else:
                select_expr = (
                    f"NULL /* missing source for {target_col} */"
                )

            select_lines.append(
                f"    {select_expr} AS {target_col}"
            )

        if not select_lines:
            continue

        # ---------------------------
        # JOIN SUPPORT
        # ---------------------------

        lookup_tables = (
            group["lookup_table"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        lookup_tables = lookup_tables[
            lookup_tables != ""
        ]

        join_conditions = (
            group["lookup_join_condition"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        join_conditions = join_conditions[
            join_conditions != ""
        ]

        from_clause = f"FROM {source_table_name}"

        if (
            not lookup_tables.empty
            and not join_conditions.empty
        ):

            lookup_table = quote_identifier(
                lookup_tables.iloc[0]
            )

            join_condition = (
                join_conditions.iloc[0]
            )

            from_clause += f"""
LEFT JOIN {lookup_table}
    ON {join_condition}
"""

        sql = f"""INSERT INTO {target_table}
SELECT
{",\n".join(select_lines)}
{from_clause};"""

        sql_blocks.append(sql)

    return (
        "\n\n".join(sql_blocks)
        if sql_blocks
        else "-- No valid SQL could be generated."
    )

def generate_data_dictionary(normalized_df: pd.DataFrame) -> pd.DataFrame:
    dictionary_df = normalized_df[
        [
            "target_table", "target_column", "target_datatype", "target_length", "target_precision",
            "target_scale", "target_nullable", "target_pk", "business_definition", "pii_flag", "data_masking_rule",
        ]
    ].copy()

    dictionary_df.columns = [
        "Target Table", "Target Column", "Data Type", "Length", "Precision", "Scale",
        "Nullable", "Primary Key", "Business Definition", "PII Flag", "Data Masking Rule",
    ]
    return dictionary_df


def generate_tech_spec(normalized_df: pd.DataFrame) -> pd.DataFrame:
    tech_df = normalized_df[
        [
            "source_system", "source_table", "source_column", "target_table", "target_column",
            "target_datatype", "target_nullable", "transformation_type", "transformation_logic",
            "lookup_table", "lookup_join_condition", "filter_condition", "dq_rule", "scd_type",
            "owner", "approval_status", "release", "notes",
        ]
    ].copy()

    tech_df.columns = [
        "Source System", "Source Table", "Source Column", "Target Table", "Target Column",
        "Target Data Type", "Nullable", "Transformation Type", "Transformation Logic", "Lookup Table",
        "Lookup Join Condition", "Filter Condition", "DQ Rule", "SCD Type", "Owner",
        "Approval Status", "Release", "Notes",
    ]
    return tech_df


def generate_dq_rules(normalized_df: pd.DataFrame) -> pd.DataFrame:
    dq_rows = []

    for _, row in normalized_df.iterrows():
        target_table = safe_cell(row, "target_table")
        target_col = safe_cell(row, "target_column")
        nullable = safe_cell(row, "target_nullable").upper()
        pk = safe_cell(row, "target_pk").upper()
        dq_rule = safe_cell(row, "dq_rule")
        severity = safe_cell(row, "dq_severity", "MEDIUM")
        action = safe_cell(row, "dq_action", "Flag Record")

        generated_rules = []
        if nullable in ["N", "NO", "FALSE", "0"]:
            generated_rules.append(f"{target_col} must not be null")
        if pk in ["Y", "YES", "TRUE", "1"]:
            generated_rules.append(f"{target_col} must be unique")
        if dq_rule:
            generated_rules.append(dq_rule)
        if not generated_rules:
            generated_rules.append("No explicit DQ rule provided")

        dq_rows.append({
            "Target Table": target_table,
            "Target Column": target_col,
            "DQ Rule": "; ".join(generated_rules),
            "Severity": severity,
            "Action": action,
        })

    return pd.DataFrame(dq_rows)


def generate_ai_analysis(normalized_df: pd.DataFrame) -> str:
    if client is None:
        return "OpenAI API key is not configured. Add OPENAI_API_KEY in Streamlit Secrets."

    sample_data = normalized_df.head(100).to_csv(index=False)

    prompt = f"""
You are a Senior Data Architect.

Analyze this Canonical Metadata Model generated from an enterprise STTM.

Provide:

1. Executive Summary
2. Business Purpose
3. Source & Target Analysis
4. Relationship & Join Analysis
5. Primary Key Recommendations
6. Data Quality Recommendations
7. Suggested Test Cases
8. Risks
9. Improvement Opportunities

Relationship Analysis Instructions:

- If lookup_table exists, identify lookup dependencies.
- If lookup_join_condition exists, analyze join complexity.
- Identify potential referential integrity issues.
- Highlight missing foreign key relationships.
- Recommend performance optimizations for joins.
- Identify potential data quality risks caused by lookup failures.
- Suggest validation checks for lookup and join logic.

Canonical Metadata Model Sample:

{sample_data}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content

# ==================================================
# FILE READER
# ==================================================
def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    filename = uploaded_file.name.lower()
    if filename.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    raise ValueError("Unsupported file type. Upload CSV or Excel file.")


# ==================================================
# STREAMLIT UI
# ==================================================
uploaded_file = st.file_uploader(
    "Upload STTM",
    type=["csv", "xlsx", "xls"]
)

if uploaded_file:

    try:
        file_name = uploaded_file.name.lower()

        # --------------------------------------------------
        # READ CSV OR MULTI-SHEET EXCEL
        # --------------------------------------------------
        if file_name.endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file)
            df = normalize_input_columns(raw_df)

        else:
            xls = pd.ExcelFile(uploaded_file)
            all_dfs = []

            for sheet in xls.sheet_names:
                temp_df = pd.read_excel(xls, sheet_name=sheet)
                temp_df = temp_df.dropna(how="all")

                if temp_df.empty:
                    continue

                temp_df = normalize_input_columns(temp_df)

                # Real-world STTMs often use one sheet per target table.
                # If target table column is not present, use sheet name as target table.
                if "TARGET_TABLE" not in temp_df.columns:
                    temp_df["TARGET_TABLE"] = sheet

                temp_df["STTM_SHEET_NAME"] = sheet
                all_dfs.append(temp_df)

            if not all_dfs:
                st.error("No valid STTM sheets found in the uploaded workbook.")
                st.stop()

            df = pd.concat(all_dfs, ignore_index=True)

            st.success(f"Loaded {len(all_dfs)} STTM sheets")
            st.write("Sheets:", ", ".join([str(s) for s in xls.sheet_names]))

        # --------------------------------------------------
        # WORKBOOK SUMMARY
        # --------------------------------------------------
        if "STTM_SHEET_NAME" in df.columns:
            st.subheader("Workbook Summary")

            sheet_summary = (
                df.groupby("STTM_SHEET_NAME")
                .size()
                .reset_index(name="Mappings")
            )

            st.dataframe(sheet_summary, use_container_width=True)

        st.success("STTM uploaded successfully")
        st.caption(f"Rows uploaded: {len(df):,} | Columns detected: {len(df.columns):,}")

        with st.expander("Uploaded STTM Preview", expanded=False):
            st.dataframe(df.head(200), use_container_width=True)

        # --------------------------------------------------
        # BUILD CANONICAL MODEL
        # --------------------------------------------------
        with st.spinner("Building Canonical Metadata Model..."):
            normalized_df, final_mapping, mapping_source, required_missing, recommended_missing = build_canonical_model(df)
            errors_df, warnings_df, quality_score = validate_canonical_model(normalized_df)

        st.subheader("Metadata Discovery Summary")

        col1, col2, col3 = st.columns(3)
        col1.metric("Detection Method", mapping_source)
        col2.metric("Canonical Rows", f"{len(normalized_df):,}")
        col3.metric("Metadata Quality Score", f"{quality_score}%")

        mapping_df = pd.DataFrame([
            {
                "Canonical Field": field,
                "Detected Uploaded Column": final_mapping.get(field) or ""
            }
            for field in CANONICAL_FIELDS
        ])

        with st.expander("Column Mapping: STTM → Canonical Model", expanded=False):
            st.dataframe(mapping_df, use_container_width=True)

        # --------------------------------------------------
        # VALIDATION RESULTS
        # --------------------------------------------------
        if not errors_df.empty:
            st.error(
                "Critical metadata issues found. Fix these before using generated artifacts for production."
            )
            st.dataframe(errors_df, use_container_width=True)
            st.stop()

        if not warnings_df.empty:
            st.warning(
                "Metadata warnings found. Artifacts can be generated, but review warnings before production use."
            )
            with st.expander("View Metadata Warnings", expanded=False):
                st.dataframe(warnings_df, use_container_width=True)

        # --------------------------------------------------
        # CANONICAL METADATA MODEL
        # --------------------------------------------------
        st.subheader("Canonical Metadata Model")
        st.caption(
            "Architecture: STTM → Metadata Discovery Engine → LLM Assist if needed → Canonical Metadata Model → Artifact Generators"
        )
        st.dataframe(normalized_df.head(500), use_container_width=True)

        st.download_button(
            "Download Canonical Metadata Model",
            normalized_df.to_csv(index=False),
            file_name="canonical_metadata_model.csv",
            mime="text/csv",
        )

        # --------------------------------------------------
        # GENERATE ARTIFACTS
        # --------------------------------------------------
        er_diagram = generate_er_diagram(normalized_df)
        graphviz_dot = generate_graphviz_erd(normalized_df)
        ddl = generate_ddl(normalized_df)
        sql = generate_sql(normalized_df)
        dictionary_df = generate_data_dictionary(normalized_df)
        tech_spec_df = generate_tech_spec(normalized_df)
        dq_df = generate_dq_rules(normalized_df)
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "ER Diagram",
            "Snowflake DDL",
            "Snowflake SQL",
            "Data Dictionary",
            "Technical Spec",
            "DQ Rules",
            "🤖 AI Analysis",
        ])
        
        with tab1:

            st.subheader("Entity Relationship Diagram")

            st.graphviz_chart(graphviz_dot)

            st.download_button(
                "Download ER Diagram",
                graphviz_dot,
                file_name="er_diagram.dot",
                mime="text/plain",
            )
                

        with tab2:
            st.code(ddl, language="sql")
            st.download_button(
                "Download DDL",
                ddl,
                file_name="snowflake_ddl.sql",
                mime="text/plain",
            )

        with tab3:
            st.code(sql, language="sql")
            st.download_button(
                "Download SQL",
                sql,
                file_name="snowflake_sql.sql",
                mime="text/plain",
            )

        with tab4:
            st.dataframe(dictionary_df, use_container_width=True)
            st.download_button(
                "Download Data Dictionary",
                dictionary_df.to_csv(index=False),
                file_name="data_dictionary.csv",
                mime="text/csv",
            )

        with tab5:
            st.dataframe(tech_spec_df, use_container_width=True)
            st.download_button(
                "Download Technical Spec",
                tech_spec_df.to_csv(index=False),
                file_name="technical_spec.csv",
                mime="text/csv",
            )

        with tab6:
            st.dataframe(dq_df, use_container_width=True)
            st.download_button(
                "Download DQ Rules",
                dq_df.to_csv(index=False),
                file_name="dq_rules.csv",
                mime="text/csv",
            )

        with tab7:
            st.subheader("AI STTM Analysis")
            st.info("AI analysis uses the Canonical Metadata Model and only the first 100 rows.")
            
            join_count = normalized_df[
                normalized_df["lookup_table"].fillna("") != ""
            ].shape[0]

            st.metric(
                "Join Relationships Detected",
                join_count
            )

            if st.button("Generate AI Insights"):
                with st.spinner("Analyzing canonical metadata using AI..."):
                    ai_response = generate_ai_analysis(normalized_df)
                    st.markdown(ai_response)
                    st.download_button(
                        "Download AI Analysis",
                        ai_response,
                        file_name="ai_analysis.txt",
                        mime="text/plain",
                    )

    except Exception as e:
        st.error("The STTM could not be processed.")
        st.exception(e)

else:
    st.info("Upload a CSV or Excel STTM file to get started.")
