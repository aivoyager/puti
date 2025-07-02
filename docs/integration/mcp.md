# MCP Integration

This document explains how to use the Model Control Protocol (MCP) integration in Puti for advanced agent capabilities.

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Creating MCP-Enabled Agents](#creating-mcp-enabled-agents)
- [Available MCP Tools](#available-mcp-tools)
- [MCP Agent Examples](#mcp-agent-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

MCP (Model Control Protocol) allows agents to execute external actions through a standardized interface. This gives agents the ability to interact with the file system, run terminal commands, execute Python code, and perform other operations outside of their language model environment.

In Puti, this functionality is provided through the `McpRole` class, which extends the standard `Role` class with additional MCP capabilities.

## Setup

To use MCP-enabled agents, you need to install Puti with the MCP dependencies:

```bash
pip install ai-puti[mcp]
```

## Creating MCP-Enabled Agents

### Basic MCP Agent

Create an MCP-enabled agent by inheriting from the `McpRole` class:

```python
from puti.llm.roles import McpRole

class Developer(McpRole):
    name: str = "Developer"
    identity: str = "Software Engineer"
    goal: str = "Help with programming tasks and development"
    
    def model_post_init(self, __context):
        # MCP roles automatically get access to tools during initialization
        pass
```

### The Alex Agent

Puti provides a pre-configured MCP agent called `Alex` with a comprehensive set of tools:

```python
from puti.llm.roles.agents import Alex

# Create an instance of Alex
alex = Alex()

# Use Alex to perform tasks
response = await alex.run("Please create a Python script that plots a sine wave")
print(response)
```

## Available MCP Tools

MCP-enabled agents in Puti have access to the following tools:

### 1. Web Search

Enables agents to search the internet for up-to-date information.

```python
from puti.llm.tools.web_search import WebSearch

# Web search is available automatically to Alex
response = await alex.run("What are the latest developments in quantum computing?")
```

### 2. File Tool

Allows agents to read, write, and manipulate files on the system.

```python
from puti.llm.tools.file import File

# Example usage through an agent
response = await alex.run("Create a file called hello.py with a simple Hello World program")
```

### 3. Terminal Tool

Gives agents the ability to execute terminal commands.

```python
from puti.llm.tools.terminal import Terminal

# Example usage through an agent
response = await alex.run("Show me the files in the current directory and their sizes")
```

### 4. Python Tool

Allows agents to execute Python code dynamically.

```python
from puti.llm.tools.python import Python

# Example usage through an agent
response = await alex.run("Calculate the first 10 Fibonacci numbers using Python")
```

### 5. Project Analyzer

Helps agents understand the structure of the current project.

```python
from puti.llm.tools.project_analyzer import ProjectAnalyzer

# Example usage through an agent
response = await alex.run("Analyze the structure of this project")
```

## MCP Agent Examples

### Software Development Assistant

```python
from puti.llm.roles import McpRole
from puti.llm.tools.terminal import Terminal
from puti.llm.tools.file import File
from puti.llm.tools.python import Python
from puti.llm.tools.project_analyzer import ProjectAnalyzer

class DevAssistant(McpRole):
    name: str = "DevAssistant"
    identity: str = "Software Development Assistant"
    goal: str = "Help with coding, debugging, and project management"
    
    def model_post_init(self, __context):
        self.set_tools([Terminal, File, Python, ProjectAnalyzer])

# Usage
assistant = DevAssistant()
response = await assistant.run("Please help me set up a basic Flask web server")
print(response)
```

### System Administrator

```python
from puti.llm.roles import McpRole
from puti.llm.tools.terminal import Terminal
from puti.llm.tools.file import File

class SysAdmin(McpRole):
    name: str = "SysAdmin"
    identity: str = "System Administrator"
    goal: str = "Help manage and optimize system operations"
    
    def model_post_init(self, __context):
        self.set_tools([Terminal, File])

# Usage
admin = SysAdmin()
response = await admin.run("Check the system's disk usage and identify large files")
print(response)
```

## Best Practices

1. **Security Considerations**: MCP-enabled agents can execute code and terminal commands, so use them in trusted environments only.

2. **Error Handling**: Use the `cp.invoke` method to catch and handle exceptions when running MCP agents:

   ```python
   from puti.llm.roles.agents import Alex
   
   alex = Alex()
   response = alex.cp.invoke(alex.run, "Perform a system task")
   ```

3. **Resource Limits**: Set appropriate timeout and resource limits when allowing agents to execute code:

   ```python
   # When initializing a custom MCP agent, you can adjust settings
   class CustomAgent(McpRole):
       name: str = "Custom"
       
       def model_post_init(self, __context):
           self.set_tools([Python])
           self.python_timeout = 5  # 5-second timeout for Python execution
   ```

4. **Session Management**: For long-running operations, manage the MCP session explicitly:

   ```python
   # Initialize session
   await agent._initialize()
   
   # Run multiple commands in the same session
   await agent.run("Command 1")
   await agent.run("Command 2")
   
   # Close the session when done
   await agent.disconnect()
   ```

## Troubleshooting

### Common Issues

1. **Connection Errors**: If you encounter connection errors, check that:
   - The MCP dependencies are installed
   - The agent is properly initialized

2. **Tool Execution Failures**: 
   - Verify file permissions
   - Check for invalid command syntax
   - Ensure the necessary dependencies are installed

3. **Timeout Errors**: 
   - Increase the timeout limit for long-running operations
   - Break complex tasks into smaller steps

### Debugging

For better insight into what's happening with MCP agents, you can enable debug logging:

```python
import logging
from puti.logs import logger_factory

logger_factory.llm.setLevel(logging.DEBUG)
```

For more help, consult the Puti GitHub repository or raise an issue if you encounter persistent problems. 