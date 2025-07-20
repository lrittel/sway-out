"""Funcntionality related to the layout of windows on a workspace."""

import logging

from i3ipc import Con

from .layout_files import ApplicationLaunchConfig, ContainerConfig, WorkspaceLayout
from .matching import is_window_matching

logger = logging.getLogger(__name__)


def has_matching_layout(
    con: Con, layout: ContainerConfig | ApplicationLaunchConfig | WorkspaceLayout
) -> bool:
    """Checks whether the current state of the given workspace matches the layout.

    Parameters:
        con: The container to check.
        layout: The layout to compare against.
    Returns:
        True if the current layout matches the given layout, False otherwise.
    """

    logging.debug(f"Checking container {con.name} ({con.id}) against '{layout}'")
    if con.type not in ["con", "floating_con", "workspace"]:
        logging.debug(
            f"Unexpected container {con.name} ({con.id}) with type {con.type}"
        )
        return False

    if isinstance(layout, ApplicationLaunchConfig):
        result = True
        if con.layout != "none":
            logging.debug(
                f"Container {con.name} ({con.id}) is a container with layout {con.layout} instead of a window"
            )
            result = False
        elif not is_window_matching(con, layout.match):
            logging.debug(
                f"Container {con.name} ({con.id}) does not match the application launch config: {layout.match}"
            )
            result = False
        logging.debug(
            f"Checking application launch config: {con.name} ({con.id}) matches '{layout.match}' -> {result}"
        )
        return result
    else:
        assert isinstance(layout, ContainerConfig) or isinstance(
            layout, WorkspaceLayout
        )
        result = True
        if con.layout == "none":
            logging.debug(
                f"Container {con.name} ({con.id}) is a window instead of a container"
            )
            result = False
        else:
            current_children = list(con.nodes)
            expected_children = layout.children
            if layout.layout is not None and con.layout != layout.layout:
                logging.debug(
                    f"Container {con.name} ({con.id}) has layout {con.layout}, expected {layout.layout}"
                )
                result = False
            if len(current_children) != len(expected_children):
                logging.debug(
                    f"Container {con.name} ({con.id}) has {len(current_children)} children, expected {len(expected_children)}"
                )
                result = False
            if not all(
                has_matching_layout(child, c)
                for child, c in zip(current_children, expected_children)
            ):
                logging.debug(
                    f"Not all children of container {con.name} ({con.id}) match the expected configuration"
                )
                result = False
        logging.debug(
            f"Checking container {con.name} ({con.id}) with layout {con.layout} against '{layout}' -> {result}"
        )
        return result
