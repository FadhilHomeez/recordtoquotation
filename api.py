from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import uuid
import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from graph import build_graph

load_dotenv()

app = FastAPI(title="Renovation Quotation Agent API")

# --- Models ---
class QuotationRequest(BaseModel):
    transcript: str
    tenant_name: str = "Homeez"

class ResolveRequest(BaseModel):
    suspense_text: str
    target_item_id: str
    tenant_name: str = "Homeez"

class QuotationResponse(BaseModel):
    quotation_id: str
    status: str

# --- DB Helper ---
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# --- Background Task ---
def process_quotation(quotation_id: str, transcript: str, tenant_name: str):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Get Tenant ID
        cur.execute("SELECT id FROM tenants WHERE name = %s", (tenant_name,))
        res = cur.fetchone()
        if not res:
            # Create if not exists for API convenience? Or fail? 
            # Let's fail for now to be safe, or default.
            print(f"Tenant {tenant_name} not found.")
            return
        tenant_id = str(res[0])
        
        # 2. Run Graph
        app_graph = build_graph()
        inputs = {
            "raw_items": [transcript], 
            # Phase 5: Pass full transcript to Extractor Node
            "tenant_id": tenant_id,
            "session_id": str(uuid.uuid4())
        }
        
        result = app_graph.invoke(inputs)
        
        # 3. Save Results (Quotations Table)
        quotation = result.get('quotation')
        total_amount = quotation.total_amount if quotation else 0.0
        
        # Update status to completed
        cur.execute("""
            UPDATE quotations 
            SET total_amount = %s, status = 'completed' 
            WHERE id = %s
        """, (total_amount, quotation_id))
        
        # Save Items (Matched)
        matched_items = result.get('matched_items', [])
        for item in matched_items:
            # We need to map back to proper format
            cur.execute("""
                INSERT INTO quotation_items (quotation_id, price_list_id, description, quantity, unit_price, confidence_score, is_suspense)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE)
            """, (quotation_id, item.price_list_id, item.description, item.quantity, item.unit_price, item.confidence_score))
            
        # Save Items (Suspense)
        suspense_items = result.get('suspense_items', [])
        for item in suspense_items:
            cur.execute("""
                INSERT INTO quotation_items (quotation_id, description, unit_price, confidence_score, is_suspense)
                VALUES (%s, %s, 0, %s, TRUE)
            """, (quotation_id, item.raw_text, item.confidence_score))
            
        conn.commit()
        print(f"Quotation {quotation_id} processed successfully.")
        
    except Exception as e:
        print(f"Error processing quotation {quotation_id}: {e}")
        conn.rollback()
        # Mark as failed
        # cur.execute("UPDATE quotations SET status = 'failed' WHERE id = %s", (quotation_id,))
        # conn.commit()
    finally:
        cur.close()
        conn.close()

# --- Endpoints ---

@app.post("/quotation", response_model=QuotationResponse)
async def create_quotation(req: QuotationRequest, background_tasks: BackgroundTasks):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Get Tenant ID
        cur.execute("SELECT id FROM tenants WHERE name = %s", (req.tenant_name,))
        res = cur.fetchone()
        if not res:
            raise HTTPException(status_code=404, detail=f"Tenant '{req.tenant_name}' not found")
        tenant_id = res[0]
        
        # 2. Create Quotation Record
        quotation_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO quotations (id, tenant_id, client_name, status)
            VALUES (%s, %s, 'API User', 'processing')
        """, (quotation_id, tenant_id))
        conn.commit()
        
        # 3. Trigger Background Processing
        background_tasks.add_task(process_quotation, quotation_id, req.transcript, req.tenant_name)
        
        return {"quotation_id": quotation_id, "status": "processing"}
        
    finally:
        cur.close()
        conn.close()

@app.get("/quotation/{quotation_id}")
async def get_quotation(quotation_id: str):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Fetch Header
        cur.execute("SELECT * FROM quotations WHERE id = %s", (quotation_id,))
        quotation = cur.fetchone()
        if not quotation:
            raise HTTPException(status_code=404, detail="Quotation not found")
            
        # Fetch Items
        cur.execute("SELECT * FROM quotation_items WHERE quotation_id = %s", (quotation_id,))
        items = cur.fetchall()
        
        return {
            "quotation": quotation,
            "items": items
        }
    finally:
        cur.close()
        conn.close()

@app.post("/resolve")
async def resolve_suspense_endpoint(req: ResolveRequest):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get Tenant
        cur.execute("SELECT id FROM tenants WHERE name = %s", (req.tenant_name,))
        res = cur.fetchone()
        if not res:
            raise HTTPException(404, "Tenant not found")
        tenant_id = res[0]
        
        # Verify Target Item Existence
        cur.execute("SELECT description FROM price_lists WHERE id = %s AND tenant_id = %s", (req.target_item_id, tenant_id))
        if not cur.fetchone():
             raise HTTPException(404, "Target price list item not found")

        # Upsert Alias
        cur.execute("""
            INSERT INTO product_aliases (tenant_id, alias_text, price_list_id, is_verified)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (tenant_id, alias_text) 
            DO UPDATE SET price_list_id = EXCLUDED.price_list_id, is_verified = TRUE
        """, (tenant_id, req.suspense_text, req.target_item_id))
        
        conn.commit()
        return {"message": "Alias created successfully", "text": req.suspense_text}
        
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(500, detail=str(e))
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
