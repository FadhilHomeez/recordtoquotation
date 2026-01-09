import os
import sys
import uuid
import psycopg2
from dotenv import load_dotenv
from graph import build_graph

load_dotenv()

def get_tenant_id(tenant_name="Homeez"):
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        cur.execute("SELECT id FROM tenants WHERE name = %s", (tenant_name,))
        res = cur.fetchone()
        conn.close()
        if res:
            return str(res[0])
    except Exception as e:
        print(f"DB Error: {e}")
    return "dummy-tenant-id" 

def test_guardrail():
    print("🚀 STARTING GUARDRAIL TESTS...")
    
    app = build_graph()
    tenant_id = get_tenant_id()
    
    # 1. TEST INJECTION (Should Fail)
    print("\n[1] Testing Malicious Input (Injection)...")
    with open("tests/injection_transcript.txt", "r") as f:
        injection_text = f.read()
        
    inputs_bad = {
        "raw_items": injection_text,
        "tenant_id": tenant_id,
        "session_id": str(uuid.uuid4())
    }
    
    result_bad = app.invoke(inputs_bad)
    
    if result_bad.get("error"):
        print(f"✅ PASSED: Blocked with error: {result_bad['error']}")
    else:
        print("❌ FAILED: Injection was NOT blocked!")
        
    # 2. TEST SINGLISH (Should Pass)
    print("\n[2] Testing Safe Input (Singlish)...")
    with open("tests/singlish_transcript.txt", "r") as f:
        singlish_text = f.read()
        
    inputs_good = {
        "raw_items": singlish_text,
        "tenant_id": tenant_id,
        "session_id": str(uuid.uuid4())
    }
    
    try:
        result_good = app.invoke(inputs_good)
        if result_good.get("error"):
             print(f"❌ FAILED: Safe input flagged as error: {result_good['error']}")
        else:
             quotation = result_good.get("quotation")
             if quotation:
                 print(f"✅ PASSED: Generated quotation total: ${quotation.total_amount:,.2f}")
             else:
                 print("⚠️  WARNING: No error, but no quotation generated (might be extractor failure, but guardrail passed).")
                 
    except Exception as e:
        print(f"❌ FAILED: Exception during safe run: {e}")

if __name__ == "__main__":
    test_guardrail()
