# Single Agent Patterns Guide

This document provides detailed guidance on using single agent patterns in the PuTi framework. Single agent patterns refer to using an individual intelligent agent to perform specific tasks without multi-agent interaction.

## Table of Contents

- [Basic Concepts](#basic-concepts)
- [Creating a Single Agent](#creating-a-single-agent)
- [Tool Integration](#tool-integration)
- [Memory Management](#memory-management)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## Basic Concepts

The single agent pattern is the most basic usage mode in the PuTi framework, allowing you to create an independent intelligent agent to handle specific tasks. Key components include:

- **Role**: The core class of the agent, defining its identity, goals, and behavior
- **LLMNode**: Provides interaction capabilities with language models
- **Tool**: Tools that provide specific functionality to the agent
- **Memory**: Manages the agent's memory and conversation history

## Creating a Single Agent

Creating a basic single agent is very simple:

```python
from puti.llm.roles import Role
from puti.llm.nodes import OpenAINode

# Create a basic agent
agent = Role(
    name="Assistant",                   # Agent name
    goal="Help users solve problems",   # Agent goal
    identity="Professional assistant",  # Agent identity
    skill="Answering questions and providing advice"  # Agent skills
)

# Optional: specify a particular language model node
agent.agent_node = OpenAINode()  # If not specified, OpenAINode will be used by default
```

### Predefined Specialized Agent Types

The framework provides several predefined specialized agent types that can be used directly:

```python
from puti.llm.roles.agents import Alex, Ethan, CZ, Debater

# Alex - General-purpose assistant with access to multiple tools
alex = Alex()

# Ethan - Agent designed specifically for Twitter interactions
ethan = Ethan()

# CZ - Domain-specific agent
cz = CZ()

# Debater - Agent specialized in debates
debater = Debater()
```

## Tool Integration

Tools are key to extending an agent's capabilities, enabling it to perform various operations:

```python
from puti.llm.roles import Role
from puti.llm.tools.web_search import WebSearch
from puti.llm.tools.calculator import CalculatorTool
from puti.llm.tools.file import File
from puti.llm.tools.project_analyzer import ProjectAnalyzer

# Create an agent with multiple tools
agent = Role(name="Multi-function Assistant")
agent.set_tools([WebSearch, CalculatorTool, File, ProjectAnalyzer])

# Or automatically add tools in a subclass
class MyCustomAgent(Role):
    name: str = "Custom Assistant"
    
    def model_post_init(self, __context):
        self.set_tools([WebSearch, CalculatorTool])
```

### Creating Custom Tools

You can create custom tools by inheriting from `BaseTool`:

```python
from puti.llm.tools import BaseTool, ToolArgs
from pydantic import Field
from typing import Annotated

# Define tool arguments
class MyToolArgs(ToolArgs):
    param1: str = Field(..., description="Description of first parameter")
    param2: int = Field(default=0, description="Description of second parameter")

# Define the tool
class MyTool(BaseTool):
    name: str = "my_tool"
    desc: str = "Description of this custom tool"
    args: MyToolArgs = None
    
    async def run(self, param1: str, param2: int = 0, *args, **kwargs) -> Annotated[str, 'tool result']:
        # Implement tool logic
        result = f"Processing parameters: {param1}, {param2}"
        return result
```

## Memory Management

Agents have built-in memory management systems to track conversation history:

```python
from puti.llm.roles import Role

agent = Role(name="Assistant")

# Run the agent to process a message
response = await agent.run("Hello, how's the weather today?")

# Get conversation history from memory
conversation_history = agent.rc.memory.get()

# Run the agent with memory context (automatically handled)
response = await agent.run("Do I need an umbrella?")  # Agent will automatically access previous conversation history
```

## Usage Examples

Here's a complete example of single agent usage:

```python
import asyncio
from puti.llm.roles.agents import Alex
from puti.llm.nodes import OpenAINode

async def main():
    # Create an agent
    agent = Alex()
    
    # Initialize conversation
    response = await agent.run("Can you help me calculate 123 + 456?")
    print(f"Agent: {response}")
    
    # Continue conversation
    response = await agent.run("Now multiply the result by 2")
    print(f"Agent: {response}")
    
    # Use tools
    response = await agent.run("Help me search for recent advances in artificial intelligence")
    print(f"Agent: {response}")

# Run the main function
asyncio.run(main())
```

### CLI Mode Operation

You can also interact with an agent using a command-line interface:

```python
from puti.llm.roles.agents import Alex
import asyncio

agent = Alex()

async def interactive_cli():
    print("Start conversation with the Agent, type 'exit' to quit")
    while True:
        user_input = input("User: ")
        if user_input.lower() == 'exit':
            break
            
        response = await agent.run(user_input)
        print(f"Agent: {response}")

asyncio.run(interactive_cli())
```

## Best Practices

When using the single agent pattern, here are some best practices:

1. **Clearly Define Goals and Identity**: Provide clear goal and identity descriptions for the agent, which helps generate more relevant responses
   
2. **Choose Tools Appropriately**: Only provide the agent with tools it needs, avoiding confusion caused by too many tools

3. **Manage Context Size**: Be mindful of conversation history length to avoid exceeding language model context limits

4. **Handle Exceptions**: Use `cp.invoke` to wrap agent calls to catch potential exceptions:
   ```python
   from puti.llm.roles.agents import Alex
   
   agent = Alex()
   response = agent.cp.invoke(agent.run, "Help me analyze this problem")
   ```

5. **Combine with Graph Pattern**: For complex tasks, consider combining single agents with Graph workflows:
   ```python
   from puti.llm.graph import Graph, Vertex
   from puti.llm.actions import Action
   from puti.llm.roles.agents import Alex
   
   agent = Alex()
   action = Action(name="analyze", prompt="Analyze the following problem: {{problem}}")
   vertex = Vertex(id="analysis", role=agent, action=action)
   
   graph = Graph()
   graph.add_vertex(vertex)
   graph.set_start_vertex("analysis")
   
   results = await graph.run(problem="Problem to be analyzed")
   ```

By following these patterns and best practices, you can effectively leverage the PuTi framework to create powerful single agent applications. 