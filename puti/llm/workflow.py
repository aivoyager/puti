"""
@Author: obstacles
@Time:  2025-06-18 11:53
@Description:  Workflow utilities for graph-based execution
"""
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from pydantic import BaseModel, Field

from puti.llm.graph import Graph
from puti.logs import logger_factory

lgr = logger_factory.llm


class Workflow(BaseModel):
    """
    Manages the execution of a graph-based workflow.

    This class encapsulates a graph and provides methods to run it in various ways,
    such as running the full graph, a subgraph, or until a specific node is reached.
    """
    graph: Graph = Field(..., description="The graph to be executed")
    results: Optional[Dict[str, Any]] = Field(default=None, description="The results of the last workflow run")

    async def run(self, max_steps: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Run the full graph workflow and return the results.

        Args:
            max_steps: The maximum number of steps to execute.
            kwargs: Additional keyword arguments to pass to the graph's run method.

        Returns:
            A dictionary mapping node IDs to their results.
        """
        try:
            self.results = await self.graph.run(max_steps=max_steps, **kwargs)
            return self.results
        except Exception as e:
            lgr.error(f"Error running graph: {str(e)}")
            raise

    async def run_until_node(self, target_node_id: str, max_steps: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Run the graph until a specific node is reached, including the target node.
        Execution stops after the target node is completed.

        Args:
            target_node_id: The ID of the node to stop at.
            max_steps: The maximum number of steps to execute.
            kwargs: Additional keyword arguments to pass to the graph's run method.

        Returns:
            A dictionary mapping the executed node IDs to their results.
        """
        if target_node_id not in self.graph.nodes:
            raise ValueError(f"Target node '{target_node_id}' not in self.graph.nodes")

        modified_graph = Graph(
            nodes=self.graph.nodes.copy(),
            edges=[edge for edge in self.graph.edges if edge.source != target_node_id],
            start_node_id=self.graph.start_node_id
        )
        
        workflow = Workflow(graph=modified_graph)
        self.results = await workflow.run(max_steps=max_steps, **kwargs)
        return self.results

    async def run_subgraph(self, start_node_id: str, end_node_ids: List[str], max_steps: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Run a portion of a graph (a "subgraph") from a specified start node
        until it is about to transition to one of the specified end nodes.
        
        Note: The end nodes themselves will not be executed.

        Args:
            start_node_id: The ID of the node where the execution should begin.
            end_node_ids: A list of node IDs that should act as termination points.
            max_steps: The maximum number of steps to execute.
            kwargs: Additional keyword arguments to pass to the graph's run method.

        Returns:
            A dictionary mapping the executed node IDs to their results.
        """
        if start_node_id not in self.graph.nodes:
            raise ValueError(f"Start node '{start_node_id}' not in self.graph.nodes")

        for node_id in end_node_ids:
            if node_id not in self.graph.nodes:
                raise ValueError(f"End node '{node_id}' not in self.graph.nodes")

        subgraph = Graph(
            nodes={k: v for k, v in self.graph.nodes.items()},
            edges=[edge for edge in self.graph.edges if edge.target not in end_node_ids],
            start_node_id=start_node_id
        )
        
        workflow = Workflow(graph=subgraph)
        self.results = await workflow.run(max_steps=max_steps, **kwargs)
        return self.results

    def save_results(self, file_path: str):
        """
        Save the results of the last workflow run to a file.

        Args:
            file_path: Path to save the results to.
        """
        if self.results is None:
            raise ValueError("No results to save. Run the workflow first.")

        serializable_results = {}
        for node_id, result in self.results.items():
            if isinstance(result, Exception):
                serializable_results[node_id] = {
                    "type": "error",
                    "message": str(result),
                    "class": result.__class__.__name__
                }
            else:
                try:
                    json.dumps(result)
                    serializable_results[node_id] = result
                except (TypeError, OverflowError):
                    serializable_results[node_id] = str(result)

        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)

        lgr.info(f"Graph results saved to {file_path}")

    @staticmethod
    def load_results(file_path: str) -> Dict[str, Any]:
        """
        Load graph execution results from a file.

        Args:
            file_path: Path to load results from.

        Returns:
            A dictionary of results.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
