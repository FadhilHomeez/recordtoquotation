from typing import Dict, Any, List
from state import RenovationState
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re

def parse_json_markdown(text):
    """
    Parses a JSON string that might be wrapped in markdown code blocks.
    """
    try:
        # Strip markdown code blocks
        match = re.search(r"```(json)?(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(2)
        return json.loads(text.strip())
    except Exception:
        # Try raw
        return json.loads(text.strip())

def extractor_node(state: RenovationState) -> Dict[str, Any]:
    print("--- EXTRACTOR NODE ---")
    raw_input = state.get('raw_items', [])
    
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
Your task is to extract only the renovation work items from the transcript.
1. Ignore all timestamps (e.g., [00:00:00]), speaker names, and small talk.
2. Focus on the actual scope of work requested (e.g., hacking, flooring, carpentry).
3. Return ONLY a valid JSON list of strings.
4. Do not just copy the transcript lines. Extract the underlying items.

Example Input:
"I want to hack the kitchen wall and do vinyl flooring."
Example Output:
["Hacking of kitchen wall", "Supply and lay vinyl flooring"]
"""),
        ("user", "{transcript}")
    ])
    
    # Use StrOutputParser to get raw text, then handle JSON manually
    chain = prompt | llm | StrOutputParser()
    
    try:
        raw_output = chain.invoke({"transcript": transcript_text})
        print(f"LLM Raw Output: {raw_output[:100]}...") # Debug print
        extracted_items = parse_json_markdown(raw_output)
        
        if not isinstance(extracted_items, list):
            # If it's a single dict, wrap in list
            if isinstance(extracted_items, dict):
                 extracted_items = [extracted_items]
            else:
                 raise ValueError("Output is not a list")

        # Convert to ExtractedItem objects
        from state import ExtractedItem
        final_items = []
        for item in extracted_items:
            if isinstance(item, str):
                final_items.append(ExtractedItem(
                    description=item,
                    quantity=1.0,
                    unit='lot',
                    location='General'
                ))
            else:
                final_items.append(ExtractedItem(
                    description=item.get('description', 'Unknown Item'),
                    quantity=float(item.get('quantity', 1.0)),
                    unit=item.get('unit', 'lot'),
                    location=item.get('location', 'General')
                ))
        
        print(f"Extracted {len(final_items)} items.")
        return {"raw_items": final_items}
    except Exception as e:
        print(f"Error in extractor: {e}")
        # Fallback: return original split by newline if LLM fails
        return {"raw_items": [line.strip() for line in transcript_text.split('\n') if line.strip()]}
