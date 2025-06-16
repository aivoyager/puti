from __future__ import annotations
from typing import Callable, Any, Dict, List, Optional
from enum import Enum
import asyncio

from pydantic import BaseModel, Field
from puti.llm.roles import Role
from abc import ABC, abstractmethod


class NodeState(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Action(BaseModel):

    name: str = Field(..., description="The name of the action")
    description: str = Field('', description="A brief description of the action")

    async def run(self, *, role: Role, **kwargs):
        # preprocessing action here ...
        resp = await role.run(action_name=self.name, action_description=self.description, **kwargs)
        # postprocessing action here ...
        return resp


class Node(BaseModel):

    id: str = Field(..., description="Unique identifier for the node")
    role: Role = Field(..., description="One node bind to one role")
    action: Action = Field(..., description="The action to be executed by the node")
    state: NodeState = Field(default=NodeState.PENDING, description="The current state of the node")
    result: Any = Field(default=None, description="The result of the node's action")

    class Config:
        arbitrary_types_allowed = True

    async def run(self, **kwargs):
        self.state = NodeState.RUNNING
        try:
            self.result = await self.action.run(role=self.role, **kwargs)
            self.state = NodeState.SUCCESS
        except Exception as e:
            self.state = NodeState.FAILED
            self.result = e
        return self.result


class Edge(BaseModel):
    source: str
    target: str
    condition: Optional[Callable[[Any], bool]] = None


class Graph(BaseModel):
    nodes: Dict[str, Node] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)
    start_node_id: Optional[str] = None

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def add_edge(self, source_id: str, target_id: str, condition: Optional[Callable[[Any], bool]] = None):
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("Source or target node not in graph")
        self.edges.append(Edge(source=source_id, target=target_id, condition=condition))

    def set_start_node(self, node_id: str):
        if node_id not in self.nodes:
            raise ValueError("Start node not in graph")
        self.start_node_id = node_id

    async def run(self):
        if not self.start_node_id:
            raise ValueError("Start node not set")

        current_node = self.nodes[self.start_node_id]
        while current_node:
            await current_node.run()
            if current_node.state == NodeState.FAILED:
                # Handle failure, maybe stop the graph or log
                print(f"Node {current_node.id} failed with result: {current_node.result}")
                break

            next_node = None
            for edge in self.edges:
                if edge.source == current_node.id:
                    if edge.condition is None or edge.condition(current_node.result):
                        next_node = self.nodes[edge.target]
                        break
            current_node = next_node

        return {node_id: node.result for node_id, node in self.nodes.items()} 