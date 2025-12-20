import numpy as np

# def surface_lines(axis, surface_div, length=1.0):
#     """
#     axis: 'x', 'y', 'z'
#     surface_div: (a, b)  # 면 분할 수
#     length: 선 길이
#     """
#     a, b = surface_div
#     coords = np.linspace(-1, 1, a + 1)
#     coords2 = np.linspace(-1, 1, b + 1)

#     lines = []

#     for sign in (-1, 1):  # -면, +면
#         for u in coords:
#             for v in coords2:
#                 if axis == 'x':
#                     start = np.array([sign, u, v])
#                     end   = start + np.array([sign * length, 0, 0])

#                 elif axis == 'y':
#                     start = np.array([u, sign, v])
#                     end   = start + np.array([0, sign * length, 0])

#                 elif axis == 'z':
#                     start = np.array([u, v, sign])
#                     end   = start + np.array([0, 0, sign * length])

#                 lines.append((start, end))

#     return lines

def rotate_axis(points, axis, angle, degrees=True):
    if degrees:
        angle = np.deg2rad(angle)

    c, s = np.cos(angle), np.sin(angle)

    if axis == 'x':
        R = np.array([
            [1, 0, 0],
            [0, c, -s],
            [0, s,  c]
        ], dtype=np.float32)

    elif axis == 'y':
        R = np.array([
            [ c, 0, s],
            [ 0, 1, 0],
            [-s, 0, c]
        ], dtype=np.float32)

    elif axis == 'z':
        R = np.array([
            [c, -s, 0],
            [s,  c, 0],
            [0,  0, 1]
        ], dtype=np.float32)

    else:
        raise ValueError("axis must be 'x', 'y', or 'z'")

    return points @ R.T


def surface_lines_from_cube(cube_vertices, axis, surface_div):
    """
    cube_vertices: (N,3) ndarray
    axis: 'x', 'y', 'z'
    surface_div: (a, b)
    return: list of (start, end)
    """

    mins = cube_vertices.min(axis=0)
    maxs = cube_vertices.max(axis=0)

    a, b = surface_div
    lines = []

    if axis == 'x':
        # Y,Z 면 분할
        y_all = np.linspace(mins[1], maxs[1], a + 1)
        z_all = np.linspace(mins[2], maxs[2], b + 1)

        y_divs = y_all[1:-1]   # 등분선
        z_divs = z_all[1:-1]

        for y in y_divs:
            for z in z_divs:
                start = np.array([mins[0], y, z])
                end   = np.array([maxs[0], y, z])
                lines.append((start, end))

    elif axis == 'y':
        x_all = np.linspace(mins[0], maxs[0], a + 1)
        z_all = np.linspace(mins[2], maxs[2], b + 1)

        x_divs = x_all[1:-1]
        z_divs = z_all[1:-1]

        for x in x_divs:
            for z in z_divs:
                start = np.array([x, mins[1], z])
                end   = np.array([x, maxs[1], z])
                lines.append((start, end))

    elif axis == 'z':
        x_all = np.linspace(mins[0], maxs[0], a + 1)
        y_all = np.linspace(mins[1], maxs[1], b + 1)

        x_divs = x_all[1:-1]
        y_divs = y_all[1:-1]

        for x in x_divs:
            for y in y_divs:
                start = np.array([x, y, mins[2]])
                end   = np.array([x, y, maxs[2]])
                lines.append((start, end))

    else:
        raise ValueError("axis must be 'x', 'y', or 'z'")

    return lines

def cube_grids(cube, X_SURFACE=(2,2), Y_SURFACE=(2,2), Z_SURFACE=(2,2)):
    lines = {}

    if X_SURFACE != (0,0):
        lines['x'] = np.array(surface_lines_from_cube(cube, 'x', X_SURFACE), dtype=np.float32)
    else:
        lines['x'] = []

    if Y_SURFACE != (0,0):
        lines['y'] = np.array(surface_lines_from_cube(cube, 'y', Y_SURFACE), dtype=np.float32)
    else:
        lines['y'] = []

    if Z_SURFACE != (0,0):
        lines['z'] = np.array(surface_lines_from_cube(cube, 'z', Z_SURFACE), dtype=np.float32)
    else:
        lines['z'] = []

    return {
        'cube': cube,
        'lines': lines
    }

def lines_to_edge_list(lines):
    """
    [(start, end), ...] → [start, end, start, end, ...]
    """
    edges = []
    for start, end in lines:
        edges.append(start)
        edges.append(end)
    return edges
