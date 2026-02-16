import os
import shutil
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QLabel, QFrame, QSizePolicy, QCheckBox, 
                             QComboBox, QDoubleSpinBox, QSlider, 
                             QScrollArea, QGroupBox, QGridLayout, QFileDialog, 
                             QMessageBox, QApplication)
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtCore import Qt, QSettings

from app.constants import USERPATH, USERPATH_SLASH
from app.ui_widgets import QToggle
from app.ui_dialogs import AutoBanSettingMenuDialog, GuideDialog, TabManagementDialog, AboutDialog, OverlaySettingsDialog

class SettingsTab(QWidget):

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        
        self.main_window = main_window

        frame = QFrame(self)
        layout = QVBoxLayout(frame)

        switchbutton_layout = QHBoxLayout()

        self.theme_check = QToggle(self)
        self.theme_check.setText("다크 모드")
        self.theme_check.clicked.connect(lambda: self.main_window.theme_change(False)) # 메인 윈도우의 함수 호출
        switchbutton_layout.addWidget(self.theme_check)

        layout.addLayout(switchbutton_layout)

        auto_start_groupbox = QGroupBox("자동 실행 설정", self)
        auto_start_layout = QGridLayout(auto_start_groupbox)

        startup_tab_label = QLabel('시작 시 기본 탭', self)
        startup_tab_label.setFont(QFont('Pretendard JP', 12, QFont.Weight.Bold))
        auto_start_layout.addWidget(startup_tab_label, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        self.startup_tab_combobox = QComboBox(self)
        self.startup_tab_combobox.addItems(["리모컨", "채팅창"])
        self.startup_tab_combobox.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        auto_start_layout.addWidget(self.startup_tab_combobox, 0, 1)

        auto_starton_launch_label = QLabel('프로그램 시작 시', self)
        auto_starton_launch_label.setFont(QFont('Pretendard JP', 12, QFont.Weight.Bold))
        auto_start_layout.addWidget(auto_starton_launch_label, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        self.auto_chatroom_connector_start = QCheckBox('채팅창 접속', self)
        self.auto_chatroom_connector_start.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        auto_start_layout.addWidget(self.auto_chatroom_connector_start, 1, 1)

        self.auto_start_chzzk_overlay = QCheckBox('치지직 영도 오버레이 자동 실행', self)
        self.auto_start_chzzk_overlay.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        auto_start_layout.addWidget(self.auto_start_chzzk_overlay, 2, 1)

        auto_starton_connect_label = QLabel('채팅창 연결 완료 시', self)
        auto_starton_connect_label.setFont(QFont('Pretendard JP', 12, QFont.Weight.Bold))
        auto_start_layout.addWidget(auto_starton_connect_label, 3, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        self.auto_chat_popup_start = QCheckBox('채팅창 팝업 실행', self)
        self.auto_chat_popup_start.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        auto_start_layout.addWidget(self.auto_chat_popup_start, 3, 1)

        self.auto_starton_close_label = QLabel('프로그램 종료 시', self)
        self.auto_starton_close_label.setFont(QFont('Pretendard JP', 12, QFont.Weight.Bold))
        auto_start_layout.addWidget(self.auto_starton_close_label, 4, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        self.auto_delete = QCheckBox('왕도네 이미지 폴더 비우기', self)
        self.auto_delete.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        auto_start_layout.addWidget(self.auto_delete, 4, 1)

        layout.addWidget(auto_start_groupbox)

        chat_room_groupbox = QGroupBox("채팅방 설정", self)
        chat_layout = QVBoxLayout(chat_room_groupbox)
        auto_notice_layout = QHBoxLayout()
        self.auto_notice_toggle = QToggle("채팅창 접속 시 자동 공지 등록")
        auto_notice_layout.addWidget(self.auto_notice_toggle)
        self.auto_notice_textbox = QLineEdit(self)
        self.auto_notice_textbox.setMaxLength(100)
        self.auto_notice_textbox.setPlaceholderText("공지 내용을 입력하세요.")
        auto_notice_layout.addWidget(self.auto_notice_textbox)
        chat_layout.addLayout(auto_notice_layout)

        self.remember_chat_popup_check = QToggle(self)
        self.remember_chat_popup_check.setText('채팅창 팝업 위치 및 크기 기억')
        self.remember_chat_popup_check.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        chat_layout.addWidget(self.remember_chat_popup_check)

        chat_room_button_layout = QHBoxLayout()
        self.auto_ban_setting_button = QPushButton("자동 밴 설정")
        self.auto_ban_setting_button.clicked.connect(self.auto_ban_setting_menu)
        self.auto_ban_setting_button.hide() # 공식 API 지원 전까지는 임시로 가림
        chat_room_button_layout.addWidget(self.auto_ban_setting_button)
        chat_layout.addLayout(chat_room_button_layout)
        layout.addWidget(chat_room_groupbox)

        remote_groupbox = QGroupBox("리모컨 설정", self)
        remote_layout = QVBoxLayout(remote_groupbox)
        self.show_donation_list_toggle = QToggle("후원목록 표시")
        self.show_donation_list_toggle.clicked.connect(self.show_donation_list_toggle_func)
        remote_layout.addWidget(self.show_donation_list_toggle)
        commision_layout = QHBoxLayout()
        self.extra_donation_settings = QToggle(self)
        self.extra_donation_settings.setText("모금액 표시 버튼 추가")
        self.extra_donation_settings.clicked.connect(self.extra_donation_settings_func)
        commision_layout.addWidget(self.extra_donation_settings)
        self.commision_rate_label = QLabel('후원 수수료(%)')
        commision_layout.addWidget(self.commision_rate_label)
        self.commision_rate = QDoubleSpinBox()
        self.commision_rate.setMinimum(0)
        self.commision_rate.setMaximum(100)
        self.commision_rate.setSingleStep(1)
        self.commision_rate.setDecimals(0)
        self.commision_rate.setSuffix(" %")
        commision_layout.addWidget(self.commision_rate)
        commision_layout.addStretch()
        remote_layout.addLayout(commision_layout)
        self.how_to_text_overlay = QPushButton("OBS 텍스트 오버레이 설정법")
        self.how_to_text_overlay.clicked.connect(self.show_text_overlay_guide)
        remote_layout.addWidget(self.how_to_text_overlay)
        layout.addWidget(remote_groupbox)

        self.how_to_prediction_overlay = QPushButton("OBS 승부예측 오버레이 설정법")
        self.how_to_prediction_overlay.clicked.connect(self.show_prediction_overlay_guide)
        remote_layout.addWidget(self.how_to_prediction_overlay)
        layout.addWidget(remote_groupbox)

        donation_setting_groupbox = QGroupBox('후원 설정', self)
        donation_layout = QVBoxLayout(donation_setting_groupbox)
        self.auto_mission_approve = QToggle(self)
        self.auto_mission_approve.setText("미션 자동 수락")
        self.auto_mission_approve.setChecked(False)
        donation_layout.addWidget(self.auto_mission_approve)

        tts_layout = QHBoxLayout()
        self.tts_label = QLabel('미션TTS')
        tts_layout.addWidget(self.tts_label)
        self.mission_read_req_tts = QCheckBox("요청", self)
        tts_layout.addWidget(self.mission_read_req_tts)
        self.mission_read_add_tts = QCheckBox("상금추가", self)
        tts_layout.addWidget(self.mission_read_add_tts)
        self.mission_read_success_tts = QCheckBox("성공", self)
        tts_layout.addWidget(self.mission_read_success_tts)
        self.mission_read_fail_tts = QCheckBox("실패", self)
        tts_layout.addWidget(self.mission_read_fail_tts)
        tts_layout.addStretch()
        donation_layout.addLayout(tts_layout)

        tts_layout2 = QHBoxLayout()
        self.mission_delay_label = QLabel('미션 TTS 딜레이')
        tts_layout2.addWidget(self.mission_delay_label)
        self.mission_delay_tts = QDoubleSpinBox()
        self.mission_delay_tts.setMinimum(0)
        self.mission_delay_tts.setMaximum(5)
        self.mission_delay_tts.setSingleStep(0.1)
        self.mission_delay_tts.setDecimals(1)
        self.mission_delay_tts.setSuffix(" 초")
        tts_layout2.addWidget(self.mission_delay_tts)
        self.mission_volume_label = QLabel('미션TTS 음량')
        tts_layout2.addWidget(self.mission_volume_label)
        self.mission_volume_tts = QSlider(Qt.Orientation.Horizontal)
        self.mission_volume_tts.setMinimum(0)
        self.mission_volume_tts.setMaximum(100)
        self.mission_volume_tts.setSingleStep(5)
        self.mission_volume_tts.setFixedWidth(100)
        tts_layout2.addWidget(self.mission_volume_tts)
        
        self.btn_tts_preview = QPushButton("미리듣기", self)
        self.btn_tts_preview.clicked.connect(self.preview_tts)
        tts_layout2.addWidget(self.btn_tts_preview)
        
        tts_layout2.addStretch()
        donation_layout.addLayout(tts_layout2)

        num_layout1 = QHBoxLayout()
        self.donation_img_cut_text = QLabel(self)
        self.donation_img_cut_text.setText("왕도네 컷 (치즈):")
        num_layout1.addWidget(self.donation_img_cut_text)
        self.donation_img_cut = QLabel(self)
        self.donation_img_cut.setText("100")
        num_layout1.addWidget(self.donation_img_cut)
        self.donation_img_cut_temp = QLineEdit(self)
        self.donation_img_cut_temp.setValidator(QIntValidator(1, 999999999, self))
        self.donation_img_cut_temp.setText(self.donation_img_cut.text())
        self.donation_img_cut_temp.setFixedWidth(75)
        num_layout1.addWidget(self.donation_img_cut_temp)
        self.donation_img_cut_temp.hide()
        self.edit_button = QPushButton('수정', self)
        self.edit_button.clicked.connect(self.toggle_edit_donation)
        num_layout1.addWidget(self.edit_button)
        num_layout1.addStretch()
        donation_layout.addLayout(num_layout1)

        num_layout2 = QHBoxLayout()
        self.bang_sel_cut_text = QLabel(self)
        self.bang_sel_cut_text.setText("방셀 컷 (치즈):")
        num_layout2.addWidget(self.bang_sel_cut_text)
        self.bang_sel_cut = QLabel(self)
        self.bang_sel_cut.setText("2000")
        num_layout2.addWidget(self.bang_sel_cut)
        self.bang_sel_cut_temp = QLineEdit(self)
        self.bang_sel_cut_temp.setValidator(QIntValidator(1, 999999999, self))
        self.bang_sel_cut_temp.setText(self.bang_sel_cut.text())
        self.bang_sel_cut_temp.setFixedWidth(75)
        num_layout2.addWidget(self.bang_sel_cut_temp)
        self.bang_sel_cut_temp.hide()
        self.edit_button_bang = QPushButton('수정', self)
        self.edit_button_bang.clicked.connect(self.toggle_edit_bang)
        num_layout2.addWidget(self.edit_button_bang)
        num_layout2.addStretch()
        donation_layout.addLayout(num_layout2)
        
        num_layout3 = QHBoxLayout()
        self.sub_gift_cut_text = QLabel(self)
        self.sub_gift_cut_text.setText("구독권 선물 컷 (장):")
        num_layout3.addWidget(self.sub_gift_cut_text)
        self.sub_gift_cut = QLabel(self)
        self.sub_gift_cut.setText("10")
        num_layout3.addWidget(self.sub_gift_cut)
        self.sub_gift_cut_temp = QLineEdit(self)
        self.sub_gift_cut_temp.setValidator(QIntValidator(1, 999999999, self))
        self.sub_gift_cut_temp.setText(self.sub_gift_cut.text())
        self.sub_gift_cut_temp.setFixedWidth(75)
        num_layout3.addWidget(self.sub_gift_cut_temp)
        self.sub_gift_cut_temp.hide()
        self.edit_button_sub_gift = QPushButton('수정', self)
        self.edit_button_sub_gift.clicked.connect(self.toggle_edit_sub_gift)
        num_layout3.addWidget(self.edit_button_sub_gift)
        num_layout3.addStretch()
        donation_layout.addLayout(num_layout3)

        self.toggle_auto_show_img = QToggle(self)
        self.toggle_auto_show_img.setText("왕도네 이미지 자동 표시")
        self.toggle_auto_show_img.setChecked(True)
        donation_layout.addWidget(self.toggle_auto_show_img)

        donation_gif_layout = QHBoxLayout()
        self.donation_gif_label = QLabel('왕도네 움짤')
        donation_gif_layout.addWidget(self.donation_gif_label)
        self.donation_gif1 = QCheckBox("1만", self)
        donation_gif_layout.addWidget(self.donation_gif1)
        self.donation_gif3 = QCheckBox("3만", self)
        donation_gif_layout.addWidget(self.donation_gif3)
        self.donation_gif20 = QCheckBox("20만", self)
        donation_gif_layout.addWidget(self.donation_gif20)
        self.donation_gif50 = QCheckBox("50만", self)
        donation_gif_layout.addWidget(self.donation_gif50)
        self.donation_gif100 = QCheckBox("100만", self)
        donation_gif_layout.addWidget(self.donation_gif100)
        donation_gif_layout.addStretch()
        donation_layout.addLayout(donation_gif_layout)

        self.how_to_auto_show_img = QPushButton("OBS 왕도네 이미지 오버레이 설정법")
        self.how_to_auto_show_img.clicked.connect(self.show_auto_show_img_guide)
        donation_layout.addWidget(self.how_to_auto_show_img)
        layout.addWidget(donation_setting_groupbox)

        video_donation_setting_groupbox = QGroupBox('영도 설정', self)
        layout.addWidget(video_donation_setting_groupbox)
        video_donation_layout = QVBoxLayout(video_donation_setting_groupbox)

        vid_num_layout = QHBoxLayout()
        self.video_price_text = QLabel(self)
        self.video_price_text.setText("영도 단가 (초당 치즈 개수):")
        vid_num_layout.addWidget(self.video_price_text)
        self.video_price = QLabel(self)
        self.video_price.setText("100")
        vid_num_layout.addWidget(self.video_price)
        self.video_price_temp = QLineEdit(self)
        self.video_price_temp.setValidator(QIntValidator(1, 999999999, self))
        self.video_price_temp.setText(self.video_price.text())
        self.video_price_temp.setFixedWidth(75)
        vid_num_layout.addWidget(self.video_price_temp)
        self.video_price_temp.hide()
        self.edit_button_vid = QPushButton('수정', self)
        self.edit_button_vid.clicked.connect(self.toggle_edit_vid)
        vid_num_layout.addWidget(self.edit_button_vid)
        vid_num_layout.addStretch()
        video_donation_layout.addLayout(vid_num_layout)

        chzzk_video_donation_layout = QHBoxLayout()
        self.chzzk_video_url_label = QLabel('치지직 영도 오버레이 URL:')
        chzzk_video_donation_layout.addWidget(self.chzzk_video_url_label)
        self.chzzk_video_url = QLineEdit(self)
        self.chzzk_video_url.setPlaceholderText('')
        self.chzzk_video_url.setEchoMode(QLineEdit.EchoMode.Password)
        chzzk_video_donation_layout.addWidget(self.chzzk_video_url)
        video_donation_layout.addLayout(chzzk_video_donation_layout)

        self.chzzk_video_ui_toggle = QToggle("영도 재생바 표시")
        video_donation_layout.addWidget(self.chzzk_video_ui_toggle)


        self.overlay_disable_gpu = QToggle("영도 오버레이 GPU 가속 비활성화 (프로그램 재시작 시 적용)")
        self.overlay_disable_gpu.setChecked(False)  # 기본값: 꺼짐
        video_donation_layout.addWidget(self.overlay_disable_gpu)

        
        # 영도 후원알림 스킵 토글

        # 영도 후원알림 스킵 토글
        self.overlay_skip_timer = QToggle("영도 후원알림 스킵 (알림음을 꺼야 완전히 스킵됩니다)")
        self.overlay_skip_timer.setChecked(True)  # 기본값: 켜짐
        self.overlay_skip_timer.toggled.connect(self.main_window.update_overlay_skip_timer)
        video_donation_layout.addWidget(self.overlay_skip_timer)

        # 리모컨 영상목록 100개 유지 토글
        self.remote_maintain_100_items = QToggle("리모컨 영상목록 100개 유지하기")
        self.remote_maintain_100_items.setChecked(True)  # 기본값: 켜짐
        self.remote_maintain_100_items.toggled.connect(self.update_maintain_items_setting)
        video_donation_layout.addWidget(self.remote_maintain_100_items)

        # 세로화면 크기 설정 버튼
        self.overlay_size_settings_button = QPushButton("영상 정렬/크기 설정")
        self.overlay_size_settings_button.clicked.connect(self.open_overlay_size_settings)
        video_donation_layout.addWidget(self.overlay_size_settings_button)


        self.google_login_button = QPushButton("Google 로그인 (유튜브 프리미엄 계정 적용)")
        self.google_login_button.clicked.connect(self.main_window.open_google_login)
        video_donation_layout.addWidget(self.google_login_button)

        self.how_to_video_donation_overlay = QPushButton("OBS 영상후원 오버레이 설정법")
        self.how_to_video_donation_overlay.clicked.connect(self.show_video_donation_overlay_guide)
        video_donation_layout.addWidget(self.how_to_video_donation_overlay)
        
        layout.addWidget(video_donation_setting_groupbox)

        file_location_groupbox = QGroupBox('파일 경로 설정', self)
        file_location_layout = QVBoxLayout(file_location_groupbox)

        file_layout = QHBoxLayout()
        self.file_text_donation = QLabel(self)
        self.file_text_donation.setText("왕도네 이미지 저장 폴더:")
        file_layout.addWidget(self.file_text_donation)
        self.file_path_box_donation = QLineEdit(self)
        self.file_path_box_donation.setPlaceholderText('왕도네 이미지를 저장할 폴더 경로를 입력하세요.')
        self.file_path_box_donation.setText(os.path.join(USERPATH, "BCU", "donationimg"))
        self.file_button_donation = QPushButton('폴더 선택..', self)
        self.file_button_donation.clicked.connect(self.open_file_dialog_donation)
        self.file_open_button_donation = QPushButton('열기', self)
        self.file_open_button_donation.clicked.connect(self.open_folder_donation)
        file_layout.addWidget(self.file_path_box_donation)
        file_layout.addWidget(self.file_button_donation)
        file_layout.addWidget(self.file_open_button_donation)
        file_location_layout.addLayout(file_layout)
        
        file_layout1 = QHBoxLayout()
        self.file_text_chat_log = QLabel(self)
        self.file_text_chat_log.setText("채팅 로그 폴더:")
        file_layout1.addWidget(self.file_text_chat_log)
        self.file_path_box_chat_log = QLineEdit(self)
        self.file_path_box_chat_log.setPlaceholderText('채팅 로그 폴더 경로를 입력하세요.')
        self.file_path_box_chat_log.setText(os.path.join(USERPATH, "BCU", "logs"))
        file_layout1.addWidget(self.file_path_box_chat_log)
        self.file_button_chat_log = QPushButton('폴더 선택..', self)
        self.file_button_chat_log.clicked.connect(self.open_file_dialog_chat_log)
        file_layout1.addWidget(self.file_button_chat_log)
        self.file_open_button_chat_log = QPushButton('열기', self)
        self.file_open_button_chat_log.clicked.connect(self.open_folder_chat_log)
        file_layout1.addWidget(self.file_open_button_chat_log)
        file_location_layout.addLayout(file_layout1)
        layout.addWidget(file_location_groupbox)

        api_setting_groupbox = QGroupBox('API 설정', self) # 이름 변경
        layout.addWidget(api_setting_groupbox)
        api_layout = QVBoxLayout(api_setting_groupbox)

        youtube_api_layout = QHBoxLayout()
        self.youtube_api_label = QLabel('YouTube Data API V3 키:')
        youtube_api_layout.addWidget(self.youtube_api_label)
        self.youtube_api_key = QLineEdit(self)
        self.youtube_api_key.setPlaceholderText('')
        self.youtube_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        youtube_api_layout.addWidget(self.youtube_api_key)
        api_layout.addLayout(youtube_api_layout)

        chzzk_api_client_id_layout = QHBoxLayout()
        self.chzzk_api_client_id_label = QLabel('치지직 API Client ID:')
        chzzk_api_client_id_layout.addWidget(self.chzzk_api_client_id_label)
        self.chzzk_api_client_id = QLineEdit(self)
        self.chzzk_api_client_id.setPlaceholderText('')
        self.chzzk_api_client_id.setEchoMode(QLineEdit.EchoMode.Password)
        chzzk_api_client_id_layout.addWidget(self.chzzk_api_client_id)
        api_layout.addLayout(chzzk_api_client_id_layout)

        chzzk_api_client_secret_layout = QHBoxLayout()
        self.chzzk_api_client_secret_label = QLabel('치지직 API Client Secret:')
        chzzk_api_client_secret_layout.addWidget(self.chzzk_api_client_secret_label)
        self.chzzk_api_client_secret = QLineEdit(self)
        self.chzzk_api_client_secret.setPlaceholderText('')
        self.chzzk_api_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        chzzk_api_client_secret_layout.addWidget(self.chzzk_api_client_secret)
        api_layout.addLayout(chzzk_api_client_secret_layout)
        layout.addWidget(api_setting_groupbox)

        etc_setting_groupbox = QGroupBox('기타 설정', self)
        layout.addWidget(etc_setting_groupbox)
        etc_layout = QVBoxLayout(etc_setting_groupbox)

        tab_settings_button = QPushButton("탭 순서 및 표시 설정")
        tab_settings_button.clicked.connect(self.open_tab_management_dialog)
        etc_layout.addWidget(tab_settings_button)

        backup_layout = QHBoxLayout()
        self.backup_button = QPushButton('설정 백업')
        self.backup_button.clicked.connect(self.open_file_dialog_backup)
        backup_layout.addWidget(self.backup_button)
        self.restore_button = QPushButton('설정 복원')
        self.restore_button.clicked.connect(self.open_file_dialog_restore)
        backup_layout.addWidget(self.restore_button)
        etc_layout.addLayout(backup_layout)

        self.kanetv8 = QToggle(self)
        self.kanetv8.setText('케인인님 내수용 모드 (재시작 시 적용됨)')
        self.kanetv8.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        if self.main_window.kanetv8temp.isChecked():
            self.kanetv8.toggle()
        etc_layout.addWidget(self.kanetv8)

        self.devmode_toggle = QToggle(self)
        self.devmode_toggle.setText('개발자 모드')
        self.devmode_toggle.clicked.connect(self.toggle_devmode)
        etc_layout.addWidget(self.devmode_toggle)

        button_layout = QHBoxLayout()
        self.login_reset_button = QPushButton("로그인 초기화")
        self.login_reset_button.clicked.connect(self.main_window.login_reset)
        button_layout.addWidget(self.login_reset_button)
        self.reset_settings_button = QPushButton("설정 초기화")
        self.reset_settings_button.clicked.connect(self.reset_settings)
        button_layout.addWidget(self.reset_settings_button)
        etc_layout.addLayout(button_layout)
        
        self.remember_window_check = QToggle(self)
        self.remember_window_check.setText('프로그램 창 위치 및 크기 기억')
        self.remember_window_check.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        etc_layout.addWidget(self.remember_window_check)

        layout.addWidget(etc_setting_groupbox)

        self.about_page = QPushButton('프로그램 정보', self)
        self.about_page.clicked.connect(self.show_dialog_about)
        layout.addWidget(self.about_page)

        layout.addStretch()
        frame.setLayout(layout)

        scroll_area = QScrollArea(self)
        scroll_area.setWidget(frame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setGeometry(0, 0, 600, 400)

        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll_area)

        self.save_settings_button = QPushButton('설정 저장', self)
        self.save_settings_button.clicked.connect(self.on_save_settings_clicked)
        tab_layout.addWidget(self.save_settings_button)

        self.setLayout(tab_layout)
        
        self.load_settings_from_main()


    ##### 설정 탭 관련 함수 #####
    
    def load_settings_from_main(self):
        """메인 윈도우의 설정 값을 이 탭의 위젯에 적용합니다."""
        mw = self.main_window # 편의를 위한 별칭
        self.file_path_box_chat_log.setText(mw.file_path_box_chat_log.text())
        self.file_path_box_donation.setText(mw.file_path_box_donation.text())
        self.donation_img_cut.setText(mw.donation_img_cut.text())
        self.sub_gift_cut.setText(mw.sub_gift_cut.text())
        self.video_price.setText(mw.video_price.text())
        self.bang_sel_cut.setText(mw.bang_sel_cut.text())
        self.mission_delay_tts.setValue(mw.mission_delay_tts.value())
        self.commision_rate.setValue(mw.commision_rate.value())
        self.mission_volume_tts.setValue(mw.mission_volume_tts.value())
        self.toggle_auto_show_img.setChecked(mw.toggle_auto_show_img.isChecked())
        self.auto_chat_popup_start.setChecked(mw.auto_chat_popup_start.isChecked())
        self.auto_chatroom_connector_start.setChecked(mw.auto_chatroom_connector_start.isChecked())
        self.auto_delete.setChecked(mw.auto_delete.isChecked())
        self.mission_read_req_tts.setChecked(mw.mission_read_req_tts.isChecked())
        self.mission_read_add_tts.setChecked(mw.mission_read_add_tts.isChecked())
        self.mission_read_success_tts.setChecked(mw.mission_read_success_tts.isChecked())
        self.mission_read_fail_tts.setChecked(mw.mission_read_fail_tts.isChecked())
        self.theme_check.setChecked(mw.theme_check.isChecked())
        self.auto_mission_approve.setChecked(mw.auto_mission_approve.isChecked())
        self.donation_gif1.setChecked(mw.donation_gif1.isChecked())
        self.donation_gif3.setChecked(mw.donation_gif3.isChecked())
        self.donation_gif20.setChecked(mw.donation_gif20.isChecked())
        self.donation_gif50.setChecked(mw.donation_gif50.isChecked())
        self.donation_gif100.setChecked(mw.donation_gif100.isChecked())
        self.chzzk_video_url.setText(mw.chzzk_video_url.text())
        self.extra_donation_settings.setChecked(mw.extra_donation_settings.isChecked())
        self.show_donation_list_toggle.setChecked(mw.show_donation_list_toggle.isChecked())
        self.devmode_toggle.setChecked(mw.devmode_toggle.isChecked())
        self.auto_notice_toggle.setChecked(mw.auto_notice_toggle.isChecked())
        self.auto_notice_textbox.setText(mw.auto_notice_textbox.text())
        self.youtube_api_key.setText(mw.youtube_api_key.text())
        self.chzzk_api_client_id.setText(mw.chzzk_api_client_id.text().strip().replace(" ",""))
        self.chzzk_api_client_secret.setText(mw.chzzk_api_client_secret.text().strip().replace(" ",""))
        self.startup_tab_combobox.setCurrentText(mw.startup_tab_combobox.currentText())
        # kanetv8은 __init__에서 이미 처리됨
        
        # 메인 윈도우의 해당 위젯들을 이 탭의 위젯으로 교체
        mw.file_path_box_chat_log = self.file_path_box_chat_log
        mw.file_path_box_donation = self.file_path_box_donation
        mw.donation_img_cut = self.donation_img_cut
        mw.sub_gift_cut = self.sub_gift_cut
        mw.video_price = self.video_price
        mw.bang_sel_cut = self.bang_sel_cut
        mw.mission_delay_tts = self.mission_delay_tts
        mw.mission_volume_tts = self.mission_volume_tts
        mw.toggle_auto_show_img = self.toggle_auto_show_img
        mw.auto_chat_popup_start = self.auto_chat_popup_start
        self.auto_start_chzzk_overlay.setChecked(mw.auto_start_chzzk_overlay.isChecked())
        mw.auto_start_chzzk_overlay = self.auto_start_chzzk_overlay
        mw.auto_chatroom_connector_start = self.auto_chatroom_connector_start
        mw.auto_delete = self.auto_delete
        mw.auto_starton_close_label = self.auto_starton_close_label
        mw.mission_read_req_tts = self.mission_read_req_tts
        mw.mission_read_add_tts = self.mission_read_add_tts
        mw.mission_read_success_tts = self.mission_read_success_tts
        mw.mission_read_fail_tts = self.mission_read_fail_tts
        mw.theme_check = self.theme_check
        mw.auto_mission_approve = self.auto_mission_approve
        mw.donation_gif1 = self.donation_gif1
        mw.donation_gif3 = self.donation_gif3
        mw.donation_gif20 = self.donation_gif20
        mw.donation_gif50 = self.donation_gif50
        mw.donation_gif100 = self.donation_gif100
        mw.chzzk_video_url = self.chzzk_video_url
        self.chzzk_video_ui_toggle.setChecked(mw.chzzk_video_ui_toggle.isChecked()) # 값 로드
        mw.chzzk_video_ui_toggle = self.chzzk_video_ui_toggle # 참조 교체
        mw.extra_donation_settings = self.extra_donation_settings
        mw.show_donation_list_toggle = self.show_donation_list_toggle
        mw.devmode_toggle = self.devmode_toggle
        mw.auto_notice_toggle = self.auto_notice_toggle
        mw.auto_notice_textbox = self.auto_notice_textbox
        mw.youtube_api_key = self.youtube_api_key
        mw.chzzk_api_client_id = self.chzzk_api_client_id
        mw.chzzk_api_client_secret = self.chzzk_api_client_secret
        mw.kanetv8 = self.kanetv8
        mw.login_reset_button = self.login_reset_button
        mw.startup_tab_combobox = self.startup_tab_combobox
        mw.startup_tab_combobox = self.startup_tab_combobox
        
        # overlay_alignment는 문자열 값으로 처리 (위젯 제거됨)
        # self.overlay_alignment = getattr(mw, 'overlay_alignment', 'top-center')
        # 하지만 SettingsTab 인스턴스 변수로 저장할 필요가 있을까? open_overlay_size_settings에서 직접 mw 접근하거나 getattr 사용하면 됨.
        # 일단 여기서는 패스.
        
        self.remember_window_check.setChecked(mw.remember_window_check.isChecked())
        mw.remember_window_check = self.remember_window_check

        self.remember_chat_popup_check.setChecked(mw.remember_chat_popup_check.isChecked())
        mw.remember_chat_popup_check = self.remember_chat_popup_check

        self.overlay_disable_gpu.setChecked(mw.overlay_disable_gpu.isChecked())
        mw.overlay_disable_gpu = self.overlay_disable_gpu

        self.overlay_skip_timer.setChecked(mw.overlay_skip_timer.isChecked())
        mw.overlay_skip_timer = self.overlay_skip_timer

        self.remote_maintain_100_items.setChecked(mw.remote_maintain_100_items.isChecked())
        mw.remote_maintain_100_items = self.remote_maintain_100_items

        # overlay_portrait_width는 위젯이 아니라 값이므로 직접 복사
        self.overlay_portrait_width = getattr(mw, 'overlay_portrait_width', 576)
        self.overlay_portrait_height = getattr(mw, 'overlay_portrait_height', 1024)

        # kanetv8temp는 메인 윈도우에 남겨둠

    def update_maintain_items_setting(self, enabled):
        """토글 변경 시 브라우저의 maintainItemsEnabled 값을 즉시 업데이트"""
        js_code = f"""
            localStorage.setItem('maintainItemsEnabled', JSON.stringify({str(enabled).lower()}));
            if (typeof maintainItemsEnabled !== 'undefined') {{
                maintainItemsEnabled = {str(enabled).lower()};
            }}
        """
        if hasattr(self.main_window, 'remote_tab') and hasattr(self.main_window.remote_tab, 'chzzk_remote_browser'):
            self.main_window.remote_tab.chzzk_remote_browser.page().runJavaScript(js_code)

    def preview_tts(self):
        self.main_window.run_tts_preview("TTS 미리듣기입니다. 잘 들리시나요?")


    def on_alignment_changed(self):
        """정렬 설정 변경 시 메인 윈도우를 통해 오버레이에 즉시 적용"""
        # overlay_alignment_combobox가 제거되었으므로, self.overlay_alignment 값을 직접 사용
        align = self.overlay_alignment
        
        width = getattr(self, 'overlay_portrait_width', 576)
        height = getattr(self, 'overlay_portrait_height', 1024)
        
        # 설정 팝업이 열려있다면 그 값을 사용
        if hasattr(self, 'overlay_settings_dialog') and self.overlay_settings_dialog and not getattr(self.overlay_settings_dialog, '_closing', True):
            width = self.overlay_settings_dialog.portrait_width
            height = self.overlay_settings_dialog.portrait_height
        
        self.main_window.update_overlay_live(width, height, align)

    def toggle_edit_vid(self):
        if self.edit_button_vid.text() == '수정':
            self.video_price_temp.setText(self.video_price.text())
            self.video_price.hide()
            self.video_price_temp.show()
            self.edit_button_vid.setText('적용')
        else:
            self.video_price.setText(self.video_price_temp.text())
            self.main_window.latest_video = []
            self.main_window.latest_donation = []
            self.main_window.is_msg = False
            QApplication.processEvents()
            self.main_window.remote_tab.image_list_cheese.clear()
            QApplication.processEvents()
            self.main_window.remote_tab.result_box_cheese.clear()
            QApplication.processEvents()
            self.main_window.remote_tab.result_box_cheese_temp.clear()
            QApplication.processEvents()
            self.video_price.show()
            self.video_price_temp.hide()
            QApplication.processEvents()
            self.edit_button_vid.setText('수정')
    
    def toggle_edit_donation(self):
        if self.edit_button.text() == '수정':
            self.donation_img_cut_temp.setText(self.donation_img_cut.text())
            self.donation_img_cut.hide()
            self.donation_img_cut_temp.show()
            self.edit_button.setText('적용')
        else:
            self.donation_img_cut.setText(self.donation_img_cut_temp.text())
            self.donation_img_cut.show()
            self.donation_img_cut_temp.hide()
            self.edit_button.setText('수정')
    
    def toggle_edit_sub_gift(self):
        if self.edit_button_sub_gift.text() == '수정':
            self.sub_gift_cut_temp.setText(self.sub_gift_cut.text())
            self.sub_gift_cut.hide()
            self.sub_gift_cut_temp.show()
            self.edit_button_sub_gift.setText('적용')
        else:
            self.sub_gift_cut.setText(self.sub_gift_cut_temp.text())
            self.sub_gift_cut.show()
            self.sub_gift_cut_temp.hide()
            self.edit_button_sub_gift.setText('수정')

    def toggle_edit_bang(self):
        if self.edit_button_bang.text() == '수정':
            self.bang_sel_cut_temp.setText(self.bang_sel_cut.text())
            self.bang_sel_cut.hide()
            self.bang_sel_cut_temp.show()
            self.edit_button_bang.setText('적용')
        else:
            self.bang_sel_cut.setText(self.bang_sel_cut_temp.text())
            self.bang_sel_cut.show()
            self.bang_sel_cut_temp.hide()
            self.edit_button_bang.setText('수정')

    def backup_config(self, folder):
        reply = QMessageBox.question(self, '백업 안내', '설정과 채팅 로그 파일이 백업됩니다.\n네이버 로그인 정보는 백업되지 않습니다. 계속하시겠습니까?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                log_folder =  self.file_path_box_chat_log.text()
                config_file_path = os.path.join(USERPATH, "BCU", "BCU.ini")
                ban_config_file_path = os.path.join(USERPATH, "BCU", "bansettings.ini")
                browser_zoom_path = os.path.join(USERPATH, "BCU", "browser_zoom.ini")
                chat_emoticons_path = os.path.join(USERPATH, "BCU", "chat_emoticons.json")
                overlay_preview_settings_path = os.path.join(USERPATH, "BCU", "overlay_preview_settings.ini")
                backup_folder_path = os.path.join(folder, "BCU_Backup")
                if not os.path.exists(backup_folder_path):
                    os.makedirs(backup_folder_path)
                if os.path.isfile(config_file_path):
                    shutil.copy(config_file_path, backup_folder_path)
                if os.path.isfile(ban_config_file_path):
                    shutil.copy(ban_config_file_path, backup_folder_path)
                if os.path.isfile(browser_zoom_path):
                    shutil.copy(browser_zoom_path, backup_folder_path)
                if os.path.isfile(chat_emoticons_path):
                    shutil.copy(chat_emoticons_path, backup_folder_path)
                if os.path.isfile(overlay_preview_settings_path):
                    shutil.copy(overlay_preview_settings_path, backup_folder_path)
                log_backup_folder_path = os.path.join(backup_folder_path, "logs")
                if not os.path.exists(log_backup_folder_path):
                    os.makedirs(log_backup_folder_path)
                if os.path.exists(log_folder):
                    for file_name in os.listdir(log_folder):
                        file_path = os.path.join(log_folder, file_name)
                        if os.path.isfile(file_path):
                            shutil.copy(file_path, log_backup_folder_path)
                QMessageBox.information(self, '백업 완료', '설정과 채팅 로그 파일이 BCU_Backup 폴더에 백업되었습니다. 해당 폴더를 잘 저장하여주세요.')
            except Exception as e:
                QMessageBox.critical(self, '백업 실패', f'백업 중 오류가 발생했습니다: {str(e)}')
    
    def restore_config(self, folder):
        reply = QMessageBox.question(self, '경고', '복원할 경우 기존 설정과 채팅 로그 파일은 모두 덮어씌워지며 복구가 불가합니다.\n정말 계속하시겠습니까?', 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                config_file_path = os.path.join(USERPATH, "BCU", "BCU.ini")
                ban_config_file_path = os.path.join(USERPATH, "BCU", "bansettings.ini")
                browser_zoom_path = os.path.join(USERPATH, "BCU", "browser_zoom.ini")
                chat_emoticons_path = os.path.join(USERPATH, "BCU", "chat_emoticons.json")
                overlay_preview_settings_path = os.path.join(USERPATH, "BCU", "overlay_preview_settings.ini")
                backup_folder_path = os.path.join(folder, "")
                if not os.path.isfile(os.path.join(backup_folder_path, "BCU.ini")):
                    backup_folder_path = os.path.join(folder, "BCU_Backup")
                log_backup_folder_path = os.path.join(backup_folder_path, "logs")
                if not os.path.exists(log_backup_folder_path):
                    QMessageBox.critical(self, '복원 실패', '백업 폴더에 채팅 로그 폴더가 존재하지 않습니다.\n복원할 수 없습니다.')
                    return
                if not os.path.isfile(os.path.join(backup_folder_path, "BCU.ini")):
                    QMessageBox.critical(self, '복원 실패', '백업 폴더에 설정 파일이 존재하지 않습니다.\n복원할 수 없습니다.')
                    return
                
                settings = QSettings(os.path.join(USERPATH, "BCU", "BCU.ini"), QSettings.Format.IniFormat)
                log_folder_path = settings.value('file_path_box_chat_log', os.path.join(USERPATH, "BCU", "logs"))
                os.makedirs(os.path.dirname(log_folder_path), exist_ok=True)
                if os.path.isfile(os.path.join(backup_folder_path, "BCU.ini")):
                    shutil.copy(os.path.join(backup_folder_path, "BCU.ini"), config_file_path)
                if os.path.isfile(os.path.join(backup_folder_path, "bansettings.ini")):
                    shutil.copy(os.path.join(backup_folder_path, "bansettings.ini"), ban_config_file_path)
                if os.path.isfile(os.path.join(backup_folder_path, "browser_zoom.ini")):
                    shutil.copy(os.path.join(backup_folder_path, "browser_zoom.ini"), browser_zoom_path)
                if os.path.isfile(os.path.join(backup_folder_path, "chat_emoticons.json")):
                    shutil.copy(os.path.join(backup_folder_path, "chat_emoticons.json"), chat_emoticons_path)
                if os.path.isfile(os.path.join(backup_folder_path, "overlay_preview_settings.ini")):
                    shutil.copy(os.path.join(backup_folder_path, "overlay_preview_settings.ini"), overlay_preview_settings_path)
                if os.path.exists(log_folder_path):
                    for file_name in os.listdir(log_folder_path):
                        file_path = os.path.join(log_folder_path, file_name)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                shutil.copytree(log_backup_folder_path, log_folder_path, dirs_exist_ok=True)
                
                QMessageBox.information(self, '복원 완료', '설정과 채팅 로그 파일이 복원되었습니다.\n프로그램을 종료합니다. 종료 후 다시 실행해주세요.')
                self.main_window.is_close_without_save_setting = True
                self.main_window.close()
            except Exception as e:
                QMessageBox.critical(self, '복원 실패', f'복원 중 오류가 발생했습니다: {str(e)}')

    def open_file_dialog_chat_log(self):
        folder = QFileDialog.getExistingDirectory(self, "채팅 로그 파일을 저장할 폴더를 선택하세요", os.path.join(USERPATH, "BCU", "logs"))
        if folder:
            self.file_path_box_chat_log.setText(folder.replace("/", "\\"))

    def open_file_dialog_donation(self):
        folder = QFileDialog.getExistingDirectory(self, "왕도네 이미지를 저장할 폴더를 선택하세요.", os.path.join(USERPATH, "BCU", "donationimg"))
        if folder:
            self.file_path_box_donation.setText(folder.replace("/", "\\"))
    
    def open_file_dialog_backup(self):
        folder = QFileDialog.getExistingDirectory(self, "설정과 로그 파일을 백업할 폴더를 선택하세요.", f"{USERPATH}")
        if folder:
            self.backup_config(folder.replace("/", "\\"))
    
    def open_file_dialog_restore(self):
        folder = QFileDialog.getExistingDirectory(self, "설정과 로그 파일을 복원할 폴더를 선택하세요.", f"{USERPATH}")
        if folder:
            self.restore_config(folder.replace("/", "\\"))
    
    def open_folder_donation(self):
        os.startfile(self.file_path_box_donation.text())

    def open_folder_chat_log(self):
        os.startfile(self.file_path_box_chat_log.text())

    # --- 가이드 다이얼로그 호출 (메인 윈도우의 공용 함수 호출) ---
    def show_auto_show_img_guide(self):
        path = f"file:///{USERPATH_SLASH}/BCU/donationimg.html" # 경로 설정
        content = [
            {'type': 'label', 'text': '1. OBS에서 브라우저 소스를 추가하세요.'},
            {'type': 'label', 'text': '2. URL을 다음으로 설정하세요.'},
            {'type': 'textbox', 'text': '{path}', 'height': 50},
            {'type': 'label', 'text': '3. 크기를 360 x 360으로 설정하세요.'},
            {'type': 'stretch'}
        ]
        self.how_to_auto_show_img_dialog = GuideDialog('OBS 왕도네 이미지 오버레이 설정법', (400, 0), content, path=path, parent=self)
        self.how_to_auto_show_img_dialog.show()
    
    def show_text_overlay_guide(self):
        path = f"file:///{USERPATH_SLASH}/BCU/ydText.html" # 경로 설정
        content = [
            {'type': 'label', 'text': '1. OBS에서 브라우저 소스를 추가하세요.'},
            {'type': 'label', 'text': '2. URL을 다음으로 설정하세요.'},
            {'type': 'textbox', 'text': '{path}', 'height': 50},
            {'type': 'label', 'text': '3. 크기를 1500 x 90으로 설정하세요.\n(너비는 마음대로 설정 가능합니다)'},
            {'type': 'stretch'}
        ]
        self.how_to_text_overlay_dialog = GuideDialog('OBS 텍스트 오버레이 설정법', (400, 0), content, path=path, parent=self)
        self.how_to_text_overlay_dialog.show()
    
    def show_prediction_overlay_guide(self):
        path = f"file:///{USERPATH_SLASH}/BCU/prediction_overlay.html" # 경로 설정
        content = [
            {'type': 'label', 'text': '1. OBS에서 브라우저 소스를 추가하세요.'},
            {'type': 'label', 'text': '2. URL을 다음으로 설정하세요.'},
            {'type': 'textbox', 'text': '{path}', 'height': 50},
            {'type': 'label', 'text': '3. 크기를 600 x 150으로 설정하세요. (항목이 많아지면 가로 길이를 늘려주세요.)'},
            {'type': 'stretch'}
        ]
        self.how_to_prediction_overlay_dialog = GuideDialog('OBS 승부예측 오버레이 설정법', (400, 0), content, path=path, parent=self)
        self.how_to_prediction_overlay_dialog.show()

    def show_video_donation_overlay_guide(self):
        content = [
            {'type': 'label', 'text': '1. 설정에서 치지직 영상 후원 알림 URL을 붙여넣으세요.'},
            {'type': 'label', 'text': '2. 유튜브 프리미엄을 적용하여 광고 제거를 하시려면, Google 로그인 버튼을 눌러 로그인 후 창을 꺼주세요.'},
            {'type': 'label', 'text': '3. 영상후원 탭에서 영상후원 오버레이 버튼을 눌러 오버레이를 실행하세요.'},
            {'type': 'label', 'text': '4. OBS에서 윈도우 캡쳐로 오버레이를 캡쳐하세요. 캡쳐 방식을 [Windows 10 (1903 이상)] 으로 하고, 윈도우 일치 우선순위를 [제목이 일치하는 창 찾기]로 설정하세요.'},
            {'type': 'label', 'text': '5. OBS 상단바의 [독 > 사용자 브라우저 독]을 선택하고, 다음 URL로 음량 조절 독을 추가하세요.'},
            {'type': 'textbox', 'text': 'http://127.0.0.1:5000/obs_volume_control', 'height': 50},
            {'type': 'stretch'}
        ]
        self.how_to_video_donation_overlay_dialog = GuideDialog('OBS 영상후원 오버레이 설정법', (400, 0), content, parent=self)
        self.how_to_video_donation_overlay_dialog.show()

    def show_dialog_about(self):
        self.about_dialog = AboutDialog()
        self.about_dialog.setGeometry(
            self.main_window.geometry().center().x() - self.about_dialog.sizeHint().width() // 2,
            self.main_window.geometry().center().y() - self.about_dialog.sizeHint().height() // 2,
            self.about_dialog.sizeHint().width(),
            self.about_dialog.sizeHint().height()
        )
        self.about_dialog.show()

    def auto_ban_setting_menu(self):
        self.ban_dialog = AutoBanSettingMenuDialog(self, self.theme_check.isChecked())
        self.ban_dialog.setGeometry(
                self.main_window.geometry().center().x() - 600 // 2,
                self.main_window.geometry().center().y() - 600 // 2,
                600, 600
            )
        self.ban_dialog.show()

    def open_tab_management_dialog(self):
        """탭 관리 대화창을 엽니다."""
        dialog = TabManagementDialog(self.main_window, self.main_window)
        dialog.exec() # 대화창이 닫힐 때까지 다른 작업을 막음

    # --- 메인 윈도우 기능 호출 ---
    def toggle_devmode(self):
        self.main_window.toggle_devmode()

    def extra_donation_settings_func(self):
        self.main_window.extra_donation_settings_func()
    
    def show_donation_list_toggle_func(self):
        self.main_window.show_donation_list_toggle_func()

    def reset_settings(self):
        reply = QMessageBox.question(self, '설정 초기화', '모든 설정이 초기화되고 프로그램이 재시작됩니다.\n계속하시겠습니까?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                config_path = os.path.join(USERPATH, "BCU", "BCU.ini")
                ban_config_path = os.path.join(USERPATH, "BCU", "bansettings.ini")
                if os.path.exists(config_path):
                    os.remove(config_path)
                if os.path.exists(ban_config_path):
                    os.remove(ban_config_path)
                
                QMessageBox.information(self, '초기화 완료', '설정이 초기화되었습니다. 프로그램을 재시작합니다.')
                
                # 프로그램 재시작
                import sys
                os.execl(sys.executable, sys.executable, *sys.argv)
            except Exception as e:
                QMessageBox.critical(self, '오류', f'초기화 중 오류가 발생했습니다: {e}')

    def on_save_settings_clicked(self):
        self.main_window.save_settings()
        QMessageBox.information(self, '설정 저장', '설정이 저장되었습니다.')

    def open_overlay_size_settings(self):
        """세로화면 크기 설정 팝업을 엽니다."""
        # 현재 저장된 세로화면 너비/높이 가져오기
        current_width = getattr(self, 'overlay_portrait_width', 576)
        current_height = getattr(self, 'overlay_portrait_height', 1024)
        
        # 현재 정렬 설정 가져오기 (초기값으로 전달, 이후 실시간 업데이트)
        # 기존 콤보박스 대신 저장된 값 사용. 없으면 'top-center' 기본값
        current_alignment = getattr(self, 'overlay_alignment', 'top-center')
        
        # 설정 팝업 생성
        self.overlay_settings_dialog = OverlaySettingsDialog(current_width, current_height, self.main_window, parent=None)
        # 초기 정렬 설정 (PreviewWidget 내부 업데이트 위해)
        self.overlay_settings_dialog.update_alignment(current_alignment)
        
        # 실시간 업데이트 연결
        def on_size_changed(w, h):
            self.overlay_portrait_width = w
            self.overlay_portrait_height = h
            # alignment는 별도 시그널로 처리하거나 현재 값 유지
            align = getattr(self, 'overlay_alignment', 'top-center')
            self.main_window.update_overlay_live(w, h, align)
            self.main_window.save_settings()
            
        def on_align_changed(align):
            self.overlay_alignment = align
            w = self.overlay_portrait_width
            h = self.overlay_portrait_height
            self.main_window.update_overlay_live(w, h, align)
            self.main_window.save_settings()
            
        def on_include_text_changed(include_text):
            # 오버레이에 직접 전달
            if hasattr(self.main_window, 'video_donation_tab') and self.main_window.video_donation_tab:
                if hasattr(self.main_window.video_donation_tab, 'overlay') and self.main_window.video_donation_tab.overlay:
                    if hasattr(self.main_window.video_donation_tab.overlay, 'set_include_text'):
                        self.main_window.video_donation_tab.overlay.set_include_text(include_text)
            
        self.overlay_settings_dialog.settings_changed.connect(on_size_changed)
        self.overlay_settings_dialog.align_changed.connect(on_align_changed)
        self.overlay_settings_dialog.include_text_changed.connect(on_include_text_changed)
        
        # 창 위치 설정 (중앙)
        screen_geo = QApplication.primaryScreen().geometry()
        x = screen_geo.width() // 2 - 400 # Width 800/2
        y = screen_geo.height() // 2 - 300
        self.overlay_settings_dialog.move(x, y)
        
        self.overlay_settings_dialog.show()
        self.overlay_settings_dialog.show()