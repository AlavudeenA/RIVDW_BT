"""All hardcoded strings used in the UI and LLM prompts. No string lives anywhere else."""


class UILabels:
    APP_TITLE = "RIVDW — Report Intelligence Virtual Data Warehouse"
    NAV_RUN_PIPELINE = "Run Pipeline"
    NAV_REVIEW_METADATA = "Review Metadata"
    NAV_MANAGE_GLOSSARY = "Manage Glossary"

    # Screen 1
    PAGE_RUN_TITLE = "Run Metadata Ingestion Pipeline"
    PAGE_RUN_DESCRIPTION = (
        "This reads your database structure, generates descriptions using AI, "
        "and stores them for querying."
    )
    BTN_RUN_PIPELINE = "Run Pipeline"
    BTN_DOWNLOAD_REPORT = "Download Summary Report"
    BTN_GO_TO_REVIEW = "Go to Review"

    STEP_CONNECT = "Connect to databases"
    STEP_CRAWL = "Read table and column structure"
    STEP_DIFF = "Find what has changed since last run"
    STEP_NORMALISE = "Standardise the format"
    STEP_ENRICH = "Generate AI descriptions"
    STEP_VALIDATE = "Validate quality"
    STEP_STORE = "Save to vector store"

    # Screen 2
    PAGE_REVIEW_TITLE = "Review AI-Generated Metadata"
    PAGE_REVIEW_DESCRIPTION = (
        "Review what the AI generated for each table and column. "
        "Correct anything that is wrong or incomplete."
    )
    FILTER_DATABASE = "Filter by database"
    FILTER_DOMAIN = "Filter by domain"
    FILTER_STATUS = "Filter by status"
    SEARCH_PLACEHOLDER = "Search by table or column name"
    BTN_APPROVE_ALL = "Approve All Visible"
    BTN_EXPORT_REVIEW = "Export for Review"
    BTN_APPROVE = "Approve"
    BTN_REJECT = "Reject"
    BTN_SAVE_EDITS = "Save edits"
    BTN_ADD_NOTE = "Add note"
    BTN_RESET_VECTOR_STORE = "Reset Vector Store"

    STATUS_PENDING = "Pending Review"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"

    LABEL_ALL = "All"
    LABEL_TABLE = "Table"
    LABEL_COLUMN = "Column"
    LABEL_DATA_TYPE = "Data type"
    LABEL_AI_DESCRIPTION = "AI-generated description"
    LABEL_BUSINESS_NOTES = "Business notes"

    # Build Metadata screen
    NAV_BUILD_METADATA = "Build Metadata"
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

    # Screen 3
    PAGE_GLOSSARY_TITLE = "Domain Glossary"
    PAGE_GLOSSARY_DESCRIPTION = (
        "Map business terms to database columns. The system uses this to find the right "
        "data when users ask questions using business language."
    )
    BTN_ADD_TERM = "Add New Term"
    BTN_EDIT = "Edit"
    BTN_DELETE = "Delete"
    BTN_EXPORT_GLOSSARY = "Export Glossary"
    BTN_SAVE = "Save"
    BTN_CANCEL = "Cancel"

    INPUT_BUSINESS_TERM = "Business term"
    INPUT_DATABASE = "Database"
    INPUT_TABLE = "Table"
    INPUT_COLUMN = "Column"
    INPUT_DOMAIN = "Domain"

    COL_BUSINESS_TERM = "Business Term"
    COL_MAPS_TO_TABLE = "Maps to Table"
    COL_MAPS_TO_COLUMN = "Maps to Column"
    COL_DOMAIN = "Domain"
    COL_ADDED_BY = "Added By"
    COL_DATE = "Date Added"


class UIMessages:
    PIPELINE_RUNNING = "Pipeline is running. Please wait..."
    PIPELINE_COMPLETE = "Pipeline completed successfully."
    PIPELINE_FAILED = "The pipeline could not complete. See details below."
    NO_ENTRIES_FOUND = "No metadata entries found. Run the pipeline first."
    NO_GLOSSARY_TERMS = "No glossary terms yet. Add your first term using the button above."
    APPROVE_ALL_CONFIRM = "Are you sure you want to approve all visible entries?"
    SAVING = "Saving..."
    SAVED = "Saved successfully."
    DELETED = "Deleted successfully."
    EXPORTED = "File ready for download."
    PIPELINE_SUMMARY = "{tables} tables processed, {columns} columns enriched, {skipped} entries skipped (unchanged)."
    STEP_RUNNING = "Running..."
    STEP_DONE = "Done"
    STEP_FAILED = "Failed"
    REJECTED_QUEUED = "Entry rejected and queued for re-enrichment on next run."


class UIConfirmations:
    RESET_VECTOR_STORE_MESSAGE = (
        "This will delete all stored metadata. "
        "You will need to run the pipeline again. Are you sure?"
    )
    RESET_CONFIRM_BTN = "Yes, reset everything"
    RESET_CANCEL_BTN = "Cancel"
    DELETE_GLOSSARY_TERM = "Are you sure you want to delete this term?"
    APPROVE_ALL_VISIBLE = (
        "This will approve all entries currently shown on screen. Continue?"
    )


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

Database: {source_db}
Domain: {domain_tag}
Table: {table_name}

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
