from typing import List, Optional, TypedDict, Dict, Any
from pydantic import BaseModel, Field

# Pydantic models for structured validation within the state
class QuotationItem(BaseModel):
    id: Optional[str] = None # DB ID if saved, or Price List ID
    description: str
    quantity: float
    unit: str
    unit_price: float
    subtotal: float
    confidence_score: float
    is_suspense: bool = False
    price_list_id: Optional[str] = None

class SuspenseItem(BaseModel):
    raw_text: str
    best_matches: List[Dict[str, Any]] # List of {text, score, id}
    confidence_score: float

class Quotation(BaseModel):
    tenant_id: str
    session_id: str
    items: List[QuotationItem] = []
    total_amount: float = 0.0

# LangGraph State
class RenovationState(TypedDict):
    # Input
    raw_items: List[str] # Extracted text items from user input/LLM
    tenant_id: str
    session_id: str
    
    # Processing
    matched_items: List[QuotationItem]
    suspense_items: List[SuspenseItem]
    
    # Output
    quotation: Optional[Quotation]
    validation_errors: List[str] # Warnings/Errors found during processing
