# Multi-Agent Interaction Patterns

This document provides detailed guidance on using the Graph, Workflow, Env, and Role patterns for multi-agent interactions in the PuTi framework.

## Table of Contents

- [Graph and Workflow](#graph-and-workflow)
  - [Basic Concepts](#basic-concepts)
  - [Creating a Graph](#creating-a-graph)
  - [Running a Workflow](#running-a-workflow)
  - [Advanced Graph Patterns](#advanced-graph-patterns)
- [Env and Role Patterns](#env-and-role-patterns)
  - [Environment Setup](#environment-setup)
  - [Role Creation](#role-creation)
  - [Multi-Agent Interaction](#multi-agent-interaction)
- [Combining Patterns](#combining-patterns)

## Graph and Workflow

### Basic Concepts

The Graph-Workflow pattern provides a structured way to orchestrate multi-agent interactions, particularly for complex tasks requiring sequential or conditional execution.

- **Vertex**: A single unit of execution in a graph, combining:
  - A Role (agent that performs the action)
  - An Action (what to execute)
  
- **Edge**: Connection between vertices, defining execution flow
  - Can include conditions for dynamic branching

- **Graph**: Collection of vertices and edges forming a complete workflow

- **Workflow**: Manager that runs a graph and collects results

### Creating a Graph

Here's how to create a basic graph:

```python
from puti.llm.graph import Graph, Vertex, Edge
from puti.llm.roles import Role, GraphRole
from puti.llm.actions import Action
from puti.llm.workflow import Workflow

# 1. Create roles
role1 = GraphRole(name="Planner", identity="planning assistant", goal="Create a plan")
role2 = GraphRole(name="Executor", identity="execution assistant", goal="Execute the plan")

# 2. Define actions
action1 = Action(
    name="planning_action",
    description="Create a detailed plan",
    prompt="Create a step-by-step plan for completing the following task: {{task}}"
)

action2 = Action(
    name="execution_action",
    description="Execute the plan",
    prompt="Execute the following plan: {{previous_result.content}}"
)

# 3. Create vertices
planning_vertex = Vertex(id="planning", role=role1, action=action1)
execution_vertex = Vertex(id="execution", role=role2, action=action2)

# 4. Create graph and add vertices
graph = Graph()
graph.add_vertex(planning_vertex)
graph.add_vertex(execution_vertex)

# 5. Add edge to define the workflow
graph.add_edge("planning", "execution")

# 6. Set the starting point
graph.set_start_vertex("planning")
```

### Running a Workflow

Once you have created a graph, you can run it using a Workflow:

```python
# Create workflow from the graph
workflow = Workflow(graph=graph)

# Run the workflow with initial parameters
results = await workflow.run(task="Build a simple website")

# Access results by vertex ID
planning_result = results["planning"]
execution_result = results["execution"]

# Save results for later analysis
workflow.save_results("workflow_results.json")
```

### Advanced Graph Patterns

#### Conditional Branching

You can create workflows with dynamic paths based on conditions:

```python
# Add conditional edges
graph.add_edge("vertex1", "vertex2", condition=lambda x: "option_a" in x.lower())
graph.add_edge("vertex1", "vertex3", condition=lambda x: "option_b" in x.lower())
```

#### Running Subgraphs

For complex workflows, you can run specific portions:

```python
# Run until a specific vertex
results = await workflow.run_until_vertex("target_vertex_id")

# Run a subgraph (from start to specified end points)
results = await workflow.run_subgraph(
    start_vertex_id="vertex2",
    end_vertex_ids=["vertex4", "vertex5"]
)
```

## Env and Role Patterns

The Env-Role pattern provides a more open, message-based approach to multi-agent interactions, enabling dynamic conversations between agents.

### Environment Setup

Create an environment for agents to interact:

```python
from puti.llm.envs import Env
from puti.llm.roles import Role
from puti.llm.messages import Message

# Create an environment with a name and description
env = Env(
    name="brainstorming_room",
    desc="A collaborative environment for creative brainstorming"
)
```

### Role Creation

Roles represent different agents in the environment:

```python
# Create roles with different capabilities
creative_role = Role(
    name="creative",
    goal="Generate innovative ideas",
    identity="creative thinker",
    skill="thinking outside the box"
)

critical_role = Role(
    name="critic",
    goal="Evaluate and refine ideas",
    identity="analytical thinker",
    skill="finding flaws and improvements"
)

# Add roles to the environment
env.add_roles([creative_role, critical_role])
```

### Multi-Agent Interaction

Enable interaction between agents:

```python
# Start a conversation with an initial message
env.publish_message(Message.from_any(
    "Let's brainstorm ideas for a new mobile app",
    receiver=creative_role.address,
    sender="user"
))

# Run the environment for multiple interaction rounds
await env.run(run_round=5)

# Access conversation history
for message in env.history:
    print(f"{message.sender}: {message.content}")
```

## Combining Patterns

For complex scenarios, you can combine both patterns:

```python
# Use GraphRoles in a structured workflow
graph_role = GraphRole(name="coordinator")

# Create a vertex with access to environment context
vertex = Vertex(id="coordination", role=graph_role, action=coordination_action)

# After graph execution, agents can continue interacting in the environment
await workflow.run()
await env.run(run_round=3)
```

## Example: Creating a Twitter Bot Workflow

Here's a complete example of using the Graph pattern for a Twitter bot:

```python
from puti.llm.roles.agents import Ethan
from puti.llm.actions.x_bot import GenerateTweetAction, PublishTweetAction
from puti.llm.workflow import Workflow
from puti.llm.graph import Vertex, Graph
from jinja2 import Template

def create_twitter_workflow(ethan_agent):
    # Define actions
    generate_action = GenerateTweetAction()
    publish_action = PublishTweetAction(
        prompt=Template("I am now publishing the tweet: {{ previous_result.content }}")
    )
    
    # Create vertices
    generate_vertex = Vertex(id="generate_tweet", action=generate_action, role=ethan_agent)
    publish_vertex = Vertex(id="publish_tweet", action=publish_action, role=ethan_agent)
    
    # Create graph
    graph = Graph()
    graph.add_vertex(generate_vertex)
    graph.add_vertex(publish_vertex)
    graph.add_edge("generate_tweet", "publish_tweet")
    graph.set_start_vertex("generate_tweet")
    
    # Create workflow
    return Workflow(graph=graph)

async def run_twitter_workflow(ethan_agent, topic=None):
    workflow = create_twitter_workflow(ethan_agent)
    
    # Set initial context with optional topic
    initial_context = {}
    if topic:
        initial_context["topic"] = topic
    
    # Run the workflow and return results
    return await workflow.run(initial_context=initial_context)
```

This document covers the key patterns for multi-agent interactions. Refer to the API documentation for complete details on all available methods and properties. 