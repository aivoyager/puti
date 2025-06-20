"""
@Author: obstacles
@Time:  2025-06-18 11:53
@Description:  Workflow utilities for graph-based execution
"""
from typing import Dict, Any, List, Optional, Annotated
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
    such as running the full graph, a subgraph, or until a specific vertex is reached.
    """
    graph: Graph = Field(..., description="The graph to be executed")
    results: Optional[Dict[Annotated[str, 'Vertex Id'], Any]] = Field(default=None, description="The results of the last workflow run")

    async def run(self, max_steps: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Run the full graph workflow and return the results.

        Args:
            max_steps: The maximum number of steps to execute.
            kwargs: Additional keyword arguments to pass to the graph's run method.

        Returns:
            A dictionary mapping vertex IDs to their results.
        """
        try:
            self.results = await self.graph.run(max_steps=max_steps, **kwargs)
            return self.results
        except Exception as e:
            lgr.error(f"Error running graph: {str(e)}")
            raise

    async def run_until_vertex(self, target_vertex_id: str, max_steps: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Run the graph until a specific vertex is reached, including the target vertex.
        Execution stops after the target vertex is completed.

        Args:
            target_vertex_id: The ID of the vertex to stop at.
            max_steps: The maximum number of steps to execute.
            kwargs: Additional keyword arguments to pass to the graph's run method.

        Returns:
            A dictionary mapping the executed vertex IDs to their results.
        """
        if target_vertex_id not in self.graph.vertices:
            raise ValueError(f"Target vertex '{target_vertex_id}' not in self.graph.vertices")

        modified_graph = Graph(
            vertices=self.graph.vertices.copy(),  # `vertices` and `graph roles` copy from
            edges=[edge for edge in self.graph.edges if edge.source != target_vertex_id],
            start_vertex_id=self.graph.start_vertex_id
        )
        
        workflow = Workflow(graph=modified_graph)
        self.results = await workflow.run(max_steps=max_steps, **kwargs)
        return self.results

    async def run_subgraph(self, start_vertex_id: str, end_vertex_ids: List[str], max_steps: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Run a portion of a graph (a "subgraph") from a specified start vertex
        until it is about to transition to one of the specified end vertices.
        
        Note: The end vertices themselves will not be executed.

        Args:
            start_vertex_id: The ID of the vertex where the execution should begin.
            end_vertex_ids: A list of vertex IDs that should act as termination points.
            max_steps: The maximum number of steps to execute.
            kwargs: Additional keyword arguments to pass to the graph's run method.

        Returns:
            A dictionary mapping the executed vertex IDs to their results.
        """
        if start_vertex_id not in self.graph.vertices:
            raise ValueError(f"Start vertex '{start_vertex_id}' not in self.graph.vertices")

        for vertex_id in end_vertex_ids:
            if vertex_id not in self.graph.vertices:
                raise ValueError(f"End vertex '{vertex_id}' not in self.graph.vertices")

        subgraph = Graph(
            vertices={k: v for k, v in self.graph.vertices.items()},
            edges=[edge for edge in self.graph.edges if edge.target not in end_vertex_ids],
            start_vertex_id=start_vertex_id
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
        for vertex_id, result in self.results.items():
            if isinstance(result, Exception):
                serializable_results[vertex_id] = {
                    "type": "error",
                    "message": str(result),
                    "class": result.__class__.__name__
                }
            else:
                try:
                    json.dumps(result)
                    serializable_results[vertex_id] = result
                except (TypeError, OverflowError):
                    serializable_results[vertex_id] = str(result)

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
