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

### 1. Basic Chat

Simple conversation with a single agent.

```python
from llm.roles.talker import PuTi
from llm.nodes import ollama_node  # Or your preferred LLM node

msg = 'What is calculus?'
talker = PuTi(agent_node=ollama_node)
response = talker.cp.invoke(talker.run, msg)
print(response)
```

### 2. Chat with MCP

Interact with an agent that can call external tools using Message Coordination Protocol (MCP).

```python
import asyncio
from llm.envs import Env
from llm.roles.talker import PuTiMCP
from llm.messages import Message

env = Env()
talker = PuTiMCP()  # This agent can potentially call tools via MCP server
env.add_roles([talker])

msg = 'How long is the flight from New York (NYC) to Los Angeles (LAX)?'
env.publish_message(Message.from_any(msg))

asyncio.run(env.run())
print(env.history) # View the conversation history
```

### 3. Agent Debate

Set up two agents for a debate.

```python
import asyncio
from llm.envs import Env
from llm.messages import Message
from llm.roles.debater import Debater

env = Env(name='debate_game', desc='Agents debating a topic')

# Define two debaters with opposing goals
debater1 = Debater(name='Alex', goal='Present positive arguments in each debate round. Your opponent is Rock.')
debater2 = Debater(name='Rock', goal='Present negative arguments in each debate round. Your opponent is Alex.')

env.add_roles([debater1, debater2])

# Start the debate
topic = 'Is technological development beneficial or harmful?'
initial_message = Message.from_any(
    f'You are now participating in a debate. The topic is: {topic}',
    receiver=debater1.address, # Start with debater1
    sender='user'
)

# Add message to the other debater's memory as well
debater2.rc.memory.add_one(initial_message)

env.publish_message(initial_message)

# Run the environment asynchronously
asyncio.run(env.run())

# Print the debate history
print(env.history)
```

## ⚙️ Configuration

Configure your LLM provider and other settings in `conf/config.yaml`:

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
from conf.llm_config import OpenaiConfig, LlamaConfig

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

