# Twitter Integration

This document explains how to use the Twitter integration in Puti, which allows agents to interact with Twitter (X) through the Twikitt library.

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
  - [Installation](#installation)
  - [Twitter Authentication](#twitter-authentication)
- [Using the Ethan Agent](#using-the-ethan-agent)
  - [Interactive Mode](#interactive-mode)
  - [Programmatic Usage](#programmatic-usage)
- [Twikitt Tool](#twikitt-tool)
  - [Available Operations](#available-operations)
  - [Usage Examples](#usage-examples)
- [Automated Twitter Tasks](#automated-twitter-tasks)
  - [Task Types](#task-types)
  - [Setting Up Scheduled Tasks](#setting-up-scheduled-tasks)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Puti's Twitter integration provides a powerful way to interact with Twitter (X) through AI agents. The integration enables:

- Sending tweets
- Replying to mentions
- Searching tweets
- Viewing notifications
- Getting user information

These capabilities are delivered through the Twikitt tool, which is pre-integrated with the Ethan agent.

## Setup

### Installation

To use the Twitter integration, install Puti with the Twitter dependencies:

```bash
pip install ai-puti[twitter]
```

### Twitter Authentication

The Twitter integration uses browser cookies for authentication via the Twikitt library:

1. **Export Twitter Cookies**: Use a browser extension like "Cookie-Editor" to export your Twitter cookies to a JSON file.

2. **Configure Environment**: Set the path to your cookies file:

   ```bash
   # In your .env file
   TWIKIT_COOKIE_PATH="/path/to/your/cookies.json"
   ```

   Alternatively, set it via command line:

   ```bash
   puti ethan-chat --cookie /path/to/your/cookies.json
   ```

3. **Guided Setup**: When running `puti ethan-chat` for the first time, Puti will guide you through setting up your Twitter credentials.

## Using the Ethan Agent

### Interactive Mode

Ethan is a specialized Twitter agent designed to help with Twitter interactions:

```bash
# Start the interactive Ethan chat
puti ethan-chat
```

You can ask Ethan to perform Twitter tasks like:
- "Post a tweet about AI advancements"
- "Check my recent mentions"
- "Reply to my latest notifications"
- "Show me trending topics in technology"

### Programmatic Usage

You can also use Ethan programmatically in your Python code:

```python
from puti.llm.roles.agents import Ethan

async def twitter_interaction():
    # Create an instance of Ethan
    ethan = Ethan()
    
    # Post a tweet
    result = await ethan.run("Post a tweet about the latest developments in AI")
    print(result)
    
    # Check mentions
    result = await ethan.run("Show me my recent mentions")
    print(result)
    
    # Reply to a tweet
    tweet_id = "12345678901234567890"  # Replace with actual tweet ID
    result = await ethan.run(f"Reply to tweet {tweet_id} with a thoughtful response")
    print(result)

# Run the async function
import asyncio
asyncio.run(twitter_interaction())
```

## Twikitt Tool

The Twikitt tool powers Ethan's Twitter capabilities and can also be integrated with custom agents.

### Available Operations

The Twikitt tool supports these primary operations:

1. **send_tweet**: Post a new tweet
2. **reply_to_tweet**: Reply to an existing tweet
3. **get_mentions**: Retrieve recent mentions
4. **browse_tweets**: Search for tweets with a query
5. **get_my_info**: Get the authenticated user's profile information
6. **get_my_tweets**: Get the authenticated user's recent tweets
7. **like_tweet**: Like a specific tweet
8. **retweet**: Retweet a specific tweet

### Usage Examples

Here's how to use the Twikitt tool with a custom agent:

```python
from puti.llm.roles import Role
from puti.llm.tools.twikitt import Twikitt

class TwitterAssistant(Role):
    name: str = "TwitterAssistant"
    identity: str = "Twitter Management Assistant"
    goal: str = "Help manage Twitter interactions"
    
    def model_post_init(self, __context):
        self.set_tools([Twikitt])

# Usage
assistant = TwitterAssistant()

# Post a tweet
response = await assistant.run("Post a tweet saying 'Just exploring the Puti framework's Twitter integration. Exciting capabilities!'")

# Check mentions
response = await assistant.run("Check if anyone has mentioned me recently")

# Advanced: Use the tool directly
from puti.llm.tools.twikitt import Twikitt

async def direct_tool_usage():
    tool = Twikitt()
    response = await tool.run('send_tweet', text='Hello from Puti!')
    print(response.data)  # Will contain the tweet ID if successful
```

## Automated Twitter Tasks

Puti's scheduler integration allows you to automate Twitter tasks.

### Task Types

Two primary task types are available:

1. **Post Task**: Automatically generates and posts tweets on specific topics
2. **Reply Task**: Automatically responds to mentions within a specified time window

### Setting Up Scheduled Tasks

Use the CLI to set up scheduled Twitter tasks:

```bash
# Post a daily tweet about AI news at 9:00 AM
puti scheduler create daily_ai_news "0 9 * * *" --type post --params '{"topic": "AI news"}'

# Reply to mentions from the last 24 hours every hour
puti scheduler create hourly_replies "0 * * * *" --type reply --params '{"time_value": 24, "time_unit": "hours"}'
```

See the [Celery Integration](celery.md) documentation for more details on task scheduling.

## Best Practices

1. **Rate Limiting**: Be mindful of Twitter's rate limits. Space out operations and avoid excessive requests.

2. **Content Guidelines**: Ensure your automated content adheres to Twitter's terms of service and community guidelines.

3. **Error Handling**: Implement proper error handling when using the Twikitt tool, as network issues or authentication problems can occur.

4. **Cookie Refresh**: Periodically update your Twitter cookies to prevent authentication issues.

5. **Backup Strategy**: Keep a backup of your cookies file in a secure location.

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Ensure your cookies file is valid and up-to-date
   - Check that the path to your cookies file is correct
   - Try logging out and back into Twitter before exporting cookies

2. **Operation Failures**:
   - Check for rate limiting (Twitter limits API calls)
   - Verify network connectivity
   - Look for any error messages in the response

3. **Tweet Content Issues**:
   - Ensure content doesn't violate Twitter's policies
   - Check that tweets aren't duplicates (Twitter blocks identical tweets)

4. **Tool Not Found**:
   - Verify that the Twikitt tool is properly added to your agent
   - Check that the Twitter dependencies are installed

### Debugging

For better insight into Twitter operations, enable debug logging:

```python
import logging
from puti.logs import logger_factory

logger_factory.llm.setLevel(logging.DEBUG)
```

If problems persist, check the Twikitt tool's response object for error messages and details. 