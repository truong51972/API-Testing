from src.models.agent.agent_state_model import AgentStateModel
from src.registry.actions import register_action


@register_action("route_intent")
def route_intent(state: AgentStateModel) -> str:
    """
    Function to determine next node based on detected intent.
    """
    intent = state.intent
    if intent == "product":
        return "product"
    elif intent == "make_order":
        return "make_order"
    elif intent == "greeting":
        return "greeting"
