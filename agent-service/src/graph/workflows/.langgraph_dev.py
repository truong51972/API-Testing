from src.graph.workflows.docs_preprocessing import DocsPreprocessingWorkflow
from src.registry.nodes import scan_and_register_nodes

scan_and_register_nodes()
docs_preprocessing_workflow = DocsPreprocessingWorkflow(
    collection_name="test",
    llm_temperature=0.1,
)
docs_preprocessing_graph = docs_preprocessing_workflow.get_graph()
