# RIVDW — Report Intelligence Virtual Data Warehouse

Reads database structure from SQL Server and Oracle, generates plain-English descriptions using an LLM, and stores the enriched metadata in a vector database for natural-language querying.

## Repository Layout

```
RIVDW/
├── rivdw_buildtime/   ← the application (start here)
│   ├── README.md      ← full setup and usage guide
│   ├── config/
│   ├── database/
│   ├── pipeline/
│   ├── ui/
│   └── vector_store/
└── RIVDW_BuildTime_Prompt.md   ← original system specification
```

## Quick Start

```bash
cd rivdw_buildtime
python -m pip install -r requirements.txt

# Copy the environment template and fill in your values
cp .env.example .env

# Run the app
python -m streamlit run ui/app.py
```

See [rivdw_buildtime/README.md](rivdw_buildtime/README.md) for full setup instructions, LLM configuration, and how to connect your databases.
