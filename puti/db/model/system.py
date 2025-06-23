"""
@Author: obstacle
@Time: 29/06/20 12:00
@Description: Model for system-wide settings and configuration.
"""
from typing import Optional
from pydantic import Field
from puti.db.model import Model


class SystemSetting(Model):
    """Model for storing system-wide settings in the database."""
    __table_name__ = 'system_settings'

    name: str = Field(..., max_length=255, json_schema_extra={'unique': True}, 
                      description="The name/key of the setting")
    value: str = Field(..., max_length=1024, description="The value of the setting")
    description: Optional[str] = Field(None, max_length=1024, 
                                      description="Optional description of what this setting controls") 