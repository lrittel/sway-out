import click


@click.group()
@click.version_option(prog_name="sway-out", package_name="sway-out")
@click.pass_context
def main(ctx: click.Context):
    ctx.ensure_object({})
    ctx.obj["SETTING"] = "value"
    pass


@main.command("foo")
@click.option("--flag-a", default=1, help="Optional argument")
@click.option("--flag-b", type=click.Path(), prompt="A path")
@click.option(
    "--flag-c", envvar="FLAG_C", prompt="Can be set using an environment variable"
)
@click.argument("arg-a")
@click.argument("arg-b", nargs=-1)
@click.pass_context
def main_foo(ctx, flag_a, flag_b, flag_c, arg_a, arg_b):
    print(ctx.obj)


if __name__ == "__main__":
    main()
