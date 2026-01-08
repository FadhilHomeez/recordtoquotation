import sys
from graph import build_graph
import psycopg2
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

def manual_test():
    if len(sys.argv) < 2:
        print("Usage: python manual_test.py <item1> <item2> ... [--tenant=<tenant_name>]")
        print("Example: python manual_test.py 'Vinyl Flooring' 'Wall Painting' --tenant=Homeez")
        return

    # Parse args
    tenant_name = "Homeez"
    raw_items = []
    
    for arg in sys.argv[1:]:
        if arg.startswith("--tenant="):
            tenant_name = arg.split("=")[1]
        else:
            raw_items.append(arg)
            
    if not raw_items:
        print("Please provide at least one item description to test.")
        return

    print(f"\n--- SETTING UP TEST FOR TENANT: {tenant_name} ---")

    # Connect to DB to get Tenant ID
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM tenants WHERE name = %s", (tenant_name,))
        res = cur.fetchone()
        
        if not res:
            print(f"Error: Tenant '{tenant_name}' not found. Please verify the name or check the database.")
            conn.close()
            return
            
        tenant_id = res[0]
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return
        
    # Build Graph
    app = build_graph()
    
    inputs = {
        "raw_items": raw_items,
        "tenant_id": str(tenant_id),
        "session_id": str(uuid.uuid4())
    }
    
    print(f"Testing items: {raw_items}\n")
    
    # Run
    result = app.invoke(inputs)
    
    print("\n--- RESULTS ---")
    matched = result.get('matched_items', [])
    suspense = result.get('suspense_items', [])
    quotation = result.get('quotation')
    
    if matched:
        print(f"\n✅ MATCHED ({len(matched)}):")
        for item in matched:
            print(f"  - Input Matched To: '{item.description}'")
            print(f"    Price: ${item.unit_price} / {item.unit}")
            print(f"    Confidence: {item.confidence_score}%")
            
    if suspense:
        print(f"\n⚠️  SUSPENSE ({len(suspense)}):")
        for item in suspense:
            print(f"  - Input: '{item.raw_text}'")
            matches =  item.best_matches
            if matches:
                top = matches[0]
                print(f"    Best Guess: '{top['text']}' (Score: {top['score']}%)")
            else:
                print("    No close matches found.")

    if quotation:
        print(f"\n💰 QUOTATION TOTAL: ${quotation.total_amount:,.2f}")
    
    print("\n-------------------------------------------")

if __name__ == "__main__":
    manual_test()
