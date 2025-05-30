
# Puti - MultiAgent Based Project

## 项目概述

本项目构建了一个基于大型语言模型（LLM）的、支持多 Agent 协作的智能系统框架。其核心目标是模拟一个由多个具有不同角色和能力的智能体（Role）组成的团队，通过MCP通信协议和任务调度机制，协同完成复杂的用户请求。系统设计强调模块化、可扩展性和灵活性，允许开发者方便地定义新的 Role 类型、集成外部工具、定制 Role 行为以及扩展通信协议。

项目的整体架构遵循分层和模块化的设计原则，确保了高内聚、低耦合，便于理解、开发和维护。

### 核心特性

* **多 Agent 架构:** 支持定义和管理多个不同类型的 Role，如辩论家、导游，采用 ReAct 模式。
* **目标驱动:** 以目标（goal）完成目的，对应阶段的任务分配给合适的 Role（Agent） 处理。
* **协作机制:** Role 之间通过消息中心（MessagePool）进行交互，实现任务委托、信息共享和结果汇报。
* **模块化设计:** 将核心逻辑（Core）、Role 定义（Role）、LLM 接口（LLM）、记忆模块（Memory）、提示工程（Prompt）、数据结构（Schema）、工具（Tools）和工具函数（Utils）清晰分离，易于维护和扩展。
* **LLM 集成:** 提供了基础的 LLM 接口及模型部署接口，方便 Role 调用 LLM 完成推理、生成等任务。
* **工具使用:** Role 可以利用集成的外部工具（如计算器、搜索引擎）（MCP）来增强其解决问题的能力。
* **记忆管理:** 为 Role 提供了记忆模块，使其能够存储和检索历史信息，保持对话或任务的上下文。

### 模块划分与职责

项目主要划分为以下几个核心模块：

1. **`env` (环境):** 环境模块来存储和管理所有的 Role 和消息池。许多Role 在这个环境来共享信息和执行任务。

2. **`agent` (Role 模块):** 定义了 Role 的基本接口，如 `run` 方法（执行任务的主逻辑）集成 LLM、Memory 和 Tools。 以及McpRole 的基本接口，处理 MCP 消息的方法等，来访问服务端的Tools。

3. **`node` (llm节点):** 封装了与大型语言模型的交互。

4. **`cost` (llm花费):** 为不同的llm提供了花费管理。

5. **`message` (消息模块):** 封装了与沟通的基础单元。

6. **`tool` (工具模块):** 封装了 Role 可以调用的外部工具。

7. **`utils` (工具函数模块):** 提供项目中可复用的辅助函数。

### Multi-Agent 协作流程

1. **Role 定义与注册:**
   * `Role` 类定义了智能体的基本结构。
   * 通过 `Environment.add_role(role)` 方法将 `Role` 实例注册到环境中。
   * `Role` 定义通过 `Environment.add_role(role)` 添加。每个 `Role` 在初始化或注册时会关联一个 `Role`。

2. **调度与执行:**
   * `env.run()` 方法是协作的总入口和调度器。基于轮询负责启动和管理整个交互过程。
   * 当环境运行时，`Role` 通过 `_perceive` 方法从 `env` 的 `memory` 或通知中获取相关 `Message`。

3. **任务协作 (基于消息):**
   * 协作的核心是基于 `Message` 的协程异步通信。
   * 一个 `Role` (通过其 `Role` 的 `_react` 方法) 根据当前用户需求，可以决定创建一个 `Message` 并通过 `_publish_message` 将left over部分发送给其他role。
   * `Message` 可以是广播或定向发送 (通过 `send_to` 字段)。
   * 其他 `Role` 在观察到相关 `Message` 后，其 `_perceive` 方法会被触发，进而根据其 `Role` 定义的目标和逻辑进行思考 (`_think`) 和行动 (`_react`)，可能产生新的 `Message`，从而形成协作链条。

### Multi-Role ReAct Chain

1. **perceive — 感知环境中的输入**
   * 作用：
     * 监听环境或通信通道中的新消息。
     * 将接收到的消息存储在内部状态（如 rc.memory）中，供后续思考使用。
   * 特点：
     * 被动行为，不做任何加工处理。
     * 仅负责“看见”或“听到”。

2. **think — 思考推理**
   * 作用：
     * 根据已有的对话历史、角色设定（system prompt）、目标等上下文信息、目标完成情况，调用模型进行一次推理生成判断下一步应该做的操作。
     * 输出可能是：
       * 普通文本回复
       * 工具调用指令（function call）
   * 特点：
     * 主动推理，生成可执行意图。
     * 产物通常为 LLM 的输出消息，需要进一步解释或执行。

3. **react — 执行动作**
   * 作用：
     * 解析 think 阶段模型生成的结果：
       * 如果是工具调用请求，执行对应工具函数，并收集输出。
       * 如果是普通回复，直接准备发送。
     * 将最终处理完成的消息放入通道中，完成一个交互周期。
   * 特点：
     * 连接推理与现实。
     * 具备执行、调用、错误处理等能力。

### McpRole 集成了MCP功能的Role

1. **核心通信机制 **

   MCP 是 Role（智能体）之间进行通信和协作的基础协议。通过 MCP 和任务调度机制，让不同的 Role 能够协同工作，共同完成复杂的用户请求。

2. **访问外部工具**

   MCP设置可让 Role 访问和利用集成的外部工具（如计算器、搜索引擎等）。存在一个 MCP 服务端，托管这些工具供 Role 调用，以增强其解决问题的能力。

3. **McpRole 接口**

   定义了 McpRole 的基本接口，包含了处理 MCP 消息的方法，通过McpRole可直接调用。

### FrameWork

该框架通过环境、智能体、消息、Mcp的分离，及基于消息的通信机制，实现了一个灵活、可扩展的多智能体协作系统。

![img_v3_02l0_093dab27-bbb7-43b7-94ff-2c32a09212dg](/Users/wangshuang/Downloads/puti/img_v3_02l0_093dab27-bbb7-43b7-94ff-2c32a09212dg.png)