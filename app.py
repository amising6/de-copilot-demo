import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="DE Copilot",
    page_icon="⚙️",
    layout="wide"
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
""")

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

    ddl = f"CREATE OR REPLACE TABLE {target_table} (\n"

    cols = []

    for _, row in df.iterrows():

        nullable = ""

        if row["Nullable"] == "N":
            nullable = "NOT NULL"

        cols.append(
            f"{row['Target_Column']} {row['Data_Type']} {nullable}"
        )

    ddl += ",\n".join(cols)

    ddl += "\n);"

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Snowflake DDL",
        "Snowflake SQL",
        "Data Dictionary",
        "Technical Spec",
        "DQ Rules"
    ])

    with tab1:

        st.code(ddl, language="sql")

    with tab2:

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

        st.code(sql, language="sql")

    with tab3:

        st.dataframe(
            df[
                [
                    "Target_Column",
                    "Data_Type",
                    "Business_Definition"
                ]
            ]
        )

    with tab4:

        st.dataframe(df)

    with tab5:

        st.dataframe(
            df[
                [
                    "Target_Column",
                    "DQ_Rule"
                ]
            ]
        )