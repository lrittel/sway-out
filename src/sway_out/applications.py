import logging

from i3ipc import Connection

from sway_out.connection import check_replies

from .layouts import ApplicationLaunchConfig

logger = logging.getLogger(__name__)


def escape_argument(arg: str) -> str:
    # TODO: Implement
    return f'"{arg}"'


def launch_application(connection: Connection, launch_config: ApplicationLaunchConfig):
    if isinstance(launch_config.cmd, str):
        cmd = launch_config.cmd
    else:
        cmd = " ".join(escape_argument(a) for a in launch_config.cmd)

    logger.debug(f"Launching application with: {cmd}")
    replies = connection.command("exec " + cmd)
    check_replies(replies)
