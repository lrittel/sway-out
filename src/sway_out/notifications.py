"""Utilities to indicate progress."""

import logging
import subprocess
from contextlib import contextmanager
from typing import Generator, Literal, final

from sway_out.utils import PROG_NAME

logger = logging.getLogger(__name__)


@final
class ProgressNotification:
    """Represents a notification showing progress."""

    EXPIRE_TIME = 60_000  # 60 seconds

    def __init__(self, stage: str, text: str):
        self.summary = stage
        self.text = text
        self.successful = True
        self.notification_id: int | None = None

    def start(self):
        """Start the progress indicator.

        Without calling this method first, `self.update()` is a no-op.
        """

        self.notification_id = _run_notify_send(
            summary=self.summary,
            text=f"{self.text} ...",
            expire_time=self.EXPIRE_TIME,
        )

    def update(self, progress: int, total: int):
        """Update the progress.

        Does nothing if `self.start` is not called first.
        """

        if self.notification_id is not None:
            self.notification_id = _run_notify_send(
                summary=self.summary,
                text=f"{self.text} {progress}/{total}",
                expire_time=self.EXPIRE_TIME,
                replace_id=self.notification_id,
            )

    def finish(self):
        """Show that the process has finished.

        Does nothing if `self.start` is not called first.
        """

        if self.notification_id is not None:
            # We are intentionally not explicitly passing an expire_time to
            # respect use the user's configuration.
            if self.successful:
                self.notification_id = _run_notify_send(
                    summary=self.summary,
                    text="Completed successfully.",
                    replace_id=self.notification_id,
                )
            else:
                self.notification_id = _run_notify_send(
                    summary=self.summary,
                    text="Completed with errors.",
                    replace_id=self.notification_id,
                )

    def error(self, error_message: str):
        """Show that an error has occurred.

        Does nothing if `self.start` is not called first.
        """

        if self.notification_id is not None:
            self.notification_id = _run_notify_send(
                summary=self.summary,
                text=(f"{self.text} - " if self.text else "")
                + f"Error: {error_message}",
                urgency="critical",
                replace_id=self.notification_id,
            )


@contextmanager
def progress_notification(stage: str, text: str) -> Generator[ProgressNotification]:
    """Show a notification with progress updates.

    This function is intended to be used as a context manager.

    Parameters:
        stage: The stage of the process.
        text: The text to display in the notification.

    Returns:
        A callback function that can be used to update the progress.
    """

    notification = ProgressNotification(stage, text)
    try:
        yield notification
    except Exception as e:
        notification.error(f"{text} - Error: {e}")
        raise
    else:
        notification.finish()


def error_notification(title: str, text: str) -> None:
    """Show a notification indicating an error.

    Parameters:
        title: The title of the notification.
        text: The error message.
    """

    _run_notify_send(summary=title, text=text, urgency="critical")


def _run_notify_send(
    summary: str,
    text: str,
    urgency: Literal["low", "normal", "critical"] = "normal",
    replace_id: int | None = None,
    expire_time: int | None = None,
):
    command = [
        "notify-send",
        f"--app-name={PROG_NAME}",
        f"--urgency={urgency}",
        "--print-id",
        summary,
        text,
    ]
    if replace_id is not None:
        command.append(f"--replace-id={replace_id}")
    if expire_time is not None:
        command.append(f"--expire-time={expire_time}")
    result = subprocess.run(command, capture_output=True, text=True)
    result.check_returncode()
    notification_id = int(result.stdout.strip())
    logger.debug(f"Showing notification with ID {notification_id}: {summary} - {text}")
    return notification_id
