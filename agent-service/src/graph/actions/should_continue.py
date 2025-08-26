from pydantic import BaseModel


def should_continue(state: BaseModel) -> str:
    """Determine if the workflow should continue or end.

    Args:
        state (BaseModel): The current state of the workflow.

    Returns:
        str: "continue" if the workflow should continue, "end" otherwise.
    """
    messages = getattr(state, "messages", None)

    if not messages or len(messages) == 0:
        return "end"
    last_message = messages[-1]

    # If there are no tool calls, then we finish
    if not last_message.tool_calls:
        return "end"
    # Otherwise if there is, we continue
    else:
        return "continue"
