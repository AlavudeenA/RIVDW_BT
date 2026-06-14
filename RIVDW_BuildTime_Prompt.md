# Report Intelligence Virtual DW — Build-Time Metadata Ingestion System

## Prompt for Claude in VS Code

---

## What we are building

Build-time: Vector Metadata Ingestion (1/2)
How schema metadata is extracted, enriched and reviewed before entering the vector store
Flow:

Source Databases (parallel):
SQL Server DB1 (Compliance)
SQL Server DB2 (ATTEST)
Oracle DB3 (GPS)
SQL Server DB4...DBn

↓ Connection Registry (YAML/Config)
(DB type • host • credentials • domain tag • owner)
↓ Schema Crawlers
SQL Server → sys.tables / sys.columns
Oracle → ALL_TAB_COLUMNS
Extensible for any JDBC/ODBC source

→ Metadata Normalizer Agent
(Merges crawl output into unified schema format • source DB tagged on every entry • ready for enrichment)
→ Incremental Diff Engine
(Skip Unchanged Entries)
↓ LLM Metadata Enrichment Agent
(Generates plain-English description per table/column • Adds domain tag • usage context • cross-source relationships)

Build-time: Vector Metadata Ingestion (2/2)
Human review, Metadata Guardian validation, and final write to the vector store
Flow:

LLM Metadata Enrichment Agent output flows into Domain Expert Review

Main Path:

Domain Expert Review (Human)
Confirms descriptions are business-accurate
Corrects domain tags
Validates cross-source relationships
Flags LLM misinterpretations

Domain Glossary (Human Curated Pre-Defined Business Terms)
↓ Metadata Guardian Agent
Checks:
Description present and meaningful?
Domain tag assigned?
Source DB tagged?
No ambiguous column names?
Simple fail → LLM re-enriches automatically
Complex fail → escalate to human resolve

Approved ↓
Vector Metadata Store
(Quality-gated • human-verified • source-tagged • domain-tagged • ready for retrieval)

Loops:

Correct + re-enrich (back to LLM)
Fix and re-enrich
Scheduled re-ingestion on schema change

Runtime: User Query Flow (1/3)
User query enters the system. LLM extracts intent. Cache and vector store checked simultaneously
Flow:

User (Natural Language Query)
(Role + department captured on login)
↓ LLM Orchestration Agent
(Intent extraction • schema routing • query planning • multi-source detection • role context)
Branches (parallel):
Vector Metadata Store (Semantic search → returns top matches + confidence score)
Approved Query Cache (Exact + semantic embedding match check)

Search Resolution Agent (if needed from Vector Store)
Score ≥ threshold → pass through
Synonym expansion + re-search
Ask user: which domain?
Surface top 3 tables to confirm

Cache Resolution Agent (if match in cache)
Detects parameter drift (date/dept/threshold)
Params match → execute cached SQL directly
Param drift → adjust SQL then execute

Runtime: User Query Flow (2/3)
SQL generation • Query Guardian validation • approval and cache write
Flow (continued from previous agents):

Text-to-SQL Generation Agent
(LLM generates SQL from enriched metadata context • Schema-aware • Read-only enforced • Row-level security parameters injected)
↓ Query Guardian Agent
Checks:
SELECT-only (no writes/drops)
Role permissions validated
Row limits enforced
Tables within user scope?
Auto-approve / Auto-reject + reason
Escalate if ambiguous
Separate critic model — never validates its own generated SQL
Every decision logged for audit trail

Decisions:
Reject / Regenerate (loop back)
Approved ↓

Approved → Write to Cache
(Query • user role • department • tables touched • source DBs • timestamp • confidence score)
↓ Source Routing Decision
Single source? → direct execution
Multi-source detected? → Federation Agent

Runtime: User Query Flow (3/3)
Federation Agent • virtual staging • composition engine • secure execution • results
Flow:
Two Paths:
A. Single Source Path (Direct Execution)
B. Multi-source Path (Federation Agent)
Federation Agent:

Identifies DBs needed via connection registry
Decomposes into per-DB sub-queries
Dispatch in parallel — each on its own connection
Collect results → stage in virtual layer

Common Steps:

Secure Query Execution
(Runs against source DBs • Enforces ACL • Allow Only Select • Query Validation)
Virtual Data Warehouse Layer (on-demand • session-scoped • in-memory)
(Collected result sets from each DB stored temporarily • No permanent storage • Cleared after response • Source-tagged • ready for cross join)
Composition Query Engine
(Runs final query across staged result sets • Joins • Aggregates • Filters • Formats for report)
Results Delivered to User
(Table • chart • export • feedback thumbs up/down • logged to usage intelligence store)

---

## What design and architecture principle you have to follow when you generate code

1. Use simple, real-world words like sendEmail() and InvoiceCalculator. If a name needs "and" (e.g., validateAndSave), that's a sign you're doing too many things in one place.

2: Give every piece exactly one job
Each method should do one thing well. Each class should represent a single concept or actor. Each file should contain one logical unit — never mix helpers, data, and UI in one file.

3: Prioritize predictability over cleverness
Write code that reads like clear prose, not a puzzle. Following the first two steps ensures any developer can understand intent instantly, and every component has only one reason to change.

4. Small, focused pieces make the system scalable and easy to understand — because you can change one thing without breaking everything else.

---

---

## Tech Stack

Core Stack
Layer Technology
UI Streamlit 1.45.0
Pipeline Orchestration LangGraph (Python)
LLM Provider Groq API (flag-based model selection and model slots)
LLM Fallback VS Code LM API
Vector Store Local Qdrant (file-based)
Embeddings FastEmbed using BAAI/bge-base-en-v1.5
Relational Store SQLite (sqlite3)
Database Access SQLAlchemy
Configuration Pydantic + pydantic-settings + python-dotenv
Data Validation Pydantic
Architecture Requirements
Build the application as a modular Python project.
Use LangGraph to orchestrate all workflows and agent execution.
Route all primary LLM requests through the Groq API.
Implement automatic fallback to VS Code LM API when Groq is turned off. Refer this how to implement it C:\Users\alavu\source\repos\structured-data-search-engine\vscode-lm-extension\src\extension.ts
Store vector embeddings in a local Qdrant instance.
Generate embeddings locally using FastEmbed and BAAI/bge-base-en-v1.5.
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
