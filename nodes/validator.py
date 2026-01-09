from typing import Dict, Any, List
from state import RenovationState

def validator_node(state: RenovationState) -> Dict[str, Any]:
    print("--- VALIDATOR NODE ---")
    
    errors = []
    
    matched_items = state.get('matched_items', [])
    suspense_items = state.get('suspense_items', [])
    quotation = state.get('quotation')
    raw_input = state.get('raw_items', [])
    
    # 1. Check for "Ghost" processing (Input exists but no output)
    if raw_input and not matched_items and not suspense_items:
        errors.append("Warning: Input received but no items were extracted or suspended.")
        
    # 2. Check Suspense Ratio
    total_items = len(matched_items) + len(suspense_items)
    if total_items > 0:
        suspense_ratio = len(suspense_items) / total_items
        if suspense_ratio > 0.5:
            errors.append(f"Warning: High suspense ratio ({suspense_ratio:.1%}). More than 50% of items could not be confidently matched.")
            
    # 3. Check Zero Total
    if quotation:
        if len(matched_items) > 0 and quotation.total_amount == 0:
            # Check if all items are actually zero priced (unlikely for matched items unless price list has 0)
            # Or if there's a logic error
            is_intentional_zero = all(item.unit_price == 0 for item in matched_items)
            if not is_intentional_zero:
                 errors.append("Error: Quotation total is $0.00 despite having matched items with potential value.")

    if errors:
        print("Validation Issues Found:")
        for err in errors:
            print(f" - {err}")
            
    return {"validation_errors": errors}
