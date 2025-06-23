"""
@Author: obstacle
@Time: 13/01/25 15:05
@Description: File model for reading configuration files
"""
import json
import yaml
import logging
from pathlib import Path
from typing import List, Union, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

from puti.logs import logger_factory

lgr = logger_factory.default

__all__ = ["FileModel"]


class FileModel(BaseModel):
    """File model for reading configuration files in various formats"""

    file_types: List[Literal['json', 'yaml']] = Field(
        default_factory=lambda: ['json', 'yaml'],
        description="List of supported file types."
    )

    def read_file(self, file_path: Union[Path, str]) -> Dict[str, Any]:
        """
        Read and parse file based on its extension.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Parsed content of the file
            
        Raises:
            ValueError: If file type is not supported
            FileNotFoundError: If file does not exist
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        file_type = file_path.suffix.lstrip('.')
        
        if file_type not in self.file_types:
            err = f"File type '{file_path.suffix}' not supported. Supported types: {', '.join(self.file_types)}"
            lgr.error(err)
            raise ValueError(err)
            
        if not file_path.exists():
            err = f"File '{file_path}' does not exist."
            lgr.error(err)
            raise FileNotFoundError(err)
        
        try:
            if file_type == 'json':
                return self._read_json(file_path)
            elif file_type == 'yaml':
                return self._read_yaml(file_path)
            else:
                # This should never happen due to the check above
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            lgr.error(f"Error reading file '{file_path}': {str(e)}")
            raise
    
    def _read_json(self, file_path: Path) -> Dict[str, Any]:
        """Read and parse JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _read_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Read and parse YAML file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
