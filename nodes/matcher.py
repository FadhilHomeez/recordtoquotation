from typing import List, Dict, Any
from state import RenovationState, QuotationItem, SuspenseItem
from thefuzz import process, fuzz
import psycopg2
import os
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

CONFIDENCE_THRESHOLD = 98

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def matcher_node(state: RenovationState) -> Dict[str, Any]:
    print("--- MATCHER NODE ---")
    raw_items = state.get('raw_items', [])
    tenant_id = state.get('tenant_id')
    
    matched_items: List[QuotationItem] = state.get('matched_items', [])
    suspense_items: List[SuspenseItem] = state.get('suspense_items', [])
    
    if not raw_items:
        return {"matched_items": matched_items, "suspense_items": suspense_items}

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Fetch Price List items for this Tenant
        cur.execute("""
            SELECT id, description, unit, unit_price 
            FROM price_lists 
            WHERE tenant_id = %s
        """, (tenant_id,))
        price_list_items = cur.fetchall()
        
        # 2. Fetch Aliases for this Tenant (Phase 3 Prep)
        cur.execute("""
            SELECT alias_text, price_list_id 
            FROM product_aliases 
            WHERE tenant_id = %s
        """, (tenant_id,))
        aliases = cur.fetchall()
        
        # Map IDs to items for easy lookup
        # Choices for fuzzy search: description + alias_text
        # Map IDs to items for easy lookup
        # Choices for fuzzy search: description + alias_text
        choices_map = {} # item_text -> price_list_item_dict
        choices_list = []
        
        for item in price_list_items:
            desc = item['description']
            choices_map[desc] = item
            choices_list.append(desc)
            
        # Incorporate aliases
        for alias in aliases:
            text = alias['alias_text']
            pl_id = alias['price_list_id']
            # Find the original item
            # We can traverse price_list_items again or key them by ID first.
            # Efficient way: Dict by ID
            
            # For simplicity, let's find the item in price_list_items linked to this alias
            linked_item = next((i for i in price_list_items if i['id'] == pl_id), None)
            if linked_item:
                choices_map[text] = linked_item # Map alias text to the ACTUAL item data
                choices_list.append(text)
        
        for item in raw_items:
            raw_text = item.description # Fuzzy match on description
            print(f"Matching: {raw_text}")
            
            # Simple matching on description for now
            # Extract top 3 matches
            matches = process.extract(raw_text, choices_list, limit=3, scorer=fuzz.token_sort_ratio)
            
            best_match = matches[0] if matches else None
            
            if best_match and best_match[1] >= CONFIDENCE_THRESHOLD:
                print(f"  Matched: {best_match[0]} ({best_match[1]}%)")
                item_data = choices_map[best_match[0]]
                
                # Use extracted quantity and unit if available/different?
                # For now, we use the price list unit for pricing consistency,
                # but we use the extracted quantity.
                
                quotation_item = QuotationItem(
                    description=item_data['description'],
                    quantity=item.quantity, # Use extracted quantity
                    unit=item_data['unit'], # Use price list unit
                    unit_price=float(item_data['unit_price']),
                    subtotal=float(item_data['unit_price']) * item.quantity, 
                    confidence_score=float(best_match[1]),
                    price_list_id=str(item_data['id']),
                    is_suspense=False,
                    location=item.location
                )
                matched_items.append(quotation_item)
            else:
                print(f"  Suspense: {raw_text} (Best: {best_match})")
                suspense_item = SuspenseItem(
                    raw_text=raw_text, # Keep original description
                    best_matches=[{"text": m[0], "score": m[1]} for m in matches],
                    confidence_score=float(best_match[1]) if best_match else 0.0
                )
                suspense_items.append(suspense_item)

    except Exception as e:
        print(f"Error in matcher: {e}")
        # In production, handle error gracefully
    finally:
        cur.close()
        conn.close()
        
    return {"matched_items": matched_items, "suspense_items": suspense_items}
