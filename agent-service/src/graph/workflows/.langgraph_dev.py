import os

os.environ["ENVIRONMENT"] = "dev"

from src.graph import workflows

docs_preprocessing_workflow = workflows.DocsPreprocessingWorkflow()
docs_preprocessing_graph = docs_preprocessing_workflow.get_graph()

simple_qa_workflow = workflows.SimpleQAWorkflow()
simple_qa_graph = simple_qa_workflow.get_graph()
