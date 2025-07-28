"""Utilities to indicate progress."""

from contextlib import contextmanager
from typing import Generator, final

from gi.repository import Notify


@final
class ProgressNotification:
    """Represents a notification showing progress."""

    def __init__(self, stage: str, text: str):
        self.summary = stage
        self.text = text
        self.notification: Notify.Notification = None

    def start(self):
        """Start the progress indicator.

        Without calling this method first, `self.update()` is a no-op.
        """

        self.notification = Notify.Notification.new(self.text, f"{self.text} ...")
        self.notification.set_timeout(Notify.EXPIRES_NEVER)
        self.notification.show()

    def update(self, progress: int, total: int):
        """Update the progress.

        Does nothing if `self.start` is not called first.
        """

        if self.notification is not None:
            self.notification.update(self.summary, f"{self.text} {progress}/{total}")
            self.notification.show()

    def finish(self):
        """Show that the process has finished.

        Does nothing if `self.start` is not called first.
        """

        if self.notification is not None:
            self.notification.update(self.summary, "Completed successfully.")
            self.notification.set_timeout(Notify.EXPIRES_DEFAULT)
            self.notification.show()

    def error(self, error_message: str):
        """Show that an error has occurred.

        Does nothing if `self.start` is not called first.
        """

        if self.notification is not None:
            self.notification.update(
                self.summary,
                f"{self.text} - Error: {error_message}",
            )
            self.notification.set_urgency(Notify.Urgency.CRITICAL)
            self.notification.set_timeout(Notify.EXPIRES_DEFAULT)
            self.notification.show()


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

    notification = Notify.Notification.new(title, text)
    notification.set_urgency(Notify.Urgency.CRITICAL)
    notification.show()
