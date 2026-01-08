from typing import Dict, Any, List
from state import RenovationState
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json
import os

def extractor_node(state: RenovationState) -> Dict[str, Any]:
    print("--- EXTRACTOR NODE ---")
    raw_input = state.get('raw_items', [])
    
    # If raw_input is already a list of short strings (from newline split), 
    # we might want to join them back for context if it looks like a conversation.
    # But strictly speaking, the API will pass a single string if we change api.py.
    # For compatibility, handle both list of strings or single string.
    
    transcript_text = ""
    if isinstance(raw_input, list):
        transcript_text = "\n".join(raw_input)
    else:
        transcript_text = str(raw_input)

    if not transcript_text.strip():
        return {"raw_items": []}

    print(f"Extracting items from transcript ({len(transcript_text)} chars)...")

    llm = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert renovation quantity surveyor. 
Your task is to extract renovation work items from a conversational transcript (which may contain Singlish or colloquialisms).
Return ONLY a JSON list of strings, where each string is a distinct renovation task mentioned.
Ignore filler talk like "Hi boss", "Can give quote", "confirm must do".
Focus on the actual work: e.g., "Wall Hacking", "Floor protection", "Dismantle toilet accessories".
Keep the extracted terms concise but descriptive enough to match a price list.
Example Output: ["Wall Hacking", "Supply and overlay vinyl flooring", "Painting of whole house"]
"""),
        ("user", "{transcript}")
    ])
    
    chain = prompt | llm | JsonOutputParser()
    
    try:
        extracted_items = chain.invoke({"transcript": transcript_text})
        print(f"Extracted {len(extracted_items)} items: {extracted_items}")
        # Update state with CLEANED items
        return {"raw_items": extracted_items}
    except Exception as e:
        print(f"Error in extractor: {e}")
        # Fallback: return original split by newline if LLM fails
        return {"raw_items": [line.strip() for line in transcript_text.split('\n') if line.strip()]}
