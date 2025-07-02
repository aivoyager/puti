# Celery Integration

This document explains how to use Celery with Puti for task scheduling and asynchronous processing, especially for automated Twitter interactions.

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Task Scheduler](#task-scheduler)
  - [Architecture](#architecture)
  - [Task Types](#task-types)
  - [CLI Management](#cli-management)
- [Custom Tasks](#custom-tasks)
- [Monitoring and Logs](#monitoring-and-logs)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Puti integrates with Celery to provide robust task scheduling capabilities, particularly for social media automation. The integration enables tasks like:

- Posting scheduled tweets on specific topics
- Automatically replying to Twitter mentions
- Performing periodic data collection and analysis
- Running agents on a schedule

## Setup

### Installation

To use the Celery integration, install Puti with the celery extra:

```bash
pip install ai-puti[celery]
```

### Configuration

The Celery configuration is managed through environment variables or a `.env` file:

```bash
# Celery broker URL (required)
CELERY_BROKER_URL="redis://localhost:6379/0"

# Celery result backend (optional)
CELERY_RESULT_BACKEND="redis://localhost:6379/0"

# Task database URL (for task persistence)
TASK_DATABASE_URL="sqlite:///path/to/tasks.db"
```

You can also adjust advanced settings in `puti/conf/celery_config.py` if needed.

## Task Scheduler

### Architecture

The Puti task scheduler consists of three components:

1. **Celery Beat**: Schedules tasks at specific times based on cron expressions
2. **Celery Worker**: Executes the scheduled tasks
3. **Task Database**: Stores task definitions, status, and execution history

### Task Types

The scheduler supports several pre-defined task types:

1. **Post Task**: Automatically generates and posts tweets on specified topics

   ```bash
   # Create a daily posting task
   puti scheduler create daily_tech_news "0 9 * * *" --type post --params '{"topic": "technology news"}'
   ```

2. **Reply Task**: Automatically responds to mentions on Twitter

   ```bash
   # Create a task to reply to mentions from the last 24 hours, running every hour
   puti scheduler create hourly_replies "0 * * * *" --type reply --params '{"time_value": 24, "time_unit": "hours"}'
   ```

### CLI Management

Manage the scheduler through the command-line interface:

```bash
# Start the scheduler
puti scheduler start

# Stop the scheduler
puti scheduler stop

# Check scheduler status
puti scheduler status

# List all scheduled tasks
puti scheduler list

# Enable/disable tasks
puti scheduler enable TASK_ID
puti scheduler disable TASK_ID

# Delete a task
puti scheduler delete TASK_ID

# View logs
puti scheduler logs --follow
```

## Custom Tasks

You can create custom tasks by extending the basic task classes:

```python
from celery_queue.simplified_tasks import BaseTask

class CustomTwitterTask(BaseTask):
    """A custom task that performs specialized Twitter operations"""
    
    name = "custom_twitter_task"
    
    async def run_task(self, **kwargs):
        """Main task logic goes here"""
        # Your custom implementation
        topic = kwargs.get('topic', 'general')
        # Use agents to perform the task
        from puti.llm.roles.agents import Ethan
        ethan = Ethan()
        result = await ethan.run(f"Write a tweet about {topic}")
        # Additional processing...
        return result

# Register the task
from celery_queue.celery_app import app
app.register_task(CustomTwitterTask())

# Schedule the task using the CLI
# puti scheduler create custom_task "*/30 * * * *" --type custom_twitter_task --params '{"topic": "AI research"}'
```

## Monitoring and Logs

### Viewing Task Logs

```bash
# View all task logs
puti scheduler logs

# Filter logs
puti scheduler logs --filter "error"
puti scheduler logs --level WARNING

# Follow logs in real-time
puti scheduler logs --follow
```

### Task Status and History

Task execution history is stored in the task database, which can be queried for monitoring and analysis.

```python
from puti.db.sqlite_operator import SQLiteOperator
from puti.constant.base import TaskStatus

# Connect to the task database
db = SQLiteOperator('path/to/tasks.db')

# Get task execution history
history = db.execute("SELECT * FROM task_executions ORDER BY execution_time DESC LIMIT 10")

# Get tasks with errors
failed_tasks = db.execute(
    "SELECT * FROM task_executions WHERE status = ?", 
    (TaskStatus.FAILED.value,)
)
```

## Best Practices

1. **Task Isolation**: Design tasks to be idempotent and independent to prevent side effects if a task is run multiple times

2. **Error Handling**: Implement robust error handling in custom tasks to prevent task failures

3. **Resource Management**: Set appropriate timeouts and concurrency limits to prevent resource exhaustion

4. **Monitoring**: Regularly check scheduler logs to ensure tasks are executing properly

5. **Database Maintenance**: Periodically clean up old task execution records to prevent database bloat

## Troubleshooting

### Common Issues

1. **Scheduler Won't Start**:
   - Check if Redis is running and accessible
   - Verify the CELERY_BROKER_URL is correct
   - Check log files for specific errors

2. **Tasks Not Running**:
   - Ensure the task is enabled
   - Check the cron expression for correctness
   - Verify the Celery worker is running

3. **Failed Tasks**:
   - Check the task logs for error details
   - Ensure required credentials are properly configured
   - Check network connectivity for tasks that require internet access

### Debugging

For advanced debugging, you can start the worker with increased verbosity:

```bash
# Start the worker with debug logging
celery -A celery_queue.celery_app worker --loglevel=DEBUG

# Start the beat scheduler with debug logging
celery -A celery_queue.celery_app beat --loglevel=DEBUG
```

### Resetting the Scheduler

If you need to completely reset the scheduler:

```bash
# Stop the scheduler
puti scheduler stop

# Delete the task database (be careful, this removes all task data)
rm path/to/tasks.db

# Start the scheduler fresh
puti scheduler start
```

For more help, consult the Puti GitHub repository or raise an issue if you encounter persistent problems. 