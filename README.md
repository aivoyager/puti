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

## Get Started
### 😁chat
```python
from llm.roles.talker import Talker

msg = 'hello, what is u name'
talker = Talker()
msg = talker.cp.invoke(talker.run, msg)
print(msg.data)
```
### 🗣️️ debate
```python
from llm.envs import Env
from llm.messages import Message
from llm.roles.debater import Debater

env = Env(name='game', desc='play games with other')
debater1 = Debater(name='bot1')
debater2 = Debater(name='bot2')
env.add_roles([debater1, debater2])
env.publish_message(Message.from_any(
    f'现在你们正在进行一场辩论赛，主题为：科技发展是有益的，还是有弊的？{debater1}为正方 {debater2}为反方',
    receiver=debater1.address
))
env.cp.invoke(env.run)
```
### 🔑 configuration
```yaml
# conf/config.yaml
client:
  - twitter:
      BEARER_TOKEN: "You twikit bearer token"
llm:
  - openai:
      MODEL: "gpt-4o-mini"
```

```python
# Access openai config
from conf import OpenaiConfig

openai_conf = OpenaiConfig()
```
🛠 Build project with own agent

```python
import puti
```

