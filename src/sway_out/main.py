"""Main entrypoint."""

import logging

import click
import pydantic
import yaml
from i3ipc import Connection

from sway_out.applications import launch_applications_from_layout
from sway_out.connection import check_replies

from .layout_files import load_layout_configuration


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

    for name, content in configuration.workspaces.items():
        replies = connection.command(f'workspace "{name}')
        check_replies(replies)
        launche_applications = launch_applications_from_layout(connection, content)


if __name__ == "__main__":
    main()
