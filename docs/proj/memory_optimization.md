# Memory 优化选项

在多轮对话时，Puti框架默认使用RAG技术来检索相关历史对话，以帮助Agent更好地理解上下文。然而，这种检索操作会消耗额外的token。本文档介绍如何通过配置选项来优化内存使用和token消耗。

## 禁用历史搜索功能

在创建Role实例或调用`run`方法时，可以设置`disable_history_search`参数来禁用历史检索功能：

```python
# 方式1: 在创建Role时禁用历史检索
agent = Alex(disable_history_search=True)

# 方式2: 在运行时临时禁用历史检索
response = await agent.run(msg="你好", disable_history_search=True)
```

### 禁用历史搜索的好处

1. **减少Token消耗**: 对于长对话，不执行历史检索可以显著减少token使用量。
2. **提高响应速度**: 跳过检索过程可以加快响应时间。
3. **适用于简单任务**: 对于无需大量上下文的简单问答，可以禁用历史检索。

### 何时应该启用历史搜索

1. **复杂任务**: 对于需要参考过去对话的复杂任务，应保持历史检索功能。
2. **知识密集型对话**: 当对话包含大量信息，Agent需要回忆起之前提到的细节时。
3. **专业领域交互**: 在专业领域（如医疗、法律等）的对话中，准确性优先于token节省。

## 技术实现

`disable_history_search`参数作用于`Role._think`方法，控制是否执行`memory.search`操作：

```python
# _think方法中的相关代码片段
relevant_history = []
if not self.disable_history_search and last_user_message and last_user_message.content:
    # 只在未禁用历史检索时执行搜索
    relevant_history = await self.rc.memory.search(last_user_message.content)
```

## 注意事项

- 默认情况下，`disable_history_search`为`False`，即启用历史检索功能。
- 可以在一次对话中动态切换此参数，以适应不同的对话阶段需求。
- 对于图形工作流中的`GraphRole`，此参数同样适用。

## 性能数据

根据初步测试，在多轮对话中禁用历史检索可以减少约15-30%的token使用量，具体取决于对话历史的长度和复杂性。 