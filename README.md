# Puti - Multi-Agent Framework 🤖

<p align="center">
  <a href="https://github.com/aivoyager/puti">
    <img src="https://socialify.git.ci/aivoyager/puti/image?description=1&font=Inter&forks=1&issues=1&language=1&name=1&owner=1&pattern=Plus&stargazers=1&theme=Dark" alt="puti" width="650" height="325" />
  </a>
</p>

<p align="center">
    <em>An elegant multi-agent framework for building autonomous agents to tackle complex tasks.</em>
</p>

<p align="center">
    <a href="https://pypi.org/project/ai-puti/"><img src="https://img.shields.io/pypi/v/ai-puti.svg?style=flat-square&logo=pypi&logoColor=white" alt="PyPI version"></a>
    <a href="https://pypi.org/project/ai-puti/"><img src="https://img.shields.io/pypi/pyversions/ai-puti.svg?style=flat-square&logo=python&logoColor=white" alt="Python versions"></a>
    <a href="https://github.com/aivoyager/puti/blob/main/LICENSE"><img src="https://img.shields.io/github/license/aivoyager/puti?style=flat-square" alt="License"></a>
    <a href="https://github.com/aivoyager/puti/issues"><img src="https://img.shields.io/github/issues/aivoyager/puti?style=flat-square" alt="Issues"></a>
    <a href="https://github.com/aivoyager/puti/pulls"><img src="https://img.shields.io/github/issues-pr/aivoyager/puti?style=flat-square" alt="Pull Requests"></a>
</p>

## ✨ Introduction

Puti is a Multi-Agent framework designed to tackle complex tasks through collaborative autonomous agents. It provides a flexible environment for building, managing, and coordinating various agents to achieve specific goals.

## 🚀 Features

*   🤝 **Multi-Agent Collaboration**: Supports communication and collaboration between multiple agents.
*   🎭 **Flexible Agent Roles**: Allows defining agent roles with different goals and capabilities (e.g., Talker, Debater).
*   🛠️ **Powerful Tools**: Agents are equipped with `web search`, `file tool`, `terminal tool`, and `python tool` capabilities.
*   💡 **Interactive Setup**: Get started instantly with a guided setup for your credentials.
*   🌍 **Environment Management**: Provides an environment for managing agent interactions and message passing.
*   🧩 **Extensible**: Easy to build and integrate your own agents and tools.

## 📦 Installation

Install Puti directly from PyPI:
```bash
pip install ai-puti
```

Or, for development, clone the repository and install in editable mode:
```bash
git clone https://github.com/aivoyager/puti.git
cd puti
pip install -e .
```

## 🚀 Quick Start: Chat with Alex

Get started immediately with Puti's interactive, all-purpose AI assistant, Alex.

```bash
puti alex-chat
```

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

## 🤝 Contributing

Contributions are welcome! Please refer to the contribution guide (if available) or contribute by submitting Issues or Pull Requests.

1.  Fork the repository
2.  Create your Feature branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

_Let the Puti framework empower your multi-agent application development!_

