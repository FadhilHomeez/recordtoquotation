from langgraph.graph import StateGraph, END
from state import RenovationState
from nodes.matcher import matcher_node
from nodes.pricer import pricer_node

def build_graph():
    workflow = StateGraph(RenovationState)
    
    # Add nodes
    workflow.add_node("matcher", matcher_node)
    workflow.add_node("pricer", pricer_node)
    
    # Define edges
    workflow.set_entry_point("matcher")
    
    # Matcher always goes to pricer (to price matched items)
    # Even if there are only suspense items, we pass through pricer (which does nothing for them)
    # or we could skip pricer?
    # Simpler to just pass through pricer.
    workflow.add_edge("matcher", "pricer")
    
    workflow.add_edge("pricer", END)
    
    return workflow.compile()

if __name__ == "__main__":
    # Test compilation
    app = build_graph()
    print("Graph compiled successfully.")
    print(app.get_graph().draw_ascii())
