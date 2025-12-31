
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QSlider, QLabel, QWidget, QSizePolicy, QMessageBox, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, QRect, QSettings, QSize
from PyQt6.QtGui import QPainter, QColor, QIcon
import os

from app.constants import USERPATH
from app.resources import resource_path

class PreviewCanvas(QWidget):
    """오버레이 화면을 그리는 캔버스 위젯"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #333;")
        self.current_pixmap = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_pixmap(self, pixmap):
        self.current_pixmap = pixmap
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_pixmap and not self.current_pixmap.isNull():
                target_rect = self.rect()
                pixmap_size = self.current_pixmap.size()
                
                scaled_size = pixmap_size.scaled(
                    target_rect.size(),
                    Qt.AspectRatioMode.KeepAspectRatio
                )
                
                dx = (target_rect.width() - scaled_size.width()) // 2
                dy = (target_rect.height() - scaled_size.height()) // 2
                
                local_pos = event.position()
                lx, ly = local_pos.x() - dx, local_pos.y() - dy
                
                if 0 <= lx < scaled_size.width() and 0 <= ly < scaled_size.height():
                    scale = scaled_size.width() / pixmap_size.width()
                    orig_x = lx / scale
                    orig_y = ly / scale
                    
                    if self.parent() and getattr(self.parent(), 'overlay', None):
                        overlay = self.parent().overlay
                        if hasattr(overlay, 'is_portrait') and overlay.is_portrait:
                            alignment = getattr(overlay, 'alignment', 'center')
                            target_w = 576
                            
                            if alignment == 'left':
                                offset_x = 0
                            elif alignment == 'right':
                                offset_x = 1280 - target_w
                            else: # center
                                offset_x = (1280 - target_w) // 2
                            
                            orig_x += offset_x
                        
                        overlay.simulate_click(int(orig_x), int(orig_y))
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        painter.fillRect(self.rect(), QColor("#333"))

        if self.current_pixmap and not self.current_pixmap.isNull():
            target_rect = self.rect()
            scaled_pixmap = self.current_pixmap.scaled(
                target_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            x = (target_rect.width() - scaled_pixmap.width()) // 2
            y = (target_rect.height() - scaled_pixmap.height()) // 2
            
            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            painter.setPen(QColor("#888"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "오버레이가 보이지 않습니다.")

from PyQt6.QtGui import QPainter, QColor, QIcon, QPixmap

class OverlayPreviewWindow(QWidget):
    def __init__(self, overlay_instance, parent=None):
        super().__init__()
        self.force_close = False
        self.setWindowFlags(Qt.WindowType.Window)
        
        self.video_donation_tab = parent 
        self.overlay = overlay_instance
        self.setWindowTitle("치지직 영도 오버레이 (미리보기)")
        
        settings_path = os.path.join(USERPATH, "BCU", "overlay_preview_settings.ini")
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        self.settings = QSettings(settings_path, QSettings.Format.IniFormat)
        
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(640, 400)

        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        controls_widget = QWidget(self)
        controls_widget.setStyleSheet("background-color: #222; border-bottom: 1px solid #444;")
        
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(10, 5, 10, 5)

        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(5)

        button_style = """
            QPushButton {
                color: white;
                background-color: #444;
                border: 1px solid #555;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #333;
            }
            QPushButton:checked {
                background-color: #d63031;
            }
        """

        self.skip_button = QPushButton(" 스킵", self)
        self.skip_button.setIcon(QIcon(resource_path(r'.\resources\icon\skip-white.png')))
        self.skip_button.setMinimumWidth(80)
        self.skip_button.setStyleSheet(button_style)
        self.skip_button.clicked.connect(lambda: self.video_donation_tab.video_control('end'))
        buttons_layout.addWidget(self.skip_button, 0, 0)

        self.pause_button = QPushButton(" 재생/정지", self)
        self.pause_button.setIcon(QIcon(resource_path(r'.\resources\icon\playpause-white.png')))
        self.pause_button.setMinimumWidth(80)
        self.pause_button.setStyleSheet(button_style)
        self.pause_button.clicked.connect(lambda: self.video_donation_tab.video_control('space'))
        buttons_layout.addWidget(self.pause_button, 0, 1)

        self.home_button = QPushButton(" 맨앞으로", self)
        self.home_button.setIcon(QIcon(resource_path(r'.\resources\icon\rewind-white.png')))
        self.home_button.setMinimumWidth(80)
        self.home_button.setStyleSheet(button_style)
        self.home_button.clicked.connect(lambda: self.video_donation_tab.video_control('home'))
        buttons_layout.addWidget(self.home_button, 0, 2)

        self.reserve_button = QPushButton(" 정지 예약", self)
        self.reserve_button.setCheckable(True)
        self.reserve_button.setIcon(QIcon(resource_path(r'.\resources\icon\pause-white.png')))
        self.reserve_button.setMinimumWidth(80)
        self.reserve_button.setStyleSheet(button_style)
        self.reserve_button.clicked.connect(lambda: self.video_donation_tab.toggle_reserve_video(self.reserve_button.isChecked()))

        if self.video_donation_tab.main_window.remote_tab.toggle_reserve_pause_video_button.isChecked():
            self.reserve_button.setChecked(True)
            self.reserve_button.setText(" 예약 해제")

        buttons_layout.addWidget(self.reserve_button, 1, 0)

        self.rotate_button = QPushButton(" 화면 회전", self)
        self.rotate_button.setMinimumWidth(80)
        self.rotate_button.setStyleSheet(button_style)
        self.rotate_button.clicked.connect(lambda: self.video_donation_tab.rotate_overlay())
        buttons_layout.addWidget(self.rotate_button, 1, 1)

        self.refresh_button = QPushButton(" 새로고침", self)
        self.refresh_button.setIcon(QIcon(resource_path(r'.\resources\icon\refresh-white.png')))
        self.refresh_button.setMinimumWidth(80)
        self.refresh_button.setStyleSheet(button_style)
        self.refresh_button.clicked.connect(lambda: self.video_donation_tab.refresh_page())
        buttons_layout.addWidget(self.refresh_button, 1, 2)

        controls_layout.addLayout(buttons_layout)

        controls_layout.addSpacing(15)

        vol_layout = QHBoxLayout()

        vol_label = QLabel("음량", self)
        vol_label.setStyleSheet("color: white; font-size: 18px;")
        vol_label.setFixedWidth(40)
        vol_layout.addWidget(vol_label)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(100)
        if self.video_donation_tab:
            current_vol = self.video_donation_tab.video_volume_slider.value()
            self.volume_slider.setValue(current_vol)
            self.current_vol_label = QLabel(f"{current_vol}%", self)
        else:
            self.current_vol_label = QLabel("50%", self)

        self.current_vol_label.setStyleSheet("color: white; font-size: 18px;")
        self.current_vol_label.setFixedWidth(50)
        self.current_vol_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.volume_slider.valueChanged.connect(self.on_volume_changed)

        vol_layout.addWidget(self.volume_slider)
        vol_layout.addWidget(self.current_vol_label)

        controls_layout.addLayout(vol_layout)
        
        controls_layout.addStretch()

        layout.addWidget(controls_widget)

        self.canvas = PreviewCanvas(self)
        layout.addWidget(self.canvas)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.capture_overlay)
        self.timer.start(16)

    def update_reserve_state(self, checked):
        """외부에서 정지 예약 상태 변경 시 호출"""
        if self.reserve_button.isChecked() != checked:
            self.reserve_button.blockSignals(True)
            self.reserve_button.setChecked(checked)
            self.reserve_button.blockSignals(False)
        
        if checked:
            self.reserve_button.setText(" 정지 예약 해제")
        else:
            self.reserve_button.setText(" 정지 예약") 

    def on_volume_changed(self, value):
        self.current_vol_label.setText(f"{value}%")
        if self.video_donation_tab:
            if self.video_donation_tab.video_volume_slider.value() != value:
                self.video_donation_tab.video_volume_slider.setValue(value)

    def update_volume_display(self, value):
        """외부(부모 탭)에서 음량 변경 시 호출"""
        if self.volume_slider.value() != value:
            self.volume_slider.blockSignals(True)
            self.volume_slider.setValue(value)
            self.current_vol_label.setText(f"{value}%")
            self.volume_slider.blockSignals(False)

    def capture_overlay(self):
        if not self.overlay or not self.overlay.isVisible():
            self.canvas.set_pixmap(None)
            return

        try:
            pixmap = self.overlay.grab()
            
            if hasattr(self.overlay, 'is_portrait') and self.overlay.is_portrait:
                alignment = getattr(self.overlay, 'alignment', 'center')
                target_w = 576
                target_h = 1254
                
                if alignment == 'left':
                    x = 0
                elif alignment == 'right':
                    x = 1280 - target_w # 704
                else: # center (default)
                    x = (1280 - target_w) // 2 # 352
                
                crop_rect = QRect(x, 0, target_w, target_h)
            else:
                # Landscape: 1280x950
                crop_rect = QRect(0, 0, 1280, 950)
                
            cropped_pixmap = pixmap.copy(crop_rect)
            self.canvas.set_pixmap(cropped_pixmap)
        except Exception as e:
            pass

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.sync()
        self.timer.stop() 
        
        if self.video_donation_tab and hasattr(self.video_donation_tab, 'on_preview_closed'):
            self.video_donation_tab.on_preview_closed()
            
        super().closeEvent(event)

    def toggle_play_pause(self):
        """미리보기 클릭 시 호출: 재생/정지 토글"""
        try:
            if self.video_donation_tab and self.video_donation_tab.main_window:
                self.video_donation_tab.main_window.remote_tab.control_pause_button.click()
        except Exception as e:
            print(f"[Preview] Click Error: {e}")
