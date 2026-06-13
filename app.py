# app.py

import json
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="DE Copilot",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ DE Copilot")

st.markdown(
    """
### Enterprise STTM Factory

Upload an STTM and automatically generate:

✅ Snowflake DDL  
✅ Snowflake SQL  
✅ Data Dictionary  
✅ Technical Specifications  
✅ Data Quality Rules  
✅ AI Analysis  
"""
)

# --------------------------------------------------
# OPENAI CLIENT
# --------------------------------------------------

def get_openai_client():
    try:
        return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except Exception:
        return None


client = get_openai_client()

# --------------------------------------------------
# CANONICAL MODEL
# --------------------------------------------------

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
]

COLUMN_ALIASES: Dict[str, List[str]] = {
    "source_system": ["SOURCE_SYSTEM", "SOURCE_SYSTEM_NAME", "SRC_SYSTEM"],
    "source_database": ["SOURCE_DATABASE", "SRC_DATABASE"],
    "source_schema": ["SOURCE_SCHEMA", "SRC_SCHEMA"],
    "source_table": [
        "SOURCE_TABLE",
        "SOURCE_TABLE_NAME",
        "SOURCE_TABLE_VIEW",
        "SOURCE_TABLE_PHYSICAL_NAME",
        "SRC_TABLE",
        "SRC_TABLE_NAME",
    ],
    "source_column": [
        "SOURCE_COLUMN",
        "SOURCE_COLUMN_NAME",
        "SOURCE_COLUMN_PHYSICAL_NAME",
        "SRC_COLUMN",
        "SRC_COLUMN_NAME",
        "SOURCE_FIELD",
    ],
    "source_datatype": [
        "SOURCE_DATA_TYPE",
        "SOURCE_DATATYPE",
        "SRC_DATA_TYPE",
        "SOURCE_TYPE",
    ],
    "source_nullable": ["SOURCE_NULLABLE", "SOURCE_IS_NULLABLE", "SRC_NULLABLE"],
    "source_pk": ["SOURCE_PK", "SOURCE_IS_PK", "SRC_PK"],
    "source_fk": ["SOURCE_FK", "SOURCE_IS_FK", "SRC_FK"],
    "target_system": ["TARGET_SYSTEM", "TARGET_SYSTEM_NAME", "TGT_SYSTEM"],
    "target_database": ["TARGET_DATABASE", "TGT_DATABASE"],
    "target_schema": ["TARGET_SCHEMA", "TGT_SCHEMA"],
    "target_table": [
        "TARGET_TABLE",
        "TARGET_TABLE_NAME",
        "TARGET_TABLE_PHYSICAL_NAME",
        "TARGET_TABLE_LOGICAL_NAME",
        "TGT_TABLE",
        "TGT_TABLE_NAME",
    ],
    "target_column": [
        "TARGET_COLUMN",
        "TARGET_COLUMN_NAME",
        "TARGET_COLUMN_PHYSICAL_NAME",
        "TGT_COLUMN",
        "TGT_COLUMN_NAME",
        "TARGET_FIELD",
    ],
    "target_datatype": [
        "TARGET_DATA_TYPE",
        "TARGET_DATATYPE",
        "TGT_DATA_TYPE",
        "DATA_TYPE",
        "DATATYPE",
    ],
    "target_length": ["TARGET_LENGTH", "LENGTH", "TARGET_COLUMN_LENGTH"],
    "target_precision": ["TARGET_PRECISION", "PRECISION"],
    "target_scale": ["TARGET_SCALE", "SCALE"],
    "target_nullable": [
        "TARGET_NULLABLE",
        "TARGET_IS_NULLABLE",
        "NULLABLE",
        "IS_NULLABLE",
    ],
    "target_pk": ["TARGET_PK", "TARGET_IS_PK", "PRIMARY_KEY", "IS_PK"],
    "target_fk": ["TARGET_FK", "TARGET_IS_FK", "FOREIGN_KEY", "IS_FK"],
    "business_definition": [
        "BUSINESS_DEFINITION",
        "BUSINESS_RULE_DESCRIPTION",
        "SOURCE_DESCRIPTION",
        "TARGET_DESCRIPTION",
        "COLUMN_DESCRIPTION",
        "DESCRIPTION",
    ],
    "transformation_type": ["TRANSFORMATION_TYPE", "TRANSFORM_TYPE"],
    "transformation_logic": [
        "TRANSFORMATION_LOGIC",
        "TRANSFORMATION_RULE",
        "RULE",
        "LOGIC",
        "DERIVATION_LOGIC",
    ],
    "lookup_table": ["LOOKUP_TABLE", "LOOKUP_TABLE_NAME", "REFERENCE_TABLE"],
    "lookup_join_condition": [
        "LOOKUP_JOIN_CONDITION",
        "LOOKUP_CONDITION",
        "JOIN_CONDITION",
    ],
    "filter_condition": ["FILTER_CONDITION", "WHERE_CONDITION"],
    "dq_rule": [
        "DQ_RULE",
        "DATA_QUALITY_RULE",
        "DATA_QUALITY_RULE_DESCRIPTION",
        "VALIDATION_RULE",
    ],
    "dq_severity": ["DQ_SEVERITY", "SEVERITY"],
    "dq_action": ["DQ_ACTION", "DQ_FAILURE_ACTION", "ERROR_ACTION"],
    "scd_type": ["SCD_TYPE"],
    "effective_date_column": ["EFFECTIVE_DATE_COLUMN", "SCD_EFFECTIVE_DATE_COLUMN"],
    "end_date_column": ["END_DATE_COLUMN", "SCD_END_DATE_COLUMN"],
    "current_flag_column": ["CURRENT_FLAG_COLUMN", "SCD_CURRENT_FLAG_COLUMN"],
    "pii_flag": ["PII_FLAG", "IS_PII", "IS_PII_TARGET", "IS_PII_SOURCE"],
    "data_masking_rule": ["DATA_MASKING_RULE", "MASKING_RULE"],
    "owner": ["OWNER", "MAPPING_OWNER", "TECHNICAL_LEAD"],
    "approval_status": ["APPROVAL_STATUS", "STTM_STATUS", "QA_STATUS"],
    "release": ["RELEASE", "PHASE_RELEASE", "SPRINT_ID"],
    "notes": ["NOTES", "NOTES_COMMENTS", "COMMENTS"],
}

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def normalize_column_name(col: str) -> str:
    return (
        str(col)
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .upper()
    )


def normalize_input_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [normalize_column_name(col) for col in normalized.columns]
    return normalized


def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    cols = set(df.columns)
    for alias in aliases:
        alias_normalized = normalize_column_name(alias)
        if alias_normalized in cols:
            return alias_normalized
    return None


def rule_based_column_mapping(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    mapping = {}
    for field, aliases in COLUMN_ALIASES.items():
        mapping[field] = find_column(df, aliases)
    return mapping


def mapping_confidence(mapping: Dict[str, Optional[str]]) -> float:
    required = [
        "source_table",
        "source_column",
        "target_table",
        "target_column",
        "target_datatype",
    ]
    matched = sum(1 for field in required if mapping.get(field))
    return matched / len(required)


def llm_column_mapping(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    if client is None:
        return {}

    columns = list(df.columns)

    prompt = f"""
You are a data engineering metadata parser.

Map uploaded STTM column names to this canonical model.

Canonical fields:
{CANONICAL_FIELDS}

Uploaded columns:
{columns}

Return only valid JSON.
Keys must be canonical field names.
Values must be uploaded column names or null.

Do not explain.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        cleaned = {}
        for field in CANONICAL_FIELDS:
            value = parsed.get(field)
            if value:
                value = normalize_column_name(value)
                cleaned[field] = value if value in df.columns else None
            else:
                cleaned[field] = None

        return cleaned

    except Exception:
        return {}


def safe_cell(row: pd.Series, col: Optional[str], default: str = "") -> str:
    if col and col in row.index and pd.notna(row[col]):
        return str(row[col]).strip()
    return default


def snowflake_type(row: pd.Series) -> str:
    dtype = safe_cell(row, "target_datatype", "VARCHAR").upper()
    length = safe_cell(row, "target_length")
    precision = safe_cell(row, "target_precision")
    scale = safe_cell(row, "target_scale")

    if dtype in ["VARCHAR2", "STRING", "TEXT", "CHAR"]:
        dtype = "VARCHAR"

    if dtype == "VARCHAR":
        if length and length not in ["0", "N/A", "NA", "NONE"]:
            return f"VARCHAR({length})"
        return "VARCHAR"

    if dtype in ["NUMBER", "NUMERIC", "DECIMAL"]:
        if precision and scale and precision not in ["0", "N/A", "NA", "NONE"]:
            return f"NUMBER({precision},{scale})"
        if precision and precision not in ["0", "N/A", "NA", "NONE"]:
            return f"NUMBER({precision})"
        return "NUMBER"

    if dtype in ["DATE"]:
        return "DATE"

    if dtype in ["TIMESTAMP", "DATETIME", "TIMESTAMP_NTZ"]:
        return "TIMESTAMP_NTZ"

    if dtype in ["BOOLEAN", "BOOL"]:
        return "BOOLEAN"

    return dtype


def build_normalized_sttm(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    rows = []

    for _, row in df.iterrows():
        normalized_row = {}

        for field in CANONICAL_FIELDS:
            source_col = mapping.get(field)
            normalized_row[field] = safe_cell(row, source_col)

        rows.append(normalized_row)

    normalized_df = pd.DataFrame(rows)

    normalized_df = normalized_df[
        normalized_df["target_column"].astype(str).str.strip() != ""
    ]

    return normalized_df


def generate_ddl(normalized_df: pd.DataFrame) -> str:
    if normalized_df.empty:
        return "-- No valid target columns found."

    ddl_blocks = []

    for target_table, group in normalized_df.groupby("target_table"):
        if not target_table:
            target_table = "TARGET_TABLE"

        column_lines = []

        for _, row in group.iterrows():
            col_name = safe_cell(row, "target_column")
            if not col_name:
                continue

            data_type = snowflake_type(row)

            nullable = safe_cell(row, "target_nullable").upper()
            not_null = " NOT NULL" if nullable in ["N", "NO", "FALSE", "0"] else ""

            column_lines.append(f"    {col_name} {data_type}{not_null}")

        ddl = f"""CREATE OR REPLACE TABLE {target_table}
(
{",\n".join(column_lines)}
);"""

        ddl_blocks.append(ddl)

    return "\n\n".join(ddl_blocks)


def generate_sql(normalized_df: pd.DataFrame) -> str:
    if normalized_df.empty:
        return "-- No valid mappings found."

    sql_blocks = []

    for target_table, group in normalized_df.groupby("target_table"):
        if not target_table:
            target_table = "TARGET_TABLE"

        source_table = group["source_table"].dropna().astype(str).replace("", pd.NA).dropna()
        source_table_name = source_table.iloc[0] if not source_table.empty else "SOURCE_TABLE"

        select_lines = []

        for _, row in group.iterrows():
            source_col = safe_cell(row, "source_column")
            target_col = safe_cell(row, "target_column")
            logic = safe_cell(row, "transformation_logic")

            if not target_col:
                continue

            if logic and logic.upper() not in ["DIRECT", "DIRECT MAPPING", "N/A", "NA", "NONE"]:
                select_expr = logic
            elif source_col:
                select_expr = source_col
            else:
                select_expr = f"NULL /* missing source for {target_col} */"

            select_lines.append(f"    {select_expr} AS {target_col}")

        sql = f"""INSERT INTO {target_table}
SELECT
{",\n".join(select_lines)}
FROM {source_table_name};"""

        sql_blocks.append(sql)

    return "\n\n".join(sql_blocks)


def generate_data_dictionary(normalized_df: pd.DataFrame) -> pd.DataFrame:
    dictionary_df = normalized_df[
        [
            "target_table",
            "target_column",
            "target_datatype",
            "target_length",
            "target_precision",
            "target_scale",
            "target_nullable",
            "target_pk",
            "business_definition",
            "pii_flag",
            "data_masking_rule",
        ]
    ].copy()

    dictionary_df.columns = [
        "Target Table",
        "Target Column",
        "Data Type",
        "Length",
        "Precision",
        "Scale",
        "Nullable",
        "Primary Key",
        "Business Definition",
        "PII Flag",
        "Data Masking Rule",
    ]

    return dictionary_df


def generate_tech_spec(normalized_df: pd.DataFrame) -> pd.DataFrame:
    tech_df = normalized_df[
        [
            "source_system",
            "source_table",
            "source_column",
            "target_table",
            "target_column",
            "target_datatype",
            "target_nullable",
            "transformation_type",
            "transformation_logic",
            "lookup_table",
            "lookup_join_condition",
            "filter_condition",
            "dq_rule",
            "scd_type",
            "owner",
            "approval_status",
            "release",
            "notes",
        ]
    ].copy()

    tech_df.columns = [
        "Source System",
        "Source Table",
        "Source Column",
        "Target Table",
        "Target Column",
        "Target Data Type",
        "Nullable",
        "Transformation Type",
        "Transformation Logic",
        "Lookup Table",
        "Lookup Join Condition",
        "Filter Condition",
        "DQ Rule",
        "SCD Type",
        "Owner",
        "Approval Status",
        "Release",
        "Notes",
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


def generate_ai_analysis(normalized_df: pd.DataFrame) -> str:
    if client is None:
        return "OpenAI API key is not configured. Add OPENAI_API_KEY in Streamlit Secrets."

    sample_data = normalized_df.head(100).to_csv(index=False)

    prompt = f"""
You are a Senior Data Architect.

Analyze this normalized STTM metadata.

Provide:

1. Executive Summary
2. Business Purpose
3. Source & Target Analysis
4. Primary Key Recommendations
5. Data Quality Recommendations
6. Suggested Test Cases
7. Risks
8. Improvement Opportunities

Normalized STTM sample:

{sample_data}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content


# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------

uploaded_file = st.file_uploader("Upload STTM CSV", type=["csv"])

if uploaded_file:
    try:
        raw_df = pd.read_csv(uploaded_file)
        df = normalize_input_columns(raw_df)

        st.success("STTM Uploaded Successfully")
        st.caption(f"Rows uploaded: {len(df):,} | Columns detected: {len(df.columns):,}")

        with st.expander("Uploaded STTM Preview", expanded=False):
            st.dataframe(df.head(200), use_container_width=True)

        rule_mapping = rule_based_column_mapping(df)
        confidence = mapping_confidence(rule_mapping)

        final_mapping = rule_mapping.copy()
        mapping_source = "Rule-Based Detection"

        if confidence < 0.8:
            llm_mapping = llm_column_mapping(df)
            if llm_mapping:
                for field in CANONICAL_FIELDS:
                    if not final_mapping.get(field) and llm_mapping.get(field):
                        final_mapping[field] = llm_mapping[field]
                mapping_source = "Rule-Based + LLM Assisted Detection"

        normalized_df = build_normalized_sttm(df, final_mapping)

        st.subheader("Detected STTM Structure")
        st.caption(f"Detection Method: {mapping_source}")

        detection_df = pd.DataFrame(
            [
                {
                    "Canonical Field": field,
                    "Detected Uploaded Column": final_mapping.get(field),
                }
                for field in CANONICAL_FIELDS
            ]
        )

        st.dataframe(detection_df, use_container_width=True)

        required_fields = ["target_table", "target_column", "target_datatype"]
        missing = [field for field in required_fields if not final_mapping.get(field)]

        if missing:
            st.error(
                "Required STTM fields could not be detected: "
                + ", ".join(missing)
            )
            st.stop()

        st.subheader("Normalized STTM Model")
        st.dataframe(normalized_df.head(200), use_container_width=True)

        ddl = generate_ddl(normalized_df)
        sql = generate_sql(normalized_df)
        dictionary_df = generate_data_dictionary(normalized_df)
        tech_spec_df = generate_tech_spec(normalized_df)
        dq_df = generate_dq_rules(normalized_df)

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            [
                "Snowflake DDL",
                "Snowflake SQL",
                "Data Dictionary",
                "Technical Spec",
                "DQ Rules",
                "🤖 AI Analysis",
            ]
        )

        with tab1:
            st.code(ddl, language="sql")
            st.download_button(
                "Download DDL",
                ddl,
                file_name="snowflake_ddl.sql",
                mime="text/plain",
            )

        with tab2:
            st.code(sql, language="sql")
            st.download_button(
                "Download SQL",
                sql,
                file_name="snowflake_sql.sql",
                mime="text/plain",
            )

        with tab3:
            st.dataframe(dictionary_df, use_container_width=True)
            st.download_button(
                "Download Data Dictionary",
                dictionary_df.to_csv(index=False),
                file_name="data_dictionary.csv",
                mime="text/csv",
            )

        with tab4:
            st.dataframe(tech_spec_df, use_container_width=True)
            st.download_button(
                "Download Technical Spec",
                tech_spec_df.to_csv(index=False),
                file_name="technical_spec.csv",
                mime="text/csv",
            )

        with tab5:
            st.dataframe(dq_df, use_container_width=True)
            st.download_button(
                "Download DQ Rules",
                dq_df.to_csv(index=False),
                file_name="dq_rules.csv",
                mime="text/csv",
            )

        with tab6:
            st.subheader("AI STTM Analysis")
            st.info("AI analysis uses the normalized STTM model and only the first 100 rows.")

            if st.button("Generate AI Insights"):
                with st.spinner("Analyzing STTM using AI..."):
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
    st.info("Upload a CSV STTM file to get started.")