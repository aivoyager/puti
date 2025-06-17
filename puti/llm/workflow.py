"""
@Author: obstacles
@Time:  2025-06-18 11:53
@Description:  Workflow utilities for graph-based execution
"""
from typing import Dict, Any, List, Optional, Union, Callable
import asyncio
import json
from pathlib import Path

from puti.llm.graph import Graph, Node, Edge
from puti.constant.llm import NodeState
from puti.logs import logger_factory

lgr = logger_factory.llm


async def run_graph(graph: Graph, **kwargs) -> Dict[str, Any]:
    """
    Run a graph workflow and return the results
    
    Args:
        graph: The graph to execute
        kwargs: Additional keyword arguments to pass to the graph's run method
        
    Returns:
        Dictionary mapping node IDs to their results
    """
    try:
        return await graph.run(**kwargs)
    except Exception as e:
        lgr.error(f"Error running graph: {str(e)}")
        raise


async def run_until_node(graph: Graph, target_node_id: str, **kwargs) -> Dict[str, Any]:
    """
    Run a graph until a specific node is reached
    
    Args:
        graph: The graph to execute
        target_node_id: The ID of the node to stop at
        kwargs: Additional keyword arguments to pass to the graph's run method
        
    Returns:
        Dictionary mapping node IDs to their results
    """
    if target_node_id not in graph.nodes:
        raise ValueError(f"Target node '{target_node_id}' not in graph")
        
    # Create a modified copy of the graph
    modified_graph = Graph(
        nodes=graph.nodes.copy(),
        edges=[edge for edge in graph.edges if edge.target != target_node_id],
        start_node_id=graph.start_node_id
    )
    
    # Add modified edges that stop at the target node
    for edge in graph.edges:
        if edge.target == target_node_id:
            modified_graph.edges.append(edge)
            
    return await run_graph(modified_graph, **kwargs)


async def run_subgraph(graph: Graph, start_node_id: str, end_node_ids: List[str], **kwargs) -> Dict[str, Any]:
    """
    Run a portion of a graph from a specified start node to specified end nodes
    
    Args:
        graph: The graph to execute
        start_node_id: The ID of the node to start from
        end_node_ids: List of node IDs to stop at
        kwargs: Additional keyword arguments to pass to the graph's run method
        
    Returns:
        Dictionary mapping node IDs to their results
    """
    if start_node_id not in graph.nodes:
        raise ValueError(f"Start node '{start_node_id}' not in graph")
        
    for node_id in end_node_ids:
        if node_id not in graph.nodes:
            raise ValueError(f"End node '{node_id}' not in graph")
            
    # Create a subgraph
    subgraph = Graph(
        nodes={k: v for k, v in graph.nodes.items()},
        edges=[edge for edge in graph.edges if edge.target not in end_node_ids or edge.source == start_node_id],
        start_node_id=start_node_id
    )
    
    return await run_graph(subgraph, **kwargs)


def save_graph_results(results: Dict[str, Any], file_path: str):
    """
    Save graph execution results to a file
    
    Args:
        results: Dictionary of results from graph execution
        file_path: Path to save results to
    """
    # Convert results to serializable format
    serializable_results = {}
    for node_id, result in results.items():
        if isinstance(result, Exception):
            serializable_results[node_id] = {
                "type": "error",
                "message": str(result),
                "class": result.__class__.__name__
            }
        else:
            try:
                # Try to convert to JSON-serializable object
                json.dumps(result)
                serializable_results[node_id] = result
            except (TypeError, OverflowError):
                # If not serializable, convert to string
                serializable_results[node_id] = str(result)
    
    # Create directory if it doesn't exist
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
    lgr.info(f"Graph results saved to {file_path}")


def load_graph_results(file_path: str) -> Dict[str, Any]:
    """
    Load graph execution results from a file
    
    Args:
        file_path: Path to load results from
        
    Returns:
        Dictionary of results
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
