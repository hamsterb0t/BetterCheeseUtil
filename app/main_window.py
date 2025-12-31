import sys
import os
import re
import shutil
import subprocess
import requests
import threading
import pygame
import urllib.parse
import json
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QPushButton, QSlider, QSpinBox, QTabWidget,
                             QTextEdit, QListWidgetItem)
from PyQt6.QtGui import QIcon, QColor, QBrush
from PyQt6.QtCore import Qt, QTimer, QUrl, QSettings, QThread, pyqtSlot, QSize, QPoint
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from datetime import datetime
import random
import qdarktheme

from app.constants import (USERPATH, AUTH_REDIRECT_URI, AUTH_FILE_PATH, 
                           VERSION, BUILDNUMBER)
from app.resources import resource_path
from app.core.chat_connector import Chatroom_Connector
from app.core.auth import OAuthHttpServerWorker
from app.ui_widgets import QToggle, LabelButtonWidget, PopupWindow

from app.tabs.chatroom_tab import ChatroomTab
from app.tabs.remote_tab import RemoteTab
from app.tabs.video_donation_tab import VideoDonationTab
from app.tabs.chat_log_search_tab import ChatLogSearchTab
from app.tabs.vote_tab import VoteTab
from app.tabs.pick_tab import PickTab
from app.tabs.settings_tab import SettingsTab

# ------------------------------


class BetterCheeseUtil(QMainWindow):
    def __init__(self):
        self.is_new_user = not os.path.exists(os.path.join(USERPATH, "BCU", "BCU.ini"))
        os.makedirs(os.path.dirname(os.path.join(USERPATH, "BCU")), exist_ok=True)
        self.settings = QSettings(os.path.join(USERPATH, "BCU", "BCU.ini"), QSettings.Format.IniFormat)
        
        overlay_dest = os.path.join(USERPATH, "BCU", "prediction_overlay.html")
        try:
            if os.path.exists(overlay_dest):
                os.remove(overlay_dest) # Force update
            overlay_src = resource_path(r'.\resources\templates\prediction_overlay.html')
            shutil.copy2(overlay_src, overlay_dest)
            print(f"Copied prediction_overlay.html to {overlay_dest}")
        except Exception as e:
            print(f"Failed to copy prediction_overlay.html: {e}")

        super().__init__()
        
        self.setWindowTitle(f'Better Cheese 유틸리티 V{VERSION}')
        self.setGeometry(100, 100, 600, 600)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

        self.chatroom_connector_instance = Chatroom_Connector()

        # 탭 간 공유 변수
        self.first_chat_date_fixed = None
        self.cheese_count_fixed = 0
        self.video_type = None
        self.latest_video = []
        self.latest_donation = []
        self.is_msg = False
        self.mission_list = {}
        self.is_close_without_save_setting = False
        self.last_played_video_tier = 0
        self.is_checking_tier = False
        self.was_video_donation_clear = True
        self.total_money = 0
        self.is_login_cookies_completed = False
        self.user_id_moa_before = ""
        self.close_main_window = False
        self.is_started_right_now = False
        self.is_chat_connected = False
        self.is_live_started = False
        self.two_tier_user_list = [] 
        self.picked_user_nick = ""
        self.is_pick_clicked = False
        self.user_id_chzzk_ban = ""
        self.user_nick_chzzk_ban = ""
        self.user_nick_chzzk_ban = ""
        self.userProfileUrl = ""
        self.overlay_alignment = "center" # 오버레이 정렬 기본값
        self.remember_window_check = QToggle(self)
        self.remember_chat_popup_check = QToggle(self)
        self.remote_duplicate_check = QToggle(self)
        self.only_subscriber_check = QToggle(self)
        
        # 오디오
        self.is_audio_playing = False
        self.audio_thread = None
        self.stop_audio_event = threading.Event()

        # OAuth
        self.oauth_state = None
        self.redirect_uri = AUTH_REDIRECT_URI
        self.http_server_thread = None
        self.http_server_worker = None

        pygame.mixer.init()

        self.integrated_browser = None
        self.chat_browser = None

        # UI 텍스트 (내수용 모드 등)
        self.load_ui_text()

        self.profile_path = os.path.join(USERPATH, "BCU", "browser_profile")
        os.makedirs(self.profile_path, exist_ok=True)
        self.persistent_profile = QWebEngineProfile("shared", self)
        self.persistent_profile.setPersistentStoragePath(self.profile_path)
        self.persistent_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        self.persistent_profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"
        )
        settings = self.persistent_profile.settings() 
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)


        # --- 탭 인스턴스화 ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { height: 40px; width: 75px; font-size: 11pt; padding: 0px; margin: 0px; }")

        # --- 시그널 연결 및 초기화 실행 ---
        self.load_settings()     # 설정값 로드 (각 탭의 load_settings_from_main이 여기서 호출됨)
        # 각 탭 클래스의 인스턴스를 생성 (self를 전달하여 메인 윈도우와 통신)
        self.chatroom_tab = ChatroomTab(self)
        self.video_donation_tab = VideoDonationTab(self)
        self.remote_tab = RemoteTab(self)
        self.chat_log_search_tab = ChatLogSearchTab(self)
        self.vote_tab = VoteTab(self)
        self.pick_tab = PickTab(self)
        self.settings_tab = SettingsTab(self)

        # 탭 위젯 딕셔너리 구성
        self.tab_widgets = {
            '채팅창': self.chatroom_tab,
            '리모컨': self.remote_tab,
            '영상후원': self.video_donation_tab,
            '채팅부검': self.chat_log_search_tab,
            '투표': self.vote_tab,
            '추첨': self.pick_tab,
            '설정': self.settings_tab
        }
        
        self.tab_order = list(self.tab_widgets.keys())
        self.connect_connector_signals() # 커넥터 시그널 연결
        self.load_tab_settings() # 탭 순서 로드
        self.initialize()        # 메인 윈도우 초기화
        self.disable_kanetv8_features()
        
        # [SettingsTab] 오버레이 정렬 UI 초기화
        # load_settings에서 self.overlay_alignment 값을 읽어왔으므로,
        # SettingsTab의 콤보박스에 반영해줘야 함 (SettingsTab 초기화 이후이므로 가능)
        alignment_map_rev = {
            "center": "가운데",
            "left": "왼쪽",
            "right": "오른쪽"
        }
        self.settings_tab.overlay_alignment_combobox.setCurrentText(alignment_map_rev.get(self.overlay_alignment, "가운데"))

        self.setCentralWidget(self.tabs)
        self.move(self.saved_window_position)
        self.remote_tab.broadcast_button.click() # remote_tab의 버튼 클릭

        if self.close_main_window:
            QApplication.processEvents()
            QTimer.singleShot(0, self.close)
            return

        self.load_all_data()
        self.update_chat_status("채팅창: 🔴연결 안 됨")
        QTimer.singleShot(2000, lambda: setattr(self, 'is_started_right_now', True))

    # =================================================================
    # ==  핵심 신호 처리 및 분배 (Core Signal Handling & Distribution) ==
    # =================================================================

    def connect_connector_signals(self):
        """Chatroom_Connector의 시그널을 메인 윈도우 또는 각 탭의 슬롯에 연결합니다."""
        if not self.chatroom_connector_instance:
            return
        try:
            # --- 1. 메인 윈도우가 직접 처리하는 시그널 ---
            self.chatroom_connector_instance.message.connect(self.message) # 핵심: 메시지 분배기
            self.chatroom_connector_instance.auto_mission.connect(self.auto_mission)
            self.chatroom_connector_instance.update_connection_status.connect(self.update_chat_status) # 공용 상태 표시
            self.chatroom_connector_instance.start_temp_server.connect(self.start_oauth_server) # OAuth 스레드 관리
            self.chatroom_connector_instance.stop_temp_server.connect(self.stop_oauth_server) # OAuth 스레드 관리
            self.chatroom_connector_instance.run_chat_popup.connect(self.run_chat_popup)
            self.chatroom_connector_instance.chatroom_get_popup_url.connect(self.chatroom_get_popup_url)

            # --- 2. ChatroomTab으로 직접 연결되는 시그널 ---
            self.chatroom_connector_instance.append_result_chat.connect(self.chatroom_tab.append_result_chat)
            self.chatroom_connector_instance.setText_resultCHAT.connect(self.chatroom_tab.set_text_result_chat)
            self.chatroom_connector_instance.login_success.connect(self.chatroom_tab.on_login_success)
            self.chatroom_connector_instance.login_failure.connect(self.chatroom_tab.on_login_failure)
            self.chatroom_connector_instance.manual_login_required.connect(self.chatroom_tab.prompt_manual_login)
            self.chatroom_connector_instance.update_nicknames.connect(self.chatroom_tab.update_nicknames_labels)
            self.chatroom_connector_instance.reconnect.connect(self.chatroom_tab.handle_reconnect_signal)

            # --- 3. RemoteTab으로 직접 연결되는 시그널 ---
            self.chatroom_connector_instance.two_tier_add.connect(self.two_tier_add) # 2티어 UI 갱신
            self.chatroom_connector_instance.refresh_remote.connect(self.refresh_remote) # 브라우저 새로고침

        except Exception as e:
            print(f"Error connecting signals: {e}")

    @pyqtSlot(str)
    def update_chat_status(self, status_text):
        """공용 상태 라벨(리모컨 탭) 및 채팅창 탭의 UI 갱신"""
        # 리모컨 탭의 상태창 업데이트
        self.remote_tab.chat_connection_status.setText(status_text)
        status_text_noemoji = status_text.replace('\U0001F7E2',"").replace('\U0001F534',"").replace('\U0001F7E1',"")
        self.setWindowTitle(f"Better Cheese 유틸리티 V{VERSION} | {status_text_noemoji}")

        # 채팅창 탭의 버튼/UI 상태 업데이트
        if "🟢" in status_text:
            self.chatroom_tab.is_chat_connected = True
        elif "🔴" in status_text:
            self.chatroom_tab.is_chat_connected = False
            if self.chatroom_tab.toggle_button_chat.isChecked():
                self.chatroom_tab.toggle_button_chat.blockSignals(True)
                self.chatroom_tab.toggle_button_chat.setChecked(False)
                self.chatroom_tab.toggle_button_chat.blockSignals(False)
                
                # handle_chat_toggle(False) 로직의 일부를 여기서 수행
                self.chatroom_tab.toggle_button_chat.setText("채팅창 접속")
                self.settings_tab.login_reset_button.setEnabled(True)
                
                if "연결 실패" in status_text or "연결 오류" in status_text :
                    self.chatroom_tab.result_box_chat.append("채팅창 연결에 실패했습니다.")
                elif "연결 끊김" in status_text:
                    self.chatroom_tab.result_box_chat.append("채팅창 연결이 끊어졌습니다.")
                else:
                    self.chatroom_tab.result_box_chat.setText("채팅창 접속 버튼을 누르면 채팅창에 접속합니다.")
                
                self.chatroom_tab.chatroom_signal.setText("")
                self.chatroom_tab.channel_label.setText("연결된 채널: (연결 안 됨)")

    @pyqtSlot(str, dict)
    def message(self, msg_str, msg_dict):
        """
        모든 메시지를 수신하여 각 탭의 처리기(handler)에 전달합니다.
        """
        # --- 1. 공용 변수 업데이트 (총 모금액) ---
        donation_type = msg_dict.get("donation_type", "")
        cheese = msg_dict.get("cheese", 0)
        if donation_type in ["영상후원", "치즈", "미션성공"]:
            self.total_money += int(cheese)
            if hasattr(self.remote_tab, 'show_total_money_dialog') and self.remote_tab.show_total_money_dialog:
                self.remote_tab.show_total_money_dialog.setMoney(self.total_money, int(self.settings_tab.commision_rate.value()))

        # --- 2. 각 탭에 메시지 분배 ---
        
        # 2-1. [ChatroomTab] : 모든 메시지를 채팅창에 표시
        msg_str_without_id = msg_str.replace(" ("+msg_dict["id"]+")", "")
        self.chatroom_tab.append_result_chat(msg_str_without_id)

        # 2-2. [VideoDonationTab] : 영상후원 메시지 처리
        if donation_type == "영상후원":
            self.video_donation_tab.process_videodonation(msg_dict)

        # 2-3. [RemoteTab] : 후원/구독/미션 메시지를 후원 목록/왕도네 목록에 처리
        elif donation_type != "채팅": 
            self.remote_tab.process_donation_message(msg_dict)
        
        # 2-4. [VoteTab] : 채팅/도네이션 메시지를 투표 로직으로 처리
        self.vote_tab.process_vote_message(msg_dict)
        
        # 2-5. [PickTab] : 채팅 메시지를 추첨 로직으로 처리
        self.pick_tab.process_pick_message(msg_dict)

    # =================================================================
    # ==  공용 서비스 (Shared Services) ==
    # =================================================================

    # --- 탭에서 호출되는 슬롯 (Main <-> Connector) ---
    @pyqtSlot()
    def two_tier_add(self):
        self.remote_tab.remote_script_2tier()

    @pyqtSlot()
    def refresh_remote(self):
        self.remote_tab.refresh_browsers()
    
    @pyqtSlot()
    def auto_mission(self):
        if self.settings_tab.auto_mission_approve.isChecked():
            QTimer.singleShot(1000, self.remote_tab.remote_auto_mission)
        
    @pyqtSlot(str)
    def append_result_chat(self, text):
        """(ChatroomTab에서 사용) Connector -> Main -> ChatroomTab"""
        self.chatroom_tab.append_result_chat(text)
    
    @pyqtSlot()
    def run_chat_popup(self):
        self.open_chat()

    @pyqtSlot()
    def chatroom_get_popup_url(self):
        print("chatroomg eet")
        QTimer.singleShot(1000, self.chatroom_tab.send_chat_message_connected)
        QTimer.singleShot(1500, self.chatroom_tab.chatroom_get_popup_url)

    # --- OAuth 스레드 관리 ---
    @pyqtSlot(str)
    def start_oauth_server(self, state):
        if self.http_server_thread and self.http_server_thread.isRunning():
            return
        parsed_uri = urllib.parse.urlparse(self.redirect_uri)
        host = parsed_uri.hostname
        port = parsed_uri.port or 80
        self.http_server_worker = OAuthHttpServerWorker(state, host, port)
        self.http_server_thread = QThread()
        self.http_server_worker.moveToThread(self.http_server_thread)
        # (중요) 시그널을 chatroom_tab의 슬롯에 연결
        self.http_server_worker.code_received_signal.connect(self.chatroom_tab.on_code_received)
        self.http_server_worker.server_stopped_signal.connect(self.on_server_stopped)
        self.http_server_thread.started.connect(self.http_server_worker.run)
        self.http_server_thread.start()

    @pyqtSlot()
    def stop_oauth_server(self):
        if self.http_server_worker:
            self.http_server_worker.stop()
        if self.http_server_thread:
            self.http_server_thread.quit()
            self.http_server_thread.wait(2000)
    
    @pyqtSlot()
    def on_server_stopped(self):
        if self.http_server_thread:
            self.http_server_thread.quit()
            self.http_server_thread.wait(1000)
            self.http_server_thread = None
        self.http_server_worker = None

    # --- 테마 및 UI ---
    def theme_change(self, is_first_launch):
        # theme_check 위젯은 settings_tab에 있음
        is_dark_theme = self.settings_tab.theme_check.isChecked()
        theme = 'dark' if is_dark_theme else 'light'
        if QApplication.instance():
            QApplication.instance().setStyle("Fusion")

        # 2. 색상 설정
        primary_color = '#60cc8c' if is_dark_theme else '#53af77'
        text_color = '#FFFFFF' if is_dark_theme else '#000000' # 찐한 검은색
        border_color = '#60cc8c' if is_dark_theme else '#53af77' # 테두리 색상

        icon_suffix = '-white' if is_dark_theme else ''
        
        # 3. 커스텀 컬러 및 스타일 강제 주입
        custom_colors = {
            "primary": primary_color,
            "foreground": text_color, 
        }

        additional_qss = f"""
            QPushButton {{
                color: {text_color};
                border: 2px solid {border_color};
                border-radius: 4px;
                padding: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid {primary_color};
            }}
            QPushButton:pressed {{
                border: 2px solid {primary_color};
                background-color: {primary_color};
            }}
            QLineEdit {{
                color: {text_color};
            }}
        """

        # 4. 테마 적용
        qdarktheme.setup_theme(
            theme=theme, 
            custom_colors=custom_colors,
            additional_qss=additional_qss
        )
        # QToggle 스타일 적용 (모든 탭의 QToggle 위젯을 여기서 한 번에 관리)
        toggle_style = f"""
            QToggle {{
                qproperty-bg_color: #777; qproperty-circle_color: #FFF;
                qproperty-active_color: {primary_color};
                qproperty-disabled_color: #CCC; qproperty-text_color: {text_color};
            }}
        """
        toggle_widgets = [
            self.video_donation_tab.noti_check_video, self.video_donation_tab.auto_video_donation_disable_set,
            self.video_donation_tab.toggle_button_auto_detect_shorts,
            self.settings_tab.theme_check,
            self.settings_tab.toggle_auto_show_img,
            self.remote_tab.video_donation_button_toggle,
            self.vote_tab.donation_vote_check, self.vote_tab.chat_vote_check, 
            self.settings_tab.auto_mission_approve, self.settings_tab.extra_donation_settings, self.settings_tab.show_donation_list_toggle,
            self.vote_tab.result_button_vote,
            self.settings_tab.kanetv8, self.pick_tab.pick_chat_read_tts, 
            self.chat_log_search_tab.moa_chat_read_tts, self.settings_tab.devmode_toggle,
            self.settings_tab.auto_notice_toggle,
            self.settings_tab.remember_window_check, self.settings_tab.remember_chat_popup_check,
            self.pick_tab.remote_duplicate_check, self.pick_tab.only_subscriber_check,
            self.settings_tab.chzzk_video_ui_toggle,
        ]
        for widget in toggle_widgets:
            if widget: # 탭이 로드되었는지 확인
                widget.setStyleSheet(toggle_style)

        # 아이콘 적용 (RemoteTab의 위젯들)
        icon_map = {
            self.remote_tab.stop_tts_button3: 'skip', self.remote_tab.control_skip_button: 'skip', 
            self.pick_tab.stop_tts_button2: 'skip', 
            self.chat_log_search_tab.stop_tts_button1: 'skip', self.remote_tab.remote_tts_skip_button: 'skip',
            self.remote_tab.control_home_button: 'rewind',
            self.remote_tab.toggle_reserve_pause_video_button: 'pause',
            self.remote_tab.chzzk_remote_pop_up_button: 'popup',
            self.remote_tab.prediction_button: 'popup', self.remote_tab.studio_popup_button: 'popup',
            self.chat_log_search_tab.studio_restriction_popup_button: 'popup', self.chat_log_search_tab.chzzk_user_profile_button: 'popup',
            self.chatroom_tab.chat_pop_up_button: 'popup',
            self.remote_tab.refresh_button: 'refresh',
            self.remote_tab.control_pause_button: 'playpause',
            self.remote_tab.remote_stop_noti_button: 'playpause',
        }
        for widget, name in icon_map.items():
            if widget:
                icon_path = resource_path(rf'.\resources\icon\{name}{icon_suffix}.png')
                widget.setIcon(QIcon(icon_path))

        # 전역 색상 변수 업데이트
        self.remote_tab.cheese_color = "#FFFF00" if is_dark_theme else "blue"
        self.remote_tab.subscribe_color = "#FFB6C1" if is_dark_theme else "purple"
        self.remote_tab.mission_color = "#90EE90" if is_dark_theme else "green"

        # 버튼 테두리 스타일 적용
        border_styles = {
            "orange": [self.remote_tab.remote_tts_skip_button, self.remote_tab.remote_stop_noti_button],
            "rgb(51, 121, 249)": [
                self.remote_tab.control_skip_button,
                self.remote_tab.control_pause_button, self.remote_tab.control_home_button,
                self.remote_tab.toggle_reserve_pause_video_button
            ],
            "red": [self.remote_tab.hide_img]
        }
        for color, widgets in border_styles.items():
            style = f"QPushButton {{ border: 2px solid {color}; }}"
            for widget in widgets:
                if widget:
                    widget.setStyleSheet(style)
        
        placeholder_style = "QLineEdit:placeholder { color: lightgray; }"
        line_edit_widgets = [
            self.chat_log_search_tab.input_box_chat_log, self.vote_tab.vote_title, self.settings_tab.file_path_box_chat_log,
            self.settings_tab.file_path_box_donation, self.chatroom_tab.input_id_box_chat
        ]
        for widget in line_edit_widgets:
            widget.setStyleSheet(placeholder_style)
        
        # 리모컨 탭 버튼 색상 갱신
        if self.remote_tab.broadcast_button.isHidden() == False: self.remote_tab.remote_buttons_color(3)
        if self.remote_tab.chzzk_remote_browser.isHidden() == False: self.remote_tab.remote_buttons_color(2)
        if self.remote_tab.image_list_cheese.isHidden() == False: self.remote_tab.remote_buttons_color(1)
        if self.remote_tab.result_box_cheese.isHidden() == False: self.remote_tab.remote_buttons_color(0)

        # 후원 목록 초기화
        self.latest_video = []
        self.latest_donation = []
        self.is_msg = False
        if is_first_launch == False: self.save_all_data()
        self.remote_tab.image_list_cheese.clear()
        self.remote_tab.result_box_cheese.clear()
        self.remote_tab.result_box_cheese_temp.clear()
        if is_first_launch == False: self.load_all_data()
        QApplication.processEvents()

    def toggle_devmode(self):
        is_checked = self.settings_tab.devmode_toggle.isChecked()
        self.chatroom_tab.test_popup_button.setVisible(is_checked)
        self.chatroom_tab.test_overlay_button.setVisible(is_checked)
        self.remote_tab.test_mission_accept_button.setVisible(is_checked)
        self.video_donation_tab.rescue_overlay_button.setVisible(is_checked)
        self.chatroom_tab.input_id_box_chat.setVisible(is_checked)

    def extra_donation_settings_func(self):
        is_checked = self.settings_tab.extra_donation_settings.isChecked()
        self.remote_tab.show_total_money_button_video.setVisible(is_checked)
    
    def show_donation_list_toggle_func(self):
        is_checked = self.settings_tab.show_donation_list_toggle.isChecked()
        self.remote_tab.donation_list_button.setVisible(is_checked)

    def load_ui_text(self):
        self.CHAT_SEARCH_BUTTON_TEXT = "부검 조이고"
        self.VIDEO_DONATION_OFF_NOTI_TEXT = "영도내림 괘씸하면 뭉추"
        if random.choice([True, False]): self.VIDEO_DONATION_OFF_NOTI_TEXT = "영도 sofla 괘씸하면 뭉추"
        self.VIDEO_DONATION_OFF_NOTI_OKTEXT = "뭉추"
        self.CHAT_LOG_TOO_MUCH_TEXT = "채팅 내역이 뭉탱이로 많습니다."
        self.VOTE_STOP_BUTTON_TEXT = "땡땡땡 자 그만"
        self.UPDATE_ABORT_TEXT = "나중에 시간날 때 할게!"

        # 이 임시 위젯은 load_settings 전에 설정을 가져오기 위해 필요
        self.kanetv8temp = QCheckBox(self)
        self.kanetv8temp.setChecked(self.settings.value('kanetv8', False, type=bool)) # 설정에서 미리 로드
        self.kanetv8temp.hide()
        
        if not self.kanetv8temp.isChecked():
            self.CHAT_SEARCH_BUTTON_TEXT = "검색"
            self.VIDEO_DONATION_OFF_NOTI_TEXT = "영도가 지정된 시간만큼 쌓였습니다."
            self.VIDEO_DONATION_OFF_NOTI_OKTEXT = "확인"
            self.CHAT_LOG_TOO_MUCH_TEXT = "채팅 내역이 매우 많습니다."
            self.VOTE_STOP_BUTTON_TEXT = "투표 마감"
            self.UPDATE_ABORT_TEXT = "지금은 안함"
    
    def disable_kanetv8_features(self):
        self.kanetv8temp = QCheckBox(self)
        self.kanetv8temp.setChecked(self.settings.value('kanetv8', False, type=bool)) # 설정에서 미리 로드
        self.kanetv8temp.hide()
        
        if not self.kanetv8temp.isChecked():
            self.remote_tab.image_list_button.hide()
            self.remote_tab.overlay_text_blank_button.hide()
            self.remote_tab.overlay_text_box.hide()
            self.remote_tab.hide_img.hide()
            self.remote_tab.overlay_text_send_button.hide()
            self.remote_tab.image_list_button.hide()
            self.settings_tab.auto_starton_close_label.hide()
            self.settings_tab.auto_delete.hide()
            self.settings_tab.toggle_auto_show_img.hide()
            self.settings_tab.donation_gif_label.hide()
            self.settings_tab.donation_gif1.hide()
            self.settings_tab.donation_gif3.hide()
            self.settings_tab.donation_gif20.hide()
            self.settings_tab.donation_gif50.hide()
            self.settings_tab.donation_gif100.hide()
            self.settings_tab.how_to_auto_show_img.hide()
            self.settings_tab.how_to_text_overlay.hide()
            self.settings_tab.bang_sel_cut.hide()
            self.settings_tab.bang_sel_cut_temp.hide()
            self.settings_tab.bang_sel_cut_text.hide()
            self.settings_tab.edit_button_bang.hide()
            self.settings_tab.file_text_donation.hide()
            self.settings_tab.file_path_box_donation.hide()
            self.settings_tab.file_button_donation.hide()
            self.settings_tab.file_open_button_donation.hide()
        
    def open_chat(self):
        url = f"https://chzzk.naver.com/live/{self.chatroom_tab.input_id_box_chat.text()}/chat"
        if self.chat_browser is None:
            self.chat_browser = PopupWindow(self.persistent_profile) 
            self.chat_browser.destroyed.connect(self.on_chat_browser_destroyed)
            self.chat_browser.resize(460, 1050)
            
            # 줌 설정 ID 부여 및 저장된 줌 불러오기
            self.chat_browser.settings_id = "chat_popup_zoom"
            settings_zoom = QSettings(os.path.join(USERPATH, "BCU", "browser_zoom.ini"), QSettings.Format.IniFormat)
            saved_zoom = float(settings_zoom.value("chat_popup_zoom", 1.0))
            self.chat_browser.browser.setZoomFactor(saved_zoom)

            parent_geo = self.geometry()
            popup_size = self.chat_browser.size()
            move_x = 1450
            move_y = 0
            self.chat_browser.move(int(move_x), int(move_y))
        self.chat_browser.setUrl(QUrl(url))
        self.chat_browser.set_title("채팅창")
        self.chat_browser.show()
        self.chat_browser.raise_()
        self.chat_browser.activateWindow()
        js_file_path = resource_path(r'.\resources\script\chatroom.js')
        with open(js_file_path, 'r', encoding='utf-8') as file:
            script = file.read()
        self.chat_browser.run_script(script)

    def open_studio_restriction(self):
        url = f"https://studio.chzzk.naver.com/{self.chatroom_tab.input_id_box_chat.text()}/blocklist"
        self.open_browser(url, 1280, 960, "치지직 스튜디오")
    
    def open_studio(self):
        url = f"https://studio.chzzk.naver.com/{self.chatroom_tab.input_id_box_chat.text()}/live"
        self.open_browser(url, 1280, 960, "치지직 스튜디오")
    
    def open_prediction(self):
        self.chatroom_tab.inject_prediction_scraper()

        # 1. chzzk_broadcast_browser가 존재하는지 확인
        if hasattr(self.remote_tab, 'chzzk_broadcast_browser') and self.remote_tab.chzzk_broadcast_browser.isVisible():
            script = """
            (function() {
                // XPath로 '승부예측' 텍스트를 가진 버튼 찾기
                const xpath = "//button[contains(., '승부예측')]";
                const matchingElement = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (matchingElement) {
                    matchingElement.click();
                    console.log("[Remote] '승부예측' 버튼 클릭됨");
                } else {
                    console.log("[Remote] '승부예측' 버튼을 찾을 수 없습니다.");
                    alert("'승부예측' 버튼을 찾을 수 없습니다. 방송 스튜디오 페이지가 맞는지 확인해주세요.");
                }
            })();
            """
            self.remote_tab.chzzk_broadcast_browser.page().runJavaScript(script)
        else:
            # 브라우저가 없거나 보이지 않으면 기존 백업 로직 (URL 열기)
            print("스튜디오 브라우저가 활성화되지 않았습니다. URL로 대체합니다.")
            url = f"https://studio.chzzk.naver.com/{self.chatroom_tab.input_id_box_chat.text()}/prediction"
            self.open_browser(url, 500, 900, "승부예측")
            if self.integrated_browser:
                self.integrated_browser.prevent_close = True
    
    def open_chzzk_user_profile(self):
        url = (f"https://chzzk.naver.com/{self.chatroom_tab.input_id_box_chat.text()}/{self.userProfileUrl}/profile/{self.user_id_chzzk_ban}")
        self.open_browser(url, 500, 500, "유저 정보")
    
    def open_chzzk_user_profile_alt(self, id):
        url = (f"https://chzzk.naver.com/{self.chatroom_tab.input_id_box_chat.text()}/{self.userProfileUrl}/profile/{id}")
        self.open_browser(url, 500, 500, "유저 정보")
    
    def open_google_login(self):
        url = "https://www.youtube.com/"
        self.open_browser(url, 800, 600, "Google 로그인")
    
    def open_browser(self, url, width, height, title):
        if self.integrated_browser is None:
            self.integrated_browser = PopupWindow(self.persistent_profile) 
            self.integrated_browser.destroyed.connect(self.on_browser_destroyed)
            self.integrated_browser.resize(width, height)
            parent_geo = self.geometry()
            popup_size = self.integrated_browser.size()
            move_x = parent_geo.x() + (parent_geo.width() - popup_size.width()) / 2
            move_y = parent_geo.y() + (parent_geo.height() - popup_size.height()) / 2
            self.integrated_browser.move(int(move_x), int(move_y))
        self.integrated_browser.setUrl(QUrl(url))
        self.integrated_browser.set_title(title)
        self.integrated_browser.show()
        self.integrated_browser.raise_()
        self.integrated_browser.activateWindow()
    
    def on_browser_destroyed(self):
        self.integrated_browser = None
    
    def on_chat_browser_destroyed(self):
        self.chat_browser = None

    # --- 오디오 (공용 TTS 서비스) ---
    def replace_only_question_marks(self, s):
        if all(char == '?' for char in s):
            return '물음표' * len(s)
        return s
    
    def download_google_tts(self, text, file_path):
        if not text.strip():
            print("오류: 텍스트가 비어있습니다.")
            return False
        
        try:
            # URL에 들어갈 텍스트를 인코딩합니다. (한글, 공백 등 처리)
            encoded_text = urllib.parse.quote(text)
            
            # 전체 URL 생성
            tts_url = f"https://www.google.com/speech-api/v1/synthesize?ie=UTF-8&lang=ko&speed=0.5&text={encoded_text}"
            
            # 헤더를 추가하여 브라우저처럼 보이게 합니다. (차단 방지)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            # GET 요청으로 MP3 데이터 요청
            response = requests.get(tts_url, headers=headers)
            
            # 요청이 성공했는지 확인
            if response.status_code == 200:
                # 응답으로 받은 바이너리(MP3) 데이터를 파일에 쓰기
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                #print(f"'{file_path}' 파일로 음성을 성공적으로 저장했습니다.")
                return True
            else:
                print(f"오류: TTS 데이터를 받아오지 못했습니다. (상태 코드: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"예외 발생: {e}")
            return False

    async def play_audio(self, chat, type):
        # --- 1단계: 변환 규칙 정의 ---
        print(chat, type)

        slang_replacements = {
            "ㄱㅇㅈㅇㄱ": "게이조이고", "ㅁㅌㅇㅇㄷ": "뭉탱이월드", "ㅁㅌㅇ": "뭉탱이", "ㅇㅇㄱㅇ": "아이고오", "ㅁㅊ": "뭉추",
            "ㅊㅁㅎㄴ?": "친목허니?", "ㅇㅇㄱㄴ": "아이고난", "ㄸㄸㅆ": "또똥싸", "ㅗㅜㅑ": "오우야",
            "ㄲㅂ": "까비", "ㅇㅎ": "아하", "ㅇㅈ": "인정", "ㄴㄴ": "노노",
            "ㄱㅅ": "감사", "ㅊㅋ": "추카", "ㅇㅋ": "오키", "ㅈㅅㅎㄴㄷ": "죄송합니다", "ㄱㅇㅇ": "귀여워",
        }

        for old, new in slang_replacements.items():
            chat = chat.replace(old, new)

        # 스티커/이모티콘 코드 제거 (낱자 변환 전에 수행)
        chat = re.sub(r'\{:.*?:\}', '', chat)
        chat = self.replace_only_question_marks(chat)

        os.makedirs(os.path.join(USERPATH, "BCU", "TTS"), exist_ok=True)
        audio = os.path.join(USERPATH, "BCU", "tts.mp3")
        self.download_google_tts(chat, audio)

        pygame.mixer.init()

        self.play_thread = threading.Thread(target=self._play_sound, args=(audio, type,))
        self.play_thread.start()

        while self.play_thread.is_alive():
            if self.stop_audio_event.is_set():
                self._stop_playback()
                break

        self.play_thread.join()  # 스레드가 끝날 때까지 기다림

        pygame.mixer.quit()

        if os.path.exists(audio):
            os.remove(audio)

    def run_tts_preview(self, text):
        """TTS 미리듣기 실행"""
        if self.is_audio_playing:
            return

        def _preview():
            try:
                os.makedirs(os.path.join(USERPATH, "BCU", "TTS"), exist_ok=True)
                audio_path = os.path.join(USERPATH, "BCU", "tts_preview.mp3")
                
                # 기존 TTS 다운로드 로직 재사용
                self.download_google_tts(text, audio_path)
                
                if os.path.exists(audio_path):
                    pygame.mixer.init()
                    pygame.mixer.music.load(audio_path)
                    
                    # 음량 설정 (설정 탭의 슬라이더 값 사용)
                    volume_level = self.settings_tab.mission_volume_tts.value() / 100.0
                    pygame.mixer.music.set_volume(volume_level)
                    
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                    
                    pygame.mixer.music.unload()
                    os.remove(audio_path)
            except Exception as e:
                print(f"TTS 미리듣기 실패: {e}")

        threading.Thread(target=_preview, daemon=True).start()

    def _play_sound(self, audio, type):
        try:
            pygame.mixer.music.load(audio)
            if type == 0:
                volumenum = self.pick_tab.volume_tts.value()/100
            elif type == 1:
                volumenum = self.chat_log_search_tab.moa_volume_tts.value()/100
            else:
                volumenum = self.settings_tab.mission_volume_tts.value()/100
            print(volumenum)
            pygame.mixer.music.set_volume(volumenum)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if self.stop_audio_event.is_set():
                    pygame.mixer.music.stop()
                    break
        except Exception as e:
            None

    def _stop_playback(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    
    def stop_tts(self):
        try:
            if self.audio_thread and self.audio_thread.is_alive():
                self.stop_audio_event.set()
                self.audio_thread.join()
            self.stop_audio_event.clear()
        except:
            pass
    
    def login_reset(self):
        reply = QMessageBox.question(self, '경고', '모든 네이버 로그인 정보 및 API 인증 토큰을 초기화하시겠습니까?', 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.is_login = False
            # QWebEngineProfile의 쿠키 저장소 비우기
            if hasattr(self.chatroom_tab, 'login_browser'):
                self.chatroom_tab.login_browser.page().profile().cookieStore().deleteAllCookies()
                self.chatroom_tab.login_browser.setUrl(QUrl("about:blank"))
            if hasattr(self.remote_tab, 'chzzk_remote_browser'):
                 self.remote_tab.chzzk_remote_browser.page().profile().cookieStore().deleteAllCookies()
                 self.remote_tab.chzzk_remote_browser.setUrl(QUrl("about:blank"))
            if hasattr(self.remote_tab, 'chzzk_broadcast_browser'):
                 self.remote_tab.chzzk_broadcast_browser.page().profile().cookieStore().deleteAllCookies()
                 self.remote_tab.chzzk_broadcast_browser.setUrl(QUrl("about:blank"))

            # 공식 API 토큰 파일(auth.json) 삭제
            if os.path.exists(AUTH_FILE_PATH):
                try:
                    os.remove(AUTH_FILE_PATH)
                    self.chatroom_tab.result_box_chat.append("✅ 공식 API 인증 토큰(auth.json)이 삭제되었습니다.")
                except Exception as e:
                    self.chatroom_tab.result_box_chat.append(f"❗ auth.json 삭제 실패: {e}")

            self.chatroom_tab.result_box_chat.append("로그인 정보가 초기화되었습니다. 채팅창 접속 버튼을 다시 눌러 인증을 진행하세요.")
    
    def start_timer_main(self):
        QApplication.processEvents()
        self.chat_log_search_tab.chat_moa()
        self.timer_chat_moa = QTimer(self)
        self.timer_chat_moa.timeout.connect(self.chat_log_search_tab.chat_moa)
        self.timer_chat_moa.start(1000)
        self.timer_live_detail_check = QTimer(self)
        self.timer_live_detail_check.timeout.connect(self.remote_tab.check_live_detail)
        self.timer_live_detail_check.start(1000)
        self.timer_saving_data = QTimer(self)
        self.timer_saving_data.timeout.connect(self.save_all_data)
        self.timer_saving_data.start(1000)
    
    def save_all_data(self):
        data = {}

        filename = "donation_data.json"
        path = os.path.join(USERPATH, "BCU", filename)

        full_html_cheese = self.remote_tab.result_box_cheese.toHtml()
        html_items_cheese = full_html_cheese.split("<hr />")
        data['result_box_cheese'] = [item.strip() for item in html_items_cheese if item.strip()]

        full_html_video = self.result_box_video.toHtml()
        html_items_video = full_html_video.split("<hr />")
        data['result_box_video'] = [item.strip() for item in html_items_video if item.strip()]
        data['chat_count_label_video'] = self.chat_count_label_video.text()
        data['len_count_label_video_open_timer'] = self.len_count_label_video_open_timer.text()
        data['len_count_label_video'] = self.len_count_label_video.text()
        
        list_items_to_save = []
        for i in range(self.remote_tab.image_list_cheese.count()):
            item = self.remote_tab.image_list_cheese.item(i)
            item_data = item.data(Qt.ItemDataRole.UserRole)  # 아이템에 저장된 딕셔너리를 직접 가져옴
            if item_data:  # 데이터가 있는 경우에만 추가
                list_items_to_save.append(item_data)
        data['image_list_cheese'] = list_items_to_save
        data['last_saved_timestamp'] = datetime.now().isoformat()

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            None

    # --- 초기화, 저장, 종료 (Application Lifecycle) ---
    def load_tab_settings(self):
        """ini 파일에서 탭 순서와 표시 여부를 불러옵니다."""
        self.tabs.clear()
        saved_order = self.settings.value("Tabs/Order", self.tab_order, type=list)
        hidden_tabs = self.settings.value("Tabs/Hidden", [], type=list)
        
        current_tabs_set = set(self.tab_widgets.keys())
        saved_order_set = set(saved_order)
        
        new_tabs = list(current_tabs_set - saved_order_set)
        final_order = [name for name in saved_order if name in current_tabs_set] + new_tabs
        
        self.tab_order = final_order

        for tab_name in self.tab_order:
            if tab_name not in hidden_tabs:
                widget = self.tab_widgets.get(tab_name)
                if widget:
                    self.tabs.addTab(widget, tab_name)

    def initialize(self):
        settings = self.settings
        try:
            os.makedirs(os.path.dirname(self.settings_tab.file_path_box_chat_log.text() + os.sep), exist_ok=True)
            if self.kanetv8temp.isChecked():
                os.makedirs(os.path.dirname(self.settings_tab.file_path_box_donation.text() + os.sep), exist_ok=True)
        except Exception as e:
            self.settings_tab.file_path_box_chat_log.setText(os.path.join(USERPATH, "BCU", "logs"))
            self.settings_tab.file_path_box_donation.setText(os.path.join(USERPATH, "BCU", "donationimg"))
            os.makedirs(os.path.dirname(self.settings_tab.file_path_box_chat_log.text() + os.sep), exist_ok=True)
            if self.kanetv8temp.isChecked():
                os.makedirs(os.path.dirname(self.settings_tab.file_path_box_donation.text() + os.sep), exist_ok=True)

        self.settings_tab.load_settings_from_main() # SettingsTab에 반영
                
        # --- 창 위치 및 크기 복원 ---

        if settings.value("remember_window_check", True):
            self.saved_window_size = settings.value("windowSize", QSize(600, 600))
            self.saved_window_position = settings.value("windowPosition", QPoint(100, 100))
            self.resize(self.saved_window_size)
            self.move(self.saved_window_position)
        else:
             # 기본값 또는 현재 값 유지
             self.saved_window_position = QPoint(100, 100) # __init__에서 사용됨
             
        self.move_essential_files()
        self.update_html()

        if self.settings_tab.auto_chatroom_connector_start.isChecked():
            self.chatroom_tab.toggle_button_chat.click()
        
        if self.settings_tab.auto_start_chzzk_overlay.isChecked():
            QTimer.singleShot(1000, self.video_donation_tab.open_overlay_only)
    
        # UI 초기 상태 적용
        self.theme_change(True)
        self.toggle_devmode()
        self.remote_tab.video_donation_button_func()
        self.extra_donation_settings_func()
        self.show_donation_list_toggle_func()
        
        self.start_timer_main()
        QApplication.processEvents()
        
        # (브라우저 URL 초기 로드)
        self.remote_tab.refresh_browsers()
        if self.startup_tab_combobox.currentText() == "채팅창":
            self.tabs.setCurrentIndex(0)
        else:
            self.tabs.setCurrentIndex(1)


    def load_settings(self):
        """
        [중요] 
        이 메서드는 원본과 거의 동일하게, 메인 윈도우의 임시 위젯 속성들을 로드합니다.
        그런 다음, 각 탭의 `load_settings_from_main()` 메서드가
        이 임시 속성들을 가져가서 자신의 UI에 적용하고, 메인 윈도우의 참조를 
        자신의 위젯으로 '교체'합니다. (settings_tab.py의 __init__ 끝부분 참조)
        """
        settings = self.settings
        
        # 임시 위젯 생성 및 값 로드
        self.file_path_box_chat_log = QLineEdit(settings.value('file_path_box_chat_log', os.path.join(USERPATH, "BCU", "logs")))
        self.file_path_box_donation = QLineEdit(settings.value('file_path_box_donation', os.path.join(USERPATH, "BCU", "donationimg")))
        self.input_num_box_chat_log = QLineEdit(settings.value('input_num_box_chat_log', '1000'))
        self.donation_img_cut = QLabel(settings.value('donation_img_cut', '10000'))
        self.sub_gift_cut = QLabel(settings.value('sub_gift_cut', '10'))
        self.video_price = QLabel(settings.value('video_price', '100'))
        self.bang_sel_cut = QLabel(settings.value('bang_sel_cut', '200000'))
        self.input_id_box_chat = QLineEdit(settings.value('input_id_box_chat', '')) # 이건 chatroom_tab이 가져감
        self.input_num_box_video = QSpinBox()
        self.input_num_box_video.setValue(int(settings.value('input_num_box_video', 60)))
        self.video_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.video_volume_slider.setValue(int(settings.value('video_volume_slider', 50)))
        self.volume_tts = QSlider(Qt.Orientation.Horizontal)
        self.volume_tts.setValue(int(settings.value('volume_tts', 50)))
        self.moa_volume_tts = QSlider(Qt.Orientation.Horizontal)
        self.moa_volume_tts.setValue(int(settings.value('moa_volume_tts', 50)))
        self.mission_volume_tts = QSlider(Qt.Orientation.Horizontal)
        self.mission_volume_tts.setValue(int(settings.value('mission_volume_tts', 50)))
        self.mission_delay_tts = QDoubleSpinBox()
        self.mission_delay_tts.setValue(float(settings.value('mission_delay_tts', 1.0)))
        self.commision_rate = QDoubleSpinBox()
        self.commision_rate.setValue(float(settings.value('commision_rate', 30)))
        self.startup_tab_combobox = QComboBox()
        self.startup_tab_combobox.addItems(["리모컨", "채팅창"])
        self.startup_tab_combobox.setCurrentText(settings.value('startup_tab_combobox', '리모컨'))

        self.overlay_alignment_combobox = QComboBox()
        self.overlay_alignment_combobox.addItems(["가운데", "왼쪽", "오른쪽"])
        # 저장된 텍스트 불러오기 (기본값 설정)
        # load_settings 시점에서는 self.overlay_alignment 변수 자체도 업데이트 해주는 것이 좋음
        saved_alignment_text = settings.value('overlay_alignment_combobox', '가운데')
        self.overlay_alignment_combobox.setCurrentText(saved_alignment_text)
        
        # 텍스트 -> 값 매핑
        alignment_map = {
            "가운데": "center",
            "왼쪽": "left",
            "오른쪽": "right"
        }
        self.overlay_alignment = alignment_map.get(saved_alignment_text, "center")
        
        # (모든 QToggle, QCheckBox, QComboBox에 대해 동일한 작업 수행)
        self.toggle_auto_show_img = QToggle()
        self.toggle_auto_show_img.setChecked(settings.value('toggle_auto_show_img', False, type=bool))
        self.noti_sound_video = QCheckBox()
        self.noti_sound_video.setChecked(settings.value('noti_sound_video', False, type=bool))
        self.auto_chat_popup_start = QCheckBox()
        self.auto_chat_popup_start.setChecked(settings.value('auto_chat_popup_start', False, type=bool))
        self.auto_start_chzzk_overlay = QCheckBox()
        self.auto_start_chzzk_overlay.setChecked(settings.value('auto_start_chzzk_overlay', False, type=bool))
        self.search_chat_all = QCheckBox()
        self.search_chat_all.setChecked(settings.value('search_chat_all', False, type=bool))
        self.search_chat_partial = QCheckBox()
        self.search_chat_partial.setChecked(settings.value('search_chat_partial', True, type=bool))
        self.ignore_space_check = QCheckBox()
        self.ignore_space_check.setChecked(settings.value('ignore_space_check', True, type=bool))
        self.auto_chatroom_connector_start = QCheckBox()
        self.auto_chatroom_connector_start.setChecked(settings.value('auto_chatroom_connector_start', False, type=bool))
        self.auto_delete = QCheckBox()
        self.auto_delete.setChecked(settings.value('auto_delete', True, type=bool))
        self.auto_starton_close_label = QLabel()
        self.pick_chat_read_tts = QToggle()
        self.pick_chat_read_tts.setChecked(settings.value('pick_chat_read_tts', True, type=bool))
        self.moa_chat_read_tts = QToggle()
        self.moa_chat_read_tts.setChecked(settings.value('moa_chat_read_tts', True, type=bool))
        self.mission_read_req_tts = QCheckBox()
        self.mission_read_req_tts.setChecked(settings.value('mission_read_req_tts', False, type=bool))
        self.mission_read_add_tts = QCheckBox()
        self.mission_read_add_tts.setChecked(settings.value('mission_read_add_tts', False, type=bool))
        self.mission_read_success_tts = QCheckBox()
        self.mission_read_success_tts.setChecked(settings.value('mission_read_success_tts', False, type=bool))
        self.mission_read_fail_tts = QCheckBox()
        self.mission_read_fail_tts.setChecked(settings.value('mission_read_fail_tts', False, type=bool))
        self.theme_check = QToggle()
        self.theme_check.setChecked(settings.value('theme_check', False, type=bool))
        self.auto_mission_approve = QToggle()
        self.auto_mission_approve.setChecked(settings.value('auto_mission_approve', False, type=bool))
        self.user_count_visible = settings.value('user_count_visible', True, type=bool)
        self.video_donation_button_toggle = QToggle()
        self.video_donation_button_toggle.setChecked(settings.value('video_donation_button_toggle', True, type=bool))
        self.donation_gif1 = QCheckBox()
        self.donation_gif1.setChecked(settings.value('donation_gif1', True, type=bool))
        self.donation_gif3 = QCheckBox()
        self.donation_gif3.setChecked(settings.value('donation_gif3', True, type=bool))
        self.donation_gif20 = QCheckBox()
        self.donation_gif20.setChecked(settings.value('donation_gif20', True, type=bool))
        self.donation_gif50 = QCheckBox()
        self.donation_gif50.setChecked(settings.value('donation_gif50', True, type=bool))
        self.donation_gif100 = QCheckBox()
        self.donation_gif100.setChecked(settings.value('donation_gif100', True, type=bool))
        self.is_video_donation_first_time2 = settings.value('is_video_donation_first_time2', True, type=bool)
        self.toggle_button_auto_detect_shorts = QToggle()
        self.toggle_button_auto_detect_shorts.setChecked(settings.value('toggle_button_auto_detect_shorts', False, type=bool))
        self.extra_donation_settings = QToggle()
        self.extra_donation_settings.setChecked(settings.value('extra_donation_settings', False, type=bool))
        self.show_donation_list_toggle = QToggle()
        self.show_donation_list_toggle.setChecked(settings.value('show_donation_list_toggle', True, type=bool))
        self.devmode_toggle = QToggle()
        self.devmode_toggle.setChecked(settings.value('devmode_toggle', type=bool))
        self.auto_notice_toggle = QToggle()
        self.auto_notice_toggle.setChecked(settings.value('auto_notice_toggle', type=bool))
        self.auto_notice_textbox = QLineEdit(settings.value('auto_notice_textbox', type=str))
        self.is_first_time_using1 = settings.value('is_first_time_using1', True, type=bool)
        self.is_login = settings.value('is_login', False, type=bool)
        self.noti_check_video = QToggle()
        self.noti_check_video.setChecked(settings.value('noti_check_video', False, type=bool))
        self.youtube_api_key = QLineEdit(settings.value('youtube_api_key', type=str))
        self.chzzk_video_url = QLineEdit(settings.value('chzzk_video_url', type=str))
        self.chzzk_api_client_id = QLineEdit(settings.value('chzzk_api_client_id', type=str))
        self.chzzk_api_client_secret = QLineEdit(settings.value('chzzk_api_client_secret', type=str))
        self.chzzk_video_ui_toggle = QToggle()
        self.chzzk_video_ui_toggle.setChecked(settings.value('chzzk_video_ui_toggle', False, type=bool))
        self.userProfileUrl = settings.value('userProfileUrl', type=str)
        self.remember_window_check.setChecked(settings.value('remember_window_check', True, type=bool))
        self.remember_chat_popup_check.setChecked(settings.value('remember_chat_popup_check', True, type=bool))
        self.remote_duplicate_check.setChecked(settings.value('remote_duplicate_check', False, type=bool))
        self.only_subscriber_check.setChecked(settings.value('only_subscriber_check', False, type=bool))


    def move_essential_files(self):
        if self.kanetv8temp.isChecked():
            shutil.copy(resource_path(r'.\resources\img\cheese_10000.gif'), os.path.join(self.file_path_box_donation.text(), "10000.gif"))
            shutil.copy(resource_path(r'.\resources\img\cheese_30000.gif'), os.path.join(self.file_path_box_donation.text(), "30000.gif"))
            shutil.copy(resource_path(r'.\resources\img\cheese_200000.gif'), os.path.join(self.file_path_box_donation.text(), "200000.gif"))
            shutil.copy(resource_path(r'.\resources\img\cheese_500000.gif'), os.path.join(self.file_path_box_donation.text(), "500000.gif"))
            shutil.copy(resource_path(r'.\resources\img\cheese_1000000.gif'), os.path.join(self.file_path_box_donation.text(), "1000000.gif"))

    def update_html(self):
        """
        템플릿 폴더의 HTML 파일들을 읽어와
        지정된 경로에 생성(복사)합니다.
        """
        if not self.kanetv8temp.isChecked(): return
        template_dir = r'.\resources\templates'
        output_dir = os.path.join(USERPATH, "BCU")

        files_to_process = [
            ("donationimg_template.html", "donationimg.html"),
            ("ydText_template.html", "ydText.html")
        ]
        try:
            os.makedirs(output_dir, exist_ok=True)

            for template_name, output_name in files_to_process:
                source_path = resource_path(os.path.join(template_dir, template_name))
                destination_path = os.path.join(output_dir, output_name)
                shutil.copyfile(source_path, destination_path)

        except FileNotFoundError as e:
            print(f"오류: 템플릿 파일을 찾을 수 없습니다. '{template_dir}' 폴더를 확인하세요. - {e}")
        except Exception as e:
            print(f"HTML 파일 생성 중 오류가 발생했습니다: {e}")

    def on_later_button_click(self):
        self.close_main_window = True
        self.is_first_time_using1 = True
    
    def load_set_color(self, html_content):
        is_dark_theme = self.settings_tab.theme_check.isChecked()
        color_map = [
            ('blue', '#FFFF00'),
            ('purple', '#FFB6C1'),
            ('green', '#90EE90'),
            ('#0000ff', '#ffff00'),
            ('#800080', '#ffb6c1'),
            ('#008000', '#90ee90')
        ]
        for light_color, dark_color in color_map:
            if is_dark_theme:
                html_content = html_content.replace(f"color: {light_color}", f"color: {dark_color}")
                html_content = html_content.replace(f"color:{light_color}", f"color:{dark_color}")
            else:
                html_content = html_content.replace(f"color: {dark_color}", f"color: {light_color}")
                html_content = html_content.replace(f"color:{dark_color}", f"color:{light_color}")
        return html_content

    def load_all_data(self):
        # (원본 코드와 동일, remote_tab, video_donation_tab의 위젯 참조)
        filename = "donation_data.json"
        path = os.path.join(USERPATH, "BCU", filename)

        if not os.path.exists(path):
            print(f"'{path}' 파일이 존재하지 않습니다.")
            return
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            last_saved_timestamp_str = data.get('last_saved_timestamp')
            if not last_saved_timestamp_str:
                print("저장된 시각 정보가 없습니다.")
                return

            last_saved_time = datetime.fromisoformat(last_saved_timestamp_str)
            time_difference = datetime.now() - last_saved_time
            cheese_data = data.get('result_box_cheese', [])
            top_100_items = cheese_data[:100]
            html_content = self.load_set_color("<hr style='line-height: 75%;'>".join(top_100_items))
            self.remote_tab.result_box_cheese.setHtml(html_content)

            list_data = data.get('image_list_cheese', [])
            self.remote_tab.image_list_cheese.clear()

            for item_data in list_data[:30]:
                item_type = item_data.get('type')
                brush = QBrush(QColor(0, 0, 0, 0))

                if item_type == 'donation':
                    file_path = item_data['file_path']
                    widget = LabelButtonWidget(self.load_set_color(item_data['formatted_text']), file_path, item_data['amount_path'], False, self)
                    item = QListWidgetItem(QIcon(file_path), item_data['item_text'])
                    item.setForeground(brush)
                    item.setData(Qt.ItemDataRole.UserRole, item_data)
                    self.remote_tab.image_list_cheese.addItem(item)
                    self.remote_tab.image_list_cheese.setItemWidget(item, widget)

                elif item_type == 'button':
                    nick = item_data['nick']
                    user_id = item_data['id']
                    btn = QPushButton(f'{nick}의 채널로 가기', self)
                    btn.clicked.connect(lambda checked, uid=user_id: self.remote_tab.open_channel_link(uid))
                    timestamp_prefix = os.path.basename(item_data['file_path']).split(']')[0][1:]
                    btn_item_text = f"[{timestamp_prefix}] 0\n{nick} 님이 {item_data['donation_type']} {int(item_data['cheese']):,}개 선물"
                    item = QListWidgetItem(btn_item_text)
                    item.setForeground(brush)
                    item.setData(Qt.ItemDataRole.UserRole, item_data)
                    self.remote_tab.image_list_cheese.addItem(item)
                    self.remote_tab.image_list_cheese.setItemWidget(item, btn)

            self.remote_tab.image_list_cheese.sortItems(Qt.SortOrder.DescendingOrder)

            if time_difference.total_seconds() < 12 * 3600:
                self.chat_count_label_video.setText(data.get('chat_count_label_video', ''))
                self.len_count_label_video_open_timer.setText(data.get('len_count_label_video_open_timer', ''))
                self.len_count_label_video.setText(data.get('len_count_label_video', ''))
                
                video_data = data.get('result_box_video', [])
                video_html_content = "<hr style='line-height: 75%;'>".join(video_data)
                self.result_box_video.setHtml(video_html_content)
                print(f"모든 데이터가 성공적으로 불러와졌습니다. 마지막 저장 시각: {last_saved_time}")
                self.video_donation_tab.start_timer_video()
            else:
                print(f"마지막 저장 시각({last_saved_time})이 현재 시각으로부터 12시간 이상 경과하여 일부 데이터는 불러오지 않습니다.")
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"파일 불러오기 중 오류가 발생했습니다: {e}")

    def delete_donation_img(self):
        # (원본 코드와 동일, settings_tab의 file_path_box_donation 참조)
        folder = self.file_path_box_donation.text()
        if not os.path.isdir(folder):
            print(f"오류: '{folder}' 폴더를 찾을 수 없습니다.")
            return
        donation_files = []
        pattern = re.compile(r'^\[\d{8} \d{6}\].*')

        for file_name in os.listdir(folder):
            if pattern.match(file_name):
                file_path = os.path.join(folder, file_name)
                if os.path.isfile(file_path):
                    donation_files.append(file_path)
        donation_files.sort()
        files_to_delete = []
        if len(donation_files) > 60: files_to_delete = donation_files[:-60]
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                deleted_count += 1
            except OSError as e:
                print(f"파일 삭제 오류 '{file_path}': {e}")
        if deleted_count > 0:
            print(f"오래된 왕도네 이미지 {deleted_count}개를 삭제했습니다.")
        else:
            print("삭제할 오래된 왕도네 이미지가 없습니다.")
        special_file_path = os.path.join(folder, "donationimg.png")
        if os.path.isfile(special_file_path):
            try:
                os.remove(special_file_path)
                print("'donationimg.png' 파일을 삭제했습니다.")
            except OSError as e:
                print(f"'donationimg.png' 파일 삭제 오류: {e}")
            
    def delete_tts_file(self):
        folder = os.path.join(USERPATH, "BCU", "TTS")
        if os.path.exists(folder):
            for file_name in os.listdir(folder):
                file_path = os.path.join(folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)

    def save_tab_settings(self):
        """현재 탭 순서와 표시 여부를 ini 파일에 저장합니다."""
        # 현재 표시된 탭들의 순서
        current_order = [self.tabs.tabText(i) for i in range(self.tabs.count())]
        
        # 숨겨진 탭들 찾기
        visible_tabs = set(current_order)
        hidden_tabs = [name for name in self.tab_order if name not in visible_tabs]
        
        self.settings.setValue("Tabs/Order", self.tab_order)
        self.settings.setValue("Tabs/Hidden", hidden_tabs)

    def closeEvent(self, event):
        try:
            if hasattr(self, 'audio_thread') and self.audio_thread and self.audio_thread.is_alive():
                self.stop_audio_event.set()
                self.audio_thread.join()
                self.stop_audio_event.clear()
        except Exception as e:
            print(f"오디오 스레드 종료 중 에러 발생: {e}")

        dialog_locations = [
            (self.remote_tab, 'show_total_money_dialog'),
            (self.settings_tab, 'about_dialog'),
            (self.settings_tab, 'how_to_auto_show_img_dialog'),
            (self.settings_tab, 'how_to_text_overlay_dialog'),
            (self.settings_tab, 'initial_setup_guide'),
            (self.settings_tab, 'ban_dialog'),
            (self.vote_tab, 'voting_result_window'),
            (self.chatroom_tab, 'test_popup'),
            (self, 'integrated_browser'),
            (self, 'chat_browser'),
            (self.video_donation_tab, 'preview_window')
        ]

        for parent, name in dialog_locations:
            if hasattr(parent, name):
                dialog = getattr(parent, name)
                if dialog is not None:
                    try:
                        dialog.close()
                    except Exception as e:
                        print(f"'{name}' 위젯을(를) 닫는 중 에러 발생: {e}")

        # --- Stop Chatroom Connector ---
        if self.chatroom_connector_instance:
             print("Stopping chatroom connector before closing...")
             self.chatroom_connector_instance.stop()
             if self.chatroom_connector_instance.async_worker:
                  self.chatroom_connector_instance.async_worker.wait(2000)

        if hasattr(self.chat_log_search_tab, 'chat_counter_window') and self.chat_log_search_tab.chat_counter_window:
            self.chat_log_search_tab.chat_counter_window.force_close = True
            self.chat_log_search_tab.chat_counter_window.close()
            
        if hasattr(self.video_donation_tab, 'overlay') and self.video_donation_tab.overlay:
            self.video_donation_tab.overlay.close()
            
        if hasattr(self.video_donation_tab, 'preview_window') and self.video_donation_tab.preview_window:
            self.video_donation_tab.preview_window.force_close = True
            self.video_donation_tab.preview_window.close()
        
        if self.is_close_without_save_setting == False:
            self.save_settings()
        
        if self.settings_tab.auto_delete.isChecked():
            self.delete_donation_img()
        self.delete_tts_file()

        event.accept()
    
    def save_settings(self):
        settings = self.settings
        settings.clear()
        self.save_tab_settings()
        
        # settings_tab에 있는 위젯들
        settings_tab_widgets = [
            'file_path_box_donation', 'file_path_box_chat_log', 'donation_img_cut',
            'sub_gift_cut', 'video_price', 'bang_sel_cut',
            'mission_delay_tts', 'commision_rate',
            'toggle_auto_show_img', 'auto_chat_popup_start', 'auto_start_chzzk_overlay',
            'auto_chatroom_connector_start', 'auto_delete',
            'kanetv8', 'mission_read_req_tts', 'mission_read_add_tts', 'mission_read_success_tts', 
            'mission_read_fail_tts', 'theme_check', 'auto_mission_approve',
            'donation_gif1', 'donation_gif3', 'donation_gif20', 'donation_gif50', 'donation_gif100', 
            'extra_donation_settings', 'devmode_toggle', 'show_donation_list_toggle',
            'auto_notice_toggle', 'auto_notice_textbox', 'youtube_api_key', 'chzzk_video_url',
            'chzzk_api_client_id', 'chzzk_api_client_secret', 'startup_tab_combobox', 'overlay_alignment_combobox',
            'remember_window_check', 'chzzk_video_ui_toggle'
        ]
        
        # chat_log_search_tab 위젯들
        chat_log_tab_widgets = ['input_num_box_chat_log', 'search_chat_all', 'search_chat_partial', 'ignore_space_check', 'moa_chat_read_tts']
        
        # pick_tab 위젯들
        pick_tab_widgets = ['pick_chat_read_tts', 'remote_duplicate_check', 'only_subscriber_check']
        
        # video_donation_tab 위젯들
        video_donation_tab_widgets = ['input_num_box_video', 'toggle_button_auto_detect_shorts', 'noti_sound_video', 'video_volume_slider']

        # remote_tab 위젯들
        remote_tab_widgets = ['video_donation_button_toggle']

        # chatroom_tab 위젯들
        chatroom_tab_widgets = ['input_id_box_chat']
        
        # 각 탭의 위젯에서 값을 가져와 저장
        all_widgets_map = {
            'settings_tab': (self.settings_tab, settings_tab_widgets),
            'chat_log_search_tab': (self.chat_log_search_tab, chat_log_tab_widgets),
            'pick_tab': (self.pick_tab, pick_tab_widgets),
            'video_donation_tab': (self.video_donation_tab, video_donation_tab_widgets),
            'remote_tab': (self.remote_tab, remote_tab_widgets),
            'chatroom_tab': (self.chatroom_tab, chatroom_tab_widgets)
        }

        for tab_name, (tab_instance, widget_names) in all_widgets_map.items():
            for name in widget_names:
                try:
                    widget = getattr(tab_instance, name)
                    value = None
                    if isinstance(widget, (QLineEdit, QTextEdit, QLabel)):
                        value = widget.text()
                        if name == 'chzzk_video_url':
                            value = value.strip().replace(" ","")
                    elif isinstance(widget, QComboBox):
                        value = widget.currentText()
                    elif isinstance(widget, (QSpinBox, QDoubleSpinBox, QSlider)):
                        value = widget.value()
                    elif isinstance(widget, (QCheckBox, QToggle)): # QToggle 포함
                        value = widget.isChecked()
                    else:
                        print(f"경고: '{name}' 위젯 처리 방법이 정의되지 않음 (종류: {type(widget)})")
                        continue
                    settings.setValue(name, value)
                except Exception as e:
                    print(f"설정 저장 오류 '{name}': {e}")
        
        # 슬라이더 값 별도 저장
        settings.setValue('volume_tts', int(self.pick_tab.volume_tts.value()))
        settings.setValue('moa_volume_tts', int(self.chat_log_search_tab.moa_volume_tts.value()))
        settings.setValue('mission_volume_tts', int(self.settings_tab.mission_volume_tts.value()))
        
        # 기타 전역 변수
        settings.setValue('is_first_time_using1', self.is_first_time_using1)
        settings.setValue('is_login', self.is_login)
        settings.setValue('is_video_donation_first_time2', self.is_video_donation_first_time2)
        
        if self.settings_tab.remember_window_check.isChecked():
            settings.setValue("windowSize", self.size())
            settings.setValue("windowPosition", self.pos())
        else:
            settings.remove("windowSize")
            settings.remove("windowPosition")
        settings.setValue("user_count_visible", self.remote_tab.user_count_visible)
        settings.setValue("userProfileUrl", self.userProfileUrl)

    # --- 밴 로직 (공용) ---
    def manager(self, type, cnt, time):
        if not self.user_id_chzzk_ban:
            QMessageBox.critical(self, '경고', '채팅부검 탭에서 유저를 먼저 검색해주세요.')
            return
        # chat_log_search_tab에서 ID/Nick 가져오기
        user_id_to_ban = self.user_id_chzzk_ban
        user_nick_to_ban = self.user_nick_chzzk_ban

        if not user_id_to_ban:
            QMessageBox.critical(self, '경고', '채팅부검 탭에서 유저를 먼저 검색해주세요.')
            return

        if type == "임시 제한":
            QMessageBox.warning(self, '알림', '치지직 공식 API는 임시 제한 기능을 지원하지 않습니다.\n영구 제한 또는 스튜디오를 이용해주세요.')
            
        elif type == "활동 제한":
            duration_text = self.chat_log_search_tab.temp_ban_duration_combo_box.currentText()
            if duration_text != "영구":
                 QMessageBox.warning(self, '알림', '치지직 공식 API는 영구 활동 제한만 지원합니다.\n기간제 활동 제한은 스튜디오를 이용해주세요.')
                 return
            
            reply = QMessageBox.question(self, '경고', f'{user_nick_to_ban}님을 영구 활동 제한 하시겠습니까?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if self.chatroom_connector_instance:
                    self.chatroom_connector_instance.ban_user(user_id_to_ban, user_nick_to_ban, "permanent", reason="")
                    self.chat_log_search_tab.ban_button_cm.setText("활동 제한 완료!")
                    QTimer.singleShot(2000, lambda: self.chat_log_search_tab.ban_button_cm.setText("활동 제한"))
    
    def update_overlay_alignment(self, alignment):
        """설정 탭에서 오버레이 정렬이 변경되었을 때 호출"""
        self.overlay_alignment = alignment
        # 현재 열려있는 오버레이가 있다면 즉시 적용
        if self.video_donation_tab.overlay:
            self.video_donation_tab.overlay.set_alignment(alignment)