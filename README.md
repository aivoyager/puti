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

