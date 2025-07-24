"""Utilities related to the Sway connection."""

import logging

from i3ipc import CommandReply, Con, Connection

logger = logging.getLogger(__name__)


def run_command_on(con: Con, command: str) -> None:
    """Run a command on the given container and checks the reply.

    Arguments:
        con: The container to run the command on.
        command: The command to run.
    Raises:
        RuntimeError: If the command fails.
    """
    logger.debug(f"Running command '{command}' on container {con.name} ({con.id})")
    replies = con.command(command)
    check_replies(replies)


def check_replies(replies: list[CommandReply]):
    """Check a list of replies for errors.

    Arguments:
        replies: The replies to check.
    Raises:
        RuntimeError: If at least one reply indicates a failure.
    """
    for reply in replies:
        logger.debug(f"Command raw reply: {reply.ipc_data}")
        if not reply.success:
            raise RuntimeError(f"Command failed: {reply.error}")


def get_focused_workspace(connection: Connection) -> str | None:
    """Get the currently focused workspace.
    Arguments:
        connection: The Sway connection.
    Returns:
        The name of the focused workspace, or None if no workspace is focused.
    """

    workspaces = connection.get_workspaces()
    for workspace in workspaces:
        if workspace.focused:
            return workspace.name
    return None
