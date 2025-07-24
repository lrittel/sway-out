"""Funcntionality related to the layout of windows on a workspace."""

import itertools
import logging

from i3ipc import Con, Connection

from sway_out.connection import check_replies, run_command_on

from .layout_files import ApplicationLaunchConfig, ContainerConfig, WorkspaceLayout
from .matching import is_window_matching

logger = logging.getLogger(__name__)

MARK = "@"
"""The layouting algorithm requires a mark to move windows around.

This should be something that is not in use otherwise.
"""


def has_matching_layout(
    con: Con, layout: ContainerConfig | ApplicationLaunchConfig | WorkspaceLayout
) -> bool:
    """Checks whether the current state of the given workspace matches the layout.

    Parameters:
        con: The container to check.
        layout: The layout to compare against.
    Returns:
        True if the current layout matches the given layout, False otherwise.
    """

    logging.debug(f"Checking container {con.name} ({con.id}) against '{layout}'")
    if con.type not in ["con", "floating_con", "workspace"]:
        logging.debug(
            f"Unexpected container {con.name} ({con.id}) with type {con.type}"
        )
        return False

    if isinstance(layout, ApplicationLaunchConfig):
        result = True
        if con.layout != "none":
            logging.debug(
                f"Container {con.name} ({con.id}) is a container with layout {con.layout} instead of a window"
            )
            result = False
        elif not is_window_matching(con, layout.match):
            logging.debug(
                f"Container {con.name} ({con.id}) does not match the application launch config: {layout.match}"
            )
            result = False
        logging.debug(
            f"Checking application launch config: {con.name} ({con.id}) matches '{layout.match}' -> {result}"
        )
        return result
    else:
        assert isinstance(layout, ContainerConfig) or isinstance(
            layout, WorkspaceLayout
        )
        result = True
        if con.layout == "none":
            logging.debug(
                f"Container {con.name} ({con.id}) is a window instead of a container"
            )
            result = False
        else:
            current_children = list(con.nodes)
            expected_children = layout.children
            if layout.layout is not None and con.layout != layout.layout:
                logging.debug(
                    f"Container {con.name} ({con.id}) has layout {con.layout}, expected {layout.layout}"
                )
                result = False
            if len(current_children) != len(expected_children):
                logging.debug(
                    f"Container {con.name} ({con.id}) has {len(current_children)} children, expected {len(expected_children)}"
                )
                result = False
            if not all(
                has_matching_layout(child, c)
                for child, c in zip(current_children, expected_children)
            ):
                logging.debug(
                    f"Not all children of container {con.name} ({con.id}) match the expected configuration"
                )
                result = False
        logging.debug(
            f"Checking container {con.name} ({con.id}) with layout {con.layout} against '{layout}' -> {result}"
        )
        return result


def create_layout(
    connection: Connection,
    workspace_name: str,
    workspace_layout: WorkspaceLayout,
    launched_applications: list[tuple[ApplicationLaunchConfig, int]],
) -> None:
    """Creates a layout on the given workspace using the already existing windows.

    The algorithm is similar to insertion sort.

    Parameters:
        connection: A connection to sway.
        workspace_name: The name of the workspace to create the layout on.
        workspace_layout: The layout to create.
        launched_applications: A mapping from launch configurations to the window IDs of the launched windows.
    """

    def find_id(application: ApplicationLaunchConfig) -> int:
        for launch_config, con_id in launched_applications:
            if launch_config is application:
                return con_id
        assert False, f"Window ID for application {application} not found in mapping"

    def find_cons_by_id(*con_ids: int) -> list[Con]:
        """Finds all containers with the given IDs."""
        tree = connection.get_tree()
        result: list[Con] = []
        for con_id in con_ids:
            con = tree.find_by_id(con_id)
            if con is None:
                raise RuntimeError(f"Container with ID {con_id} not found in tree")
            result.append(con)
        return result

    def find_con_for_application(container: ApplicationLaunchConfig) -> Con:
        con_id = find_id(container)
        result = connection.get_tree().find_by_id(con_id)
        assert (
            result is not None
        ), f"Container for application with con ID {con_id} not found"
        return result

    def find_parent_con(con_id: int) -> Con:
        tree = connection.get_tree()
        for con in tree.descendants():
            if con_id in [c.id for c in con.nodes]:
                return con
        assert (
            False
        ), "This should not happen because there should always be at least a workspace as a parent."

    def move_con_to_workspace(con_id: int):
        [con] = find_cons_by_id(con_id)
        if con.workspace().id != workspace_id:
            logger.debug(
                f"Moving container {con.name} ({con.id}) to workspace {workspace_name}"
            )
            run_command_on(con, f"move container to workspace {workspace_name}")
        else:
            logger.debug(
                f"Container {con.name} ({con.id}) is already on workspace {workspace_name}"
            )

        # Make sure that the con is a direct child of the workspace to make layouting less error-prone.
        while find_parent_con(child_id).id != workspace_id:
            # Move the container to the right to not disturb the finished part of the layout.
            run_command_on(con, f"move right")
            # Make shure that the container is still on the workspace.
            [con] = find_cons_by_id(con_id)
            assert con.workspace().id == workspace_id, (
                f"Accidentally moved {con.name} ({con.id}) to another workspace "
                + f"({con.workspace().name} ({con.workspace().id}) "
                + f"instead of {workspace_name} ({workspace_id}))"
            )

    def swap_cons(con_id: int, target_id: int):
        [con, target_con] = find_cons_by_id(con_id, target_id)
        if target_id != con_id:
            logger.debug(
                f"Swapping container {con.name} ({con.id}) with {target_con.name} ({target_con.id}) "
                + f"to position {index} on workspace {workspace_name}"
            )
            run_command_on(con, f"swap container with con_id {target_con.id}")
        else:
            logger.debug(f"Container {con.name} ({con.id}) is already in position")

    def move_con_into(con_id: int, target_id: int):
        # There does not seem to be a way to move a con to an arbitrary position in a layout.
        # But we can move it into the layout using marks.
        [con, target_con] = find_cons_by_id(con_id, target_id)
        run_command_on(target_con, f"mark --add {MARK}")
        run_command_on(con, f"move container to mark {MARK}")
        run_command_on(target_con, f"unmark {MARK}")

    def create_container_layout(
        container_layout: ApplicationLaunchConfig | ContainerConfig,
    ) -> int:
        if isinstance(container_layout, ContainerConfig):
            assert container_layout.children, "ContainerConfig must have children"
            logger.debug(
                f"Creating layout for container as {container_layout.layout} ..."
            )

            # First, find or create the first container in the layout.
            first_child_id = create_container_layout(container_layout.children[0])

            # Then create the layout.
            [first_child_con] = find_cons_by_id(first_child_id)
            run_command_on(first_child_con, f"splith")
            [first_child_con] = find_cons_by_id(first_child_id)
            run_command_on(first_child_con, f"layout {container_layout.layout}")
            layout_con = find_parent_con(first_child_con.id)
            layout_id = layout_con.id

            # Finally add the remaining children to the layout.
            for index, child_layout in itertools.islice(
                enumerate(container_layout.children), 1, None
            ):
                child_id = create_container_layout(child_layout)

                # Ensure that the child is on the right workspace.
                move_con_to_workspace(child_id)

                # Move the child into the layout.
                move_con_into(child_id, layout_id)
                assert find_parent_con(child_id).id == layout_id, (
                    f"The child {child_id} ended up somewhere unexpected after moving it into the "
                    + f"layout {layout_id}."
                )

                # Swap the child to the correct position if needed.
                [layout_con] = find_cons_by_id(layout_id)
                assert len(layout_con.nodes) >= index + 1, (
                    f"After moving the child, there should be at least {index + 1} windows on the layout, "
                    + "but found {len(layout_con.nodes)}"
                )
                swap_cons(child_id, layout_con.nodes[index].id)

            logger.debug(f"Layout for container as {container_layout.layout} done")
            layouted_ids.add(layout_id)
            return layout_id
        else:
            # Nothing to lay out here.
            assert isinstance(container_layout, ApplicationLaunchConfig)
            result = find_con_for_application(container_layout)
            logger.debug(f'Reached leaf "{result.name}" while creating layout')
            layouted_ids.add(result.id)
            return result.id

    # Check if the mark is already in use.
    marks_in_use = connection.get_marks()
    if MARK in marks_in_use:
        raise RuntimeError(f"The mark '{MARK}' is already in use.")

    # Track which cons we have layouted to detect windows that are not supposed to be here.
    layouted_ids = set()

    # Find the con_id of the workspace to create the layout on.
    workspace_cons_filtered = [
        ws for ws in connection.get_tree().workspaces() if ws.name == workspace_name
    ]
    assert (
        len(workspace_cons_filtered) == 1
    ), f"Expected exactly one workspace with name {workspace_name}, found {len(workspace_cons_filtered)}"
    workspace_con = workspace_cons_filtered[0]
    workspace_id = workspace_con.id

    # Start the layout creation at the workspace level.
    # Set the layout of the workspace to horizontal to ensure moving containers to the workspace work correctly.
    assert (
        workspace_con.nodes
    ), f"The workspace {workspace_name} should not be empty at this point"
    run_command_on(workspace_con.nodes[0], "layout splith")
    for index, child_layout in enumerate(workspace_layout.children):
        logger.debug(f"Creating layout for workspace {workspace_name} ...")
        child_id = create_container_layout(child_layout)

        # Ensure that the child is on the right workspace.
        move_con_to_workspace(child_id)

        # Because we start at index == 0, there should now be at least index+1 windows on the workspace.
        [workspace_con] = find_cons_by_id(workspace_id)
        assert len(workspace_con.nodes) >= index + 1

        # Swap the child to the correct position if needed.
        target_con = workspace_con.nodes[index]
        swap_cons(child_id, target_con.id)

    assert (
        workspace_con.nodes
    ), f"The workspace {workspace_name} should not be empty at this point"
    if workspace_layout.layout is not None:
        # Set the layout of the workspace to the one specified in the layout.
        logger.debug(
            f"Setting layout of workspace {workspace_name} to {workspace_layout.layout}"
        )
        run_command_on(workspace_con.nodes[0], f"layout {workspace_layout.layout}")
    logger.info(f"Layout for workspace {workspace_name} done")
    layouted_ids.add(workspace_id)

    # The mark should be freed up after the layout is created.
    marks_in_use = connection.get_marks()
    assert (
        MARK not in marks_in_use
    ), f"The mark '{MARK}' was not removed after layout creation."

    # Look for windows that are not part of the layout.
    [workspace_con] = find_cons_by_id(workspace_id)
    for con in workspace_con.descendants():
        if con.id not in layouted_ids:
            logger.warning(f"Container {con.name} ({con.id}) is not part of the layout")
