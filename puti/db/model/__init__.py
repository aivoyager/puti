"""
@Author: obstacle
@Time: 16/01/25 17:39
@Description:  
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class Model(BaseModel):
    """Base model for all database models."""
    __table_name__ = ''
    
    # Allow arbitrary types and extra fields
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    
    # Common fields for all models
    id: Optional[int] = Field(None, description="Primary key ID")
