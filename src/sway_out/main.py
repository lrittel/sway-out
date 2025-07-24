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
        launched_applications = launch_applications_from_layout(connection, content)
        create_layout(connection, name, content, launched_applications)

    if configuration.focused_workspace:
        if focused_workspace is None:
            click.echo(
                "No focused workspace found. Cannot apply focused workspace layout.",
                err=True,
            )
            return
        replies = connection.command(f'workspace "{focused_workspace}"')
        check_replies(replies)
        launched_applications = launch_applications_from_layout(
            connection, configuration.focused_workspace
        )
        create_layout(
            connection,
            focused_workspace,
            configuration.focused_workspace,
            launched_applications,
        )


@main.command("check")
@click.argument("layout_file", type=click.File("rb"))
@click.pass_context
def main_check(ctx: click.Context, layout_file):
    connection = ctx.find_object(Connection)
    assert connection is not None
    try:
        configuration = load_layout_configuration(layout_file)
    except (yaml.YAMLError, pydantic.ValidationError) as e:
        click.echo(f"Failed to read layout configuration: {e}", err=True)
        return

    focused_workspace = get_focused_workspace(connection)

    is_matching = True
    tree = connection.get_tree()
    for name, content in configuration.workspaces.items():
        for workspace in tree.workspaces():
            if workspace.name == name:
                break
        else:
            click.echo(f"Workspace '{name}' not found.", err=True)
            return

        if has_matching_layout(workspace, content):
            click.echo(f"Workspace '{name}' matches the layout.")
        else:
            click.echo(f"Workspace '{name}' does not match the layout.")
            is_matching = False

    if configuration.focused_workspace:
        if focused_workspace is None:
            click.echo(
                "No focused workspace found. Cannot check focused workspace layout.",
                err=True,
            )
            return
        for workspace in tree.workspaces():
            if workspace.name == name:
                break
        else:
            assert False, "Focused workspace should always be in the tree"
        if has_matching_layout(workspace, configuration.focused_workspace):
            click.echo("Focused workspace matches its layout.")
        else:
            click.echo("Focused workspace does not match its layout.")
            is_matching = False

    if is_matching:
        click.echo("All workspaces match their layouts.")
    else:
        click.echo("Some workspaces do not match their layouts.")


if __name__ == "__main__":
    main()
