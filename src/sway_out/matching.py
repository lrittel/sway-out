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

        if leaf.app_id is not None:
            # The window is Wayland native
            logger.debug(f"Checking Wayland leaf: {leaf.app_id} ({leaf.name})")
            wayland = match_expression.wayland
            if wayland is None:
                continue
            assert (
                wayland.app_id is not None or wayland.title is not None
            ), "At least one Wayland match expression must be provided, this should be enforced by the model."
            if (
                wayland.app_id is not None
                and re.match(wayland.app_id, leaf.app_id) is None
            ):
                continue
            if wayland.title is not None and re.match(wayland.title, leaf.name) is None:
                continue
        else:
            # The window runs under XWayland
            logger.debug(
                f"Checking XWayland leaf: {leaf.window_class},{leaf.window_instance} ({leaf.window_title})"
            )
            x11 = match_expression.x11
            if x11 is None:
                continue
            assert (
                x11.class_ is not None
                or x11.instance is not None
                or x11.title is not None
            ), "At least one X11 match expression must be provided, this should be enforced by the model."
            if (
                x11.title is not None
                and leaf.window_title is not None
                and re.match(x11.title, leaf.window_title) is None
            ):
                continue
            if (
                x11.class_ is not None
                and leaf.window_class is not None
                and re.match(x11.class_, leaf.window_class) is None
            ):
                continue
            if (
                x11.instance is not None
                and leaf.window_instance is not None
                and re.match(x11.instance, leaf.window_instance) is None
            ):
                continue

        logger.debug(f"Matching leaf found: {leaf.name} ({leaf.window_title})")
        yield leaf

    logger.debug("Finished window search")


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
