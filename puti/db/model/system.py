"""
@Author: obstacle
@Time: 27/06/20 11:30
@Description: System models for storing system-wide settings and configuration.
"""
from typing import Optional
from pydantic import Field
from puti.db.model import Model


class SystemSetting(Model):
    """Model for storing system-wide settings."""
    __table_name__ = 'system_settings'
    
    name: str = Field(..., max_length=255, description="The name/key of the setting")
    value: str = Field(..., description="The value of the setting")
    description: Optional[str] = Field(None, description="Optional description of what this setting is for")
    created_at: Optional[str] = Field(None, description="When this setting was created")
    updated_at: Optional[str] = Field(None, description="When this setting was last updated")
    is_del: bool = False 