"""All hardcoded strings used in the UI and LLM prompts. No string lives anywhere else."""


class UILabels:
    APP_TITLE = "RIVDW — Report Intelligence Virtual Data Warehouse"

    # Build Metadata screen
    NAV_BUILD_METADATA = "Build Metadata"

    # Query screen
    NAV_QUERY = "Query"
    PAGE_QUERY_TITLE = "Query Metadata"
    PAGE_QUERY_DESCRIPTION = (
        "Ask a question in plain English to find relevant tables and columns "
        "across your databases."
    )
    QUERY_INPUT_PLACEHOLDER = "e.g. Which tables store employee trade requests for compliance review?"
    BTN_QUERY_SUBMIT = "Search"
    PAGE_BUILD_TITLE = "Build Metadata"
    PAGE_BUILD_DESCRIPTION = (
        "Select a database, generate AI descriptions for every table and column, "
        "then review and correct them — all in one place."
    )
    LABEL_SELECT_DB = "Select Database"
    BTN_GENERATE = "Generate Metadata"
    BTN_SAVE_TABLE = "Save Changes"
    BTN_REGENERATE_TABLE = "Re-generate"
    LABEL_TABLE_DESCRIPTION = "Table Description"
    LABEL_COLUMN_DESCRIPTION = "Column Description"
    LABEL_HISTORY = "Change History"
    LABEL_FILTER_TABLE_HISTORY = "Filter history by table"
    LABEL_VERSION = "Version"
    LABEL_CHANGED_AT = "Changed At"
    LABEL_CHANGED_BY = "Changed By"
    LABEL_CHANGE_TYPE = "Type"
    GENERATING_TABLE = "Generating metadata for table: {table_name} ({col_count} columns)..."
    TABLE_DONE = "Done: {table_name}"
    GENERATION_COMPLETE = "Metadata generated for {table_count} tables. Scroll down to review."
    NO_DATABASES_CONFIGURED = "No databases configured. Add an entry to config/databases.json and a connection string to .env, then restart."
    NO_ENTRIES_FOR_DB = "No metadata found for this database. Click Generate Metadata to start."
    HISTORY_EMPTY = "No changes recorded yet. Generate or edit metadata to see history here."
    BTN_EXPORT_HISTORY = "Export History CSV"


class UIMessages:
    SAVING = "Saving..."
    SAVED = "Saved successfully."
    EXPORTED = "File ready for download."


class LLMPrompts:
    ENRICHMENT_TEMPLATE = """You are a data dictionary expert for a banking compliance system.

Describe the following database table/column in plain English.
Write as if explaining to a business analyst who does not know SQL.

Database: {source_db}
Domain: {domain_tag}
Table: {table_name}
Column: {column_name}
Data type: {data_type}
Known business terms that may apply: {business_terms}

Provide:
1. A clear description of what this stores (minimum 3 sentences)
2. What business process uses this data
3. Related tables this is likely joined with
4. Any business terms a non-technical person might use to refer to this

Be specific. Avoid vague phrases like "stores data" or "contains information".
Return a JSON object with keys: description, business_process, related_tables (list), business_terms (list).
"""

    TABLE_ENRICHMENT_TEMPLATE = """You are a data dictionary expert for a banking compliance system.

Describe the following database table in plain English.
Write as if explaining to a business analyst who does not know SQL.

Database: {source_db}
Domain: {domain_tag}
Table: {table_name}

Columns in this table: {column_list}

Provide:
1. A clear description of what this table stores (minimum 3 sentences)
2. What business process this table supports
3. Other tables it is likely joined with
4. Common business terms used to refer to this data

Be specific. Avoid vague phrases like "stores data" or "contains information".
Return a JSON object with keys: description, business_process, related_tables (list), business_terms (list).
"""


    BATCH_TABLE_TEMPLATE = """You are a data dictionary expert for a banking compliance system.

A business analyst needs to understand a database table and all its columns.
Write in plain English — no SQL jargon, no technical abbreviations.

Database: {db_display_name} ({source_db})
Schema: {schema_name}
Database context: {db_description}
Domain: {domain_tag}
Table: {schema_name}.{table_name}

Columns (name | data type):
{column_list}

For each column, write a clear description (minimum 3 sentences) that explains:
- What the column stores in business terms
- Which business process creates or uses this value
- Any obvious related tables or columns

Also describe what the overall table is used for (minimum 3 sentences).

Return ONLY a valid JSON object in this exact format — no markdown, no extra text:
{{
  "table_description": "...",
  "table_business_process": "...",
  "table_related_tables": ["table1", "table2"],
  "columns": {{
    "column_name_1": {{
      "description": "...",
      "business_process": "...",
      "related_tables": ["t1"],
      "business_terms": ["term1"]
    }},
    "column_name_2": {{
      "description": "...",
      "business_process": "...",
      "related_tables": [],
      "business_terms": []
    }}
  }}
}}

Never use phrases like "stores data", "contains information", "holds values".
Be specific to the {domain_tag} domain.
"""


class LogMessages:
    CRAWL_START = "Starting schema crawl for database: {db_name}"
    CRAWL_DONE = "Crawl complete for {db_name}: {count} columns found"
    CRAWL_SKIPPED = "Skipping unreachable database: {db_name} — {error}"
    DIFF_SUMMARY = "Diff complete: {new} new, {changed} changed, {unchanged} unchanged entries"
    NORMALISE_DONE = "Normalisation complete: {count} entries standardised"
    ENRICH_BATCH = "Enriching batch {batch_num}/{total_batches} ({count} entries)"
    ENRICH_ENTRY_FAILED = "Enrichment failed for {entry_id}: {error}"
    GUARDIAN_APPROVED = "Guardian approved: {entry_id}"
    GUARDIAN_REVIEW = "Guardian flagged for review: {entry_id} — {reason}"
    GUARDIAN_REJECTED = "Guardian rejected: {entry_id} — {reason}"
    STORE_SAVED = "Saved {count} entries to vector store"
    STORE_SKIPPED = "Skipped {count} rejected entries (not stored)"
    SNAPSHOT_SAVED = "Snapshot saved: {path}"
    LLM_FALLBACK = "Groq is disabled — falling back to VS Code LM API"
    LLM_TOKENS = "Batch {batch_num} used approximately {tokens} tokens"


class ErrorMessages:
    DB_CONNECTION_FAILED = (
        "Could not connect to database '{db_name}'. "
        "Check your connection settings and try again."
    )
    LLM_UNAVAILABLE = (
        "The AI description service is not available. "
        "Check your Groq API key or VS Code LM extension."
    )
    VECTOR_STORE_ERROR = (
        "Could not save to the vector store. "
        "Check that the Qdrant data directory is writable."
    )
    SNAPSHOT_READ_ERROR = "Could not read previous snapshot. Starting fresh comparison."
    PIPELINE_NODE_ERROR = "Step '{node}' encountered an error: {error}"
    INVALID_DB_TYPE = "Unsupported database type: {db_type}. Use 'sqlserver' or 'oracle'."
