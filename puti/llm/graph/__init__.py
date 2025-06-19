"""
@Author: obstacles
@Time:  2025-06-18 11:53
@Description:  Graph-based workflow system for orchestrating role interactions
"""
from __future__ import annotations
from typing import Callable, Any, Dict, List, Optional, Set, Union, Tuple
import asyncio
import logging
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, model_validator
from puti.llm.roles import Role, GraphRole
from puti.llm.actions import Action
from puti.constant.llm import NodeState as VertexState
from puti.logs import logger_factory
from puti.llm.messages import Message

lgr = logger_factory.llm


class Vertex(BaseModel):
    """A vertex in the workflow graph, representing a single unit of execution"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(..., description="Unique identifier for the vertex")
    role: Role = Field(..., description="Role that executes the vertex's action")
    action: Action = Field(..., description="The action to be executed by the vertex")
    state: VertexState = Field(default=VertexState.PENDING, description="The current state of the vertex")
    result: Any = Field(default=None, description="The result of the vertex's action")
    execution_time: Optional[float] = Field(default=None, description="Execution time in seconds")
    error: Optional[Exception] = Field(default=None, description="Error that occurred during execution")
    
    async def run(self, *args, **kwargs):
        """Execute the vertex's action and record the result"""
        self.state = VertexState.RUNNING
        start_time = datetime.now()
        
        try:
            # If role is a GraphRole, set the vertex_id
            if isinstance(self.role, GraphRole):
                self.role.set_vertex_id(self.id)
                
            # Execute the action with this vertex's role
            self.result = await self.action.run(role=self.role, *args, **kwargs)
            self.state = VertexState.SUCCESS
            lgr.debug(f"Vertex '{self.id}' executed successfully")
        except Exception as e:
            self.state = VertexState.FAILED
            self.result = e
            self.error = e
            lgr.error(f"Vertex '{self.id}' failed with error: {str(e)}")
        finally:
            end_time = datetime.now()
            self.execution_time = (end_time - start_time).total_seconds()
            
        return self.result

    @property
    def is_successful(self) -> bool:
        """Check if the vertex executed successfully."""
        return self.state == VertexState.SUCCESS


class Edge(BaseModel):
    """Connection between two vertices with an optional condition"""
    source: str
    target: str
    condition: Optional[Callable[[Any], bool]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the edge")
    
    def matches(self, value: Any) -> bool:
        """Check if the value satisfies the condition"""
        if isinstance(value, Message):
            value = value.content
        if self.condition is None:
            return True
        try:
            return self.condition(value)
        except Exception as e:
            lgr.error(f"Edge condition evaluation failed: {str(e)}")
            return False


class Graph(BaseModel):
    """
    A directed graph representing a workflow of actions and conditions.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    vertices: Dict[str, Vertex] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)
    start_vertex_id: Optional[str] = None
    shared_context: Dict[str, Any] = Field(default_factory=dict, description="Shared context across all vertices")
    execution_history: List[str] = Field(default_factory=list, description="History of vertex execution order")
    
    def add_vertex(self, vertex: Vertex):
        """Add a vertex to the graph"""
        self.vertices[vertex.id] = vertex
        
        # If vertex has a GraphRole, set the shared context
        if isinstance(vertex.role, GraphRole):
            vertex.role.set_graph_context(self.shared_context)

    def add_edge(self, source_id: str, target_id: str, condition: Optional[Callable[[Any], bool]] = None, 
                metadata: Optional[Dict[str, Any]] = None):
        """Add an edge between two vertices with an optional condition"""
        if source_id not in self.vertices or target_id not in self.vertices:
            raise ValueError(f"Source vertex '{source_id}' or target vertex '{target_id}' not in graph")
            
        edge_metadata = metadata or {}
        self.edges.append(Edge(source=source_id, target=target_id, condition=condition, metadata=edge_metadata))

    def set_start_vertex(self, vertex_id: str):
        """Set the starting vertex for the workflow"""
        if vertex_id not in self.vertices:
            raise ValueError(f"Start vertex '{vertex_id}' not in graph")
        self.start_vertex_id = vertex_id
        
    def get_vertex(self, vertex_id: str) -> Optional[Vertex]:
        """Get a vertex by its ID"""
        return self.vertices.get(vertex_id)
        
    def get_outgoing_edges(self, vertex_id: str) -> List[Edge]:
        """Get all edges leaving from a vertex"""
        return [edge for edge in self.edges if edge.source == vertex_id]
        
    def get_successor_vertices(self, vertex_id: str) -> List[Vertex]:
        """Get all successor vertices for a given vertex"""
        edges = self.get_outgoing_edges(vertex_id)
        return [self.vertices[edge.target] for edge in edges]
        
    def reset(self):
        """Reset the graph to its initial state"""
        for vertex in self.vertices.values():
            vertex.state = VertexState.PENDING
            vertex.result = None
            vertex.error = None
            vertex.execution_time = None
        self.execution_history = []
        
    @model_validator(mode='after')
    def validate_graph(self):
        """Validate that the graph is properly structured"""
        # Check for cycles (simple validation)
        visited = set()
        
        def has_cycle(vertex_id: str, path: Set[str]) -> bool:
            if vertex_id in path:
                return True
            if vertex_id in visited:
                return False
                
            visited.add(vertex_id)
            path.add(vertex_id)
            
            for edge in self.get_outgoing_edges(vertex_id):
                if has_cycle(edge.target, path):
                    return True
                    
            path.remove(vertex_id)
            return False
            
        if self.start_vertex_id and has_cycle(self.start_vertex_id, set()):
            lgr.warning("Graph contains cycles, which may cause infinite loops. Use 'max_steps' in the run method.")
            
        return self

    async def run(self, *args, max_steps: int = 10, **kwargs):
        """
        Execute the graph workflow starting from the start vertex.
        
        Args:
            args: Positional arguments to pass to the first vertex
            max_steps: The maximum number of vertices/steps to execute to prevent infinite loops. Defaults to 10.
            kwargs: Keyword arguments to pass to all vertices
            
        Returns:
            A dictionary mapping vertex IDs to their results
        """
        if not self.start_vertex_id:
            raise ValueError("Start vertex not set")
            
        self.reset()
        self.shared_context.clear()
        
        current_vertex_id = self.start_vertex_id
        # Initial input for the very first vertex, if provided
        initial_prompt = kwargs.pop('prompt', None)
        last_vertex_result = Message.from_any(initial_prompt) if initial_prompt else None
        results_map = {}

        while current_vertex_id and len(self.execution_history) < max_steps:
            current_vertex = self.vertices[current_vertex_id]
            self.execution_history.append(current_vertex_id)
            
            # Prepare arguments for the vertex
            vertex_kwargs = kwargs.copy()
            if last_vertex_result is not None:
                # Pass the Message object directly as previous_result
                vertex_kwargs['previous_result'] = last_vertex_result
            if len(self.execution_history) == 1 and initial_prompt:
                vertex_kwargs['prompt'] = initial_prompt
            
            vertex_result = await current_vertex.run(*args, **vertex_kwargs)
            results_map[current_vertex_id] = vertex_result
            
            # If vertex failed, store the exception and stop
            if not current_vertex.is_successful:
                results_map[current_vertex_id] = current_vertex.result
                lgr.error(f"Stopping graph execution due to failure in vertex '{current_vertex.id}'.")
                break
                
            # Store the result, ensuring it's a Message object for consistency
            if isinstance(vertex_result, Message):
                results_map[current_vertex_id] = vertex_result.content  # Store content for results_map
                last_vertex_result = vertex_result
            else:
                # If the result is not already a Message, convert it
                converted_result_message = Message.from_any(vertex_result)
                results_map[current_vertex_id] = converted_result_message.content
                last_vertex_result = converted_result_message
            
            # Update shared context
            self.shared_context[current_vertex_id] = last_vertex_result

            # Find the next vertex to execute based on conditions
            next_vertex_id = None
            outgoing_edges = self.get_outgoing_edges(current_vertex_id)
            
            if not outgoing_edges:
                lgr.info(f"Vertex '{current_vertex_id}' is a terminal vertex. Halting execution.")
                break
            
            # If there's only one unconditional edge, take it
            if len(outgoing_edges) == 1 and outgoing_edges[0].condition is None:
                next_vertex_id = outgoing_edges[0].target
            else:
                # Otherwise, evaluate conditions
                for edge in outgoing_edges:
                    if edge.matches(vertex_result):
                        next_vertex_id = edge.target
                        lgr.debug(f"Condition for edge '{current_vertex_id}' -> '{next_vertex_id}' met.")
                        break  # Take the first matching edge
            
            current_vertex_id = next_vertex_id
            last_vertex_result = vertex_result

        return results_map
        
    async def run_parallel(self, vertex_ids: List[str], *args, **kwargs) -> Dict[str, Any]:
        """
        Execute multiple vertices in parallel and return their results.
        
        Args:
            vertex_ids: List of vertex IDs to execute in parallel
            args: Positional arguments to pass to all vertices
            kwargs: Keyword arguments to pass to all vertices
            
        Returns:
            Dictionary mapping vertex IDs to their results
        """
        # Validate vertex IDs
        invalid_vertices = [vertex_id for vertex_id in vertex_ids if vertex_id not in self.vertices]
        if invalid_vertices:
            raise ValueError(f"Invalid vertex IDs: {invalid_vertices}")
            
        # Execute vertices in parallel
        tasks = [self.vertices[vertex_id].run(*args, **kwargs) for vertex_id in vertex_ids]
        await asyncio.gather(*tasks)
        
        # Collect results
        return {vertex_id: self.vertices[vertex_id].result for vertex_id in vertex_ids}
        
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph execution"""
        total_time = sum(vertex.execution_time or 0 for vertex in self.vertices.values())
        executed_vertices = [vertex for vertex in self.vertices.values() if vertex.state != VertexState.PENDING]
        success_vertices = [vertex for vertex in executed_vertices if vertex.state == VertexState.SUCCESS]
        failed_vertices = [vertex for vertex in executed_vertices if vertex.state == VertexState.FAILED]
        
        return {
            "total_execution_time": total_time,
            "executed_vertex_count": len(executed_vertices),
            "success_vertex_count": len(success_vertices),
            "failed_vertex_count": len(failed_vertices),
            "execution_history": self.execution_history,
            "average_vertex_time": total_time / len(executed_vertices) if executed_vertices else 0
        }
