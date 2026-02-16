import sys
import os
import subprocess
import functools
import webbrowser
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox,
                             QComboBox, QDialog, QDialogButtonBox,
                             QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QProgressBar,
                             QPushButton, QSizePolicy, QSpacerItem, QSpinBox, QTableWidget,
                             QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QMainWindow, QMenu)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QCloseEvent, QAction, QMouseEvent, QKeyEvent
from PyQt6.QtCore import Qt, QSettings, QUrl, QTimer, pyqtSignal, QSize, QEvent, QPointF

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript, QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import QSizeF


from app.resources import resource_path
from app.constants import USERPATH, VERSION, BUILDNUMBER
from app.ui_widgets import QToggle
from PyQt6.QtWidgets import QSlider, QGridLayout


class OverlayPreviewWidget(QWidget):
    """가로/세로 화면 박스를 그리는 위젯 - 실제 오버레이처럼 겹쳐서 표시"""
    def __init__(self, portrait_width: int, portrait_height: int, alignment: str = "center", parent=None):
        super().__init__(parent)
        self.portrait_width = portrait_width
        self.portrait_height = portrait_height
        self.alignment = alignment
        
        # 실제 크기 표시 (scale = 1.0)
        self.scale = 1.0
        # 오프셋 없이 0,0 부터 시작
        offset_x, offset_y = 0, 0
        
        # 9-Grid Alignment Parsing
        # alignment string format: "top-left", "center-center", "bottom-right", etc.
        # Fallback for legacy "left", "center", "right" -> "top-left", "top-center", "top-right"
        
        self.h_align = "center"
        self.v_align = "top"
        
        if "-" in self.alignment:
            parts = self.alignment.split("-")
            if len(parts) >= 2:
                self.v_align = parts[0] # top, center, bottom
                self.h_align = parts[1] # left, center, right
        else:
            # Legacy Single Value
            if self.alignment in ["left", "center", "right"]:
                self.v_align = "top" 
                self.h_align = self.alignment
            elif self.alignment == "top": self.v_align="top"; self.h_align="center"
            elif self.alignment == "bottom": self.v_align="bottom"; self.h_align="center"
        # 고정 크기 (설정창 내부용)
        self.setFixedSize(300, 560)  # 적절한 비율 유지를 위한 크기

        
    def sizeHint(self):
         return QSize(300, 560) 
    
    def update_portrait_size(self, width: int, height: int):
        self.portrait_width = width
        self.portrait_height = height
        self.update()  # 다시 그리기
    
    def update_alignment(self, alignment: str):
        self.alignment = alignment
        
        # Update internal h_align, v_align
        if "-" in self.alignment:
            parts = self.alignment.split("-")
            if len(parts) >= 2:
                self.v_align = parts[0]
                self.h_align = parts[1]
        else:
            if self.alignment in ["left", "center", "right"]:
                self.v_align = "top"
                self.h_align = self.alignment
            elif self.alignment == "top": self.v_align="top"; self.h_align="center"
            elif self.alignment == "bottom": self.v_align="bottom"; self.h_align="center"
        
        self.update()
    
    def update_portrait_size(self, width, height):
        self.portrait_width = width
        self.portrait_height = height
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPen, QBrush, QFont as QGuiFont
        
        # 1. 기본 치수 계산
        h_video_h = 720
        h_text_h = 162
        h_total_h = h_video_h + h_text_h  # 882
        
        include_text = getattr(self, 'include_text', True)
        h_content_h = h_total_h if include_text else h_video_h
        
        p_video_w = self.portrait_width
        p_video_h = self.portrait_height
        p_text_h = 162
        p_total_h = p_video_h + p_text_h
        
        # 전체 캔버스 높이 (둘 중 큰 값)
        max_h = max(h_total_h, p_total_h)
        
        # 2. 스케일 계산
        VIRTUAL_WIDTH = 1280
        VIRTUAL_HEIGHT = max_h # 전체 높이를 max_h로 맞춤
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        widget_w = self.width()
        widget_h = self.height()
        
        scale_x = widget_w / VIRTUAL_WIDTH
        scale_y = widget_h / VIRTUAL_HEIGHT
        scale = min(scale_x, scale_y)
        
        drawn_w = VIRTUAL_WIDTH * scale
        drawn_h = VIRTUAL_HEIGHT * scale
        offset_x = (widget_w - drawn_w) / 2
        offset_y = (widget_h - drawn_h) / 2
        
        painter.translate(offset_x, offset_y)
        painter.scale(scale, scale)
        
        # 3. 배경 그리기
        win_h = max_h
        
        # 전체 영역 (검은색)
        painter.fillRect(0, 0, 1280, win_h, QColor(20, 20, 20))
        painter.setPen(QPen(QColor(60, 60, 60), 2))
        painter.drawRect(0, 0, 1280, win_h)
        
        # 3. 가로 모드 영역 (빨간 점선) - 9분할 정렬 기준 (Clean Implementation)
        h_video_h = 720
        h_text_h = 162
        h_total_h = h_video_h + h_text_h  # 882
        
        include_text = getattr(self, 'include_text', True)
        h_content_h = h_total_h if include_text else h_video_h
        
        p_video_h = self.portrait_height
        p_text_h = 162
        p_total_h = p_video_h + p_text_h
        
        # 전체 캔버스 높이 (둘 중 큰 값)
        max_h = max(h_total_h, p_total_h)
        
        # 윈도우 높이 설정
        win_h = max_h 

        # Horizontal Align for Landscape (가로화면 Y 위치)
        if self.h_align == "left":
            h_x = 0
        elif self.h_align == "right":
            h_x = 0
        else:
            h_x = 0
        
        # Vertical Align for Landscape
        if self.v_align == "top":
            h_y = 0
        elif self.v_align == "bottom":
            h_y = win_h - h_total_h
        else:  # center
            if include_text:
                h_y = (win_h - h_total_h) // 2
            else:
                h_y = (win_h - h_video_h) // 2
        
        red_pen = QPen(QColor(255, 80, 80), 4)
        red_pen.setDashPattern([10, 10])
        painter.setPen(red_pen)
        painter.setBrush(QBrush(QColor(80, 0, 0, 80)))
        
        painter.drawRect(h_x, int(h_y), 1280, h_video_h)
        painter.drawRect(h_x, int(h_y) + h_video_h, 1280, h_text_h)
        
        # 5. 세로화면(Blue) 위치 계산 - 항상 Y=0 고정!
        # 세로화면(portrait)은 창 상단에 고정. v_align은 가로화면에만 적용됨.
        if self.h_align == "left":
            p_x = 0
        elif self.h_align == "right":
            p_x = 1280 - (getattr(self, 'portrait_width', 576))
        else: # center
            p_x = (1280 - (getattr(self, 'portrait_width', 576))) // 2
        
        # Portrait Y position is ALWAYS 0 (top of window)
        p_y = 0
        
        blue_pen = QPen(QColor(80, 80, 255), 4)
        blue_pen.setDashPattern([10, 10])
        painter.setPen(blue_pen)
        painter.setBrush(QBrush(QColor(0, 0, 80, 100)))
        
        painter.drawRect(int(p_x), int(p_y), getattr(self, 'portrait_width', 576), p_video_h)
        painter.drawRect(int(p_x), int(p_y) + p_video_h, getattr(self, 'portrait_width', 576), p_text_h)
        
        # 6. 텍스트 정보
        painter.setPen(QColor(255, 255, 255))
        font = QGuiFont("맑은 고딕", 80, QGuiFont.Weight.Bold)
        painter.setFont(font)
        
        info_text = f"전체: 1280x{win_h}"
        painter.drawText(20, win_h - 20, info_text)
        
        painter.end()


class OverlaySettingsDialog(QDialog):
    """설정 팝업 - 슬라이더와 치수 표"""
    settings_changed = pyqtSignal(int, int)  # portrait_width, portrait_height 변경 시그널
    align_changed = pyqtSignal(str) # 정렬 변경 시그널 추가
    include_text_changed = pyqtSignal(bool)  # 후원텍스트 포함 정렬 변경 시그널
    
    def __init__(self, portrait_width: int, portrait_height: int, main_window, parent=None):
        super().__init__(parent)
        self.portrait_width = portrait_width
        self.portrait_height = portrait_height
        self.original_width = portrait_width  # 원래 값 저장 (취소 시 복원용)
        self.original_height = portrait_height
        self.main_window = main_window
        self.preview_dialog = None
        self._closing = False
        
        self.setWindowTitle("영상 정렬/크기 설정")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))
        
        self.initUI()
        
    def update_alignment(self, alignment):
        self.alignment = alignment # Update internal alignment
        self.preview_widget.update_alignment(alignment)
        # 9-grid 버튼 상태 업데이트
        self.update_button_states(alignment) # 새로 추가된 메서드 호출
    
    def update_button_states(self, current_alignment):
        for align_name, btn in self.align_buttons.items():
            btn.setChecked(align_name == current_alignment)
    
    def initUI(self):
        # Main Layout: Horizontal (Left: Controls, Right: Preview)
        main_layout = QHBoxLayout(self)
        
        # --- Left: Controls ---
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0) # Remove margins for the controls widget
        
        # 1. Height Slider
        controls_layout.addWidget(QLabel("세로화면 높이 조절"))
        
        h_layout = QHBoxLayout()
        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(576, 2276)
        self.height_slider.setValue(self.portrait_height)
        self.height_slider.valueChanged.connect(self.on_height_slider_changed)
        h_layout.addWidget(self.height_slider)
        
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(576, 2276)
        self.height_spinbox.setValue(self.portrait_height)
        self.height_spinbox.setSuffix(" px")
        self.height_spinbox.valueChanged.connect(self.on_height_spinbox_changed)
        h_layout.addWidget(self.height_spinbox)
        
        controls_layout.addLayout(h_layout)
        
        # 2. Width Slider
        controls_layout.addWidget(QLabel("세로화면 너비 조절"))
        
        w_layout = QHBoxLayout()
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(300, 1280)
        self.width_slider.setValue(self.portrait_width)
        self.width_slider.valueChanged.connect(self.on_width_slider_changed)
        w_layout.addWidget(self.width_slider)
        
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(300, 1280)
        self.width_spinbox.setValue(self.portrait_width)
        self.width_spinbox.setSuffix(" px")
        self.width_spinbox.valueChanged.connect(self.on_width_spinbox_changed)
        w_layout.addWidget(self.width_spinbox)
        
        controls_layout.addLayout(w_layout)

        controls_layout.addSpacing(20)

        # 3. 9-Grid Alignment Buttons
        controls_layout.addWidget(QLabel("정렬 설정"))
        
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(5)
        
        self.align_buttons = {}
        alignments = [
            ("top-left", 0, 0), ("top-center", 0, 1), ("top-right", 0, 2),
            ("center-left", 1, 0), ("center-center", 1, 1), ("center-right", 1, 2),
            ("bottom-left", 2, 0), ("bottom-center", 2, 1), ("bottom-right", 2, 2)
        ]
        
        for name, r, c in alignments:
            btn = QPushButton()
            btn.setFixedSize(50, 50)
            btn.setCheckable(True)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 키보드 포커스 제거
            # Unicode arrows or text can be used
            labels = {
                "top-left": "↖", "top-center": "↑", "top-right": "↗",
                "center-left": "←", "center-center": "•", "center-right": "→",
                "bottom-left": "↙", "bottom-center": "↓", "bottom-right": "↘"
            }
            btn.setText(labels.get(name, ""))
            btn.setProperty("align_value", name)
            # Use lambda to capture name
            btn.clicked.connect(lambda checked, n=name: self.on_align_btn_clicked(n))
            grid_layout.addWidget(btn, r, c)
            self.align_buttons[name] = btn
            
        controls_layout.addWidget(grid_container, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 3.5. Include Text Checkbox
        self.include_text_checkbox = QCheckBox("후원 텍스트 포함 정렬")
        self.include_text_checkbox.setChecked(True)  # 기본값: 체크됨 (영상+텍스트 기준)
        self.include_text_checkbox.toggled.connect(self.on_include_text_changed)
        controls_layout.addWidget(self.include_text_checkbox)
        
        controls_layout.addStretch()

        # 4. Dimension Info
        controls_layout.addSpacing(10)
        table_label = QLabel("치수 정보")
        table_label.setStyleSheet("font-weight: bold;")
        controls_layout.addWidget(table_label)
        
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnMinimumWidth(0, 140)  # 가로화면 열
        grid.setColumnMinimumWidth(1, 140)  # 세로화면 열
        
        # 헤더
        grid.addWidget(QLabel("<b>가로화면</b>"), 0, 0)
        grid.addWidget(QLabel("<b>세로화면</b>"), 0, 1)
        
        # 영상
        grid.addWidget(QLabel("영상:"), 1, 0)
        self.h_video_label = QLabel("[1280] x [720]")
        grid.addWidget(self.h_video_label, 1, 0, Qt.AlignmentFlag.AlignRight)
        
        grid.addWidget(QLabel("영상:"), 1, 1)
        self.p_video_label = QLabel(f"[{self.portrait_width}] x [{int(self.portrait_width * 1024 / 576)}]")
        grid.addWidget(self.p_video_label, 1, 1, Qt.AlignmentFlag.AlignRight)
        
        # 후원텍스트
        grid.addWidget(QLabel("후원알림:"), 2, 0)
        self.h_text_label = QLabel("[1280] x [162]")
        grid.addWidget(self.h_text_label, 2, 0, Qt.AlignmentFlag.AlignRight)
        
        grid.addWidget(QLabel("후원알림:"), 2, 1)
        self.p_text_label = QLabel(f"[{self.portrait_width}] x [162]")
        grid.addWidget(self.p_text_label, 2, 1, Qt.AlignmentFlag.AlignRight)
        
        # 전체 창 크기
        p_total_h = int(self.portrait_width * 1024 / 576) + 162
        
        grid.addWidget(QLabel("전체:"), 3, 0)
        self.h_total_label = QLabel("[1280] x [882]")
        grid.addWidget(self.h_total_label, 3, 0, Qt.AlignmentFlag.AlignRight)
        
        grid.addWidget(QLabel("전체:"), 3, 1)
        self.p_total_label = QLabel(f"[{self.portrait_width}] x [{p_total_h}]")
        grid.addWidget(self.p_total_label, 3, 1, Qt.AlignmentFlag.AlignRight)
        
        controls_layout.addLayout(grid)
        
        # 버튼
        controls_layout.addSpacing(15)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("확인")
        self.ok_button.clicked.connect(self.on_ok_clicked)
        button_layout.addWidget(self.ok_button)
        
        controls_layout.addLayout(button_layout)
        
        controls_widget.setFixedWidth(350) # Controls Width
        
        # Add Left Panel to Main Layout
        main_layout.addWidget(controls_widget)
        
        # Right Panel (Preview)
        # 정렬 정보가 필요하므로 SettingsTab에서 주입받아야 하지만, 
        # 여기서는 기본값 'center'로 시작하고 외부에서 update_alignment로 갱신
        self.preview_widget = OverlayPreviewWidget(self.portrait_width, self.portrait_height, "center-center")
        main_layout.addWidget(self.preview_widget)

    
    def on_width_slider_changed(self, value):
        self.width_spinbox.blockSignals(True)
        self.width_spinbox.setValue(value)
        self.width_spinbox.blockSignals(False)
        
        # 9:16 비율 강제 (너비 기준)
        height = int(value * 16 / 9)
        self.update_height_widgets(height)
        
        self.portrait_width = value
        self.portrait_height = height
        self.update_dimensions()
    
    def on_width_spinbox_changed(self, value):
        self.width_slider.blockSignals(True)
        self.width_slider.setValue(value)
        self.width_slider.blockSignals(False)
        
        # 9:16 비율 강제 (너비 기준)
        height = int(value * 16 / 9)
        self.update_height_widgets(height)

        self.portrait_width = value
        self.portrait_height = height
        self.update_dimensions()
    
    def on_height_slider_changed(self, value):
        self.height_spinbox.blockSignals(True)
        self.height_spinbox.setValue(value)
        self.height_spinbox.blockSignals(False)
        
        # 9:16 비율 강제 (높이 기준)
        width = int(value * 9 / 16)
        self.update_width_widgets(width)

        self.portrait_height = value
        self.portrait_width = width
        self.update_dimensions()
    
    def on_height_spinbox_changed(self, value):
        self.height_slider.blockSignals(True)
        self.height_slider.setValue(value)
        self.height_slider.blockSignals(False)
        
        # 9:16 비율 강제 (높이 기준)
        width = int(value * 9 / 16)
        self.update_width_widgets(width)

        self.portrait_height = value
        self.portrait_width = width
        self.update_dimensions()

    def update_height_widgets(self, height):
        self.height_slider.blockSignals(True)
        self.height_spinbox.blockSignals(True)
        self.height_slider.setValue(height)
        self.height_spinbox.setValue(height)
        self.height_slider.blockSignals(False)
        self.height_spinbox.blockSignals(False)

    def update_width_widgets(self, width):
        self.width_slider.blockSignals(True)
        self.width_spinbox.blockSignals(True)
        self.width_slider.setValue(width)
        self.width_spinbox.setValue(width)
        self.width_slider.blockSignals(False)
        self.width_spinbox.blockSignals(False)
    
    def update_dimensions(self):
        width = self.portrait_width
        height = self.portrait_height
        p_total_h = height + 162
        
        self.p_video_label.setText(f"[{width}] x [{height}]")
        self.p_text_label.setText(f"[{width}] x [162]")
        self.p_total_label.setText(f"[{width}] x [{p_total_h}]")
        
        # 전체 창 크기 레이블 업데이트
        total_h = max(882, p_total_h)
        if hasattr(self, 'h_total_label'):
             self.h_total_label.setText(f"[1280] x [{total_h}]")

        # 미리보기 업데이트
        # 미리보기 위젯 업데이트
        if hasattr(self, 'preview_widget'):
            self.preview_widget.update_portrait_size(width, height)
        
        self.settings_changed.emit(width, height)
    
    def on_ok_clicked(self):
        # 확인 버튼 클릭 시 저장하고 닫기 (묻지 않음)
        self.save_and_close()
    
    def on_cancel_clicked(self):
        self._closing = True
        self.close()
    
    def save_and_close(self):
        # 메인 윈도우에 값 저장
        if self.main_window and hasattr(self.main_window, 'settings_tab'):
            self.main_window.settings_tab.overlay_portrait_width = self.portrait_width
            self.main_window.settings_tab.overlay_portrait_height = self.portrait_height
        self._closing = True
        self.close()
    
    def closeEvent(self, event):
        # 자동 저장 (상시 저장됨)이므로 별도 확인 없이 닫음
        # 미리보기도 닫기 (존재한다면)
        if self.preview_dialog and hasattr(self.preview_dialog, 'close'):
             try:
                 self.preview_dialog.close()
             except:
                 pass
        
        event.accept()



    def on_align_btn_clicked(self, align_value):
        # UI 업데이트
        self.update_button_states(align_value)
        # 미리보기 업데이트
        self.preview_widget.update_alignment(align_value)
        
        # 메인 윈도우/설정에 즉시 반영되어야 함
        # 기존 settings_changed 시그널은 size만 전달하므로, 
        # 이를 확장하거나(settings_tab에서 처리) 별도 시그널/콜백이 필요
        # 간단히 settings_tab에서 이 다이얼로그의 align_buttons 상태를 읽거나,
        # 여기서 직접 parent/callback 호출
        
        # 가장 깔끔한 방법: settings_tab에서 connect한 콜백을 호출하거나 새 시그널 emit
        # 여기서는 settings_tab.py의 on_size_changed 같은 로직이 필요함.
        # settings_changed 시그널은 (w, h)만 보냄.
        # align_changed 시그널 추가
        self.align_changed.emit(align_value)

    def update_button_states(self, current_align: str):
        # Legacy fallback
        if current_align in ["left", "center", "right"]:
            current_align = f"top-{current_align}"
        if current_align == "top": current_align = "top-center"
        if current_align == "bottom": current_align = "bottom-center"
            
        for name, btn in self.align_buttons.items():
            is_active = (name == current_align)
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            else:
                btn.setStyleSheet("")
    
    def on_include_text_changed(self, checked):
        """후원텍스트 포함 정렬 옵션 변경 시"""
        # 미리보기 위젯에 include_text 값 전달
        self.preview_widget.include_text = checked
        self.preview_widget.update()
        
        # 설정 변경 시그널 발송 (오버레이에 변경 적용)
        w = self.width_slider.value()
        h = self.height_slider.value()
        self.settings_changed.emit(w, h)
        
        # include_text 변경 시그널 발송 (오버레이에 직접 전달)
        self.include_text_changed.emit(checked)
        
        # 정렬 시그널도 발송하여 위치 업데이트 (include_text 변경은 위치에 영향)
        # 현재 선택된 정렬값 찾기
        current_align = None
        for name, btn in self.align_buttons.items():
            if btn.isChecked():
                current_align = name
                break
        if current_align:
            self.align_changed.emit(current_align)


class TabManagementDialog(QDialog):
    """탭 관리 다이얼로그"""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.tabs_widget = self.main_window.tabs
        self.all_tab_widgets = self.main_window.tab_widgets
        self.ESSENTIAL_TABS = {'채팅창', '리모컨', '설정'}
        
        self.initUI()

    def initUI(self):
        self.setWindowTitle('탭 순서 및 표시 설정')
        self.setMinimumWidth(350)

        layout = QVBoxLayout()
        
        info_label = QLabel(
            "마우스로 드래그하여 탭의 순서를 변경할 수 있습니다.\n"
            "회색 글씨의 탭은 숨기기가 불가능한 탭입니다."
        )
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.populate_list()

        button_layout = QHBoxLayout()
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        ok_button = QPushButton('확인')
        ok_button.clicked.connect(self.accept)

        cancel_button = QPushButton('취소')
        cancel_button.clicked.connect(self.reject)

        apply_button = QPushButton('적용')
        apply_button.clicked.connect(self.apply_changes)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(apply_button)

        layout.addWidget(self.list_widget)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())

    def populate_list(self):
        self.list_widget.clear()
        current_visible_tabs = {self.tabs_widget.tabText(i) for i in range(self.tabs_widget.count())}
        for tab_name in self.main_window.tab_order:
            item = QListWidgetItem(tab_name)
            if tab_name in self.ESSENTIAL_TABS:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setForeground(QColor('gray'))
                item.setToolTip("숨길 수 없습니다.")
            else:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if tab_name in current_visible_tabs:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
            
    def apply_changes(self):
        new_order = []
        visible_tabs = set()

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            tab_name = item.text()
            new_order.append(tab_name)
            if item.checkState() == Qt.CheckState.Checked:
                visible_tabs.add(tab_name)
        
        self.main_window.tab_order = new_order
        
        self.tabs_widget.clear()
        for tab_name in new_order:
            if tab_name in visible_tabs:
                widget = self.all_tab_widgets.get(tab_name)
                if widget:
                    self.tabs_widget.addTab(widget, tab_name)

    def accept(self):
        self.apply_changes()
        super().accept()

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('About Better Cheese 유틸리티')
        self.setFixedSize(466, 580)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

        main_layout = QVBoxLayout()

        icon_label = QLabel(self)
        pixmap = QPixmap(resource_path(r'.\resources\icon\icon_BCU.ico'))
        pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(icon_label)

        info_label = QLabel()
        info_label.setOpenExternalLinks(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)

        html_content = f"""
        <div style="text-align: center;">
            <h2 style="font-size: 16pt; font-weight: bold;">Better Cheese 유틸리티</h2>
            <p>버전: {VERSION}<br>
            빌드번호: {BUILDNUMBER}</p>
            <p>Made With ♥ By 햄스터봇</p>
            <p style="font-size: 10pt;">이 프로그램은 무료 프로그램이며, 허락없는 무단 재배포를 금지합니다.</p>
            <p style="font-size: 9pt;">이 프로그램은 치지직의 비공식 서드파티 프로그램으로,<br>
            치지직에서 개발한 프로그램이 아닙니다.<br>
            "치지직", "Chzzk"은 NAVER Corp.의 상표입니다.</p>
            <p style="font-size: 9pt;"><b>이 프로그램은 다음 라이브러리를 사용하였습니다:</b><br>
            chzzkpy by gunyu1019<br>
            (<a href="https://github.com/gunyu1019/chzzkpy">https://github.com/gunyu1019/chzzkpy</a>)</p>
        </div>
        """
        info_label.setText(html_content)
        main_layout.addWidget(info_label)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        button_layout = QHBoxLayout()
        close_button = QPushButton('닫기')
        close_button.clicked.connect(self.close)
        
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        button_layout.addStretch(1)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)


class GuideDialog(QDialog):
    """
    설정 안내, 방법 등 다양한 정보 대화창을 생성하는 범용 클래스.
    """
    def __init__(self, title, size, content_list, main_window=None, path=None, parent=None):
        """
        :param title: 대화창 제목 (str)
        :param size: 대화창 크기 (tuple, e.g., (width, height))
        :param content_list: 대화창에 표시될 위젯 정보 리스트 (list of dicts)
        :param main_window: 버튼 액션에 필요한 메인 윈도우 인스턴스
        :param path: OBS 경로 등 텍스트 박스에 표시할 경로 (str)
        """
        super().__init__(parent)
        self.title = title
        self.size = size
        self.content_list = content_list
        self.main_window = main_window
        self.path = path

        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

        width, height = self.size
        if height > 0:
            self.setFixedSize(width, height)
        else:
            self.setFixedWidth(width)

        layout = QVBoxLayout()

        for item in self.content_list:
            widget_type = item.get('type')

            if widget_type == 'label':
                widget = QLabel(item.get('text', ''))
                widget.setWordWrap(True)
                layout.addWidget(widget)

            elif widget_type == 'textbox':
                text = self.path if item.get('text') == '{path}' else item.get('text', '')
                widget = QTextEdit()
                widget.setReadOnly(True)
                widget.setText(text)
                if 'height' in item:
                    widget.setFixedHeight(item['height'])
                layout.addWidget(widget)

            elif widget_type == 'button':
                widget = QPushButton(item.get('text', ''))
                action = item.get('action')
                if action:
                    self.connect_button_action(widget, action)
                layout.addWidget(widget)
            
            elif widget_type == 'stretch':
                layout.addStretch(item.get('factor', 1))

        self.setLayout(layout)

    def connect_button_action(self, button, action_info):
        action_name = action_info.get('name')
        close_on_click = action_info.get('close', False)
        button.clicked.connect(lambda: self.execute_action(action_name, close_on_click))

    def execute_action(self, action_name, close_on_click):
        if hasattr(self.main_window, action_name):
            method = getattr(self.main_window, action_name)
            method()
        if close_on_click:
            self.close()
            
    def closeEvent(self, event):
        event.accept()
     
class VotingResultWindow(QDialog):
    def __init__(self, results):
        super().__init__()
        self.results_vote = results
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        table = QTableWidget()
        
        # Sort vote numbers (assuming they are strings like '1', '2', '3')
        sorted_votes = sorted(self.results_vote.keys(), key=int)
        
        # Calculate total number of rows
        total_rows = sum(len(self.results_vote[vote_number]) for vote_number in sorted_votes)
        table.setRowCount(total_rows)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['투표 번호', '투표자'])
        table.horizontalHeader().setStretchLastSection(True)
        
        row = 0
        for vote_number in sorted_votes:
            # Sort voters alphabetically for each vote number
            sorted_voters = sorted(self.results_vote[vote_number])
            for voter in sorted_voters:
                table.setItem(row, 0, QTableWidgetItem(vote_number))
                table.setItem(row, 1, QTableWidgetItem(voter))
                row += 1

        layout.addWidget(table)
        self.setLayout(layout)
        self.setWindowTitle('투표자 명단')
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

class RemoteBanDialog(QDialog):
    def __init__(self, nickname):
        super().__init__()
        self.initUI(nickname)

    def initUI(self,nickname):
        self.setWindowTitle('유저 밴')
        self.setGeometry(150, 150, 400, 300)

        layout = QVBoxLayout()

        self.usernickname_label = QLabel(f'닉네임: {nickname}', self)
        layout.addWidget(self.usernickname_label)

        # 옵션

        ban_layout0 = QHBoxLayout()

        self.ban_type_check1 = QCheckBox('임시 제한', self)
        ban_layout0.addWidget(self.ban_type_check1)

        self.temp_restrict_duration_combobox2 = QComboBox(self)
        self.temp_restrict_duration_combobox2.setFixedWidth(110)
        self.temp_restrict_duration_combobox2.addItems(["1회 (30초)", "2회 (1분)", "3회 (10분)"])
        self.temp_restrict_duration_combobox2.setEnabled(True)
        ban_layout0.addWidget(self.temp_restrict_duration_combobox2)
        
        ban_layout0.addStretch()
        layout.addLayout(ban_layout0)

        ban_layout = QHBoxLayout()

        # 옵션
        self.ban_type_check2 = QCheckBox('활동 제한', self)
        ban_layout.addWidget(self.ban_type_check2)

        button_group_b = QButtonGroup(self)
        button_group_b.addButton(self.ban_type_check1)
        button_group_b.addButton(self.ban_type_check2)
        self.ban_type_check1.toggle()
        button_group_b.setExclusive(True)

        self.temp_ban_duration_combobox2 = QComboBox(self)
        self.temp_ban_duration_combobox2.addItems(["1 일", "3 일", "7 일", "15 일", "30 일", "90 일", "영구"])
        self.temp_ban_duration_combobox2.setFixedWidth(70)
        self.temp_ban_duration_combobox2.setDisabled(True)
        ban_layout.addWidget(self.temp_ban_duration_combobox2)

        ban_layout.addStretch()

        self.ban_type_check1.toggled.connect(self.update_combobox_state)
        self.ban_type_check2.toggled.connect(self.update_combobox_state)

        layout.addLayout(ban_layout)

        self.notice = QLabel('이미 활동 제한된 유저의 정지 기한을 변경하시려면\n채팅부검 메뉴 또는 치지직 스튜디오를 이용하세요.', self)

        layout.addWidget(self.notice)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

    def get_ban_settings(self):
        return self.ban_type_check1.isChecked(), self.temp_ban_duration_combobox2.currentText(), self.temp_restrict_duration_combobox2.currentIndex() + 1, self.temp_restrict_duration_combobox2.currentText()
    
    def update_combobox_state(self):
        self.temp_restrict_duration_combobox2.setEnabled(self.ban_type_check1.isChecked())
        self.temp_ban_duration_combobox2.setEnabled(self.ban_type_check2.isChecked())

class AutoBanSettingMenuDialog(QDialog):
    def __init__(self, parent=None, is_dark_theme=False):
        super().__init__(parent)
        self.settings = QSettings(os.path.join(USERPATH, "BCU", "bansettings.ini"), QSettings.Format.IniFormat)
        self.is_dark_theme = is_dark_theme
        self.initUI()
        self.load_settings()

    def initUI(self):
        self.setWindowTitle('자동 밴 설정')
        self.setGeometry(150, 150, 600, 600)

        layout = QVBoxLayout()

        self.auto_ban_toggle = QToggle(self)
        self.auto_ban_toggle.setText('자동 밴 ON/OFF')
        layout.addWidget(self.auto_ban_toggle)

        length_ban_frame = QFrame()
        length_ban_frame.setFrameShape(QFrame.Shape.StyledPanel)
        length_ban_layout = QVBoxLayout()

        self.length_ban_toggle = QToggle(self)
        self.length_ban_toggle.setText('일정 길이보다 긴 채팅 입력 시 자동 밴')
        length_ban_layout.addWidget(self.length_ban_toggle)

        ban_length_layout = QHBoxLayout()
        self.ban_length_label = QLabel('채팅 길이:')
        ban_length_layout.addWidget(self.ban_length_label)
        self.ban_length_spinbox = QSpinBox()
        self.ban_length_spinbox.setRange(1, 100)
        self.ban_length_spinbox.setSuffix(' 자 초과')
        self.ban_length_spinbox.setFixedWidth(100)
        ban_length_layout.addWidget(self.ban_length_spinbox)

        self.duration_combobox = QComboBox()
        self.duration_combobox.addItems(['블라인드', '임시제한', '1일', '3일', '7일', '15일', '30일', '90일', '영구제한'])
        self.duration_combobox.setFixedWidth(100)
        ban_length_layout.addWidget(self.duration_combobox)

        ban_length_layout.addStretch()
        length_ban_layout.addLayout(ban_length_layout)

        length_ban_frame.setLayout(length_ban_layout)
        layout.addWidget(length_ban_frame)

        length_donation_ban_frame = QFrame()
        length_donation_ban_frame.setFrameShape(QFrame.Shape.StyledPanel)
        length_donation_ban_layout = QVBoxLayout()

        self.length_donation_ban_toggle = QToggle(self)
        self.length_donation_ban_toggle.setText('일정 길이보다 긴 후원 메시지 입력 시 자동 밴')
        length_donation_ban_layout.addWidget(self.length_donation_ban_toggle)

        ban_length_donation_layout = QHBoxLayout()
        self.ban_length_donation_label = QLabel('후원 메시지 길이:')
        ban_length_donation_layout.addWidget(self.ban_length_donation_label)
        self.ban_length_donation_spinbox = QSpinBox()
        self.ban_length_donation_spinbox.setRange(1, 100)
        self.ban_length_donation_spinbox.setSuffix(' 자 초과')
        self.ban_length_donation_spinbox.setFixedWidth(100)
        ban_length_donation_layout.addWidget(self.ban_length_donation_spinbox)

        self.donation_duration_combobox = QComboBox()
        self.donation_duration_combobox.addItems(['블라인드', '임시제한', '1일', '3일', '7일', '15일', '30일', '90일', '영구제한'])
        self.donation_duration_combobox.setFixedWidth(100)
        ban_length_donation_layout.addWidget(self.donation_duration_combobox)

        ban_length_donation_layout.addStretch()
        length_donation_ban_layout.addLayout(ban_length_donation_layout)

        length_donation_ban_frame.setLayout(length_donation_ban_layout)
        layout.addWidget(length_donation_ban_frame)

        word_ban_frame = QFrame()
        word_ban_frame.setFrameShape(QFrame.Shape.StyledPanel)
        word_ban_layout = QVBoxLayout()

        self.word_ban_toggle = QToggle(self)
        self.word_ban_toggle.setText('금지 단어 포함된 채팅 / 후원 메시지 입력 시 자동 밴')
        word_ban_layout.addWidget(self.word_ban_toggle)

        self.word_input_layout = QHBoxLayout()
        self.word_input = QLineEdit(self)
        self.word_input.setPlaceholderText('금지 단어를 입력하세요')
        self.add_word_button = QPushButton('추가', self)
        self.add_word_button.clicked.connect(self.add_word)

        self.word_input_layout.addWidget(self.word_input)
        self.word_input_layout.addWidget(self.add_word_button)
        word_ban_layout.addLayout(self.word_input_layout)

        self.word_list = QListWidget(self)
        word_ban_layout.addWidget(self.word_list)

        word_ban_frame.setLayout(word_ban_layout)
        layout.addWidget(word_ban_frame)

        button_layout = QHBoxLayout()
        self.apply_button = QPushButton('적용')
        self.apply_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.apply_button)

        self.no_save_button = QPushButton('저장 안 함')
        self.no_save_button.clicked.connect(self.close)
        button_layout.addWidget(self.no_save_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        primary_color = '#60cc8c' if self.is_dark_theme else '#53af77'
        text_color = '#FFF' if self.is_dark_theme else '#000'

        toggle_style = f"""
            QToggle {{
                qproperty-bg_color: #777;
                qproperty-circle_color: #FFF;
                qproperty-active_color: {primary_color};
                qproperty-disabled_color: #CCC;
                qproperty-text_color: {text_color};
            }}
        """
        toggle_widgets = [
            self.auto_ban_toggle, self.length_ban_toggle, self.length_donation_ban_toggle, self.word_ban_toggle
        ]
        for widget in toggle_widgets:
            widget.setStyleSheet(toggle_style)

    def add_word(self):
        word = self.word_input.text()
        if word and not self.is_word_in_list(word):
            item = QListWidgetItem(word)
            item_widget = QWidget()
            item_layout = QHBoxLayout()

            spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            item_layout.addItem(spacer)

            duration_combobox = QComboBox()
            duration_combobox.addItems(['블라인드', '임시제한', '1일', '3일', '7일', '15일', '30일', '90일', '영구제한'])
            duration_combobox.setFixedWidth(100)
            item_layout.addWidget(duration_combobox)

            delete_button = QPushButton('삭제')
            delete_button.setFixedWidth(100)
            delete_button.clicked.connect(functools.partial(self.remove_word, item))
            item_layout.addWidget(delete_button)

            item_widget.setLayout(item_layout)
            item.setSizeHint(item_widget.sizeHint())
            self.word_list.addItem(item)
            self.word_list.setItemWidget(item, item_widget)

            self.word_input.clear()
        else:
            self.word_input.clear()

    def is_word_in_list(self, word):
        for i in range(self.word_list.count()):
            if self.word_list.item(i).text() == word:
                return True
        return False

    def remove_word(self, item):
        self.word_list.takeItem(self.word_list.row(item))

    def save_settings(self):
        self.settings.setValue('is_auto_ban', self.auto_ban_toggle.isChecked())
        self.settings.setValue('length_ban', self.length_ban_toggle.isChecked())
        self.settings.setValue('ban_length', self.ban_length_spinbox.value())
        self.settings.setValue('ban_duration', self.duration_combobox.currentText())
        self.settings.setValue('is_length_ban_donation', self.length_donation_ban_toggle.isChecked())
        self.settings.setValue('is_ban_donation_length', self.ban_length_donation_spinbox.value())
        self.settings.setValue('ban_donation_duration', self.donation_duration_combobox.currentText())
        self.settings.setValue('is_word_ban', self.word_ban_toggle.isChecked())

        words = []
        for i in range(self.word_list.count()):
            item = self.word_list.item(i)
            item_widget = self.word_list.itemWidget(item)
            if item_widget:
                combobox = item_widget.findChild(QComboBox)
                if combobox:
                    words.append((item.text(), combobox.currentText()))
        self.settings.setValue('banned_words', str(words))
        self.close()

    def load_settings(self):
        try:
            self.auto_ban_toggle.setChecked(self.settings.value('is_auto_ban', False, type=bool))
            self.length_ban_toggle.setChecked(self.settings.value('length_ban', False, type=bool))
            self.ban_length_spinbox.setValue(self.settings.value('ban_length', 50, type=int))
            self.duration_combobox.setCurrentIndex(self.duration_combobox.findText(self.settings.value('ban_duration', '블라인드', type=str)))
            self.word_ban_toggle.setChecked(self.settings.value('is_word_ban', False, type=bool))
            self.length_donation_ban_toggle.setChecked(self.settings.value('is_length_ban_donation', False, type=bool))
            self.ban_length_donation_spinbox.setValue(self.settings.value('is_ban_donation_length', 50, type=int))
            self.donation_duration_combobox.setCurrentIndex(self.donation_duration_combobox.findText(self.settings.value('ban_donation_duration', '블라인드', type=str)))

            words_str = self.settings.value('banned_words', '[]', type=str)
            words = eval(words_str)
            for word, duration_name in words:
                item = QListWidgetItem(word)
                item_widget = QWidget()
                item_layout = QHBoxLayout()

                spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                item_layout.addItem(spacer)

                duration_combobox = QComboBox()
                duration_combobox.addItems(['블라인드', '임시제한', '1일', '3일', '7일', '15일', '30일', '90일', '영구제한'])
                duration_combobox.setFixedWidth(100)
                duration_combobox.setCurrentIndex(duration_combobox.findText(duration_name))
                item_layout.addWidget(duration_combobox)

                delete_button = QPushButton('삭제')
                delete_button.setFixedWidth(100)
                delete_button.clicked.connect(functools.partial(self.remove_word, item))
                item_layout.addWidget(delete_button)

                item_widget.setLayout(item_layout)
                item.setSizeHint(item_widget.sizeHint())
                self.word_list.addItem(item)
                self.word_list.setItemWidget(item, item_widget)
        except Exception as e:
            self.auto_ban_toggle.setChecked(False)
            self.length_ban_toggle.setChecked(False)
            self.ban_length_spinbox.setValue(50)
            self.duration_combobox.setCurrentIndex(0)
            self.word_ban_toggle.setChecked(False)
            self.ban_length_donation_label.setChecked(False)
            self.ban_length_donation_spinbox.setValue(50)
            self.donation_duration_combobox.setCurrentIndex(0)

class ShowTotalMoneyDialog(QDialog):
    def __init__(self, total_money):
        super().__init__()
        self.total_money = total_money
        self.initUI()

    def initUI(self):
        self.setWindowTitle("총 모금액")
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

        self.layout = QVBoxLayout(self)

        total_money_amount = self.total_money
        total_money_amount = int(total_money_amount*0.8)
        self.total_money_label = QLabel(f"총 모금액: {total_money_amount:,}원", self)
        self.total_money_label.setFont(QFont('Pretendard JP', 20))
        self.layout.addWidget(self.total_money_label)
        self.layout.addStretch()

        self.setLayout(self.layout)
    
    def setMoney(self, total_money, commision_rate):
        self.total_money = total_money
        total_money_amount = self.total_money
        total_money_amount = int(total_money_amount*(100-commision_rate)/100)
        self.total_money_label.setText(f"총 모금액: {total_money_amount:,}원")

class ChzzkRemotePopupWindow(QDialog):
    def __init__(self, text_edit, parent=None):
        super().__init__(parent)
        self.setWindowTitle("치지직 리모컨")
        self.resize(650, 500)

        layout = QVBoxLayout()
        self.text_edit = text_edit
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

class OverlayWebPage(QWebEnginePage):
    video_started_signal = pyqtSignal(str) # 신호 정의
    resolution_detected_signal = pyqtSignal(str) # 해상도 감지 신호

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[Overlay Console] {message}")
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)
        if message.startswith("유튜브 영상 재생 시작됨. 영상 주소:"):
            try:
                # URL 추출 로직
                video_url = message.split("유튜브 영상 재생 시작됨. 영상 주소:")[1].split("?autoplay")[0].strip()
                # 신호 발송
                self.video_started_signal.emit(video_url)
            except IndexError:
                pass
        if message.startswith("유튜브 영상 재생 종료됨"):
            # 종료 시에도 필요하다면 신호를 보낼 수 있음
            pass
        
        if message.startswith("[ChzzkResolution]"):
            # 예: [ChzzkResolution] portrait (720x1280)
            try:
                res_type = message.split("]")[1].strip().split("(")[0].strip()
                self.resolution_detected_signal.emit(res_type)
            except Exception as e:
                print(f"[Overlay Console] Resolution Parse Error: {e}")

    def featurePermissionRequested(self, securityOrigin, feature):
        """권한 요청 자동 허용 (Encrypted Media 등 포함)"""
        self.setFeaturePermission(securityOrigin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)

    def createWindow(self, _type):
        from app.ui_widgets import PopupWindow
        
        popup = PopupWindow(self.profile()) 
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        
        new_page = popup.browser.page()
        
        def on_url_changed(url):
            url_str = url.toString()
            if "prediction" in url_str:
                popup.set_title("승부예측")
                popup.prevent_close = True
                print(f"[OverlayWebPage] Prediction popup detected: {url_str}")
        
        new_page.urlChanged.connect(on_url_changed)
        
        popup.show()
        return new_page

class ChzzkOverlay(QMainWindow):
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 윈도우 플래그: Frameless로 투명화 향상 (Tool 플래그는 OBS 캡처 방해)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # 윈도우 설정: 배경 투명 활성화
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose) # 닫힐 때 자동 삭제
        
        self.setWindowTitle("치지직 영도 오버레이")
        
        settings_path = os.path.join(USERPATH, "BCU", "overlay_settings.ini")
        os.makedirs(os.path.dirname(settings_path), exist_ok=True) # 폴더 확보
        self.settings = QSettings(settings_path, QSettings.Format.IniFormat)
        print(f"[Overlay] Settings Path: {settings_path}")
        
        self.is_portrait = False
        self.alignment = "center"
        if hasattr(self.parent(), 'main_window'):
             self.alignment = getattr(self.parent().main_window, 'overlay_alignment', "center")
             self.include_text = getattr(self.parent().main_window, 'overlay_alignment_include_text', True)
        else:
             self.include_text = True

        self.setFixedSize(1280, 1254)

        self.profile_path = os.path.join(USERPATH, "BCU", "browser_profile")
        os.makedirs(self.profile_path, exist_ok=True)
        self.persistent_profile = QWebEngineProfile("shared", self)
        self.persistent_profile.setPersistentStoragePath(self.profile_path)
        self.persistent_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        # User-Agent: Using default Chromium UA (Firefox spoofing removed)
        settings = self.persistent_profile.settings() 
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        # 자동 재생을 위해 사용자 제스처 요구 비활성화
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        # 플러그인(DRM 등) 활성화
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)

        self.browser = QWebEngineView()
        
        page = OverlayWebPage(self.persistent_profile, self.browser)
        self.browser.setPage(page)
        
        # 비디오 시작 신호 연결
        page.video_started_signal.connect(self.on_video_started)
        # 해상도 감지 신호 연결 (Auto-Rotation)
        page.resolution_detected_signal.connect(self.on_resolution_detected)
        
        # 배경 투명 설정 (새 페이지에 적용)
        self.browser.setStyleSheet("background: transparent;")
        self.browser.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.browser.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 컨텍스트 메뉴 활성화
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        
        # JS 주입
        self.inject_script()
        
        # 로드 완료 시그널 연결 (초기 설정을 확실히 적용하기 위함)
        self.browser.loadFinished.connect(self._on_load_finished)
        
        # URL 로드
        if parent:
            url = parent.main_window.settings_tab.chzzk_video_url.text().strip().replace(" ","")
            is_ui = parent.main_window.settings_tab.chzzk_video_ui_toggle.isChecked()
        else:
            url = "about:blank" # 기본값
            is_ui = False # 기본값 (안전장치)

        url += "?cookie=true&w=1280&h=720"
        if is_ui:
            url += "&ui=true"
        
        self.browser.load(QUrl(url))
        self.setCentralWidget(self.browser)

        # 오프스크린 이동 (화면 밖에서 렌더링)
        max_x = 0
        for screen in QApplication.screens():
            geo = screen.geometry()
            right = geo.x() + geo.width()
            if right > max_x:
                max_x = right
        
        self.move(max_x, 0) # 모든 모니터의 오른쪽 끝(가상 데스크톱 끝)에 배치
        print(f"[Overlay] Window positioned at ({max_x}, 0)")


    def on_video_started(self, url):
        """영상 시작 시 호출되어 영상 타입을 확인하고 방향을 자동 전환합니다."""
        # 정지 예약 로직은 video_donation_tab.py의 on_video_started에서 처리됨
        if self.parent() and self.parent().main_window:
            if not self.parent().main_window.video_donation_tab.toggle_button_auto_detect_shorts.isChecked():
                return
        try:
            # URL에서 Video ID 추출 (embed URL 기준)
            # 예: https://www.youtube.com/embed/VIDEO_ID
            if "embed/" in url:
                video_id = url.split("embed/")[1].split("?")[0]
            else:
                return

            self.set_volume(self.parent().main_window.video_donation_tab.video_volume_slider.value())
            print(f"[Overlay] Video Started: {video_id}")

            if "youtube.com" not in url and "youtu.be" not in url:
                print("[Overlay] Not a YouTube video, skipping YouTube-specific orientation logic.")
                return

            # parent().main_window.remote_tab 에 접근하여 영상 타입 확인
            # parent는 VideoDonationTab 등의 탭일 가능성이 큼
            if self.parent() and hasattr(self.parent(), 'main_window'):
                remote_tab = self.parent().main_window.remote_tab
                if hasattr(remote_tab, 'get_youtube_video_type'):
                    video_type = remote_tab.get_youtube_video_type(video_id)
                    print(f"[Overlay] Detected Video Type: {video_type}")
                    if video_type == "shorts":
                        # 쇼츠면 세로 모드여야 함 (is_portrait가 True여야 함)
                        if not self.is_portrait:
                            print("[Overlay] Switching to Portrait Mode (Auto)")
                            self.set_orientation(True)
                    elif video_type == "normal": # normal
                        # 일반 영상이면 가로 모드여야 함 (is_portrait가 False여야 함)
                        if self.is_portrait:
                            print("[Overlay] Switching to Landscape Mode (Auto)")
                            self.set_orientation(False)
        except Exception as e:
            print(f"[Overlay] Auto-Orientation Error: {e}")
            try:
                if self.is_portrait:
                    print("[Overlay] Switching to Landscape Mode (Chzzk Video?)")
                    self.set_orientation(False)
            except Exception as e:
                print(f"[Overlay] Auto-Orientation Error: {e}")

    def refresh_page(self, url: str = "", is_ui: bool = False):
        # 인자가 제공되지 않으면 parent에서 가져옴
        if not url:
            if self.parent():
                url = self.parent().main_window.settings_tab.chzzk_video_url.text().strip().replace(" ","")
                is_ui = self.parent().main_window.settings_tab.chzzk_video_ui_toggle.isChecked()
            else:
                url = "about:blank" # 기본값
                is_ui = False # 기본값 (안전장치)

        url += "?cookie=true&w=1280&h=720"
        if is_ui:
            url += "&ui=true"
        
        self.browser.load(QUrl(url))

    def set_orientation(self, is_portrait):
        self.is_portrait = is_portrait
        print(f"[Overlay] Applying Orientation: {'Portrait' if is_portrait else 'Landscape'}, Align: {self.alignment}")
        
        self.browser.page().runJavaScript(f"toggleOrientation({str(self.is_portrait).lower()});")
        self.browser.page().runJavaScript(f"setAlignment('{self.alignment}');")
        
        self.browser.setZoomFactor(1.0)

    def toggle_orientation(self):
        self.set_orientation(not self.is_portrait)
        
    def set_alignment(self, alignment):
        self.alignment = alignment
        self.browser.page().runJavaScript(f"setAlignment('{alignment}');")

    def set_portrait_size(self, width, height=None):
        """세로 모드 너비와 높이 설정"""
        self.portrait_width = width
        if height is None:
            height = int(width * 1024 / 576)  # 기본 비율
        self.portrait_height = height
        
        # 윈도우 크기 동적 조절 (가로: 1280, 세로: max(landscape_h, portrait_h))
        # include_text 상태 반영
        include_text = getattr(self, 'include_text', True)
        text_h = 162 if include_text else 0 # For compatibility if needed, but we use fixed 200 for window
        
        # User Request: Window height must NOT change. Text must ALWAYS be visible.
        # So we always allocate space for 200px text.
        const_text_h = 162
        
        landscape_h = 720 + const_text_h
        portrait_h = height + const_text_h
        total_h = max(landscape_h, portrait_h)
        
        self.setFixedSize(1280, total_h)
        
        self.browser.page().runJavaScript(f"setPortraitSize({width}, {height});")
        print(f"[Overlay] Portrait size set to: {width}x{height}, Window resized to 1280x{total_h}, IncludeText: {include_text}")

    def set_skip_timer_enabled(self, enabled: bool):
        """3000ms 타이머 스킵 활성화/비활성화"""
        self.browser.page().runJavaScript(f"setSkipTimerEnabled({str(enabled).lower()});")
        print(f"[Overlay] Skip timer enabled: {enabled}")

    def set_include_text(self, include_text: bool):
        """후원텍스트 포함 정렬 설정"""
        self.include_text = include_text
        self.browser.page().runJavaScript(f"setIncludeText({str(include_text).lower()});")
        # 크기 재계산 및 윈도우 리사이즈
        self.set_portrait_size(self.portrait_width, self.portrait_height)
        print(f"[Overlay] Include text: {include_text}")

    def closeEvent(self, event: QCloseEvent):
        self.closed.emit()
        self.browser.stop()
        self.browser.deleteLater()
        event.accept()

    def _on_load_finished(self, ok):
        if ok:
            # 설정 재적용 (JS 함수들이 로드된 후 실행 보장)
            # 타이머를 사용하여 약간의 지연 후 실행 (안전장치)
            QTimer.singleShot(100, lambda: self.set_alignment(self.alignment))
            QTimer.singleShot(200, lambda: self.set_portrait_size(getattr(self, 'portrait_width', 576), getattr(self, 'portrait_height', 1024)))
            QTimer.singleShot(300, lambda: self.set_include_text(getattr(self, 'include_text', True)))
            print("[Overlay] Page loaded, settings re-applied.")

    def inject_script(self):
        script = QWebEngineScript()
        script_path = os.path.join(r'.\resources\script', 'video_overlay.js')
        try:
            with open(resource_path(script_path), "r", encoding="utf-8") as file:
                script_content = file.read()
        except Exception as e:
            print(f"[Overlay] Failed to load script: {e}")
            return
        script.setSourceCode(script_content)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)
        
        profile = self.browser.page().profile()
        profile.scripts().insert(script)

    def simulate_click(self, x, y):
        target_widget = self.browser.focusProxy()
        if not target_widget:
            target_widget = self.browser

        # 좌표 설정
        local_pos = QPointF(x, y)
        
        # Mouse Press Event
        press_event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            local_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        QApplication.sendEvent(target_widget, press_event)
        
        # Mouse Release Event
        release_event = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            local_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        QApplication.sendEvent(target_widget, release_event)
        
        print(f"[Overlay] Native Click Event Sent to ({x}, {y})")

    def simulate_skip(self):
        """
        'End' 키 입력과 함께 스킵 버튼 좌표를 직접 클릭합니다.
        Mobile 여부를 감지하지 않고 좌표를 클릭합니다.
        """
        # 상태 확인
        is_port = getattr(self, 'is_portrait', False)
        align = getattr(self, 'alignment', 'center')

        coords_to_click = []

        if not is_port: 
            # Landscape (가로)
            # Mobile: 1247x646
            coords_to_click.append((1247, 646))
            coords_to_click.append((1247, 646))
        else:
            # Portrait (세로)
            if align == 'left':
                # Mobile: 542x950
                coords_to_click.append((542, 950))
                coords_to_click.append((542, 950))
            elif align == 'right':
                # Mobile: 1246x950
                coords_to_click.append((1246, 950))
                coords_to_click.append((1246, 950))
            else: # center
                # Mobile: 895x950
                coords_to_click.append((895, 950))
                coords_to_click.append((895, 950))
        
        print(f"[Overlay] Simulating Skip (Blind Click + Force End) - Mode: {'Portrait' if is_port else 'Landscape'}, Align: {align}")
        for x, y in coords_to_click:
            self.simulate_click(x, y)
        
        # Also trigger force video end
        self.browser.page().runJavaScript("window.bcuForceVideoEnd && window.bcuForceVideoEnd();")

    def force_connect(self):
        """Trigger force connect (buffer reset)"""
        print("[In-Process Overlay] Force Connect Requested")
        self.browser.page().runJavaScript("window.bcuForceConnect && window.bcuForceConnect();")

    def force_skip(self):
        """Trigger force skip (4 API calls)"""
        print("[In-Process Overlay] Force Skip Requested")
        self.browser.page().runJavaScript("window.bcuForceSkip && window.bcuForceSkip();")

    def seek_to_start(self):
        """Seek video to start and pause"""
        print("[In-Process Overlay] Seek To Start Requested")
        self.browser.page().runJavaScript("window.bcuSeekToStart && window.bcuSeekToStart();")

    def toggle_play_pause(self):
        """Toggle play/pause on video"""
        print("[In-Process Overlay] Toggle Play/Pause Requested")
        self.browser.page().runJavaScript("window.bcuTogglePlayPause && window.bcuTogglePlayPause();")

    def simulate_key(self, key: str):
        """Simulate keyboard key press"""
        target_widget = self.browser.focusProxy()
        if not target_widget:
            target_widget = self.browser
        
        # First click to focus
        click_x = 640
        click_y = 360
        if self.is_portrait:
            if self.alignment == 'left':
                click_x = 288
            elif self.alignment == 'right':
                click_x = 992
            click_y = 512
        
        self.simulate_click(click_x, click_y)
        
        # Map key string to Qt key
        key_map = {
            'home': Qt.Key.Key_Home,
            'end': Qt.Key.Key_End,
            'space': Qt.Key.Key_Space,
        }
        
        qt_key = key_map.get(key.lower())
        if qt_key is None:
            print(f"[Overlay] Unknown key: {key}")
            return
        
        def send_key():
            press = QKeyEvent(QEvent.Type.KeyPress, qt_key, Qt.KeyboardModifier.NoModifier)
            release = QKeyEvent(QEvent.Type.KeyRelease, qt_key, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(target_widget, press)
            QApplication.sendEvent(target_widget, release)
            print(f"[Overlay] Key sent: {key}")
        
        # Delay to allow focus
        QTimer.singleShot(100, send_key)

    def set_volume(self, volume: int):
        """
        음량 조절 (0~100)
        MutationObserver와 이벤트 리스너를 사용하여 즉각적이고 부하가 적은 제어를 구현합니다.
        """
        # 0.0 ~ 1.0 변환
        vol_float = max(0, min(100, volume)) / 100.0
        
        js_code = f"""
        (function() {{
            window.BcuTargetVolume = {vol_float};
            window.BcuTargetVolumeInt = {volume};

            // 음량 적용 함수
            function applyToMedia(el) {{
                if (el && (el.tagName === 'VIDEO' || el.tagName === 'AUDIO')) {{
                    el.volume = window.BcuTargetVolume;
                    // Explicit mute for instant feedback
                    if (window.BcuTargetVolume <= 0.01) {{
                        el.muted = true;
                    }} else {{
                        el.muted = false;
                    }}
                }}
            }}

            function applyToIframe(iframe) {{
                if (!iframe || !iframe.contentWindow) return;
                
                // Try direct DOM access with Recursion (for Same-Origin iFrames like Chzzk Clip)
                try {{
                    if (iframe.contentDocument) {{
                        const doc = iframe.contentDocument;
                        
                        // 1. Apply to media in this iframe
                        const videos = doc.querySelectorAll('video, audio');
                        videos.forEach(media => {{
                            applyToMedia(media);
                        }});

                        // 2. Recursive apply to child iframes
                        const childIframes = doc.querySelectorAll('iframe');
                        childIframes.forEach(child => applyToIframe(child));
                    }}
                }} catch (e) {{
                    // Cross-origin restricted
                }}

                try {{
                    // YouTube
                    iframe.contentWindow.postMessage(JSON.stringify({{
                        'event': 'command',
                        'func': 'setVolume',
                        'args': [window.BcuTargetVolumeInt] 
                    }}), '*');
                }} catch (e) {{}}
            }}

            function applyAll() {{
                document.querySelectorAll('video, audio').forEach(applyToMedia);
                document.querySelectorAll('iframe').forEach(iframe => {{
                    applyToIframe(iframe);
                    // Attach listeners and retries for existing iframes
                    iframe.addEventListener('load', () => applyToIframe(iframe));
                    setTimeout(() => applyToIframe(iframe), 1000);
                    setTimeout(() => applyToIframe(iframe), 3000);
                }});
            }}

            // 1. 즉시 적용
            applyAll();

            // 2. 매니저 설치 (최초 1회만)
            if (!window.BcuVolumeManagerInstalled) {{
                window.BcuVolumeManagerInstalled = true;

                // (1) HTML5 미디어 이벤트 캡처 (play, loadeddata 등)
                ['play', 'playing', 'loadedmetadata', 'loadeddata', 'durationchange'].forEach(evtName => {{
                    window.addEventListener(evtName, (e) => {{
                        applyToMedia(e.target);
                    }}, true); // Capture phase required for these events
                }});

                // (2) DOM 변경 감지 (새로운 비디오/아이프레임 추가)
                const observer = new MutationObserver((mutations) => {{
                    mutations.forEach((mutation) => {{
                        mutation.addedNodes.forEach((node) => {{
                            if (node.nodeType === 1) {{ // ELEMENT_NODE
                                if (node.tagName === 'VIDEO' || node.tagName === 'AUDIO') {{
                                    applyToMedia(node);
                                }} else if (node.tagName === 'IFRAME') {{
                                    applyToIframe(node);
                                    // 로드 완료 시 재시도
                                    node.addEventListener('load', () => applyToIframe(node));
                                    // 약간의 딜레이 후 확정 적용
                                    setTimeout(() => applyToIframe(node), 1000);
                                }} else {{
                                    // 하위 요소 검색
                                    node.querySelectorAll && node.querySelectorAll('video, audio').forEach(applyToMedia);
                                    node.querySelectorAll && node.querySelectorAll('iframe').forEach(i => {{
                                        applyToIframe(i);
                                        i.addEventListener('load', () => applyToIframe(i));
                                    }});
                                }}
                            }}
                        }});
                    }});
                }});
                
                const obsTarget = document.body || document.documentElement;
                if (obsTarget) {{
                    observer.observe(obsTarget, {{
                        childList: true,
                        subtree: true
                    }});
                }}
            }}
            
        }})();
        """
        self.browser.page().runJavaScript(js_code)

    def on_resolution_detected(self, res_type):
        """JS에서 감지된 해상도 타입(portrait/landscape)에 따라 회전"""
        print(f"[Overlay] Resolution Detected: {res_type}")
        target_portrait = (res_type == "portrait")
        # Direct application ensures alignment is also fixed/applied
        self.set_orientation(target_portrait)