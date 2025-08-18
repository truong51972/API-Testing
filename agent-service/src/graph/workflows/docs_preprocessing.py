from typing import Optional

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.registry.nodes import NODE_REGISTRY


class DocsPreprocessingWorkflow(BaseModel):
    collection_name: str = Field(
        default="e_commerce_ai", description="Collection name for vector database"
    )
    llm_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="Temperature for LLM generation"
    )

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

        self.workflow.add_node(
            "stopword_removal",
            NODE_REGISTRY.get("docs_preprocessing.stopword_removal")(),
        )
        self.workflow.add_node(
            "text_normalization",
            NODE_REGISTRY.get("docs_preprocessing.text_normalization")(),
        )
        self.workflow.add_node(
            "metadata_removal",
            NODE_REGISTRY.get("docs_preprocessing.metadata_removal")(),
        )
        self.workflow.add_node(
            "text_correction",
            NODE_REGISTRY.get("docs_preprocessing.text_correction")(),
        )
        self.workflow.add_node(
            "text_extractor",
            NODE_REGISTRY.get("docs_preprocessing.text_extractor")(),
        )
        self.workflow.add_node(
            "data_store",
            NODE_REGISTRY.get("docs_preprocessing.data_store")(),
        )

    def _setup_edges(self):
        """Configure all edges and entry point"""
        self.workflow.set_entry_point("entry")
        self.workflow.add_edge("entry", "text_extractor")
        self.workflow.add_edge("text_extractor", "text_normalization")
        self.workflow.add_edge("text_normalization", "text_correction")
        self.workflow.add_edge("text_correction", "metadata_removal")
        self.workflow.add_edge("metadata_removal", "stopword_removal")
        self.workflow.add_edge("stopword_removal", "data_store")
        self.workflow.add_edge("data_store", END)

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
