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
from jinja2 import Template
from puti.logs import logger_factory

lgr = logger_factory.default


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
        prompt=Template("I am now publishing the tweet: {{ previous_result.content }}")
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


async def run_ethan_workflow(ethan: Ethan, topic: str = None) -> Dict[str, Any]:
    """
    Run the Ethan workflow to generate and publish a tweet.
    
    Args:
        ethan: The Ethan role instance
        topic: Optional topic for the tweet. If None, Ethan will generate a topic
        
    Returns:
        Dictionary containing the results of each step in the workflow
    """
    try:
        # Create the workflow
        workflow = create_ethan_workflow(ethan)
        
        # Set initial context with topic if provided
        initial_context = {}
        if topic:
            initial_context["topic"] = topic
            lgr.info(f"Running Ethan workflow with provided topic: {topic}")
        else:
            lgr.info("Running Ethan workflow with auto-generated topic")
        
        # Run the workflow
        results = await workflow.run(initial_context=initial_context)
        
        # Log the results
        lgr.info(f"Ethan workflow completed successfully")
        
        return results
        
    except Exception as e:
        lgr.error(f"Error running Ethan workflow: {str(e)}")
        # Re-raise the exception so the caller can handle it
        raise
