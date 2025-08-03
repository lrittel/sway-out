"""Launching of applications."""

import logging
import time

from i3ipc import Con, Connection

from .connection import check_replies
from .layout_files import (
    ApplicationLaunchConfig,
    ContainerConfig,
    WindowMatchExpression,
    WorkspaceLayout,
)
from .matching import find_current_workspace, find_windows_on_workspace
from .utils import get_con_description

logger = logging.getLogger(__name__)

LAUNCH_TIMEOUT_SECONDS = 10
"""How long to wait for the application to launch before giving up.

See also:
  - [wait_for_window][sway_out.applications.wait_for_window]
"""

LAUNCH_CHECK_INTERVAL_SECONDS = 0.5
"""How long to wait between checks for the application window.

See also:
  - [wait_for_window][sway_out.applications.wait_for_window]
"""


def match_existing_windows(workspace: Con, layout: WorkspaceLayout) -> None:
    """Match existing windows in the workspace with the launch configurations.

    This function updates the con_id of the launch configurations in the layout
    to match existing windows on the current workspace.

    Parameters:
        workspace: The workspace to search for existing windows.
        layout: The layout containing the applications to match.

    Note:
        This function modifies its argument.
    """

    def match_element(
        element_layout: ApplicationLaunchConfig | ContainerConfig,
    ) -> None:
        if isinstance(element_layout, ApplicationLaunchConfig):
            matching_windows = [
                con
                for con in find_windows_on_workspace(element_layout.match, workspace)
                if con.id not in matched_con_ids
            ]
            if matching_windows:
                con = matching_windows[0]
                element_layout._con_id = con.id
                matched_con_ids.add(con.id)
                logger.info(f"Matched existing window {get_con_description(con)}")
            else:
                logger.debug(f"No matching window found for {element_layout.cmd}")
        else:
            assert isinstance(element_layout, ContainerConfig)
            for child in element_layout.children:
                match_element(child)

    matched_con_ids: set[int] = set()

    for child in layout.children:
        match_element(child)

    logger.debug(f"Matched {len(matched_con_ids)} existing windows in the layout")


def launch_applications_from_layout(connection: Connection, layout: WorkspaceLayout):
    """Launch the applications contained in the given layout.

    The con_id of the launched applications are stored in
    the launch configurations for later reference.

    Parameters:
        connection: A connection to Sway.
        layout: The layout containing the applications to launch.

    Note:
        This function modifies its argument.

    See also:
        - [sway_out.applications.launch_application][]
    """

    def go(container: ApplicationLaunchConfig | ContainerConfig) -> None:
        if isinstance(container, ApplicationLaunchConfig):
            if hasattr(container, "_con_id"):
                logger.debug(
                    f"Skipping launch of {container.cmd} because it matched an existing window"
                )
            else:
                launch_application(connection, container)
        else:
            assert isinstance(container, ContainerConfig)
            for child in container.children:
                go(child)

    for child in layout.children:
        go(child)


def escape_argument(arg: str) -> str:
    """Escape a string for the use in a Sway command.

    Parameters:
        arg: The argument string.

    Returns:
        The argument string with some characters escaped.
    """
    # TODO: Implement
    return f'"{arg}"'


def launch_application(connection: Connection, launch_config: ApplicationLaunchConfig):
    """Launch an application on the current workspace.

    The con_id of the launched application is stored in the
    launch configuration for later reference.

    Parameters:
        connection: A connection to Sway.
        launch_config: The launch configuration for the application.

    Raises:
        RuntimeError:
            If the application fails to start.

    Note:
        This function modifies its argument.
    """

    if isinstance(launch_config.cmd, str):
        cmd = launch_config.cmd
    else:
        cmd = " ".join(escape_argument(a) for a in launch_config.cmd)

    # Find the currently focused workspace to launch the application on.
    workspace = find_current_workspace(connection)
    if workspace is None:
        logger.warning("No focused workspace found to search for windows.")
        raise RuntimeError("No focused workspace found to search for windows.")
    logger.debug(f"Preparing to launch command on focused workspace: {workspace.name}")

    # Find existing windows that match the launch configuration to ignore them.
    matching_windows_before = list(
        find_windows_on_workspace(launch_config.match, workspace)
    )
    logger.debug(
        f"{len(matching_windows_before)} window(s) match the expression before launch"
    )

    # Launch the application.
    logger.debug(f"Launching application with: '{cmd}'")
    replies = connection.command("exec " + cmd)
    check_replies(replies)

    # Wait for the application to launch and the window to appear
    try:
        con_id = wait_for_window(
            connection, workspace, launch_config.match, matching_windows_before
        )
    except RuntimeError as e:
        logger.error(f"Failed to launch application '{cmd}': {e}")
        raise RuntimeError(f"Failed to launch application '{cmd}': {e}") from e
    else:
        logger.info(f"'{cmd}' successfully launched with con_id {con_id}")
        launch_config._con_id = con_id


def wait_for_window(
    connection: Connection,
    workspace: Con,
    match: WindowMatchExpression,
    known_windows: list[Con],
) -> int:
    """Wait for the application to launch and a matching window to appear on the workspace.

    Parameters:
        connection: A connection to Sway.
        workspace: The workspace tree node to look in.
        match: The matching expression to use.
        known_windows: Windows to ignore.

    Returns:
        The Sway ID of the new con.

    Raises:
        RuntimeError:
            If no matching window is found within the timeout duration.
    """

    known_window_ids = {window.id for window in known_windows}
    matching_windows = []
    for _ in range(int(LAUNCH_TIMEOUT_SECONDS / LAUNCH_CHECK_INTERVAL_SECONDS)):
        # update the workspace to check for new windows
        workspace = connection.get_tree().find_by_id(workspace.id)
        if workspace is None:
            raise RuntimeError("The workspace has disappeared")
        logger.debug(f"Checking for matching windows")
        matching_windows = list(find_windows_on_workspace(match, workspace))
        logger.debug(
            f"{len(matching_windows)} window(s) currently match the launch expression {match}"
        )
        for window in matching_windows:
            if window.id not in known_window_ids:
                logger.debug(
                    f"New matching window found: {window.name} ({window.window_title})"
                )
                return window.id
        time.sleep(LAUNCH_CHECK_INTERVAL_SECONDS)
    else:
        raise RuntimeError(
            f"Application did not launch within {LAUNCH_TIMEOUT_SECONDS} seconds."
        )
