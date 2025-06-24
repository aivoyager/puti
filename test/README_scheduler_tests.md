# 调度器测试说明

本目录包含针对puti调度器功能的各种测试，包括命令行界面、执行逻辑和集成测试。

## 测试文件结构

- `test_scheduler_cli.py`: 测试调度器的命令行接口功能
- `test_scheduler_execution.py`: 测试调度任务的执行逻辑
- `test_scheduler_integration.py`: 测试调度器的完整集成功能
- `test_scheduler_all.py`: 一次性运行所有调度器相关测试的脚本

## 主要测试内容

### 命令行接口测试 (test_scheduler_cli.py)

- 测试帮助信息显示
- 测试列出计划任务（带各种过滤选项）
- 测试创建计划任务（带任务类型支持）
- 测试启用/禁用计划任务
- 测试删除计划任务
- 测试状态检查命令
- 测试参数解析和验证
- 测试无效参数处理

### 执行逻辑测试 (test_scheduler_execution.py)

- 测试任务状态跟踪（针对不同任务类型）
- 测试cron表达式解析和下一次运行时间计算
- 测试多个调度任务的并发执行
- 测试任务参数传递

### 集成测试 (test_scheduler_integration.py)

- 测试创建和检索调度
- 测试列出所有调度（包括按任务类型筛选）
- 测试更新调度（包括任务类型变更）
- 测试启用/禁用调度功能
- 测试删除调度
- 测试调度器守护进程的启动和停止
- 测试命令行接口与调度器的集成

## 任务类型支持

最近添加的功能是支持多种任务类型，包括：

- `post`: 发推任务（默认类型）
- `reply`: 回复任务
- `retweet`: 转发任务
- `like`: 点赞任务
- `follow`: 关注任务
- `notification`: 通知任务
- `analytics`: 数据分析任务
- `content_curation`: 内容策划任务
- `scheduled_thread`: 计划线程任务
- `other`: 其他任务

所有测试都已更新以支持和验证这些新的任务类型。

## 运行测试

可以通过以下命令运行所有调度器测试：

```bash
python -m test.test_scheduler_all
```

或者单独运行特定的测试文件：

```bash
python -m pytest test/test_scheduler_cli.py -v
python -m pytest test/test_scheduler_execution.py -v
python -m pytest test/test_scheduler_integration.py -v
```

## 注意事项

- 某些测试依赖于Celery后台任务系统，需要确保Celery环境正确配置
- 测试使用SQLite数据库，不会影响生产环境
- 测试会自动创建和管理必要的目录和文件结构
- 部分测试（如`test_cli_commands`）被跳过，因为它们依赖于特定的环境设置或需要额外的进程控制 