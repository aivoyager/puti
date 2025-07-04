"""
@Author: obstacles
@Time: 2024-08-10
@Description: Tests for the context-aware reply functionality
"""
import pytest
import logging

from puti.llm.roles.agents import Ethan
from puti.llm.actions.x_bot import GetUnrepliedMentionsAction, ContextAwareReplyAction
from puti.llm.graph import Graph, Vertex
from puti.celery_queue.simplified_tasks import context_aware_reply_task

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
lgr = logging.getLogger("test_context_aware_reply")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_aware_reply_graph_integration():
    """
    Tests the full context-aware reply graph workflow with the real Twitter API.

    This test simulates the Celery task by:
    1. Creating a graph with GetUnrepliedMentionsAction followed by ContextAwareReplyAction.
    2. Running the entire graph.

    This provides an end-to-end test of the reply logic.

    To run this test:
       pytest test/x_bot/test_context_aware_reply.py::test_context_aware_reply_graph_integration -v -s
    """
    # Create Ethan instance with Twitter capabilities
    ethan = Ethan()

    # 1. Define actions for the graph, mirroring the Celery task setup
    get_mentions_action = GetUnrepliedMentionsAction(
        time_value=24,       # Look back 24 hours
        time_unit="hours",
        max_mentions=2       # Limit to 2 for testing to be quicker
    )
    reply_action = ContextAwareReplyAction(
        max_context_depth=5
    )

    # 2. Create vertices
    get_mentions_vertex = Vertex(
        id='get_unreplied_mentions',
        action=get_mentions_action,
        role=ethan
    )
    reply_vertex = Vertex(
        id='context_aware_reply',
        action=reply_action,
        role=ethan
    )

    # 3. Create and configure the graph
    graph = Graph()
    graph.add_vertices(get_mentions_vertex, reply_vertex)
    graph.add_edge('get_unreplied_mentions', 'context_aware_reply')
    graph.set_start_vertex('get_unreplied_mentions')

    # 4. Run the graph
    lgr.info("Running the context-aware reply graph...")
    result = await graph.run()

    # The first vertex result (list of IDs) might be useful for context.
    get_mentions_result = graph.get_vertex('get_unreplied_mentions').result
    if not get_mentions_result:
        pytest.skip("GetUnrepliedMentionsAction did not find any tweets to process. This is not a failure.")

    # Verify final result from the reply vertex
    lgr.info(f"Graph execution completed. Final result map: {result}")

    # The final result is a map of vertex_id -> result. We care about the last step's result.
    final_reply_result = result.get('context_aware_reply', '')

    assert "error" not in str(final_reply_result).lower()
    assert "Success" in str(final_reply_result)

    # Print the result for manual verification
    print(f"\nGraph-based context-aware reply test finished. Final summary: {final_reply_result}")


async def test_context_aware_reply_task():
    resp = context_aware_reply_task()
    print('')