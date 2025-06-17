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
from puti.constant.llm import NodeState
from puti.logs import logger_factory
from puti.llm.messages import Message

lgr = logger_factory.llm


class Node(BaseModel):
    """A node in the workflow graph, representing a single unit of execution"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(..., description="Unique identifier for the node")
    role: Role = Field(..., description="Role that executes the node's action")
    action: Action = Field(..., description="The action to be executed by the node")
    state: NodeState = Field(default=NodeState.PENDING, description="The current state of the node")
    result: Any = Field(default=None, description="The result of the node's action")
    execution_time: Optional[float] = Field(default=None, description="Execution time in seconds")
    error: Optional[Exception] = Field(default=None, description="Error that occurred during execution")
    
    async def run(self, *args, **kwargs):
        """Execute the node's action and record the result"""
        self.state = NodeState.RUNNING
        start_time = datetime.now()
        
        try:
            # If role is a GraphRole, set the node_id
            if isinstance(self.role, GraphRole):
                self.role.set_node_id(self.id)
                
            # Execute the action
            self.result = await self.action.run(*args, **kwargs)
            self.state = NodeState.SUCCESS
            lgr.debug(f"Node '{self.id}' executed successfully")
        except Exception as e:
            self.state = NodeState.FAILED
            self.result = e
            self.error = e
            lgr.error(f"Node '{self.id}' failed with error: {str(e)}")
        finally:
            end_time = datetime.now()
            self.execution_time = (end_time - start_time).total_seconds()
            
        return self.result


class Edge(BaseModel):
    """Connection between two nodes with an optional condition"""
    source: str
    target: str
    condition: Optional[Callable[[Any], bool]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the edge")
    
    def matches(self, value: Any) -> bool:
        """Check if the value satisfies the condition"""
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
    
    nodes: Dict[str, Node] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)
    start_node_id: Optional[str] = None
    shared_context: Dict[str, Any] = Field(default_factory=dict, description="Shared context across all nodes")
    execution_history: List[str] = Field(default_factory=list, description="History of node execution order")
    
    def add_node(self, node: Node):
        """Add a node to the graph"""
        self.nodes[node.id] = node
        
        # If node has a GraphRole, set the shared context
        if isinstance(node.role, GraphRole):
            node.role.set_graph_context(self.shared_context)

    def add_edge(self, source_id: str, target_id: str, condition: Optional[Callable[[Any], bool]] = None, 
                metadata: Optional[Dict[str, Any]] = None):
        """Add an edge between two nodes with an optional condition"""
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError(f"Source node '{source_id}' or target node '{target_id}' not in graph")
            
        edge_metadata = metadata or {}
        self.edges.append(Edge(source=source_id, target=target_id, condition=condition, metadata=edge_metadata))

    def set_start_node(self, node_id: str):
        """Set the starting node for the workflow"""
        if node_id not in self.nodes:
            raise ValueError(f"Start node '{node_id}' not in graph")
        self.start_node_id = node_id
        
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by its ID"""
        return self.nodes.get(node_id)
        
    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        """Get all edges leaving from a node"""
        return [edge for edge in self.edges if edge.source == node_id]
        
    def get_successor_nodes(self, node_id: str) -> List[Node]:
        """Get all successor nodes for a given node"""
        edges = self.get_outgoing_edges(node_id)
        return [self.nodes[edge.target] for edge in edges]
        
    def reset(self):
        """Reset the graph to its initial state"""
        for node in self.nodes.values():
            node.state = NodeState.PENDING
            node.result = None
            node.error = None
            node.execution_time = None
        self.execution_history = []
        
    @model_validator(mode='after')
    def validate_graph(self):
        """Validate that the graph is properly structured"""
        # Check for cycles (simple validation)
        visited = set()
        
        def has_cycle(node_id: str, path: Set[str]) -> bool:
            if node_id in path:
                return True
            if node_id in visited:
                return False
                
            visited.add(node_id)
            path.add(node_id)
            
            for edge in self.get_outgoing_edges(node_id):
                if has_cycle(edge.target, path):
                    return True
                    
            path.remove(node_id)
            return False
            
        if self.start_node_id and has_cycle(self.start_node_id, set()):
            lgr.warning("Graph contains cycles, which may cause infinite loops")
            
        return self

    async def run(self, *args, **kwargs):
        """
        Execute the graph workflow starting from the start node.
        
        Args:
            args: Positional arguments to pass to the first node
            kwargs: Keyword arguments to pass to all nodes
            
        Returns:
            A dictionary mapping node IDs to their results
        """
        if not self.start_node_id:
            raise ValueError("Start node not set")
            
        self.reset()
        self.shared_context.clear()
        
        current_node_id = self.start_node_id
        # Initial input for the very first node, if provided
        initial_msg = kwargs.pop('msg', None)
        last_node_result = Message.from_any(initial_msg) if initial_msg else None
        results_map = {}

        while current_node_id:
            current_node = self.nodes[current_node_id]
            self.execution_history.append(current_node_id)
            
            # Prepare arguments for the node
            node_kwargs = kwargs.copy()
            if last_node_result is not None:
                # Pass the Message object directly as previous_result
                node_kwargs['previous_result'] = last_node_result

            # Execute the node
            await current_node.run(**node_kwargs)
            
            # Store the result, ensuring it's a Message object for consistency
            if isinstance(current_node.result, Message):
                results_map[current_node_id] = current_node.result.content  # Store content for results_map
                last_node_result = current_node.result
            else:
                # If the result is not already a Message, convert it
                converted_result_message = Message.from_any(current_node.result)
                results_map[current_node_id] = converted_result_message.content
                last_node_result = converted_result_message
            
            # Update shared context
            self.shared_context[current_node_id] = last_node_result

            # Stop if the node failed
            if current_node.state == NodeState.FAILED:
                lgr.error(f"Node {current_node.id} failed with result: {current_node.result}")
                break

            # Find the next node based on edges and conditions
            next_node_id = None
            for edge in self.edges:
                if edge.source == current_node_id:
                    if edge.matches(current_node.result): # Use original result for condition check
                        next_node_id = edge.target
                        break
                        
            current_node_id = next_node_id

        return results_map
        
    async def run_parallel(self, node_ids: List[str], *args, **kwargs) -> Dict[str, Any]:
        """
        Execute multiple nodes in parallel and return their results.
        
        Args:
            node_ids: List of node IDs to execute in parallel
            args: Positional arguments to pass to all nodes
            kwargs: Keyword arguments to pass to all nodes
            
        Returns:
            Dictionary mapping node IDs to their results
        """
        # Validate node IDs
        invalid_nodes = [node_id for node_id in node_ids if node_id not in self.nodes]
        if invalid_nodes:
            raise ValueError(f"Invalid node IDs: {invalid_nodes}")
            
        # Execute nodes in parallel
        tasks = [self.nodes[node_id].run(*args, **kwargs) for node_id in node_ids]
        await asyncio.gather(*tasks)
        
        # Collect results
        return {node_id: self.nodes[node_id].result for node_id in node_ids}
        
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph execution"""
        total_time = sum(node.execution_time or 0 for node in self.nodes.values())
        executed_nodes = [node for node in self.nodes.values() if node.state != NodeState.PENDING]
        success_nodes = [node for node in executed_nodes if node.state == NodeState.SUCCESS]
        failed_nodes = [node for node in executed_nodes if node.state == NodeState.FAILED]
        
        return {
            "total_execution_time": total_time,
            "executed_node_count": len(executed_nodes),
            "success_node_count": len(success_nodes),
            "failed_node_count": len(failed_nodes),
            "execution_history": self.execution_history,
            "average_node_time": total_time / len(executed_nodes) if executed_nodes else 0
        }
