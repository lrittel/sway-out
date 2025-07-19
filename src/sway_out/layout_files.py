"""Data structures and utilities for layout descriptions."""

from typing import Annotated, Literal, Self, TextIO

import yaml
from pydantic import BaseModel, Field, model_validator


class WaylandWindowMatchExpression(BaseModel):
    app_id: str | None = None
    title: str | None = None

    @model_validator(mode="after")
    def validate_match(self) -> Self:
        if self.app_id is None and self.title is None:
            raise ValueError("At least one match expression must be provided.")
        return self


class X11WindowMatchExpression(BaseModel):
    class_: Annotated[str | None, Field(alias="class", title="Window class")] = None
    instance: Annotated[str | None, Field(title="Window instance")] = None
    title: str | None = None

    @model_validator(mode="after")
    def validate_match(self) -> Self:
        if self.class_ is None and self.instance is None and self.title is None:
            raise ValueError("At least one match expression must be provided.")
        return self


class WindowMatchExpression(BaseModel):
    wayland: WaylandWindowMatchExpression | None = None
    x11: X11WindowMatchExpression | None = None

    @model_validator(mode="after")
    def validate_match(self) -> Self:
        if self.wayland is None and self.x11 is None:
            raise ValueError("At least one match expression must be provided.")
        return self


class ApplicationLaunchConfig(BaseModel):
    cmd: Annotated[
        list[str] | str,
        Field(title="Launch command", description="Command to launch the application."),
    ]
    match: Annotated[
        WindowMatchExpression,
        Field(
            title="Window match expression",
            description="A filter to determine if the application is running.",
        ),
    ]


class ContainerConfig(BaseModel):
    type_: Literal["splith", "splitv", "stacking", "tabbed"]
    children: "list[ApplicationLaunchConfig | ContainerConfig]"


class WorkspaceLayout(BaseModel):
    layout: list[ApplicationLaunchConfig | ContainerConfig]


class Layout(BaseModel):
    workspaces: dict[str, WorkspaceLayout]


def load_layout_configuration(file: TextIO) -> Layout:
    """Load a layout configuration from a file-like object.

    Arguments:
        file: The source file.
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
