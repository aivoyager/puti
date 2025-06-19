"""
@Author: obstacles
@Time:  2025-06-18 11:54
@Description:  Tests for the Graph implementation
"""
import asyncio
import pytest
from puti.llm.graph import Graph, Vertex, Edge
from puti.constant.llm import VertexState
from puti.llm.roles import Role, GraphRole
from puti.llm.workflow import Workflow
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
    role1 = GraphRole(name="Role1", identity="helpful assistant", goal="Just reply with the user's prompt.")
    role2 = GraphRole(name="Role2", identity="helpful assistant", goal="repeats the input you receive.")

    # 2. Define actions for vertices
    action1 = Action(name="action1", description="test action1", prompt='hello world')
    
    # 使用字符串占位符方式，自动引用前一节点的结果
    action2 = Action(
        name="action2",
        description="test action2",
        prompt=jinja2.Template("Received: {{ previous_result.content }}. Now repeating it.")
    )

    # 3. Create vertices
    vertex1 = Vertex(id="vertex1", role=role1, action=action1)
    vertex2 = Vertex(id="vertex2", role=role2, action=action2)

    # 4. Create graph
    graph = Graph()
    graph.add_vertex(vertex1)
    graph.add_vertex(vertex2)
    graph.add_edge("vertex1", "vertex2")
    graph.set_start_vertex("vertex1")

    # 5. Run the graph
    results = await graph.run(prompt='hello world')

    # 6. Assert results (flexible assertions for LLM output)
    assert "hello world" in results["vertex1"].lower()
    vertex2_output_lower = results["vertex2"].lower()
    assert "hello world" in vertex2_output_lower
    assert ("received" in vertex2_output_lower or "input" in vertex2_output_lower)
    assert "repeating" in vertex2_output_lower


@pytest.mark.asyncio
async def test_sequential_graph_with_multiple_placeholders():
    """Tests a graph with multiple placeholders in action prompts."""
    # 1. Define roles
    role1 = GraphRole(name="Role1", identity="helpful assistant", goal="Just reply with the user's prompt.")
    role2 = GraphRole(name="Role2", identity="helpful assistant", goal="combines inputs")

    # 2. Define actions for vertices
    action1 = Action(name="action1", description="test action1", prompt='hello world')
    
    # 使用多个占位符，包括自定义参数和前一节点结果
    action2 = Action(
        name="action2", 
        description="test action2", 
        prompt=jinja2.Template("Previous result: {{ previous_result.content }}. Custom param: {{ custom_param }}.")
    )

    # 3. Create vertices
    vertex1 = Vertex(id="vertex1", role=role1, action=action1)
    vertex2 = Vertex(id="vertex2", role=role2, action=action2)

    # 4. Create graph
    graph = Graph()
    graph.add_vertex(vertex1)
    graph.add_vertex(vertex2)
    graph.add_edge("vertex1", "vertex2")
    graph.set_start_vertex("vertex1")

    # 5. Run the graph with a custom parameter
    results = await graph.run(prompt='hello world', custom_param='test value')

    # 6. Assert results
    assert "hello world" in results["vertex1"].lower()
    vertex2_output_lower = results["vertex2"].lower()
    assert "hello world" in vertex2_output_lower
    assert "test value" in vertex2_output_lower


@pytest.mark.asyncio
async def test_conditional_graph():
    """Tests a graph with conditional branching."""
    # 1. Define roles
    role1 = Role(name="Role1", identity="You are a decision maker. If the input is 'a', say 'path_a'. If it's 'b', say 'path_b'.")
    role_a = Role(name="RoleA", identity="You are Role A. Announce you have been activated.")
    role_b = Role(name="RoleB", identity="You are Role B. Announce you have been activated.")

    # 2. Define actions
    action1 = Action(name="action1", description="decision action", prompt="a")
    
    # 使用字符串占位符替代函数
    action_a = Action(
        name="action_a",
        description="Process branch A",
        prompt=jinja2.Template("Triggered by: {{ previous_result.content }}")
    )
    
    action_b = Action(
        name="action_b",
        description="Process branch B",
        prompt=jinja2.Template("Triggered by: {{ previous_result.content }}")
    )

    # 3. Create vertices
    vertex1 = Vertex(id="vertex1", role=role1, action=action1)
    vertex_a = Vertex(id="vertexA", role=role_a, action=action_a)
    vertex_b = Vertex(id="vertexB", role=role_b, action=action_b)

    # 4. Create graph
    graph = Graph()
    graph.add_vertex(vertex1)
    graph.add_vertex(vertex_a)
    graph.add_vertex(vertex_b)
    graph.add_edge("vertex1", "vertexA", condition=lambda x: "path_a" in x.lower())
    graph.add_edge("vertex1", "vertexB", condition=lambda x: "path_b" in x.lower())
    graph.set_start_vertex("vertex1")

    # 5. Run graph
    results = await graph.run()

    # 6. Assert results
    assert "path_a" in results["vertex1"].lower()


@pytest.mark.asyncio
async def test_graph_error_handling():
    """Tests that the graph stops execution on a failed vertex."""
    # 1. Define roles
    role1 = Role(name="Role1")
    role2 = Role(name="Role2")

    # 2. Define actions, with one designed to fail
    async def action1(role):
        raise ValueError("Something went wrong")

    async def action2(previous_result: str, role):
        # This action should not be called
        result = await role.run(prompt=previous_result)
        return result.content if isinstance(result, Message) else result

    # 3. Create vertices with Action wrappers
    action1_wrapped = Action(name="action1", description="Fails with error", prompt=lambda: action1(role1))
    action2_wrapped = Action(name="action2", description="Should not run", prompt=lambda: action2(None, role2))
    
    vertex1 = Vertex(id="vertex1", role=role1, action=action1_wrapped)
    vertex2 = Vertex(id="vertex2", role=role2, action=action2_wrapped)

    # 4. Create graph
    graph = Graph()
    graph.add_vertex(vertex1)
    graph.add_vertex(vertex2)
    graph.add_edge("vertex1", "vertex2")
    graph.set_start_vertex("vertex1")

    # 5. Run graph
    workflow = Workflow(graph=graph)
    results = await workflow.run()

    # 6. Assert results
    assert isinstance(results["vertex1"], ValueError)
    assert "vertex2" not in results or results["vertex2"] is None
    assert vertex1.state == VertexState.FAILED
    assert vertex2.state == VertexState.PENDING


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
        result = await planner.run(prompt="What is the result of 100 + 5*5?")
        return result.content if isinstance(result, Message) else result

    # 使用字符串占位符
    execute_action = Action(
        name="execute_action",
        description="Report the final result",
        prompt=jinja2.Template("The final result is: {{ previous_result.content }}")
    )

    # 4. Create vertices
    plan_vertex = Vertex(id="plan_vertex", role=planner, action=plan_action)
    execute_vertex = Vertex(id="execute_vertex", role=executor, action=execute_action)

    # 5. Create graph
    graph = Graph()
    graph.add_vertex(plan_vertex)
    graph.add_vertex(execute_vertex)
    graph.add_edge("plan_vertex", "execute_vertex")
    graph.set_start_vertex("plan_vertex")

    # 6. Run the graph
    results = await graph.run()

    # 7. Assert results
    # The planner's output after using the tool should contain the numerical answer
    assert "125" in results["plan_vertex"]
    # The executor should report the result it was given
    assert "125" in results["execute_vertex"]


@pytest.mark.asyncio
async def test_complex_graph():
    """Tests a more complex graph where multiple vertices can branch based on the results."""
    # 1. Define roles
    r1 = Role(name="R1", identity="You are a router determining if a prompt is happy, neutral, or sad. Return one of: HAPPY, NEUTRAL, SAD.")
    r2 = Role(name="R2", identity="You add exclamation marks to a prompt.")
    r3 = Role(name="R3", identity="You add question marks to a prompt.")
    r4 = Role(name="R4", identity="You add ellipsis to a prompt.")
    r5 = Role(name="R5", identity="You are a final processor who returns the prompt as is.")

    # Define actions
    action1 = Action(name="action1", description="Route prompt", prompt='Hello world')
    action2 = Action(name="action2", description="Add excitement", prompt="{{previous_result.content}}")
    action3 = Action(name="action3", description="Add questions", prompt="{{previous_result.content}}")
    action4 = Action(name="action4", description="Add contemplation", prompt="{{previous_result.content}}")
    action5 = Action(name="action5", description="Final output", prompt="{{previous_result.content}}")

    # Create vertices
    v1 = Vertex(id="v1", role=r1, action=action1)
    v2 = Vertex(id="v2", role=r2, action=action2)
    v3 = Vertex(id="v3", role=r3, action=action3)
    v4 = Vertex(id="v4", role=r4, action=action4)
    v5 = Vertex(id="v5", role=r5, action=action5)

    # Create graph
    graph = Graph()
    graph.add_vertex(v1)
    graph.add_vertex(v2)
    graph.add_vertex(v3)
    graph.add_vertex(v4)
    graph.add_vertex(v5)
    
    # Add edges with conditions
    graph.add_edge("v1", "v2", condition=lambda x: "HAPPY" in x.upper())
    graph.add_edge("v1", "v3", condition=lambda x: "NEUTRAL" in x.upper())
    graph.add_edge("v1", "v4", condition=lambda x: "SAD" in x.upper())
    graph.add_edge("v2", "v5")
    graph.add_edge("v3", "v5")
    graph.add_edge("v4", "v5")
    
    graph.set_start_vertex("v1")

    # Run graph
    workflow = Workflow(graph=graph)
    results = await workflow.run()

    # Assert results
    assert "v1" in results
    assert "v5" in results  # The final vertex should have executed
    
    # One of v2, v3, or v4 should have executed based on the routing
    executed_middle_vertices = [v_id for v_id in ["v2", "v3", "v4"] if v_id in results]
    assert len(executed_middle_vertices) == 1


@pytest.mark.asyncio
async def test_graph_run_workflow():
    """Tests running a graph through the workflow class."""
    # Create a simple graph with mocked roles
    mock_role = AsyncMock(spec=Role)
    mock_role.run = AsyncMock(return_value=AssistantMessage(content="mocked response"))
    
    # Create actions
    action1 = Action(
        name="first_action",
        description="First action in workflow",
        prompt="Start the process"
    )
    
    action2 = Action(
        name="second_action",
        description="Second action in workflow",
        prompt="{{previous_result.content}}"
    )
    
    # Create vertices
    v1 = Vertex(id="first", role=mock_role, action=action1)
    v2 = Vertex(id="second", role=mock_role, action=action2)
    
    # Create graph
    graph = Graph()
    graph.add_vertex(v1)
    graph.add_vertex(v2)
    graph.add_edge("first", "second")
    graph.set_start_vertex("first")
    
    # Create workflow and run graph
    workflow = Workflow(graph=graph)
    result = await workflow.run()
    
    # Assertions
    assert "first" in result
    assert "second" in result
    mock_role.run.assert_called()


@pytest.mark.asyncio
async def test_action_new_api():
    """Tests the new Action API where role is provided during execution, not construction."""
    # 1. Define a role
    role = Role(name="TestRole", identity="helpful assistant")
    role.run = AsyncMock(return_value=AssistantMessage(content="Response from role"))
    
    # 2. Create an action without binding a role
    action = Action(
        name="new_api_action",
        description="An action demonstrating the new API",
        prompt="This is a test message"
    )
    
    # 3. Create a vertex that binds the role and action
    vertex = Vertex(id="test_vertex", role=role, action=action)
    
    # 4. Run the vertex, which will pass its role to the action
    result = await vertex.run()
    
    # 5. Assert results
    assert "Response from role" in result.content
    assert vertex.is_successful
    assert role.run.called
    # The mock should have been called with our message
    role.run.assert_called_once()
    args, kwargs = role.run.call_args
    assert kwargs.get('prompt') == "This is a test message"
    assert kwargs.get('action_name') == "new_api_action"