import json
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from openai import OpenAI

# ==================================================
# STREAMLIT CONFIG
# ==================================================
st.set_page_config(
    page_title="DE Copilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("⚙️ DE Copilot")


st.markdown(
    """

### Enterprise Metadata Intelligence Platform

**Architecture**

STTM → Metadata Discovery Engine → Canonical Metadata Model → AI Intelligence Layer → Artifact Factory → Human Review → Approval → Deployment → Observability & Audit

Transform complex source-to-target mappings into governed, production-ready data engineering assets in minutes.

Upload a CSV or Excel STTM and automatically generate:

✅ Canonical Metadata Model  
✅ Entity Relationship Diagram (ERD)  
✅ Snowflake DDL  
✅ Snowflake SQL  
✅ Data Dictionary  
✅ Technical Specifications  
✅ Data Quality Rules  
✅ AI-Powered Metadata Analysis  
✅ AI Intelligence Recommendations  
✅ Human Review Queue  
✅ Approval Workflow  
✅ Deployment Manifest  
✅ Observability Dashboard  
✅ Audit Trail  

---

### Why DE Copilot?

A technology-agnostic metadata platform that transforms STTM metadata into reusable engineering artifacts through a Canonical Metadata Model.

**Build once. Generate everywhere. Govern before deployment.**

"""
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
# SESSION STATE
# ==================================================
def init_session_state():
    if "audit_events" not in st.session_state:
        st.session_state.audit_events = []
    if "review_decisions" not in st.session_state:
        st.session_state.review_decisions = {}
    if "workflow_status" not in st.session_state:
        st.session_state.workflow_status = "Draft"


def add_audit_event(action: str, detail: str = "", actor: str = "DE Copilot"):
    st.session_state.audit_events.append(
        {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Actor": actor,
            "Action": action,
            "Detail": detail,
        }
    )


init_session_state()

# ==================================================
# SAMPLE STTM FILES
# ==================================================
st.subheader("📂 Sample STTM Files")

st.markdown(
    """
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
- SQL generation
"""
)

sample_files = {
    "📄 Download Basic STTM": "samples/sample_sttm_basic.csv",
    "🛒 Download Retail STTM": "samples/sample_sttm_retail.xlsx",
    "🏦 Download Banking STTM": "samples/sample_sttm_banking_multisheet.xlsx",
    "🔗 Download Join Example STTM": "samples/sample_sttm_join_example.xlsx",
}

sample_cols = st.columns(4)
for index, (label, file_path) in enumerate(sample_files.items()):
    path = Path(file_path)
    if path.exists():
        with open(path, "rb") as f:
            sample_cols[index % 4].download_button(label=label, data=f, file_name=path.name)

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

REQUIRED_CANONICAL_FIELDS = ["target_table", "target_column"]
RECOMMENDED_CANONICAL_FIELDS = ["source_table", "source_column", "target_datatype"]

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
    "source_datatype": ["SOURCE_DATA_TYPE", "SOURCE_DATATYPE", "SRC_DATA_TYPE", "SRC_DATATYPE", "SOURCE_TYPE"],
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
    "lookup_column": ["LOOKUP_COLUMN", "LOOKUP_KEY", "REFERENCE_COLUMN", "REF_COLUMN"],
    "join_type": ["JOIN_TYPE", "LOOKUP_JOIN_TYPE"],
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
# LLM COLUMN INTERPRETER
# ==================================================
def llm_assisted_column_mapping(df: pd.DataFrame, base_mapping: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
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

Return ONLY valid JSON object.
Keys must be canonical field names.
Values must be uploaded column names from uploaded_columns or null.
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
# ARTIFACT GENERATORS
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
    if dtype == "DATE":
        return "DATE"
    if dtype in ["TIMESTAMP", "DATETIME", "TIMESTAMP_NTZ"]:
        return "TIMESTAMP_NTZ"
    if dtype in ["BOOLEAN", "BOOL"]:
        return "BOOLEAN"
    if not dtype:
        return "VARCHAR"
    return dtype


def generate_er_diagram(normalized_df: pd.DataFrame) -> str:
    tables = {}
    for target_table, group in normalized_df.groupby("target_table"):
        columns = []
        for _, row in group.iterrows():
            col_name = safe_cell(row, "target_column")
            pk = safe_cell(row, "target_pk").upper()
            fk = safe_cell(row, "target_fk").upper()
            prefix = "PK " if pk in ["Y", "YES", "TRUE", "1"] else "FK " if fk in ["Y", "YES", "TRUE", "1"] else ""
            columns.append(f"{prefix}{col_name}")
        tables[target_table] = columns

    output = []
    for table, cols in tables.items():
        output.append(f"\n[{table}]")
        for col in cols:
            output.append(f"  - {col}")
    return "\n".join(output)


def generate_graphviz_erd(normalized_df: pd.DataFrame) -> str:
    lines = ["digraph ERD {", "rankdir=LR;", "node [shape=box];"]

    tables = sorted(normalized_df["target_table"].dropna().astype(str).unique())
    for table in tables:
        if table.strip():
            lines.append(f'"{table}";')

    for _, row in normalized_df.iterrows():
        fk_flag = safe_cell(row, "target_fk").upper()
        if fk_flag not in ["Y", "YES", "TRUE", "1"]:
            continue
        parent_table = safe_cell(row, "source_table")
        child_table = safe_cell(row, "target_table")
        if parent_table and child_table:
            lines.append(f'"{parent_table}" -> "{child_table}";')

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
        source_table_values = group["source_table"].dropna().astype(str).str.strip()
        source_table_values = source_table_values[source_table_values != ""]
        source_table_name = quote_identifier(source_table_values.iloc[0]) if not source_table_values.empty else "SOURCE_TABLE"

        select_lines = []
        seen_targets = set()

        for _, row in group.iterrows():
            source_col = quote_identifier(safe_cell(row, "source_column"))
            target_col = quote_identifier(safe_cell(row, "target_column"))
            logic = safe_cell(row, "transformation_logic")

            if not target_col or target_col in seen_targets:
                continue
            seen_targets.add(target_col)

            if logic and logic.upper() not in ["DIRECT", "DIRECT MAPPING", "N/A", "NA", "NONE", "NULL"]:
                select_expr = informatca_to_snowflake_expression(logic)
            elif source_col:
                select_expr = source_col
            else:
                select_expr = f"NULL /* missing source for {target_col} */"

            select_lines.append(f"    {select_expr} AS {target_col}")

        if not select_lines:
            continue

        lookup_tables = group["lookup_table"].dropna().astype(str).str.strip()
        lookup_tables = lookup_tables[lookup_tables != ""]
        join_conditions = group["lookup_join_condition"].dropna().astype(str).str.strip()
        join_conditions = join_conditions[join_conditions != ""]

        from_clause = f"FROM {source_table_name}"
        if not lookup_tables.empty and not join_conditions.empty:
            lookup_table = quote_identifier(lookup_tables.iloc[0])
            join_condition = join_conditions.iloc[0]
            from_clause += f"""
LEFT JOIN {lookup_table}
    ON {join_condition}
"""

        sql = f"""INSERT INTO {target_table}
SELECT
{",\n".join(select_lines)}
{from_clause};"""
        sql_blocks.append(sql)

    return "\n\n".join(sql_blocks) if sql_blocks else "-- No valid SQL could be generated."


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

        dq_rows.append(
            {
                "Target Table": target_table,
                "Target Column": target_col,
                "DQ Rule": "; ".join(generated_rules),
                "Severity": severity,
                "Action": action,
            }
        )
    return pd.DataFrame(dq_rows)

# ==================================================
# ENTERPRISE INTELLIGENCE, REVIEW, DEPLOYMENT, AUDIT
# ==================================================
def is_yes(value: str) -> bool:
    return str(value).strip().upper() in ["Y", "YES", "TRUE", "1"]


def generate_ai_recommendations(normalized_df: pd.DataFrame, warnings_df: pd.DataFrame) -> pd.DataFrame:
    recommendations = []

    for _, row in normalized_df.iterrows():
        target_table = safe_cell(row, "target_table")
        target_col = safe_cell(row, "target_column")
        target_datatype = safe_cell(row, "target_datatype")
        transformation_logic = safe_cell(row, "transformation_logic")
        lookup_table = safe_cell(row, "lookup_table")
        lookup_join_condition = safe_cell(row, "lookup_join_condition")

        if is_yes(safe_cell(row, "target_pk")):
            recommendations.append(
                {
                    "Category": "Data Quality",
                    "Artifact": f"{target_table}.{target_col}",
                    "Recommendation": "Validate uniqueness constraint for primary key column.",
                    "Severity": "HIGH",
                    "Status": "Pending Review",
                }
            )

        if is_yes(safe_cell(row, "pii_flag")):
            masking_rule = safe_cell(row, "data_masking_rule") or "Apply enterprise masking policy"
            recommendations.append(
                {
                    "Category": "Security & Governance",
                    "Artifact": f"{target_table}.{target_col}",
                    "Recommendation": masking_rule,
                    "Severity": "HIGH",
                    "Status": "Pending Review",
                }
            )

        if str(safe_cell(row, "target_nullable")).upper() in ["N", "NO", "FALSE", "0"]:
            recommendations.append(
                {
                    "Category": "Data Quality",
                    "Artifact": f"{target_table}.{target_col}",
                    "Recommendation": "Add NOT NULL validation rule.",
                    "Severity": "MEDIUM",
                    "Status": "Pending Review",
                }
            )

        if not target_datatype:
            recommendations.append(
                {
                    "Category": "Metadata Completeness",
                    "Artifact": f"{target_table}.{target_col}",
                    "Recommendation": "Target datatype is missing. Review before deployment.",
                    "Severity": "MEDIUM",
                    "Status": "Pending Review",
                }
            )

        if lookup_table or lookup_join_condition:
            recommendations.append(
                {
                    "Category": "Relationship & Join Review",
                    "Artifact": f"{target_table}.{target_col}",
                    "Recommendation": "Review lookup join logic and add referential integrity validation.",
                    "Severity": "MEDIUM",
                    "Status": "Pending Review",
                }
            )

        if transformation_logic and transformation_logic.upper() not in ["DIRECT", "DIRECT MAPPING", "N/A", "NA", "NONE", "NULL"]:
            recommendations.append(
                {
                    "Category": "Transformation Review",
                    "Artifact": f"{target_table}.{target_col}",
                    "Recommendation": "Complex transformation detected. Add unit test and business approval.",
                    "Severity": "MEDIUM",
                    "Status": "Pending Review",
                }
            )

    if not warnings_df.empty:
        for _, warning in warnings_df.iterrows():
            recommendations.append(
                {
                    "Category": "Metadata Warning",
                    "Artifact": warning.get("Issue", "Metadata Warning"),
                    "Recommendation": warning.get("Recommendation", "Review metadata warning."),
                    "Severity": "MEDIUM",
                    "Status": "Pending Review",
                }
            )

    if not recommendations:
        recommendations.append(
            {
                "Category": "Readiness",
                "Artifact": "Project",
                "Recommendation": "No critical AI recommendations detected. Proceed with human review.",
                "Severity": "LOW",
                "Status": "Pending Review",
            }
        )

    return pd.DataFrame(recommendations).drop_duplicates().reset_index(drop=True)


def generate_observability_metrics(normalized_df: pd.DataFrame, dq_df: pd.DataFrame, warnings_df: pd.DataFrame, ai_recommendations_df: pd.DataFrame) -> Dict[str, int]:
    total_rows = len(normalized_df)
    mapped_source_count = int((normalized_df["source_column"].astype(str).str.strip() != "").sum()) if total_rows else 0
    dq_count = len(dq_df)
    pii_count = int(normalized_df["pii_flag"].astype(str).str.upper().isin(["Y", "YES", "TRUE", "1"]).sum()) if total_rows else 0
    table_count = int(normalized_df["target_table"].nunique()) if total_rows else 0
    join_count = int((normalized_df["lookup_table"].astype(str).str.strip() != "").sum()) if total_rows else 0

    metadata_coverage = int((mapped_source_count / total_rows) * 100) if total_rows else 0
    dq_coverage = int((dq_count / total_rows) * 100) if total_rows else 0

    return {
        "Target Tables": table_count,
        "Canonical Columns": total_rows,
        "Metadata Coverage %": metadata_coverage,
        "DQ Coverage %": dq_coverage,
        "PII Columns": pii_count,
        "Join Relationships": join_count,
        "Metadata Warnings": len(warnings_df),
        "AI Recommendations": len(ai_recommendations_df),
    }


def generate_review_queue(ai_recommendations_df: pd.DataFrame) -> pd.DataFrame:
    queue = ai_recommendations_df.copy()
    if queue.empty:
        return queue
    queue.insert(0, "Review ID", [f"REV-{i + 1:03d}" for i in range(len(queue))])
    queue["Reviewer Decision"] = queue["Review ID"].map(st.session_state.review_decisions).fillna("Pending")
    return queue


def generate_deployment_manifest(project_name: str, workflow_status: str, metrics: Dict[str, int]) -> str:
    safe_project_name = project_name.replace(" ", "_").replace(".", "_")
    status = "ready_for_deployment" if workflow_status == "Approved" else "not_ready_pending_approval"

    manifest = {
        "project": safe_project_name,
        "release": "1.0",
        "environment": "DEV",
        "workflow_status": workflow_status,
        "deployment_status": status,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "artifacts": {
            "canonical_metadata_model": "generated",
            "er_diagram": "generated",
            "snowflake_ddl": "generated",
            "snowflake_sql": "generated",
            "data_dictionary": "generated",
            "technical_specification": "generated",
            "dq_rules": "generated",
            "ai_recommendations": "generated",
            "audit_log": "generated",
        },
        "observability_metrics": metrics,
        "approval_gate": {
            "required": True,
            "current_status": workflow_status,
            "rule": "Deployment is allowed only after workflow_status is Approved.",
        },
    }

    return json.dumps(manifest, indent=2)


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
10. Human Review Recommendations
11. Deployment Readiness Recommendations
12. Observability and Audit Recommendations

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
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content


# ==================================================
# LEGACY INFORMATICA POWER CENTER XML ADAPTER
# ==================================================
def informatca_to_snowflake_expression(expression: str) -> str:
    """Translate a small, safe subset of common Informatica syntax for generated SQL."""
    expression = clean_value(expression)
    if not expression:
        return ""
    translated = expression
    translated = re.sub(r"\bIIF\s*\(", "IFF(", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bNVL\s*\(", "COALESCE(", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bSYSDATE\b", "CURRENT_TIMESTAMP()", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bISNULL\s*\(", "IS_NULL_VALUE(", translated, flags=re.IGNORECASE)
    return translated


def _xml_attr(element, attribute: str, default: str = "") -> str:
    # PowerCenter XML exports vary between TRANSFORMATIONNAME and TRANSFORMATION_NAME.
    wanted = re.sub(r"_", "", attribute).upper()
    for key, value in element.attrib.items():
        if re.sub(r"_", "", key).upper() == wanted:
            return clean_value(value, default)
    return default


def _informatica_datatype_to_canonical(datatype: str) -> str:
    value = clean_value(datatype).lower()
    mapping = {
        "string": "VARCHAR",
        "nstring": "VARCHAR",
        "varchar": "VARCHAR",
        "char": "VARCHAR",
        "decimal": "NUMBER",
        "integer": "NUMBER",
        "int": "NUMBER",
        "bigint": "NUMBER",
        "smallint": "NUMBER",
        "double": "FLOAT",
        "float": "FLOAT",
        "date/time": "TIMESTAMP_NTZ",
        "datetime": "TIMESTAMP_NTZ",
        "timestamp": "TIMESTAMP_NTZ",
        "date": "DATE",
        "binary": "BINARY",
    }
    return mapping.get(value, value.upper() or "VARCHAR")


def _get_table_attributes(transformation) -> Dict[str, str]:
    return {
        _xml_attr(attr, "NAME"): _xml_attr(attr, "VALUE")
        for attr in transformation.findall("./TABLEATTRIBUTE")
    }


def parse_informatica_powercenter_xml(uploaded_file) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], pd.DataFrame]:
    """
    Extract a governed, field-level canonical mapping from a PowerCenter XML export.
    v1 supports source/target metadata, connectors, expression inventory, and lookup flags.
    Complex objects are transparently marked as needing review rather than silently converted.
    """
    raw_xml = uploaded_file.getvalue()
    root = ET.fromstring(raw_xml)

    folders = root.findall(".//FOLDER")
    if not folders:
        raise ValueError("No POWERMART FOLDER element found. Upload a PowerCenter XML export.")

    # Mapping definitions and reusable objects can be stored in different folders.
    # Read the first executable mapping and inventory reusable objects across the export.
    mappings = root.findall(".//MAPPING")
    if not mappings:
        raise ValueError("No MAPPING element found in the Informatica XML.")

    mapping = mappings[0]
    mapping_name = _xml_attr(mapping, "NAME", "INFORMATICA_MAPPING")

    source_defs = {}
    for source in root.findall(".//SOURCE"):
        source_name = _xml_attr(source, "NAME")
        source_defs[source_name] = {
            "database": _xml_attr(source, "DATABASETYPE"),
            "fields": {
                _xml_attr(field, "NAME"): {
                    "datatype": _informatica_datatype_to_canonical(_xml_attr(field, "DATATYPE")),
                    "precision": _xml_attr(field, "PRECISION"),
                    "scale": _xml_attr(field, "SCALE"),
                    "nullable": "Y" if _xml_attr(field, "NULLABLE").upper() not in ["NOTNULL", "N", "NO"] else "N",
                    "description": _xml_attr(field, "DESCRIPTION"),
                }
                for field in source.findall("./SOURCEFIELD")
            },
        }

    target_defs = {}
    for target in root.findall(".//TARGET"):
        target_name = _xml_attr(target, "NAME")
        target_defs[target_name] = {
            "database": _xml_attr(target, "DATABASETYPE"),
            "fields": {
                _xml_attr(field, "NAME"): {
                    "datatype": _informatica_datatype_to_canonical(_xml_attr(field, "DATATYPE")),
                    "precision": _xml_attr(field, "PRECISION"),
                    "scale": _xml_attr(field, "SCALE"),
                    "nullable": "Y" if _xml_attr(field, "NULLABLE").upper() not in ["NOTNULL", "N", "NO"] else "N",
                    "keytype": _xml_attr(field, "KEYTYPE"),
                    "description": _xml_attr(field, "DESCRIPTION"),
                }
                for field in target.findall("./TARGETFIELD")
            },
        }

    transformations = {}
    for transformation in root.findall(".//TRANSFORMATION"):
        transform_name = _xml_attr(transformation, "NAME")
        attributes = _get_table_attributes(transformation)
        transformations[transform_name] = {
            "type": _xml_attr(transformation, "TYPE"),
            "fields": {
                _xml_attr(field, "NAME"): {
                    "expression": _xml_attr(field, "EXPRESSION"),
                    "datatype": _informatica_datatype_to_canonical(_xml_attr(field, "DATATYPE")),
                    "precision": _xml_attr(field, "PRECISION"),
                    "scale": _xml_attr(field, "SCALE"),
                    "porttype": _xml_attr(field, "PORTTYPE"),
                }
                for field in transformation.findall("./TRANSFORMFIELD")
            },
            "attributes": attributes,
        }

    instances = {
        _xml_attr(instance, "NAME"): {
            "object_name": _xml_attr(instance, "TRANSFORMATIONNAME"),
            "object_type": _xml_attr(instance, "TRANSFORMATIONTYPE"),
        }
        for instance in mapping.findall("./INSTANCE")
    }

    connectors = []
    for connector in mapping.findall("./CONNECTOR"):
        connectors.append({
            "from_instance": _xml_attr(connector, "FROMINSTANCE"),
            "from_field": _xml_attr(connector, "FROMFIELD"),
            "to_instance": _xml_attr(connector, "TOINSTANCE"),
            "to_field": _xml_attr(connector, "TOFIELD"),
        })

    inbound = {}
    for connector in connectors:
        inbound.setdefault((connector["to_instance"], connector["to_field"]), []).append(connector)

    def resolve_upstream(instance_name: str, field_name: str, depth: int = 0) -> Dict[str, str]:
        """Trace a field backward through connectors. v1 keeps a short lineage chain."""
        if depth > 8:
            return {"source_table": "", "source_column": "", "chain": "Lineage depth exceeded"}

        instance = instances.get(instance_name, {})
        object_name = instance.get("object_name", instance_name)
        object_type = instance.get("object_type", "")

        if object_type == "Source Definition" or object_name in source_defs:
            return {"source_table": object_name, "source_column": field_name, "chain": f"{object_name}.{field_name}"}

        parents = inbound.get((instance_name, field_name), [])
        if not parents:
            # Expression outputs often reference an INPUT field with a different name
            # (for example CD_NACE output derived from CD_NACE_in). Follow that safely.
            transform = transformations.get(object_name, {})
            field_metadata = transform.get("fields", {}).get(field_name, {})
            expression = clean_value(field_metadata.get("expression", ""))
            # First try a direct identifier; then inspect simple function expressions
            # such as LTRIM(RTRIM(CD_NACE_in)) for an upstream input port.
            candidates = []
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression):
                candidates.extend([expression, f"{expression}_in", expression.replace("_out", "_in")])
            else:
                tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expression)
                candidates.extend(reversed(tokens))
            for candidate_field in candidates:
                parents = inbound.get((instance_name, candidate_field), [])
                if parents:
                    break
            if not parents:
                return {"source_table": "", "source_column": "", "chain": f"{instance_name}.{field_name}"}

        parent = parents[0]
        upstream = resolve_upstream(parent["from_instance"], parent["from_field"], depth + 1)
        chain = f"{upstream.get('chain', '')} → {instance_name}.{field_name}"
        upstream["chain"] = chain
        return upstream

    rows = []
    findings = []
    target_instances = [
        (instance_name, data)
        for instance_name, data in instances.items()
        if data.get("object_type") == "Target Definition" or data.get("object_name") in target_defs
    ]

    for target_instance, target_instance_data in target_instances:
        target_table = target_instance_data.get("object_name", target_instance)
        target_definition = target_defs.get(target_table, {"fields": {}})

        for target_field, target_metadata in target_definition.get("fields", {}).items():
            incoming = inbound.get((target_instance, target_field), [])
            if not incoming:
                rows.append({
                    "source_system": "Informatica PowerCenter",
                    "source_table": "",
                    "source_column": "",
                    "target_system": "Snowflake",
                    "target_table": target_table,
                    "target_column": target_field,
                    "target_datatype": target_metadata.get("datatype", "VARCHAR"),
                    "target_precision": target_metadata.get("precision", ""),
                    "target_scale": target_metadata.get("scale", ""),
                    "target_nullable": target_metadata.get("nullable", "Y"),
                    "target_pk": "Y" if "PRIMARY" in target_metadata.get("keytype", "").upper() else "",
                    "business_definition": target_metadata.get("description", ""),
                    "transformation_type": "Unmapped Target Field",
                    "transformation_logic": "",
                    "dq_rule": "",
                    "dq_severity": "HIGH",
                    "dq_action": "Block Release",
                    "approval_status": "Needs Review",
                    "notes": "No incoming connector found for target field.",
                })
                findings.append({
                    "Severity": "WARNING",
                    "Issue": f"Unmapped target field: {target_table}.{target_field}",
                    "Count": 1,
                    "Recommendation": "Confirm whether the column is populated by a default, sequence, or manual migration rule.",
                })
                continue

            connector = incoming[0]
            from_instance = connector["from_instance"]
            from_field = connector["from_field"]
            from_instance_data = instances.get(from_instance, {})
            transform_name = from_instance_data.get("object_name", from_instance)
            transform_type = from_instance_data.get("object_type", "")
            transform = transformations.get(transform_name, {})
            transform_field = transform.get("fields", {}).get(from_field, {})
            upstream = resolve_upstream(from_instance, from_field)
            attrs = transform.get("attributes", {})

            logic = informatca_to_snowflake_expression(transform_field.get("expression", ""))
            lookup_table = attrs.get("Lookup table name", "")
            lookup_condition = attrs.get("Lookup condition", "")

            notes = f"Lineage: {upstream.get('chain', '')}"
            approval_status = "Draft"
            dq_severity = "MEDIUM"
            dq_action = "Flag Record"

            if transform_type in ["Lookup Procedure", "Lookup"]:
                approval_status = "Needs Review"
                notes += " | Lookup conversion requires Snowflake join/reference-table review."
                findings.append({
                    "Severity": "WARNING",
                    "Issue": f"Lookup migration review required: {transform_name}",
                    "Count": 1,
                    "Recommendation": "Confirm reference-table join, duplicate-match behavior, and lookup cache semantics before release.",
                })

            if transform_type in ["Update Strategy", "Sequence Generator", "Router", "Aggregator", "Joiner", "Stored Procedure"]:
                approval_status = "Needs Review"
                dq_severity = "HIGH"
                dq_action = "Block Release"
                notes += f" | {transform_type} requires manual migration decision."
                findings.append({
                    "Severity": "WARNING",
                    "Issue": f"Manual migration decision required: {transform_type}",
                    "Count": 1,
                    "Recommendation": "Review target load pattern, merge strategy, and semantic equivalence before release.",
                })

            rows.append({
                "source_system": "Informatica PowerCenter",
                "source_database": "",
                "source_schema": "",
                "source_table": upstream.get("source_table", ""),
                "source_column": upstream.get("source_column", ""),
                "source_datatype": "",
                "target_system": "Snowflake",
                "target_database": "",
                "target_schema": "",
                "target_table": target_table,
                "target_column": target_field,
                "target_datatype": target_metadata.get("datatype", "VARCHAR"),
                "target_length": "",
                "target_precision": target_metadata.get("precision", ""),
                "target_scale": target_metadata.get("scale", ""),
                "target_nullable": target_metadata.get("nullable", "Y"),
                "target_pk": "Y" if "PRIMARY" in target_metadata.get("keytype", "").upper() else "",
                "business_definition": target_metadata.get("description", ""),
                "transformation_type": transform_type or "Direct Mapping",
                "transformation_logic": logic,
                "lookup_table": lookup_table,
                "lookup_join_condition": lookup_condition,
                "dq_rule": "",
                "dq_severity": dq_severity,
                "dq_action": dq_action,
                "owner": "",
                "approval_status": approval_status,
                "release": "",
                "notes": notes,
            })

    if not rows:
        raise ValueError("No target field mappings could be extracted from the PowerCenter XML.")

    mapping_inventory = pd.DataFrame([{
        "Mapping": mapping_name,
        "Source Definitions": len(source_defs),
        "Target Definitions": len(target_defs),
        "Instances": len(instances),
        "Connectors": len(connectors),
        "Transformations": len(transformations),
        "Extracted Target Mappings": len(rows),
    }])

    transformation_inventory = pd.DataFrame([
        {
            "Transformation": name,
            "Type": data.get("type", ""),
            "Fields": len(data.get("fields", {})),
            "Lookup Table": data.get("attributes", {}).get("Lookup table name", ""),
            "Migration Treatment": (
                "Needs Review" if data.get("type", "") in [
                    "Lookup Procedure", "Lookup", "Update Strategy", "Sequence Generator",
                    "Router", "Aggregator", "Joiner", "Stored Procedure"
                ] else "Supported / Inventory"
            ),
        }
        for name, data in transformations.items()
    ])

    return (
        pd.DataFrame(rows),
        {
            "mapping_inventory": mapping_inventory,
            "transformation_inventory": transformation_inventory,
            "mapping_name": mapping_name,
        },
        pd.DataFrame(findings).drop_duplicates().reset_index(drop=True),
    )

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
st.subheader("Start a Governed Delivery Workflow")
input_mode = st.radio(
    "Choose your starting point",
    ["Business Requirement / STTM", "Legacy ETL Mapping"],
    horizontal=True,
)

legacy_context = None
uploaded_file = None
df = pd.DataFrame()
sheet_names = []

if input_mode == "Business Requirement / STTM":
    st.caption("Upload a CSV or Excel STTM to generate governed engineering artifacts.")
    uploaded_file = st.file_uploader(
        "Upload Business Requirement / STTM",
        type=["csv", "xlsx", "xls"],
        key="sttm_upload",
    )
else:
    st.caption("Upload an Informatica PowerCenter XML export. DE Copilot will extract metadata, identify migration risks, and generate Snowflake-ready artifacts.")
    legacy_platform = st.selectbox(
        "Legacy platform",
        ["Informatica PowerCenter XML", "DataStage Export — Coming Soon", "SSIS Package — Coming Soon"],
        key="legacy_platform",
    )
    if legacy_platform != "Informatica PowerCenter XML":
        st.info("This adapter is on the roadmap. Please select Informatica PowerCenter XML for the working v2 demo.")
    uploaded_file = st.file_uploader(
        "Upload Informatica PowerCenter XML",
        type=["xml"],
        key="informatica_upload",
    )

if uploaded_file:
    try:
        file_name = uploaded_file.name.lower()

        # --------------------------------------------------
        # INGEST BUSINESS REQUIREMENTS OR LEGACY XML
        # --------------------------------------------------
        if input_mode == "Legacy ETL Mapping":
            if not file_name.endswith(".xml"):
                st.error("Upload a valid Informatica XML export.")
                st.stop()

            with st.spinner("Parsing Informatica PowerCenter mapping metadata..."):
                df, legacy_context, legacy_findings_df = parse_informatica_powercenter_xml(uploaded_file)
                df = normalize_input_columns(df)

            add_audit_event(
                "Legacy Informatica XML Uploaded",
                f"File uploaded: {uploaded_file.name} | Mapping: {legacy_context['mapping_name']}"
            )
            st.success(f"Informatica mapping extracted: {legacy_context['mapping_name']}")
        else:
            add_audit_event("STTM Uploaded", f"File uploaded: {uploaded_file.name}")

            if file_name.endswith(".csv"):
                raw_df = pd.read_csv(uploaded_file)
                df = normalize_input_columns(raw_df)
                sheet_names = ["CSV"]
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
                    if "TARGET_TABLE" not in temp_df.columns:
                        temp_df["TARGET_TABLE"] = sheet

                    temp_df["STTM_SHEET_NAME"] = sheet
                    all_dfs.append(temp_df)
                    sheet_names.append(sheet)

                if not all_dfs:
                    st.error("No valid STTM sheets found in the uploaded workbook.")
                    st.stop()

                df = pd.concat(all_dfs, ignore_index=True)
                st.success(f"Loaded {len(all_dfs)} STTM sheets")
                st.write("Sheets:", ", ".join(sheet_names))

        # --------------------------------------------------
        # WORKBOOK SUMMARY
        # --------------------------------------------------
        if "STTM_SHEET_NAME" in df.columns:
            st.subheader("Workbook Summary")
            sheet_summary = df.groupby("STTM_SHEET_NAME").size().reset_index(name="Mappings")
            st.dataframe(sheet_summary, use_container_width=True)

        if legacy_context is not None:
            st.subheader("Legacy Mapping Analysis")
            st.caption("Informatica XML → Canonical Metadata Model → Governed Snowflake Delivery Packet")
            st.dataframe(legacy_context["mapping_inventory"], use_container_width=True)

            with st.expander("Detected Transformations and Migration Treatment", expanded=False):
                st.dataframe(legacy_context["transformation_inventory"], use_container_width=True)

            if not legacy_findings_df.empty:
                st.warning("Legacy migration review items detected. These are carried into the Release Gate.")
                with st.expander("View Legacy Migration Findings", expanded=False):
                    st.dataframe(legacy_findings_df, use_container_width=True)

        st.success("Input uploaded successfully")
        st.caption(f"Rows uploaded: {len(df):,} | Columns detected: {len(df.columns):,}")

        with st.expander("Uploaded STTM Preview", expanded=False):
            st.dataframe(df.head(200), use_container_width=True)

        # --------------------------------------------------
        # BUILD CANONICAL MODEL
        # --------------------------------------------------
        with st.spinner("Building Canonical Metadata Model..."):
            normalized_df, final_mapping, mapping_source, required_missing, recommended_missing = build_canonical_model(df)
            errors_df, warnings_df, quality_score = validate_canonical_model(normalized_df)

            if legacy_context is not None and not legacy_findings_df.empty:
                warnings_df = pd.concat([warnings_df, legacy_findings_df], ignore_index=True).drop_duplicates()
                quality_score = max(0, quality_score - min(25, len(legacy_findings_df) * 5))

        add_audit_event("Canonical Metadata Model Generated", f"Rows: {len(normalized_df)} | Quality Score: {quality_score}%")

        st.subheader("Metadata Discovery Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Detection Method", "LLM Assisted" if "LLM" in mapping_source else "Rule Based")
        st.caption(f"Method: {mapping_source}")
        col2.metric("Canonical Rows", f"{len(normalized_df):,}")
        col3.metric("Metadata Quality Score", f"{quality_score}%")

        mapping_df = pd.DataFrame(
            [{"Canonical Field": field, "Detected Uploaded Column": final_mapping.get(field) or ""} for field in CANONICAL_FIELDS]
        )

        with st.expander("Column Mapping: STTM → Canonical Model", expanded=False):
            st.dataframe(mapping_df, use_container_width=True)

        # --------------------------------------------------
        # VALIDATION RESULTS
        # --------------------------------------------------
        if not errors_df.empty:
            st.error("Critical metadata issues found. Fix these before using generated artifacts for production.")
            st.dataframe(errors_df, use_container_width=True)
            st.stop()

        if not warnings_df.empty:
            st.warning("Metadata warnings found. Artifacts can be generated, but review warnings before production use.")
            with st.expander("View Metadata Warnings", expanded=False):
                st.dataframe(warnings_df, use_container_width=True)

        # --------------------------------------------------
        # CANONICAL METADATA MODEL
        # --------------------------------------------------
        st.subheader("Canonical Metadata Model")
        st.caption("Architecture: Business Requirement / Legacy ETL → Metadata Discovery Engine → Canonical Metadata Model → Artifact Factory → Release Gate")
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
        ai_recommendation_df = generate_ai_recommendations(normalized_df, warnings_df)
        observability_metrics = generate_observability_metrics(normalized_df, dq_df, warnings_df, ai_recommendation_df)

        add_audit_event("Artifacts Generated", "ERD, DDL, SQL, Data Dictionary, Technical Spec, DQ Rules, AI Recommendations")


        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs(
            [
                "ER Diagram",
                "Snowflake DDL",
                "Snowflake SQL",
                "Data Dictionary",
                "Technical Spec",
                "DQ Rules",
                "🤖 AI Analysis",
                "🧠 AI Intelligence",
                "👤 Human Review",
                "✅ Approval & Deployment",
                "📊 Observability",
                "🧾 Audit Trail",
            ]
        )

        with tab1:
            st.subheader("Entity Relationship Diagram")
            st.graphviz_chart(graphviz_dot)
            st.download_button("Download ER Diagram", graphviz_dot, file_name="er_diagram.dot", mime="text/plain")

        with tab2:
            st.code(ddl, language="sql")
            st.download_button("Download DDL", ddl, file_name="snowflake_ddl.sql", mime="text/plain")

        with tab3:
            st.code(sql, language="sql")
            st.download_button("Download SQL", sql, file_name="snowflake_sql.sql", mime="text/plain")

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
            st.download_button("Download DQ Rules", dq_df.to_csv(index=False), file_name="dq_rules.csv", mime="text/csv")

        with tab7:
            st.subheader("AI Metadata Analysis")
            st.info("AI analysis uses the Canonical Metadata Model and only the first 100 rows. Legacy migration findings remain subject to human review.")
            join_count = normalized_df[normalized_df["lookup_table"].fillna("") != ""].shape[0]
            st.metric("Join Relationships Detected", join_count)

            if st.button("Generate AI Insights"):
                with st.spinner("Analyzing canonical metadata using AI..."):
                    ai_response = generate_ai_analysis(normalized_df)
                    add_audit_event("AI Analysis Completed", "AI metadata analysis generated")
                    st.markdown(ai_response)
                    st.download_button("Download AI Analysis", ai_response, file_name="ai_analysis.txt", mime="text/plain")

        with tab8:
            st.subheader("AI Intelligence Layer")
            st.caption("Rule-based intelligence over the Canonical Metadata Model. This layer prepares items for human review.")

            rec_col1, rec_col2, rec_col3 = st.columns(3)
            high_count = int((ai_recommendation_df["Severity"] == "HIGH").sum()) if not ai_recommendation_df.empty else 0
            medium_count = int((ai_recommendation_df["Severity"] == "MEDIUM").sum()) if not ai_recommendation_df.empty else 0
            low_count = int((ai_recommendation_df["Severity"] == "LOW").sum()) if not ai_recommendation_df.empty else 0
            rec_col1.metric("High Priority", high_count)
            rec_col2.metric("Medium Priority", medium_count)
            rec_col3.metric("Low Priority", low_count)

            st.dataframe(ai_recommendation_df, use_container_width=True)
            st.download_button(
                "Download AI Recommendations",
                ai_recommendation_df.to_csv(index=False),
                file_name="ai_recommendations.csv",
                mime="text/csv",
            )

        with tab9:
            st.subheader("Human Review Queue")
            st.caption("Human-in-the-loop review before approval and deployment.")

            review_queue_df = generate_review_queue(ai_recommendation_df)
            st.dataframe(review_queue_df, use_container_width=True)

            if not review_queue_df.empty:
                selected_review_id = st.selectbox("Select Review Item", review_queue_df["Review ID"].tolist())
                reviewer_name = st.text_input("Reviewer Name", value="Amit Singh")
                reviewer_decision = st.selectbox("Reviewer Decision", ["Pending", "Approved", "Rejected", "Request Changes"])
                reviewer_comment = st.text_area("Reviewer Comment", value="Reviewed as part of metadata governance workflow.")

                if st.button("Save Review Decision"):
                    st.session_state.review_decisions[selected_review_id] = reviewer_decision
                    add_audit_event(
                        "Human Review Decision Saved",
                        f"{selected_review_id}: {reviewer_decision} | {reviewer_comment}",
                        actor=reviewer_name,
                    )
                    st.success(f"Saved decision for {selected_review_id}: {reviewer_decision}")

        with tab10:
            st.subheader("Approval & Deployment Readiness")
            st.caption("This is a simulated deployment gate. No production deployment is triggered from the demo.")

            st.session_state.workflow_status = st.selectbox(
                "Workflow Status",
                ["Draft", "Under Review", "Approved", "Rejected"],
                index=["Draft", "Under Review", "Approved", "Rejected"].index(st.session_state.workflow_status),
            )

            if st.session_state.workflow_status == "Approved":
                st.success("Deployment Status: READY FOR DEV DEPLOYMENT")
            elif st.session_state.workflow_status == "Rejected":
                st.error("Deployment Status: BLOCKED")
            else:
                st.warning("Deployment Status: NOT READY - approval required")

            if st.button("Record Workflow Status"):
                add_audit_event("Workflow Status Updated", f"Status changed to {st.session_state.workflow_status}")
                st.success("Workflow status recorded in audit trail.")
            st.markdown("---")
            st.subheader("Approved Release Package")

            if st.session_state.workflow_status != "Approved":

                st.warning(
                    "Project package is locked. "
                    "Complete Human Review and Approval before download."
                )

            else:

                deployment_manifest = generate_deployment_manifest(
                    uploaded_file.name,
                    st.session_state.workflow_status,
                    observability_metrics
                )

                audit_df_for_zip = pd.DataFrame(
                    st.session_state.audit_events
                )

                zip_buffer = BytesIO()

                with zipfile.ZipFile(
                    zip_buffer,
                    "w",
                    zipfile.ZIP_DEFLATED
                ) as zip_file:

                    zip_file.writestr(
                        "canonical_metadata_model.csv",
                        normalized_df.to_csv(index=False)
                    )

                    zip_file.writestr(
                        "snowflake_ddl.sql",
                        ddl
                    )

                    zip_file.writestr(
                        "snowflake_sql.sql",
                        sql
                    )

                    zip_file.writestr(
                        "er_diagram.dot",
                        graphviz_dot
                    )

                    zip_file.writestr(
                        "data_dictionary.csv",
                        dictionary_df.to_csv(index=False)
                    )

                    zip_file.writestr(
                        "technical_specification.csv",
                        tech_spec_df.to_csv(index=False)
                    )

                    zip_file.writestr(
                        "dq_rules.csv",
                        dq_df.to_csv(index=False)
                    )

                    zip_file.writestr(
                        "ai_recommendations.csv",
                        ai_recommendation_df.to_csv(index=False)
                    )

                    zip_file.writestr(
                        "deployment_manifest.json",
                        deployment_manifest
                    )

                    zip_file.writestr(
                        "audit_log.csv",
                        audit_df_for_zip.to_csv(index=False)
                    )

                zip_buffer.seek(0)

                st.success(
                    "Approval completed. Release package unlocked."
                )

                st.download_button(
                    "🚀 Download Approved Release Package",
                    data=zip_buffer,
                    file_name="de_copilot_approved_release.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

            updated_manifest = generate_deployment_manifest(uploaded_file.name, st.session_state.workflow_status, observability_metrics)
            st.code(updated_manifest, language="json")
            st.download_button(
                "Download Deployment Manifest",
                updated_manifest,
                file_name="deployment_manifest.json",
                mime="application/json",
            )

        with tab11:
            st.subheader("Observability Dashboard")
            st.caption("Metadata, generation, review, and governance coverage metrics.")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Target Tables", observability_metrics["Target Tables"])
            m2.metric("Canonical Columns", observability_metrics["Canonical Columns"])
            m3.metric("Metadata Coverage", f"{observability_metrics['Metadata Coverage %']}%")
            m4.metric("DQ Coverage", f"{observability_metrics['DQ Coverage %']}%")

            m5, m6, m7, m8 = st.columns(4)
            m5.metric("PII Columns", observability_metrics["PII Columns"])
            m6.metric("Join Relationships", observability_metrics["Join Relationships"])
            m7.metric("Metadata Warnings", observability_metrics["Metadata Warnings"])
            m8.metric("AI Recommendations", observability_metrics["AI Recommendations"])

            st.markdown("### Observability Summary")
            st.dataframe(pd.DataFrame([observability_metrics]), use_container_width=True)

        with tab12:
            st.subheader("Audit Trail")
            st.caption("Traceability of metadata processing, artifact generation, review, approval, and deployment readiness events.")

            audit_df = pd.DataFrame(st.session_state.audit_events)
            if audit_df.empty:
                st.info("No audit events recorded yet.")
            else:
                st.dataframe(audit_df, use_container_width=True)
                st.download_button("Download Audit Log", audit_df.to_csv(index=False), file_name="audit_log.csv", mime="text/csv")

    except Exception as e:
        st.error("The STTM could not be processed.")
        st.exception(e)

else:
    st.info("Start from a Business Requirement / STTM or an Informatica PowerCenter XML export.")
