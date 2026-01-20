"""Creation of new layout from existing workspace states."""

import logging
from typing import cast

from i3ipc import Con, Connection

from sway_out.layout import get_container_size_excluding_gaps
from sway_out.layout_files import (
    ApplicationLaunchConfig,
    ContainerConfig,
    Layout,
    WaylandWindowMatchExpression,
    WindowMatchExpression,
    WorkspaceLayout,
    X11WindowMatchExpression,
)
from sway_out.utils import get_con_description, is_window

logger = logging.getLogger(__name__)


def create_layout_from_workspace(
    connection: Connection, workspace_names: list[str] | None = None
) -> Layout:
    """Create a layout from the current workspace states.

    Arguments:
        connection: A connection to Sway.
        workspace_names: The names of workspaces to include, iff omitted, all
            workspaces are included.

    Raises:
        RuntimeError: If an unexpected con type is encountered.

    Returns:
        A layout object.
    """

    def create_layout_for_container(con: Con, parent: Con):
        logger.debug("Creating layout for container %s", get_con_description(con))
        match con.type:
            case "con":
                if is_window(con):
                    if con.app_id is not None:
                        wayland = WaylandWindowMatchExpression(
                            app_id=con.app_id,
                            title=con.name,
                        )
                        x11 = None
                    else:
                        wayland = None
                        x11 = X11WindowMatchExpression(
                            class_=con.window_class,
                            instance=con.window_instance,
                            title=con.name,
                        )

                    result = ApplicationLaunchConfig(
                        cmd=_guess_command_for_application(con),
                        match=WindowMatchExpression(wayland=wayland, x11=x11),
                    )
                else:
                    children = [
                        create_layout_for_container(child, con) for child in con.nodes
                    ]
                    _fix_up_percentages(children)
                    result = ContainerConfig(children, con.layout)

                if len(con.marks) == 1:
                    result.mark = con.marks[0]
                elif len(con.marks) > 1:
                    result.marks = con.marks

                if con.focused:
                    result.focus = True

                result.percent = _calculate_percent(con, parent)

                return result
            case "floating_con":
                logger.warning(
                    "Support for floating containers is not implemented, yet; skipping container %s",
                    get_con_description(con),
                )
            case _:
                raise RuntimeError(
                    f"Unexpected con type encountered for con_id {con.id}: {con.type}"
                )

    tree = connection.get_tree()
    workspaces: dict[str, WorkspaceLayout] = {}
    for workspace in tree.workspaces():
        if workspace.name is None:
            continue
        if workspace_names is not None and workspace.name not in workspace_names:
            continue

        children = [
            create_layout_for_container(con, workspace) for con in workspace.nodes
        ]
        _fix_up_percentages(children)
        workspaces[workspace.name] = WorkspaceLayout(
            children=children, layout=workspace.layout
        )

    return Layout(focused_workspace=None, workspaces=workspaces)


def _guess_command_for_application(con: Con) -> list[str]:
    """Guess the command line for a container based on its PID.

    Parameters:
        con: The container to guess the command for.

    Returns:
        A list of command line arguments, or an empty list if the command cannot be guessed.
    """

    if con.pid is None:
        logger.error(
            "Cannot guess command for container %s without a PID",
            get_con_description(con),
        )
        return []

    # Retrieve the command line from /proc
    path = f"/proc/{con.pid}/cmdline"
    try:
        with open(path, "r") as f:
            cmdline = f.read().strip()
            if cmdline:
                # Join the command line arguments with spaces.
                # There seems to be a trailing null byte, so we drop the last element.
                return cmdline.split("\0")[:-1]
            else:
                return []
    except FileNotFoundError:
        logger.warning(f"Command line for PID {con.pid} not found at {path}")
        return []
    except Exception as e:
        logger.error(f"Error reading command line for PID {con.pid}: {e}")
        return []


def _calculate_percent(con: Con, parent: Con) -> int | None:
    """Calculate the percent for a container based on its size."""

    match parent.layout:
        case "stacked" | "tabbed":
            return None
        case "splith":
            # We assume that the decoration is always at the top.
            assert con.rect.width == con.deco_rect.width or con.deco_rect.width == 0
            child_width = con.rect.width
            parent_width = get_container_size_excluding_gaps(parent)[0]
            return child_width * 100 // parent_width
        case "splitv":
            child_height = con.rect.height + con.deco_rect.height
            parent_height = get_container_size_excluding_gaps(parent)[1]
            return child_height * 100 // parent_height
        case _:
            assert False or f"Unexpected layout type {parent.layout} encountered"

    if con.rect.width == 0 or con.rect.height == 0:
        return None
    workspace = con.workspace()
    assert workspace is not None
    return (con.rect.width * con.rect.height) // (
        workspace.rect.width * workspace.rect.height
    )


def _fix_up_percentages(
    children_layouts: list[ApplicationLaunchConfig | ContainerConfig],
):
    """Make the perentages total 100%.

    This is necessary in cases where the total is not exactly 100% due to rounding errors.

    Parameters:
        children_layouts: The list of children layouts to fix up.

    Note:
        This function modifies the input list in place.
    """

    # Skip the fix-up in cases where it is not necessary.
    if not children_layouts or any(child.percent is None for child in children_layouts):
        return

    total = sum(cast(int, child.percent) for child in children_layouts)
    difference = 100 - total
    if difference != 0:
        # Lazily adjust the last child to fix the percentage.
        last_child = children_layouts[-1]
        assert last_child.percent is not None, "This should have been checked before"
        last_child.percent = cast(int, last_child.percent) + difference

    assert (
        sum(cast(int, child.percent) for child in children_layouts) == 100
    ), "Percentages do not sum up to 100% after fix-up"
