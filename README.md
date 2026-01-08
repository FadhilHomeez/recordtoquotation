# Singapore Interior Design Quotation Agent
A Multi-Tenant SaaS Agent that converts audio/transcripts of ID client meetings into structured Renovation Quotations.

## Setup

1. **Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2. **Database**:
    - Ensure Postgres is running.
    - Copy `.env.example` to `.env` and update `DATABASE_URL`.
    - Run schema creation:
        ```bash
        psql $DATABASE_URL -f schema.sql
        ```
    
3. **Ingest Price List**:
    - Use `create_sample_excel.py` to generate value for testing:
        ```bash
        python create_sample_excel.py
        ```
    - Run ingestion:
        ```bash
        python ingest_excel.py sample_prices.xlsx "Test Tenant" --create-tenant
        ```

## Architecture
- `schema.sql`: Postgres schema (Tenants, Price Lists, Aliases, Quotations).
- `ingest_excel.py`: Pipeline to load ID Excel price lists.
- `state.py`: LangGraph state definition (Phase 2).
- `graph.py`: Main workflow (Phase 2).

## Next Steps
Phase 2 will implement the Core Graph Logic (Matcher, Pricer).
