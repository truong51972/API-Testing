from typing import Optional

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.graph import nodes
from src.models import DocsPreProcessingStateModel


class DocsPreprocessingWorkflow(BaseModel):
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
        self.workflow.add_node(
            "document_normalization",
            nodes.DocumentNormalizationNode(),
        )
        self.workflow.add_node(
            "document_chunking",
            nodes.DocumentChunkingNode(),
        )
        self.workflow.add_node(
            "text_extractor",
            nodes.TextExtractorNode(),
        )
        self.workflow.add_node(
            "document_description",
            nodes.DocumentDescriptionNode(),
        )

    def _setup_edges(self):
        """Configure all edges and entry point"""
        self.workflow.set_entry_point("text_extractor")
        self.workflow.add_edge("text_extractor", "document_normalization")
        self.workflow.add_edge("document_normalization", "document_description")
        self.workflow.add_edge("document_description", "document_chunking")
        self.workflow.add_edge("document_chunking", END)

    def get_graph(self):
        """Get the compiled graph"""
        return self.graph

    def invoke(self, input_data) -> DocsPreProcessingStateModel:
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
