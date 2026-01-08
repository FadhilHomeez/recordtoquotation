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

    print(f"Reading {file_path}...")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Normalize columns
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Map columns to expected keys
    column_map = {
        'category': 'category',
        'description': 'description',
        'item description': 'description', # Alias
        'unit': 'unit',
        'unit price': 'unit_price',
        'price': 'unit_price', # Alias
        'code': 'item_code',
        'item code': 'item_code' # Alias
    }
    
    # Check for required columns
    required = ['description', 'unit_price']
    
    mapped_df = pd.DataFrame()
    for col in df.columns:
        if col in column_map:
            mapped_df[column_map[col]] = df[col]
        elif col in column_map.values():
             mapped_df[col] = df[col]
            
    # Check if required columns exist
    missing = [req for req in required if req not in mapped_df.columns]
    if missing:
        print(f"Missing required columns: {missing}")
        print(f"Available columns: {df.columns}")
        return

    # Clean data
    mapped_df['description'] = mapped_df['description'].astype(str).str.strip()
    mapped_df['unit_price'] = pd.to_numeric(mapped_df['unit_price'], errors='coerce').fillna(0)
    if 'category' in mapped_df.columns:
        mapped_df['category'] = mapped_df['category'].astype(str).str.strip()
    else:
        mapped_df['category'] = 'General'
        
    if 'unit' in mapped_df.columns:
        mapped_df['unit'] = mapped_df['unit'].astype(str).str.strip()
    else:
        mapped_df['unit'] = 'LS' # Lump Sum default

    if 'item_code' not in mapped_df.columns:
        mapped_df['item_code'] = None

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Get or Create Tenant
        cur.execute("SELECT id FROM tenants WHERE name = %s", (tenant_name,))
        res = cur.fetchone()
        
        if res:
            tenant_id = res[0]
            print(f"Found existing tenant: {tenant_name} ({tenant_id})")
        elif create_tenant:
            print(f"Creating new tenant: {tenant_name}")
            cur.execute("INSERT INTO tenants (name) VALUES (%s) RETURNING id", (tenant_name,))
            tenant_id = cur.fetchone()[0]
        else:
            print(f"Tenant '{tenant_name}' not found. Use --create-tenant to create it.")
            return

        # Prepare data for insertion
        # Remove duplicates from mapped_df based on description to avoid ON CONFLICT errors within the same batch
        original_count = len(mapped_df)
        mapped_df = mapped_df.drop_duplicates(subset=['description'], keep='last')
        if len(mapped_df) < original_count:
            print(f"Dropped {original_count - len(mapped_df)} duplicate descriptions.")
        
        print(f"Ingesting {len(mapped_df)} items...")
        
        insert_query = """
            INSERT INTO price_lists (tenant_id, category, description, unit, unit_price, item_code)
            VALUES %s
            ON CONFLICT (tenant_id, description) 
            DO UPDATE SET
                unit_price = EXCLUDED.unit_price,
                category = EXCLUDED.category,
                unit = EXCLUDED.unit,
                item_code = EXCLUDED.item_code,
                effective_date = CURRENT_DATE;
        """
        
        data_tuples = []
        for _, row in mapped_df.iterrows():
            data_tuples.append((
                str(tenant_id),
                row['category'],
                row['description'],
                row['unit'],
                row['unit_price'],
                row['item_code']
            ))
            
        execute_values(cur, insert_query, data_tuples)
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
