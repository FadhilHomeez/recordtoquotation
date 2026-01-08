import sys
import psycopg2
import os
from dotenv import load_dotenv
from thefuzz import process

load_dotenv()

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def resolve_suspense(suspense_text, target_query, tenant_name="Homeez"):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Get Tenant ID
        cur.execute("SELECT id FROM tenants WHERE name = %s", (tenant_name,))
        res = cur.fetchone()
        if not res:
            print(f"Tenant '{tenant_name}' not found.")
            return
        tenant_id = res[0]
        
        # 2. Find the target price list item
        # We allow target_query to be an ID OR a partial description search
        # Try ID first (UUID format)
        target_item = None
        
        try:
            # Check if valid UUID
            uuid_query = "SELECT id, description, unit_price FROM price_lists WHERE id = %s AND tenant_id = %s"
            cur.execute(uuid_query, (target_query, tenant_id))
            target_item = cur.fetchone()
        except psycopg2.Error:
            conn.rollback() # Not a UUID, ignore error
            
        if not target_item:
            # Search by description
            print(f"Searching for '{target_query}' in price list...")
            cur.execute("SELECT id, description FROM price_lists WHERE tenant_id = %s", (tenant_id,))
            all_items = cur.fetchall() # [(id, desc), ...]
            
            choices = [item[1] for item in all_items]
            best_match = process.extractOne(target_query, choices)
            
            if best_match:
                print(f"Did you mean: '{best_match[0]}' (Score: {best_match[1]})? [y/N]")
                user_input = input().lower()
                if user_input == 'y':
                    # Find ID
                    for item in all_items:
                        if item[1] == best_match[0]:
                            target_item = item
                            break
            
        if not target_item:
            print("Could not find a matching price list item. Aborting.")
            return

        target_id = target_item[0]
        target_desc = target_item[1]
        
        print(f"\nCreating Alias:")
        print(f"  '{suspense_text}' -> '{target_desc}'")
        
        # 3. Insert Alias
        # Check if exists first
        cur.execute("""
            INSERT INTO product_aliases (tenant_id, alias_text, price_list_id, is_verified)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (tenant_id, alias_text) 
            DO UPDATE SET price_list_id = EXCLUDED.price_list_id, is_verified = TRUE
        """, (tenant_id, suspense_text, target_id))
        
        conn.commit()
        print("\n✅ Alias successfully created! The agent will now recognize this term.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        pass
        # Proceed to interactive prompt if args missing? 
        # Or just show usage.
        print("Usage: python resolve_suspense.py <suspense_term> <target_search_term>")
        print("Example: python resolve_suspense.py 'Walkway' 'Vinyl'")
    else:
        resolve_suspense(sys.argv[1], sys.argv[2])
