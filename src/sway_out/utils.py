"""Small utility function."""

from i3ipc import Con

PROG_NAME = "sway-out"


def is_window(con: Con) -> bool:
    """Check if a container is a window.

    Parameters:
        con: The container to check.

    Returns:
        `True` if the container is a window, `False` otherwise.
    """
    return con.pid is not None


def get_con_description(con: Con) -> str:
    """Get a human-readable description of a container.

    Parameters:
        con: The container to describe.

    Returns:
        A string describing the container.
    """

    if is_window(con):
        return f"{con.name} (PID: {con.pid})"
    elif con.type == "workspace":
        return f"{con.name} (ID: {con.id})"
    else:
        return f"{con.name} (ID: {con.id})"
