from typing import Annotated

import yaml
from pydantic import BaseModel, Field


class ApplicationLaunchConfig(BaseModel):
    cmd: Annotated[
        list[str] | str,
        Field(title="Launch command", description="Command to launch the application."),
    ]


class Layout(BaseModel):
    applications: list[ApplicationLaunchConfig]


def load_layout_configuration(file) -> Layout:
    """Load a layout configuration from a file-like object.

    Arguments:
        file:
            The source file.
    Raises:
        yaml.YAMLError:
            When the file does not contain valid YAML.
        pydantic.ValidationError:
            When the YAML is ill-formed.
    Returns:
        The configuration object.
    """

    obj = yaml.load(file, yaml.SafeLoader)
    return Layout.model_validate(obj)
