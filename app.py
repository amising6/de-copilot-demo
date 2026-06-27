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
### Governed Metadata-to-Delivery Platform

**Start from business intent or legacy implementation metadata.**

**Architecture**

Business Requirement / STTM **or** Legacy ETL Mapping → Metadata Discovery → Canonical Metadata Model → Artifact Factory → Validation & Risk Assessment → Human Review → Approval → Release Package → Audit

Transform source-to-target mappings, Informatica PowerCenter XML, and supporting metadata into governed, Snowflake-ready engineering artifacts.

**Core outputs**

✅ Canonical Metadata & Field-Level Lineage  
✅ Snowflake DDL and Transformation SQL  
✅ Default / Constant / Derived Value Handling  
✅ Data Dictionary, Technical Specification and DQ Rules  
✅ Migration Risk Assessment and Unsupported-Pattern Flags  
✅ Human Review Queue, Decision History and Approval Gate  
✅ Release Package, Deployment Manifest and Audit Trail  

**Build once. Generate everywhere. Govern before release.**
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
    "target_default",
    "lineage_path",
    "migration_status",
    "input_mode",
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
    "target_default": ["TARGET_DEFAULT", "DEFAULT_VALUE", "DEFAULTVALUE"],
    "lineage_path": ["LINEAGE_PATH", "LINEAGE"],
    "migration_status": ["MIGRATION_STATUS", "CONVERSION_STATUS"],
    "input_mode": ["INPUT_MODE", "SOURCE_MODE"],
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
            target_default = safe_cell(row, "target_default")
            default_clause = f" DEFAULT {informatca_to_snowflake_expression(target_default)}" if target_default else ""
            column_lines.append(f"    {col_name} {data_type}{default_clause}{not_null}")

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

    if "input_mode" in normalized_df.columns and (
        normalized_df["input_mode"].astype(str).str.contains("Legacy ETL Mapping", case=False, na=False).any()
    ):
        return generate_legacy_snowflake_sql(normalized_df)

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
def _xml_attr(element, attribute: str, default: str = "") -> str:
    """Read PowerCenter attributes with or without underscores."""
    wanted = re.sub(r"_", "", attribute).upper()
    for key, value in element.attrib.items():
        if re.sub(r"_", "", key).upper() == wanted:
            return clean_value(value, default)
    return default



def _xml_raw_attr(element, attribute: str, default: str = "") -> str:
    """Read XML attribute without treating literal SQL NULL as an empty value."""
    wanted = re.sub(r"_", "", attribute).upper()
    for key, value in element.attrib.items():
        if re.sub(r"_", "", key).upper() == wanted:
            return str(value).strip()
    return default

def _informatica_datatype_to_canonical(datatype: str) -> str:
    value = clean_value(datatype).lower()
    mapping = {
        "string": "VARCHAR", "nstring": "VARCHAR", "varchar": "VARCHAR",
        "varchar2": "VARCHAR", "char": "VARCHAR",
        "decimal": "NUMBER", "number(p,s)": "NUMBER", "integer": "NUMBER",
        "int": "NUMBER", "bigint": "NUMBER", "smallint": "NUMBER",
        "double": "FLOAT", "float": "FLOAT",
        "date/time": "TIMESTAMP_NTZ", "datetime": "TIMESTAMP_NTZ",
        "timestamp": "TIMESTAMP_NTZ", "date": "DATE", "binary": "BINARY",
    }
    return mapping.get(value, value.upper() or "VARCHAR")


def _get_table_attributes(transformation) -> Dict[str, str]:
    return {
        _xml_attr(attr, "NAME"): _xml_attr(attr, "VALUE")
        for attr in transformation.findall("./TABLEATTRIBUTE")
    }


def _strip_informatica_error_default(value: str) -> str:
    value = clean_value(value)
    if value.upper().startswith("ERROR("):
        return ""
    return value


def _replace_iif(expression: str) -> str:
    """Convert nested Informatica IIF(cond, true, false) into Snowflake IFF()."""
    expression = clean_value(expression)
    if not expression:
        return ""

    result = expression
    # IFF is valid Snowflake; loop handles nested IIF tokens safely without a full parser.
    result = re.sub(r"\bIIF\s*\(", "IFF(", result, flags=re.IGNORECASE)
    return result


def informatca_to_snowflake_expression(expression: str, macro_defaults: Optional[Dict[str, str]] = None) -> str:
    """
    Translate a deliberately small, transparent subset of Informatica syntax.
    Unknown functions are preserved and flagged through the review workflow.
    """
    expression = str(expression or "").strip()
    if not expression:
        return ""
    if expression.lower() == "null":
        return "NULL"

    translated = _replace_iif(expression)
    translated = re.sub(r":UDF\.DEFAULTSTRINGNULL\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)",
                        r"COALESCE(NULLIF(TRIM(\1), ''), 'XNA')", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bNVL\s*\(", "COALESCE(", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bLTRIM\s*\(\s*RTRIM\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\)",
                        r"TRIM(\1)", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bRTRIM\s*\(\s*LTRIM\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\)",
                        r"TRIM(\1)", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bSYSDATE\b", "CURRENT_TIMESTAMP()", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bTO_DATE\s*\(\s*'\$\$([A-Za-z0-9_]+)'\s*,\s*'([^']+)'\s*\)",
                        r"TO_TIMESTAMP_NTZ(:\1, '\2')", translated, flags=re.IGNORECASE)

    # ISNULL(field) is not a Snowflake function. Translate simple occurrences.
    translated = re.sub(r"\bISNULL\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)",
                        r"(\1 IS NULL)", translated, flags=re.IGNORECASE)
    translated = translated.replace("<>", "!=")
    return translated


def _is_constant_sql(expression: str) -> bool:
    return bool(re.fullmatch(r"\s*(NULL|-?\d+(\.\d+)?|'[^']*')\s*", clean_value(expression), flags=re.IGNORECASE))


def _review_item(category: str, artifact: str, recommendation: str, severity: str = "MEDIUM",
                 status: str = "Pending Review") -> Dict[str, str]:
    return {
        "Category": category,
        "Artifact": artifact,
        "Recommendation": recommendation,
        "Severity": severity,
        "Status": status,
    }



def _is_passthrough_expression(expression: str, field_name: str) -> bool:
    return bool(re.fullmatch(r"\s*" + re.escape(field_name) + r"\s*", str(expression or ""), flags=re.IGNORECASE))

def parse_informatica_powercenter_xml(uploaded_file) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], pd.DataFrame]:
    """
    Extract a field-level governed mapping. The adapter preserves what is explicit in XML
    and flags ambiguity; it never invents source lineage or target defaults.
    """
    raw_xml = uploaded_file.getvalue()
    root = ET.fromstring(raw_xml)

    mappings = root.findall(".//MAPPING")
    if not mappings:
        raise ValueError("No MAPPING element found. Upload a valid Informatica PowerCenter XML export.")

    mapping = mappings[0]
    mapping_name = _xml_attr(mapping, "NAME", "INFORMATICA_MAPPING")

    source_defs: Dict[str, Dict] = {}
    for source in root.findall(".//SOURCE"):
        source_name = _xml_attr(source, "NAME")
        source_defs[source_name] = {
            "database": _xml_attr(source, "DBDNAME") or _xml_attr(source, "DATABASETYPE"),
            "fields": {
                _xml_attr(field, "NAME"): {
                    "datatype": _informatica_datatype_to_canonical(_xml_attr(field, "DATATYPE")),
                    "precision": _xml_attr(field, "PRECISION"),
                    "scale": _xml_attr(field, "SCALE"),
                    "length": _xml_attr(field, "PHYSICALLENGTH") or _xml_attr(field, "LENGTH"),
                    "nullable": "N" if _xml_attr(field, "NULLABLE").upper() in ["NOTNULL", "N", "NO"] else "Y",
                    "description": _xml_attr(field, "DESCRIPTION"),
                }
                for field in source.findall("./SOURCEFIELD")
            },
        }

    target_defs: Dict[str, Dict] = {}
    for target in root.findall(".//TARGET"):
        target_name = _xml_attr(target, "NAME")
        target_defs[target_name] = {
            "database": _xml_attr(target, "DATABASETYPE"),
            "fields": {
                _xml_attr(field, "NAME"): {
                    "datatype": _informatica_datatype_to_canonical(_xml_attr(field, "DATATYPE")),
                    "precision": _xml_attr(field, "PRECISION"),
                    "scale": _xml_attr(field, "SCALE"),
                    "length": _xml_attr(field, "PHYSICALLENGTH") or _xml_attr(field, "LENGTH"),
                    "nullable": "N" if _xml_attr(field, "NULLABLE").upper() in ["NOTNULL", "N", "NO"] else "Y",
                    "keytype": _xml_attr(field, "KEYTYPE"),
                    "description": _xml_attr(field, "DESCRIPTION"),
                }
                for field in target.findall("./TARGETFIELD")
            },
        }

    transformations: Dict[str, Dict] = {}
    for transformation in root.findall(".//TRANSFORMATION"):
        transform_name = _xml_attr(transformation, "NAME")
        transformations[transform_name] = {
            "type": _xml_attr(transformation, "TYPE"),
            "fields": {
                _xml_attr(field, "NAME"): {
                    "expression": _xml_raw_attr(field, "EXPRESSION"),
                    "default": _strip_informatica_error_default(_xml_raw_attr(field, "DEFAULTVALUE")),
                    "datatype": _informatica_datatype_to_canonical(_xml_attr(field, "DATATYPE")),
                    "precision": _xml_attr(field, "PRECISION"),
                    "scale": _xml_attr(field, "SCALE"),
                    "porttype": _xml_attr(field, "PORTTYPE"),
                }
                for field in transformation.findall("./TRANSFORMFIELD")
            },
            "attributes": _get_table_attributes(transformation),
        }

    instances = {
        _xml_attr(instance, "NAME"): {
            "object_name": _xml_attr(instance, "TRANSFORMATIONNAME"),
            "object_type": _xml_attr(instance, "TRANSFORMATIONTYPE"),
            "type": _xml_attr(instance, "TYPE"),
        }
        for instance in mapping.findall("./INSTANCE")
    }

    connectors = [{
        "from_instance": _xml_attr(connector, "FROMINSTANCE"),
        "from_field": _xml_attr(connector, "FROMFIELD"),
        "to_instance": _xml_attr(connector, "TOINSTANCE"),
        "to_field": _xml_attr(connector, "TOFIELD"),
    } for connector in mapping.findall("./CONNECTOR")]

    inbound: Dict[Tuple[str, str], List[Dict]] = {}
    for connector in connectors:
        inbound.setdefault((connector["to_instance"], connector["to_field"]), []).append(connector)

    def resolve_upstream(instance_name: str, field_name: str, depth: int = 0) -> Dict[str, str]:
        if depth > 12:
            return {"source_table": "", "source_column": "", "chain": "Lineage depth exceeded", "expression": ""}

        instance = instances.get(instance_name, {})
        object_name = instance.get("object_name") or instance_name
        object_type = instance.get("object_type", "")

        if object_type == "Source Definition" or object_name in source_defs:
            return {
                "source_table": object_name,
                "source_column": field_name,
                "chain": f"{object_name}.{field_name}",
                "expression": f"src.{field_name}",
                "lookup_table": "",
                "lookup_join_condition": "",
            }

        transform = transformations.get(object_name, {})
        field_meta = transform.get("fields", {}).get(field_name, {})
        field_expr = str(field_meta.get("expression", "") or "").strip()
        parents = inbound.get((instance_name, field_name), [])

        # A lookup output has no inbound connection for the returned field. Trace one
        # lookup input to retain source lineage and produce an explicit reviewable join.
        if transform.get("type") in ["Lookup Procedure", "Lookup"] and not parents:
            attrs = transform.get("attributes", {})
            lookup_table = attrs.get("Lookup table name", "")
            lookup_alias = re.sub(r"[^A-Za-z0-9_]", "_", object_name.lower())[:24] or "lkp"
            input_parent = None
            input_name = ""
            for (to_instance, to_field), candidate_parents in inbound.items():
                if to_instance == instance_name and candidate_parents:
                    input_parent = candidate_parents[0]
                    input_name = to_field
                    break
            upstream_input = resolve_upstream(input_parent["from_instance"], input_parent["from_field"], depth + 1) if input_parent else {}
            lookup_condition = attrs.get("Lookup condition", "")
            lookup_filter = attrs.get("Lookup Source Filter", "")
            if lookup_condition and input_name and upstream_input.get("source_column"):
                lookup_condition = re.sub(
                    r"\b" + re.escape(input_name) + r"\b",
                    f"src.{upstream_input['source_column']}",
                    lookup_condition,
                    flags=re.IGNORECASE,
                )
                # Left hand side lookup fields get a stable alias.
                tokens = lookup_condition.split("=")
                if len(tokens) == 2:
                    left = tokens[0].strip()
                    if "." not in left:
                        lookup_condition = f"{lookup_alias}.{left} = {tokens[1].strip()}"
            if lookup_filter:
                lookup_filter = lookup_filter.replace(f"{lookup_table}.", f"{lookup_alias}.")
                lookup_condition = f"{lookup_condition} AND {lookup_filter}" if lookup_condition else lookup_filter
            return {
                "source_table": upstream_input.get("source_table", ""),
                "source_column": upstream_input.get("source_column", ""),
                "chain": f"{upstream_input.get('chain', '')} → {instance_name}.{field_name}".strip(" →"),
                "expression": f"{lookup_alias}.{field_name}",
                "lookup_table": lookup_table,
                "lookup_join_condition": lookup_condition,
            }

        if parents:
            parent = parents[0]
            upstream = resolve_upstream(parent["from_instance"], parent["from_field"], depth + 1)
            chain = f"{upstream.get('chain', '')} → {instance_name}.{field_name}".strip(" →")
            if field_expr and not _is_passthrough_expression(field_expr, field_name):
                translated_expr = informatca_to_snowflake_expression(field_expr)
                # Resolve named input ports in the current expression back to source fields.
                for (to_instance, to_field), candidate_parents in inbound.items():
                    if to_instance != instance_name or not candidate_parents:
                        continue
                    binding = resolve_upstream(candidate_parents[0]["from_instance"], candidate_parents[0]["from_field"], depth + 1)
                    replacement = binding.get("expression") or (f"src.{binding.get('source_column')}" if binding.get("source_column") else to_field)
                    translated_expr = re.sub(r"\b" + re.escape(to_field) + r"\b", replacement, translated_expr)
                    if not upstream.get("lookup_table") and binding.get("lookup_table"):
                        upstream["lookup_table"] = binding.get("lookup_table")
                        upstream["lookup_join_condition"] = binding.get("lookup_join_condition")
                upstream["expression"] = translated_expr
            upstream["chain"] = chain
            return upstream

        # Handle expression outputs whose inputs use different port names
        # (for example CD_NACE output derived from CD_NACE_in).
        input_bindings = []
        translated_expr = informatca_to_snowflake_expression(field_expr) if field_expr else ""
        propagated_lookup_table = ""
        propagated_lookup_condition = ""
        primary_upstream = None
        bindings_by_port = {}

        for (to_instance, to_field), candidate_parents in inbound.items():
            if to_instance != instance_name or not candidate_parents:
                continue
            parent = candidate_parents[0]
            binding = resolve_upstream(parent["from_instance"], parent["from_field"], depth + 1)
            if primary_upstream is None:
                primary_upstream = binding
            bindings_by_port[to_field] = binding
            replacement = binding.get("expression") or (
                f"src.{binding.get('source_column')}" if binding.get("source_column") else to_field
            )
            if translated_expr:
                translated_expr = re.sub(r"\b" + re.escape(to_field) + r"\b", replacement, translated_expr)
            if not propagated_lookup_table and binding.get("lookup_table"):
                propagated_lookup_table = binding.get("lookup_table", "")
                propagated_lookup_condition = binding.get("lookup_join_condition", "")

        if primary_upstream is not None:
            # Prefer the input port that semantically matches the output field.
            primary_upstream = (
                bindings_by_port.get(f"{field_name}_in")
                or bindings_by_port.get(field_name)
                or primary_upstream
            )
            primary_upstream["expression"] = translated_expr or primary_upstream.get("expression", "")
            primary_upstream["chain"] = f"{primary_upstream.get('chain', '')} → {instance_name}.{field_name}".strip(" →")
            if propagated_lookup_table:
                primary_upstream["lookup_table"] = propagated_lookup_table
                primary_upstream["lookup_join_condition"] = propagated_lookup_condition
            return primary_upstream

        return {
            "source_table": "",
            "source_column": "",
            "chain": f"{instance_name}.{field_name}",
            "expression": informatca_to_snowflake_expression(field_expr) if field_expr.strip().lower() != "null" else "NULL",
            "lookup_table": "",
            "lookup_join_condition": "",
        }

    rows: List[Dict] = []
    findings: List[Dict] = []

    target_instances = [
        (instance_name, data)
        for instance_name, data in instances.items()
        if data.get("object_type") == "Target Definition" or data.get("object_name") in target_defs
    ]

    for target_instance, target_info in target_instances:
        target_table = target_info.get("object_name") or target_instance
        target_definition = target_defs.get(target_table, {"fields": {}})

        for target_field, target_meta in target_definition.get("fields", {}).items():
            incoming = inbound.get((target_instance, target_field), [])
            target_base = {
                "source_system": "Informatica PowerCenter",
                "source_database": "",
                "source_schema": "",
                "source_table": "",
                "source_column": "",
                "source_datatype": "",
                "source_nullable": "",
                "source_pk": "",
                "source_fk": "",
                "target_system": "Snowflake",
                "target_database": "",
                "target_schema": "",
                "target_table": target_table,
                "target_column": target_field,
                "target_datatype": target_meta.get("datatype", "VARCHAR"),
                "target_length": target_meta.get("length", ""),
                "target_precision": target_meta.get("precision", ""),
                "target_scale": target_meta.get("scale", ""),
                "target_nullable": target_meta.get("nullable", "Y"),
                "target_pk": "Y" if "PRIMARY" in target_meta.get("keytype", "").upper() else "",
                "target_fk": "",
                "business_definition": target_meta.get("description", ""),
                "transformation_type": "",
                "transformation_logic": "",
                "lookup_table": "",
                "lookup_join_condition": "",
                "filter_condition": "",
                "dq_rule": "",
                "dq_severity": "MEDIUM",
                "dq_action": "Flag Record",
                "scd_type": "",
                "effective_date_column": "",
                "end_date_column": "",
                "current_flag_column": "",
                "pii_flag": "",
                "data_masking_rule": "",
                "owner": "",
                "approval_status": "Draft",
                "release": "",
                "notes": "",
                "lookup_column": "",
                "join_type": "LEFT",
                "target_default": "",
                "lineage_path": "",
                "migration_status": "Supported with Review",
                "input_mode": "Legacy ETL Mapping",
            }

            if not incoming:
                target_base.update({
                    "transformation_type": "Unmapped Target Field",
                    "approval_status": "Needs Review",
                    "dq_severity": "HIGH",
                    "dq_action": "Block Release",
                    "migration_status": "Manual Decision Required",
                    "notes": "No incoming connector or explicit Informatica default was found.",
                    "lineage_path": f"{target_table}.{target_field}",
                })
                findings.append({
                    "Severity": "HIGH",
                    "Issue": f"Unmapped target field: {target_table}.{target_field}",
                    "Count": 1,
                    "Recommendation": "Confirm a valid source, an approved target default, or an explicit exclusion before release.",
                })
                rows.append(target_base)
                continue

            connector = incoming[0]
            from_instance = connector["from_instance"]
            from_field = connector["from_field"]
            from_info = instances.get(from_instance, {})
            transform_name = from_info.get("object_name") or from_instance
            transform_type = from_info.get("object_type") or transformations.get(transform_name, {}).get("type", "")
            transform = transformations.get(transform_name, {})
            field_meta = transform.get("fields", {}).get(from_field, {})
            attrs = transform.get("attributes", {})
            upstream = resolve_upstream(from_instance, from_field)

            logic = str(upstream.get("expression", "") or "").strip()
            explicit_default = clean_value(field_meta.get("default", ""))
            if not logic and explicit_default:
                logic = informatca_to_snowflake_expression(explicit_default)

            # A literal constant/default is derived logic, not a misleading physical source mapping.
            if _is_constant_sql(logic):
                upstream["source_table"] = ""
                upstream["source_column"] = ""

            target_base.update({
                "source_table": upstream.get("source_table", ""),
                "source_column": upstream.get("source_column", ""),
                "transformation_type": transform_type or "Direct Mapping",
                "transformation_logic": logic,
                "lookup_table": upstream.get("lookup_table", "") or attrs.get("Lookup table name", ""),
                "lookup_join_condition": upstream.get("lookup_join_condition", "") or attrs.get("Lookup condition", ""),
                "filter_condition": attrs.get("Filter Condition", "") or attrs.get("Source Filter", ""),
                "target_default": explicit_default if _is_constant_sql(explicit_default) else "",
                "lineage_path": upstream.get("chain", ""),
                "notes": f"Lineage: {upstream.get('chain', '')}",
            })

            review_types = {
                "Lookup Procedure", "Lookup", "Update Strategy", "Sequence Generator",
                "Router", "Aggregator", "Joiner", "Stored Procedure"
            }
            if transform_type in review_types:
                target_base.update({
                    "approval_status": "Needs Review",
                    "migration_status": "Needs Review",
                    "dq_severity": "HIGH" if transform_type not in ["Lookup", "Lookup Procedure"] else "MEDIUM",
                    "dq_action": "Block Release" if transform_type not in ["Lookup", "Lookup Procedure"] else "Flag Record",
                })
                target_base["notes"] += f" | {transform_type} requires semantic-equivalence review."
                findings.append({
                    "Severity": "HIGH" if transform_type not in ["Lookup", "Lookup Procedure"] else "MEDIUM",
                    "Issue": f"{transform_type} migration review required: {transform_name}",
                    "Count": 1,
                    "Recommendation": "Confirm the Snowflake implementation, edge-case behavior, and test evidence before approval.",
                })

            rows.append(target_base)

    if not rows:
        raise ValueError("No target mappings could be extracted from the Informatica XML.")

    # Mapping-level Source Qualifier filters apply to every generated load block.
    source_filters = []
    for name, data in transformations.items():
        if data.get("type") == "Source Qualifier":
            value = clean_value(data.get("attributes", {}).get("Source Filter", ""))
            if value:
                source_filters.append(informatca_to_snowflake_expression(value))
    if source_filters:
        for row in rows:
            existing = clean_value(row.get("filter_condition", ""))
            if not existing:
                row["filter_condition"] = " AND ".join(source_filters)

    mapping_inventory = pd.DataFrame([{
        "Mapping": mapping_name,
        "Source Definitions": len(source_defs),
        "Target Definitions": len(target_defs),
        "Transformations": len(transformations),
        "Connectors": len(connectors),
        "Extracted Target Mappings": len(rows),
        "Blocked / Needs Review": sum(1 for row in rows if row["approval_status"] == "Needs Review"),
    }])

    transformation_inventory = pd.DataFrame([{
        "Transformation": name,
        "Type": data.get("type", ""),
        "Fields": len(data.get("fields", {})),
        "Lookup Table": data.get("attributes", {}).get("Lookup table name", ""),
        "Migration Treatment": "Needs Review" if data.get("type") in {
            "Lookup Procedure", "Lookup", "Update Strategy", "Sequence Generator",
            "Router", "Aggregator", "Joiner", "Stored Procedure"
        } else "Parsed / SQL Translation Candidate",
    } for name, data in transformations.items()])

    canonical_df = pd.DataFrame(rows)
    for col in CANONICAL_FIELDS:
        if col not in canonical_df.columns:
            canonical_df[col] = ""
    canonical_df = canonical_df[CANONICAL_FIELDS].fillna("")

    return canonical_df, {
        "mapping_inventory": mapping_inventory,
        "transformation_inventory": transformation_inventory,
        "mapping_name": mapping_name,
    }, pd.DataFrame(findings).drop_duplicates().reset_index(drop=True)


def generate_legacy_snowflake_sql(normalized_df: pd.DataFrame) -> str:
    """Generate SQL with explicit expressions/defaults and clear review placeholders."""
    if normalized_df.empty:
        return "-- No mappings available."

    sql_blocks = []
    for target_table, group in normalized_df.groupby("target_table", dropna=False):
        target_table = quote_identifier(target_table) or "TARGET_TABLE"
        source_tables = [v for v in group["source_table"].astype(str).str.strip().unique() if v]
        source_table = quote_identifier(source_tables[0]) if source_tables else "SOURCE_TABLE /* REVIEW: source unresolved */"

        select_lines = []
        where_conditions = []
        joins = []
        seen = set()

        for _, row in group.iterrows():
            target_col = quote_identifier(safe_cell(row, "target_column"))
            if not target_col or target_col in seen:
                continue
            seen.add(target_col)

            logic = str(row.get("transformation_logic", "") or "").strip()
            source_col = quote_identifier(safe_cell(row, "source_column"))
            default = str(row.get("target_default", "") or "").strip()
            status = safe_cell(row, "migration_status")
            notes = safe_cell(row, "notes")

            if logic:
                expr = informatca_to_snowflake_expression(logic)
            elif default:
                expr = informatca_to_snowflake_expression(default)
            elif source_col:
                expr = source_col
            else:
                expr = f"NULL /* REVIEW REQUIRED: {target_col} has no approved source/default */"

            if status == "Manual Decision Required":
                expr += " /* BLOCKED: confirm mapping/default before release */"

            select_lines.append(f"    {expr} AS {target_col}")

            filter_condition = safe_cell(row, "filter_condition")
            if filter_condition and filter_condition not in where_conditions:
                where_conditions.append(informatca_to_snowflake_expression(filter_condition))

            lookup_table = safe_cell(row, "lookup_table")
            lookup_condition = safe_cell(row, "lookup_join_condition")
            if lookup_table:
                comment = f"-- REVIEW: Informatica lookup {lookup_table}"
                if lookup_condition:
                    alias_match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\.", lookup_condition)
                    lookup_alias = alias_match.group(1) if alias_match else "lkp"
                    joins.append(f"LEFT JOIN {lookup_table} {lookup_alias}\n    ON {informatca_to_snowflake_expression(lookup_condition)} {comment}")
                else:
                    joins.append(f"/* {comment}; join condition not resolved */")

        from_clause = f"FROM {source_table} src"
        joins_sql = "\n".join(dict.fromkeys(joins))
        where_sql = f"\nWHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        sql_blocks.append(
            f"""INSERT INTO {target_table}
SELECT
{",\n".join(select_lines)}
{from_clause}
{joins_sql}{where_sql};"""
        )
    return "\n\n".join(sql_blocks)


# ==================================================
# REVIEW WORKFLOW HELPERS
# ==================================================
def init_project_review_state(project_key: str) -> None:
    """Reset review state when a different upload/mode becomes the active delivery packet."""
    if st.session_state.get("active_project_key") != project_key:
        st.session_state.active_project_key = project_key
        st.session_state.review_decisions = {}
        st.session_state.review_history = []
        st.session_state.workflow_status = "Draft"

        # Clear widget state from the prior project so decision/comment values
        # never leak from one review item or upload into another.
        for key in [
            "individual_review_id",
            "individual_reviewer_name",
            "individual_review_decision",
            "individual_review_comment",
            "bulk_review_ids",
            "bulk_reviewer_name",
            "bulk_review_decision",
            "bulk_review_comment",
            "review_feedback",
        ]:
            st.session_state.pop(key, None)


def reset_individual_review_form() -> None:
    """Called whenever a reviewer selects another REV item."""
    st.session_state["individual_review_decision"] = "Pending"
    st.session_state["individual_review_comment"] = ""


def save_review_decision(review_id: str, decision: str, reviewer: str, comment: str, action: str) -> None:
    """Persist the latest decision and an immutable history record."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.review_decisions[review_id] = {
        "decision": decision,
        "reviewer": reviewer,
        "comment": comment,
        "timestamp": timestamp,
    }
    st.session_state.review_history.append({
        "Review ID": review_id,
        "Decision": decision,
        "Reviewer": reviewer,
        "Comment": comment,
        "Timestamp": timestamp,
        "Action": action,
    })
    add_audit_event(action, f"{review_id}: {decision} | {comment}", actor=reviewer)


def build_review_queue(ai_recommendations_df: pd.DataFrame) -> pd.DataFrame:
    if ai_recommendations_df.empty:
        return pd.DataFrame()

    queue = ai_recommendations_df.copy().reset_index(drop=True)
    queue.insert(0, "Review ID", [f"REV-{idx + 1:03d}" for idx in range(len(queue))])

    decision_map = st.session_state.get("review_decisions", {})
    queue["Reviewer Decision"] = queue["Review ID"].map(
        lambda rid: decision_map.get(rid, {}).get("decision", "Pending")
    )
    queue["Reviewer"] = queue["Review ID"].map(
        lambda rid: decision_map.get(rid, {}).get("reviewer", "")
    )
    queue["Comment"] = queue["Review ID"].map(
        lambda rid: decision_map.get(rid, {}).get("comment", "")
    )
    queue["Reviewed At"] = queue["Review ID"].map(
        lambda rid: decision_map.get(rid, {}).get("timestamp", "")
    )

    # Pending and Request Changes remain active. All completed decisions move to history.
    queue["Queue Status"] = queue["Reviewer Decision"].map(
        lambda decision: "Open" if decision in ["Pending", "Request Changes"] else "Closed"
    )
    queue["Bulk Eligible"] = queue.apply(
        lambda row: (
            row["Queue Status"] == "Open"
            and str(row.get("Severity", "")).upper() in ["LOW", "MEDIUM"]
        ),
        axis=1,
    )
    return queue


def unresolved_review_count(review_queue_df: pd.DataFrame) -> int:
    if review_queue_df.empty:
        return 0
    return int((review_queue_df["Queue Status"] == "Open").sum())


def review_status_counts(review_queue_df: pd.DataFrame) -> Dict[str, int]:
    if review_queue_df.empty:
        return {"Open": 0, "Approved": 0, "Rejected": 0, "Request Changes": 0}
    return {
        "Open": int((review_queue_df["Queue Status"] == "Open").sum()),
        "Approved": int(
            review_queue_df["Reviewer Decision"].isin(
                ["Approved", "Approved with Conditions"]
            ).sum()
        ),
        "Rejected": int((review_queue_df["Reviewer Decision"] == "Rejected").sum()),
        "Request Changes": int(
            (review_queue_df["Reviewer Decision"] == "Request Changes").sum()
        ),
    }

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
    key="input_mode",
)

st.markdown("---")

legacy_context = None
legacy_findings_df = pd.DataFrame()
uploaded_file = None
df = pd.DataFrame()
sheet_names: List[str] = []

# ==================================================
# BUSINESS REQUIREMENT / STTM EXPERIENCE
# ==================================================
if input_mode == "Business Requirement / STTM":
    st.markdown("### Start from Business Requirements or Source-to-Target Mapping")
    st.caption(
        "Upload a CSV, Excel source-to-target mapping, or business requirement metadata. "
        "DE Copilot discovers metadata and generates governed Snowflake-ready delivery artifacts."
    )

    with st.expander("Explore Sample STTM Files", expanded=False):
        st.markdown(
            """
**Available samples**

📄 **Basic STTM** — single-table mapping, DDL, SQL, and DQ rules  
🛒 **Retail Multi-Table STTM** — customer, product, and order model with ERD  
🏦 **Banking Multi-Sheet STTM** — customer, account, transaction, and branch workbook  
🔗 **Join Example STTM** — lookup tables, join conditions, and relationship metadata  
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
                with open(path, "rb") as sample_file:
                    sample_cols[index].download_button(
                        label=label,
                        data=sample_file,
                        file_name=path.name,
                        key=f"sample_sttm_{index}",
                    )
            else:
                sample_cols[index].caption(f"Sample unavailable: {path.name}")

    uploaded_file = st.file_uploader(
        "Upload Business Requirement / STTM",
        type=["csv", "xlsx", "xls"],
        key="sttm_upload",
    )

# ==================================================
# LEGACY ETL EXPERIENCE
# ==================================================
else:
    st.markdown("### Start from Legacy ETL Metadata")
    st.caption(
        "Upload an Informatica PowerCenter XML export. DE Copilot extracts source and target metadata, "
        "field-level lineage, expressions, defaults, filters, lookup dependencies, migration risks, "
        "and Snowflake-ready delivery artifacts."
    )

    legacy_platform = st.selectbox(
        "Legacy platform",
        [
            "Informatica PowerCenter XML",
            "DataStage Export — Coming Soon",
            "SSIS Package — Coming Soon",
            "Talend Job Export — Coming Soon",
        ],
        key="legacy_platform",
    )

    if legacy_platform == "Informatica PowerCenter XML":
        with st.expander("Try a Sample Informatica Mapping", expanded=False):
            st.markdown(
                """
**Sample PowerCenter mapping includes**

- Source Qualifier with a source filter
- Expression transformations
- Default and constant values
- Filter logic
- Lookup Procedure dependency
- Field-level lineage
- Target mapping
- Migration findings that require a human decision
"""
            )

            sample_xml_candidates = [
                Path("samples/example.XML"),
                Path("samples/example_informatica_mapping.xml"),
                Path("example.XML"),
            ]
            sample_xml_path = next((path for path in sample_xml_candidates if path.exists()), None)

            if sample_xml_path:
                with open(sample_xml_path, "rb") as sample_file:
                    st.download_button(
                        "⬇️ Download Sample Informatica XML",
                        data=sample_file,
                        file_name="example_informatica_mapping.xml",
                        mime="application/xml",
                        key="download_informatica_sample",
                    )
            else:
                st.info(
                    "To enable this download, place the example XML in "
                    "`samples/example.XML` in the deployed project."
                )

        uploaded_file = st.file_uploader(
            "Upload Informatica PowerCenter XML",
            type=["xml"],
            key="informatica_upload",
        )
    else:
        st.info(
            "This adapter is on the roadmap. Select Informatica PowerCenter XML "
            "for the working legacy-migration demo."
        )
        uploaded_file = None


if uploaded_file:
    try:
        file_name = uploaded_file.name.lower()
        project_key = f"{input_mode}:{uploaded_file.name}:{getattr(uploaded_file, 'size', '')}"
        init_project_review_state(project_key)

        if input_mode == "Legacy ETL Mapping":
            if not file_name.endswith(".xml"):
                st.error("Upload a valid Informatica XML export.")
                st.stop()

            with st.spinner("Parsing Informatica PowerCenter metadata and field lineage..."):
                normalized_df, legacy_context, legacy_findings_df = parse_informatica_powercenter_xml(uploaded_file)
                errors_df, warnings_df, quality_score = validate_canonical_model(normalized_df)

            if not legacy_findings_df.empty:
                warnings_df = pd.concat([warnings_df, legacy_findings_df], ignore_index=True).drop_duplicates()
                quality_score = max(0, quality_score - min(30, len(legacy_findings_df) * 5))

            mapping_source = "Informatica PowerCenter XML Adapter"
            final_mapping = {field: field for field in CANONICAL_FIELDS}
            add_audit_event("Legacy Mapping Parsed", f"{legacy_context['mapping_name']} | {len(normalized_df)} target fields extracted")

            st.success(f"Mapping extracted: {legacy_context['mapping_name']}")
            st.subheader("Legacy Mapping Analysis")
            m1, m2, m3, m4 = st.columns(4)
            inventory = legacy_context["mapping_inventory"].iloc[0]
            m1.metric("Source Definitions", inventory["Source Definitions"])
            m2.metric("Target Definitions", inventory["Target Definitions"])
            m3.metric("Transformations", inventory["Transformations"])
            m4.metric("Review Items", inventory["Blocked / Needs Review"])

            with st.expander("Detected Transformations and Migration Treatment", expanded=False):
                st.dataframe(legacy_context["transformation_inventory"], use_container_width=True)

            if not legacy_findings_df.empty:
                st.warning("The adapter found migration risks. They will remain in the Release Gate until reviewed.")
        else:
            add_audit_event("Business Requirement / STTM Uploaded", f"File: {uploaded_file.name}")

            if file_name.endswith(".csv"):
                raw_df = pd.read_csv(uploaded_file)
                df = normalize_input_columns(raw_df)
                sheet_names = ["CSV"]
            else:
                xls = pd.ExcelFile(uploaded_file)
                all_dfs = []
                for sheet in xls.sheet_names:
                    temp_df = pd.read_excel(xls, sheet_name=sheet).dropna(how="all")
                    if temp_df.empty:
                        continue
                    temp_df = normalize_input_columns(temp_df)
                    if "TARGET_TABLE" not in temp_df.columns:
                        temp_df["TARGET_TABLE"] = sheet
                    temp_df["STTM_SHEET_NAME"] = sheet
                    all_dfs.append(temp_df)
                    sheet_names.append(sheet)

                if not all_dfs:
                    st.error("No valid STTM sheets found in the workbook.")
                    st.stop()
                df = pd.concat(all_dfs, ignore_index=True)

            if "STTM_SHEET_NAME" in df.columns:
                st.subheader("Workbook Summary")
                st.dataframe(df.groupby("STTM_SHEET_NAME").size().reset_index(name="Mappings"), use_container_width=True)

            with st.spinner("Building Canonical Metadata Model..."):
                normalized_df, final_mapping, mapping_source, _, _ = build_canonical_model(df)
                errors_df, warnings_df, quality_score = validate_canonical_model(normalized_df)

            add_audit_event("Canonical Metadata Model Generated", f"Rows: {len(normalized_df)} | Quality: {quality_score}%")

        st.subheader("Metadata Discovery Summary")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Input Mode", "Legacy ETL" if input_mode == "Legacy ETL Mapping" else "Business Requirement")
        s2.metric("Discovery Method", "XML Adapter" if input_mode == "Legacy ETL Mapping" else ("LLM Assisted" if "LLM" in mapping_source else "Rule Based"))
        s3.metric("Canonical Fields", f"{len(normalized_df):,}")
        s4.metric("Metadata Quality", f"{quality_score}%")

        if not errors_df.empty:
            st.error("Critical metadata issues found. Resolve these before release.")
            st.dataframe(errors_df, use_container_width=True)

        if not warnings_df.empty:
            st.warning("Review findings exist. Artifacts are generated for analysis, but the release gate remains controlled.")
            with st.expander("View Validation and Migration Findings", expanded=False):
                st.dataframe(warnings_df, use_container_width=True)

        with st.expander("Canonical Metadata Model", expanded=False):
            st.caption("The shared model used by both Business Requirement and Legacy ETL paths.")
            st.dataframe(normalized_df.head(500), use_container_width=True)
            st.download_button("Download Canonical Metadata", normalized_df.to_csv(index=False),
                               file_name="canonical_metadata_model.csv", mime="text/csv")

        er_diagram = generate_er_diagram(normalized_df)
        graphviz_dot = generate_graphviz_erd(normalized_df)
        ddl = generate_ddl(normalized_df)
        sql = generate_sql(normalized_df)
        dictionary_df = generate_data_dictionary(normalized_df)
        tech_spec_df = generate_tech_spec(normalized_df)
        dq_df = generate_dq_rules(normalized_df)
        ai_recommendation_df = generate_ai_recommendations(normalized_df, warnings_df)

        # Add one review item per explicit migration/manual mapping status.
        if input_mode == "Legacy ETL Mapping":
            special_review_items = []
            for _, row in normalized_df.iterrows():
                if safe_cell(row, "migration_status") in ["Needs Review", "Manual Decision Required"]:
                    special_review_items.append(
                        _review_item(
                            "Legacy Migration",
                            f"{safe_cell(row, 'target_table')}.{safe_cell(row, 'target_column')}",
                            safe_cell(row, "notes") or "Confirm equivalent Snowflake implementation.",
                            "HIGH" if safe_cell(row, "migration_status") == "Manual Decision Required" else "MEDIUM",
                        )
                    )
            if special_review_items:
                ai_recommendation_df = pd.concat([ai_recommendation_df, pd.DataFrame(special_review_items)], ignore_index=True).drop_duplicates()

        observability_metrics = generate_observability_metrics(normalized_df, dq_df, warnings_df, ai_recommendation_df)
        review_queue_df = build_review_queue(ai_recommendation_df)
        open_count = unresolved_review_count(review_queue_df)

        tabs = st.tabs([
            "ER Diagram", "Snowflake DDL", "Snowflake SQL", "Data Dictionary",
            "Technical Spec", "DQ Rules", "🤖 AI Analysis", "🧠 Findings",
            "👤 Human Review", "✅ Approval & Release", "📊 Observability", "🧾 Audit Trail"
        ])

        with tabs[0]:
            st.subheader("Entity Relationship Diagram")
            st.graphviz_chart(graphviz_dot)
            st.download_button("Download ER Diagram", graphviz_dot, file_name="er_diagram.dot", mime="text/plain")

        with tabs[1]:
            st.subheader("Snowflake Target DDL")
            st.caption("Only explicit constants/defaults extracted from Informatica are included. Missing values are never invented.")
            st.code(ddl, language="sql")
            st.download_button("Download DDL", ddl, file_name="snowflake_ddl.sql", mime="text/plain")

        with tabs[2]:
            st.subheader("Snowflake Transformation SQL")
            st.caption("Derived expressions, explicit constants/defaults, source filters, and unresolved fields are visible in the generated SQL.")
            st.code(sql, language="sql")
            st.download_button("Download SQL", sql, file_name="snowflake_transformation.sql", mime="text/plain")

        with tabs[3]:
            st.dataframe(dictionary_df, use_container_width=True)
            st.download_button("Download Data Dictionary", dictionary_df.to_csv(index=False), file_name="data_dictionary.csv", mime="text/csv")

        with tabs[4]:
            st.dataframe(tech_spec_df, use_container_width=True)
            st.download_button("Download Technical Spec", tech_spec_df.to_csv(index=False), file_name="technical_spec.csv", mime="text/csv")

        with tabs[5]:
            st.dataframe(dq_df, use_container_width=True)
            st.download_button("Download DQ Rules", dq_df.to_csv(index=False), file_name="dq_rules.csv", mime="text/csv")

        with tabs[6]:
            st.subheader("AI Metadata Analysis")
            st.caption("AI analysis is advisory. The governed Release Gate remains the decision point.")
            if st.button("Generate AI Insights", key="generate_ai_insights"):
                with st.spinner("Analyzing canonical metadata..."):
                    ai_response = generate_ai_analysis(normalized_df)
                    add_audit_event("AI Analysis Completed", "Metadata analysis generated")
                    st.markdown(ai_response)
                    st.download_button("Download AI Analysis", ai_response, file_name="ai_analysis.txt", mime="text/plain")

        with tabs[7]:
            st.subheader("Validation, Migration Risks & Recommendations")
            p1, p2, p3 = st.columns(3)
            p1.metric("High Priority", int((ai_recommendation_df["Severity"] == "HIGH").sum()))
            p2.metric("Medium Priority", int((ai_recommendation_df["Severity"] == "MEDIUM").sum()))
            p3.metric("Open Review Items", open_count)
            st.dataframe(ai_recommendation_df, use_container_width=True)
            st.download_button("Download Findings", ai_recommendation_df.to_csv(index=False), file_name="delivery_findings.csv", mime="text/csv")

        with tabs[8]:
            st.subheader("Human Review Queue")
            st.caption(
                "Risk-based review workflow. Approved or rejected items leave the active queue and appear in Review History. "
                "High-priority items must be reviewed individually."
            )

            # Rebuild every run so completed decisions immediately move out of the active queue.
            review_queue_df = build_review_queue(ai_recommendation_df)
            open_queue = review_queue_df[review_queue_df["Queue Status"] == "Open"].copy()
            closed_queue = review_queue_df[review_queue_df["Queue Status"] == "Closed"].copy()
            counts = review_status_counts(review_queue_df)

            q1, q2, q3, q4 = st.columns(4)
            q1.metric("Open Items", counts["Open"])
            q2.metric("Approved", counts["Approved"])
            q3.metric("Rejected", counts["Rejected"])
            q4.metric("Request Changes", counts["Request Changes"])

            feedback = st.session_state.pop("review_feedback", "")
            if feedback:
                st.success(feedback)

            st.markdown("### Open Review Queue")
            if open_queue.empty:
                st.success("No open review items remain.")
            else:
                display_cols = [
                    col for col in [
                        "Review ID", "Severity", "Category", "Artifact",
                        "Recommendation", "Reviewer Decision", "Bulk Eligible"
                    ] if col in open_queue.columns
                ]
                st.dataframe(open_queue[display_cols], use_container_width=True, hide_index=True)

                # ----------------------------------------------------------
                # BULK REVIEW — intentionally restricted to LOW / MEDIUM risk
                # ----------------------------------------------------------
                st.markdown("### Bulk Review")
                st.caption(
                    "Bulk review is available only for Low and Medium priority findings. "
                    "High-priority migration and governance risks require individual review."
                )

                bulk_eligible_queue = open_queue[open_queue["Bulk Eligible"]].copy()
                if bulk_eligible_queue.empty:
                    st.info("No low- or medium-risk open items are eligible for bulk review.")
                else:
                    bulk_review_ids = st.multiselect(
                        "Select multiple eligible review items",
                        bulk_eligible_queue["Review ID"].tolist(),
                        key="bulk_review_ids",
                    )
                    bulk_col1, bulk_col2 = st.columns(2)
                    with bulk_col1:
                        st.text_input(
                            "Bulk reviewer name",
                            value="Amit Singh",
                            key="bulk_reviewer_name",
                        )
                    with bulk_col2:
                        st.selectbox(
                            "Bulk decision",
                            ["Approved", "Approved with Conditions", "Rejected", "Request Changes"],
                            key="bulk_review_decision",
                        )

                    st.text_area(
                        "Bulk reviewer comment",
                        key="bulk_review_comment",
                        placeholder="Apply the same decision and rationale to all selected low/medium-risk items.",
                    )

                    def apply_bulk_review() -> None:
                        selected_ids = st.session_state.get("bulk_review_ids", [])
                        if not selected_ids:
                            st.session_state["review_feedback"] = "Select at least one eligible review item for bulk review."
                            return

                        reviewer = clean_value(st.session_state.get("bulk_reviewer_name", "Amit Singh"), "Amit Singh")
                        decision = st.session_state.get("bulk_review_decision", "Approved")
                        comment = clean_value(st.session_state.get("bulk_review_comment", ""))

                        for review_id in selected_ids:
                            save_review_decision(
                                review_id,
                                decision,
                                reviewer,
                                comment,
                                "Bulk Review Decision Recorded",
                            )

                        st.session_state["review_feedback"] = (
                            f"Applied '{decision}' to {len(selected_ids)} eligible review item(s)."
                        )
                        # Reset bulk form so values cannot accidentally carry into a later selection.
                        st.session_state["bulk_review_ids"] = []
                        st.session_state["bulk_review_comment"] = ""

                    st.button(
                        "Apply Bulk Review Decision",
                        key="apply_bulk_review",
                        disabled=not bulk_review_ids,
                        on_click=apply_bulk_review,
                        use_container_width=True,
                    )

                # ----------------------------------------------------------
                # INDIVIDUAL REVIEW — decision/comment reset on REV change
                # ----------------------------------------------------------
                st.markdown("### Individual Review")
                st.caption("Select an item for a detailed decision. Switching the review ID clears the prior decision and comment.")

                st.selectbox(
                    "Select open item",
                    open_queue["Review ID"].tolist(),
                    key="individual_review_id",
                    on_change=reset_individual_review_form,
                )
                st.text_input(
                    "Reviewer name",
                    value="Amit Singh",
                    key="individual_reviewer_name",
                )
                st.selectbox(
                    "Decision",
                    ["Pending", "Approved", "Approved with Conditions", "Rejected", "Request Changes"],
                    key="individual_review_decision",
                )
                st.text_area(
                    "Reviewer comment",
                    key="individual_review_comment",
                    placeholder="Add approval rationale, conditions, rejection reason, or required changes.",
                )

                def apply_individual_review() -> None:
                    review_id = st.session_state.get("individual_review_id")
                    reviewer = clean_value(st.session_state.get("individual_reviewer_name", "Amit Singh"), "Amit Singh")
                    decision = st.session_state.get("individual_review_decision", "Pending")
                    comment = clean_value(st.session_state.get("individual_review_comment", ""))

                    if not review_id:
                        st.session_state["review_feedback"] = "Select a review item before saving."
                        return
                    if decision == "Pending":
                        st.session_state["review_feedback"] = "Choose Approved, Approved with Conditions, Rejected, or Request Changes before saving."
                        return

                    save_review_decision(
                        review_id,
                        decision,
                        reviewer,
                        comment,
                        "Individual Review Decision Recorded",
                    )
                    st.session_state["review_feedback"] = f"Saved {decision} for {review_id}."
                    # The next selected REV must start with a blank decision/comment form.
                    st.session_state.pop("individual_review_id", None)
                    reset_individual_review_form()

                st.button(
                    "Save Review Decision",
                    key="save_individual_review",
                    on_click=apply_individual_review,
                )

            st.markdown("---")
            with st.expander("Review History", expanded=False):
                if closed_queue.empty:
                    st.info("No completed review decisions yet.")
                else:
                    history_cols = [
                        col for col in [
                            "Review ID", "Severity", "Category", "Artifact", "Recommendation",
                            "Reviewer Decision", "Reviewer", "Comment", "Reviewed At"
                        ] if col in closed_queue.columns
                    ]
                    st.dataframe(closed_queue[history_cols], use_container_width=True, hide_index=True)

                if st.session_state.get("review_history"):
                    st.download_button(
                        "Download Review History",
                        pd.DataFrame(st.session_state.review_history).to_csv(index=False),
                        file_name="review_history.csv",
                        mime="text/csv",
                    )

        with tabs[9]:
            st.subheader("Approval & Release Gate")
            st.caption("The release package stays locked until all review items are closed and an approver records the final decision.")

            # Rebuild after any review decision.
            review_queue_df = build_review_queue(ai_recommendation_df)
            open_count = unresolved_review_count(review_queue_df)
            can_approve = open_count == 0

            status_options = ["Draft", "Under Review", "Approved with Conditions", "Approved", "Rejected"]
            current_status = st.session_state.workflow_status
            if current_status not in status_options:
                current_status = "Draft"

            requested_status = st.selectbox(
                "Final workflow status",
                status_options,
                index=status_options.index(current_status),
                key="workflow_status_selector",
            )

            if requested_status in ["Approved", "Approved with Conditions"] and not can_approve:
                st.error(f"Release is blocked: {open_count} review item(s) remain open.")
                st.session_state.workflow_status = "Under Review"
            else:
                st.session_state.workflow_status = requested_status

            if st.session_state.workflow_status in ["Approved", "Approved with Conditions"]:
                st.success("Release Gate: APPROVED")
            elif st.session_state.workflow_status == "Rejected":
                st.error("Release Gate: BLOCKED")
            else:
                st.warning("Release Gate: PENDING REVIEW")

            if st.button("Record Workflow Status", key="record_workflow"):
                add_audit_event("Workflow Status Updated", st.session_state.workflow_status)
                st.success("Workflow status recorded.")

            manifest = generate_deployment_manifest(uploaded_file.name, st.session_state.workflow_status, observability_metrics)
            st.code(manifest, language="json")

            if st.session_state.workflow_status in ["Approved", "Approved with Conditions"]:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("canonical_metadata_model.csv", normalized_df.to_csv(index=False))
                    zf.writestr("snowflake_ddl.sql", ddl)
                    zf.writestr("snowflake_transformation.sql", sql)
                    zf.writestr("er_diagram.dot", graphviz_dot)
                    zf.writestr("data_dictionary.csv", dictionary_df.to_csv(index=False))
                    zf.writestr("technical_specification.csv", tech_spec_df.to_csv(index=False))
                    zf.writestr("dq_rules.csv", dq_df.to_csv(index=False))
                    zf.writestr("delivery_findings.csv", ai_recommendation_df.to_csv(index=False))
                    zf.writestr("review_history.csv", pd.DataFrame(st.session_state.review_history).to_csv(index=False))
                    zf.writestr("deployment_manifest.json", manifest)
                    zf.writestr("audit_log.csv", pd.DataFrame(st.session_state.audit_events).to_csv(index=False))
                zip_buffer.seek(0)
                st.download_button("🚀 Download Approved Delivery Packet", zip_buffer,
                                   file_name="de_copilot_approved_delivery_packet.zip",
                                   mime="application/zip", use_container_width=True)
            else:
                st.info("Close all review items and approve the workflow to unlock the delivery packet.")

            st.download_button("Download Deployment Manifest", manifest,
                               file_name="deployment_manifest.json", mime="application/json")

        with tabs[10]:
            st.subheader("Observability Dashboard")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Target Tables", observability_metrics["Target Tables"])
            c2.metric("Canonical Fields", observability_metrics["Canonical Columns"])
            c3.metric("Metadata Coverage", f"{observability_metrics['Metadata Coverage %']}%")
            c4.metric("Open Reviews", open_count)
            st.dataframe(pd.DataFrame([observability_metrics]), use_container_width=True)

        with tabs[11]:
            st.subheader("Audit Trail")
            audit_df = pd.DataFrame(st.session_state.audit_events)
            if audit_df.empty:
                st.info("No audit events recorded yet.")
            else:
                st.dataframe(audit_df, use_container_width=True)
                st.download_button("Download Audit Log", audit_df.to_csv(index=False),
                                   file_name="audit_log.csv", mime="text/csv")

    except Exception as exc:
        st.error("The input could not be processed.")
        st.exception(exc)
else:
    st.info("Start from a Business Requirement / STTM or a Legacy Informatica PowerCenter XML export.")
