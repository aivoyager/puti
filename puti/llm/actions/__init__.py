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
from puti.logs import logger_factory
from puti.llm.messages import Message

lgr = logger_factory.llm


# Define a type hint for the callable placeholder
# It takes one argument (the previous result) and returns a string
MsgPlaceholder = Callable[[Any], str]


class Action(BaseModel):
    # Allow Pydantic to handle complex types like jinja2.Template
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="The name of the action")
    description: str = Field('', description="A brief description of the action")
    prompt: Optional[Union['Action', str, Template, MsgPlaceholder]] = Field(
        default=None,
        description="The prompt to be sent to the role. Can be a plain string, a Jinja2 Template, or a callable."
    )

    async def run(self, role: Role, *args, **kwargs) -> Union[str, Message]:
        """
        Execute the action using the provided role.
        
        Args:
            role: The role to execute the action with.
            args: Additional positional arguments to pass to the role.
            kwargs: Additional keyword arguments to pass to the role.
        
        Returns:
            The response from the role.
        """
        lgr.debug(f'`{self.name}` Action is running...')

        if role is None:
            raise ValueError("Role must be provided to run an action.")
        
        # Determine the effective prompt to pass to the role
        resolved_prompt = self.prompt

        # If a 'prompt' is explicitly provided in runtime kwargs, it overrides self.prompt
        if 'prompt' in kwargs:
            resolved_prompt = kwargs.pop('prompt')

        # If the determined prompt is a callable (placeholder function)
        if callable(resolved_prompt):
            # Assume the callable takes 'previous_result' from kwargs
            # The 'previous_result' would be the output of the preceding action/node.
            previous_result = kwargs.get('previous_result')
            # Execute the callable to get the actual prompt string
            resolved_prompt = resolved_prompt(previous_result)
        # If it's a Jinja2 Template, render it
        elif isinstance(resolved_prompt, Template):
            try:
                resolved_prompt = resolved_prompt.render(**kwargs)
                # lgr.debug(f"Action {self.name}: Rendered prompt: {resolved_prompt}")
            except jinja2.exceptions.TemplateError as e:
                lgr.error(f"Action {self.name}: Jinja2 templating error: {e}")
                raise
        # If it's a plain string, it's used as-is
        elif isinstance(resolved_prompt, str):
            pass
            # lgr.debug(f"Action {self.name}: Using prompt as-is: {resolved_prompt}")

        resp = await role.run(
            msg=resolved_prompt,  # Pass the resolved prompt
            action_name=self.name,
            action_description=self.description,
            *args,
            **kwargs
        )
        # postprocessing action here ...
        return resp

    def __call__(self, prompt, role: Role, *args, **kwargs):
        """
        Allow the action to be called as a function.
        
        Args:
            prompt: The prompt to pass to the role.
            role: The role to execute the action with.
            args: Additional positional arguments to pass to run().
            kwargs: Additional keyword arguments to pass to run().
            
        Returns:
            The coroutine from run().
        """
        return self.run(role=role, prompt=prompt, *args, **kwargs)

    @classmethod
    def with_placeholder(cls, name: str, description: str, template: str) -> 'Action':
        """
        Factory method to create an Action with a template string containing placeholders.
        
        Args:
            name: The name of the action
            description: A brief description of the action
            template: A string template with placeholders (e.g., "Result: {previous_result}")
            
        Returns:
            An Action instance with the template as its prompt
        """
        return cls(name=name, description=description, prompt=template)
