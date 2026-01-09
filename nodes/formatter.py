from typing import Dict, Any
from state import RenovationState
import os

def formatter_node(state: RenovationState) -> Dict[str, Any]:
    print("--- FORMATTER NODE ---")
    matched_items = state.get('matched_items', [])
    suspense_items = state.get('suspense_items', [])
    errors = state.get('validation_errors', [])
    quotation = state.get('quotation')
    
    report = []
    report.append("# Renovation Quotation Summary")
    
    # 1. Final Quotation
    report.append("## Final Quotation")
    if matched_items:
        report.append("| Description | Location | Quantity | Unit | Unit Price | Subtotal |")
        report.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for item in matched_items:
            loc = item.location if item.location else "General"
            report.append(f"| {item.description} | {loc} | {item.quantity} | {item.unit} | ${item.unit_price:,.2f} | ${item.subtotal:,.2f} |")
            
        if quotation:
             report.append(f"\n**Total Amount: ${quotation.total_amount:,.2f}**")
    else:
        report.append("No items matched.")
        
    report.append("\n")
        
    # 2. Items Needing Review (Suspense)
    if suspense_items:
        report.append("## Items Needing Review")
        report.append("The following items could not be confidently matched to the price list:")
        report.append("| Original Text | Best Guess | Confidence |")
        report.append("| :--- | :--- | :--- |")
        for item in suspense_items:
            best = item.best_matches[0] if item.best_matches else {'text': 'None', 'score': 0}
            report.append(f"| {item.raw_text} | {best['text']} | {item.confidence_score}% |")
        report.append("\n")

    # 3. Validation Warnings
    if errors:
        report.append("## Validation Warnings")
        for err in errors:
            report.append(f"- ⚠️ {err}")
    
    report_str = "\n".join(report)
    
    file_path = os.path.abspath("quotation_summary.md")
    with open(file_path, "w") as f:
        f.write(report_str)
        
    print(f"Quotation summary generated at: {file_path}")
    return {"quotation_summary_path": file_path}
