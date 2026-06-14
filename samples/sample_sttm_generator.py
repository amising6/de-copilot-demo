# generate_sample_sttm.py

import csv
import random

output_file = "sample_enterprise_sttm_100_columns.csv"

headers = [
    "Mapping_ID",
    "Project_Name",
    "Subject_Area",
    "Source_System",
    "Source_Database",
    "Source_Schema",
    "Source_Table",
    "Source_Column",
    "Source_Data_Type",
    "Source_Length",
    "Source_Nullable",
    "Source_PK",
    "Source_FK",
    "Business_Rule_ID",
    "Business_Rule_Name",
    "Business_Definition",
    "Transformation_Type",
    "Transformation_Logic",
    "Lookup_Table",
    "Lookup_Join_Condition",
    "Filter_Condition",
    "Target_System",
    "Target_Database",
    "Target_Schema",
    "Target_Table",
    "Target_Column",
    "Target_Data_Type",
    "Target_Length",
    "Target_Precision",
    "Target_Scale",
    "Target_Nullable",
    "Target_PK",
    "Target_FK",
    "DQ_Rule",
    "DQ_Severity",
    "DQ_Action",
    "SCD_Type",
    "Effective_Date_Column",
    "End_Date_Column",
    "Current_Flag_Column",
    "PII_Flag",
    "Data_Masking_Rule",
    "Owner",
    "Approval_Status",
    "Release",
    "Notes",
]

target_columns = [
    ("CUSTOMER_ID", "NUMBER", "18", "0", "N", "Y", "Unique customer identifier"),
    ("CUSTOMER_NUMBER", "VARCHAR", "50", "", "N", "N", "Business customer number"),
    ("FIRST_NAME", "VARCHAR", "100", "", "Y", "N", "Customer first name"),
    ("LAST_NAME", "VARCHAR", "100", "", "Y", "N", "Customer last name"),
    ("FULL_NAME", "VARCHAR", "250", "", "Y", "N", "Customer full name"),
    ("EMAIL_ADDRESS", "VARCHAR", "255", "", "Y", "N", "Customer email address"),
    ("PHONE_NUMBER", "VARCHAR", "30", "", "Y", "N", "Customer phone number"),
    ("DATE_OF_BIRTH", "DATE", "", "", "Y", "N", "Customer date of birth"),
    ("GENDER", "VARCHAR", "20", "", "Y", "N", "Customer gender"),
    ("MARITAL_STATUS", "VARCHAR", "30", "", "Y", "N", "Customer marital status"),
    ("CUSTOMER_SEGMENT", "VARCHAR", "50", "", "Y", "N", "Customer market segment"),
    ("CUSTOMER_STATUS", "VARCHAR", "30", "", "N", "N", "Customer active or inactive status"),
    ("ADDRESS_LINE_1", "VARCHAR", "255", "", "Y", "N", "Primary address line"),
    ("ADDRESS_LINE_2", "VARCHAR", "255", "", "Y", "N", "Secondary address line"),
    ("CITY", "VARCHAR", "100", "", "Y", "N", "Customer city"),
    ("STATE_CODE", "VARCHAR", "10", "", "Y", "N", "Customer state code"),
    ("ZIP_CODE", "VARCHAR", "20", "", "Y", "N", "Postal code"),
    ("COUNTRY_CODE", "VARCHAR", "10", "", "Y", "N", "Country code"),
    ("REGION", "VARCHAR", "50", "", "Y", "N", "Business region"),
    ("AGENT_ID", "NUMBER", "18", "0", "Y", "N", "Agent identifier"),
    ("AGENT_NAME", "VARCHAR", "200", "", "Y", "N", "Agent name"),
    ("BROKER_ID", "NUMBER", "18", "0", "Y", "N", "Broker identifier"),
    ("BROKER_NAME", "VARCHAR", "200", "", "Y", "N", "Broker name"),
    ("PRODUCT_ID", "NUMBER", "18", "0", "Y", "N", "Product identifier"),
    ("PRODUCT_NAME", "VARCHAR", "200", "", "Y", "N", "Product name"),
    ("POLICY_NUMBER", "VARCHAR", "50", "", "Y", "N", "Policy number"),
    ("POLICY_TYPE", "VARCHAR", "50", "", "Y", "N", "Policy type"),
    ("POLICY_STATUS", "VARCHAR", "30", "", "Y", "N", "Policy status"),
    ("POLICY_START_DATE", "DATE", "", "", "Y", "N", "Policy start date"),
    ("POLICY_END_DATE", "DATE", "", "", "Y", "N", "Policy end date"),
    ("RENEWAL_DATE", "DATE", "", "", "Y", "N", "Policy renewal date"),
    ("PREMIUM_AMOUNT", "NUMBER", "18", "2", "Y", "N", "Premium amount"),
    ("WRITTEN_PREMIUM", "NUMBER", "18", "2", "Y", "N", "Written premium"),
    ("EARNED_PREMIUM", "NUMBER", "18", "2", "Y", "N", "Earned premium"),
    ("CLAIM_COUNT", "NUMBER", "18", "0", "Y", "N", "Number of claims"),
    ("CLAIM_AMOUNT", "NUMBER", "18", "2", "Y", "N", "Total claim amount"),
    ("LOSS_RATIO", "NUMBER", "10", "4", "Y", "N", "Loss ratio"),
    ("UNDERWRITER_ID", "NUMBER", "18", "0", "Y", "N", "Underwriter identifier"),
    ("UNDERWRITER_NAME", "VARCHAR", "200", "", "Y", "N", "Underwriter name"),
    ("RISK_SCORE", "NUMBER", "10", "2", "Y", "N", "Calculated risk score"),
    ("CREDIT_SCORE", "NUMBER", "10", "0", "Y", "N", "Customer credit score"),
    ("CUSTOMER_TENURE_DAYS", "NUMBER", "18", "0", "Y", "N", "Customer tenure in days"),
    ("MARKETING_OPT_IN", "VARCHAR", "1", "", "Y", "N", "Marketing preference"),
    ("EMAIL_OPT_IN", "VARCHAR", "1", "", "Y", "N", "Email preference"),
    ("SMS_OPT_IN", "VARCHAR", "1", "", "Y", "N", "SMS preference"),
    ("CREATED_DATE", "TIMESTAMP_NTZ", "", "", "N", "N", "Record created timestamp"),
    ("UPDATED_DATE", "TIMESTAMP_NTZ", "", "", "Y", "N", "Record updated timestamp"),
    ("CURRENT_FLAG", "VARCHAR", "1", "", "N", "N", "Current row indicator"),
    ("EFFECTIVE_DATE", "DATE", "", "", "N", "N", "SCD effective date"),
    ("EXPIRY_DATE", "DATE", "", "", "Y", "N", "SCD expiry date"),
]

source_tables = ["SRC_CUSTOMER", "SRC_POLICY", "SRC_CLAIM", "SRC_AGENT", "SRC_PRODUCT"]
source_systems = ["CRM", "POLICY_ADMIN", "CLAIMS", "AGENCY", "PRODUCT_MASTER"]

transformation_templates = [
    "Direct Mapping",
    "TRIM({src_col})",
    "UPPER(TRIM({src_col}))",
    "LOWER(TRIM({src_col}))",
    "COALESCE({src_col}, 'UNKNOWN')",
    "ROUND({src_col}, 2)",
    "CAST({src_col} AS DATE)",
    "CASE WHEN {src_col} IS NULL THEN 'N' ELSE 'Y' END",
    "CASE WHEN {src_col} IN ('BOUND','ISSUED') THEN 'ACTIVE' ELSE 'INACTIVE' END",
    "CONCAT(FIRST_NAME, ' ', LAST_NAME)",
]

dq_templates = [
    "Must not be null",
    "Must be unique",
    "Must match approved reference values",
    "Must be greater than or equal to zero",
    "Must be valid date",
    "Must follow valid email format",
    "Length must not exceed target length",
    "Must pass datatype validation",
    "Must be valid active status",
    "Must exist in lookup table",
]

rows = []

# First 50 rows map to CUSTOMER_DIM
for i, (target_col, data_type, precision_or_length, scale, nullable, pk, definition) in enumerate(
    target_columns, start=1
):
    source_table = random.choice(source_tables)
    source_system = random.choice(source_systems)
    source_col = target_col if i % 5 != 0 else f"SRC_{target_col}"

    transformation = random.choice(transformation_templates).format(src_col=source_col)
    dq_rule = random.choice(dq_templates)

    row = [
        f"MAP_{i:04d}",
        "DE Copilot Insurance Data Product",
        "Customer 360",
        source_system,
        "SRC_DB",
        "PUBLIC",
        source_table,
        source_col,
        "VARCHAR" if data_type == "VARCHAR" else data_type,
        precision_or_length,
        nullable,
        "Y" if pk == "Y" else "N",
        "N",
        f"BR_{i:04d}",
        "Customer Data Standardization",
        definition,
        "Derived" if transformation != "Direct Mapping" else "Direct",
        transformation,
        "LKP_PRODUCT" if "PRODUCT" in target_col else "",
        "SRC.PRODUCT_ID = LKP.PRODUCT_ID" if "PRODUCT" in target_col else "",
        "WHERE ACTIVE_FLAG = 'Y'",
        "SNOWFLAKE",
        "ANALYTICS_DB",
        "CORE",
        "CUSTOMER_DIM",
        target_col,
        data_type,
        precision_or_length if data_type == "VARCHAR" else "",
        precision_or_length if data_type == "NUMBER" else "",
        scale if data_type == "NUMBER" else "",
        nullable,
        pk,
        "N",
        dq_rule,
        "HIGH" if nullable == "N" else "MEDIUM",
        "Reject Row" if nullable == "N" else "Flag Record",
        "SCD2" if target_col in ["CURRENT_FLAG", "EFFECTIVE_DATE", "EXPIRY_DATE"] else "SCD1",
        "EFFECTIVE_DATE",
        "EXPIRY_DATE",
        "CURRENT_FLAG",
        "Y" if target_col in ["EMAIL_ADDRESS", "PHONE_NUMBER", "DATE_OF_BIRTH"] else "N",
        "MASK_EMAIL" if target_col == "EMAIL_ADDRESS" else "",
        "Data Engineering Team",
        "Approved",
        "Release 1.0",
        f"Mapping generated for {target_col}",
    ]

    rows.append(row)

# Add 50 more rows for other domains to make 100 rows
extra_targets = []
for i in range(51, 101):
    extra_targets.append(
        (
            f"METRIC_{i}",
            "NUMBER",
            "18",
            "2",
            "Y",
            "N",
            f"Derived business metric number {i}",
        )
    )

for i, (target_col, data_type, precision, scale, nullable, pk, definition) in enumerate(
    extra_targets, start=51
):
    source_table = random.choice(["SRC_POLICY", "SRC_CLAIM", "SRC_BILLING", "SRC_SUBMISSION"])
    source_col = f"SRC_{target_col}"
    transformation = random.choice(
        [
            f"ROUND({source_col}, 2)",
            f"COALESCE({source_col}, 0)",
            f"CASE WHEN {source_col} < 0 THEN 0 ELSE {source_col} END",
            f"SUM({source_col}) OVER (PARTITION BY POLICY_NUMBER)",
            f"{source_col} * 1.05",
        ]
    )

    row = [
        f"MAP_{i:04d}",
        "DE Copilot Insurance Data Product",
        "Policy Metrics",
        "POLICY_ADMIN",
        "SRC_DB",
        "PUBLIC",
        source_table,
        source_col,
        "NUMBER",
        precision,
        nullable,
        "N",
        "N",
        f"BR_{i:04d}",
        "Policy Metric Calculation",
        definition,
        "Derived",
        transformation,
        "",
        "",
        "WHERE RECORD_STATUS = 'ACTIVE'",
        "SNOWFLAKE",
        "ANALYTICS_DB",
        "CORE",
        "POLICY_METRIC_FACT",
        target_col,
        data_type,
        "",
        precision,
        scale,
        nullable,
        pk,
        "N",
        "Must be greater than or equal to zero",
        "MEDIUM",
        "Flag Record",
        "SCD1",
        "",
        "",
        "",
        "N",
        "",
        "Data Engineering Team",
        "Approved",
        "Release 1.0",
        f"Complex metric mapping generated for {target_col}",
    ]

    rows.append(row)

with open(output_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file, quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    writer.writerows(rows)

print(f"Generated {output_file} with {len(rows)} mapping rows.")