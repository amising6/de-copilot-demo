import streamlit as st
import pandas as pd
from openai import OpenAI

st.set_page_config(
page_title="DE Copilot",
page_icon="⚙️",
layout="wide"
)

# --------------------------------------------------
# OPENAI CLIENT
# --------------------------------------------------

client = None

try:
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
client = None

# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("⚙️ DE Copilot")

st.markdown("""
### Enterprise STTM Factory

Upload an STTM and automatically generate:

✅ Snowflake DDL
✅ Snowflake SQL
✅ Data Dictionary
✅ Technical Specifications
✅ Data Quality Rules
✅ AI Analysis
""")

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def normalize_columns(df):
df = df.copy()
df.columns = (
df.columns
.str.strip()
.str.replace(" ", "_", regex=False)
.str.replace("-", "_", regex=False)
.str.replace("/", "_", regex=False)
.str.upper()
)
return df


def find_column(df, aliases):
for alias in aliases:
alias = alias.upper()
if alias in df.columns:
return alias
return None


def safe_value(row, col, default=""):
if col and col in row and pd.notna(row[col]):
return str(row[col]).strip()
return default


def safe_table_name(value, default_name):
if value and str(value).strip():
return str(value).strip()
return default_name


def build_snowflake_type(row, datatype_col, length_col, precision_col, scale_col):
dtype = safe_value(row, datatype_col, "VARCHAR").upper()

length = safe_value(row, length_col, "")
precision = safe_value(row, precision_col, "")
scale = safe_value(row, scale_col, "")

if dtype in ["VARCHAR", "VARCHAR2", "CHAR", "STRING", "TEXT"]:
if length and length not in ["0", "N/A", "NA"]:
return f"VARCHAR({length})"
return "VARCHAR"

if dtype in ["NUMBER", "NUMERIC", "DECIMAL"]:
if precision and scale and precision not in ["0", "N/A", "NA"]:
return f"NUMBER({precision},{scale})"
if precision and precision not in ["0", "N/A", "NA"]:
return f"NUMBER({precision})"
return "NUMBER"

if dtype in ["DATE"]:
return "DATE"

if dtype in ["TIMESTAMP", "TIMESTAMP_NTZ", "DATETIME"]:
return "TIMESTAMP_NTZ"

if dtype in ["BOOLEAN", "BOOL"]:
return "BOOLEAN"

return dtype


def generate_ai_analysis(df):
if client is None:
return "OpenAI API key is not configured. Please add OPENAI_API_KEY in Streamlit Secrets."

sample_data = df.head(100).to_csv(index=False)

prompt = f"""
You are a Senior Data Architect.

Analyze this STTM metadata.

Provide:

1. Executive Summary
2. Business Purpose
3. Source & Target Analysis
4. Primary Key Recommendations
5. Data Quality Recommendations
6. Suggested Test Cases
7. Risks
8. Improvement Opportunities

STTM sample:

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
temperature=0.2
)

return response.choices[0].message.content


# --------------------------------------------------
# COLUMN ALIASES
# --------------------------------------------------

COLUMN_ALIASES = {
"SOURCE_TABLE": [
"SOURCE_TABLE",
"SOURCE_TABLE_NAME",
"SOURCE_TABLE_VIEW",
"SOURCE_TABLE_PHYSICAL_NAME",
"SRC_TABLE",
"SRC_TABLE_NAME",
"SOURCE_ENTITY"
],
"SOURCE_COLUMN": [
"SOURCE_COLUMN",
"SOURCE_COLUMN_NAME",
"SOURCE_COLUMN_PHYSICAL_NAME",
"SRC_COLUMN",
"SRC_COLUMN_NAME",
"SOURCE_FIELD"
],
"TARGET_TABLE": [
"TARGET_TABLE",
"TARGET_TABLE_NAME",
"TARGET_TABLE_PHYSICAL_NAME",
"TARGET_TABLE_LOGICAL_NAME",
"TGT_TABLE",
"TGT_TABLE_NAME",
"DESTINATION_TABLE"
],
"TARGET_COLUMN": [
"TARGET_COLUMN",
"TARGET_COLUMN_NAME",
"TARGET_COLUMN_PHYSICAL_NAME",
"TGT_COLUMN",
"TGT_COLUMN_NAME",
"TARGET_FIELD"
],
"DATA_TYPE": [
"DATA_TYPE",
"TARGET_DATA_TYPE",
"TARGET_DATATYPE",
"TGT_DATA_TYPE",
"DATATYPE"
],
"LENGTH": [
"LENGTH",
"TARGET_LENGTH",
"TARGET_COLUMN_LENGTH"
],
"PRECISION": [
"PRECISION",
"TARGET_PRECISION"
],
"SCALE": [
"SCALE",
"TARGET_SCALE"
],
"NULLABLE": [
"NULLABLE",
"TARGET_IS_NULLABLE",
"IS_NULLABLE",
"TARGET_NULLABLE"
],
"BUSINESS_DEFINITION": [
"BUSINESS_DEFINITION",
"SOURCE_DESCRIPTION",
"TARGET_DESCRIPTION",
"COLUMN_DESCRIPTION",
"DESCRIPTION",
"BUSINESS_RULE_DESCRIPTION"
],
"TRANSFORMATION_RULE": [
"TRANSFORMATION_RULE",
"TRANSFORMATION_LOGIC",
"BUSINESS_RULE_DESCRIPTION",
"RULE",
"LOGIC"
],
"DQ_RULE": [
"DQ_RULE",
"DATA_QUALITY_RULE",
"DATA_QUALITY_RULE_DESCRIPTION",
"VALIDATION_RULE",
"DQ_DESCRIPTION"
]
}

# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------

uploaded_file = st.file_uploader(
"Upload STTM CSV",
type=["csv"]
)

if uploaded_file:

try:
raw_df = pd.read_csv(uploaded_file)
df = normalize_columns(raw_df)

st.success("STTM Uploaded Successfully")

st.subheader("Uploaded STTM Preview")
st.dataframe(df.head(200), use_container_width=True)

st.caption(f"Rows uploaded: {len(df):,} | Columns detected: {len(df.columns):,}")

# --------------------------------------------------
# AUTO DETECT COLUMNS
# --------------------------------------------------

source_table_col = find_column(df, COLUMN_ALIASES["SOURCE_TABLE"])
source_column_col = find_column(df, COLUMN_ALIASES["SOURCE_COLUMN"])
target_table_col = find_column(df, COLUMN_ALIASES["TARGET_TABLE"])
target_column_col = find_column(df, COLUMN_ALIASES["TARGET_COLUMN"])
datatype_col = find_column(df, COLUMN_ALIASES["DATA_TYPE"])
length_col = find_column(df, COLUMN_ALIASES["LENGTH"])
precision_col = find_column(df, COLUMN_ALIASES["PRECISION"])
scale_col = find_column(df, COLUMN_ALIASES["SCALE"])
nullable_col = find_column(df, COLUMN_ALIASES["NULLABLE"])
business_col = find_column(df, COLUMN_ALIASES["BUSINESS_DEFINITION"])
transform_col = find_column(df, COLUMN_ALIASES["TRANSFORMATION_RULE"])
dq_col = find_column(df, COLUMN_ALIASES["DQ_RULE"])

st.subheader("Detected STTM Structure")

detected_df = pd.DataFrame(
[
["Source Table", source_table_col],
["Source Column", source_column_col],
["Target Table", target_table_col],
["Target Column", target_column_col],
["Data Type", datatype_col],
["Length", length_col],
["Precision", precision_col],
["Scale", scale_col],
["Nullable", nullable_col],
["Business Definition", business_col],
["Transformation Rule", transform_col],
["DQ Rule", dq_col],
],
columns=["Logical Field", "Detected Column"]
)

st.dataframe(detected_df, use_container_width=True)

required_missing = []

if not target_table_col:
required_missing.append("Target Table")

if not target_column_col:
required_missing.append("Target Column")

if not datatype_col:
required_missing.append("Data Type")

if required_missing:
st.error(
"Unable to generate artifacts because required STTM fields were not detected: "
+ ", ".join(required_missing)
)

st.write("Available columns in uploaded file:")
st.write(df.columns.tolist())

st.stop()

# --------------------------------------------------
# TABLE NAMES
# --------------------------------------------------

target_table = safe_table_name(
df[target_table_col].dropna().iloc[0]
if target_table_col and not df[target_table_col].dropna().empty
else "",
"TARGET_TABLE"
)

source_table = safe_table_name(
df[source_table_col].dropna().iloc[0]
if source_table_col and not df[source_table_col].dropna().empty
else "",
"SOURCE_TABLE"
)

# --------------------------------------------------
# DDL GENERATION
# --------------------------------------------------

ddl_columns = []

for _, row in df.iterrows():

target_column = safe_value(row, target_column_col)

if not target_column:
continue

data_type = build_snowflake_type(
row,
datatype_col,
length_col,
precision_col,
scale_col
)

nullable = ""

if nullable_col:
nullable_value = safe_value(row, nullable_col).upper()

if nullable_value in ["N", "NO", "FALSE", "0"]:
nullable = "NOT NULL"

ddl_columns.append(
f" {target_column} {data_type} {nullable}".rstrip()
)

ddl = f"""CREATE OR REPLACE TABLE {target_table}
(
{",\n".join(ddl_columns)}
);
"""

# --------------------------------------------------
# SQL GENERATION
# --------------------------------------------------

sql_lines = []

for _, row in df.iterrows():

target_column = safe_value(row, target_column_col)

if not target_column:
continue

source_column = safe_value(row, source_column_col, target_column)

transformation = safe_value(row, transform_col)

if transformation and transformation.upper() not in ["N/A", "NA", "NONE"]:
sql_lines.append(
f" /* {transformation} */\n {source_column} AS {target_column}"
)
else:
sql_lines.append(
f" {source_column} AS {target_column}"
)

sql = f"""INSERT INTO {target_table}
SELECT
{",\n".join(sql_lines)}
FROM {source_table};
"""

# --------------------------------------------------
# DATA DICTIONARY
# --------------------------------------------------

dictionary_data = []

for _, row in df.iterrows():

dictionary_data.append(
{
"Target_Table": safe_value(row, target_table_col),
"Target_Column": safe_value(row, target_column_col),
"Data_Type": build_snowflake_type(
row,
datatype_col,
length_col,
precision_col,
scale_col
),
"Nullable": safe_value(row, nullable_col),
"Business_Definition": safe_value(row, business_col)
}
)

dictionary_df = pd.DataFrame(dictionary_data)

# --------------------------------------------------
# TECHNICAL SPEC
# --------------------------------------------------

tech_spec_data = []

for _, row in df.iterrows():

tech_spec_data.append(
{
"Source_Table": safe_value(row, source_table_col),
"Source_Column": safe_value(row, source_column_col),
"Target_Table": safe_value(row, target_table_col),
"Target_Column": safe_value(row, target_column_col),
"Data_Type": build_snowflake_type(
row,
datatype_col,
length_col,
precision_col,
scale_col
),
"Transformation_Rule": safe_value(row, transform_col),
"DQ_Rule": safe_value(row, dq_col),
"Business_Definition": safe_value(row, business_col)
}
)

tech_spec_df = pd.DataFrame(tech_spec_data)

# --------------------------------------------------
# DQ RULES
# --------------------------------------------------

dq_data = []

for _, row in df.iterrows():

target_column = safe_value(row, target_column_col)
nullable_value = safe_value(row, nullable_col).upper()
dq_rule = safe_value(row, dq_col)

generated_rule = ""

if nullable_value in ["N", "NO", "FALSE", "0"]:
generated_rule = f"{target_column} must not be null"

if dq_rule:
if generated_rule:
generated_rule += f"; {dq_rule}"
else:
generated_rule = dq_rule

dq_data.append(
{
"Target_Table": safe_value(row, target_table_col),
"Target_Column": target_column,
"DQ_Rule": generated_rule
}
)

dq_df = pd.DataFrame(dq_data)

# --------------------------------------------------
# TABS
# --------------------------------------------------

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
[
"Snowflake DDL",
"Snowflake SQL",
"Data Dictionary",
"Technical Spec",
"DQ Rules",
"🤖 AI Analysis"
]
)

with tab1:
st.code(ddl, language="sql")

st.download_button(
"Download DDL",
ddl,
file_name="snowflake_ddl.sql",
mime="text/plain"
)

with tab2:
st.code(sql, language="sql")

st.download_button(
"Download SQL",
sql,
file_name="snowflake_sql.sql",
mime="text/plain"
)

with tab3:
st.dataframe(dictionary_df, use_container_width=True)

st.download_button(
"Download Data Dictionary",
dictionary_df.to_csv(index=False),
file_name="data_dictionary.csv",
mime="text/csv"
)

with tab4:
st.dataframe(tech_spec_df, use_container_width=True)

st.download_button(
"Download Technical Spec",
tech_spec_df.to_csv(index=False),
file_name="technical_spec.csv",
mime="text/csv"
)

with tab5:
st.dataframe(dq_df, use_container_width=True)

st.download_button(
"Download DQ Rules",
dq_df.to_csv(index=False),
file_name="dq_rules.csv",
mime="text/csv"
)

with tab6:
st.subheader("AI STTM Analysis")

st.info("AI analysis uses the first 100 rows only to control cost and improve speed.")

if st.button("Generate AI Insights"):

with st.spinner("Analyzing STTM using AI..."):

ai_response = generate_ai_analysis(df)

st.markdown(ai_response)

st.download_button(
"Download AI Analysis",
ai_response,
file_name="ai_analysis.txt",
mime="text/plain"
)

except Exception as e:
st.error("The STTM could not be processed.")
st.write("Error details:")
st.exception(e)

else:
st.info("Upload a CSV STTM file to get started.")