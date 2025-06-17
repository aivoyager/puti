"""
@Author: obstacles
@Time:  2025-06-18 14:22
@Description:  
"""
from pydantic import BaseModel, Field, ConfigDict
from puti.llm.roles import Role
from typing import Union, Callable, Any, Dict, Optional
import re
import jinja2
from jinja2 import Template


# Define a type hint for the callable placeholder
# It takes one argument (the previous result) and returns a string
MsgPlaceholder = Callable[[Any], str]


class Action(BaseModel):
    # Allow Pydantic to handle complex types like jinja2.Template
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="The name of the action")
    description: str = Field('', description="A brief description of the action")
    role: Role = Field(..., description="The role that executes the action")
    msg: Union['Action', str, Template, MsgPlaceholder] = Field(..., description="The message to be sent to the role. Can be a plain string, a Jinja2 Template, or a callable.")

    async def run(self, *args, **kwargs):
        # Determine the effective message to pass to the role
        resolved_msg = self.msg

        # If a 'msg' is explicitly provided in runtime kwargs, it overrides self.msg
        if 'msg' in kwargs:
            resolved_msg = kwargs.pop('msg')

        # If the determined message is a callable (placeholder function)
        if callable(resolved_msg):
            # Assume the callable takes 'previous_result' from kwargs
            # The 'previous_result' would be the output of the preceding action/node.
            previous_result = kwargs.get('previous_result')
            # Execute the callable to get the actual message string
            resolved_msg = resolved_msg(previous_result)
        # If it's a Jinja2 Template, render it
        elif isinstance(resolved_msg, Template):
            try:
                resolved_msg = resolved_msg.render(**kwargs)
                print(f"[DEBUG] Action {self.name}: Rendered msg: {resolved_msg}")
            except jinja2.exceptions.TemplateError as e:
                print(f"[ERROR] Action {self.name}: Jinja2 templating error: {e}")
                raise
        # If it's a plain string, it's used as-is
        elif isinstance(resolved_msg, str):
            print(f"[DEBUG] Action {self.name}: Using msg as-is: {resolved_msg}")

        resp = await self.role.run(
            msg=resolved_msg,  # Pass the resolved message
            action_name=self.name,
            action_description=self.description,
            *args,
            **kwargs
        )
        # postprocessing action here ...
        return resp

    def __call__(self, msg, *args, **kwargs):
        return self.run(msg=msg, *args, **kwargs)

    @classmethod
    def with_placeholder(cls, name: str, description: str, role: Role, template: str) -> 'Action':
        """
        Factory method to create an Action with a template string containing placeholders.
        
        Args:
            name: The name of the action
            description: A brief description of the action
            role: The role that executes the action
            template: A string template with placeholders (e.g., "Result: {previous_result}")
            
        Returns:
            An Action instance with the template as its msg
        """
        return cls(name=name, description=description, role=role, msg=template)
