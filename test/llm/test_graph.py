"""
@Author: obstacles
@Time:  2025-06-18 11:54
@Description:  Tests for the Graph implementation
"""
import asyncio
import pytest
from puti.llm.graph import Graph, Node, Edge, NodeState
from puti.llm.roles import Role, GraphRole
from puti.llm.roles.agents import Alex
from puti.llm.tools.calculator import CalculatorTool
from puti.llm.messages import Message, AssistantMessage
from puti.llm.actions import Action
from unittest.mock import AsyncMock, patch
from typing import Dict, Any
import jinja2

from puti.llm.workflow import Workflow


# Note: These tests interact with a live LLM and may require an API key
# (e.g., OPENAI_API_KEY) to be set in the environment.


@pytest.mark.asyncio
async def test_sequential_graph():
    """Tests a simple sequential graph where one role's output is the next one's input."""
    # 1. Define roles
    role1 = GraphRole(name="Role1", identity="helpful assistant", goal="Just reply with the user's message.")
    role2 = GraphRole(name="Role2", identity="helpful assistant", goal="repeats the input you receive.")

    # 2. Define actions for nodes
    action1 = Action(name="action1", description="test action1", role=role1, msg='hello world')
    
    # 使用字符串占位符方式，自动引用前一节点的结果
    action2 = Action(
        name="action2",
        description="test action2",
        role=role2,
        msg=jinja2.Template("Received: {{ previous_result.content }}. Now repeating it.")
    )

    # 3. Create nodes
    node1 = Node(id="node1", role=role1, action=action1)
    node2 = Node(id="node2", role=role2, action=action2)

    # 4. Create graph
    graph = Graph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge("node1", "node2")
    graph.set_start_node("node1")

    # 5. Run the graph
    results = await graph.run(msg='hello world')

    # 6. Assert results (flexible assertions for LLM output)
    assert "hello world" in results["node1"].lower()
    node2_output_lower = results["node2"].lower()
    assert "hello world" in node2_output_lower


@pytest.mark.asyncio
async def test_sequential_graph_with_multiple_placeholders():
    """Tests a graph with multiple placeholders in action messages."""
    # 1. Define roles
    role1 = GraphRole(name="Role1", identity="helpful assistant", goal="Just reply with the user's message.")
    role2 = GraphRole(name="Role2", identity="helpful assistant", goal="combines inputs")

    # 2. Define actions for nodes
    action1 = Action(name="action1", description="test action1", role=role1, msg='hello world')
    
    # 使用多个占位符，包括自定义参数和前一节点结果
    action2 = Action(
        name="action2", 
        description="test action2", 
        role=role2, 
        msg=jinja2.Template("Previous result: {{ previous_result.content }}. Custom param: {{ custom_param }}.")
    )

    # 3. Create nodes
    node1 = Node(id="node1", role=role1, action=action1)
    node2 = Node(id="node2", role=role2, action=action2)

    # 4. Create graph
    graph = Graph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge("node1", "node2")
    graph.set_start_node("node1")

    # 5. Run the graph with a custom parameter
    results = await graph.run(msg='hello world', custom_param='test value')

    # 6. Assert results
    assert "hello world" in results["node1"].lower()
    node2_output_lower = results["node2"].lower()
    assert "hello world" in node2_output_lower
    assert "test value" in node2_output_lower


@pytest.mark.asyncio
async def test_conditional_graph():
    """Tests a graph with conditional branching."""
    # 1. Define roles
    role1 = Role(name="Role1", identity="You are a decision maker. If the input is 'a', say 'path_a'. If it's 'b', say 'path_b'.")
    role_a = Role(name="RoleA", identity="You are Role A. Announce you have been activated.")
    role_b = Role(name="RoleB", identity="You are Role B. Announce you have been activated.")

    # 2. Define actions
    action1 = Action(name="action1", description="decision action", role=role1, msg="a")
    
    # 使用字符串占位符替代函数
    action_a = Action(
        name="action_a",
        description="Process branch A",
        role=role_a,
        msg=jinja2.Template("Triggered by: {{ previous_result.content }}")
    )
    
    action_b = Action(
        name="action_b",
        description="Process branch B",
        role=role_b,
        msg=jinja2.Template("Triggered by: {{ previous_result.content }}")
    )

    # 3. Create nodes
    node1 = Node(id="node1", role=role1, action=action1)
    node_a = Node(id="nodeA", role=role_a, action=action_a)
    node_b = Node(id="nodeB", role=role_b, action=action_b)

    # 4. Create graph
    graph = Graph()
    graph.add_node(node1)
    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_edge("node1", "nodeA", condition=lambda x: "path_a" in x.lower())
    graph.add_edge("node1", "nodeB", condition=lambda x: "path_b" in x.lower())
    graph.set_start_node("node1")

    # 5. Run graph
    results = await graph.run()

    # 6. Assert results
    assert "path_a" in results["node1"].lower()


@pytest.mark.asyncio
async def test_graph_error_handling():
    """Tests that the graph stops execution on a failed node."""
    # 1. Define roles
    failing_role = Role(name="FailingRole")
    # Mock the role's run method to simulate a failure
    failing_role.run = AsyncMock(side_effect=ValueError("Something went wrong"))
    role2 = Role(name="Role2")

    # 2. Define actions, with one designed to fail
    action1 = Action(name="failing_action", role=failing_role, msg="This will fail")
    action2 = Action(name="action2", role=role2, msg="This action should not run")

    # 3. Create nodes
    node1 = Node(id="node1", role=failing_role, action=action1)
    node2 = Node(id="node2", role=role2, action=action2)

    # 4. Create graph
    graph = Graph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge("node1", "node2")
    graph.set_start_node("node1")

    # 5. Run graph
    results = await graph.run()

    # 6. Assert results
    assert isinstance(results["node1"], ValueError)
    assert "node2" not in results
    assert node1.state == NodeState.FAILED
    assert not node1.is_successful
    assert node2.state == NodeState.PENDING


@pytest.mark.asyncio
async def test_graph_with_tool_usage():
    """Tests a graph where a role uses a tool."""
    # 1. Define roles
    planner = Alex(name="Planner", identity="You are a planner. Your goal is to answer questions. Use your tools if necessary.")
    executor = Role(name="Executor", identity="You are an executor. Your goal is to report the results you are given.")

    # 2. Equip the planner role with a tool
    planner.set_tools([CalculatorTool])

    # 3. Define actions
    plan_action = Action(
        name="plan_action",
        description="Plan and execute a calculation",
        role=planner,
        msg="迪士尼有什么新情报"
    )

    execute_action = Action(
        name="execute_action",
        description="Report the final result",
        role=executor,
        msg=jinja2.Template("The final result is: {{ previous_result.content }}")
    )

    # 4. Create nodes
    plan_node = Node(id="plan_node", role=planner, action=plan_action)
    execute_node = Node(id="execute_node", role=executor, action=execute_action)

    # 5. Create graph
    graph = Graph()
    graph.add_node(plan_node)
    graph.add_node(execute_node)
    graph.add_edge("plan_node", "execute_node")
    graph.set_start_node("plan_node")

    # 6. Run the graph
    results = await graph.run()

    # 7. Assert results
    # The planner's output should be a message containing the tool's result.
    # We check if the content of that message contains '125'.
    # assert "125" in results["plan_node"]

    # The executor should report the result it was given.
    # Its output should also contain '125'.
    # assert "125" in results["execute_node"]
    assert plan_node.is_successful
    assert execute_node.is_successful


@pytest.mark.asyncio
async def test_complex_graph():
    """Tests a more complex graph with multiple branches and conditions."""
    # 1. Create mock roles and their responses
    role1 = Role(name="role1")
    role1.run = AsyncMock(return_value=AssistantMessage(content="Decision A"))

    role2a = Role(name="role2a")
    role2a.run = AsyncMock(return_value=AssistantMessage(content="Result A"))

    role2b = Role(name="role2b")
    role2b.run = AsyncMock(return_value=AssistantMessage(content="Result B"))

    role3 = Role(name="role3")
    role3.run = AsyncMock(return_value=AssistantMessage(content="Combined result"))

    # 2. Create actions that use these roles
    action1 = Action(name="action1", role=role1, msg="start")
    action2a = Action(name="action2a", role=role2a, msg="go to a")
    action2b = Action(name="action2b", role=role2b, msg="go to b")
    action3 = Action(name="action3", role=role3, msg="end")

    # 3. Create nodes
    node1 = Node(id="start", role=role1, action=action1)
    node2a = Node(id="branch_a", role=role2a, action=action2a)
    node2b = Node(id="branch_b", role=role2b, action=action2b)
    node3 = Node(id="end", role=role3, action=action3)

    # 4. Create graph with multiple paths
    graph = Graph()
    graph.add_node(node1)
    graph.add_node(node2a)
    graph.add_node(node2b)
    graph.add_node(node3)

    # Add edges with conditions. The condition is checked against the result of the source node's action.
    graph.add_edge("start", "branch_a", condition=lambda x: "A" in x)
    graph.add_edge("start", "branch_b", condition=lambda x: "B" in x)
    graph.add_edge("branch_a", "end")
    graph.add_edge("branch_b", "end")

    graph.set_start_node("start")

    # 5. Run graph
    results = await graph.run()

    # 6. Assert results
    assert results["start"] == "Decision A"
    assert results["branch_a"] == "Result A"
    assert "branch_b" not in results
    assert results["end"] == "Combined result"

    # Verify correct node states
    assert node1.is_successful
    assert node2a.is_successful
    assert not node2b.is_successful
    assert node3.is_successful


@pytest.mark.asyncio
async def test_graph_run_workflow():
    """Tests that the workflow.run function correctly executes a graph."""
    # 1. Create a simple graph
    role = Role(name="TestRole")
    # Mock the role's execution to return a predictable result without a live API call
    role.run = AsyncMock(return_value=AssistantMessage(content="Success"))

    action = Action(name="test_action", role=role, msg="test")
    node = Node(id="test_node", role=role, action=action)

    graph = Graph()
    graph.add_node(node)
    graph.set_start_node("test_node")

    # 2. Run the graph using the workflow utility
    workflow = Workflow(graph=graph)
    result = await workflow.run()

    # 3. Verify that the graph ran and produced the expected result
    assert result == {"test_node": "Success"}
    assert node.is_successful


@pytest.mark.asyncio
async def test_run_until_node():
    """Tests running a graph until a specific node is reached."""
    # 1. Setup graph
    role_a = Role(name="RoleA")
    role_a.run = AsyncMock(return_value=AssistantMessage(content="Result A"))
    role_b = Role(name="RoleB")
    role_b.run = AsyncMock(return_value=AssistantMessage(content="Result B"))
    role_c = Role(name="RoleC")
    role_c.run = AsyncMock(return_value=AssistantMessage(content="Result C"))

    action_a = Action(name="action_a", role=role_a, msg="start")
    action_b = Action(name="action_b", role=role_b, msg="continue")
    action_c = Action(name="action_c", role=role_c, msg="end")

    node_a = Node(id="A", role=role_a, action=action_a)
    node_b = Node(id="B", role=role_b, action=action_b)
    node_c = Node(id="C", role=role_c, action=action_c)

    graph = Graph()
    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_node(node_c)
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.set_start_node("A")

    # 2. Run until node 'B', which should execute A and B, but not C.
    workflow = Workflow(graph=graph)
    results = await workflow.run_until_node("B")

    # 3. Assert that execution stopped after node B
    assert "A" in results
    assert "B" in results
    assert "C" not in results  # C should not have run
    assert node_a.is_successful
    assert node_b.is_successful
    assert node_c.state == NodeState.PENDING  # C should be pending


@pytest.mark.asyncio
async def test_run_subgraph():
    """Tests running a subgraph from a start node to an end node."""
    # 1. Setup graph
    role = Role(name="TestRole")
    role.run = AsyncMock(side_effect=lambda msg, **kwargs: AssistantMessage(content=f"Processed {msg}"))

    action_a = Action(name="action_a", role=role, msg="A")
    action_b = Action(name="action_b", role=role, msg="B")
    action_c = Action(name="action_c", role=role, msg="C")
    action_d = Action(name="action_d", role=role, msg="D")

    node_a = Node(id="A", role=role, action=action_a)
    node_b = Node(id="B", role=role, action=action_b)
    node_c = Node(id="C", role=role, action=action_c)
    node_d = Node(id="D", role=role, action=action_d)

    graph = Graph()
    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_node(node_c)
    graph.add_node(node_d)
    graph.add_edge("A", "B")
    graph.add_edge("B", "D")
    graph.add_edge("A", "C")
    graph.set_start_node("A")

    # 2. Run subgraph from 'A' and stop before 'D'
    workflow = Workflow(graph=graph)
    results = await workflow.run_subgraph(start_node_id="A", end_node_ids=["D"])

    # 3. Assert results
    assert "A" in results
    assert "B" in results
    assert "C" not in results  # C is on another branch and won't be executed
    assert "D" not in results  # Execution should stop before the end node
    assert node_a.is_successful
    assert node_b.is_successful
    assert node_c.state == NodeState.PENDING  # C should not have run
    assert node_d.state == NodeState.PENDING


def test_save_and_load_graph_results(tmp_path):
    """Tests saving and loading graph results to a file."""
    # 1. Define results and create a workflow instance
    graph = Graph()  # A dummy graph
    workflow = Workflow(graph=graph)
    workflow.results = {
        "node1": "Success",
        "node2": ValueError("Something went wrong"),
        "node3": "Another success"
    }
    file_path = tmp_path / "results.json"

    # 2. Save results
    workflow.save_results(str(file_path))

    # 3. Load results
    loaded_results = Workflow.load_results(str(file_path))

    # 4. Assert results are correctly serialized and deserialized
    assert loaded_results["node1"] == "Success"
    assert loaded_results["node3"] == "Another success"
    # Check the serialized error
    error_info = loaded_results["node2"]
    assert error_info["type"] == "error"
    assert error_info["message"] == "Something went wrong"
    assert error_info["class"] == "ValueError"


@pytest.mark.asyncio
async def test_cyclic_graph_with_max_steps():
    """Tests that a graph with a cycle terminates correctly using max_steps."""
    # 1. Define a stateful role to count executions
    class CountingRole(Role):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.count = 0

        async def run(self, msg: str, **kwargs) -> AssistantMessage:
            self.count += 1
            # Return a message that includes the current count
            return AssistantMessage(content=f"Count for {self.name} is now {self.count}")

    role_a = CountingRole(name="RoleA")
    role_b = CountingRole(name="RoleB")

    # 2. Define actions. The message now uses a template to pass context.
    action_a = Action(name="action_a", role=role_a, msg=jinja2.Template("From B: {{ previous_result.content }}"))
    action_b = Action(name="action_b", role=role_b, msg=jinja2.Template("From A: {{ previous_result.content }}"))

    # 3. Create nodes
    node_a = Node(id="A", role=role_a, action=action_a)
    node_b = Node(id="B", role=role_b, action=action_b)

    # 4. Create a cyclic graph A -> B -> A
    graph = Graph()
    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_edge("A", "B")
    graph.add_edge("B", "A")  # This creates the cycle
    graph.set_start_node("A")

    # 5. Run the workflow with a max_steps limit to prevent an infinite loop
    workflow = Workflow(graph=graph)
    max_steps = 3  # We expect the execution A -> B -> A
    results = await workflow.run(max_steps=max_steps, msg="Start")

    # 6. Assert results
    # The execution history should have exactly max_steps items
    assert len(graph.execution_history) == max_steps
    assert graph.execution_history == ["A", "B", "A"]

    # Check the final content of the results map, which holds the last message from each node
    assert "Count for RoleA is now 2" in results["A"]
    assert "Count for RoleB is now 1" in results["B"]

    # Check the underlying role state
    assert role_a.count == 2
    assert role_b.count == 1
    assert node_a.is_successful
    assert node_b.is_successful