import streamlit as st
import pandas as pd
import json
from openai import OpenAI

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="DE Copilot",
    page_icon="🚀",
    layout="wide"
)

# --------------------------------------------------
# OPENAI CLIENT
# --------------------------------------------------
client = None
try:
    if "OPENAI_API_KEY" in st.secrets:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    client = None

st.title("🚀 Dynamic DE Copilot")

st.markdown("""
### Zero-Hardcoding Enterprise STTM Factory
This engine uses a **Ranked Heuristics Scoring Engine + Budget-Capped LLM Semantic Mapping Pipeline** to dynamically parse *any* vendor layout accurately.
""")

# --------------------------------------------------
# PHASE 1: RANKED HEURISTIC PARSING ENGINE
# --------------------------------------------------
def normalize_string(s):
    return str(s).strip().upper().replace(" ", "_").replace("-", "_").replace("/", "_")

def guess_columns_heuristically(uploaded_headers):
    """
    Ranks headers based on engineering weight parameters to prevent 
    false positives (e.g., matching a logical View or ID over a Physical column name).
    """
    guessed_mapping = {}
    normalized_headers = [normalize_string(h) for h in uploaded_headers]
    header_map = dict(zip(normalized_headers, uploaded_headers))

    # Priority ranking structures: First items in list are heavily preferred
    targets = {
        "SOURCE_TABLE": ["SRC_TABLE_PHYSICAL_NAME", "SOURCE_TABLE_PHYSICAL_NAME", "SOURCE_TABLE_PHYSICAL", "SRC_PHYS_NAME", "SRC_TBL", "SRC_TABLE", "SOURCE_TABLE", "SOURCE_TABLE_VIEW", "SOURCE_ENTITY"],
        "SOURCE_COLUMN": ["SRC_COLUMN_PHYSICAL_NAME", "SOURCE_COLUMN_PHYSICAL_NAME", "SOURCE_COLUMN_PHYSICAL", "SRC_COL_PHYS", "SRC_COL", "SRC_COLUMN", "SOURCE_COLUMN", "SOURCE_FIELD"],
        "TARGET_TABLE": ["TGT_TABLE_PHYSICAL_NAME", "TARGET_TABLE_PHYSICAL_NAME", "TARGET_TABLE_PHYSICAL", "TGT_PHYS_NAME", "TARGET_TABLE_LOGICAL_NAME", "TGT_TBL", "TARGET_TABLE", "TARGET_ENTITY", "DESTINATION_TABLE"],
        "TARGET_COLUMN": ["TGT_COLUMN_PHYSICAL_NAME", "TARGET_COLUMN_PHYSICAL_NAME", "TARGET_COLUMN_PHYSICAL", "TGT_COL_PHYS", "TARGET_COLUMN_NAME", "TGT_COL", "TARGET_COLUMN", "TARGET_FIELD", "DESTINATION_COLUMN"],
        "DATA_TYPE": ["TARGET_DATA_TYPE", "TGT_DATA_TYPE", "DATA_TYPE", "DATATYPE", "TYPE"],
        "LENGTH": ["TARGET_LENGTH", "TGT_LENGTH", "LENGTH", "SIZE", "MAX_LEN"],
        "PRECISION": ["TARGET_PRECISION", "TGT_PRECISION", "PRECISION", "NUMERIC_PRECISION"],
        "SCALE": ["TARGET_SCALE", "TGT_SCALE", "SCALE", "NUMERIC_SCALE"],
        "NULLABLE": ["TARGET_IS_NULLABLE", "IS_NULLABLE", "NULLABLE", "NULL_INDICATOR"],
        "TRANSFORMATION_RULE": ["TRANSFORMATION_LOGIC", "TRANSFORMATION", "LOGIC", "BUSINESS_RULE"],
        "BUSINESS_DEFINITION": ["SOURCE_DESCRIPTION", "TARGET_DESCRIPTION", "DESCRIPTION", "DEFINITION", "BUSINESS_DEFINITION"],
        "DQ_RULE": ["DATA_QUALITY_RULE_DESCRIPTION", "DQ_RULE", "DQ_DESCRIPTION", "DATA_QUALITY", "VALIDATION_RULE"]
    }

    for key, patterns in targets.items():
        matched = False
        
        # Pass 1: Look for highly weighted exact pattern matches
        for pattern in patterns:
            if pattern in header_map:
                guessed_mapping[key] = header_map[pattern]
                matched = True
                break
        
        # Pass 2: Fall back to substring matching only if absolute targets fail
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

# --------------------------------------------------
# PHASE 2: BUDGET-GUARDED LLM SEMANTIC MAPPING
# --------------------------------------------------
def guess_columns_with_ai(uploaded_headers):
    if client is None:
        return None

    prompt = f"""
    Map these custom CSV headers to standard functional keys:
    Headers: {list(uploaded_headers)}

    Keys:
    1.SOURCE_TABLE, 2.SOURCE_COLUMN, 3.TARGET_TABLE, 4.TARGET_COLUMN, 5.DATA_TYPE, 6.LENGTH, 7.PRECISION, 8.SCALE, 9.NULLABLE, 10.TRANSFORMATION_RULE, 11.BUSINESS_DEFINITION, 12.DQ_RULE

    Rules:
    - Prioritize 'PHYSICAL' column variations over logical descriptive attributes or structural ID keys.
    - If missing, map to null.
    - Return ONLY minimal JSON matching keys directly to input headers. Keep output extremely short.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=80  # Budget protection ceiling
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return None

# --------------------------------------------------
# RUNTIME ENGINE
# --------------------------------------------------
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

# File Loader Interface
uploaded_file = st.file_uploader("Upload Any Vendor/Custom STTM File", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        raw_headers = df.columns.tolist()
        
        st.success(f"File uploaded. Processing {len(df):,} items across {len(raw_headers)} dimensions.")

        with st.spinner("Resolving schema dimensions dynamically..."):
            final_mapping = guess_columns_heuristically(raw_headers)
            
            critical_keys = ["SOURCE_TABLE", "SOURCE_COLUMN", "TARGET_TABLE", "TARGET_COLUMN", "DATA_TYPE"]
            missing_critical = any(final_mapping.get(k) is None for k in critical_keys)

            if missing_critical and client is not None:
                ai_mapping = guess_columns_with_ai(raw_headers)
                if ai_mapping:
                    for k, v in ai_mapping.items():
                        if not final_mapping.get(k):
                            final_mapping[k] = v

        st.subheader("📊 Programmatic Schema Identification Output")
        st.json(final_mapping)

        if not final_mapping.get("TARGET_TABLE") or not final_mapping.get("TARGET_COLUMN"):
            st.error("Engine Stop: Target Table or Target Column schemas could not be deduced dynamically.")
            st.stop()

        target_table_name = safe_value(df.iloc[0], final_mapping["TARGET_TABLE"], "TARGET_TABLE_OUT")
        source_table_name = safe_value(df.iloc[0], final_mapping["SOURCE_TABLE"], "SOURCE_TABLE_IN")

        # --------------------------------------------------
        # GENERATION ARTIFACT ENGINE LOOPS
        # --------------------------------------------------
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

        # Present Outputs
        tab1, tab2, tab3 = st.tabs(["❄️ Snowflake DDL", "🔁 Data Flow SQL", "🔍 Parsed STTM Data"])
        with tab1:
            st.code(ddl_out, language="sql")
        with tab2:
            st.code(sql_out, language="sql")
        with tab3:
            st.dataframe(df.head(100))

    except Exception as e:
        st.error(f"Execution Error processing STTM payload: {str(e)}")