"""
@Author: obstacles
@Time:  2025-07-29 17:00
@Description: A tool to analyze and report the project's directory structure.
"""
import os
from abc import ABC
from pathlib import Path

from pydantic import Field

from puti.core.resp import ToolResponse
from puti.llm.tools import BaseTool, ToolArgs
from puti.utils.path import root_dir


class ProjectAnalyzerArgs(ToolArgs, ABC):
    path: str = Field(default=None, description="The relative path from the project root to start analyzing. Defaults to the project root.")
    max_depth: int = Field(default=3, description="The maximum depth of directories to traverse. Default is 3.")


class ProjectAnalyzer(BaseTool, ABC):
    name: str = "project_structure_analyzer"
    desc: str = (
        "Analyzes and provides a summary of the project's directory and file structure. "
        "Use this tool to understand the codebase layout, find files, or explore the project's architecture. "
        "You can specify a starting path and a maximum depth for the analysis."
    )
    args: ProjectAnalyzerArgs = None

    ignored_dirs: set = {'.git', '.idea', '__pycache__', '.pytest_cache', 'dist', 'build', 'ai_puti.egg-info', 'node_modules'}
    ignored_files: set = {'.DS_Store'}

    def _generate_tree(self, start_path: Path, max_depth: int) -> str:
        tree_str = ""
        for root, dirs, files in os.walk(start_path, topdown=True):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            
            current_path = Path(root)
            depth = len(current_path.relative_to(start_path).parts)

            if depth > max_depth:
                dirs[:] = []  # Don't go deeper
                continue

            if current_path != start_path:
                indent = "    " * (depth - 1) + "└── "
                tree_str += f"{indent}{current_path.name}/\n"
            
            file_indent = "    " * depth + "├── "
            for f in sorted(files):
                if f not in self.ignored_files:
                    tree_str += f"{file_indent}{f}\n"

        return tree_str

    async def run(self, path: str = None, max_depth: int = 3, *args, **kwargs) -> ToolResponse:
        try:
            start_path = root_dir()
            if path:
                requested_path = (start_path / path).resolve()
                # Security check: ensure the path is within the project directory
                if root_dir() not in requested_path.parents and requested_path != root_dir():
                    return ToolResponse.fail(msg="Error: Path is outside the project directory.")
                start_path = requested_path

            if not start_path.is_dir():
                return ToolResponse.fail(msg=f"Error: Path '{start_path}' is not a valid directory.")

            tree_output = self._generate_tree(start_path, max_depth)
            
            final_report = (
                f"Project structure analysis from '{start_path.relative_to(root_dir())}':\n"
                f"```\n{tree_output}\n```"
            )
            return ToolResponse.success(data=final_report)
        except Exception as e:
            return ToolResponse.fail(msg=f"An error occurred while analyzing the project structure: {str(e)}") 