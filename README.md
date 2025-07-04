# Puti - Multi-Agent Framework 🤖

<!-- 奇异人生(Life is Strange)风格Logo - Max的笔记本风格 -->
<p align="center">
  <img src="examples/assets/puti_logo_final.svg" alt="PUTI Logo - Life is Strange Journal Style" width="400"/>
</p>

<p align="center">
    <em>An elegant multi-agent framework for building autonomous agents to tackle complex tasks.</em>
</p>

<p align="center">
    <a href="https://github.com/aivoyager/puti/stargazers"><img src="https://img.shields.io/github/stars/aivoyager/puti?style=flat-square" alt="Stars"></a>
    <a href="https://github.com/aivoyager/puti/network/members"><img src="https://img.shields.io/github/forks/aivoyager/puti?style=flat-square" alt="Forks"></a>
    <a href="https://github.com/aivoyager/puti/issues"><img src="https://img.shields.io/github/issues/aivoyager/puti?style=flat-square" alt="Issues"></a>
    <a href="https://github.com/aivoyager/puti/pulls"><img src="https://img.shields.io/github/issues-pr/aivoyager/puti?style=flat-square" alt="Pull Requests"></a>
    <a href="https://github.com/aivoyager/puti/blob/main/LICENSE"><img src="https://img.shields.io/github/license/aivoyager/puti?style=flat-square" alt="License"></a>
    <a href="https://pypi.org/project/ai-puti/"><img src="https://img.shields.io/pypi/v/ai-puti.svg?style=flat-square&logo=pypi&logoColor=white" alt="PyPI version"></a>
    <a href="https://pypi.org/project/ai-puti/"><img src="https://img.shields.io/pypi/pyversions/ai-puti.svg?style=flat-square&logo=python&logoColor=white" alt="Python versions"></a>
</p>

## ✨ Introduction

Puti is a versatile, multi-agent framework designed to simplify the development of applications powered by Large Language Models (LLMs). It provides a structured, extensible architecture for creating, managing, and coordinating intelligent agents that can collaborate to solve complex problems.

-   **🤖 Multi-Agent Systems**: Design sophisticated workflows where multiple agents collaborate, delegate tasks, and solve problems together.
-   **🛠️ Extensible Tools**: Equip agents with a powerful set of built-in tools (`web_search`, `file_io`, `terminal`, `python`) or easily create your own.
-   **🔄 Persistent Task Scheduling**: Automate workflows with a built-in, cron-like scheduler managed via a simple CLI.
-   **🗣️ Interactive & Scriptable**: Use agents interactively through the command line or integrate them seamlessly into your Python scripts.
-   **🚀 Ready-to-Use Agents**: Get started quickly with pre-built agents like `Alex` (general-purpose) and `Ethan` (Twitter-focused).

### Alex-Chat
![Alex Chat Demo](examples/puti_alex.gif)

### Ethan-Chat
![Ethan Chat Demo](examples/ethan.png)

## 🚀 Upcoming Features

We are continuously improving Puti. Here's what's on the horizon:

-   **✨ Enhanced Developer Experience**:
    -   **Syntactic Sugar**: Introducing more intuitive and expressive syntax to simplify agent and task definitions, making development faster and more enjoyable.
    -   **Improved Abstractions**: Refining the core abstractions for even easier customization and extension.

-   **🌐 Web UI for Visualization & Management**:
    -   A comprehensive web interface to visualize agent interactions, manage scheduled tasks, and monitor system performance in real-time.

-   **🧠 Advanced Agent Capabilities**:
    -   **Memory Optimization**: Implementing more sophisticated memory management to allow for longer conversations and more complex task execution.
    -   **Dynamic Goal Setting**: Enabling agents to dynamically set and adapt their own goals based on new information.

## 📦 Installation

Install Puti directly from PyPI:
```bash
pip install ai-puti
```

Or, for development, clone the repository and install in editable mode:
```bash
git clone https://github.com/aivoyager/puti.git
cd puti

# Set up the development environment (creates venv and installs dependencies)
python -m puti.bootstrap
# Or use the console script after installation
# pip install -e .
# puti-setup
```

## 🚀 Quick Start

### Chat with Alex
Get started immediately with Puti's interactive, all-purpose AI assistant, Alex. Alex is an all-purpose bot with multiple integrated tools to help you with a wide range of tasks.

```bash
puti alex-chat
```

### Chat with Ethan (Twikit Integration)
Interact with Ethan, an agent specialized in Twitter interactions using the `twikit` library. Ethan is a Twitter bot designed to help you manage your daily Twitter activities.

```bash
puti ethan-chat
```

**On your first run with Ethan**, Puti ensures your `twikit` is ready:
1.  **Cookie Path Check**: The app looks for the `TWIKIT_COOKIE_PATH` environment variable.
2.  **Guided Setup**: If the path is not found, you'll be prompted to enter the file path to your `cookies.json`.
3.  **Validation**: It checks if the file exists at the provided path.
4.  **Secure Storage**: The path is saved to your local `.env` file for future sessions.


**On your first run**, Puti provides a guided setup experience:
1.  🕵️ **Auto-detection**: The app checks if your OpenAI credentials are set up.
2.  🗣️ **Interactive Prompts**: If anything is missing, you'll be prompted to enter your `API Key`, `Base URL`, and `Model`.
3.  💾 **Secure, Local Storage**: Your credentials are saved securely in a local `.env` file for future use.

On subsequent runs, the setup is skipped, and you'll jump right into the chat.

## ⚙️ Configuration

Puti uses a flexible configuration system that prioritizes environment variables.

### 1. Guided Setup (Recommended)
As described in the Quick Start, running `puti alex-chat` for the first time will automatically guide you through creating a `.env` file. This is the easiest way to get started.

### 2. Manual Setup
You can also configure Puti by manually creating a `.env` file in your project's root directory.

```.env
# .env file
OPENAI_API_KEY="sk-..."
OPENAI_BASE_URL="https://api.openai.com/v1"
OPENAI_MODEL="gpt-4o-mini"
TWIKIT_COOKIE_PATH="/path/to/your/cookies.json"
```
The application will automatically load these variables on startup. System-level environment variables will also work and will override the `.env` file.


## 💡 Usage Examples

### 1. 🧑‍🎨 Agent Create
Create a `Debater` agent with `web search` tool.
```python
from puti.llm.roles import Role
from typing import Any
from puti.llm.tools.web_search import WebSearch

class Debater(Role):
    """ A debater agent with web search tool can find latest information for debate. """
    name: str = '乔治'

    def model_post_init(self, __context: Any) -> None:
        
        # setup tool here
        self.set_tools([WebSearch])
```

### 2. 🗣️ Multi Agent Debate
Set up two agents for a debate quickly.
```python
from puti.llm.roles import Role
from puti.llm.envs import Env
from puti.llm.messages import Message

# Debater
Ethan = Role(name='Ethan', identity='Affirmative Debater')
Olivia = Role(name='Olivia', identity='Opposition Debater')

# create a debate contest and put them in contest
env = Env(
    name='debate contest',
    desc="""Welcome to the Annual Debate Championship..."""
)
env.add_roles([Ethan, Olivia])

# topic
topic = '科技发展是有益的还是有害的？ '

# create a message start from Ethan
msg = Message(content=topic, sender='user', receiver=Ethan.address)
# Olivia needs user's input as background, but don't perceive it
Olivia.rc.memory.add_one(msg)

# then we publish this message to env
env.publish_message(msg)

# start the debate in 5 round
env.cp.invoke(env.run, run_round=5)

# we can see all process from history
print(env.history)
```

### 3. 👨‍💻 Alex Agent in Code
`Alex` is an mcp agent equipped with `web search`, `file tool`, `terminal tool`, and `python tool` capabilities.
```python
from puti.llm.roles.agents import Alex

alex = Alex()
resp = alex.run('What major news is there today?')
print(resp)
```

### 4. 🔧 Custom your MCP Agent
Server equipped with `web search`, `file tool`, `terminal tool`, and `python tool`
```python
from puti.llm.roles import McpRole

class SoftwareEngineer(McpRole):
    name: str = 'Rock'
    skill: str = 'You are proficient in software development, including full-stack web development, software architecture design, debugging, and optimizing complex systems...'
    goal: str = 'Your goal is to design, implement, and maintain scalable and robust software systems that meet user requirements and business objectives...'
```

### 5. 📅 Task Scheduler (`puti scheduler`)
Puti includes a powerful, built-in task scheduler for automating recurring tasks. It runs as a persistent background process powered by Celery and can be managed entirely from the command line.

![Puti Scheduler Logs](examples/puti_scheduler.png)

A few key commands:
```bash
# Start, stop, or check the status of the scheduler daemon
puti scheduler start
puti scheduler stop
puti scheduler status

# List all scheduled tasks
puti scheduler list

# Create a task to run every 5 minutes
# It's disabled by default; enable it with `puti scheduler enable <ID>`
puti scheduler create my_task "*/5 * * * *" --type "post" --params '{"topic": "AI News"}'

# Follow the real-time logs for all tasks
# Other options like --filter, --level are also available
puti scheduler logs --follow
```

## 📜 Development History

Puti has evolved significantly since its inception. Here are some of the key milestones in its journey:

-   **🌱 Phase 1: Foundation & Core Concepts (4 months ago)**
    -   The project was born with the core concepts of `Agent`, `Environment`, and `Message`.
    -   The initial use case was a multi-agent `Debate` scenario, establishing the foundation for agent collaboration.
    -   Support for multiple LLM providers, including `Ollama` and `Deepseek`, was integrated early on.

-   **🛠️ Phase 2: Tooling & Agent Capabilities (3-4 months ago)**
    -   A powerful tool system was introduced, equipping agents with `terminal`, `python`, `file I/O`, and `web_search` capabilities through Function Calling.
    -   The `MCP` (Multi-agent Collaboration Protocol) was established to standardize agent interactions.

-   **🐦 Phase 3: Twitter Automation & Scheduling (2-3 months ago)**
    -   The focus shifted towards practical automation with deep integration of `Twikit` for Twitter operations.
    -   A robust, persistent task scheduler, powered by `Celery` and `Celery Beat`, was built to handle recurring tasks like automated posts and replies.
    -   This phase laid the groundwork for creating autonomous social media agents.

-   **🧠 Phase 4: Intelligent Agents & Framework Refinement (1-2 months ago)**
    -   Ready-to-use, pre-built agents like `Alex` (a general-purpose assistant) and `Ethan` (a Twitter specialist) were created.
    -   Advanced concepts such as `RAG` (Retrieval-Augmented Generation) and enhanced memory systems were explored to make agents smarter.
    -   The `puti` CLI was born, providing a user-friendly entry point for interacting with the framework.

-   **🚀 Phase 5: CLI Enhancement & Code Refactoring (Recent)**
    -   The command-line interface, especially `puti scheduler`, was significantly enhanced with features like real-time logs, status checks, and dynamic task management.
    -   Major code refactoring, such as moving the `celery_queue` module into the main `puti` package, was undertaken to improve project structure and maintainability.
    -   Continuous bug fixes and refinements to solidify the framework's stability and reliability.

## 🌟 Our Vision

Our goal for Puti is to build more than just a framework; we aim to cultivate a vibrant, open-source ecosystem for multi-agent AI. We envision a future where developers and researchers can easily create, share, and deploy sophisticated autonomous agents that tackle real-world challenges.

We are committed to making Puti a benchmark for reliability, flexibility, and ease of use. With the support of the community, we hope to grow Puti into a highly successful and impactful project that pushes the boundaries of what's possible with collaborative AI.

## 📚 Documentation

For detailed documentation, please refer to:

- **[Project Description](docs/proj/description.md)**: An overview of Puti's goals and architecture.
- **[CLI Guide](docs/proj/cli.md)**: Instructions for using the command-line interface.
- **[Agent Patterns](docs/agent/)**: Guides for single-agent and multi-agent patterns.
- **[Integration Guides](docs/integration/)**: Detailed instructions for integrations like MCP, Celery, and Twitter.
- **[Memory Optimization](docs/proj/memory_optimization.md)**: Guide to optimize token usage by controlling historical search.
- **[Roadmap](docs/proj/ROADMAP.MD)**: The future development plan for Puti.

## 🙏 Acknowledgements

Puti is inspired by and builds upon the work of several outstanding open-source projects in the multi-agent and LLM space. We extend our heartfelt gratitude to the developers and communities behind these projects:

-   [**MetaGPT**](https://github.com/geekan/MetaGPT): For pioneering the concept of role-based multi-agent collaboration and providing a strong foundation for structured, human-like workflows.
-   [**OpenManus**](https://github.com/aivoyager/openmanus): For its innovative approach to long-term memory and self-improving agents, which has been influential in shaping our memory management system.
-   [**AgentScope**](https://github.com/modelscope/agentscope): For its flexible and easy-to-use multi-agent framework, which has been a great reference for our agent communication and environment design.
-   [**LangGraph**](https://github.com/langchain-ai/langgraph): For its powerful graph-based approach to building stateful, multi-agent applications, which has inspired our own graph and workflow patterns.

We are grateful for their contributions to the open-source community, which have made projects like Puti possible.

## 🤝 Contributing

We welcome contributions to Puti! Please see our [Contributing Guide](CONTRIBUTING.md) for more details on how to get started.

## 📄 License

Puti is licensed under the [MIT License](LICENSE). 