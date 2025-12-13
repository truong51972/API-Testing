from typing import Optional

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.graph import nodes
from src.models import TestcasesGenStateModel


class TestCaseGenerationWorkflow(BaseModel):
    agent_state: BaseModel = Field(
        default=TestcasesGenStateModel,
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
            "document_preparator",
            nodes.DocumentPreparator(),
        )
        self.workflow.add_node(
            "testcase_generator_job",
            nodes.TestcaseGeneratorJob(),
        )
        self.workflow.add_node(
            "document_collector",
            nodes.DocumentCollector(),
        )
        self.workflow.add_node(
            "document_standardizer",
            nodes.DocumentStandardizer(),
        )
        self.workflow.add_node(
            "testcase_generator",
            nodes.TestCaseGenerator(),
        )
        # self.workflow.add_node(
        #     "api_info_collector",
        #     nodes.APIInfoCollector(),
        # )

    def _setup_edges(self):
        """Configure all edges and entry point"""
        self.workflow.set_entry_point("document_preparator")
        self.workflow.add_edge("document_preparator", "testcase_generator_job")
        self.workflow.add_conditional_edges(
            "testcase_generator_job",
            nodes.orchestrate_job,
            {"completed": END, "in_progress": "document_collector"},
        )
        self.workflow.add_edge("document_collector", "document_standardizer")
        # self.workflow.add_edge("document_standardizer", "api_info_collector")
        # self.workflow.add_edge("api_info_collector", "testcase_generator")
        self.workflow.add_edge("document_standardizer", "testcase_generator")
        self.workflow.add_edge("testcase_generator", "testcase_generator_job")

    def get_graph(self):
        """Get the compiled graph"""
        return self.graph

    def invoke(self, input_data) -> TestcasesGenStateModel:
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
