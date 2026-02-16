import sys
import re
import os
import traceback
import pyautogui
import win32gui
import win32con
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QCheckBox, 
                             QSpinBox, QMessageBox, QApplication, QTextEdit, QSlider)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QTimer

from app.constants import GLOBALFONTSIZE
from app.ui_widgets import QToggle
from app.resources import resource_path
from app.services import web_server
from datetime import datetime
from playsound import playsound
from app.ui_widgets import QToggle
from app.resources import resource_path

from app.ui_dialogs import ChzzkOverlay
from app.ui_preview import OverlayPreviewWindow
from datetime import datetime
from playsound import playsound

class VideoDonationTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        
        self.main_window = main_window
        self.overlay = None  # 오버레이 인스턴스 저장용 변수

        layout = QVBoxLayout()
        
        self.video_donation_start_time = datetime.strptime("2020-03-18 00:03:21", '%Y-%m-%d %H:%M:%S')

        noti_layout = QHBoxLayout()

        self.noti_check_video = QToggle(self)
        self.noti_check_video.setCheckable(True)
        self.noti_check_video.setText("영도내림 알림")
        self.noti_check_video.setChecked(False)
        noti_layout.addWidget(self.noti_check_video)

        self.auto_video_donation_disable_set = QToggle(self)
        self.auto_video_donation_disable_set.setCheckable(True)
        self.auto_video_donation_disable_set.setText('자동 영도내림')
        self.auto_video_donation_disable_set.setChecked(False)
        noti_layout.addWidget(self.auto_video_donation_disable_set, alignment=Qt.AlignmentFlag.AlignCenter)

        self.noti_sound_video = QCheckBox('알림음', self)
        self.noti_sound_video.toggle()
        noti_layout.addWidget(self.noti_sound_video, alignment=Qt.AlignmentFlag.AlignCenter)

        noti_layout.addStretch()

        self.reset_button_video = QPushButton('목록 초기화', self)
        self.reset_button_video.clicked.connect(self.confirm_reset_video_list)
        self.reset_button_video.setFixedWidth(150)
        noti_layout.addWidget(self.reset_button_video)

        layout.addLayout(noti_layout)

        num_layout = QHBoxLayout()

        self.num_text_video = QLabel(self)
        self.num_text_video.setText("목표 영도 시간:")
        num_layout.addWidget(self.num_text_video)

        self.input_num_box_video = QSpinBox(self)
        self.input_num_box_video.setRange(0, 999)
        self.input_num_box_video.setSingleStep(5)
        self.input_num_box_video.setValue(60)
        self.input_num_box_video.setSuffix(" 분")
        self.input_num_box_video.setMaximumWidth(100)
        num_layout.addWidget(self.input_num_box_video)

        self.video_volume_text_label = QLabel("음량", self) # 라벨 추가
        num_layout.addWidget(self.video_volume_text_label)

        self.video_volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.video_volume_slider.setRange(0, 100)

        saved_volume = self.main_window.settings.value("video_volume", 50, type=int)
        self.video_volume_slider.setValue(saved_volume)
        self.video_volume_slider.setFixedWidth(100)
        self.video_volume_slider.valueChanged.connect(self.on_video_volume_changed) # 슬롯 연결
        num_layout.addWidget(self.video_volume_slider)

        self.video_volume_label = QLabel(f"{saved_volume}%", self)
        self.video_volume_label.setFixedWidth(50)
        num_layout.addWidget(self.video_volume_label)

        num_layout.addStretch()
        layout.addLayout(num_layout)

        quick_settings_layout = QHBoxLayout()

        self.toggle_button_auto_detect_shorts = QToggle(self)
        self.toggle_button_auto_detect_shorts.setText('자동 쇼츠 확대/축소')
        self.toggle_button_auto_detect_shorts.setChecked(False)
        quick_settings_layout.addWidget(self.toggle_button_auto_detect_shorts)

        self.overlay_button = QPushButton("영상후원 오버레이 켜기", self)
        self.overlay_button.clicked.connect(self.open_overlay)
        quick_settings_layout.addWidget(self.overlay_button)

        self.reset_overlay_button = QPushButton("오버레이 리셋", self)
        self.reset_overlay_button.clicked.connect(self.reset_overlay)
        quick_settings_layout.addWidget(self.reset_overlay_button)

        self.force_connect_button_tab = QPushButton("강제연결", self)
        self.force_connect_button_tab.clicked.connect(lambda: self.video_control('connect'))
        quick_settings_layout.addWidget(self.force_connect_button_tab)

        self.force_skip_button_tab = QPushButton("강제스킵", self)
        self.force_skip_button_tab.clicked.connect(lambda: self.video_control('force_skip'))
        quick_settings_layout.addWidget(self.force_skip_button_tab)

        quick_settings_layout.addStretch()
        layout.addLayout(quick_settings_layout)

        rescue_layout = QHBoxLayout()
        self.rescue_overlay_button = QPushButton("오버레이 표시 토글 (숨김)", self)
        self.rescue_overlay_button.hide() # 기본적으로 숨김
        self.rescue_overlay_button.clicked.connect(self.toggle_overlay_position)
        rescue_layout.addWidget(self.rescue_overlay_button)
        
        rescue_layout.addStretch()
        layout.addLayout(rescue_layout)

        self.result_box_video = QTextEdit(self)
        self.result_box_video.setReadOnly(True)
        self.result_box_video.setFont(QFont('Pretendard JP', GLOBALFONTSIZE-1))
        layout.addWidget(self.result_box_video)

        video_count_layout = QHBoxLayout()
        self.chat_count_label_video = QLabel(self)
        self.chat_count_label_video.setText("개수: ")
        video_count_layout.addWidget(self.chat_count_label_video)

        self.len_count_label_video_open_timer = QLabel(self)
        self.len_count_label_video_open_timer.setText("영도 올린 시간: ")
        video_count_layout.addWidget(self.len_count_label_video_open_timer)
        layout.addLayout(video_count_layout)

        video_count_layout1 = QHBoxLayout()
        
        self.len_count_label_video = QLabel(self)
        self.len_count_label_video.setText("총 시간: ")
        video_count_layout1.addWidget(self.len_count_label_video)
        layout.addLayout(video_count_layout1)

        self.error_box_video = QTextEdit(self)
        self.error_box_video.setReadOnly(True)
        self.error_box_video.setMaximumHeight(100)
        self.error_box_video.setFont(QFont('Pretendard JP', GLOBALFONTSIZE-1))
        self.error_box_video.setText("에러 로그 입니다.")
        self.error_box_video.hide()
        layout.addWidget(self.error_box_video)

        self.error_hide_video = QPushButton("에러창 가리기")
        self.error_hide_video.clicked.connect(lambda: (self.error_hide_video.hide(), self.error_box_video.hide()))
        self.error_hide_video.hide()
        layout.addWidget(self.error_hide_video)

        self.setLayout(layout)
        self.load_settings_from_main()


    ##### 영상후원 탭 관련 함수 #####

    def on_video_volume_changed(self, value):
        self.video_volume_label.setText(f"{value}%")
        self.video_volume_control(value)
        web_server.emit_volume_update(value)
        if hasattr(self, 'preview_window') and self.preview_window:
            self.preview_window.update_volume_display(value)
    
    def load_settings_from_main(self):
        """메인 윈도우의 설정 값을 이 탭의 위젯에 적용하고, 위젯 참조를 교체합니다."""
        mw = self.main_window
        
        self.noti_check_video.setChecked(mw.noti_check_video.isChecked())
        self.noti_sound_video.setChecked(mw.noti_sound_video.isChecked())
        self.input_num_box_video.setValue(mw.input_num_box_video.value())
        self.toggle_button_auto_detect_shorts.setChecked(mw.toggle_button_auto_detect_shorts.isChecked())
        self.video_volume_slider.setValue(mw.video_volume_slider.value())

        mw.noti_check_video = self.noti_check_video
        mw.noti_sound_video = self.noti_sound_video
        mw.input_num_box_video = self.input_num_box_video
        mw.toggle_button_auto_detect_shorts = self.toggle_button_auto_detect_shorts
        mw.video_volume_slider = self.video_volume_slider
        
        mw.result_box_video = self.result_box_video
        mw.chat_count_label_video = self.chat_count_label_video
        mw.len_count_label_video_open_timer = self.len_count_label_video_open_timer
        mw.len_count_label_video = self.len_count_label_video
        mw.error_box_video = self.error_box_video
        mw.noti_check_video = self.noti_check_video

    def confirm_reset_video_list(self):
        reply = QMessageBox.question(self, '경고', '영상후원 목록을 초기화 하시겠습니까?\n이 결정은 되돌릴 수 없습니다!', 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.video_donation_start_time = datetime.now()
            self.main_window.first_chat_date_fixed = None
            self.result_box_video.setText("")
            self.chat_count_label_video.setText("개수: ")
            self.len_count_label_video.setText("총 시간: ")
            self.len_count_label_video_open_timer.setText("영도 올린 시간: ")
            self.main_window.was_video_donation_clear = True
            
            try:
                if hasattr(self.main_window, 'show_total_money_dialog') and self.main_window.remote_tab.show_total_money_dialog:
                    self.main_window.remote_tab.show_total_money_dialog.setMoney(self.main_window.total_money, int(self.main_window.settings_tab.commision_rate.value()))
            except:
                None
            self.stop_timer_video()

    def process_videodonation(self, dict):
        """메인 윈도우의 message 핸들러가 호출 (영상후원 메시지 처리)"""
        try:
            chat_date_str = dict.get("time", "")
            nick = dict.get("nick", "")
            cheese = dict.get("cheese", 0)
            sec = dict.get("sec", 0)
            tier = dict.get("tier", 1)
            
            result_video = ""
            video_price_per_sec = int(self.main_window.video_price.text())
            if video_price_per_sec == 0: video_price_per_sec = 1 # 0으로 나누기 방지
            
            sec = int(int(sec) / video_price_per_sec)
            
            if int(tier) == 2:
                result_video += (f"[{chat_date_str}] <🟥{nick}>\t{sec}초")
                if hasattr(self.main_window, 'remote_tab'):
                    self.main_window.remote_tab.remote_script()
            else:
                result_video += (f"[{chat_date_str}] <{nick}>\t{sec}초")
            result_video += f" ({int(cheese):,}개)"
            
            if result_video != "":
                try: chat_count = int(self.chat_count_label_video.text().split("개수: ")[1])
                except:
                    chat_count = 0
                    self.len_count_label_video_open_timer.setText("영도 올린 시간: 0시간 0분 0초")
                    self.start_timer_video()
                try: cheese_count = int(self.len_count_label_video.text().split("총 시간: ")[1].split("시간")[0]) * 3600 + int(self.len_count_label_video.text().split("총 시간: ")[1].split("시간")[1].split("분")[0]) * 60 + int(self.len_count_label_video.text().split("총 시간: ")[1].split("분")[1].split("초")[0])
                except: cheese_count = 0
                
                chat_count += 1
                cheese_count += sec
                
                cursor = self.result_box_video.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                cursor.insertText(result_video + "\n")
                self.result_box_video.setTextCursor(cursor)
                QApplication.processEvents()
                self.chat_count_label_video.setText(f"개수: {chat_count}")
                hours_elapsede, remainder = divmod(cheese_count, 3600)
                minutes_elapsede, seconds_elapsede = divmod(remainder, 60)
                self.len_count_label_video.setText(f"총 시간: {hours_elapsede}시간 {minutes_elapsede}분 {seconds_elapsede}초")
                QApplication.processEvents()
                
            notinum = int(self.input_num_box_video.value())
            if(cheese_count >= notinum * 60 and (self.noti_check_video.isChecked() or self.auto_video_donation_disable_set.isChecked())):
                self.stop_timer_video()
                if self.main_window.is_started_right_now:
                    self.trigger_video_donation_end_notification()
                self.auto_video_donation_disable_set.setChecked(False)
                self.noti_check_video.setChecked(False)
            QApplication.processEvents()
            
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            err = traceback.format_exc()
            errortime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.error_box_video.setText(f"[{errortime}]\n❗오류 발생!{exc_type} {exc_tb.tb_lineno} {err} {fname}\n\n{self.error_box_video.toPlainText()}")
            self.error_box_video.show()
            self.error_box_video.setText(f"[{errortime}]\n❗오류 발생!{exc_type} {exc_tb.tb_lineno} {err} {fname}\n\n{self.error_box_video.toPlainText()}")
            self.error_box_video.show()
            self.chat_count_label_video.setText("")
    
    def open_overlay_only(self):
        if self.overlay is None:
            if self.main_window.chzzk_video_url.text() == "":
                QMessageBox.warning(self, "경고", "치지직 영도 URL이 설정되지 않았습니다.")
                return
            url = self.main_window.settings_tab.chzzk_video_url.text().strip().replace(" ","")
            is_ui = self.main_window.settings_tab.chzzk_video_ui_toggle.isChecked()
            alignment = getattr(self.main_window, 'overlay_alignment', 'center')
            # 인프로세스 모드
            self.overlay = ChzzkOverlay(self)
            self.overlay.closed.connect(self.on_overlay_closed)
            self.overlay.browser.page().video_started_signal.connect(self.on_video_started)
            self.overlay.browser.page().resolution_detected_signal.connect(self.on_resolution_detected)
            self.overlay.set_alignment(alignment)
            self.overlay.show()
            # 바로 ready 상태
            QTimer.singleShot(100, self.on_overlay_ready)

    def on_overlay_ready(self):
        """Called when overlay IPC is ready"""
        # OBS capture workaround: Delay hiding from taskbar by 1 second
        QTimer.singleShot(1000, self.update_taskbar_visibility)
        # Apply portrait size and donation text visibility settings
        # Increase delay to ensure page is fully loaded
        QTimer.singleShot(2000, self.apply_overlay_settings)
        
    def apply_overlay_settings(self):
        """Apply portrait size, height, alignment and donation text settings to overlay"""
        if self.overlay:
            # Get portrait width and height from settings
            portrait_width = getattr(self.main_window.settings_tab, 'overlay_portrait_width', 576)
            portrait_height = getattr(self.main_window.settings_tab, 'overlay_portrait_height', 1024)
            if hasattr(self.overlay, 'set_portrait_size'):
                self.overlay.set_portrait_size(portrait_width, portrait_height)
            
            # Get alignment from settings_tab (9-grid string format)
            alignment = getattr(self.main_window.settings_tab, 'overlay_alignment', 'top-center')
            # Send full 9-grid alignment value (setAlignment JS now parses it)
            if hasattr(self.overlay, 'set_alignment'):
                self.overlay.set_alignment(alignment)
            
            # Get donation text visibility (inverted since setting is "hide")
            # hide_donation_text removed
            hide_donation_text = False
            if hasattr(self.overlay, 'set_donation_text_visible'):
                self.overlay.set_donation_text_visible(not hide_donation_text)
            
            print(f"[Overlay] Applied settings: portrait={portrait_width}x{portrait_height}, align={alignment}, hide_text={hide_donation_text}")
        
    def update_taskbar_visibility(self):
        """Update overlay taskbar visibility - always hide"""
        if self.overlay and self.overlay.isVisible():
            if hasattr(self.overlay, 'set_taskbar_visible'):
                self.overlay.set_taskbar_visible(False)  # 항상 숨기기

    def open_overlay(self):
        if self.overlay is None:
            if self.main_window.chzzk_video_url.text() == "":
                QMessageBox.warning(self, "경고", "치지직 영도 URL이 설정되지 않았습니다.")
                return
            url = self.main_window.settings_tab.chzzk_video_url.text().strip().replace(" ","")
            is_ui = self.main_window.settings_tab.chzzk_video_ui_toggle.isChecked()
            alignment = getattr(self.main_window, 'overlay_alignment', 'center')

            # 인프로세스 모드
            self.overlay = ChzzkOverlay(self)
            self.overlay.closed.connect(self.on_overlay_closed)
            self.overlay.browser.page().video_started_signal.connect(self.on_video_started)
            self.overlay.browser.page().resolution_detected_signal.connect(self.on_resolution_detected)
            self.overlay.set_alignment(alignment)
            self.overlay.show()
            # 바로 ready 상태
            QTimer.singleShot(100, self.on_overlay_ready)
            
            # 미리보기 창 동시 실행
            self.preview_window = OverlayPreviewWindow(self.overlay, self)
            self.preview_window.show()
        else:
            if hasattr(self, 'preview_window') and self.preview_window:
                self.preview_window.raise_()
                self.preview_window.activateWindow()
            else:
                # 미리보기 창 실행
                self.preview_window = OverlayPreviewWindow(self.overlay, self)
                self.preview_window.show()
        
        # 설정 적용 (세로화면 크기 등)
        if hasattr(self.main_window, 'settings_tab'):
            w = getattr(self.main_window.settings_tab, 'overlay_portrait_width', 576)
            h = getattr(self.main_window.settings_tab, 'overlay_portrait_height', 1024)
            # overlay_process.py의 set_portrait_size 사용.
            # 하지만 overlay가 아직 로딩 중일 수 있음. ready 시점에 적용하는 것이 좋지만,
            # set_portrait_size는 내부 멤버 변수 설정 + JS 주입이므로 즉시 호출해도 됨 (단 JS는 로드 후 실행됨)
            # 하지만 JS 주입은 _on_load_finished 이후에 가능하므로, 
            # overlay_process 내에서 멤버 변수로 저장해두고 로드 후 적용하거나,
            # 여기서 딜레이를 주거나, on_video_started 등에서 적용해야 함.
            # 가장 확실한 건 on_overlay_ready에서 적용.
        
    def on_overlay_ready(self):
        # 오버레이 준비 완료 시 실행
        if hasattr(self.main_window, 'settings_tab'):
             w = getattr(self.main_window.settings_tab, 'overlay_portrait_width', 576)
             h = getattr(self.main_window.settings_tab, 'overlay_portrait_height', 1024)
             align = getattr(self.main_window.settings_tab, 'overlay_alignment', 'top-center')
             
             if self.overlay:
                 # 정렬 먼저 적용 (변수 설정)
                 self.overlay.alignment = align
                 # 크기 적용 (JS 주입 포함)
                 self.overlay.set_portrait_size(w, h)
                 # 정렬 적용 (JS 주입)
                 self.overlay.set_alignment(align)
                 print(f"[VideoDonationTab] Applied saved settings: {w}x{h}, {align}")

    def reset_overlay(self):
        if self.overlay:
            self.overlay.close()
            # on_overlay_closed will handle self.overlay = None and closing preview
            QTimer.singleShot(500, self.open_overlay) # Wait for close and then re-open
        else:
            self.open_overlay()

    def on_preview_closed(self):
        self.preview_window = None

    def on_overlay_closed(self):
        self.overlay = None
        # 프리뷰가 닫혀도 오버레이는 닫힘. 오버레이가 닫히면 프리뷰도 닫아야 함 (양방향)
        if hasattr(self, 'preview_window') and self.preview_window:
            if self.preview_window.isVisible():
                self.preview_window.close()
            self.preview_window = None
    
    def rotate_overlay(self):
        if self.overlay is not None:
            self.overlay.toggle_orientation()

    def set_overlay_alignment(self, alignment):
        if self.overlay is not None:
            self.overlay.set_alignment(alignment)
        else:
            QMessageBox.information(self, "알림", "오버레이가 실행 중이지 않습니다.")
    
    def refresh_page(self):
        if self.overlay is not None:
            url = self.main_window.settings_tab.chzzk_video_url.text().strip().replace(" ","")
            is_ui = self.main_window.settings_tab.chzzk_video_ui_toggle.isChecked()
            self.overlay.refresh_page(url, is_ui)
    
    def on_video_started(self, url: str):
        """영상 시작 시 호출되어 영상 타입을 확인하고 방향을 자동 전환합니다."""
        if self.main_window.remote_tab.toggle_reserve_pause_video_button.text() == "정지 예약 해제":
            QTimer.singleShot(1500, lambda: self.main_window.remote_tab.control_pause_button.click())
            QTimer.singleShot(1500, lambda: self.main_window.remote_tab.toggle_reserve_pause_video_button.click())
        if not self.toggle_button_auto_detect_shorts.isChecked():
            return
        try:
            if "embed/" in url:
                video_id = url.split("embed/")[1].split("?")[0]
            else:
                return

            self.overlay.set_volume(self.video_volume_slider.value())
            print(f"[Overlay] Video Started: {video_id}")

            if "youtube.com" not in url and "youtu.be" not in url:
                print("[Overlay] Not a YouTube video, skipping YouTube-specific orientation logic.")
                return

            if hasattr(self.main_window, 'remote_tab'):
                remote_tab = self.main_window.remote_tab
                if hasattr(remote_tab, 'get_youtube_video_type'):
                    video_type = remote_tab.get_youtube_video_type(video_id)
                    print(f"[Overlay] Detected Video Type: {video_type}")
                    if video_type == "shorts":
                        if not self.overlay.is_portrait:
                            print("[Overlay] Switching to Portrait Mode (Auto)")
                            self.overlay.set_orientation(True)
                    elif video_type == "normal":
                        if self.overlay.is_portrait:
                            print("[Overlay] Switching to Landscape Mode (Auto)")
                            self.overlay.set_orientation(False)
        except Exception as e:
            print(f"[Overlay] Auto-Orientation Error: {e}")
            try:
                if self.overlay.is_portrait:
                    print("[Overlay] Switching to Landscape Mode (Chzzk Video?)")
                    self.overlay.set_orientation(False)
            except Exception as e:
                print(f"[Overlay] Auto-Orientation Error: {e}")
    
    def on_resolution_detected(self, res_type: str):
        """JS에서 감지된 해상도 타입(portrait/landscape)에 따라 회전"""
        print(f"[Overlay] Resolution Detected: {res_type}")
        target_portrait = (res_type == "portrait")
        if self.overlay:
            self.overlay.set_orientation(target_portrait)

    def toggle_overlay_position(self):
        """Toggle overlay between visible (0,0) and hidden (off-screen) positions"""
        if self.overlay is None:
            QMessageBox.information(self, "알림", "오버레이가 실행 중이지 않습니다.")
            return

        current_pos = self.overlay.pos()
        if current_pos.x() == 0 and current_pos.y() == 0:
            # Currently at (0,0) -> move to hidden position (off-screen)
            max_x = 0
            for screen in QApplication.screens():
                geo = screen.geometry()
                right = geo.x() + geo.width()
                if right > max_x:
                    max_x = right
            self.overlay.move(max_x, 0)
            self.rescue_overlay_button.setText("오버레이 표시 토글 (숨김)")
        else:
            # Hidden -> move to (0,0)
            self.overlay.move(0, 0)
            self.rescue_overlay_button.setText("오버레이 표시 토글 (보임)")


    ##### 타이머 함수 (이 탭 전용) #####
    def start_timer_video(self):
        self.stop_timer_video()
        self.timer_video_refresh = QTimer(self)
        self.timer_video_refresh.timeout.connect(self.video_refresh)
        self.timer_video_refresh.start(1000)

    def stop_timer_video(self):
        if hasattr(self, 'timer_video_refresh'):
            self.timer_video_refresh.stop()
            del self.timer_video_refresh

    def video_refresh(self):
        try:
            current_text = self.len_count_label_video_open_timer.text().replace("영도 올린 시간: ", "")
            match = re.search(r'(\d+)시간 (\d+)분 (\d+)초', current_text)
            if not match:
                return
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds + 1
            new_hours = total_seconds // 3600
            new_minutes = (total_seconds % 3600) // 60
            new_seconds = total_seconds % 60
            new_text = f"영도 올린 시간: {new_hours}시간 {new_minutes}분 {new_seconds}초"
            self.len_count_label_video_open_timer.setText(new_text)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            err = traceback.format_exc()
            errortime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.error_box_video.setText(f"[{errortime}]\n❗오류 발생!{exc_type} {exc_tb.tb_lineno} {err} {fname}\n\n{self.error_box_video.toPlainText()}")
            self.error_box_video.show()

    def auto_video_donation_disable(self):
        try:
            self.video_donation_disable_msg = QMessageBox()
            self.video_donation_disable_msg.setWindowTitle("자동으로 영도 내리는 중..")
            self.video_donation_disable_msg.setText("영도가 내려집니다..")
            self.video_donation_disable_msg.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))  # 아이콘 설정
            self.video_donation_disable_msg.setIconPixmap(QIcon(resource_path(r'.\resources\icon\dongmad.png')).pixmap(64, 64))  # 아이콘 설정
            self.video_donation_disable_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            self.video_donation_disable_msg.setGeometry(
                self.main_window.geometry().center().x() - self.video_donation_disable_msg.sizeHint().width() // 2,
                self.main_window.geometry().center().y() - self.video_donation_disable_msg.sizeHint().height() // 2,
                self.video_donation_disable_msg.sizeHint().width(),
                self.video_donation_disable_msg.sizeHint().height()
            )
            self.video_donation_disable_msg.show()
            QApplication.processEvents()

            try:
                responsecode = self.video_donation_disable()
                if responsecode:
                    self.video_donation_disable_msg.accept()
                    return
                else:
                    return
            except Exception as e:
                return
            
        except Exception:
            self.video_donation_disable_msg.accept()
            QMessageBox.critical(self, "자동 영도내림 중 에러 발생!", "자동 영도내림 중 에러가 발생하였습니다. 수동으로 영도를 내려주세요.")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            err = traceback.format_exc()
    
    def video_donation_disable(self):
        try:
            js_file_path = resource_path(r'.\resources\script\remote_auto_video_donation_disable.js')
            with open(js_file_path, 'r', encoding='utf-8') as file:
                script = file.read()
            self.main_window.remote_tab.chzzk_broadcast_browser.page().runJavaScript(script)
            return True
        except:
            return False
        
    def show_video_donation_end_message(self):
        self.video_donation_off_noti_msg = QMessageBox()
        self.video_donation_off_noti_msg.setWindowTitle("영도 내림 알림")
        self.video_donation_off_noti_msg.setText(self.main_window.VIDEO_DONATION_OFF_NOTI_TEXT)
        self.video_donation_off_noti_msg.setFont(QFont('Pretendard JP', 15))
        self.video_donation_off_noti_msg.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))  # 아이콘 설정
        self.video_donation_off_noti_msg.setIconPixmap(QIcon(resource_path(r'.\resources\icon\dongmad.png')).pixmap(64, 64))  # 아이콘 설정
        self.video_donation_off_noti_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.video_donation_off_noti_msg.button(QMessageBox.StandardButton.Ok).setText(self.main_window.VIDEO_DONATION_OFF_NOTI_OKTEXT)  # 버튼 텍스트 변경
        self.video_donation_off_noti_msg.setGeometry(
            self.main_window.geometry().center().x() - self.video_donation_off_noti_msg.sizeHint().width() // 2,
            self.main_window.geometry().center().y() - self.video_donation_off_noti_msg.sizeHint().height() // 2,
            self.video_donation_off_noti_msg.sizeHint().width(),
            self.video_donation_off_noti_msg.sizeHint().height()
        )
        if self.auto_video_donation_disable_set.isChecked():
            self.video_donation_off_noti_msg.setText("자동"+ self.main_window.VIDEO_DONATION_OFF_NOTI_TEXT)
        self.video_donation_off_noti_msg.show()
    
    def show_video_donation_end_message_alt(self):
        if self.auto_video_donation_disable_set.isChecked():
            QMessageBox.information(self,"영도 내림 알림","자동 영도내림 성공!\n"+ self.main_window.VIDEO_DONATION_OFF_NOTI_TEXT)
        else:
            QMessageBox.information(self,"영도 내림 알림",self.main_window.VIDEO_DONATION_OFF_NOTI_TEXT)
        QApplication.processEvents()

    def show_video_donation_end_message_alt_mute(self):
        self.video_donation_off_noti_msg = QMessageBox()
        self.video_donation_off_noti_msg.setWindowTitle("영도 내림 알림")
        self.video_donation_off_noti_msg.setText(self.main_window.VIDEO_DONATION_OFF_NOTI_TEXT)
        self.video_donation_off_noti_msg.setFont(QFont('Pretendard JP', 15))
        self.video_donation_off_noti_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.video_donation_off_noti_msg.button(QMessageBox.StandardButton.Ok).setText(self.main_window.VIDEO_DONATION_OFF_NOTI_OKTEXT)  # 버튼 텍스트 변경
        self.video_donation_off_noti_msg.setGeometry(
            self.main_window.geometry().center().x() - self.video_donation_off_noti_msg.sizeHint().width() // 2,
            self.main_window.geometry().center().y() - self.video_donation_off_noti_msg.sizeHint().height() // 2,
            self.video_donation_off_noti_msg.sizeHint().width(),
            self.video_donation_off_noti_msg.sizeHint().height()
        )
        if self.auto_video_donation_disable_set.isChecked():
            self.video_donation_off_noti_msg.setText("자동 영도내림 완료.\n"+ self.main_window.VIDEO_DONATION_OFF_NOTI_TEXT)
        self.video_donation_off_noti_msg.show()
        QApplication.processEvents()
    
    def show_message_video_donation_end(self):
        self.video_donation_off_noti_msg = QMessageBox()
        self.video_donation_off_noti_msg.setWindowTitle("영도 끝났다")
        self.video_donation_off_noti_msg.setText("영도가 끝났습니다. 유튜브 녹화 버튼 누르세요.")
        self.video_donation_off_noti_msg.setFont(QFont('Pretendard JP', 14))
        self.video_donation_off_noti_msg.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))  # 아이콘 설정
        self.video_donation_off_noti_msg.setIconPixmap(QIcon(resource_path(r'.\resources\icon\dongmad.png')).pixmap(64, 64))  # 아이콘 설정
        self.video_donation_off_noti_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.video_donation_off_noti_msg.button(QMessageBox.StandardButton.Ok).setText("녹화가 아니라 다시보기!")  # 버튼 텍스트 변경
        self.video_donation_off_noti_msg.setGeometry(
            self.main_window.geometry().center().x() - self.video_donation_off_noti_msg.sizeHint().width() // 2,
            self.main_window.geometry().center().y() - self.video_donation_off_noti_msg.sizeHint().height() // 2,
            self.video_donation_off_noti_msg.sizeHint().width(),
            self.video_donation_off_noti_msg.sizeHint().height()
        )
        self.video_donation_off_noti_msg.show()
        QApplication.processEvents()
    
    def trigger_video_donation_end_notification(self):
        print("438")
        if self.main_window.settings_tab.kanetv8.isChecked():
            if self.noti_check_video.isChecked():
                if self.noti_sound_video.isChecked():
                    playsound(resource_path(r'resources\mp3\noti.mp3'))
            if self.auto_video_donation_disable_set.isChecked():
                self.overlay_text_box_video_donation_disable_func()
                self.auto_video_donation_disable()
            QApplication.processEvents()
            if self.noti_check_video.isChecked():
                self.show_video_donation_end_message()
        else:
            if self.auto_video_donation_disable_set.isChecked():
                self.overlay_text_box_video_donation_disable_func()
                self.auto_video_donation_disable()
            QApplication.processEvents()
            if self.noti_check_video.isChecked():
                if self.noti_sound_video.isChecked():
                    self.show_video_donation_end_message_alt()
                else:
                    self.show_video_donation_end_message_alt_mute()
    
    def overlay_text_box_replace_text(self, text):
        replace_targets = ["영도올림", "영도좀만", "영도왕잠시", "영도왕좀만", "영도 올림", "영도 좀만", "영도 왕잠시", "영도 왕좀만", "영도왕조금", "영도 왕조금", "영도 왕 조금", "영도 왕 잠시", "영도 왕 좀만"]
        result = text
        k = 0
        for target in replace_targets:
            if target in result: k+=1
            result = result.replace(target, "영도내림")
        if k == 0:
            if result != "" and result != "영도내림":
                result = "(영도내림) " + result
            else:
                result = "영도내림"
        return result
    
    def overlay_text_box_video_donation_disable_func(self):
        text = self.main_window.remote_tab.overlay_text_box.text()
        text = self.overlay_text_box_replace_text(text)
        self.main_window.remote_tab.overlay_text_box.setText(text)
        self.main_window.remote_tab.overlay_text_send_button.click()
    
        
    # --- 오버레이 제어 ---
    ### 영도 리모컨 관련 함수 ##

    def video_control_reserve(self):
        """정지 예약 버튼 토글 (기존 연결 유지용)"""
        # 버튼이 이미 토글된 상태이므로 현재 상태를 그대로 전달
        current_state = self.main_window.remote_tab.toggle_reserve_pause_video_button.isChecked()
        self.toggle_reserve_video(current_state)

    def toggle_reserve_video(self, checked):
        """정지 예약 상태를 변경하고 모든 UI를 동기화합니다."""
        
        # 1. Remote Tab 버튼 동기화
        remote_btn = self.main_window.remote_tab.toggle_reserve_pause_video_button
        if remote_btn.isChecked() != checked:
            remote_btn.blockSignals(True)
            remote_btn.setChecked(checked)
            remote_btn.blockSignals(False)
        
        if checked:
            remote_btn.setText("정지 예약 해제")
        else:
            remote_btn.setText("정지 예약")

        # 2. Preview Window 버튼 동기화
        if hasattr(self, 'preview_window') and self.preview_window:
            self.preview_window.update_reserve_state(checked)

        print(f"Video Reserve Pause: {checked}")

    def video_control(self, action):
        """
        오버레이의 영상 플레이어를 컨트롤합니다.
        action: 'end', 'home', 'space'
        """
        if self.overlay is None:
            return

        print(f"Video Control Action: {action}")
        
        if action == 'end':
            # Skip 버튼 클릭 + End 키 전송
            self.overlay.simulate_skip()
            self.overlay.simulate_key('end')
        elif action == 'home':
            # 맨 앞으로 - 스크립트로 0초 이동 및 일시정지
            if hasattr(self.overlay, 'seek_to_start'):
                self.overlay.seek_to_start()
            else:
                self.overlay.simulate_key('home')
        elif action == 'space':
            # 재생/정지 - 스크립트로 토글
            if hasattr(self.overlay, 'toggle_play_pause'):
                self.overlay.toggle_play_pause()
            else:
                # Fallback: 영상 중앙 클릭
                if hasattr(self.overlay, 'is_portrait') and self.overlay.is_portrait:
                    alignment = getattr(self.overlay, 'alignment', 'center')
                    if alignment == 'left':
                        click_x = 288
                    elif alignment == 'right':
                        click_x = 992
                    else:
                        click_x = 640
                    click_y = 512
                else:
                    click_x = 640
                    click_y = 360
                self.overlay.simulate_click(click_x, click_y)
        elif action == 'connect':
            if hasattr(self.overlay, 'force_connect'):
                self.overlay.force_connect()
        elif action == 'force_skip':
            if hasattr(self.overlay, 'force_skip'):
                self.overlay.force_skip()

    def video_volume_control(self, volume):
        if self.overlay:
            self.overlay.set_volume(volume)