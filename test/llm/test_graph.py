"""
@Author: obstacles
@Time:  2025-06-18 11:54
@Description:  Tests for the Graph implementation
"""
import asyncio
import pytest
from puti.llm.graph import Graph, Node, Edge, NodeState
from puti.llm.roles import Role, GraphRole
from puti.llm.workflow import run_graph
from puti.llm.tools.calculator import CalculatorTool
from puti.llm.messages import Message, AssistantMessage
from puti.llm.actions import Action
from unittest.mock import AsyncMock, patch
from typing import Dict, Any
import jinja2

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
    assert ("received" in node2_output_lower or "input" in node2_output_lower)
    assert "repeating" in node2_output_lower


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
    assert "role a" in results["nodeA"].lower()
    assert "nodeB" not in results or results["nodeB"] is None


@pytest.mark.asyncio
async def test_graph_error_handling():
    """Tests that the graph stops execution on a failed node."""
    # 1. Define roles
    role1 = Role(name="Role1")
    role2 = Role(name="Role2")

    # 2. Define actions, with one designed to fail
    async def action1():
        raise ValueError("Something went wrong")

    async def action2(previous_result: str):
        # This action should not be called
        result = await role2.run(with_message=previous_result)
        return result.content if isinstance(result, Message) else result

    # 3. Create nodes
    node1 = Node(id="node1", role=role1, action=action1)
    node2 = Node(id="node2", role=role2, action=lambda: action2(node1.result))

    # 4. Create graph
    graph = Graph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge("node1", "node2")
    graph.set_start_node("node1")

    # 5. Run graph
    results = await run_graph(graph)

    # 6. Assert results
    assert isinstance(results["node1"], ValueError)
    assert "node2" not in results or results["node2"] is None
    assert node1.state == NodeState.FAILED
    assert node2.state == NodeState.PENDING


@pytest.mark.asyncio
async def test_graph_with_tool_usage():
    """Tests a graph where a role uses a tool."""
    # 1. Define roles
    planner = Role(name="Planner", identity="You are a planner. Your goal is to answer questions. Use your tools if necessary.")
    executor = Role(name="Executor", identity="You are an executor. Your goal is to report the results you are given.")

    # 2. Equip the planner role with a tool
    planner.set_tools([CalculatorTool])

    # 3. Define actions
    async def plan_action():
        # The planner is prompted to perform a calculation
        result = await planner.run(with_message="What is the result of 100 + 5*5?")
        return result.content if isinstance(result, Message) else result

    # 使用字符串占位符
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
    results = await run_graph(graph)

    # 7. Assert results
    # The planner's output after using the tool should contain the numerical answer
    assert "125" in results["plan_node"]
    # The executor should report the result it was given
    assert "125" in results["execute_node"]


@pytest.mark.asyncio
async def test_complex_graph():
    """Tests a more complex graph with multiple branches and conditions."""
    # 1. Create mock roles
    role1 = AsyncMock()
    role1.run.return_value = AssistantMessage(content="Analyzing request")
    
    role2a = AsyncMock()
    role2a.run.return_value = AssistantMessage(content="Processing option A")
    
    role2b = AsyncMock()
    role2b.run.return_value = AssistantMessage(content="Processing option B")
    
    role3 = AsyncMock()
    role3.run.return_value = AssistantMessage(content="Final result")

    # 2. Create actions
    action1 = AsyncMock(return_value="Decision A")
    action2a = AsyncMock(return_value="Result A")
    action2b = AsyncMock(return_value="Result B")
    action3 = AsyncMock(return_value="Combined result")

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
    
    # Add edges with conditions
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
    assert node1.state == NodeState.SUCCESS
    assert node2a.state == NodeState.SUCCESS
    assert node2b.state == NodeState.PENDING
    assert node3.state == NodeState.SUCCESS


@pytest.mark.asyncio
async def test_graph_run_workflow():
    """Tests that the workflow.run_graph function correctly executes a graph."""
    # Create a simple graph
    role = Role(name="TestRole")
    action = AsyncMock(return_value="Success")
    
    node = Node(id="test_node", role=role, action=action)
    
    graph = Graph()
    graph.add_node(node)
    graph.set_start_node("test_node")
    
    # Mock the graph's run method
    with patch.object(Graph, 'run', AsyncMock(return_value={"test_node": "Success"})) as mock_run:
        result = await run_graph(graph)
        
    # Verify results
    assert mock_run.called
    assert result == {"test_node": "Success"}