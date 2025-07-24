"""Functions for managing marks on containers."""

from i3ipc import Connection

from .connection import find_cons_by_id, run_command_on
from .layout_files import ApplicationLaunchConfig, ContainerConfig, WorkspaceLayout


def has_marks(connection: Connection, workspace_layout: WorkspaceLayout) -> bool:
    """Check if the the workspace has all marks from the layout assigned.

    Parameters:
        connection: A connection to Sway.
        workspace_layout: The layout containing the marks to check for.

    Returns:
        True if the workspace has all marks assigned, False otherwise.
    """

    def go(layout: ContainerConfig | ApplicationLaunchConfig):
        (con,) = find_cons_by_id(connection, layout._con_id)

        return not (set(layout.assigned_marks) - set(con.marks)) and (
            not isinstance(layout, ContainerConfig)
            or all(go(child) for child in layout.children)
        )

    return all(go(child) for child in workspace_layout.children)


def apply_marks(connection: Connection, workspace_layout: WorkspaceLayout) -> None:
    """Apply marks to containers in the specified workspace layout.

    All nodes with marks in the workspace layout have to have their con_id set.

    Parameters:
        connection: A connection to Sway.
        workspace_layout: The layout containing the containers to mark.
    """

    def go(layout: ContainerConfig | ApplicationLaunchConfig):
        (con,) = find_cons_by_id(connection, layout._con_id)
        marks = layout.assigned_marks
        for m in marks:
            run_command_on(con, f"mark --add {m}")

        if isinstance(layout, ContainerConfig):
            for child in layout.children:
                go(child)

    for child in workspace_layout.children:
        go(child)
