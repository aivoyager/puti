# Command-Line Interface (CLI) Guide

This document explains how to use the Puti command-line interface to interact with agents, manage the scheduler, and configure your environment.

## Table of Contents

- [Installation](#installation)
- [Agent Interaction](#agent-interaction)
  - [Alex Chat](#alex-chat)
  - [Ethan Chat](#ethan-chat)
- [Task Scheduler](#task-scheduler)
  - [Process Management](#process-management)
  - [Task Management](#task-management)
  - [Logging](#logging)
- [Configuration](#configuration)

## Installation

Before using the CLI, make sure Puti is installed:

```bash
pip install ai-puti
```

This will install the `puti` command-line tool with all its subcommands.

## Agent Interaction

### Alex Chat

Alex is a multi-purpose assistant with a wide range of tools. To start a conversation with Alex:

```bash
puti alex-chat
```

**Options:**

- `--stream`: Enable streaming output (shows responses as they're generated)
- `--model MODEL`: Specify a different language model to use (default: as configured in settings)

**Example:**

```bash
puti alex-chat --stream --model gpt-4
```

### Ethan Chat

Ethan is specialized for Twitter interactions. To chat with Ethan:

```bash
puti ethan-chat
```

**Options:**

- `--stream`: Enable streaming output
- `--model MODEL`: Specify a different language model
- `--cookie PATH`: Specify the path to Twitter cookies (overrides env var)

**Example:**

```bash
puti ethan-chat --cookie /path/to/cookies.json
```

## Task Scheduler

The scheduler manages recurring tasks, particularly for Twitter interactions.

### Process Management

Control the scheduler daemon process:

```bash
# Start the scheduler in the background
puti scheduler start

# Stop the scheduler
puti scheduler stop

# Check the status
puti scheduler status
```

### Task Management

Manage individual scheduled tasks:

```bash
# List all tasks
puti scheduler list

# Create a new task
puti scheduler create [NAME] [CRON_SCHEDULE] --type TYPE --params JSON_PARAMS
```

> **Note:** For detailed information about the `create` command parameters and task types, see the [Scheduler Create Command Documentation](scheduler_create_command.md).

**Examples:**

```bash
# Post a daily tweet about AI at noon
puti scheduler create daily_ai_post "0 12 * * *" --type "post" --params '{"topic": "AI"}'

# Reply to mentions from the last 24 hours, every hour
puti scheduler create hourly_replies "0 * * * *" --type "reply" --params '{"time_value": 24, "time_unit": "hours"}'

# Enable a task
puti scheduler enable TASK_ID

# Disable a task
puti scheduler disable TASK_ID

# Delete a task
puti scheduler delete TASK_ID
```

### Logging

View and filter scheduler logs:

```bash
# Basic log viewing
puti scheduler logs

# Stream logs in real-time
puti scheduler logs --follow

# Filter logs containing specific text
puti scheduler logs --filter "error"

# Show only logs of a specific level
puti scheduler logs --level WARNING

# Show simplified output
puti scheduler logs --simple

# Show raw log lines
puti scheduler logs --raw
```

## Configuration

On first run, Puti will guide you through configuration. You can also manually configure the application by creating or editing the `.env` file:

```bash
# Edit the configuration file
nano .env

# Example configuration:
# OPENAI_API_KEY="sk-..."
# OPENAI_BASE_URL="https://api.openai.com/v1"
# OPENAI_MODEL="gpt-4o"
# TWIKIT_COOKIE_PATH="/path/to/cookies.json"
```

The configuration values can also be set as environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o"
puti alex-chat
```

## Advanced Usage

### Debug Mode

For debugging and development:

```bash
# Run with debug output
puti alex-chat --debug

# Show version information
puti --version
```

### Help

Get help with any command:

```bash
puti --help
puti alex-chat --help
puti scheduler --help
``` 