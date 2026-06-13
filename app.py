import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="DE Copilot",
    page_icon="⚙️",
    layout="wide"
)

# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("⚙️ DE Copilot")

st.markdown(
    "[🌐 DataEngineeringCopilot.com](https://dataengineeringcopilot.com)"
)

st.markdown(
    "[💻 GitHub Repository](https://github.com/amising6/de-copilot-demo)"
)

st.markdown("""
### Enterprise STTM Factory

Upload an STTM and automatically generate:

✅ Snowflake DDL

✅ Snowflake SQL

✅ Data Dictionary

✅ Technical Specifications

✅ Data Quality Rules
""")

# --------------------------------------------------
# Upload File
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload STTM CSV",
    type=["csv"]
)

# --------------------------------------------------
# Process File
# --------------------------------------------------

if uploaded_file:

    try:

        df = pd.read_csv(uploaded_file)

        st.success("STTM Uploaded Successfully")

        st.subheader("Uploaded STTM")

        st.dataframe(df)

        # ------------------------------------------
        # Target Table
        # ------------------------------------------

        target_table = df["Target_Table"].iloc[0]

        # ------------------------------------------
        # Generate DDL
        # ------------------------------------------

        ddl = f"CREATE OR REPLACE TABLE {target_table} (\n"

        ddl_columns = []

        for _, row in df.iterrows():

            nullable = ""

            if str(row["Nullable"]).upper() == "N":
                nullable = "NOT NULL"

            ddl_columns.append(
                f"{row['Target_Column']} {row['Data_Type']} {nullable}"
            )

        ddl += ",\n".join(ddl_columns)

        ddl += "\n);"

        # ------------------------------------------
        # Generate SQL
        # ------------------------------------------

        sql_lines = []

        for _, row in df.iterrows():

            sql_lines.append(
                f"{row['Source_Column']} AS {row['Target_Column']}"
            )

        sql = f"""
INSERT INTO {target_table}

SELECT

{', '.join(sql_lines)}

FROM {df['Source_Table'].iloc[0]};
"""

        # ------------------------------------------
        # Data Dictionary
        # ------------------------------------------

        dictionary_df = df[
            [
                "Target_Column",
                "Data_Type",
                "Business_Definition"
            ]
        ]

        # ------------------------------------------
        # DQ Rules
        # ------------------------------------------

        dq_df = df[
            [
                "Target_Column",
                "DQ_Rule"
            ]
        ]

        # ------------------------------------------
        # Tabs
        # ------------------------------------------

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Snowflake DDL",
            "Snowflake SQL",
            "Data Dictionary",
            "Technical Spec",
            "DQ Rules"
        ])

        # ------------------------------------------
        # DDL TAB
        # ------------------------------------------

        with tab1:

            st.code(ddl, language="sql")

            st.download_button(
                "📥 Download DDL",
                ddl,
                file_name="snowflake_ddl.sql",
                mime="text/plain"
            )

        # ------------------------------------------
        # SQL TAB
        # ------------------------------------------

        with tab2:

            st.code(sql, language="sql")

            st.download_button(
                "📥 Download SQL",
                sql,
                file_name="snowflake_sql.sql",
                mime="text/plain"
            )

        # ------------------------------------------
        # DATA DICTIONARY TAB
        # ------------------------------------------

        with tab3:

            st.dataframe(dictionary_df)

            st.download_button(
                "📥 Download Data Dictionary",
                dictionary_df.to_csv(index=False),
                file_name="data_dictionary.csv",
                mime="text/csv"
            )

        # ------------------------------------------
        # TECHNICAL SPEC TAB
        # ------------------------------------------

        with tab4:

            st.dataframe(df)

            st.download_button(
                "📥 Download Technical Spec",
                df.to_csv(index=False),
                file_name="technical_spec.csv",
                mime="text/csv"
            )

        # ------------------------------------------
        # DQ RULES TAB
        # ------------------------------------------

        with tab5:

            st.dataframe(dq_df)

            st.download_button(
                "📥 Download DQ Rules",
                dq_df.to_csv(index=False),
                file_name="dq_rules.csv",
                mime="text/csv"
            )

    except Exception as e:

        st.error(f"Error processing file: {e}")

else:

    st.info("Upload a sample STTM CSV to get started.")