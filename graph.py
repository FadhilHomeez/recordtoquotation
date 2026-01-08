from langgraph.graph import StateGraph, END
from state import RenovationState
from nodes.matcher import matcher_node
from nodes.pricer import pricer_node
from nodes.extractor import extractor_node

def build_graph():
    workflow = StateGraph(RenovationState)
    
    # Add nodes
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("matcher", matcher_node)
    workflow.add_node("pricer", pricer_node)
    
    # 3. Define Edges
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "matcher")
    workflow.add_edge("matcher", "pricer")
    workflow.add_edge("pricer", END) # (to price matched items) - Interpreted as a comment for this line
    # Even if there are only suspense items, we pass through pricer (which does nothing for them)
    # or we could skip pricer?
    # Simpler to just pass through pricer.
    
    return workflow.compile()

if __name__ == "__main__":
    # Test compilation
    app = build_graph()
    print("Graph compiled successfully.")
    print(app.get_graph().draw_ascii())
