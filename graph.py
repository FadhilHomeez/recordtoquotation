from langgraph.graph import StateGraph, END
from state import RenovationState
from nodes.matcher import matcher_node
from nodes.pricer import pricer_node
from nodes.extractor import extractor_node
from nodes.guard import guard_node
from nodes.validator import validator_node

def guard_condition(state):
    """Check if guard node detected an error."""
    if state.get("error"):
        return END
    return "extractor"

def build_graph():
    workflow = StateGraph(RenovationState)
    
    # Add nodes
    workflow.add_node("guard", guard_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("matcher", matcher_node)
    workflow.add_node("pricer", pricer_node)
    workflow.add_node("validator", validator_node)
    
    # 3. Define Edges
    workflow.set_entry_point("guard")
    
    # Conditional edge from guard
    workflow.add_conditional_edges(
        "guard",
        guard_condition
    )
    
    workflow.add_edge("extractor", "matcher")
    workflow.add_edge("matcher", "pricer")
    workflow.add_edge("pricer", "validator")
    workflow.add_edge("validator", END)
    
    return workflow.compile()

if __name__ == "__main__":
    # Test compilation
    app = build_graph()
    print("Graph compiled successfully.")
    print(app.get_graph().draw_ascii())
