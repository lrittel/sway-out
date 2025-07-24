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


def get_focused_workspace(connection: Connection) -> Con | None:
    """Get the currently focused workspace.

    Arguments:
        connection: The Sway connection.

    Returns:
        The con of the focused workspace, or None if no workspace is focused.
    """

    tree = connection.get_tree()
    focused = tree.find_focused()
    if focused is None:
        logger.warning("No focused con found.")
        return None
    if focused.type != "workspace":
        focused = focused.workspace()
    if focused is None:
        logger.warning("No focused workspace found.")
        return None
    return focused


def find_cons_by_id(connection: Connection, *con_ids: int) -> tuple[Con, ...]:
    """Finds all containers with the given IDs.

    Each call to this function results in one IPC call. So passing multiple
    con_ids at once reduces the number of IPC calls while also ensuring that
    all con objects are consistent.

    Arguments:
        connection: The Sway connection to use.
        con_ids: The IDs of the containers to find.

    Returns:
        A list of containers with the given IDs. The order of the list matches
        the order of the IDs.

    Raises:
        RuntimeError: If a container with a given ID is not found in the tree.
    """
    tree = connection.get_tree()
    result = tuple(tree.find_by_id(con_id) for con_id in con_ids)
    missing_ids = [con_id for con_id, con in zip(con_ids, result) if con is None]
    if missing_ids:
        raise RuntimeError(
            f"Container(s) with IDs {', '.join(str(i) for i in missing_ids)} not found in tree"
        )
    assert None not in result
    return result
