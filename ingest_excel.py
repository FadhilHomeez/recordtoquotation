import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
import uuid
import sys
from dotenv import load_dotenv

load_dotenv()

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def ingest_excel(file_path, tenant_name, create_tenant=False):
    """
    Ingests an Excel price list into the database for a specific tenant.
    
    Expected Excel columns:
    - Category
    - Description
    - Unit
    - Unit Price
    - Code (Optional)
    """
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Create/Get Tenant
        cur.execute("SELECT id FROM tenants WHERE name = %s", (tenant_name,))
        tenant = cur.fetchone()
        if not tenant:
            print(f"Creating tenant '{tenant_name}'...")
            cur.execute("INSERT INTO tenants (name) VALUES (%s) RETURNING id", (tenant_name,))
            tenant_id = cur.fetchone()[0]
        else:
            tenant_id = tenant[0]
            print(f"Tenant '{tenant_name}' found (ID: {tenant_id}).")
            # Optional: Clear existing items for a clean reload
            print("Clearing existing price list items for this tenant...")
            cur.execute("DELETE FROM price_lists WHERE tenant_id = %s", (tenant_id,))

        # Load Data
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext == '.csv':
            # New format has headers on row 3 (index 2)
            df = pd.read_csv(file_path, header=2)
        else:
            # Fallback to excel (assuming row 0 header for old format)
            df = pd.read_excel(file_path)

        print(f"Loaded {len(df)} rows from {file_path}")
        
        # normalize columns
        df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]

        # Map columns based on file type/content
        # New CSV: Service_Category, Name, Unit, Price, Service_ID
        # Old Excel: Category, Description, Unit, Unit Price
        
        records_to_insert = []
        seen_descriptions = set()

        for _, row in df.iterrows():
            # Handle new format
            if 'Service_Category' in df.columns:
                category = row.get('Service_Category')
                description = row.get('Name')
                unit = row.get('Unit')
                price = row.get('Price')
                item_code = row.get('Service_ID')
            else:
                # Old format fallback
                category = row.get('Category')
                description = row.get('Description')
                unit = row.get('Unit')
                price = row.get('Unit Price')
                item_code = None

            # Clean data
            if pd.isna(description) or pd.isna(price):
                continue
                
            description = str(description).strip()
            
            # Deduplication
            if description in seen_descriptions:
                continue
            seen_descriptions.add(description)

            # Handle price cleaning (remove $, commas)
            try:
                val = str(price).replace('$', '').replace(',', '').strip()
                # Handle ranges or text in price? For now assume numeric-ish
                unit_price = float(val)
            except ValueError:
                unit_price = 0.0

            records_to_insert.append((
                str(tenant_id),
                category if not pd.isna(category) else 'General',
                description,
                unit if not pd.isna(unit) else 'lot',
                unit_price,
                item_code
            ))

        print(f"Inserting {len(records_to_insert)} items...")
        
        execute_values(cur, """
            INSERT INTO price_lists (tenant_id, category, description, unit, unit_price, item_code)
            VALUES %s
        """, records_to_insert)
        conn.commit()
        print("Ingestion complete.")

    except Exception as e:
        conn.rollback()
        print(f"Error during ingestion: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ingest_excel.py <file_path> <tenant_name> [--create-tenant]")
        sys.exit(1)
        
    file_path = sys.argv[1]
    tenant_name = sys.argv[2]
    create_tenant = "--create-tenant" in sys.argv
    
    ingest_excel(file_path, tenant_name, create_tenant)
