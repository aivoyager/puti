# `puti scheduler create` 命令详细文档

## 命令概述

`puti scheduler create` 命令用于在 Puti 调度系统中创建新的定时任务。这些任务可以按照指定的时间表自动执行，例如发布推文、回复提及或进行其他 Twitter 相关操作。

## 基本语法

```bash
puti scheduler create NAME CRON_SCHEDULE --type TASK_TYPE [--params JSON_PARAMS]
```

## 必需参数

1. **`NAME`**
   - 任务的唯一名称
   - 用于在列表和日志中标识任务
   - 示例：`daily_ai_tweet`, `hourly_replies`

2. **`CRON_SCHEDULE`**
   - 标准 cron 表达式，定义任务的执行时间表
   - 格式：`分 时 日 月 周`（与标准 cron 格式相同）
   - 示例：
     - `0 12 * * *` - 每天中午 12 点执行
     - `0 * * * *` - 每小时整点执行
     - `*/15 * * * *` - 每 15 分钟执行一次
     - `0 9 * * 1-5` - 工作日（周一至周五）上午 9 点执行

3. **`--type TASK_TYPE`**
   - 指定任务的类型
   - 可用值：
     - `post` - 生成并发布推文
     - `reply` - 回复最近的未回复推文
     - `context_reply` - 带有完整对话上下文的智能回复
     - `retweet` - 转发推文（目前未实现）
     - `like` - 点赞推文（目前未实现）
     - `follow` - 关注用户（目前未实现）

## 可选参数

1. **`--params JSON_PARAMS`**
   - 任务特定参数的 JSON 字符串
   - 默认值：`{}`（空对象）
   - 根据任务类型需要不同的参数（见下文）

## 任务类型及其参数

### 1. `post` 类型（发布推文）

发布类型的任务会让 Ethan 生成并发布一条推文。

**参数：**
```json
{
  "topic": "话题名称或描述"
}
```

**示例：**
```bash
# 创建每天中午发布关于 AI 的推文的任务
puti scheduler create daily_ai_tweet "0 12 * * *" --type post --params '{"topic": "AI 技术最新进展"}'

# 创建每周一发布关于数据科学的推文的任务
puti scheduler create weekly_datascience "0 10 * * 1" --type post --params '{"topic": "数据科学趋势和应用"}'
```

### 2. `reply` 类型（回复推文）

回复类型的任务会让 Ethan 查找并回复一定时间范围内的未回复推文。

**参数：**
```json
{
  "time_value": 数值,  // 查找多长时间内的推文
  "time_unit": "单位"   // "hours" 或 "days"
}
```

**示例：**
```bash
# 创建每小时回复过去 24 小时内未回复推文的任务
puti scheduler create hourly_replies "0 * * * *" --type reply --params '{"time_value": 24, "time_unit": "hours"}'

# 创建每天回复过去 3 天内未回复推文的任务
puti scheduler create daily_replies "0 9 * * *" --type reply --params '{"time_value": 3, "time_unit": "days"}'
```

### 3. `context_reply` 类型（上下文感知回复）

上下文感知回复任务会让 Ethan 查找未回复的提及，获取完整的对话上下文，然后生成更智能、更连贯的回复。

**参数：**
```json
{
  "time_value": 数值,       // 查找多长时间内的提及
  "time_unit": "单位",       // "hours" 或 "days"
  "max_mentions": 数值,     // 最多处理多少条提及，默认为 3
  "max_context_depth": 数值  // 追溯对话历史的最大深度，默认为 5
}
```

**示例：**
```bash
# 创建每 3 小时回复过去 12 小时内未回复提及的任务，最多处理 5 条提及
puti scheduler create context_replies "0 */3 * * *" --type context_reply --params '{"time_value": 12, "time_unit": "hours", "max_mentions": 5, "max_context_depth": 5}'

# 创建每天早上回复过去 24 小时内未回复提及的任务，限制为 2 条提及
puti scheduler create morning_replies "0 8 * * *" --type context_reply --params '{"time_value": 24, "time_unit": "hours", "max_mentions": 2}'
```

## 重要说明

1. **新创建的任务默认是禁用状态**
   - 创建后需要使用 `puti scheduler enable TASK_ID` 命令启用任务

2. **任务 ID 会在创建后显示**
   - 创建成功后，系统会显示分配给任务的 ID

3. **查看任务状态**
   - 使用 `puti scheduler list` 或 `puti scheduler status` 查看所有任务的状态

4. **Cron 表达式验证**
   - 系统会验证 cron 表达式的有效性，无效的表达式会导致错误

5. **任务类型验证**
   - 系统会验证任务类型的有效性，无效的类型会默认为 `unimplemented`

## 高级用例

### 组合多个任务

您可以创建多个互补的任务来构建完整的 Twitter 互动策略：

```bash
# 每天早上 9 点发布一条关于 AI 的推文
puti scheduler create morning_ai_post "0 9 * * *" --type post --params '{"topic": "AI 技术最新进展"}'

# 每 3 小时回复一次提及，确保及时响应
puti scheduler create regular_replies "0 */3 * * *" --type context_reply --params '{"time_value": 3, "time_unit": "hours"}'

# 每晚 10 点回复过去一整天的未回复推文
puti scheduler create nightly_catchup "0 22 * * *" --type reply --params '{"time_value": 1, "time_unit": "days"}'
```

### 调整任务频率

根据您的 Twitter 活跃度调整任务频率：

- 对于高活跃度账户，可以增加回复任务的频率
- 对于内容创作，可以设置在一天中不同时间发布不同主题的推文

## 故障排除

1. **参数解析错误**
   - 确保 JSON 参数格式正确，使用双引号包裹键名
   - 在命令行中使用 JSON 时，外层需要使用单引号

2. **Cron 表达式错误**
   - 确保 cron 表达式格式正确
   - 使用在线 cron 表达式生成器来帮助创建有效的表达式

3. **任务未执行**
   - 检查调度器是否正在运行：`puti scheduler status`
   - 确保任务已启用：`puti scheduler list`
   - 检查日志：`puti scheduler logs` 