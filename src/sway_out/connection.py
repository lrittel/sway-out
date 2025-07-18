"""Utilities related to the Sway connection."""

import logging

from i3ipc import CommandReply

logger = logging.getLogger(__name__)


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
