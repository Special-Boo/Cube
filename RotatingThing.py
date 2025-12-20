import numpy as np
from copy import deepcopy
import myUtils_openGL

import ctypes, sys, math

from PySide6.QtCore import QTime, QPoint, Signal, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMenu
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QMouseEvent, QAction
from OpenGL.GL import *
from OpenGL.GLU import *
import keyboard

def subdivide_edge(a, b, steps=20):
    """
    a, b: numpy array shape (3,)
    steps: number of subdivisions
    """
    result = []
    for i in range(steps):
        t1 = i / steps
        t2 = (i + 1) / steps
        p1 = a * (1 - t1) + b * t1
        p2 = a * (1 - t2) + b * t2
        result.append((p1, p2))
    return result

def build_subdivided_cube(edges, steps=20):
    subdivided = []
    for i in range(0, len(edges), 2):
        a = np.array(edges[i], dtype=np.float32)
        b = np.array(edges[i+1], dtype=np.float32)
        subdivided.extend(subdivide_edge(a, b, steps))
    return subdivided

ORIG_CUBE = np.array([
            (-1, -1, -1), (1, -1, -1),
            (1, -1, -1), (1,  1, -1),
            (1,  1, -1), (-1, 1, -1),
            (-1, 1, -1), (-1,-1,-1),

            (-1,-1, 1), ( 1,-1, 1),
            ( 1,-1, 1), ( 1, 1, 1),
            ( 1, 1, 1), (-1,1, 1),
            (-1,1, 1), (-1,-1,1),

            (-1,-1,-1), (-1,-1,1),
            ( 1,-1,-1), ( 1,-1,1),
            ( 1, 1,-1), ( 1, 1,1),
            (-1, 1,-1), (-1, 1,1),
        ], dtype=np.float32)
ORIG_CUBE*= 2


# MID_FLOOR = np.array([
#     (-1, 0, -1), ( 1, 0, -1),
#     ( 1, 0, -1), ( 1, 0,  1),
#     ( 1, 0,  1), (-1, 0,  1),
#     (-1, 0,  1), (-1, 0, -1),
# ], dtype=np.float32)

# ORIG_CUBE = np.concat([ORIG_CUBE, MID_FLOOR])
class CubeOverlay(QOpenGLWidget):
    exit_signal = Signal()
    toggle_onoff = Signal()

    def __init__(self):
        super().__init__()
        self.start_time = QTime.currentTime()

        # ===== 투명 오버레이 창 =====
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.dragging = False
        self.drag_offset = QPoint()

        # 클릭스루 해제 (기본은 막아둔다)
        self.disable_click_through()

        # 회전
        self.rotate_flag = 1
        self.angle = 0
        self.cube_vertices = deepcopy(ORIG_CUBE)

        # 박스 비율 조정 X Y Z (Z는 카메라와 사물간의 거리 방향 [distnace])
        self.scale = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.cube_vertices = self.cube_vertices * self.scale
        self.edges = build_subdivided_cube(self.cube_vertices, steps=20)

        # fov 비율 조정 - FOV rate는 작을수록 넓은 시야를 가짐.
        self.fov_scale = 2
        self.view_zoom = 1  # 화면 확대 배율 (1.0 = 기본)

        # self.scale = np.array([1.5, 1.0, 1.5], dtype=np.float32)
        # self.cube_vertices = self.cube_vertices * self.scale
        self.sin_table_size = 1024
        self.sin_table = [math.sin(2 * math.pi * (i / self.sin_table_size))
                          for i in range(self.sin_table_size)]

        self.timer = QTimer()

        # 만약 박스가 회전하기를 원한다면 주석 풀기
        # self.timer.timeout.connect(self.rotate_cube_time)

        self.timer.start(8)

        self.c1, self.c2, self.c3, self.a = 0.2, 0.6, 1.0, 1.0   # 0.3 = 30% 불투명
        self.c_mode = "b"

        self.resize(1000, 786)
        keyboard.on_press_key("num 8", lambda _: self.rotate_cube('x', 10))
        keyboard.on_press_key("num 2", lambda _: self.rotate_cube('x', -10))
        keyboard.on_press_key("num 4", lambda _: self.rotate_cube('y', 10))
        keyboard.on_press_key("num 6", lambda _: self.rotate_cube('y', -10))
        keyboard.on_press_key("num 5", lambda _: self.reset_cube())

        keyboard.on_press_key("shift", lambda _: self.disable_click_through())
        keyboard.on_release_key("shift", lambda _: self.enable_click_through())
        keyboard.on_press_key("num 0", lambda _: self.toggle_active())
        # keyboard.on_press_key("num 1", lambda _: self.toggle_ratio())
        # keyboard.on_press_key("num 3", lambda _: self.toggle_color())
        self.toggle_onoff.connect(self.toggle_active_main)

        self.active = True
        
        self.show()

    def reset_cube(self):
        self.cube_vertices = deepcopy(ORIG_CUBE)
        self.edges = build_subdivided_cube(self.cube_vertices, steps=20)
        self.update()

    def rotate_cube(self,XYZ,angle):
        self.cube_vertices = myUtils_openGL.rotate_axis(self.cube_vertices,XYZ,angle,degrees = True)
        self.edges = build_subdivided_cube(self.cube_vertices, steps=20)
        self.update()


    def toggle_color(self):
        if self.c_mode == "w":
            self.c1,self.c2,self.c3,self.a = 0.2, 0.6, 1.0 ,1.0
            self.c_mode = "b"
        elif self.c_mode == 'b':
            self.c1,self.c2,self.c3,self.a = 1.0, 1.0, 1.0, 0.7
            self.c_mode = "w"


    # def toggle_ratio(self):
    #     self.cube_vertices = deepcopy(ORIG_CUBE)
    #     if self.scale[0] == 1.5:
    #         self.scale = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    #     elif self.scale[0] == 1.0:
    #         self.scale = np.array([1.5, 1.0, 1.5], dtype=np.float32)
    #     self.cube_vertices = self.cube_vertices * self.scale


    def show_context_menu(self, pos):
        menu = QMenu()

        close_action = QAction("Close", self)
        close_action.triggered.connect(QApplication.quit)
        menu.addAction(close_action)

        # 화면 좌표 위치에서 팝업
        menu.exec(pos)

    def close_app(self):
        self.tray.hide()
        QApplication.quit()

    def toggle_active_main(self):
        if self.timer.isActive():
            self.a = 0
            self.update()
            self.timer.stop()
        elif not self.timer.isActive():
            self.a = 0.7
            if self.c_mode == 'b':
                self.a = 1.0
            self.timer.start()
            self.update()

    def toggle_active(self):
        self.toggle_onoff.emit()

    def rotate_cube_time(self):
        self.angle += 0.25
        # if self.angle >= 1\
        # or self.angle <= -1:
        #     self.rotate_flag *= -1
        self.update()

    # def rotate_cube_offset(self,adjust_offset):
    #     self.angle += adjust_offset
    #     self.update()
    # ------------------------------
    # 클릭 스루 ON
    # ------------------------------
    def enable_click_through(self):
        hwnd = self.winId()
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        WS_EX_TRANSPARENT = 0x20

        ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED | WS_EX_TRANSPARENT
        )

    # ------------------------------
    # 클릭 스루 OFF (드래그 가능)
    # ------------------------------
    def disable_click_through(self):
        hwnd = self.winId()
        GWL_EXSTYLE = -20
        ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        # transparent 비트 제거
        ctypes.windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE, ex & ~0x20
        )

    # ------------------------------
    # 오른클릭 -> 드래그 이동
    # ------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        # Ctrl + 우클릭 → 드래그 시작
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            self.dragging = True
            self.drag_offset = event.globalPosition().toPoint() - self.pos()

            # 드래그 시작하는 순간 클릭스루 비활성화
            self.disable_click_through()

        if event.button() == Qt.RightButton and (event.modifiers() & Qt.ShiftModifier):
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_offset
            self.move(new_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.enable_click_through()  # 다시 클릭스루 켬

    # ------------------------------
    # OpenGL 초기화
    # ------------------------------
    def initializeGL(self):
        glClearColor(0, 0, 0, 0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # ------------------------------
    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        if h == 0:
            h = 1

        aspect = w / h

        if aspect >= 1.0:
            # 가로가 더 긴 화면 → X 범위 확장
            glOrtho(-aspect, aspect, -1, 1, -10, 10)
        else:
            # 세로가 더 긴 화면 → Y 범위 확장
            glOrtho(-1, 1, -1 / aspect, 1 / aspect, -10, 10)

        glMatrixMode(GL_MODELVIEW)

    # def resizeGL(self, w, h):
    #     glViewport(0, 0, w, h)
    #     glMatrixMode(GL_PROJECTION)
    #     glLoadIdentity()
    #     gluPerspective(45, w / h, 0.1, 50)
    #     glMatrixMode(GL_MODELVIEW)

    def stereographic(self, x, y, z):
        FOV = self.fov_scale  # ← 숫자만 바꾸면 FOV 변함

        L = math.sqrt(x*x + y*y + z*z)
        if L < 1e-6:
            return 0, 0

        x /= L; y /= L; z /= L

        denom = 1.0 - z
        if abs(denom) < 1e-6:
            denom = 1e-6

        u = x / denom
        v = y / denom

        return u * FOV, v * FOV


    # ------------------------------
    # ------------------------------
    # stereographic 카메라 버전
    # ------------------------------
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        if not self.active:
            return  # 렌더링 완전 차단

        # 회전 각도 계산 (degree → radian)
        elapsed = self.start_time.msecsTo(QTime.currentTime())
        idx = (elapsed // 2) % self.sin_table_size
        x_angle_deg = self.sin_table[idx] * 1.0   # x축 살짝 흔들기 (10도 정도)
        y_angle_deg = self.angle                   # 기존 self.angle 유지

        ax = math.radians(x_angle_deg)
        ay = math.radians(y_angle_deg)

        cosx, sinx = math.cos(ax), math.sin(ax)
        cosy, siny = math.cos(ay), math.sin(ay)

        glColor4f(self.c1, self.c2, self.c3, self.a)
        glLineWidth(1)

        glBegin(GL_LINES)
        for p1, p2 in self.edges:
            # --- 1) 회전 ---
            x1 = cosy * p1[0] + siny * p1[2]
            z1 = -siny * p1[0] + cosy * p1[2]
            y1 = cosx * p1[1] - sinx * z1
            z1 = sinx * p1[1] + cosx * z1
            u1, v1 = self.stereographic(x1, y1, z1 - 2)
            # 큐브를 멀리 보내고 싶으면 z축을 건들기 Z - 4, z - 6 등등


            x2 = cosy * p2[0] + siny * p2[2]
            z2 = -siny * p2[0] + cosy * p2[2]
            y2 = cosx * p2[1] - sinx * z2
            z2 = sinx * p2[1] + cosx * z2
            u2, v2 = self.stereographic(x2, y2, z2 - 2)

            u1 *= self.view_zoom
            v1 *= self.view_zoom
            u2 *= self.view_zoom
            v2 *= self.view_zoom

            glVertex3f(u1, v1, 0)
            glVertex3f(u2, v2, 0)
        glEnd()





# ------------------------------
# 실행부
# ------------------------------
app = QApplication(sys.argv)
win = CubeOverlay()
sys.exit(app.exec())
