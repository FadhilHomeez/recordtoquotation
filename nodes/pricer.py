from typing import Dict, Any, List
from state import RenovationState, Quotation, QuotationItem

def pricer_node(state: RenovationState) -> Dict[str, Any]:
    print("--- PRICER NODE ---")
    matched_items: List[QuotationItem] = state.get('matched_items', [])
    tenant_id = state.get('tenant_id')
    session_id = state.get('session_id')
    
    total_amount = 0.0
    
    for item in matched_items:
        # Check if unit price needs re-fetching?
        # In matcher we already fetched it. 
        # If we had complex logic (e.g. volume discounts), we would do it here.
        # For now, just recalculate subtotal to be safe.
        
        item.subtotal = item.quantity * item.unit_price
        total_amount += item.subtotal
        
    quotation = Quotation(
        tenant_id=tenant_id,
        session_id=session_id,
        items=matched_items,
        total_amount=total_amount
    )
    
    return {"quotation": quotation}
