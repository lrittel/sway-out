"""Main entrypoint."""

import logging

import click
import pydantic
import yaml
from i3ipc import Connection

from .applications import launch_applications_from_layout
from .connection import run_command
from .layout import create_layout
from .layout_files import load_layout_configuration, map_workspaces
from .marks import apply_marks
from .matching import find_current_workspace

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(prog_name="sway-out", package_name="sway-out")
@click.pass_context
def main(ctx: click.Context):
    """Main entrypoint."""

    logging.basicConfig(level=logging.DEBUG)
    ctx.ensure_object(Connection)


@main.command("apply")
@click.argument("layout_file", type=click.File("rb"))
@click.pass_context
def main_apply(ctx: click.Context, layout_file):
    connection = ctx.find_object(Connection)
    assert connection is not None
    try:
        configuration = load_layout_configuration(layout_file)
    except (yaml.YAMLError, pydantic.ValidationError) as e:
        click.echo(f"Failed to read layout configuration: {e}", err=True)
        return

    workspace_layout_mapping = map_workspaces(connection, configuration)

    for workspace_name, workspace_layout in workspace_layout_mapping.items():
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


if __name__ == "__main__":
    main()
