#!/usr/bin/env python3
"""
Migration notice for puti command line tools
"""
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

migration_message = """
# Puti Command Line Migration Notice

The scheduler functionality has been fully integrated into the main `puti` command.
This means you can now use the scheduler commands directly through the main command.

## Migration Guide

### Old Commands vs New Commands

| Old Command                    | New Command                  |
|-------------------------------|------------------------------|
| `puti-scheduler start`         | `puti scheduler start`       |
| `puti-scheduler stop`          | `puti scheduler stop`        |
| `puti-scheduler status`        | `puti scheduler status`      |
| `puti-scheduler list`          | `puti scheduler list`        |
| `puti-scheduler create ...`    | `puti scheduler create ...`  |
| `puti-scheduler enable <id>`   | `puti scheduler enable <id>` |
| `puti-scheduler disable <id>`  | `puti scheduler disable <id>`|
| `puti-scheduler delete <id>`   | `puti scheduler delete <id>` |
| `puti-scheduler run <id>`      | `puti scheduler run <id>`    |

### Setting up the environment

Make sure to use the puti virtual environment:

```bash
# Activate the puti virtual environment
source /path/to/puti/venv/bin/activate

# Then you can use the puti command
puti scheduler list
```

The old standalone scripts (`puti-scheduler`, `puti-cmd`, etc.) have been deprecated and will be removed in a future version.
"""

console.print(Panel(
    Markdown(migration_message),
    title="Puti Command Line Migration Notice",
    border_style="yellow"
))

console.print("\n[green]For any issues or questions, please refer to the project documentation.[/green]") 