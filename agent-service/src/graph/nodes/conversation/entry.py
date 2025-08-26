# src.graph.nodes.docs_preprocessing.data_cleaning
from typing import Any, Dict

from langchain_core.messages import HumanMessage


class EntryNode:
    def __call__(self, state) -> Dict[str, Any]:

        return {
            "messages": [HumanMessage(content=state.user_input)],
        }
