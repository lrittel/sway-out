import logging

import click
import pydantic
import yaml

from sway_out.applications import launch_application

from .client import Client
from .layouts import load_layout_configuration


@click.group()
@click.version_option(prog_name="sway-out", package_name="sway-out")
@click.pass_context
def main(ctx: click.Context):
    logging.basicConfig(level=logging.DEBUG)
    ctx.ensure_object(Client)


@main.command("apply")
@click.argument("layout_file", type=click.File("rb"))
@click.pass_context
def main_foo(ctx: click.Context, layout_file):
    client = ctx.find_object(Client)
    try:
        configuration = load_layout_configuration(layout_file)
    except (yaml.YAMLError, pydantic.ValidationError) as e:
        click.echo(f"Failed to read layout configuration: {e}", err=True)
        return

    for application in configuration.applications:
        launch_application(client, application)


if __name__ == "__main__":
    main()
