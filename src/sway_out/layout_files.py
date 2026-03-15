"""Data structures and utilities for layout descriptions."""

import re
from collections import defaultdict
from collections.abc import Generator
from typing import Annotated, Literal, Self, TextIO

import yaml
from i3ipc import Connection
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from .connection import get_focused_workspace

type FocusType = Literal["parent", "workspace", "output", "global"]


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
        if v is None:
            return v
        marks = v if isinstance(v, list) else [v]
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
            child_percentages = [
                child.percent or 0
                for child in self.children
                if child.percent is not None
            ]
            percent_sum = sum(child_percentages)
            any_none = (
                any(child.percent is None for child in self.children)
                or not self.children
            )
            if not any_none and percent_sum != 100:
                raise ValueError(
                    "If a percentage is set on all children of a"
                    + " layout, the percentages have add up to 100: "
                    + f"{' + '.join(str(p) for p in child_percentages)} = {percent_sum} != 100"
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


class ContainerFocusMixin:
    """A mixin to add focus-related fields to a model."""

    focus: Annotated[
        FocusType | None,
        Field(
            default=None,
            title="Focus after launch",
            description="If set, the container will be focused after it is launched on the specified scope.",
        ),
    ]


class WaylandWindowMatchExpression(BaseModel):
    app_id: str | None = None
    title: str | None = None

    @field_validator("app_id", "title", mode="after")
    @staticmethod
    def validate_regex(value: str | None) -> str | None:
        if value is None:
            return value
        try:
            _ = re.compile(value)
        except re.error as e:
            raise ValueError(f"The regex '{value}' is invalid: {e}")
        else:
            return value

    @model_validator(mode="after")
    def validate_match(self) -> Self:
        if self.app_id is None and self.title is None:
            raise ValueError("At least one match expression must be provided.")
        return self


class X11WindowMatchExpression(BaseModel):
    class_: Annotated[str | None, Field(alias="class", title="Window class")] = None
    instance: Annotated[str | None, Field(title="Window instance")] = None
    title: str | None = None

    @field_validator("class_", "instance", "title", mode="after")
    @staticmethod
    def validate_regex(value: str | None) -> str | None:
        if value is None:
            return value
        try:
            _ = re.compile(value)
        except re.error as e:
            raise ValueError(f"The regex '{value}' is invalid: {e}")
        else:
            return value

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


class ApplicationLaunchConfig(  # type: ignore[reportUnsafeMultipleInheritance]
    BaseModel, MarksMixin, ConIdMixin, LayoutChildMixin, ContainerFocusMixin
):
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


class ContainerConfig(  # type: ignore[reportUnsafeMultipleInheritance]
    BaseModel,
    MarksMixin,
    ConIdMixin,
    LayoutParentMixin,
    LayoutChildMixin,
    ContainerFocusMixin,
):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class WorkspaceLayout(BaseModel, ConIdMixin, LayoutParentMixin):
    output: Annotated[
        str | list[str] | None,
        Field(
            title="Output to place the workspace on",
            description="The workspace will be put on this workspace "
            + "if it exists. If multiple outputs are specified, they "
            + "are tried in order.",
        ),
    ] = None


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
        dict[str, WorkspaceLayout] | None,
        Field(
            default=None,
            title="Workspace layouts",
            description="These layouts get applied to the workspaces with the name of the respective key.",
        ),
    ]

    @model_validator(mode="after")
    def validate_workspaces(self) -> Self:
        if self.focused_workspace is not None and self.workspaces is not None:
            raise ValueError(
                "Cannot set both `focused_workspace` and `workspaces` at the same time."
            )
        if self.focused_workspace is None and self.workspaces is None:
            raise ValueError(
                "Either `focused_workspace` or `workspaces` has to be present."
            )
        return self

    @model_validator(mode="after")
    def validate_focus_containers(self) -> Self:
        def validate(config: ApplicationLaunchConfig | ContainerConfig):
            if isinstance(config, ApplicationLaunchConfig):
                return

            count = 0

            for child in config.children:
                if child.focus == "parent":
                    count += 1

                count += self._count_focused_elements(
                    child, ["global", "output", "workspace"]
                )

            if count > 1:
                raise ValueError(
                    "Only one container of the direct children of a container can have `focus` set to "
                    + "`parent` or `workspace`, `output` or `global` for one (possibly indirect) child."
                )

        if self.focused_workspace is not None:
            for child in self.focused_workspace.children:
                validate(child)

        if self.workspaces is not None:
            for workspace_layout in self.workspaces.values():
                for child in workspace_layout.children:
                    validate(child)

        return self

    @model_validator(mode="after")
    def validate_focus_workspace(self) -> Self:
        if self.focused_workspace is not None:
            workspace_count = self._count_focused_elements(
                self.focused_workspace, ["global", "output", "workspace"]
            )

            if workspace_count > 1:
                raise ValueError(
                    "Only one container can have `focus` set to `workspace`, `output` or `global` in a workspace."
                )

        if self.workspaces is not None:
            for workspace_layout in self.workspaces.values():
                workspace_count = self._count_focused_elements(
                    workspace_layout, ["global", "output", "workspace"]
                )

                if workspace_count > 1:
                    raise ValueError(
                        "Only one container can have `focus` set to `workspace`, `output` or `global` in a workspace."
                    )

        return self

    @model_validator(mode="after")
    def validate_focus_output(self) -> Self:
        focus_counts: defaultdict[str, int] = defaultdict(lambda: 0)

        if self.workspaces is None:
            return self

        for workspace_layout in self.workspaces.values():
            count = self._count_focused_elements(workspace_layout, ["global", "output"])
            if isinstance(output := workspace_layout.output, str):
                focus_counts[output] += count
            elif isinstance(workspace_layout.output, list):
                for output in workspace_layout.output:
                    focus_counts[output] += count

        for output, count in focus_counts.items():
            if count > 1:
                raise ValueError(
                    f"Only one container can have `focus` set to `output` or `global` for output {output}, got {count}."
                )

        return self

    @model_validator(mode="after")
    def validate_focus_global(self) -> Self:
        total_count = 0

        if self.focused_workspace is not None:
            total_count += self._count_focused_elements(
                self.focused_workspace, ["global"]
            )

        if self.workspaces is not None:
            for workspace_layout in self.workspaces.values():
                total_count += self._count_focused_elements(
                    workspace_layout, ["global"]
                )

        if total_count > 1:
            raise ValueError(
                "Only one container can have `focus` set to `global` in the entire layout."
            )

        return self

    @staticmethod
    def _count_focused_elements(
        layout: WorkspaceLayout | ContainerConfig | ApplicationLaunchConfig,
        focus_types: list[FocusType],
    ) -> int:
        count = 0

        if isinstance(layout, (WorkspaceLayout, ContainerConfig)):
            count += sum(
                Layout._count_focused_elements(child, focus_types)
                for child in layout.children
            )

        if (
            isinstance(layout, (ContainerConfig, ApplicationLaunchConfig))
            and layout.focus in focus_types
        ):
            count += 1

        return count


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


def save_layout_configuration(layout: Layout, file: TextIO):
    """Save a layout configuration to a file-like object.

    Arguments:
        layout: The layout to save.
        file: The destination file.
    """

    obj = layout.model_dump(exclude_none=True, exclude_unset=True)
    yaml.dump(obj, file, yaml.SafeDumper, encoding="utf-8", allow_unicode=True)


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
        if layout.workspaces is not None:
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
            assert focused_workspace_name is not None, "Focused workspace has no name"
            yield focused_workspace_name, focused_workspace_layout

    tree = connection.get_tree()
    return dict(go())


def iter_container_configs(
    layout: Layout | WorkspaceLayout | ContainerConfig | ApplicationLaunchConfig,
) -> Generator[ContainerConfig | ApplicationLaunchConfig]:
    if isinstance(layout, Layout):
        if (child := layout.focused_workspace) is not None:
            yield from iter_container_configs(child)

        if layout.workspaces is not None:
            for child in layout.workspaces.values():
                yield from iter_container_configs(child)
    elif isinstance(layout, WorkspaceLayout):
        for child in layout.children:
            yield from iter_container_configs(child)
    elif isinstance(layout, ContainerConfig):
        for child in layout.children:
            yield from iter_container_configs(child)
    else:
        assert isinstance(layout, ApplicationLaunchConfig)
        yield layout
