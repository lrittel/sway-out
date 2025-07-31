"""Funcntionality related to the layout of windows on a workspace."""

import itertools
import logging
from typing import Literal

from i3ipc import Con, Connection

from .connection import find_cons_by_id, run_command_on
from .layout_files import ApplicationLaunchConfig, ContainerConfig, WorkspaceLayout
from .utils import get_con_description

logger = logging.getLogger(__name__)

MARK = "@"
"""The layouting algorithm requires a mark to move windows around.

This should be something that is not in use otherwise.
"""

RESIZE_ATTEMPTS = 5
"""Number of attempts to resize a container to the expected size."""

RESIZE_TOLERANCE_PERCENT = 1
"""The tolerance in percent for resizing a container.

Because the parent container size might not always be exactly divisible by the
ratio of the children, we allow a small tolerance so that the layout can still be
applied.
"""


def create_layout(
    connection: Connection,
    workspace_layout: WorkspaceLayout,
) -> None:
    """Creates a layout on the given workspace using the already existing windows.

    The algorithm is similar to insertion sort.

    All launch configurations have to have a con_id set.  The con_id attributes
    of containers will be set in the process.

    Parameters:
        connection: A connection to sway.
        workspace_layout: The layout to create.

    Note: This function modifies its argument.
    """

    def find_parent_con(con_id: int) -> Con:
        tree = connection.get_tree()
        for con in tree.descendants():
            if con_id in [c.id for c in con.nodes]:
                return con
        assert (
            False
        ), "This should not happen because there should always be at least a workspace as a parent."

    def move_con_to_workspace(con_id: int):
        (con,) = find_cons_by_id(connection, con_id)
        if con.workspace().id != workspace_id:
            logger.debug(
                f"Moving container {get_con_description(con)} to workspace {get_con_description(workspace_con)}"
            )
            run_command_on(
                con, f"move container to workspace {get_con_description(workspace_con)}"
            )
        else:
            logger.debug(
                f"Container {get_con_description(con)} is already on workspace {get_con_description(workspace_con)}"
            )

        # Make sure that the con is a direct child of the workspace to make layouting less error-prone.
        while find_parent_con(child_id).id != workspace_id:
            # Move the container to the right to not disturb the finished part of the layout.
            run_command_on(con, f"move right")
            # Make shure that the container is still on the workspace.
            (con,) = find_cons_by_id(connection, con_id)
            assert con.workspace().id == workspace_id, (
                f"Accidentally moved {get_con_description(con)} to another workspace "
                + f"({get_con_description(con.workspace())} "
                + f"instead of {get_con_description(workspace_con)})"
            )

    def swap_cons(con_id: int, target_id: int):
        (con, target_con) = find_cons_by_id(connection, con_id, target_id)
        if target_id != con_id:
            logger.debug(
                f"Swapping container {get_con_description(con)} with {get_con_description(target_con)} "
                + f"to position {index} on workspace {get_con_description(workspace_con)}"
            )
            run_command_on(con, f"swap container with con_id {target_con.id}")
        else:
            logger.debug(f"Container {get_con_description(con)} is already in position")

    def move_con_into(con_id: int, target_id: int):
        # There does not seem to be a way to move a con to an arbitrary position in a layout.
        # But we can move it into the layout using marks.
        (con, target_con) = find_cons_by_id(connection, con_id, target_id)
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
            (first_child_con,) = find_cons_by_id(connection, first_child_id)
            run_command_on(first_child_con, f"splith")
            (first_child_con,) = find_cons_by_id(connection, first_child_id)
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
                (layout_con, child_con) = find_cons_by_id(
                    connection, layout_id, child_id
                )
                assert len(layout_con.nodes) >= index + 1, (
                    f"After moving the child, there should be at least {index + 1} windows on the layout, "
                    + "but found {len(layout_con.nodes)}"
                )
                swap_cons(child_id, layout_con.nodes[index].id)

            logger.debug(f"Layout for container as {container_layout.layout} done")
            layouted_ids.add(layout_id)
            container_layout._con_id = layout_id
            return layout_id
        else:
            # Nothing to lay out here.
            assert isinstance(container_layout, ApplicationLaunchConfig)
            tree = connection.get_tree()
            result = _find_con(tree, container_layout)
            logger.debug(f'Reached leaf "{result.name}" while creating layout')
            layouted_ids.add(result.id)
            return result.id

    # Check if the mark is already in use.
    marks_in_use = connection.get_marks()
    if MARK in marks_in_use:
        raise RuntimeError(f"The mark '{MARK}' is already in use.")

    # Track which cons we have layouted to detect windows that are not supposed to be here.
    layouted_ids = set()

    # Start the layout creation at the workspace level.
    # Set the layout of the workspace to horizontal to ensure moving containers to the workspace work correctly.
    workspace_id = workspace_layout._con_id
    assert workspace_id is not None, "The con_id should have been set earlier"
    (workspace_con,) = find_cons_by_id(connection, workspace_id)
    assert (
        workspace_con.nodes
    ), f"The workspace {get_con_description(workspace_con)} should not be empty at this point"
    run_command_on(workspace_con.nodes[0], "layout splith")
    for index, child_layout in enumerate(workspace_layout.children):
        logger.debug(
            f"Creating layout for workspace {get_con_description(workspace_con)} ..."
        )
        child_id = create_container_layout(child_layout)

        # Ensure that the child is on the right workspace.
        move_con_to_workspace(child_id)

        # Because we start at index == 0, there should now be at least index+1 windows on the workspace.
        (workspace_con, child_con) = find_cons_by_id(connection, workspace_id, child_id)
        assert len(workspace_con.nodes) >= index + 1

        # Swap the child to the correct position if needed.
        target_con = workspace_con.nodes[index]
        swap_cons(child_id, target_con.id)

    assert (
        workspace_con.nodes
    ), f"The workspace {get_con_description(workspace_con)} should not be empty at this point"
    if workspace_layout.layout is not None:
        # Set the layout of the workspace to the one specified in the layout.
        logger.debug(
            f"Setting layout of workspace {get_con_description(workspace_con)} to {workspace_layout.layout}"
        )
        run_command_on(workspace_con.nodes[0], f"layout {workspace_layout.layout}")
    logger.info(f"Layout for workspace {get_con_description(workspace_con)} done")
    layouted_ids.add(workspace_id)

    # The mark should be freed up after the layout is created.
    marks_in_use = connection.get_marks()
    assert (
        MARK not in marks_in_use
    ), f"The mark '{MARK}' was not removed after layout creation."


def find_leftover_windows(
    connection: Connection, workspace_layout: WorkspaceLayout
) -> list[Con]:
    """Finds windows that are not part of the given workspace layout.

    Parameters:
        connection: A connection to sway.
        workspace_layout: The layout to check against.

    Returns:
        A list of windows that are not part of the layout.
    """

    def remove_matched_windows(
        con_layout: WorkspaceLayout | ContainerConfig | ApplicationLaunchConfig,
    ):
        if isinstance(con_layout, ApplicationLaunchConfig):
            assert (
                con_layout._con_id is not None
            ), "The con_id of the application launch config should have been set before calling this function."
            if con_layout._con_id in leftover_windows:
                del leftover_windows[con_layout._con_id]
            else:
                logger.warning(
                    f"Application {con_layout.name} with con_id {con_layout._con_id} not found while "
                    + "looking for leftover windows."
                )
        else:
            for child in con_layout.children:
                remove_matched_windows(child)

    tree = connection.get_tree()
    workspace_id = workspace_layout._con_id
    leftover_windows = {
        con.id: con for con in tree.leaves() if con.workspace().id == workspace_id
    }
    remove_matched_windows(workspace_layout)
    return leftover_windows.values()


def resize_layout(
    connection: Connection,
    workspace_layout: WorkspaceLayout,
) -> None:
    """Resizes the containers on the workspace so that they match the given layout.


    Parameters:
        connection: A connection to sway.
        workspace_layout: The layout to apply.
    """

    def resize_children(con_layout: WorkspaceLayout | ContainerConfig):
        con = _find_con(tree, con_layout)

        con_width_px, con_height_px = _get_container_size_excluding_gaps(con)

        if con_layout.layout in ["splith", "splitv"]:
            layout = con_layout.layout
        else:
            layout = "other"

        # Give up after a few attempts to avoid infinite loops.
        for i in range(RESIZE_ATTEMPTS):
            logger.debug(
                f"Resizing container {get_con_description(con)} to {con_width_px}px x {con_height_px}px "
                + f"(attempt {i + 1}/{RESIZE_ATTEMPTS})"
            )
            retry = False
            for child in con_layout.children:
                if not resize_con(child, con_width_px, con_height_px, layout):
                    retry = True
            if not retry:
                logger.debug(
                    f"Container {get_con_description(con)} resized successfully after "
                    + f"{i+1}/{RESIZE_ATTEMPTS} attempts."
                )
                break
        else:
            logger.error(
                f"Failed to resize container {get_con_description(con)} to {con_width_px}px x {con_height_px}px "
                + f"after {RESIZE_ATTEMPTS} attempts."
            )

    def resize_con(
        con_layout: ApplicationLaunchConfig | ContainerConfig,
        parent_width_px: int,
        parent_height_px: int,
        parent_layout: Literal["splith", "splitv", "other"],
    ) -> bool:
        con = _find_con(tree, con_layout)

        result = True
        if con_layout.percent is not None:
            assert parent_layout != "other", (
                "Percentages are only supported for horizontal and vertical splits, not for other layouts."
                + "This should have been enforced by the configuration models."
            )
            if parent_layout == "splith":
                expected_width_px = parent_width_px * con_layout.percent // 100
                run_command_on(con, f"resize set width {expected_width_px} px")
                actual_width_px = con.rect.width
                tolerance_px = expected_width_px * RESIZE_TOLERANCE_PERCENT // 100
                logger.debug(
                    f"Expected width: {expected_width_px}px, actual width: {actual_width_px}px, "
                    + f"tolerance: {tolerance_px}px"
                )
                result = (
                    expected_width_px - tolerance_px
                    <= actual_width_px
                    <= expected_width_px + tolerance_px
                )
            else:
                expected_height_px = parent_height_px * con_layout.percent // 100
                run_command_on(con, f"resize set height {expected_height_px} px")
                actual_height_px = con.rect.height
                tolerance_px = expected_height_px * RESIZE_TOLERANCE_PERCENT // 100
                logger.debug(
                    f"Expected height: {expected_height_px}px, actual height: {actual_height_px}px, "
                    + f"tolerance: {tolerance_px}px"
                )
                result = (
                    expected_height_px - tolerance_px
                    <= actual_height_px
                    <= expected_height_px + tolerance_px
                )

        # Resize children once the parent container has been resized.
        if result and isinstance(con_layout, ContainerConfig):
            resize_children(con_layout)

        return result

    tree = connection.get_tree()
    resize_children(workspace_layout)


def check_layout(
    connection: Connection,
    workspace_layout: WorkspaceLayout,
) -> bool:
    """Checks if the current layout matches the given workspace layout.

    Parameters:
        connection: A connection to sway.
        workspace_layout: The layout to check against.

    Returns:
        `True` if the current layout matches the given workspace layout, `False` otherwise.
    """

    def check_container_layout(
        container_layout: ApplicationLaunchConfig | ContainerConfig,
        parent_width_px: int,
        parent_height_px: int,
        parent_layout: Literal["splith", "splitv", "other"],
    ) -> bool:
        assert (
            container_layout._con_id is not None
        ), "The con_id of the container layout should have been set before calling this function."

        con = tree.find_by_id(container_layout._con_id)

        result = True

        if container_layout.percent is not None:
            assert parent_layout != "other", (
                "Percentages are only supported for horizontal and vertical splits, not for other layouts."
                + "This should have been enforced by the configuration models."
            )
            if parent_layout == "splith":
                # We assume that the decoration is always at the top.
                assert con.rect.width == con.deco_rect.width or con.deco_rect.width == 0
                actual_percent = con.rect.width * 100 // parent_width_px
                expected_width_px = parent_width_px * container_layout.percent // 100
                logger.debug(
                    f"Expected width: {expected_width_px}px, actual width: {con.rect.width}px"
                )
            else:
                actual_percent = (
                    (con.rect.height + con.deco_rect.height) * 100 // parent_height_px
                )
                expected_height_px = parent_height_px * container_layout.percent // 100
                logger.debug(
                    f"Expected height: {expected_height_px}px, actual height: {con.rect.height}px"
                )

            if (
                container_layout.percent - RESIZE_TOLERANCE_PERCENT
                <= actual_percent
                <= container_layout.percent + RESIZE_TOLERANCE_PERCENT
            ):
                logger.debug(
                    f"Container layout for {get_con_description(con)} matches the expected percentage: "
                    + f"{actual_percent}% == {container_layout.percent}%"
                )
                result = True
            else:
                logger.error(
                    f"Container layout for {get_con_description(con)} does not match the expected "
                    + f"percentage: {actual_percent}% != {container_layout.percent}%"
                )
                result = False

        if isinstance(container_layout, ContainerConfig):
            # Get the container dimensions
            con_width_px, con_height_px = _get_container_size_excluding_gaps(con)
            if con.layout in ["splith", "splitv"]:
                con_layout = con.layout
            else:
                con_layout = "other"

            # Check all children, even if some do not match.
            for child in container_layout.children:
                if not check_container_layout(
                    child, con_width_px, con_height_px, con_layout
                ):
                    result = False

        return result

    tree = connection.get_tree()
    assert (
        workspace_layout._con_id is not None
    ), "The con_id of the workspace layout should have been set before calling this function."
    workspace_con = tree.find_by_id(workspace_layout._con_id)
    if not workspace_con:
        logger.error(
            f"Workspace with con_id {workspace_layout._con_id} not found in the tree."
        )
        return False

    if workspace_con.layout in ["splith", "splitv"]:
        layout = workspace_con.layout
    else:
        layout = "other"
    width_px, height_px = _get_container_size_excluding_gaps(workspace_con)

    # Always check all containers in the workspace to show an exhaustive error message.
    result = True
    for child in workspace_layout.children:
        if not check_container_layout(child, width_px, height_px, layout):
            result = False
    return result


def _find_con(
    tree: Con, container: WorkspaceLayout | ContainerConfig | ApplicationLaunchConfig
) -> Con:
    con_id = container._con_id
    assert con_id is not None, (
        f"Application {container} has no con_id set. "
        + "This is required for the layout creation."
    )
    result = tree.find_by_id(con_id)
    if result is None:
        raise RuntimeError(f"Container for application with con ID {con_id} not found")
    else:
        return result


def _get_container_size_excluding_gaps(con: Con) -> tuple[int, int]:
    # For windows, we use the rect and deco rect.
    # rect does not include the decoration, i.e. title bar.
    # For containers, we sum up the children where necessary to exclude
    # gaps between windows in the result.
    # We assume that the decoration is always at the top.

    if con.layout == "splith":
        width = sum(_get_container_size_excluding_gaps(child)[0] for child in con.nodes)
    else:
        assert con.rect.width == con.deco_rect.width or con.deco_rect.width == 0
        width = con.rect.width

    if con.layout == "splitv":
        height = sum(
            _get_container_size_excluding_gaps(child)[1] for child in con.nodes
        )
    else:
        height = con.rect.height + con.deco_rect.height

    return width, height
