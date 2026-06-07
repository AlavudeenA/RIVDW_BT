# Report Intelligence Virtual DW — Build-Time Metadata Ingestion System
## Prompt for Claude in VS Code

---

## What we are building

Build the **build-time pipeline** for a system called **Report Intelligence Virtual DW (RIVDW)**.

This pipeline connects to multiple databases (SQL Server, Oracle), reads their table and column structure (not the actual data), enriches those descriptions using an LLM, lets a human review and correct those descriptions, validates quality through an automated agent, and stores the final result in a vector database so it can be used later for natural language querying.

Think of it as: **"teach the system what data exists and what it means, before any user asks a question."**

---

## Tech Stack

Core Stack
Layer	Technology
UI	Streamlit 1.45.0
Pipeline Orchestration	LangGraph (Python)
LLM Provider	Groq API (flag-based model selection and model slots)
LLM Fallback	VS Code LM API
Vector Store	Local Qdrant (file-based)
Embeddings	FastEmbed using BAAI/bge-small-en-v1.5
Relational Store	SQLite (sqlite3)
Database Access	SQLAlchemy
Configuration	Pydantic + pydantic-settings + python-dotenv
Data Validation	Pydantic
Architecture Requirements
Build the application as a modular Python project.
Use LangGraph to orchestrate all workflows and agent execution.
Route all primary LLM requests through the Groq API.
Implement automatic fallback to VS Code LM API when Groq is turned off. Refer this how to implement it C:\Users\alavu\source\repos\structured-data-search-engine\vscode-lm-extension\src\extension.ts
Store vector embeddings in a local Qdrant instance.
Generate embeddings locally using FastEmbed and BAAI/bge-small-en-v1.5.
Use SQLite as the primary relational database for:
Registry data
Glossary data
Run history
Application metadata
Access SQLite through SQLAlchemy ORM.
Manage all configuration through:
Pydantic models
pydantic-settings
.env files
Use Pydantic models for all request, response, and internal data validation.
The above tech stack is the right choice, in case something contradics prefer these tech stack I mentioned here in Tech Stack section
---

## Project Folder Structure

Create this exact folder structure. Every file has one job only.

```
rivdw_buildtime/
│
├── .env                          # secrets — never commit this
├── .env.example                  # example with placeholder values — commit this
├── requirements.txt              # all pip dependencies
├── README.md                     # how to run the project
│
├── config/
│   ├── __init__.py
│   ├── settings.py               # loads .env, exposes typed config object
│   └── strings.py                # ALL hardcoded UI strings, labels, messages live here
│
├── database/
│   ├── __init__.py
│   ├── connection_registry.py    # reads database list from config, creates SQLAlchemy engines
│   └── schema_crawler.py         # connects to each DB, reads table/column structure
│
├── pipeline/
│   ├── __init__.py
│   ├── graph.py                  # LangGraph pipeline definition — nodes wired together here
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── crawl_node.py         # node: run schema crawlers, return raw metadata
│   │   ├── diff_node.py          # node: compare against previous snapshot, find changes only
│   │   ├── normalise_node.py     # node: make all crawl output the same format
│   │   ├── enrich_node.py        # node: call LLM to generate plain-English descriptions
│   │   └── guardian_node.py      # node: validate quality, reject thin or ambiguous entries
│
├── models/
│   ├── __init__.py
│   ├── metadata_entry.py         # Pydantic model: one table or column entry
│   └── pipeline_state.py         # Pydantic model: what travels between pipeline nodes
│
├── vector_store/
│   ├── __init__.py
│   └── chroma_store.py           # all ChromaDB operations: save, search, update, reset
│
├── glossary/
│   ├── __init__.py
│   └── domain_glossary.py        # business term → table/column mapping, loaded from JSON
│
├── glossary_data/
│   └── glossary.json             # the actual glossary entries (editable by business users)
│
├── snapshots/
│   └── .gitkeep                  # stores previous crawl snapshots for diff comparison
│
└── ui/
    ├── __init__.py
    ├── app.py                    # Streamlit entry point — page routing only
    └── pages/
        ├── __init__.py
        ├── run_pipeline.py       # Screen 1: run the pipeline, see progress
        ├── review_metadata.py    # Screen 2: review and edit LLM enrichments
        └── manage_glossary.py    # Screen 3: manage domain glossary terms
```

---

## Screens — what the UI should look like

### Screen 1 — Run Pipeline (`run_pipeline.py`)

**Purpose:** Trigger the build-time pipeline and watch it run step by step.

**Elements:**
- Page title: "Run Metadata Ingestion Pipeline"
- Short description: "This reads your database structure, generates descriptions using AI, and stores them for querying."
- A "Run Pipeline" button — large, prominent
- A step-by-step progress display showing each node as it completes:
  - Connect to databases
  - Read table and column structure
  - Find what has changed since last run
  - Standardise the format
  - Generate AI descriptions
  - Validate quality
  - Save to vector store
- Each step shows: a spinner while running, green tick when done, red cross if failed
- A summary at the end: "X tables processed, Y columns enriched, Z entries skipped (unchanged)"
- An expandable section "View Details" that shows the raw log output
- A "Download Summary Report" button that exports results as CSV

**Behaviour:**
- Pipeline runs in the background using LangGraph
- UI updates as each node completes using Streamlit's `st.status` or progress components
- If a step fails, show a clear error message in plain English (not a Python traceback)
- After pipeline completes, show a "Go to Review" button that navigates to Screen 2

---

### Screen 2 — Review and Edit Metadata (`review_metadata.py`)

**Purpose:** Let a domain expert review what the LLM generated and correct it before it is finalised. This is the most important screen in the whole system.

**Elements:**
- Page title: "Review AI-Generated Metadata"
- Short description: "Review what the AI generated for each table and column. Correct anything that is wrong or incomplete."
- Left sidebar filters:
  - Dropdown: "Filter by database" (All, DB1, DB2, DB3...)
  - Dropdown: "Filter by domain" (All, Compliance, Surveillance, Employee...)
  - Dropdown: "Filter by status" (All, Pending Review, Approved, Rejected)
  - Search box: "Search by table or column name"
- Main area — a list of cards, one per table, each card shows:
  - Table name (bold)
  - Database and domain tag (small, greyed)
  - AI-generated description (editable text area)
  - A list of columns for that table, each showing:
    - Column name
    - Data type
    - AI-generated description (editable text area)
    - A small "Add note" button to add business context
  - Three buttons at the bottom of each card:
    - "Approve" (green) — marks this entry as human-verified
    - "Reject" (red) — marks it as rejected, sends it back for re-enrichment
    - "Save edits" (blue) — saves manual corrections without approving yet
- At the top of the page:
  - "Approve All Visible" button — approves everything currently shown after confirmation
  - "Export for Review" button — downloads current view as CSV so it can be reviewed offline
- At the bottom of the page:
  - "Reset Vector Store" button — clears all stored metadata with a confirmation dialog
    - Confirmation message: "This will delete all stored metadata. You will need to run the pipeline again. Are you sure?"
    - Two buttons inside confirmation: "Yes, reset everything" and "Cancel"

**Behaviour:**
- All edits are saved immediately to ChromaDB when the user clicks "Save edits"
- Approved entries get a `human_verified: true` flag in the vector store
- Rejected entries get queued for re-enrichment on next pipeline run
- Filters update the displayed cards in real time without a page reload
- Each card remembers its last saved state — reopening the page shows the last saved version

---

### Screen 3 — Manage Domain Glossary (`manage_glossary.py`)

**Purpose:** Let domain experts maintain the business-term-to-column mapping that helps the system understand banking-specific language.

**Elements:**
- Page title: "Domain Glossary"
- Short description: "Map business terms to database columns. The system uses this to find the right data when users ask questions using business language."
- A table showing current glossary entries with columns:
  - Business term (e.g. "headcount")
  - Maps to table (e.g. "pip_violations")
  - Maps to column (e.g. "pip_eligible_count")
  - Domain (e.g. "compliance")
  - Added by / date
- "Add New Term" button that opens a simple form:
  - Text input: "Business term"
  - Dropdown: "Database" (populated from connection registry)
  - Dropdown: "Table" (populated dynamically when database is selected)
  - Dropdown: "Column" (populated dynamically when table is selected)
  - Dropdown: "Domain"
  - "Save" button
- Each existing row has an "Edit" and "Delete" button
- "Export Glossary" button — downloads as CSV
- Changes to the glossary are saved to `glossary_data/glossary.json`

---

## Pipeline Steps — what each step does

### Step 1 — Crawl (`crawl_node.py`)
Connect to each database listed in the connection registry.
For each database, run a read-only query against the system catalog to get all table names and column names with their data types.
Return a raw list of entries — one per column.

For SQL Server use:
```sql
SELECT t.name as table_name, c.name as column_name, ty.name as data_type
FROM sys.tables t
JOIN sys.columns c ON t.object_id = c.object_id
JOIN sys.types ty ON c.user_type_id = ty.user_type_id
WHERE t.is_ms_shipped = 0
ORDER BY t.name, c.column_id
```

For Oracle use:
```sql
SELECT table_name, column_name, data_type
FROM ALL_TAB_COLUMNS
WHERE owner = :schema_name
ORDER BY table_name, column_id
```

Tag every entry with: source_db, db_type, domain_tag (from connection registry).
Save the full crawl result as a JSON snapshot file in `snapshots/` with today's date in the filename.

### Step 2 — Diff (`diff_node.py`)
Load the most recent previous snapshot from `snapshots/`.
Compare it against the current crawl result.
Identify: new entries (never seen before), changed entries (column type changed), unchanged entries.
Only pass new and changed entries to the next step.
Unchanged entries are skipped — they already have good metadata in the vector store.
Log how many were skipped to save cost and time.

### Step 3 — Normalise (`normalise_node.py`)
Take the raw crawl output (which may differ between SQL Server and Oracle format).
Convert every entry to a standard Pydantic model (`MetadataEntry`) with consistent field names and consistent data type vocabulary.
Examples of normalisation:
- Oracle `NUMBER` → `integer`
- Oracle uppercase `TABLE_NAME` → lowercase `table_name`
- SQL Server `datetime` → `timestamp`
- Fill in `nullable: unknown` if the source did not provide it

### Step 4 — Enrich (`enrich_node.py`)
For each normalised entry, call the LLM with a structured prompt.
Ask it to generate:
- A plain-English description of what this table or column contains
- What business process it belongs to
- What other tables it is likely related to
- Any known business terms that refer to this column (check against the domain glossary)

Use a consistent prompt template stored in `config/strings.py` — not hardcoded inside the function.
Process in batches of 20 to avoid rate limits.
Log the cost estimate (token count) for each batch.
If the LLM call fails for any entry, log it and continue — do not stop the whole pipeline.

### Step 5 — Validate (`guardian_node.py`)
For each enriched entry, run these checks:
- Description is present and longer than 20 words (not a thin one-liner)
- Domain tag is assigned and is one of the known domains
- Source database is tagged
- Description does not contain generic filler phrases like "this column contains data" or "stores information"
- If a glossary term applies to this column, it is mentioned in the description

If all checks pass: mark as `guardian_status: approved`
If a check fails but it looks fixable: mark as `guardian_status: needs_review`, add a note explaining exactly what failed
If a check fails badly (empty description, missing domain): mark as `guardian_status: rejected`, queue for re-enrichment

### Step 6 — Store (`chroma_store.py`)
For entries marked `approved` or `needs_review`: save to ChromaDB.
Each entry stored with:
- The enriched description as the text to embed
- Metadata fields: table_name, column_name, source_db, domain_tag, db_type, guardian_status, human_verified, last_updated
For entries marked `rejected`: log them, do not store, they will be picked up on next pipeline run after re-enrichment.
For entries that were unchanged (skipped in diff step): do nothing, their existing vector store entry remains valid.

---

## Data Models

### MetadataEntry (models/metadata_entry.py)
```python
class MetadataEntry(BaseModel):
    # identity
    id: str                      # unique: source_db + table_name + column_name
    source_db: str               # which database this came from
    db_type: str                 # sqlserver / oracle / postgresql
    domain_tag: str              # compliance / surveillance / employee / brokerage

    # structure
    table_name: str
    column_name: str             # empty string if this is a table-level entry
    data_type: str               # normalised type name
    nullable: Optional[bool]

    # enrichment
    description: str             # LLM-generated plain-English description
    business_terms: List[str]    # glossary terms that map to this entry
    related_tables: List[str]    # LLM-identified related tables

    # status
    guardian_status: str         # approved / needs_review / rejected
    human_verified: bool         # True once a domain expert approves it
    human_notes: str             # any corrections added by the reviewer
    last_updated: datetime
```

### PipelineState (models/pipeline_state.py)
```python
class PipelineState(BaseModel):
    # input
    databases_to_crawl: List[str]

    # data flowing between nodes
    raw_entries: List[dict]
    changed_entries: List[dict]
    normalised_entries: List[MetadataEntry]
    enriched_entries: List[MetadataEntry]
    validated_entries: List[MetadataEntry]

    # tracking
    skipped_count: int
    failed_entries: List[dict]
    total_tokens_used: int
    pipeline_run_id: str
    started_at: datetime
```

---

## Config and Secrets

### .env file structure
```
# LLM
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small

# Database connections — add one block per database
DB1_NAME=compliance_db
DB1_TYPE=sqlserver
DB1_HOST=your-server.database.windows.net
DB1_PORT=1433
DB1_USERNAME=readonly_user
DB1_PASSWORD=your_password
DB1_DATABASE=ComplianceDB
DB1_SCHEMA=dbo
DB1_DOMAIN_TAG=compliance
DB1_OWNER=compliance-team@yourcompany.com

DB2_NAME=employee_db
DB2_TYPE=oracle
DB2_HOST=oracle-server.internal
DB2_PORT=1521
DB2_USERNAME=readonly_user
DB2_PASSWORD=your_password
DB2_DATABASE=HRDB
DB2_SCHEMA=HR
DB2_DOMAIN_TAG=employee
DB2_OWNER=hr-team@yourcompany.com

# Vector store
CHROMA_PERSIST_DIR=./chroma_data
CHROMA_COLLECTION_NAME=rivdw_metadata

# Snapshots
SNAPSHOT_DIR=./snapshots

# Pipeline settings
ENRICHMENT_BATCH_SIZE=20
MIN_DESCRIPTION_WORD_COUNT=20
GUARDIAN_FILLER_PHRASES=this column contains data,stores information,contains values
```

### config/settings.py
Load all .env values into a typed Settings object using pydantic-settings.
Expose a single `get_settings()` function that returns the Settings instance.
Every other file imports from settings — no file reads .env directly.

### config/strings.py
Every string that appears in the UI or in LLM prompts lives here.
No hardcoded strings anywhere else.
Organised into sections: UI_LABELS, UI_MESSAGES, UI_CONFIRMATIONS, LLM_PROMPTS, LOG_MESSAGES, ERROR_MESSAGES.

Example:
```python
class LLMPrompts:
    ENRICHMENT_TEMPLATE = """
    You are a data dictionary expert for a banking compliance system.
    
    Describe the following database table/column in plain English.
    Write as if explaining to a business analyst who does not know SQL.
    
    Database: {source_db}
    Domain: {domain_tag}
    Table: {table_name}
    Column: {column_name}
    Data type: {data_type}
    
    Provide:
    1. A clear description of what this stores (minimum 3 sentences)
    2. What business process uses this data
    3. Related tables this is likely joined with
    4. Any business terms a non-technical person might use to refer to this
    
    Be specific. Avoid vague phrases like "stores data" or "contains information".
    """
```

---

## Software Engineering Principles to Follow

**Single Responsibility Principle**
Every file does exactly one thing.
`schema_crawler.py` only crawls. It does not normalise or enrich.
`chroma_store.py` only talks to ChromaDB. It does not call the LLM.
If you find yourself writing "and also" when describing what a file does, split it into two files.

**Easy to read**
Use variable names that say what they are: `normalised_entries` not `ne`, `source_database_name` not `src`.
Write a one-line comment above every function explaining what it does in plain English.
If a function is longer than 30 lines, split it.

**Easy to change**
All strings in `config/strings.py` — so changing UI text or LLM prompts is a one-file change.
All settings in `.env` and `config/settings.py` — so changing a database or model is a one-file change.
Each pipeline node is a separate file — so adding or removing a step touches only `pipeline/graph.py`.

**Error handling**
Every function that calls an external service (database, LLM, ChromaDB) must have a try/except.
Errors must be logged with enough context to debug: which database, which table, which step failed.
Pipeline must continue when one entry fails — never let one bad entry stop the whole run.

**Testability**
Each node function takes a PipelineState and returns a PipelineState — pure function, easy to unit test.
No global state. No singletons except for settings.

**Logging**
Use Python's standard `logging` module — not print statements.
Log at INFO level for normal progress, WARNING for skipped entries, ERROR for failures.
Every log line includes: timestamp, node name, and what happened.

---

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Copy example env and fill in your values
cp .env.example .env

# Run the Streamlit app
streamlit run ui/app.py
```

---

## What to build first (order of work)

1. Project structure and all empty files with docstrings
2. `config/settings.py` and `config/strings.py`
3. `models/metadata_entry.py` and `models/pipeline_state.py`
4. `database/connection_registry.py` and `database/schema_crawler.py`
5. `pipeline/nodes/` — one node at a time, starting with crawl, diff, normalise
6. `pipeline/nodes/enrich_node.py` — LLM enrichment
7. `pipeline/nodes/guardian_node.py` — validation
8. `vector_store/chroma_store.py`
9. `pipeline/graph.py` — wire all nodes together
10. `ui/pages/run_pipeline.py` — Screen 1
11. `ui/pages/review_metadata.py` — Screen 2
12. `ui/pages/manage_glossary.py` — Screen 3
13. `ui/app.py` — wire all screens together

Build and test each step before moving to the next. Do not build all files at once.

---

## Important constraints

- Never read actual data rows from the databases — only read system catalog tables (table names and column names)
- All database connections must be read-only service accounts
- Never log or store database credentials anywhere except .env
- The LLM enrichment step must work even if some databases are unreachable — skip that database, log a warning, continue with others
- The UI must work for a business user who is not a developer — no technical jargon in button labels or messages
- Every destructive action (reset vector store, delete glossary term) must ask for confirmation before executing

