<h1 align="center"><strong>voyager_alpha base on multi agent</strong></h1>
<p align="center" style="color: aqua"><b>Tackle complex tasks</b></p>

<p align="center">
    <a href="./README.md">
        <img src="https://img.shields.io/badge/document-English-blue.svg" alt="EN doc">
    </a>
    <a href="https://opensource.org/licenses/MIT">
        <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
    </a>
    <a href="./docs/ROADMAP.MD">
        <img src="https://img.shields.io/badge/ROADMAP-ROADMAP-blue.svg" alt="License: MIT">
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

## install req for dev
```shell
pip install -r requirements.txt
```

## Get Started
### 😁 chat:

```python
from llm.roles.talker import PuTi
from llm.nodes import ollama_node

msg = 'what is calculus'
talker = PuTi(agent_node=ollama_node)
msg = talker.cp.invoke(talker.run, msg)
```
### 🧰 chat with mcp
```python
from llm.envs import Env
from llm.roles.talker import PuTiMCP
from llm.messages import Message

env = Env()
talker = PuTiMCP()  # inherit from PuTiMCP, then call tools from mcp server
env.add_roles([talker])
msg = 'How long is the flight from New York(NYC) to Los Angeles(LAX)'
env.publish_message(Message.from_any(msg))
asyncio.run(env.run())
```

### 🗣️️ debate
```python
from llm.envs import Env
from llm.messages import Message
from llm.roles.debater import Debater

env = Env(name='game', desc='play games with other')
debater1 = Debater(name='alex', goal='make a positive point every round of debate. Your opponent is rock')
debater2 = Debater(name='rock', goal='make a negative point every round of debate. Your opponent is alex')
env.add_roles([debater1, debater2])
message = Message.from_any(
    f'现在你们正在进行一场辩论赛，主题为：科技发展是有益的，还是有弊的？',
    receiver=debater1.address,
    sender='user'
)
debater2.rc.memory.add_one(message)
env.publish_message(message)
env.cp.invoke(env.run)  # run
print(env.history)
```
### 🔑 configuration file
```yaml
# storage in conf/config.yaml
llm:
    - openai:
        MODEL: "gpt-4o-mini"
        BASE_URL: "your base url"
        API_KEY: "your api key"
        MAX_TOKEN: 4096
    - llama:
        BASE_URL: "Your ollama server"  # ollama
        MODEL: "llama3.1:latest"
        STREAM: true
```

```python
# Access openai config
from conf.llm_config import OpenaiConfig

# then you can check your configuration at here
openai_conf = OpenaiConfig()
```
🛠 Build project with own agent

coming soon

