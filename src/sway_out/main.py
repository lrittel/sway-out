"""Main entrypoint."""

import logging
from dataclasses import dataclass

import click
import gi
import pydantic
import yaml

gi.require_version("Notify", "0.7")
from gi.repository import Notify
from i3ipc import Connection

from .applications import launch_applications_from_layout
from .connection import run_command
from .layout import create_layout
from .layout_files import load_layout_configuration, map_workspaces
from .marks import apply_marks
from .matching import find_current_workspace
from .notifications import error_notification, progress_notification

logger = logging.getLogger(__name__)

PROG_NAME = "sway-out"

Notify.init(PROG_NAME)


@dataclass
class GlobalState:
    """The user-provided configuration for the application and some global state."""

    connection: Connection
    notifications: bool = True


@click.group()
@click.version_option(prog_name=PROG_NAME, package_name="sway-out")
@click.option(
    "--notifications/--no-notifications",
    default=True,
    help="Enable or disable notifications.",
)
@click.pass_context
def main(ctx: click.Context, notifications: bool):
    """Main entrypoint."""

    logging.basicConfig(level=logging.DEBUG)
    ctx.obj = GlobalState(Connection(), notifications)


@main.command("apply")
@click.argument("layout_file", type=click.File("rb"))
@click.pass_context
def main_apply(ctx: click.Context, layout_file):
    connection: Connection = ctx.obj.connection
    assert connection is not None
    try:
        configuration = load_layout_configuration(layout_file)
    except (yaml.YAMLError, pydantic.ValidationError) as e:
        if ctx.obj.notifications:
            error_notification("Error during layout creation", str(e))

        click.echo(f"Failed to read layout configuration: {e}", err=True)
        return

    workspace_layout_mapping = map_workspaces(connection, configuration)

    try:
        with progress_notification("Applying layout", "Workspace") as notification:
            if ctx.obj.notifications:
                notification.start()
            for index, (workspace_name, workspace_layout) in enumerate(
                workspace_layout_mapping.items()
            ):
                notification.update(index + 1, len(workspace_layout_mapping))
                run_command(connection, f"workspace {workspace_name}")
                workspace_con = find_current_workspace(connection)
                workspace_layout._con_id = workspace_con.id
                assert workspace_con is not None, "No current workspace found?"
                logger.info("Applying layout for workspace: %s", workspace_name)
                launch_applications_from_layout(connection, workspace_layout)
                create_layout(connection, workspace_layout)
                apply_marks(connection, workspace_layout)
            logger.info(
                f"Successfully applied layout for {len(workspace_layout_mapping)} workspace(s)"
            )
    except Exception as e:
        if ctx.obj.notifications:
            error_notification("Error during layout creation", str(e))

        logger.exception("An error occurred during layout creation")


if __name__ == "__main__":
    main()
