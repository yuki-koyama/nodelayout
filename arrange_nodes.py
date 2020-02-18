import bpy
import sys
import math
import datetime


def _get_from_socket_index(node: bpy.types.Node, node_socket: bpy.types.NodeSocket) -> int:
    for i, socket in enumerate(node.outputs):
        if socket == node_socket:
            return i
    assert False


def _get_to_socket_index(node: bpy.types.Node, node_socket: bpy.types.NodeSocket) -> int:
    for i, socket in enumerate(node.inputs):
        if socket == node_socket:
            return i
    assert False


# Note: "dimensions" and "height" may not be correct depending on the situation
def _get_height(node: bpy.types.Node) -> float:
    epsilon = 1e-05

    if node.dimensions.y > epsilon:
        # Note: node.dimensions.y seems to store twice the value of node.height
        return node.dimensions.y / 2.0
    elif math.fabs(node.height - 100.0) > epsilon:
        return node.height
    else:
        return 200.0


def _arrange_nodes_internal_routine(
        node_tree: bpy.types.NodeTree,
        max_num_iters: int,
        target_space: float,
        fix_horizontal_location: bool,
        fix_vertical_location: bool,
        fix_overlaps: bool,
        verbose: bool,
        is_second_stage: bool,
) -> int:

    epsilon = 1e-05
    target_space = 2.0 * target_space if not is_second_stage else target_space
    k_horizontal_distance = 0.9 if not is_second_stage else 0.5
    k_vertical_distance = 0.5 if not is_second_stage else 0.05

    # Gauss-Seidel-style iterations
    previous_squared_deltas_sum = sys.float_info.max
    iter_count = 0
    for iter_count in range(max_num_iters):
        squared_deltas_sum = 0.0

        if fix_horizontal_location:
            for link in node_tree.links:
                k_horizontal_distance = 0.9 if not is_second_stage else 0.5
                threshold_factor = 2.0

                x_from = link.from_node.location[0]
                x_to = link.to_node.location[0]
                w_from = link.from_node.width
                signed_space = x_to - x_from - w_from
                C = signed_space - target_space
                grad_C_x_from = -1.0
                grad_C_x_to = 1.0

                # Skip if the distance is sufficiently large
                if C >= target_space * threshold_factor:
                    continue

                lagrange = C / (grad_C_x_from * grad_C_x_from + grad_C_x_to * grad_C_x_to)
                delta_x_from = -lagrange * grad_C_x_from
                delta_x_to = -lagrange * grad_C_x_to

                link.from_node.location[0] += k_horizontal_distance * delta_x_from
                link.to_node.location[0] += k_horizontal_distance * delta_x_to

                squared_deltas_sum += k_horizontal_distance * k_horizontal_distance * (delta_x_from * delta_x_from +
                                                                                       delta_x_to * delta_x_to)

        if fix_vertical_location:
            socket_offset = 20.0

            for link in node_tree.links:
                from_socket_index = _get_from_socket_index(link.from_node, link.from_socket)
                to_socket_index = _get_to_socket_index(link.to_node, link.to_socket)
                y_from = link.from_node.location[1] - socket_offset * from_socket_index
                y_to = link.to_node.location[1] - socket_offset * to_socket_index
                C = y_from - y_to
                grad_C_y_from = 1.0
                grad_C_y_to = -1.0
                lagrange = C / (grad_C_y_from * grad_C_y_from + grad_C_y_to * grad_C_y_to)
                delta_y_from = -lagrange * grad_C_y_from
                delta_y_to = -lagrange * grad_C_y_to

                link.from_node.location[1] += k_vertical_distance * delta_y_from
                link.to_node.location[1] += k_vertical_distance * delta_y_to

                squared_deltas_sum += k_vertical_distance * k_vertical_distance * (delta_y_from * delta_y_from +
                                                                                   delta_y_to * delta_y_to)

        if fix_overlaps and is_second_stage:
            k = 0.9
            margin = 0.5 * target_space

            # Examine all node pairs
            for node_1 in node_tree.nodes:
                for node_2 in node_tree.nodes:
                    if node_1 == node_2:
                        continue

                    x_1 = node_1.location[0]
                    x_2 = node_2.location[0]
                    w_1 = node_1.width
                    w_2 = node_2.width
                    cx_1 = x_1 + 0.5 * w_1
                    cx_2 = x_2 + 0.5 * w_2
                    rx_1 = 0.5 * w_1 + margin
                    rx_2 = 0.5 * w_2 + margin

                    y_1 = node_1.location[1]
                    y_2 = node_2.location[1]
                    h_1 = _get_height(node_1)
                    h_2 = _get_height(node_2)
                    cy_1 = y_1 - 0.5 * h_1
                    cy_2 = y_2 - 0.5 * h_2
                    ry_1 = 0.5 * h_1 + margin
                    ry_2 = 0.5 * h_2 + margin

                    C_x = math.fabs(cx_1 - cx_2) - (rx_1 + rx_2)
                    C_y = math.fabs(cy_1 - cy_2) - (ry_1 + ry_2)

                    # If no collision, just skip
                    if C_x >= 0.0 or C_y >= 0.0:
                        continue

                    # Solve collision for the "easier" direction
                    if C_x > C_y:
                        grad_C_x_1 = 1.0 if cx_1 - cx_2 >= 0.0 else -1.0
                        grad_C_x_2 = -1.0 if cx_1 - cx_2 >= 0.0 else 1.0
                        lagrange = C_x / (grad_C_x_1 * grad_C_x_1 + grad_C_x_2 * grad_C_x_2)
                        delta_x_1 = -lagrange * grad_C_x_1
                        delta_x_2 = -lagrange * grad_C_x_2

                        node_1.location[0] += k * delta_x_1
                        node_2.location[0] += k * delta_x_2

                        squared_deltas_sum += k * k * (delta_x_1 * delta_x_1 + delta_x_2 * delta_x_2)
                    else:
                        grad_C_y_1 = 1.0 if cy_1 - cy_2 >= 0.0 else -1.0
                        grad_C_y_2 = -1.0 if cy_1 - cy_2 >= 0.0 else 1.0
                        lagrange = C_y / (grad_C_y_1 * grad_C_y_1 + grad_C_y_2 * grad_C_y_2)
                        delta_y_1 = -lagrange * grad_C_y_1
                        delta_y_2 = -lagrange * grad_C_y_2

                        node_1.location[1] += k * delta_y_1
                        node_2.location[1] += k * delta_y_2

                        squared_deltas_sum += k * k * (delta_y_1 * delta_y_1 + delta_y_2 * delta_y_2)

        if verbose:
            print("Iteration #" + str(iter_count) + ": " + str(previous_squared_deltas_sum - squared_deltas_sum))

        # Check the termination conditiion
        if math.fabs(previous_squared_deltas_sum - squared_deltas_sum) < epsilon:
            break

        previous_squared_deltas_sum = squared_deltas_sum

    return iter_count


def arrange_nodes(node_tree: bpy.types.NodeTree,
                  use_current_layout_as_initial_guess: bool = False,
                  max_num_iters: int = 1000,
                  target_space: float = 50.0,
                  fix_horizontal_location: bool = True,
                  fix_vertical_location: bool = True,
                  fix_overlaps: bool = True,
                  verbose: bool = False) -> None:

    if not use_current_layout_as_initial_guess:
        for node in node_tree.nodes:
            node.location = (0.0, 0.0)

    if verbose:
        print("-----------------")
        print("Target nodes:")
        for node in node_tree.nodes:
            print("- " + node.name)

    time_0 = datetime.datetime.now()

    # First pass
    iter_count_1st = _arrange_nodes_internal_routine(node_tree,
                                                     max_num_iters,
                                                     target_space,
                                                     fix_horizontal_location,
                                                     fix_vertical_location,
                                                     fix_overlaps,
                                                     verbose=verbose,
                                                     is_second_stage=False)

    time_1 = datetime.datetime.now()

    # Second pass
    iter_count_2nd = _arrange_nodes_internal_routine(node_tree,
                                                     max_num_iters,
                                                     target_space,
                                                     fix_horizontal_location,
                                                     fix_vertical_location,
                                                     fix_overlaps,
                                                     verbose=verbose,
                                                     is_second_stage=True)

    time_2 = datetime.datetime.now()

    if verbose:
        print("Elapsed time (1st pass): {} (#iters = {})".format(time_1 - time_0, iter_count_1st))
        print("Elapsed time (2nd pass): {} (#iters = {})".format(time_2 - time_1, iter_count_2nd))
