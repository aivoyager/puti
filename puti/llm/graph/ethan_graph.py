"""
@Author: obstacles
@Time:  2023-06-18 14:22
@Description:  
"""
from puti.llm.roles.agents import Ethan
from puti.llm.actions.x_bot import GenerateTweetAction, PublishTweetAction
from puti.llm.workflow import Workflow
from puti.llm.graph import Vertex, Graph
from typing import Dict, Any
import asyncio
from puti.utils.files import save_json


def create_ethan_workflow(ethan: Ethan) -> Workflow:
    """
    Create a workflow for Ethan to generate and post a tweet.
    The workflow is simplified to two steps:
    1. Generate a topic, create, and review the tweet in a single action.
    2. Publish the final tweet.

    Args:
        ethan: The Ethan role instance.

    Returns:
        A Workflow instance configured for Ethan.
    """
    # 1. Define actions
    generate_and_review_action = GenerateTweetAction()
    publish_action = PublishTweetAction(
        prompt="I am now publishing the tweet: {{ previous_result.content }}"
    )
    
    # 2. Create workflow vertices
    generate_and_review_vertex = Vertex(id="generate_and_review", action=generate_and_review_action, role=ethan)
    
    publish_vertex = Vertex(
        id="publish_tweet", 
        action=publish_action,
        role=ethan,
    )
    
    # 3. Create the graph and add vertices
    graph = Graph()
    graph.add_vertex(generate_and_review_vertex)
    graph.add_vertex(publish_vertex)
    
    # 4. Define the workflow by adding edges
    graph.add_edge("generate_and_review", "publish_tweet")
    
    # The graph now starts with the combined generation/review step
    graph.set_start_vertex("generate_and_review")
    
    # 5. Create and return the workflow
    return Workflow(graph=graph)


async def run_ethan_workflow(ethan: Ethan, save_path: str = None) -> Dict[str, Any]:
    """
    Run the Ethan workflow to generate and post a tweet.
    
    Args:
        ethan: The Ethan role instance.
        save_path: Optional path to save results.
        
    Returns:
        The results of the workflow execution.
    """
    workflow = create_ethan_workflow(ethan)
    results = await workflow.run(max_steps=10)
    
    if save_path:
        save_json(results, save_path)
    
    return results


if __name__ == "__main__":
    ethan = Ethan()
    asyncio.run(run_ethan_workflow(ethan, "ethan_workflow_results.json"))
