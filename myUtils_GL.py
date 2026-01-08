import numpy as np
from PySide6.QtGui import QColor


class InfluenceTool:
    def __init__(self, radius, falloff="linear"):
        self.radius = radius
        self.falloff = falloff

    def apply(self, points, center_point, delta):
        for p in points:
            d = np.linalg.norm(p.pos - center_point.pos)
            if d < self.radius:
                w = self._weight(d)
                p.move(delta * w)

    def _weight(self, d):
        if self.falloff == "linear":
            return 1.0 - d / self.radius
        elif self.falloff == "smooth":
            t = d / self.radius
            return 1.0 - (3*t*t - 2*t*t*t)
        else:
            return 1.0
        

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


class MYGL_Point:
    def __init__(self, data):
        self.pos = np.array([data[0],data[1],data[2]], dtype=np.float32)

    def scale_around(self, center=(0,0,0), scale=(1,1,1)):
        if type(center) != np.ndarray:
            center = np.array(center,dtype=np.float32)

        assert np.max(np.abs(center - scale))*np.sqrt(3) < 100

        self.pos = (self.pos - center) * scale + center

    @property
    def raw(self):
        return self.pos

    @raw.setter
    def raw(self, value):
        arr = np.asarray(value, dtype=np.float32)
        assert arr.shape == (3,)
        self.pos[:] = arr

class MYGL_Line:
    def __init__(self,data,QColor=QColor(0,0,0,255)):
        ps = []
        for p in data:
            ps.append(MYGL_Point(p))
            
        self.p = ps
        self.color = QColor

    def setColor(self,QColor):
        self.color = QColor

    def getColor(self):
        return self.color.red(), self.color.green(), self.color.blue(), self.color.alpha()
    
class MYGL_ContinuousLine:
    def __init__(self,data:list):
        self.lines = data

    def __iter__(self):
        return iter(self.lines)
    

def rotate_axis(pos, axis, angle, center=(0.0, 0.0, 0.0)):
    """
    pos   : np.ndarray shape (3,)
    axis  : np.ndarray shape (3,)  (회전축)
    angle : float (radians)
    center: 기준점 (default = origin)
    """
    angle = np.deg2rad(angle)
    
    pos = np.asarray(pos, dtype=np.float32)
    center = np.asarray(center, dtype=np.float32)
    axis = np.asarray(axis, dtype=np.float32)

    # 축 정규화
    axis = axis / np.linalg.norm(axis)

    # 기준점으로 이동
    v = pos - center

    cos_t = np.cos(angle)
    sin_t = np.sin(angle)

    # Rodrigues' rotation formula
    v_rot = (
        v * cos_t +
        np.cross(axis, v) * sin_t +
        axis * np.dot(axis, v) * (1 - cos_t)
    )

    return v_rot + center

def _subdivide_edge(line, steps=20):
    """
    a, b: numpy array shape (3,)
    steps: number of subdivisions
    """
    result = []
    a = line.p[0].raw
    b = line.p[1].raw

    for i in range(steps):
        t1 = i / steps
        t2 = (i + 1) / steps
        p1 = a * (1 - t1) + b * t1
        p2 = a * (1 - t2) + b * t2
        result.append(MYGL_Line([p1,p2]))
    return MYGL_ContinuousLine(result)

def line_divs(lines, steps=20):
    """
    edges: np.ndarray shape (N, 2, 3)
    return: np.ndarray shape (M, 2, 3)
    """
    line_divs = []

    for line in lines:
        line_divs.append(_subdivide_edge(line, steps))

    return line_divs

def make_cube_edges(min_v=-1.0, max_v=1.0, dtype=np.float32):
    v = min_v
    w = max_v

    lines = [
        # bottom face (z = v)
        MYGL_Line([(v, v, v), (w, v, v)]),
        MYGL_Line([(w, v, v), (w, w, v)]),
        MYGL_Line([(w, w, v), (v, w, v)]),
        MYGL_Line([(v, w, v), (v, v, v)]),

        # top face (z = w)
        MYGL_Line([(v, v, w), (w, v, w)]),
        MYGL_Line([(w, v, w), (w, w, w)]),
        MYGL_Line([(w, w, w), (v, w, w)]),
        MYGL_Line([(v, w, w), (v, v, w)]),

        # vertical edges
        MYGL_Line([(v, v, v), (v, v, w)]),
        MYGL_Line([(w, v, v), (w, v, w)]),
        MYGL_Line([(w, w, v), (w, w, w)]),
        MYGL_Line([(v, w, v), (v, w, w)]),
    ]

    return lines

def cube_division_lines(axis: str, n: int, min_v=-1.0, max_v=1.0):
    assert axis in ('x', 'y', 'z')
    assert n >= 2

    lines = []
    steps = np.linspace(min_v, max_v, n + 1)[1:-1]

    for v in steps:
        if axis == 'x':
            pts = [
                (v, min_v, min_v),
                (v, max_v, min_v),
                (v, max_v, max_v),
                (v, min_v, max_v),
            ]
        elif axis == 'y':
            pts = [
                (min_v, v, min_v),
                (max_v, v, min_v),
                (max_v, v, max_v),
                (min_v, v, max_v),
            ]
        else:  # z
            pts = [
                (min_v, min_v, v),
                (max_v, min_v, v),
                (max_v, max_v, v),
                (min_v, max_v, v),
            ]

        # 사각형 테두리 선
        for i in range(4):
            lines.append(MYGL_Line([pts[i], pts[(i + 1) % 4]]))

    return lines



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
