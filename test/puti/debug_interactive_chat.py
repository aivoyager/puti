"""
This script allows you to easily debug the 'puti alex-chat' interactive command
within the PyCharm IDE or any other Python debugger.

By running this script in Debug mode, you can set breakpoints anywhere in your
application's codebase (e.g., in `puti/cli.py`, `puti/core/config_setup.py`,
or inside the `Alex` agent's logic) and step through the code execution.

How to use this for debugging in PyCharm:
-----------------------------------------
1.  **Set a breakpoint**: Click in the gutter to the left of a line number
    in any file you want to investigate. A red dot will appear.
    (e.g., try setting one on the `ensure_config_is_present()` line in `puti/cli.py`).

2.  **Right-click this file** (`debug_interactive_chat.py`) in the Project view.

3.  **Select "Debug 'debug_interactive_chat'"** from the context menu.

4.  **The script will run**, and the PyCharm debugger will pause at your breakpoint.
    You can then inspect variables, step over lines, or step into functions.

5.  **Interact with the application**: When the code runs the interactive parts
    (like `questionary` prompts), the prompts will appear in the **"Console" tab**
    of the PyCharm "Debug" window. You can type your responses there directly.
"""
from puti.cli import main

if __name__ == '__main__':
    # This is the programmatic equivalent of running "puti alex-chat" from your terminal.
    # We get the main entry point (`main` function decorated with @click.group)
    # and pass the command we want to execute as a list of strings.
    # Click handles the rest of the dispatching.
    main(['alex-chat'])
