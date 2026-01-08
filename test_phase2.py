import sys
from graph import build_graph
import psycopg2
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

def verify_phase2():
    # 1. Setup Test Data
    tenant_name = "Phase2 Test Tenant"
    
    # Connect to DB to get Tenant ID (created in Phase 1 or we create now)
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM tenants WHERE name = %s", (tenant_name,))
    res = cur.fetchone()
    
    if not res:
        print(f"Creating test tenant: {tenant_name}")
        cur.execute("INSERT INTO tenants (name) VALUES (%s) RETURNING id", (tenant_name,))
        tenant_id = cur.fetchone()[0]
        conn.commit()
        
        # Insert some price list items
        cur.execute("""
            INSERT INTO price_lists (tenant_id, description, unit, unit_price)
            VALUES 
                (%s, 'Vinyl Flooring 5mm', 'sqft', 5.50),
                (%s, 'Whole House Painting', 'LS', 1500.00)
            ON CONFLICT (tenant_id, description) DO NOTHING
        """, (str(tenant_id), str(tenant_id)))
        conn.commit()
    else:
        tenant_id = res[0]
        print(f"Using existing tenant: {tenant_id}")
        
    cur.close()
    conn.close()
    
    # 2. Run Graph
    app = build_graph()
    
    inputs = {
        "raw_items": ["Vinyl Flooring 5mm", "Random Suspense Item"],
        "tenant_id": str(tenant_id),
        "session_id": str(uuid.uuid4())
    }
    
    print("\nInvoking Graph with inputs:", inputs)
    result = app.invoke(inputs)
    
    print("\n--- RESULT ---")
    matched = result.get('matched_items', [])
    suspense = result.get('suspense_items', [])
    quotation = result.get('quotation')
    
    print(f"Matched Items ({len(matched)}):")
    for item in matched:
        print(f" - {item.description} | ${item.unit_price} | Score: {item.confidence_score}")
        
    print(f"Suspense Items ({len(suspense)}):")
    for item in suspense:
        print(f" - {item.raw_text} | Score: {item.confidence_score}")
        
    if quotation:
        print(f"\nQuotation Total: ${quotation.total_amount}")
    
    # Assertions
    if len(matched) >= 1 and matched[0].description == "Vinyl Flooring 5mm":
        print("\nSUCCESS: Matched known item.")
    else:
        print("\nFAIL: Did not match known item.")
        
    if len(suspense) >= 1 and suspense[0].raw_text == "Random Suspense Item":
        print("SUCCESS: Correctly identified suspense item.")
    else:
        print("FAIL: Did not identify suspense item.")

if __name__ == "__main__":
    verify_phase2()
