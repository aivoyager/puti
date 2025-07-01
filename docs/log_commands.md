# Puti 日志命令使用指南

## 实时日志查看

从 Puti 的日志文件中查看日志信息并支持实时跟踪日志输出。

### 基本用法

```bash
# 查看服务的最新日志（默认显示20行）
python -m puti scheduler logs worker
python -m puti scheduler logs scheduler
python -m puti scheduler logs beat

# 使用测试脚本（更简便）
python test/test_logs_command.py worker
python test/test_logs_command.py scheduler
```

### 实时跟踪选项

使用 `-f` 或 `--follow` 选项可以实时查看日志输出：

```bash
# 实时查看 worker 日志
python -m puti scheduler logs worker -f

# 使用测试脚本
python test/test_logs_command.py worker -f
```

实时查看模式下，按 `Ctrl+C` 可以退出日志查看。

### 过滤选项

#### 按关键字过滤

使用 `--filter` 选项可以按关键字过滤日志：

```bash
# 只显示包含 "ERROR" 的日志行
python -m puti scheduler logs worker --filter ERROR

# 使用测试脚本
python test/test_logs_command.py worker --filter ERROR
```

#### 按日志级别过滤

使用 `--level` 选项可以按最低日志级别过滤：

```bash
# 只显示 WARNING 级别及以上的日志
python -m puti scheduler logs worker --level WARNING

# 使用测试脚本
python test/test_logs_command.py worker --level WARNING
```

可用的日志级别有：
- DEBUG（最低级别）
- INFO
- WARNING
- ERROR
- CRITICAL（最高级别）

### 显示格式选项

#### 简化格式

使用 `--simple` 选项可以以简化格式显示日志（不显示时间戳）：

```bash
python -m puti scheduler logs worker --simple

# 使用测试脚本
python test/test_logs_command.py worker --simple
```

#### 原始格式

使用 `--raw` 选项可以以原始格式显示日志（不进行格式化）：

```bash
python -m puti scheduler logs worker --raw

# 使用测试脚本
python test/test_logs_command.py worker --raw
```

### 限制显示行数

使用 `-n` 或 `--lines` 选项可以限制显示的日志行数：

```bash
# 显示最新的5行日志
python -m puti scheduler logs worker -n 5

# 使用测试脚本
python test/test_logs_command.py worker -n 5
```

### 组合选项

这些选项可以组合使用：

```bash
# 实时查看最近10行WARNING及以上级别日志，使用简化格式
python -m puti scheduler logs worker -f -n 10 --level WARNING --simple

# 过滤包含"ERROR"关键字的最近20行日志
python -m puti scheduler logs worker --filter ERROR -n 20

# 使用测试脚本
python test/test_logs_command.py worker -f -n 10 --level WARNING --simple
```

## 刷新Worker和Beat进程

在代码更改后，需要重启Celery worker和beat进程才能使更改生效。`refresh`命令提供了便捷的方式来完成这一操作。

### 基本用法

```bash
# 同时刷新worker和beat进程
python -m puti.cli scheduler refresh

# 只刷新worker进程
python -m puti.cli scheduler refresh --beat=False

# 只刷新beat进程（调度器）
python -m puti.cli scheduler refresh --worker=False
```

### 强制刷新

如果进程无法正常停止，可以使用`--force`选项强制停止进程：

```bash
# 强制刷新所有进程
python -m puti.cli scheduler refresh --force
```

### 工作流程

`refresh`命令的工作流程：

1. 停止指定的进程（worker和/或beat）
2. 启动新的进程，加载最新的代码更改
3. 显示操作结果

### 何时使用

在以下情况下，您应该使用`refresh`命令：

- 修改了任务代码后（如`simplified_tasks.py`）
- 修改了工具代码后（如`twikitt.py`）
- 修改了数据库管理代码后（如`task_state_guard.py`）
- 修改了任何会被worker或beat进程使用的代码后

使用`refresh`命令可以确保您的更改被立即应用，而不需要手动停止和启动进程。

## 注意事项

1. 实时跟踪（`-f`）选项在有些终端环境下可能会有显示延迟
2. 过滤条件对不符合标准日志格式的行可能无法正确应用
3. 在较大的日志文件上，加载时可能会有短暂延迟 