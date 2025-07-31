"""Data structures and utilities for layout descriptions."""

from typing import Annotated, Literal, Self, TextIO

import yaml
from i3ipc import Connection
from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator

from .connection import get_focused_workspace


class MarksMixin:
    """Mixin to add marks to a model.

    The fields related to marks are extracted to avoid duplication between
    [sway_out.layout_files.ApplicationLaunchConfig][] and
    [sway_out.layout_files.ContainerConfig][].
    """

    mark: Annotated[
        str | None,
        Field(
            default=None,
            title="Mark to assign",
            description="A mark to assign to the container. Mutually exclusive with `marks`.",
        ),
    ]
    marks: Annotated[
        list[str] | None,
        Field(
            default=None,
            title="Marks to assign",
            description="A list of marks to assign to the container. Mutually exclusive with `mark`.",
        ),
    ]

    @property
    def assigned_marks(self) -> list[str]:
        """Get the marks assigned to this container.
        Returns:
            A list of marks assigned to this container.
        """
        if self.mark is not None:
            return [self.mark]
        if self.marks is not None:
            return self.marks
        return []

    @field_validator("mark", "marks", mode="after")
    @staticmethod
    def validate_mark_values(v: str | list[str] | None) -> str | list[str] | None:
        marks = v if isinstance(v, list) else [v or ""]
        for mark in marks:
            if len(mark) != 1:
                raise ValueError(f"Mark must be a single character, got: {mark!r}")
        return v

    @model_validator(mode="after")
    def validate_marks(self) -> Self:
        if self.mark is not None and self.marks is not None:
            raise ValueError("Cannot set both `mark` and `marks` at the same time.")
        return self


class ConIdMixin:
    """Mixin to add con_id to a model.

    The con_id is used to identify the container in Sway.
    """

    _con_id: Annotated[int | None, PrivateAttr(default=None)]


class LayoutParentMixin:
    """A mixin to add layout-parent-related fields to a model."""

    children: "list[ApplicationLaunchConfig | ContainerConfig]"
    layout: Literal["splith", "splitv", "stacking", "tabbed"]

    @model_validator(mode="after")
    def validate_percent(self) -> Self:
        if self.layout in ["splith", "splitv"]:
            percent_sum = sum(child.percent or 0 for child in self.children)
            any_none = any(child.percent is None for child in self.children)
            if not any_none and percent_sum != 100:
                raise ValueError(
                    "If a percentage is set on all children of a"
                    + " layout, the percentages have add up to 100"
                )
        elif self.layout in ["stacking", "tabbed"]:
            any_percent = any(child.percent is not None for child in self.children)
            if any_percent:
                raise ValueError(
                    "Percentages are not allowed in stacking or tabbed layouts"
                )
        else:
            assert (
                False
            ), "Unknown layout type, this should have been caught by the validation."
        return self


class LayoutChildMixin:
    """A mixin to add layout-child-related fields to a model."""

    percent: Annotated[int | None, Field(default=None, ge=0, le=100)]


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


class ApplicationLaunchConfig(BaseModel, MarksMixin, ConIdMixin, LayoutChildMixin):
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


class ContainerConfig(
    BaseModel, MarksMixin, ConIdMixin, LayoutParentMixin, LayoutChildMixin
):
    pass


class WorkspaceLayout(BaseModel, ConIdMixin, LayoutParentMixin):
    pass


class Layout(BaseModel):
    focused_workspace: Annotated[
        WorkspaceLayout | None,
        Field(
            default=None,
            title="Layout for the focused workspace",
            description="If present, this layout gets applied to the workspace that is currently focused.",
        ),
    ]
    workspaces: Annotated[
        dict[str, WorkspaceLayout],
        Field(
            default={},
            title="Workspace layouts",
            description="These layouts get applied to the workspaces with the name of the respective key.",
        ),
    ]


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


def map_workspaces(
    connection: Connection, layout: Layout
) -> dict[str, WorkspaceLayout]:
    """Map the workspace names from the layout to the actual workspaces.

    The currently focused workspace is used to resolve
    [sway_out.layout_files.Layout.focused_workspace][].

    con_ids stay unset if the workspace does not exist in Sway.

    Arguments:
        connection: A connection to Sway.
        layout: The layout to map.

    Returns:
        A mapping of workspace layouts with the con_id set to the id of the
        corresponding workspace to the name of the respective workspace.

    Note:
        The layout objects do not get copied, so `layout` is modified.
    """

    def go():
        for workspace_name, workspace_layout in layout.workspaces.items():
            for workspace in tree.workspaces():
                if workspace.name == workspace_name:
                    workspace_layout._con_id = workspace.id
                    break
            yield workspace_name, workspace_layout
        if layout.focused_workspace is not None:
            focused_workspace_layout = layout.focused_workspace
            focused_worksapce_con = get_focused_workspace(connection)
            assert focused_worksapce_con is not None, "No focused workspace found?"
            focused_workspace_name = focused_worksapce_con.name
            yield focused_workspace_name, focused_workspace_layout

    tree = connection.get_tree()
    return dict(go())
