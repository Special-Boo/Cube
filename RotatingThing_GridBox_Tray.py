import numpy as np
from copy import deepcopy
import myUtils_GL

import ctypes, sys, math

from PySide6.QtCore import QTime, QPoint, Signal, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QMouseEvent, QAction, QColor, QIcon
from OpenGL.GL import *
from OpenGL.GLU import *

def color_continuous_lines(data,QColor):
    for continuousline in data:
        for line in continuousline:
            line.setColor(QColor)

def color_lines(lines,QColor):
    for line in lines:
        line.setColor(QColor)

def set_color(MYGL_Line,QColor):
    MYGL_Line.setColor(QColor)

def scale_line(line,scale):
    line.p[0].scale_around((0,0,0),scale)
    line.p[1].scale_around((0,0,0),scale)

CUBE_LINES = myUtils_GL.make_cube_edges(-1,1)
DIV_LINES_X = myUtils_GL.cube_division_lines('x',4,-1,1)
DIV_LINES_Y = myUtils_GL.cube_division_lines('y',4,-1,1)
DIV_LINES_Z = myUtils_GL.cube_division_lines('z',4,-1,1)
# ADD = ORIG_CUBE.tolist()

# X_1 = deepcopy(ORIG_CUBE + np.array([2, 0, 0], dtype=np.float32)).tolist()
# X_2 = deepcopy(ORIG_CUBE + np.array([-2, 0, 0], dtype=np.float32)).tolist()
# Y_1 = deepcopy(ORIG_CUBE + np.array([0, 2, 0], dtype=np.float32)).tolist()
# Y_2 = deepcopy(ORIG_CUBE + np.array([0, -2, 0], dtype=np.float32)).tolist()
# Z_1 = deepcopy(ORIG_CUBE + np.array([0, 0, 2], dtype=np.float32)).tolist()
# Z_2 = deepcopy(ORIG_CUBE + np.array([0, 0, -2], dtype=np.float32)).tolist()
# ADD = np.array(X_1 + X_2 + Y_1 + Y_2 + Z_1 + Z_2 + deepcopy(ORIG_CUBE.tolist()))
# TOTAL = ADD*2
# ORIG_CUBE = TOTAL


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

        self._click_through = True
        self.dragging = False
        self.drag_offset = QPoint()

        # 클릭스루 해제 (기본은 막아둔다)
        self.disable_click_through()
        # 회전
        self.rotate_flag = 1
        self.angle = 0
        self.cube = deepcopy(CUBE_LINES)

        # 박스 비율 조정 X Y Z (Z는 카메라와 사물간의 거리 방향 [distnace])
        self.scale = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.AA = myUtils_GL.line_divs(self.cube, steps=20)
        self.BB = myUtils_GL.line_divs(DIV_LINES_X,steps = 20)
        self.CC = myUtils_GL.line_divs(DIV_LINES_Y,steps = 20)
        self.DD = myUtils_GL.line_divs(DIV_LINES_Z,steps = 20)

        self.color_turn_on()
        self.edges = self.AA + self.BB + self.CC + self.DD
        # self.edges = self.AA

        for continuousline in self.edges:
            for line in continuousline:
                scale_line(line,self.scale)

        # fov 비율 조정 - FOV rate는 작을수록 넓은 시야를 가짐.
        self.fov_scale = 2.5
        self.view_zoom = 1  # 화면 확대 배율 (1.0 = 기본)

        # self.scale = np.array([1.5, 1.0, 1.5], dtype=np.float32)
        # self.cube = self.cube * self.scale
        self.sin_table_size = 1024
        self.sin_table = [math.sin(2 * math.pi * (i / self.sin_table_size))
                          for i in range(self.sin_table_size)]

        self.timer = QTimer()

        # 만약 박스가 회전하기를 원한다면 주석 풀기
        self.timer.timeout.connect(self.rotate_cube_time)

        self.timer.start(8)
        self.resize(600, 600)
        # keyboard.on_press_key("num 1", lambda _: self.toggle_ratio())
        # keyboard.on_press_key("num 3", lambda _: self.toggle_color())
        self.toggle_onoff.connect(self.toggle_active_main)

        self.active = True
        self.init_tray()
        self.show()

    def init_tray(self):
        # 트레이 지원 여부 확인(가끔 환경에 따라 꺼져있을 수 있음)
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("System tray not available")
            return

        # 아이콘은 반드시 필요(없으면 일부 환경에서 표시가 이상함)
        # 1) 파일 아이콘: QIcon("icon.ico")
        # 2) 기본 아이콘: style standard icon 사용도 가능(아래 주석 참고)
        tray_icon = QIcon("tray.ico")  # TODO: 너의 ico 경로로 바꾸기

        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.setToolTip("Cube Overlay")

        menu = QMenu()

        self.act_clickthrough = QAction("Click-through: ON", self)
        self.act_clickthrough.setCheckable(True)
        self.act_clickthrough.setChecked(True)
        self.act_clickthrough.triggered.connect(self.toggle_click_through_from_tray)
        menu.addAction(self.act_clickthrough)

        act_showhide = QAction("Show/Hide Overlay", self)
        act_showhide.triggered.connect(self.toggle_overlay_visible)
        menu.addAction(act_showhide)

        menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)

        # 트레이 아이콘 클릭(좌클릭) 동작도 원하면
        self.tray.activated.connect(self.on_tray_activated)

        self.tray.show()

    def on_tray_activated(self, reason):
        # 좌클릭으로 토글하고 싶으면 이런 식
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_click_through_from_tray()

    def toggle_overlay_visible(self):
        self.setVisible(not self.isVisible())

    def toggle_click_through_from_tray(self):
        self._click_through = not self._click_through

        if self._click_through:
            self.enable_click_through()
            self.act_clickthrough.setText("Click-through: ON")
            self.act_clickthrough.setChecked(True)
        else:
            self.disable_click_through()
            self.act_clickthrough.setText("Click-through: OFF")
            self.act_clickthrough.setChecked(False)

    def color_turn_off(self):
        color_continuous_lines(self.AA,QColor(0,0,0,0))
        color_continuous_lines(self.BB,QColor(0,0,0,0))
        color_continuous_lines(self.CC,QColor(0,0,0,0))
        color_continuous_lines(self.DD,QColor(0,0,0,0))
    
    def color_turn_on(self):
        color_continuous_lines(self.AA,QColor(int(255*0.2), int(255*0.6), int(255*1.0), int(255*1.0)))
        color_continuous_lines(self.BB,QColor(int(255*0.0), int(255*0.0), int(255*0.0), int(255*0.3)))
        color_continuous_lines(self.CC,QColor(int(255*0.0), int(255*0.0), int(255*0.0), int(255*0.3)))
        color_continuous_lines(self.DD,QColor(int(255*0.0), int(255*0.0), int(255*0.0), int(255*0.3)))

    def reset_cube(self):
        self.cube = deepcopy(CUBE_LINES)

        # 박스 비율 조정 X Y Z (Z는 카메라와 사물간의 거리 방향 [distnace])
        self.scale = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.AA = myUtils_GL.line_divs(self.cube, steps=20)
        self.BB = myUtils_GL.line_divs(DIV_LINES_X,steps = 20)
        self.CC = myUtils_GL.line_divs(DIV_LINES_Y,steps = 20)
        self.DD = myUtils_GL.line_divs(DIV_LINES_Z,steps = 20)

        self.color_turn_on()
        self.edges = self.AA + self.BB + self.CC + self.DD
        # self.edges = self.AA

        for continuousline in self.edges:
            for line in continuousline:
                scale_line(line,self.scale)
        self.update()

    def rotate_cube(self,XYZ,angle):
        for continuousline in self.edges:
            for line in continuousline:
                line.p[0].raw = myUtils_GL.rotate_axis(line.p[0].raw,XYZ,angle)
                line.p[1].raw = myUtils_GL.rotate_axis(line.p[1].raw,XYZ,angle)
        self.update()


    def toggle_color(self):
        if self.c_mode == "w":
            self.c1,self.c2,self.c3,self.a = 0.2, 0.6, 1.0 ,1.0
            self.c_mode = "b"
        elif self.c_mode == 'b':
            self.c1,self.c2,self.c3,self.a = 1.0, 1.0, 1.0, 0.7
            self.c_mode = "w"


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
            self.color_turn_off()
            self.update()
            self.timer.stop()
        elif not self.timer.isActive():
            self.color_turn_on()
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
        self.dragging = True
        self.drag_offset = event.globalPosition().toPoint() - self.pos()

        # 드래그 시작하는 순간 클릭스루 비활성화
        self.disable_click_through()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_offset
            self.move(new_pos)

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
            # 세로가 더 긴 화면 → Y 범위 확장66622288844444444444466666666
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

        glLineWidth(1)

        glBegin(GL_LINES)
        for continuousline in self.edges:
            for line in continuousline:
                # --- 1) 회전 ---
                p1, p2 = line.p
                c1,c2,c3,a = line.getColor()
                glColor4f(c1/255, c2/255, c3/255, a/255)
                p1 = p1.raw
                p2 = p2.raw

                x1 = cosy * p1[0] + siny * p1[2]
                z1 = -siny * p1[0] + cosy * p1[2]
                y1 = cosx * p1[1] - sinx * z1
                z1 = sinx * p1[1] + cosx * z1
                u1, v1 = self.stereographic(x1, y1, z1 - 2.7)
                # u1, v1 = self.stereographic(p1[0], p1[1], p1[2] - 1)
                # 큐브를 멀리 보내고 싶으면 z축을 건들기 Z - 4, z - 6 등등


                x2 = cosy * p2[0] + siny * p2[2]
                z2 = -siny * p2[0] + cosy * p2[2]
                y2 = cosx * p2[1] - sinx * z2
                z2 = sinx * p2[1] + cosx * z2
                u2, v2 = self.stereographic(x2, y2, z2 - 2.7)
                # u2, v2 = self.stereographic(p2[0], p2[1], p2[2] - 1)

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
