import os
import webbrowser
import pyautogui
import requests
import re
import traceback
import sys
import asyncio
import threading
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QLabel, QFrame, QSizePolicy, QTextEdit, QDialog, QApplication, QListWidgetItem, QSlider)
from PyQt6.QtGui import QFont, QIcon, QBrush, QColor
from PyQt6.QtCore import QUrl, QSize, pyqtSlot, QTimer, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile

from app.constants import GLOBALFONTSIZE, startupTime
from app.resources import resource_path
from app.ui_widgets import QToggle, CustomWebEnginePage, QListWidgetDonationImg, LabelButtonWidget
from app.ui_dialogs import ChzzkRemotePopupWindow, RemoteBanDialog, ShowTotalMoneyDialog
from app.ui_preview import OverlayPreviewWindow
from datetime import datetime

class RemoteTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        
        self.main_window = main_window

        self.video_tab = self.main_window.video_donation_tab

        self.auto_displayed_images = set()
        self.cheese_color = "blue"
        self.subscribe_color = "purple"
        self.mission_color = "green"

        layout = QVBoxLayout()
        live_layout = QHBoxLayout()

        self.chat_connection_status = QLineEdit('채팅창: 🔴연결 안 됨')
        self.chat_connection_status.setFixedWidth(180)
        self.chat_connection_status.setFixedHeight(30)
        self.chat_connection_status.setReadOnly(True)
        self.chat_connection_status.hide()
        live_layout.addWidget(self.chat_connection_status)

        self.video_donation_button_toggle = QToggle(self)
        self.video_donation_button_toggle.setText("영도 리모컨 표시")
        self.video_donation_button_toggle.clicked.connect(self.video_donation_button_func)
        live_layout.addWidget(self.video_donation_button_toggle)

        self.uptime = QLineEdit('업타임 ')
        self.uptime.setFixedWidth(150)
        self.uptime.setFixedHeight(30)
        self.uptime.setReadOnly(True)
        live_layout.addWidget(self.uptime)

        self.user_count_visible = self.main_window.user_count_visible

        self.user_count = QLineEdit('시청자 ')
        self.user_count.setFixedWidth(150)
        self.user_count.setFixedHeight(30)
        self.user_count.setReadOnly(True)
        live_layout.addWidget(self.user_count)

        self.user_count_alt = QLineEdit('시청자 [숨겨짐]')
        self.user_count_alt.setFixedWidth(150)
        self.user_count_alt.setFixedHeight(30)
        self.user_count_alt.setReadOnly(True)
        self.user_count_alt.hide()
        live_layout.addWidget(self.user_count_alt)

        self.live_detail_button = QPushButton("숨기기", self)
        self.live_detail_button.clicked.connect(self.live_detail_func)
        live_layout.addWidget(self.live_detail_button)

        live_layout.addStretch()
        layout.addLayout(live_layout)

        remote_menu_layout = QHBoxLayout()
        self.overlay_text_box = QLineEdit(self)
        self.overlay_text_box.setPlaceholderText("텍스트 오버레이 입력")
        remote_menu_layout.addWidget(self.overlay_text_box)

        self.overlay_text_blank_button = QPushButton("비우기", self)
        # send_overlay_text는 메인 윈도우의 공용 메서드
        self.overlay_text_blank_button.clicked.connect(lambda: [self.send_overlay_text(''), self.overlay_text_box.setText('')])
        self.overlay_text_blank_button.setFixedWidth(100)
        remote_menu_layout.addWidget(self.overlay_text_blank_button)

        self.overlay_text_send_button = QPushButton("입력", self)
        self.overlay_text_send_button.clicked.connect(lambda: self.send_overlay_text(self.overlay_text_box.text()))
        self.overlay_text_send_button.setFixedWidth(100)
        remote_menu_layout.addWidget(self.overlay_text_send_button)
        self.overlay_text_box.returnPressed.connect(self.overlay_text_send_button.click)
        layout.addLayout(remote_menu_layout)

        buttons_layout = QHBoxLayout()
        self.control_remote_label = QLabel('후원', self)
        self.control_remote_label.setFixedWidth(40)
        buttons_layout.addWidget(self.control_remote_label)

        self.remote_tts_skip_button = QPushButton("  TTS 넘기기", self)
        self.remote_tts_skip_button.clicked.connect(self.remote_skip_TTS)
        self.remote_tts_skip_button.setIcon(QIcon(resource_path(r'.\resources\icon\skip.png')))
        self.remote_tts_skip_button.setIconSize(QSize(20,20))
        self.remote_tts_skip_button.setMinimumWidth(100)
        buttons_layout.addWidget(self.remote_tts_skip_button)

        self.hide_img = QPushButton(" 이미지 숨기기")
        self.hide_img.clicked.connect(self.blank_donation_image)
        self.hide_img.setIcon(QIcon(resource_path(r'.\resources\icon\X.png')))
        self.hide_img.setMinimumWidth(100)
        buttons_layout.addWidget(self.hide_img)

        self.remote_stop_noti_button = QPushButton("  알림 정지/시작", self)
        self.remote_stop_noti_button.clicked.connect(self.remote_stop_notification)
        self.remote_stop_noti_button.setIcon(QIcon(resource_path(r'.\resources\icon\playpause.png')))
        self.remote_stop_noti_button.setIconSize(QSize(30,20))
        self.remote_stop_noti_button.setMinimumWidth(100)
        buttons_layout.addWidget(self.remote_stop_noti_button)
        layout.addLayout(buttons_layout)

        ExtraLayout = QHBoxLayout()
        ExtraLayout.addSpacing(46)
        self.stop_tts_button3 = QPushButton("미션 TTS 넘기기", self)
        self.stop_tts_button3.clicked.connect(self.main_window.stop_tts) # 메인 윈도우 공용 함수
        self.stop_tts_button3.setIcon(QIcon(resource_path(r'.\resources\icon\skip.png')))
        self.stop_tts_button3.setIconSize(QSize(20,20))
        self.stop_tts_button3.hide()
        ExtraLayout.addWidget(self.stop_tts_button3)
        layout.addLayout(ExtraLayout)

        control_layout = QHBoxLayout()
        self.control_video_label = QLabel('영도', self)
        self.control_video_label.setFixedWidth(40)
        control_layout.addWidget(self.control_video_label)

        self.control_skip_button = QPushButton(' 스킵', self)
        self.control_skip_button.setIcon(QIcon(resource_path(r'.\resources\icon\skip.png')))
        self.control_skip_button.setIconSize(QSize(20,20))
        self.control_skip_button.setMinimumWidth(100)
        self.control_skip_button.clicked.connect(lambda: self.video_tab.video_control('end'))
        control_layout.addWidget(self.control_skip_button)

        self.control_pause_button = QPushButton(' 재생/정지', self)
        self.control_pause_button.setIcon(QIcon(resource_path(r'.\resources\icon\playpause.png')))
        self.control_pause_button.setIconSize(QSize(30,20))
        self.control_pause_button.setMinimumWidth(100)
        self.control_pause_button.clicked.connect(lambda: self.video_tab.video_control('space'))
        control_layout.addWidget(self.control_pause_button)

        self.control_home_button = QPushButton(' 맨앞으로', self)
        self.control_home_button.setIcon(QIcon(resource_path(r'.\resources\icon\rewind.png')))
        self.control_home_button.setIconSize(QSize(20,20))
        self.control_home_button.setMinimumWidth(100)
        self.control_home_button.clicked.connect(lambda: self.video_tab.video_control('home'))
        control_layout.addWidget(self.control_home_button)

        self.toggle_reserve_pause_video_button = QPushButton('정지 예약', self)
        self.toggle_reserve_pause_video_button.setCheckable(True)
        self.toggle_reserve_pause_video_button.setIcon(QIcon(resource_path(r'.\resources\icon\pause.png')))
        self.toggle_reserve_pause_video_button.setIconSize(QSize(30,20))
        self.toggle_reserve_pause_video_button.setMinimumWidth(100)
        self.toggle_reserve_pause_video_button.clicked.connect(lambda: self.video_tab.video_control_reserve())
        control_layout.addWidget(self.toggle_reserve_pause_video_button)
        self.chzzk_remote_popup_window = None
        layout.addLayout(control_layout)
    
        donation_layout = QHBoxLayout()
        self.show_total_money_button_video = QPushButton('총 모금액 표시', self)
        self.show_total_money_button_video.clicked.connect(self.show_total_money)
        self.show_total_money_button_video.hide()
        donation_layout.addWidget(self.show_total_money_button_video)
        self.test_mission_accept_button = QPushButton('미션 수락 테스트', self)
        self.test_mission_accept_button.clicked.connect(self.remote_auto_mission)
        self.test_mission_accept_button.hide()
        donation_layout.addWidget(self.test_mission_accept_button)
        donation_layout.addStretch()
        layout.addLayout(donation_layout)

        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.remote_frame_layout = QVBoxLayout(frame)
        button_layout = QHBoxLayout()
        self.is_chzzk_remote_popup_open = False

        self.donation_list_button = QPushButton('후원목록', self)
        self.donation_list_button.clicked.connect(lambda: [self.chzzk_remote_browser.hide() if not self.is_chzzk_remote_popup_open else None, self.chzzk_broadcast_browser.hide(), self.refresh_button.hide(), self.chzzk_remote_pop_up_button.hide(), self.prediction_button.hide(), self.studio_popup_button.hide(), self.image_list_cheese.hide(), self.result_box_cheese.show(), self.remote_buttons_color(0)])
        button_layout.addWidget(self.donation_list_button)

        self.image_list_button = QPushButton('왕도네', self)
        self.image_list_button.clicked.connect(lambda: [self.chzzk_remote_browser.hide() if not self.is_chzzk_remote_popup_open else None, self.chzzk_broadcast_browser.hide(), self.refresh_button.hide(), self.chzzk_remote_pop_up_button.hide(), self.prediction_button.hide(), self.studio_popup_button.hide(), self.image_list_cheese.show(), self.result_box_cheese.hide(), self.remote_buttons_color(1)])
        button_layout.addWidget(self.image_list_button)

        self.remote_button = QPushButton('치지직 리모컨', self)
        self.remote_button.clicked.connect(lambda: [self.chzzk_remote_browser.show(), self.chzzk_broadcast_browser.hide(), self.refresh_button.show(), self.chzzk_remote_pop_up_button.show(), self.prediction_button.hide(), self.studio_popup_button.hide(), self.image_list_cheese.hide(), self.result_box_cheese.hide(), self.remote_buttons_color(2)])
        button_layout.addWidget(self.remote_button)

        self.broadcast_button = QPushButton('간단 방송 설정', self)
        self.broadcast_button.clicked.connect(lambda: [self.chzzk_remote_browser.hide() if not self.is_chzzk_remote_popup_open else None, self.chzzk_broadcast_browser.show(), self.refresh_button.show(), self.chzzk_remote_pop_up_button.hide(), self.prediction_button.show(), self.studio_popup_button.show(), self.image_list_cheese.hide(), self.result_box_cheese.hide(), self.remote_buttons_color(3)])
        button_layout.addWidget(self.broadcast_button)
        self.remote_frame_layout.addLayout(button_layout)

        self.remote_buttons_layout = QHBoxLayout()
        self.chzzk_remote_pop_up_button = QPushButton("  리모컨 팝업", self)
        self.chzzk_remote_pop_up_button.setIcon(QIcon(resource_path(r'.\resources\icon\popup.png')))
        self.chzzk_remote_pop_up_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.chzzk_remote_pop_up_button.clicked.connect(self.open_chzzk_remote_popup)
        self.remote_buttons_layout.addWidget(self.chzzk_remote_pop_up_button)
        
        self.prediction_button = QPushButton("승부예측", self)
        self.prediction_button.setIcon(QIcon(resource_path(r'.\resources\icon\popup.png')))
        self.prediction_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.prediction_button.clicked.connect(self.main_window.open_prediction)
        self.prediction_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.remote_buttons_layout.addWidget(self.prediction_button)

        self.studio_popup_button = QPushButton("치지직 스튜디오", self)
        self.studio_popup_button.setIcon(QIcon(resource_path(r'.\resources\icon\popup.png')))
        self.studio_popup_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.studio_popup_button.clicked.connect(self.main_window.open_studio)
        self.studio_popup_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.remote_buttons_layout.addWidget(self.studio_popup_button)

        self.refresh_button = QPushButton('새로고침', self)
        self.refresh_button.setFont(QFont('Pretendard JP', 11))
        self.refresh_button.clicked.connect(lambda: [self.chzzk_remote_browser.setUrl(QUrl(f"https://studio.chzzk.naver.com/{self.main_window.chatroom_tab.input_id_box_chat.text()}/remotecontrol")) if self.chzzk_remote_browser.isVisible() else (self.chzzk_broadcast_browser.setUrl(QUrl(f"https://studio.chzzk.naver.com/{self.main_window.chatroom_tab.input_id_box_chat.text()}/live")) if self.chzzk_broadcast_browser.isVisible() else None) ])
        self.refresh_button.setFixedWidth(100)
        self.refresh_button.setIcon(QIcon(resource_path(r'.\resources\icon\refresh.png')))
        self.refresh_button.setIconSize(QSize(30,20))
        self.remote_buttons_layout.addWidget(self.refresh_button)
        self.remote_frame_layout.addLayout(self.remote_buttons_layout)

        self.chzzk_remote_browser = QWebEngineView()
        self.chzzk_remote_browser.setPage(CustomWebEnginePage(self.main_window.persistent_profile, self.chzzk_remote_browser))
        self.chzzk_remote_browser.page().javaScriptConsoleMessage = self.console_message_handler_remote
        settings = self.chzzk_remote_browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.chzzk_remote_browser.setUrl(QUrl(f"https://studio.chzzk.naver.com/{self.main_window.chatroom_tab.input_id_box_chat.text()}/remotecontrol"))
        self.chzzk_remote_browser.loadFinished.connect(self.on_load_finished_remote)
        self.remote_frame_layout.addWidget(self.chzzk_remote_browser)

        self.chzzk_remote_browser_mission = QWebEngineView()
        self.chzzk_remote_browser_mission.setPage(CustomWebEnginePage(self.main_window.persistent_profile, self.chzzk_remote_browser_mission))
        self.chzzk_remote_browser_mission.page().javaScriptConsoleMessage = self.console_message_handler_remote
        settings = self.chzzk_remote_browser_mission.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.chzzk_remote_browser_mission.setUrl(QUrl(f"https://studio.chzzk.naver.com/{self.main_window.chatroom_tab.input_id_box_chat.text()}/remotecontrol"))
        self.chzzk_remote_browser_mission.loadFinished.connect(self.on_load_finished_remote)
        self.chzzk_remote_browser_mission.hide()
        self.remote_frame_layout.addWidget(self.chzzk_remote_browser_mission)

        self.chzzk_broadcast_browser = QWebEngineView()
        self.chzzk_broadcast_browser.setPage(CustomWebEnginePage(self.main_window.persistent_profile, self.chzzk_broadcast_browser))
        self.chzzk_broadcast_browser.setUrl(QUrl(f"https://studio.chzzk.naver.com/{self.main_window.chatroom_tab.input_id_box_chat.text()}/live"))
        self.chzzk_broadcast_browser.loadFinished.connect(self.on_load_finished_broadcast)
        self.chzzk_broadcast_browser.page().javaScriptConsoleMessage = self.console_message_handler_broadcast
        self.remote_frame_layout.addWidget(self.chzzk_broadcast_browser)

        self.image_list_cheese = QListWidgetDonationImg(self)
        self.image_list_cheese.setIconSize(QSize(100,100))
        self.image_list_cheese.setSortingEnabled(True)
        self.image_list_cheese.setFont(QFont())
        self.image_list_cheese.setStyleSheet("""
            QListWidget::item { color: rgba(0, 0, 0, 0); }
            QListWidget::item:selected { color: rgba(0, 0, 0, 0); }
        """)
        self.image_list_cheese.hide()
        self.remote_frame_layout.addWidget(self.image_list_cheese)

        self.result_box_cheese = QTextEdit(self)
        self.result_box_cheese.setReadOnly(True)
        self.result_box_cheese.setFont(QFont('Pretendard JP', GLOBALFONTSIZE-1))
        self.remote_frame_layout.addWidget(self.result_box_cheese)
        self.result_box_cheese.hide()

        self.result_box_cheese_temp = QTextEdit(self)
        self.result_box_cheese_temp.hide()
        layout.addWidget(frame)

        self.error_box_dl = QTextEdit(self)
        self.error_box_dl.setReadOnly(True)
        self.error_box_dl.setMaximumHeight(100)
        self.error_box_dl.setFont(QFont('Pretendard JP', GLOBALFONTSIZE-1))
        self.error_box_dl.setText("에러 로그 입니다.")
        self.error_box_dl.hide()
        layout.addWidget(self.error_box_dl)
        
        self.error_hide_dl = QPushButton("에러창 가리기")
        self.error_hide_dl.clicked.connect(lambda: (self.error_hide_dl.hide(), self.error_box_dl.hide()))
        self.error_hide_dl.hide()
        layout.addWidget(self.error_hide_dl)
        
        # 7. 최종 레이아웃 설정
        self.setLayout(layout)

        # 8. 메인 윈도우 설정값에 따라 UI 초기 상태 설정
        self.video_donation_button_toggle.setChecked(self.main_window.video_donation_button_toggle.isChecked())
        
        # UI 초기 상태 적용
        if self.user_count_visible:
            # 시청자 수 보이기
            self.user_count.show()
            self.user_count_alt.hide()
            self.live_detail_button.setText("숨기기")
        else:
            # 시청자 수 숨기기
            self.user_count.hide()
            self.user_count_alt.show()
            self.live_detail_button.setText("보이기")
        
        self.video_donation_button_func()
        
        # dev_mode에 따라 테스트 버튼 숨기기
        if not self.main_window.devmode_toggle.isChecked():
            self.test_mission_accept_button.hide()
            
        # extra_donation_settings에 따라 모금액 버튼 숨기기
        if not self.main_window.extra_donation_settings.isChecked():
            self.show_total_money_button_video.hide()
        
        if not self.main_window.show_donation_list_toggle.isChecked():
            self.donation_list_button.hide()
    
    ##### 리모컨 탭 관련 함수 #####
    
    def live_detail_func(self):
        self.user_count_visible = not self.user_count_visible
        if self.user_count_visible:
            # 시청자 수 보이기
            self.user_count.show()
            self.user_count_alt.hide()
            self.live_detail_button.setText("숨기기")
        else:
            # 시청자 수 숨기기
            self.user_count.hide()
            self.user_count_alt.show()
            self.live_detail_button.setText("보이기")
    
    def video_donation_button_func(self):
        visible = self.video_donation_button_toggle.isChecked()
        self.control_video_label.setVisible(visible)
        self.control_skip_button.setVisible(visible)
        self.control_pause_button.setVisible(visible)
        self.control_home_button.setVisible(visible)
        self.toggle_reserve_pause_video_button.setVisible(visible)
    
    def open_chzzk_remote_popup(self):
        if self.chzzk_remote_popup_window is None:
            self.remote_button.hide()
            if self.chzzk_remote_browser.isVisible():
                if self.main_window.show_donation_list_toggle.isChecked():
                    self.donation_list_button.click()
                else:
                    self.broadcast_button.click()
            self.chzzk_remote_browser.show()
            self.is_chzzk_remote_popup_open = True
            self.remote_frame_layout.removeWidget(self.chzzk_remote_browser)
            self.chzzk_remote_popup_window = ChzzkRemotePopupWindow(self.chzzk_remote_browser, self)
            self.chzzk_remote_popup_window.finished.connect(self.on_chzzk_remote_popup_closed)
            self.chzzk_remote_popup_window.show()

    def on_chzzk_remote_popup_closed(self):
        if self.chzzk_remote_popup_window:
            self.remote_frame_layout.insertWidget(5, self.chzzk_remote_browser)
            self.chzzk_remote_popup_window = None
            self.is_chzzk_remote_popup_open = False
            self.remote_button.show()
            self.chzzk_remote_browser.hide()

    def check_live_detail(self):
        try:
            if self.main_window.is_live_started:
                if self.main_window.broadcast_start_time != None:
                    uptime = self._timedelta_to_hms(datetime.now() - self.main_window.broadcast_start_time)
                    self.uptime.setText(f"업타임 {uptime}")
        except Exception as e:
            return

    def blank_donation_image(self):
        self.send_image_path("blank","")
    
    def show_total_money(self):
        try:
            money = int(self.main_window.total_money)
        except:
            money = 0
        self.show_total_money_dialog = ShowTotalMoneyDialog(money)
        self.show_total_money_dialog.setGeometry(
                self.main_window.geometry().center().x() - 310 // 2,
                self.main_window.geometry().center().y() - 50 // 2,
                310, 50
            )
        self.show_total_money_dialog.show()

    def _timedelta_to_hms(self, td):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    ### 치지직 리모컨 브라우저 관련 함수 ###
    def on_load_finished_remote(self):
        check_load_script = """
            (function() {
                const intervalID = setInterval(function() {
                    const elementExists = document.querySelector(".remote_control_aside_button__Khhjh") !== null;
                    if (elementExists) {
                        console.log("page_loaded:" + elementExists);
                        clearInterval(intervalID);
                    }
                }, 100);
            })();
        """
        self.chzzk_remote_browser.page().runJavaScript(check_load_script)
        
    def on_loaded_complete_remote(self):
        self.remote_script()
        self.remote_script_2tier()
    
    def console_message_handler_remote(self, level, message, line, sourceID):
        print(message)
        if "SEARCH_REQUEST" in message:
            # 다른 탭(채팅부검)의 기능을 호출
            chat_log_tab = self.main_window.chat_log_search_tab
            if message.startswith("SEARCH_REQUEST:ban_"):
                text_to_copy = message.replace("SEARCH_REQUEST:ban_", "").replace("⭕","").replace("✅","").replace("2️⃣","").replace("🟥","").strip()
                
                dialog = QDialog(self.main_window)
                dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
                dialog.setWindowModality(Qt.WindowModality.WindowModal)
                dialog.setWindowTitle("검색 중")
                dialog.setFixedSize(300, 120)
                
                mw_geometry = self.main_window.geometry()
                dialog.move(
                    mw_geometry.center().x() - dialog.width() // 2,
                    mw_geometry.center().y() - dialog.height() // 2
                )

                # Layout
                layout = QVBoxLayout(dialog)
                
                label_title = QLabel("검색 중...", dialog)
                label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                title_font = QFont()
                title_font.setPointSize(12)
                title_font.setBold(True)
                label_title.setFont(title_font)
                
                label_desc = QLabel(f"'{text_to_copy}'\n아이디를 검색하고 있습니다.", dialog)
                label_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

                btn_cancel = QPushButton("취소", dialog)
                
                chat_log_tab.stop_signal = False # Reset Signal
                
                def cancel_search():
                    chat_log_tab.stop_signal = True
                    dialog.close()

                btn_cancel.clicked.connect(cancel_search)
                dialog.rejected.connect(cancel_search) # Handle X button

                layout.addWidget(label_title)
                layout.addWidget(label_desc)
                layout.addWidget(btn_cancel) # Add button
                
                dialog.show()
                QApplication.processEvents() # Force UI Update

                id = self.main_window.chat_log_search_tab.search_id(text_to_copy)
                
                was_cancelled = chat_log_tab.stop_signal
                
                try:
                    dialog.rejected.disconnect(cancel_search)
                except:
                    pass
                dialog.close()
                
                if was_cancelled:
                    print("[Search] Cancelled by user.")
                    return

                if id:
                    self.main_window.open_chzzk_user_profile_alt(id)
                else:
                    err_dialog = QDialog(self.main_window)
                    err_dialog.setWindowTitle("검색 실패")
                    err_dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
                    err_dialog.setFixedSize(400, 200)
                    
                    err_dialog.move(
                        mw_geometry.center().x() - err_dialog.width() // 2,
                        mw_geometry.center().y() - err_dialog.height() // 2
                    )

                    layout = QVBoxLayout(err_dialog)
                    
                    label_text = f"'{text_to_copy}'\n아이디를 찾을 수 없습니다.\n\n치지직 스튜디오에서 수동으로 닉네임을 입력하여\n활동 제한을 할 수 있습니다."
                    label = QLabel(label_text, err_dialog)
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Buttons Layout
                    btn_layout = QHBoxLayout()
                    
                    btn_studio = QPushButton("스튜디오 활동제한", err_dialog)
                    btn_studio.clicked.connect(lambda: [err_dialog.accept(), self.main_window.open_studio_restriction()])
                    
                    btn_cancel = QPushButton("닫기", err_dialog)
                    btn_cancel.clicked.connect(err_dialog.reject)
                    
                    btn_layout.addWidget(btn_studio)
                    btn_layout.addWidget(btn_cancel)
                    
                    layout.addWidget(label)
                    layout.addLayout(btn_layout)
                    
                    err_dialog.exec()
            else:
                text_to_copy = message.replace("SEARCH_REQUEST:search_", "").replace("⭕","").replace("✅","").replace("2️⃣","").replace("🟥","").strip()
                self.main_window.chat_log_search_tab.search_log_check(text_to_copy)
        
        if "PLAY ALL CLICKED" in message:
            self.main_window.video_donation_tab.refresh_page()
        if "page_loaded:" in message:
            page_loaded = message.split("page_loaded:")[1].strip()
            if page_loaded == "true":
                self.on_loaded_complete_remote()
        if "Link Open:" in message:
            link = message.split("Link Open: ")[1]
            webbrowser.open(link)
                

    def remote_script(self):
        # maintain100Items 설정값을 localStorage에 먼저 저장
        maintain_enabled = self.main_window.settings_tab.remote_maintain_100_items.isChecked()
        setting_script = f"localStorage.setItem('maintainItemsEnabled', JSON.stringify({str(maintain_enabled).lower()}));"
        self.chzzk_remote_browser.page().runJavaScript(setting_script)
        
        js_file_path = resource_path(r'.\resources\script\remote.js')
        with open(js_file_path, 'r', encoding='utf-8') as file:
            script = file.read()
        self.chzzk_remote_browser.page().runJavaScript(script)

    def remote_script_2tier(self):
        self.chzzk_remote_browser.page().runJavaScript(f"predefinedArray = {self.main_window.two_tier_user_list}; addTier2Indicator();")
    
    def remote_auto_mission(self):
        js_file_path = resource_path(r'.\resources\script\remote_auto_mission.js')
        with open(js_file_path, 'r', encoding='utf-8') as file:
            script = file.read()
        self.chzzk_remote_browser_mission.page().runJavaScript(script)
        if self.main_window.settings_tab.devmode_toggle.isChecked():
            self.chzzk_remote_browser_mission.page().runJavaScript("clickMissionTabTest();")
        else:
            self.chzzk_remote_browser_mission.page().runJavaScript("clickMissionTab();")
    
    def remote_skip_TTS(self):
        self.main_window.stop_tts()
        self.chzzk_remote_browser.page().runJavaScript("clickSkipButton();")
        
    def remote_stop_notification(self):
        self.chzzk_remote_browser.page().runJavaScript("clickStopNotificationButton();")
        
    ### 치지직 스튜디오 브라우저 관련 함수 ###
    def on_load_finished_broadcast(self):
        check_load_script = """
            (function() {
                const intervalID = setInterval(function() {
                    const elementExists = document.querySelector(".live_form_content__H9r7D") !== null;
                    const isPrediction = window.location.href.includes("/prediction");
                    if (elementExists || isPrediction) {
                        console.log("page_loaded:true");
                        clearInterval(intervalID);
                    }
                }, 100);
            })();
        """
        self.chzzk_broadcast_browser.page().runJavaScript(check_load_script)

    def on_loaded_complete_broadcast(self):
        QTimer.singleShot(100, self.show_only_info_section)

    def console_message_handler_broadcast(self, level, message, line, sourceID):
        print(message)
        if "page_loaded:" in message:
            page_loaded = message.split("page_loaded:")[1].strip()
            if page_loaded == "true":
                self.on_loaded_complete_broadcast()

    def show_only_info_section(self):
        script_path = os.path.join(r'.\resources\script', 'show_info_section.js')
        try:
            with open(resource_path(script_path), "r", encoding="utf-8") as file:
                script_content = file.read()
            self.chzzk_broadcast_browser.page().runJavaScript(script_content)
        except FileNotFoundError:
            print(f"오류: 스크립트 파일을 찾을 수 없습니다. 경로를 확인하세요: '{script_path}'")

        # Inject Prediction Templates Script (RE-ADDED)
        tpl_script_path = os.path.join(r'.\resources\script', 'prediction_templates.js')
        try:
            with open(resource_path(tpl_script_path), "r", encoding="utf-8") as file:
                tpl_script_content = file.read()
            self.chzzk_broadcast_browser.page().runJavaScript(tpl_script_content)
            print("[RemoteTab] Prediction Templates injected into broadcast browser.")
        except FileNotFoundError:
            print(f"오류: 프리셋 스크립트 파일을 찾을 수 없습니다. '{tpl_script_path}'")
        except Exception as e:
            print(f"스크립트 실행 중 오류가 발생했습니다: {e}")
            
    ##### 기타 공용 함수 #####
    
    def remote_buttons_color(self, active_index):
        is_dark_theme = self.main_window.settings_tab.theme_check.isChecked()
        if is_dark_theme:
            default_bg_color = "black"
            default_text_color = "white"
        else: # 라이트 테마
            default_bg_color = "white"
            default_text_color = "black"
        active_style = """
            QPushButton {
                border: 2px solid rgb(83, 175, 119);
                background-color: rgb(83, 175, 119);
                color: white;
            }
        """
        default_style = f"""
            QPushButton {{
                border: 2px solid rgb(83, 175, 119);
                background-color: {default_bg_color};
                color: {default_text_color};
            }}
        """
        buttons = [
            self.donation_list_button, 
            self.image_list_button, 
            self.remote_button, 
            self.broadcast_button
        ]
        for i, button in enumerate(buttons):
            if i == active_index:
                button.setStyleSheet(active_style)
            else:
                button.setStyleSheet(default_style)
                
    # --- 이 탭에서 직접 처리하는 시그널 슬롯 ---
    
    @pyqtSlot(str)
    def update_chat_status(self, status_text):
        """(이 슬롯은 메인 윈도우가 받아서 다시 호출해줘야 함)"""
        self.chat_connection_status.setText(status_text)

    # --- 이 탭이 다른 탭/메인윈도우에 제공하는 함수 ---
    
    def refresh_browsers(self):
        """메인 윈도우나 커넥터가 호출할 수 있는 브라우저 새로고침 함수"""
        streamer_id = self.main_window.chatroom_tab.input_id_box_chat.text()
        print(streamer_id)
        if not streamer_id and self.main_window.chatroom_connector_instance:
            streamer_id = self.main_window.chatroom_connector_instance.streamer_ID
        
        if streamer_id:
            print(f"refresh_browsers: streamer_ID = {streamer_id}")
            self.chzzk_remote_browser.load(QUrl(f"https://studio.chzzk.naver.com/{streamer_id}/remotecontrol"))
            self.chzzk_broadcast_browser.load(QUrl(f"https://studio.chzzk.naver.com/{streamer_id}/live"))
        else:
            print("refresh_browsers: streamer_ID를 찾을 수 없습니다.")
            self.chzzk_remote_browser.setUrl(QUrl("about:blank"))
            self.chzzk_broadcast_browser.setUrl(QUrl("about:blank"))

    def process_donation_message(self, msg_dict):
        """메인 윈도우의 message 핸들러가 호출해주는 함수"""
        donation_type = msg_dict.get("donation_type", "")
        if donation_type != "채팅" and donation_type != "영상후원":
            resultB = self.process_donation(msg_dict) # process_donation은 메인에 있음
            if resultB != "":
                self.main_window.is_msg = True # 이 플래그도 메인 윈도우 소유
                self.result_box_cheese.setHtml(resultB)
                QApplication.processEvents()
    
    ### 영도 쇼츠 확대 관련 함수 #####
    def get_chzzk_video_type(self, thumbnail):
        # 치지직 클립 썸네일의 크기를 확인하여 영상 타입을 결정
        try:
            # 이미지 다운로드
            response = requests.get(thumbnail)
            response.raise_for_status()  # 요청 실패 시 예외 발생
            
            # 이미지를 PIL Image 객체로 변환
            img = Image.open(BytesIO(response.content))
            
            # 이미지 크기 출력 (width, height)
            width, height = img.size
            if width == 720 and height == 1280:
                return "shorts"
            elif width < height:
                return "shorts"
            else:
                return "normal" 
        except requests.exceptions.RequestException as e:
            return "normal"
        except Exception as e:
            return "normal"
    
    def get_youtube_video_type(self, videoId):
        try:
            if 'clip-donation' in videoId:
                return 'normal'
            # API 요청 URL 구성
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "player",
                "id": videoId,
                "maxHeight": 720,
                "maxWidth": 1280,
                "key": self.main_window.settings_tab.youtube_api_key.text().strip()
            }

            # 요청 보내기
            response = requests.get(url, params=params)
            data = response.json()
            player_info = data["items"][0]["player"]
            embed_height = player_info.get("embedHeight")
            embed_width = player_info.get("embedWidth")
            if int(embed_height) == 720:
                if int(embed_width) <= 450:
                    return "shorts"
                else:
                    return "normal"
            elif int(embed_width) <= int(embed_height):
                return "shorts"
            else:
                return "normal"
        except (KeyError, IndexError):
            return "normal"
    
    ### 텍스트 오버레이 관련 함수 ###
    def send_overlay_text(self, text):
        url = "http://127.0.0.1:5000/update_text"  # Flask 서버의 엔드포인트 URL
        data = {"text": text}  # 서버에 보낼 데이터
        try:
            response = requests.post(url, json=data)  # POST 요청 보내기
            if response.status_code == 200:
                None
            else:
                None
        except Exception as e:
            None
    

    
    def donation_num_check(self, cheese, donation_type, tier, quantity):
        cheese_num = int(cheese)
        if donation_type == "구독선물":
            if int(tier) == 1: cheese_num = int(quantity) * 4900
            else: cheese_num = int(quantity) * 14900
        if cheese_num>=10000 and cheese_num<30000:
            if self.main_window.donation_gif1.isChecked() == True: return "cheese_10000.gif"
            else: return "cheese_10000.png"
        elif cheese_num>=30000 and cheese_num<50000:
            if self.main_window.donation_gif3.isChecked() == True: return "cheese_30000.gif"
            else: return "cheese_30000.png"
        elif cheese_num>=50000 and cheese_num<70000: return "cheese_50000.png"
        elif cheese_num>=70000 and cheese_num<100000: return "cheese_70000.png"
        elif cheese_num>=100000 and cheese_num<200000: return "cheese_100000.png"
        elif cheese_num>=200000 and cheese_num<500000:
            if self.main_window.donation_gif20.isChecked() == True: return "cheese_200000.gif"
            else: return "cheese_200000.png"
        elif cheese_num>=500000 and cheese_num<1000000:
            if self.main_window.donation_gif50.isChecked() == True: return "cheese_500000.gif"
            else: return "cheese_500000.png"
        elif cheese_num>=1000000:
            if self.main_window.donation_gif100.isChecked() == True: return "cheese_1000000.gif"
            else: return "cheese_1000000.gif"
        else:
            if donation_type == "구독선물":
                if int(tier) == 1: return "subgift_1.png"
                elif int(tier) == 2: return "subgift_2.png"
            else: return "cheese.png"

    def wraptext(self, text):
        wrapped_text = ""
        for i in range(0, len(text), 20):
            wrapped_text += text[i:i+20] + "\n"
        wrapped_text = wrapped_text[:-1]
        return wrapped_text
    
    def wraptext_alt(self, text):
        wrapped_text = ""
        count = 0
        for i in range(0, len(text)):
            wrapped_text += text[i]
            if text[i] == " ": count += 0.5
            else: count += 1
            if count>=30:
                count = 0
                wrapped_text += "<br>"
        return wrapped_text
    
    def set_image(self,path, backpath):
        try:
            self.send_image_path(path, backpath)
        except Exception as e:
            None

    def send_image_path(self, image_path, back_image_path):
        try:
            back_image_path = back_image_path.replace("\\","/")
            url = "http://127.0.0.1:5000/update_image"  # Flask 서버의 엔드포인트 URL
            data = {"image_path": image_path, "back_image_path": back_image_path}  # 서버에 보낼 데이터
            response = requests.post(url, json=data)  # POST 요청 보내기
            if response.status_code == 200:
                None
            else:
                None
        except Exception as e:
            None

    def _generate_formatted_text(self, donation_type, nick, cheese, tier, quantity, chat_date_str, pnum, selection_type, receiver_nick, msg=None):
        """후원 정보를 기반으로 서식이 적용된 HTML 텍스트를 생성합니다."""
        # 공통 스타일 정의
        date_style = "font-size: 10pt;"
        nick_style = "font-size: 12pt;"
        main_style = "font-size: 12pt;"

        # 유형별 색상 및 텍스트 구성
        color_map = {
            "치즈": self.cheese_color,
            "미션성공": self.mission_color, "미션실패": self.mission_color, "미션": self.mission_color,
            "구독": self.subscribe_color, "구독선물": self.subscribe_color
        }
        color = color_map.get(donation_type, 'black')
        
        cheese_val = int(cheese)


        text_map = {
            "치즈": f"{cheese_val:,}치즈 선물",
            "미션성공": f"상금 {cheese_val:,}치즈 획득",
            "미션": f"상금 {cheese_val:,}치즈 추가",
            "구독선물": f"{tier}티어 구독권 {quantity}장 선물",
        }
        if selection_type == "MANUAL": ## 지정 구독선물
            text_map["구독선물"] = f"{receiver_nick}에게 {tier}티어 구독권 선물"

        main_text = text_map.get(donation_type, f"{donation_type} {cheese_val:,}개")

        if donation_type in ["미션성공", "미션실패"]:
            if int(pnum) != 0: nick += f" 외 {pnum}명"

        # 최종 HTML 생성
        header = f"<span style='{date_style}'>[{chat_date_str}]</span><br>"
        body = ""
        if donation_type == "미션성공":
            body = f"<b><span style='{nick_style}'>미션 성공! {nick}의 미션</span></b><br>" \
                f"<b><span style='color: {color}; {main_style}'>{main_text}</span></b>"
        elif donation_type == "미션실패":
            body = f"<b><span style='{nick_style}'>미션 실패.. {nick}의 미션</span></b><br>" \
                f"<b><span style='color: {color}; {main_style}'>{main_text}</span></b>"
        else:
            body = f"<b><span style='{nick_style}'>{nick}</span></b>님이 " \
                f"<b><span style='color: {color}; {main_style}'>{main_text}</span></b>"

        footer = ""
        if msg:
            footer = f"<br><span style='{nick_style}'> {self.wraptext_alt(msg)}</span>"

        return f"{header}{body}{footer}"

    def _update_result_text(self, result, donation_type, nick, cheese, tier, chat_date_str, msg, pnum, sum, month, quantity, selection_type, receiver_nick):
        new_donation = ""
        cheese_val = int(cheese)
        highlight_style = "background-color: rgba(255, 255, 0, 0.4);"
        is_highlight = (
            (donation_type == "구독선물" and quantity >= int(self.main_window.sub_gift_cut.text())) or
            (donation_type in ["치즈"] and cheese_val >= int(self.main_window.donation_img_cut.text())) or
            (donation_type in ["미션성공"] and cheese_val >= int(self.main_window.donation_img_cut.text()))
        )

        base_style = "line-height: 50%;"
        p_tag_style = f"style='{base_style}{highlight_style if is_highlight else ''}'"
        
        date_line = f"<p style='line-height: 50%; font-size: 10pt;'>[{chat_date_str}]</p>"

        text = ""
        if donation_type == "구독선물":
            if selection_type == "RANDOM": # 랜덤 선물
                text = f"<b><span>{nick}</span></b>님이 <b><span style='color: {self.subscribe_color};'>{tier}티어 구독권 {quantity}장 선물</span></b><span></span>"
            else: # 지정 선물
                text = f"<b><span>{nick}</span></b>님이 <b><span>{receiver_nick}</span></b>에게 <b><span style='color: {self.subscribe_color};'>{tier}티어 구독권 선물</span></b><span></span>"
        elif donation_type == "구독":
            text = f"<b><span>{nick}</span></b>님이 <b><span style='color: {self.subscribe_color};'>티어{tier} {month}개월 구독</span></b>"
        elif donation_type == "미션": # 미션금 추가
            text = f"<b><span>{nick}</span></b>님이 <b><span style='color: {self.mission_color};'>미션 상금 {cheese_val:,}개 추가</span></b> "
        elif donation_type in ["미션대기", "미션수락", "미션거절", "미션성공", "미션실패"]:
            status_map = {"미션대기": "대기 중", "미션수락": "수락!", "미션거절": "거절..", "미션성공": "성공!", "미션실패": "실패.."}
            status = status_map.get(donation_type)
            more_ppl_text = ""
            if int(pnum) != 0: more_ppl_text = f" 외 {pnum}명"
            text = f"<b><span>{nick}{more_ppl_text}</span></b>님의 <b><span style='color: {self.mission_color};'>미션 {cheese_val:,}개 {status}</span></b> "
        else: # 치즈
            text = f"<b><span>{nick}</span></b>님이 <b><span style='color: {self.cheese_color};'>{cheese_val:,}치즈 선물!</span></b> "
        new_donation = f"<p {p_tag_style}>{text}</p>"


        if msg:
            msg_style = f"style='line-height: 100%;{highlight_style if is_highlight else ''}'"
            msg_prefix = "메시지"
            msg_suffix = ""
            if "미션" in donation_type:
                msg_prefix = "미션"
                if donation_type == "미션":
                    msg_suffix = f" <b><span>(누적 {int(sum):,}개)</span></b>"
            new_donation += f"<p {msg_style}> ➥ <b><span>{msg_prefix}:</span></b> <span>{msg}{msg_suffix}</span></p>"

        result = "<hr style='line-height: 75%;'>" + date_line + new_donation + result
        return result

    def _create_donation_image(self, nick, donation_type, cheese, tier, pnum, chat_date_str, quantity, selection_type, receiver_nick):
        def get_fitting_font(text, max_width, font_path, initial_size, min_size=10):
            font_size = initial_size
            font = ImageFont.truetype(font_path, font_size, encoding="UTF-8")
            
            while font.getlength(text) > max_width and font_size > min_size:
                font_size -= 1  # 폰트 크기를 1씩 줄임
                font = ImageFont.truetype(font_path, font_size, encoding="UTF-8")
            return font

        def draw_texts_on_image(draw, font_path, nick_text, donation_text):
            nick_font = get_fitting_font(nick_text, 350, font_path, initial_size=30)
            nick_width = nick_font.getlength(nick_text)
            nick_bbox = nick_font.getbbox(nick_text)
            nick_height = nick_bbox[3] - nick_bbox[1]
            draw.text(
                (180 - nick_width / 2, 294 - nick_height / 2 - nick_bbox[1]),
                nick_text, 
                font=nick_font, 
                fill=(115, 249, 168)
            )

            donation_font = get_fitting_font(donation_text, 350, font_path, initial_size=30)
            donation_width = donation_font.getlength(donation_text)
            donation_bbox = donation_font.getbbox(donation_text)
            donation_height = donation_bbox[3] - donation_bbox[1]
            draw.text(
                (180 - donation_width / 2, 328 - donation_height / 2 - donation_bbox[1]),
                donation_text, 
                font=donation_font, 
                fill=(246, 208, 83)
            )
                

        imgname = self.donation_num_check(cheese, donation_type, tier, quantity)
        
        invalid_chars = r'[<>:"/\\|?*]'
        clean_nick = re.sub(invalid_chars, '', nick)
        base_filename = f"[{re.sub('[-:]', '', chat_date_str)}] {clean_nick} 님이 {donation_type} {int(cheese):,}개 선물"
        
        font_path = resource_path(r'.\resources\fonts\SB Aggro M.ttf')
        nick_text = f"{nick}"
        if donation_type == "미션성공":
            if int(pnum) != 0:
                nick_text = f"{nick} 외 {pnum}명"
        text_map = {
            "치즈": f"{int(cheese):,}치즈", "미션성공": f"미션성공 {int(cheese):,}치즈",
            "구독선물": f"구독선물 {tier}티어 {int(quantity):,}장"
        }
        donation_text = text_map.get(donation_type, f"{donation_type} {int(cheese):,}개")

        img = Image.new('RGBA', (360, 360), (0, 0, 0, 0))
        background = Image.open(resource_path(r'.\resources\img\background_0.png')).convert('RGBA')
        img.paste(background, (0, 0), background)

        char_img_path = resource_path(rf".\resources\img\{imgname.replace('.gif', '.png') if imgname.endswith('.gif') else imgname}")
        char_img = Image.open(char_img_path)
        img.paste(char_img, (0, 272 - char_img.size[1]), char_img)

        draw = ImageDraw.Draw(img)
        draw_texts_on_image(draw, font_path, nick_text, donation_text) # 헬퍼 함수 호출
        
        output_path = os.path.join(self.main_window.file_path_box_donation.text(), f"{base_filename}.png")
        img.save(output_path)
        
        gif_alt_path = ""
        if imgname.endswith(".gif"):
            alt_img = Image.new('RGBA', (360, 360), (0, 0, 0, 0))
            alt_img.paste(background, (0, 0), background)
            alt_draw = ImageDraw.Draw(alt_img)
            draw_texts_on_image(alt_draw, font_path, nick_text, donation_text)
            gif_alt_path = os.path.join(self.main_window.file_path_box_donation.text(), f"{base_filename}_alt.png")
            alt_img.save(gif_alt_path)

        return output_path, gif_alt_path, imgname

    def _add_item_to_gui_list(self, file_path, formatted_text, item_text, id, nick, cheese, donation_type, amount_path):
        if self.image_list_cheese.findItems(item_text, Qt.MatchFlag.MatchContains):
            return
        donation_data = {
            'type': 'donation', 
            'file_path': file_path,
            'formatted_text': formatted_text,
            'item_text': item_text,
            'amount_path': amount_path,
            'id': id,
            'nick': nick,
            'cheese': cheese,
            'donation_type': donation_type,
        }

        label_button_widget = LabelButtonWidget(formatted_text, file_path, amount_path, True, self)
        item = QListWidgetItem(QIcon(file_path), item_text)
        item.setData(Qt.ItemDataRole.UserRole, donation_data)
        
        brush = QBrush(QColor(0, 0, 0, 0))
        item.setForeground(brush)

        self.image_list_cheese.addItem(item)
        self.image_list_cheese.setItemWidget(item, label_button_widget)

        if int(cheese) >= int(self.main_window.bang_sel_cut.text()) and nick != "익명의 후원자" and donation_type != "미션성공":
            button_data = {
                'type': 'button',
                'id': id,
                'nick': nick,
                'cheese': cheese,
                'donation_type': donation_type,
                'file_path': file_path,
            }
            
            btn = QPushButton(f'{nick}의 채널로 가기', self)
            btn.clicked.connect(lambda: self.open_channel_link(id))
            
            timestamp_prefix = os.path.basename(file_path).split(']')[0][1:]
            btn_item_text = f"[{timestamp_prefix}] 0\n{nick} 님이 {donation_type} {int(cheese):,}개 선물"
            
            btn_item = QListWidgetItem(btn_item_text)
            btn_item.setData(Qt.ItemDataRole.UserRole, button_data)
            btn_item.setForeground(brush)
            self.image_list_cheese.addItem(btn_item)
            self.image_list_cheese.setItemWidget(btn_item, btn)

        self.image_list_cheese.sortItems(Qt.SortOrder.DescendingOrder)
    
    def open_channel_link(self, id):
        url = f"https://chzzk.naver.com/{id}/community"
        self.main_window.open_browser(url, 1280, 960, "치지직")

    def process_donation(self, dict):
        try:
            result = self.result_box_cheese.toHtml()
            chat_date_str = dict.get("time", "")
            nick = dict.get("nick", "")
            id = dict.get("id", "")
            cheese = dict.get("cheese", 0)
            donation_type = dict.get("donation_type", "")
            sum = dict.get("sum", 0)
            pnum = dict.get("pnum", 0)
            sec = dict.get("sec", 0)
            msg = dict.get("msg", "")
            title = dict.get("title", "")
            tier = dict.get("tier", 1)
            quantity = dict.get("quantity", 1)
            month = dict.get("month", 1)
            selection_type = dict.get("selection_type", "RANDOM")
            receiver_nick = dict.get("receiver_nick", "(받은이 닉네임)")

            if msg:
                tts_map = {
                    "미션": (self.main_window.mission_read_add_tts, f"상금 {cheese}치즈 추가! 총 상금 {sum}치즈."),
                    "미션대기": (self.main_window.mission_read_req_tts, f"새로운 미션 도착! {msg}. 상금 {cheese}치즈."),
                    "미션성공": (self.main_window.mission_read_success_tts, f"미션 성공! 상금 {cheese}치즈 획득. {msg}."),
                    "미션실패": (self.main_window.mission_read_fail_tts, f"미션 실패! 위로금 {str(int(int(cheese)/10))}치즈 획득. {msg}."),
                }
                if donation_type in tts_map:
                    checkbox, mission_text = tts_map[donation_type]
                    if checkbox.isChecked():
                        if self.main_window.audio_thread and self.main_window.audio_thread.is_alive():
                            self.main_window.stop_audio_event.set()
                            self.main_window.audio_thread.join()
                        self.main_window.stop_audio_event.clear()
                        self.main_window.audio_thread = threading.Timer(self.main_window.mission_delay_tts.value(), lambda: asyncio.run(self.main_window.play_audio(mission_text, 2,)))
                        self.main_window.audio_thread.start()
            
            result = self._update_result_text(result, donation_type, nick, cheese, tier, chat_date_str, msg, pnum, sum, month, quantity, selection_type, receiver_nick)

            is_sub_gift_skippable = donation_type == "구독선물" and int(quantity) < int(self.main_window.sub_gift_cut.text())
            is_donation_skippable = donation_type != "구독선물" and int(cheese) < int(self.main_window.donation_img_cut.text())
            
            image_creation_skip_types = ["미션실패", "미션수락", "미션대기", "미션", "미션거절"]
            
            if (not self.main_window.settings_tab.kanetv8.isChecked() or
                is_sub_gift_skippable or
                is_donation_skippable or
                donation_type in image_creation_skip_types):
                return result

            invalid_chars = r'[<>:"/\\|?*]'
            clean_nick = re.sub(invalid_chars, '', nick)
            base_filename = f"[{re.sub('[-:]', '', chat_date_str)}] {clean_nick} 님이 {donation_type} {int(cheese):,}개 선물"
            image_path = os.path.join(self.main_window.file_path_box_donation.text(), f"{base_filename}.png")
            
            gif_alt_path = ""
            imgname = ""

            if not os.path.exists(image_path):
                image_path, gif_alt_path, imgname = self._create_donation_image(nick, donation_type, cheese, tier, pnum, chat_date_str, quantity, selection_type, receiver_nick)
            else:
                imgname = self.donation_num_check(cheese, donation_type, tier, quantity)

            chat_date = datetime.strptime(chat_date_str, '%Y-%m-%d %H:%M:%S')
            if self.main_window.toggle_auto_show_img.isChecked() and startupTime < chat_date:
                if image_path not in self.auto_displayed_images:
                    if imgname.endswith(".gif"):
                        amount_path = os.path.join(self.main_window.file_path_box_donation.text(), imgname.replace('cheese_', ""))
                        if not gif_alt_path:
                            _, gif_alt_path, _ = self._create_donation_image(nick, donation_type, cheese, tier, pnum, chat_date_str, quantity, selection_type, receiver_nick)
                        self.send_image_path(amount_path, gif_alt_path)
                    else:
                        self.send_image_path(image_path, "")
                    self.auto_displayed_images.add(image_path)
            
            formatted_text_no_msg = self._generate_formatted_text(donation_type, nick, cheese, tier, quantity, chat_date_str, pnum, selection_type, receiver_nick)
            formatted_text_with_msg = self._generate_formatted_text(donation_type, nick, cheese, tier, quantity, chat_date_str, pnum, selection_type, receiver_nick, msg)

            item_text = f"[{re.sub('[-:]', '', chat_date_str)}]\n{nick} 님이 {donation_type} {int(cheese):,}개 선물"
            if msg:
                item_text += f"\n➥ 메시지: {self.wraptext(msg)}"

            amount_path = os.path.join(self.main_window.file_path_box_donation.text(), imgname.replace('cheese_', ""))
            
            self._add_item_to_gui_list(
                image_path,
                formatted_text_with_msg if msg else formatted_text_no_msg,
                item_text, id, nick, cheese, donation_type, amount_path
            )

            return result

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            err = traceback.format_exc()
            errortime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_text = f"[{errortime}]\n❗오류 발생!{exc_type} {exc_tb.tb_lineno} {err} {fname}\n\n"
            self.error_box_dl.setText(error_text + self.error_box_dl.toPlainText())
            self.error_box_dl.show()
            self.error_hide_dl.show()
            return result