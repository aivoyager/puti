import asyncio
import pytest
from puti.llm.graph import Graph, Node
from puti.llm.roles import Role, GraphRole
from puti.llm.workflow import run_graph
from puti.llm.tools.calculator import CalculatorTool
from puti.llm.messages import Message

# Note: These tests interact with a live LLM and may require an API key
# (e.g., OPENAI_API_KEY) to be set in the environment.


@pytest.mark.asyncio
async def test_sequential_graph():
    """Tests a simple sequential graph where one role's output is the next one's input."""
    # 1. Define roles
    role1 = GraphRole(name="Role1", identity="helpful assistant", goal="Just reply with the user's message.")
    role2 = GraphRole(name="Role2", identity="helpful assistant", goal="repeats the input you receive.")

    # 2. Define actions for nodes
    async def action1():
        result = await role1.run(with_message="hello world")
        return result.content if isinstance(result, Message) else result

    async def action2(previous_result: str):
        result = await role2.run(with_message=previous_result)
        return result.content if isinstance(result, Message) else result

    # 3. Create nodes
    node1 = Node(id="node1", role=role1, action=action1)
    # The lambda ensures node1.result is read *after* node1 has finished running
    node2 = Node(id="node2", role=role2, action=lambda: action2(node1.result))

    # 4. Create graph
    graph = Graph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge("node1", "node2")
    graph.set_start_node("node1")

    # 5. Run the graph
    results = await run_graph(graph)

    # 6. Assert results (flexible assertions for LLM output)
    assert "hello world" in results["node1"].lower()
    assert "hello world" in results["node2"].lower()


@pytest.mark.asyncio
async def test_conditional_graph():
    """Tests a graph with conditional branching."""
    # 1. Define roles
    role1 = Role(name="Role1", identity="You are a decision maker. If the input is 'a', say 'path_a'. If it's 'b', say 'path_b'.")
    role_a = Role(name="RoleA", identity="You are Role A. Announce you have been activated.")
    role_b = Role(name="RoleB", identity="You are Role B. Announce you have been activated.")

    # 2. Define actions
    async def start_action():
        result = await role1.run(with_message="a")
        return result.content if isinstance(result, Message) else result

    async def action_a(previous_result: str):
        result = await role_a.run(with_message=f"Triggered by: {previous_result}")
        return result.content if isinstance(result, Message) else result

    async def action_b(previous_result: str):
        result = await role_b.run(with_message=f"Triggered by: {previous_result}")
        return result.content if isinstance(result, Message) else result

    # 3. Create nodes
    node1 = Node(id="node1", role=role1, action=start_action)
    node_a = Node(id="nodeA", role=role_a, action=lambda: action_a(node1.result))
    node_b = Node(id="nodeB", role=role_b, action=lambda: action_b(node1.result))

    # 4. Create graph
    graph = Graph()
    graph.add_node(node1)
    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_edge("node1", "nodeA", condition=lambda x: "path_a" in x.lower())
    graph.add_edge("node1", "nodeB", condition=lambda x: "path_b" in x.lower())
    graph.set_start_node("node1")

    # 5. Run graph
    results = await run_graph(graph)

    # 6. Assert results
    assert "path_a" in results["node1"].lower()
    assert "role a" in results["nodeA"].lower()
    assert "nodeB" not in results or results["nodeB"] is None


@pytest.mark.asyncio
async def test_run_with_error():
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

    async def execute_action(plan_result: str):
        result = await executor.run(with_message=f"The final result is: {plan_result}")
        return result.content if isinstance(result, Message) else result

    # 4. Create nodes
    plan_node = Node(id="plan_node", role=planner, action=plan_action)
    execute_node = Node(id="execute_node", role=executor, action=lambda: execute_action(plan_node.result))

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