import streamlit as st
import pandas as pd
import json
from openai import OpenAI

# --------------------------------------------------
# CONFIGURATION & INITIALIZATION
# --------------------------------------------------
st.set_page_config(
    page_title="DE Copilot",
    page_icon="🚀",
    layout="wide"
)

client = None
try:
    if "OPENAI_API_KEY" in st.secrets:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    client = None

st.title("🚀 DataEngineeringCopilot")
st.markdown("### Enterprise STTM Parser & Artifact Generator")

# --------------------------------------------------
# PARSING ENGINE FUNCTIONS
# --------------------------------------------------
def normalize_string(s):
    return str(s).strip().upper().replace(" ", "_").replace("-", "_").replace("/", "_")

def guess_columns_heuristically(uploaded_headers):
    """
    Scores and ranks headers dynamically to catch target logic fields while
    filtering out noise from massive (e.g. 100-column) metadata structures.
    """
    guessed_mapping = {}
    normalized_headers = [normalize_string(h) for h in uploaded_headers]
    header_map = dict(zip(normalized_headers, uploaded_headers))

    # Highest priority targets are placed first in lists to prevent false-positives
    targets = {
        "SOURCE_TABLE": ["SRC_TABLE_PHYSICAL_NAME", "SOURCE_TABLE_PHYSICAL_NAME", "SOURCE_TABLE_PHYSICAL", "SRC_PHYS_NAME", "SRC_TBL", "SRC_TABLE", "SOURCE_TABLE"],
        "SOURCE_COLUMN": ["SRC_COLUMN_PHYSICAL_NAME", "SOURCE_COLUMN_PHYSICAL_NAME", "SOURCE_COLUMN_PHYSICAL", "SRC_COL_PHYS", "SRC_COL", "SRC_COLUMN", "SOURCE_COLUMN"],
        "TARGET_TABLE": ["TGT_TABLE_PHYSICAL_NAME", "TARGET_TABLE_PHYSICAL_NAME", "TARGET_TABLE_PHYSICAL", "TGT_PHYS_NAME", "TARGET_TABLE_LOGICAL_NAME", "TGT_TBL", "TARGET_TABLE"],
        "TARGET_COLUMN": ["TGT_COLUMN_PHYSICAL_NAME", "TARGET_COLUMN_PHYSICAL_NAME", "TARGET_COLUMN_PHYSICAL", "TGT_COL_PHYS", "TARGET_COLUMN_NAME", "TGT_COL", "TARGET_COLUMN"],
        "DATA_TYPE": ["TARGET_DATA_TYPE", "TGT_DATA_TYPE", "DATA_TYPE", "DATATYPE", "TYPE"],
        "LENGTH": ["TARGET_LENGTH", "TGT_LENGTH", "LENGTH", "SIZE", "MAX_LEN"],
        "PRECISION": ["TARGET_PRECISION", "TGT_PRECISION", "PRECISION"],
        "SCALE": ["TARGET_SCALE", "TGT_SCALE", "SCALE"],
        "NULLABLE": ["TARGET_IS_NULLABLE", "IS_NULLABLE", "NULLABLE"],
        "TRANSFORMATION_RULE": ["TRANSFORMATION_LOGIC", "TRANSFORMATION", "LOGIC", "BUSINESS_RULE_DESCRIPTION"],
        "BUSINESS_DEFINITION": ["SOURCE_DESCRIPTION", "TARGET_DESCRIPTION", "DESCRIPTION", "DEFINITION"],
        "DQ_RULE": ["DATA_QUALITY_RULE_DESCRIPTION", "DQ_RULE", "DQ_DESCRIPTION", "VALIDATION_RULE"]
    }

    for key, patterns in targets.items():
        matched = False
        for pattern in patterns:
            if pattern in header_map:
                guessed_mapping[key] = header_map[pattern]
                matched = True
                break
        
        if not matched:
            best_match = None
            highest_priority_idx = 999
            for norm_h, original in header_map.items():
                for idx, pattern in enumerate(patterns):
                    if len(pattern) > 3 and pattern in norm_h:
                        if idx < highest_priority_idx:
                            highest_priority_idx = idx
                            best_match = original
            guessed_mapping[key] = best_match

    return guessed_mapping

def guess_columns_with_ai(uploaded_headers):
    if client is None:
        return None

    prompt = f"""
    Map these custom CSV headers to standard functional keys:
    Headers: {list(uploaded_headers)}

    Keys:
    1.SOURCE_TABLE, 2.SOURCE_COLUMN, 3.TARGET_TABLE, 4.TARGET_COLUMN, 5.DATA_TYPE, 6.LENGTH, 7.PRECISION, 8.SCALE, 9.NULLABLE, 10.TRANSFORMATION_RULE, 11.BUSINESS_DEFINITION, 12.DQ_RULE

    Rules:
    - Prioritize 'PHYSICAL' column variations over logical names.
    - Return ONLY minimal JSON matching keys to input headers. Keep output short.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=80
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return None

def safe_value(row, col, default=""):
    if col and col in row and pd.notna(row[col]):
        return str(row[col]).strip()
    return default

def build_snowflake_type(row, mapping):
    dtype = safe_value(row, mapping.get("DATA_TYPE"), "VARCHAR").upper()
    length = safe_value(row, mapping.get("LENGTH"), "")
    precision = safe_value(row, mapping.get("PRECISION"), "")
    scale = safe_value(row, mapping.get("SCALE"), "")

    if any(x in dtype for x in ["VARCHAR", "STRING", "TEXT", "CHAR"]):
        return f"VARCHAR({length})" if length.isdigit() and length != "0" else "VARCHAR"
    if any(x in dtype for x in ["NUMBER", "DECIMAL", "NUMERIC", "INT"]):
        if precision.isdigit() and scale.isdigit() and precision != "0":
            return f"NUMBER({precision},{scale})"
        return "NUMBER"
    return dtype

# --------------------------------------------------
# APPLICATION RUNTIME
# --------------------------------------------------
uploaded_file = st.file_uploader("Upload STTM CSV", type=["csv"])

if uploaded_file:
    try:
        # Strict parsing controls to safeguard 100-column formatting layouts
        df = pd.read_csv(
            uploaded_file, 
            sep=',', 
            quotechar='"', 
            doublequote=True, 
            skipinitialspace=True,
            encoding='utf-8'
        )
        raw_headers = df.columns.tolist()
        
        st.success(f"STTM successfully read: {len(df):,} rows across {len(raw_headers)} metadata dimensions.")

        # Execute Mapping Pipeline
        with st.spinner("Analyzing schema properties..."):
            final_mapping = guess_columns_heuristically(raw_headers)
            
            critical_keys = ["SOURCE_TABLE", "SOURCE_COLUMN", "TARGET_TABLE", "TARGET_COLUMN", "DATA_TYPE"]
            missing_critical = any(final_mapping.get(k) is None for k in critical_keys)

            if missing_critical and client is not None:
                ai_mapping = guess_columns_with_ai(raw_headers)
                if ai_mapping:
                    for k, v in ai_mapping.items():
                        if not final_mapping.get(k):
                            final_mapping[k] = v

        st.subheader("📊 Dynamic Schema Mapping Resolution")
        st.json(final_mapping)

        if not final_mapping.get("TARGET_TABLE") or not final_mapping.get("TARGET_COLUMN"):
            st.error("Engine Stop: Target Table or Target Column schemas could not be deduced dynamically.")
            st.stop()

        target_table_name = safe_value(df.iloc[0], final_mapping["TARGET_TABLE"], "TARGET_TABLE_OUT")
        source_table_name = safe_value(df.iloc[0], final_mapping["SOURCE_TABLE"], "SOURCE_TABLE_IN")

        # Compile Code Artifacts
        ddl_lines = []
        sql_lines = []

        for _, row in df.iterrows():
            tgt_col = safe_value(row, final_mapping["TARGET_COLUMN"])
            src_col = safe_value(row, final_mapping["SOURCE_COLUMN"], tgt_col)
            
            if not tgt_col:
                continue

            col_type = build_snowflake_type(row, final_mapping)
            null_val = safe_value(row, final_mapping.get("NULLABLE")).upper()
            is_nullable = "NOT NULL" if null_val in ["N", "NO", "FALSE", "0"] else ""
            
            ddl_lines.append(f"  {tgt_col} {col_type} {is_nullable}".strip())

            logic = safe_value(row, final_mapping.get("TRANSFORMATION_RULE"))
            if logic and logic.upper() != "NONE":
                sql_lines.append(f"  /* Rule: {logic} */\n  {src_col} AS {tgt_col}")
            else:
                sql_lines.append(f"  {src_col} AS {tgt_col}")

        ddl_out = f"CREATE OR REPLACE TABLE {target_table_name} (\n" + ",\n".join(ddl_lines) + "\n);"
        sql_out = f"INSERT INTO {target_table_name}\nSELECT\n" + ",\n".join(sql_lines) + f"\nFROM {source_table_name};"

        # Output UI Layout
        tab1, tab2, tab3 = st.tabs(["❄️ Snowflake DDL", "🔁 Data Flow SQL", "🔍 Parsed File View"])
        with tab1:
            st.code(ddl_out, language="sql")
        with tab2:
            st.code(sql_out, language="sql")
        with tab3:
            st.dataframe(df.head(100), use_container_width=True)

    except Exception as e:
        st.error(f"Execution Error processing STTM payload: {str(e)}")