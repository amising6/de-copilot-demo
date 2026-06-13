# app.py

import streamlit as st
import pandas as pd
from openai import OpenAI

st.set_page_config(
    page_title="DE Copilot",
    page_icon="⚙️",
    layout="wide"
)

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

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
# AI FUNCTION
# --------------------------------------------------

def generate_ai_analysis(df):

    sample_data = df.to_csv(index=False)

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

STTM:

{sample_data}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content

# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload STTM CSV",
    type=["csv"]
)

if uploaded_file:

    df = pd.read_csv(uploaded_file)

    st.success("STTM Uploaded Successfully")

    st.subheader("Uploaded STTM")

    st.dataframe(df)

    target_table = df["Target_Table"].iloc[0]
    source_table = df["Source_Table"].iloc[0]

    # --------------------------------------------------
    # DDL GENERATION
    # --------------------------------------------------

    ddl_columns = []

    for _, row in df.iterrows():

        nullable = ""

        if str(row["Nullable"]).upper() == "N":
            nullable = "NOT NULL"

        ddl_columns.append(
            f"{row['Target_Column']} {row['Data_Type']} {nullable}"
        )

    ddl = f"""
CREATE OR REPLACE TABLE {target_table}
(
{', '.join(ddl_columns)}
);
"""

    # --------------------------------------------------
    # SQL GENERATION
    # --------------------------------------------------

    sql_lines = []

    for _, row in df.iterrows():

        sql_lines.append(
            f"{row['Source_Column']} AS {row['Target_Column']}"
        )

    sql = f"""
INSERT INTO {target_table}

SELECT

{', '.join(sql_lines)}

FROM {source_table};
"""

    # --------------------------------------------------
    # DATA DICTIONARY
    # --------------------------------------------------

    dictionary_df = df[
        [
            "Target_Column",
            "Data_Type",
            "Business_Definition"
        ]
    ]

    # --------------------------------------------------
    # TECH SPEC
    # --------------------------------------------------

    tech_spec_df = df.copy()

    # --------------------------------------------------
    # DQ RULES
    # --------------------------------------------------

    dq_df = df[
        [
            "Target_Column",
            "DQ_Rule"
        ]
    ]

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

    # --------------------------------------------------
    # TAB 1
    # --------------------------------------------------

    with tab1:

        st.code(ddl, language="sql")

        st.download_button(
            "Download DDL",
            ddl,
            file_name="snowflake_ddl.sql"
        )

    # --------------------------------------------------
    # TAB 2
    # --------------------------------------------------

    with tab2:

        st.code(sql, language="sql")

        st.download_button(
            "Download SQL",
            sql,
            file_name="snowflake_sql.sql"
        )

    # --------------------------------------------------
    # TAB 3
    # --------------------------------------------------

    with tab3:

        st.dataframe(dictionary_df)

        st.download_button(
            "Download Data Dictionary",
            dictionary_df.to_csv(index=False),
            file_name="data_dictionary.csv"
        )

    # --------------------------------------------------
    # TAB 4
    # --------------------------------------------------

    with tab4:

        st.dataframe(tech_spec_df)

        st.download_button(
            "Download Technical Spec",
            tech_spec_df.to_csv(index=False),
            file_name="technical_spec.csv"
        )

    # --------------------------------------------------
    # TAB 5
    # --------------------------------------------------

    with tab5:

        st.dataframe(dq_df)

        st.download_button(
            "Download DQ Rules",
            dq_df.to_csv(index=False),
            file_name="dq_rules.csv"
        )

    # --------------------------------------------------
    # TAB 6
    # --------------------------------------------------

    with tab6:

        st.subheader("AI STTM Analysis")

        if st.button("Generate AI Insights"):

            with st.spinner("Analyzing STTM..."):

                ai_response = generate_ai_analysis(df)

                st.markdown(ai_response)

                st.download_button(
                    "Download AI Analysis",
                    ai_response,
                    file_name="ai_analysis.txt"
                )
