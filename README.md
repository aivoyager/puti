# Puti - Multi-Agent Framework

<p align="center">
    <em>Tackle complex tasks with autonomous agents.</em>
</p>

<p align="center">
    <a href="./README.md">
        <img src="https://img.shields.io/badge/document-English-blue.svg" alt="EN doc">
    </a>
    <a href="https://opensource.org/licenses/MIT">
        <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
    </a>
    <a href="./docs/ROADMAP.MD">
        <img src="https://img.shields.io/badge/ROADMAP-ROADMAP-blue.svg" alt="Roadmap">
    </a>
</p>

<p align="center">
    <!-- Project Stats -->
    <a href="https://github.com/aivoyager/puti/issues">
        <img src="https://img.shields.io/github/issues/aivoyager/puti" alt="GitHub issues">
    </a>
    <a href="https://github.com/aivoyager/puti/network">
        <img src="https://img.shields.io/github/forks/aivoyager/puti" alt="GitHub forks">
    </a>
    <a href="https://github.com/aivoyager/puti/stargazers">
        <img src="https://img.shields.io/github/stars/aivoyager/puti" alt="GitHub stars">
    </a>
    <a href="https://github.com/aivoyager/puti/blob/main/LICENSE">
        <img src="https://img.shields.io/github/license/aivoyager/puti" alt="GitHub license">
    </a>
    <a href="https://star-history.com/#aivoyager/puti">
        <img src="https://img.shields.io/github/stars/aivoyager/puti?style=social" alt="GitHub star chart">
    </a>
</p>

## ✨ Introduction

Puti is a Multi-Agent framework designed to tackle complex tasks through collaborative autonomous agents. It provides a flexible environment for building, managing, and coordinating various agents to achieve specific goals.

## 🚀 Features

*   **Multi-Agent Collaboration**: Supports communication and collaboration between multiple agents.
*   **Flexible Agent Roles**: Allows defining agent roles with different goals and capabilities (e.g., Talker, Debater).
*   **Powerful Tools**: Agents are equipped with `web search`, `file tool`, `terminal tool`, and `python tool` capabilities.
*   **Environment Management**: Provides environment for managing agent interactions and message passing.
*   **Configurable**: Easily configure LLM providers and other settings through YAML files.
*   **Extensible**: Easy to build and integrate your own agents and tools.

## 📦 Installation

Clone the repository and install required dependencies:
```bash
pip install ai-puti
```

```bash
git clone https://github.com/aivoyager/puti.git
cd puti
pip install -r requirements.txt
```

## 💡 Usage Examples

### 1. Agent Create
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

### 2. Multi Agent Debate

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
    desc="""Welcome to the Annual Debate Championship, a dynamic forum where critical thinking, persuasive speaking, and intellectual rigor converge.  This competition brings together talented debaters from diverse backgrounds to engage in structured argumentation on pressing contemporary issues.  Participants will compete in teams, presenting arguments for or against a given motion, while being judged on clarity, evidence, rebuttal strength, and overall delivery.
The goal of this debate is not only to win points but to foster respectful discourse, challenge assumptions, and inspire new perspectives.  Whether you are a passionate speaker or a curious listener, this event promises thought-provoking dialogue and high-level competition.
          """
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

### 3. Alex Agent

`Alex` is an mcp agent equipped with `web search`, `file tool`, `terminal tool`, and `python tool` capabilities. This section demonstrates its basic functionality.<br>
You can even ask him to `write code` or `fix code` for you.
```python
from puti.llm.roles.agents import Alex

alex = Alex()

# using search tool here find result for free
resp = alex.cp.invoke(alex.run, 'What major news is there today?')
print(resp)
```

### 4. Custom your MCP Agent
Server equipped with `web search`, `file tool`, `terminal tool`, and `python tool`
```python
from puti.llm.roles import McpRole

class SoftwareEngineer(McpRole):
    name: str = 'Rock'
    skill: str = 'You are proficient in software development, including full-stack web development, software architecture design, debugging, and optimizing complex systems. You have expertise in programming languages such as Python, JavaScript, and C++, and are skilled in using tools like Git, Docker, and CI/CD pipelines. You are capable of writing clean, maintainable code, conducting code reviews, and collaborating effectively in agile development teams.'
    goal: str = 'Your goal is to design, implement, and maintain scalable and robust software systems that meet user requirements and business objectives. You aim to continuously improve code quality, ensure timely delivery of features, and contribute to the overall success of the engineering team and product.'
```

## ⚙️ Configuration

Configure your LLM provider and other settings in `conf/config.yaml` by `demo file`:

```yaml
# conf/config.yaml
llm:
    - openai:
        MODEL: "gpt-4o-mini"  # Or your preferred model
        BASE_URL: "YOUR_OPENAI_COMPATIBLE_API_BASE_URL" # e.g., https://api.openai.com/v1
        API_KEY: "YOUR_API_KEY"
        MAX_TOKEN: 4096
    - llama: # Example for Ollama
        BASE_URL: "http://localhost:11434" # Your Ollama server address
        MODEL: "llama3.1:latest"
        STREAM: true
    # Add other LLM configurations as needed
```

Access configuration in your code:
```python
from puti.conf.llm_config import OpenaiConfig, LlamaConfig

# Access OpenAI configuration
openai_conf = OpenaiConfig()
print(f"Using OpenAI Model: {openai_conf.MODEL}")

# Access Llama configuration
llama_conf = LlamaConfig()
print(f"Using Llama Model: {llama_conf.MODEL}")
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

