"""Main entrypoint."""

import logging

import click
import pydantic
import yaml
from i3ipc import Connection

from .applications import launch_applications_from_layout
from .connection import check_replies, get_focused_workspace
from .layout import create_layout, has_matching_layout
from .layout_files import load_layout_configuration
from .marks import apply_marks


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

    focused_workspace = get_focused_workspace(connection)

    for name, content in configuration.workspaces.items():
        replies = connection.command(f'workspace "{name}')
        check_replies(replies)
        workspace = get_focused_workspace(connection)
        assert workspace is not None, "We are on a non-existing workspace?"
        content._con_id = workspace.id
        launch_applications_from_layout(connection, content)
        create_layout(connection, content)
        apply_marks(connection, content)

    if configuration.focused_workspace:
        if focused_workspace is None:
            click.echo(
                "No focused workspace found. Cannot apply focused workspace layout.",
                err=True,
            )
            return
        replies = connection.command(f'workspace "{focused_workspace}"')
        check_replies(replies)
        content = connection.focused_workspace
        content._con_id = workspace.id
        launch_applications_from_layout(connection, content)
        create_layout(connection, content)
        apply_marks(connection, content)


if __name__ == "__main__":
    main()
