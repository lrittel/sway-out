"""Functions to place workspaces on outputs."""

import logging
from collections.abc import Generator

from i3ipc import Connection

from sway_out.connection import find_cons_by_id, run_command
from sway_out.layout_files import WorkspaceLayout

logger = logging.getLogger(__name__)


def move_workspace_to_output(connection: Connection, workspace_layout: WorkspaceLayout):
    """Move the given workspace_layout to the output if one is specified and available."""

    if workspace_layout.output is None:
        outputs_to_try = []
    elif isinstance(workspace_layout.output, str):
        outputs_to_try = [workspace_layout.output]
    else:
        assert isinstance(workspace_layout.output, list)
        outputs_to_try = workspace_layout.output

    existing_outputs = set(_get_output_names(connection))
    assert (
        workspace_layout._con_id is not None
    ), "The workspace needs to be populated first."
    for output in outputs_to_try:
        if output in existing_outputs:
            run_command(connection, f"move workspace to output {output}")
            logger.debug(f"Moved workspace to {output}")
            break
        else:
            logger.debug(f"Output {output} does not exist")


def _get_output_names(connection: Connection) -> Generator[str]:
    """Retrieve the names of the available outputs."""

    for output in connection.get_outputs():
        yield output.name
