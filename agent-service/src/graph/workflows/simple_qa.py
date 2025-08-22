from typing import Optional

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.registry.actions import ACTION_REGISTRY
from src.registry.nodes import NODE_REGISTRY
from src.registry.tools import TOOL_REGISTRY
from src.registry.workflows import register_workflow


@register_workflow("simple_qa")
class SimpleQAWorkflow(BaseModel):
    agent_state: BaseModel = Field(
        default=DocsPreProcessingStateModel,
        description="State of the AI agent, including user input and intent",
    )
    # These fields will be set during initialization
    workflow: Optional[StateGraph] = Field(default=None, exclude=True)
    graph: Optional[object] = Field(default=None, exclude=True)

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True

    def __init__(self, **data):
        super().__init__(**data)
        self._setup_workflow()

    def _setup_workflow(self):
        """Initialize and configure the workflow graph"""
        self.workflow = StateGraph(self.agent_state)
        self._add_nodes()
        self._setup_edges()
        self.graph = self.workflow.compile()

    def _add_nodes(self):
        """Add all nodes to the workflow"""
        # Add basic nodes

        self.workflow.add_node("entry", NODE_REGISTRY.get("conversation.entry")())

        document_tool = TOOL_REGISTRY.get("document.document_tool")()
        print(f"Document Tool: {document_tool}")
        simple_qa_node = NODE_REGISTRY.get("simple_qa.simple_qa")(tools=[document_tool])
        print(f"Simple QA Node: {simple_qa_node}")
        self.workflow.add_node(
            "simple_qa",
            simple_qa_node,
        )

        self.workflow.add_node(
            "document_tool",
            ToolNode([document_tool]),
        )

    def _setup_edges(self):
        """Configure all edges and entry point"""
        self.workflow.set_entry_point("entry")
        self.workflow.add_edge("entry", "simple_qa")
        self.workflow.add_conditional_edges(
            "simple_qa",
            ACTION_REGISTRY.get("should_continue"),
            {
                "continue": "document_tool",
                "end": END,
            },
        )
        self.workflow.add_edge("document_tool", "simple_qa")

    def get_graph(self):
        """Get the compiled graph"""
        return self.graph

    def invoke(self, input_data):
        """Execute the agent workflow"""
        if not self.graph:
            raise ValueError(
                "Graph not initialized. Please ensure workflow setup is complete."
            )
        return self.graph.invoke(input_data)

    def stream(self, input_data):
        """Stream the agent workflow execution"""
        if not self.graph:
            raise ValueError(
                "Graph not initialized. Please ensure workflow setup is complete."
            )
        return self.graph.stream(input_data)

    def reset_workflow(self):
        """Reset and reinitialize the workflow"""
        self._setup_workflow()

    def update_config(self, **kwargs):
        """Update configuration and reinitialize workflow"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self._setup_workflow()
