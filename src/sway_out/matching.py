"""Matching windows."""

import logging
import re
from collections.abc import Generator

from i3ipc import Con, Connection

from .layout_files import WindowMatchExpression

logger = logging.getLogger(__name__)


def find_windows_on_workspace(
    match_expression: WindowMatchExpression, workspace: Con
) -> Generator[Con]:
    """Find all windows on a workspace given a match expression.

    Parameters:
        match_expression: The match expression to use.
        workspace: A workspace tree object.
    """

    leaves = list(workspace.leaves())
    logger.debug(
        f'Looking for windows on the current workspace "{workspace.name}" with {len(leaves)} leaves'
    )
    for leaf in leaves:
        if leaf.type not in ["con", "floating_con"]:
            logger.debug(
                f"Skipping leaf with type {leaf.type}: {leaf.name} ({leaf.window_title})"
            )
            continue

        if is_window_matching(leaf, match_expression):
            logger.debug(f"Matching leaf found: {leaf.name} ({leaf.window_title})")
            yield leaf

    logger.debug("Finished window search")


def is_window_matching(con: Con, match_expression: WindowMatchExpression) -> bool:
    """Check if a window matches the given match expression.

    Parameters:
        con: The window to check.
        match_expression: The match expression to use.

    Returns:
        True if the window matches the expression, False otherwise.
    """

    if con.app_id is not None:
        # The window is Wayland native
        logger.debug(f"Checking Wayland con: {con.app_id} ({con.name})")
        wayland = match_expression.wayland
        if wayland is None:
            return False
        assert (
            wayland.app_id is not None or wayland.title is not None
        ), "At least one Wayland match expression must be provided, this should be enforced by the model."
        return (
            wayland.app_id is None or re.match(wayland.app_id, con.app_id) is not None
        ) and (wayland.title is None or re.match(wayland.title, con.name) is not None)
    elif con.window_class is not None or con.window_instance is not None:
        # The window runs under XWayland
        logger.debug(
            f"Checking XWayland con: {con.window_class},{con.window_instance} ({con.window_title})"
        )
        x11 = match_expression.x11
        if x11 is None:
            return False
        assert (
            x11.class_ is not None or x11.instance is not None or x11.title is not None
        ), "At least one X11 match expression must be provided, this should be enforced by the model."
        return (
            (x11.title is None or re.match(x11.title, con.window_title) is not None)
            and (
                x11.class_ is None or re.match(x11.class_, con.window_class) is not None
            )
            and (
                x11.instance is None
                or re.match(x11.instance, con.window_instance) is not None
            )
        )
    else:
        return False


def find_current_workspace(connection: Connection) -> Con | None:
    """Find the current workspace.

    Parameters:
        connection: A connection to Sway

    Returns:
        The tree node of the current workspace or `None` if it is not available.
    """

    tree = connection.get_tree()
    focused = tree.find_focused()
    if focused is None:
        return None
    workspace = focused.workspace()
    return workspace
