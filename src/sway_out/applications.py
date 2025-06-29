import logging
import time

from i3ipc import Con, Connection

from sway_out.connection import check_replies
from sway_out.matching import find_current_workspace, find_windows_on_workspace

from .layouts import ApplicationLaunchConfig, WindowMatchExpression

logger = logging.getLogger(__name__)

LAUNCH_TIMEOUT_SECONDS = 10
"""How long to wait for the application to launch before giving up."""

LAUNCH_CHECK_INTERVAL_SECONDS = 0.5
"""How long to wait between checks for the application window."""


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

    Parameters:
        connection: A connection to Sway.
        launch_config: The launch configuration for the application.
    Raises:
        RuntimeError:
            If the application fails to start.
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
        wait_for_window(
            connection, workspace, launch_config.match, matching_windows_before
        )
    except RuntimeError as e:
        logger.error(f"Failed to launch application '{cmd}': {e}")
        raise RuntimeError(f"Failed to launch application '{cmd}': {e}") from e
    else:
        logger.info(f"'{cmd}' successfully launched")


def wait_for_window(
    connection: Connection,
    workspace: Con,
    match: WindowMatchExpression,
    known_windows: list[Con],
):
    """Wait for the application to launch and a matching window to appear on the workspace.

    Parameters:
        connection: A connection to Sway.
        workspace: The workspace tree node to look in.
        match: The matching expression to use.
        known_windows: Windows to ignore.
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
            f"{len(matching_windows)} window(s) currently match the expression launch"
        )
        for window in matching_windows:
            if window.id not in known_window_ids:
                logger.debug(
                    f"New matching window found: {window.name} ({window.window_title})"
                )
                return
        time.sleep(LAUNCH_CHECK_INTERVAL_SECONDS)
    else:
        raise RuntimeError(
            f"Application did not launch within {LAUNCH_TIMEOUT_SECONDS} seconds."
        )
