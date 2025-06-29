import logging

from i3ipc import Connection

logger = logging.getLogger(__name__)


class Client:
    def __init__(self):
        self._connection = Connection()

    def command(self, command: str):
        logger.debug(f"Running command: {command}")
        self._connection.command(command)
