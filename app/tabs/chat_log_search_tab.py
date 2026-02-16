import sys
import os
import traceback
import clipboard
import threading
import asyncio
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QCheckBox, QButtonGroup, QComboBox, 
                             QTextEdit, QLabel, QSlider, QFrame, QMessageBox, 
                             QApplication)
from PyQt6.QtGui import QFont, QIcon, QIntValidator
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSlot

from app.constants import GLOBALFONTSIZE
from app.resources import resource_path
from app.ui_widgets import QToggle

class ChatLogSearchTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.stop_signal = False
        self.result_chat_done = False
        
        layout = QVBoxLayout()

        input_layout = QHBoxLayout()
        self.search_type_combo = QComboBox(self)
        self.search_type_combo.addItems(["아이디/닉네임", "채팅 내용"])
        self.search_type_combo.setFixedWidth(120)
        self.search_type_combo.currentTextChanged.connect(self.update_ui_for_mode)
        input_layout.addWidget(self.search_type_combo)

        self.input_box_chat_log = QLineEdit(self)
        self.input_box_chat_log.setPlaceholderText('닉네임 또는 아이디를 입력하세요.')
        self.input_box_chat_log.returnPressed.connect(lambda: self.search_log(False))
        input_layout.addWidget(self.input_box_chat_log)

        self.search_button_chat_log = QPushButton(self.main_window.CHAT_SEARCH_BUTTON_TEXT, self)
        self.search_button_chat_log.setFixedWidth(100)
        self.search_button_chat_log.clicked.connect(lambda: self.search_log(False))
        input_layout.addWidget(self.search_button_chat_log)

        self.search_stop_button_chat_log = QPushButton("검색 중지", self)
        self.search_stop_button_chat_log.setFixedWidth(100)
        self.search_stop_button_chat_log.clicked.connect(self.search_stop)
        input_layout.addWidget(self.search_stop_button_chat_log)
        self.search_stop_button_chat_log.hide()

        self.search_button_chat_moa = QPushButton("채팅 모아보기", self)
        self.search_button_chat_moa.clicked.connect(self.toggle_chatMoa)
        self.search_button_chat_moa.setCheckable(True)
        input_layout.addWidget(self.search_button_chat_moa)

        layout.addLayout(input_layout)

        optimize_layout = QHBoxLayout()
        self.search_chat_all = QCheckBox('모든 채팅 검색', self)
        optimize_layout.addWidget(self.search_chat_all)
        self.search_chat_partial = QCheckBox('최근 채팅 검색', self)
        optimize_layout.addWidget(self.search_chat_partial)
        
        self.button_group_chat_log = QButtonGroup(self)
        self.button_group_chat_log.addButton(self.search_chat_all)
        self.button_group_chat_log.addButton(self.search_chat_partial)
        self.search_chat_partial.toggle()
        self.button_group_chat_log.setExclusive(True)

        self.ignore_space_check = QCheckBox('공백/대소문자 무시', self)
        optimize_layout.addWidget(self.ignore_space_check)
        optimize_layout.addStretch()
        layout.addLayout(optimize_layout)

        search_option_layout = QHBoxLayout()
        self.num_text_chat_log = QLabel(self)
        self.num_text_chat_log.setText("검색할 최근 채팅 수:")
        search_option_layout.addWidget(self.num_text_chat_log)

        self.input_num_box_chat_log = QLineEdit(self)
        self.input_num_box_chat_log.setValidator(QIntValidator(1,999999999,self))
        self.input_num_box_chat_log.setText("1000")
        self.input_num_box_chat_log.setFixedWidth(100)
        search_option_layout.addWidget(self.input_num_box_chat_log)
        search_option_layout.addStretch()
        layout.addLayout(search_option_layout)

        TTSLayout = QHBoxLayout()
        self.moa_chat_read_tts = QToggle(self)
        self.moa_chat_read_tts.setText("TTS 읽어주기")
        self.moa_chat_read_tts.clicked.connect(self.moa_chat_read_ttsfunc)
        TTSLayout.addWidget(self.moa_chat_read_tts)

        self.moa_volume_label = QLabel('음량 ')
        TTSLayout.addWidget(self.moa_volume_label)

        self.moa_volume_tts = QSlider(Qt.Orientation.Horizontal)
        self.moa_volume_tts.setMinimum(0)
        self.moa_volume_tts.setMaximum(100)
        self.moa_volume_tts.setSingleStep(5)
        self.moa_volume_tts.setFixedWidth(100)
        TTSLayout.addWidget(self.moa_volume_tts)

        self.stop_tts_button1 = QPushButton("TTS 넘기기", self)
        self.stop_tts_button1.clicked.connect(self.main_window.stop_tts)
        self.stop_tts_button1.setIcon(QIcon(resource_path(r'.\resources\icon\skip.png')))
        self.stop_tts_button1.setIconSize(QSize(20,20))
        self.stop_tts_button1.setFixedWidth(200)
        TTSLayout.addWidget(self.stop_tts_button1)
        TTSLayout.addStretch()
        layout.addLayout(TTSLayout)

        search_button_layout = QHBoxLayout()

        self.copy_user_id_button = QPushButton("아이디 복사", self)
        self.copy_user_id_button.clicked.connect(self.copy_id)
        search_button_layout.addWidget(self.copy_user_id_button)

        self.studio_restriction_popup_button = QPushButton("  스튜디오 활동제한", self)
        self.studio_restriction_popup_button.clicked.connect(self.main_window.open_studio_restriction)
        self.studio_restriction_popup_button.setIcon(QIcon(resource_path(r'.\resources\icon\popup.png')))
        search_button_layout.addWidget(self.studio_restriction_popup_button)
        
        self.chzzk_user_profile_button = QPushButton("  유저 정보 보기 [밴 기능 접근]", self)
        self.chzzk_user_profile_button.clicked.connect(self.main_window.open_chzzk_user_profile)
        self.chzzk_user_profile_button.setIcon(QIcon(resource_path(r'.\resources\icon\popup.png')))
        search_button_layout.addWidget(self.chzzk_user_profile_button)
        layout.addLayout(search_button_layout)

        ban_button_layout = QHBoxLayout()
        ban_frame0 = QFrame(self)
        ban_frame0layout = QHBoxLayout(ban_frame0)
        ban_frame0layout.setContentsMargins(0, 0, 0, 0)
        self.temp_restrict_duration_combo_box = QComboBox(self)
        self.temp_restrict_duration_combo_box.addItems(["1회 (30초)", "2회 (1분)", "3회 (10분)"])
        self.temp_restrict_duration_combo_box.setFixedWidth(110)
        ban_frame0layout.addWidget(self.temp_restrict_duration_combo_box)
        self.temp_ban_button_cm = QPushButton("임시 제한", self)
        self.temp_ban_button_cm.clicked.connect(lambda: self.manager("임시 제한", self.temp_restrict_duration_combo_box.currentIndex() + 1, self.temp_restrict_duration_combo_box.currentText()))
        ban_frame0layout.addWidget(self.temp_ban_button_cm)
        ban_button_layout.addWidget(ban_frame0)

        ban_frame = QFrame(self)
        ban_frame_layout = QHBoxLayout(ban_frame)
        ban_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.temp_ban_duration_combo_box = QComboBox(self)
        self.temp_ban_duration_combo_box.addItems(["1 일", "3 일", "7 일", "15 일", "30 일", "90 일", "영구"])
        self.temp_ban_duration_combo_box.setFixedWidth(70)
        ban_frame_layout.addWidget(self.temp_ban_duration_combo_box)
        self.ban_button_cm = QPushButton("활동 제한", self)
        self.ban_button_cm.clicked.connect(lambda: self.manager("활동 제한", "", ""))
        ban_frame_layout.addWidget(self.ban_button_cm)
        ban_button_layout.addWidget(ban_frame)
        layout.addLayout(ban_button_layout)

        self.result_box_chat_log = QTextEdit(self)
        self.result_box_chat_log.setReadOnly(True)
        self.result_box_chat_log.setFont(QFont('Pretendard JP', GLOBALFONTSIZE-1))
        layout.addWidget(self.result_box_chat_log)

        self.chat_count_label_chat_log = QLabel(self)
        self.chat_count_label_chat_log.setText("채팅 수:")
        layout.addWidget(self.chat_count_label_chat_log)

        ban_num_layout = QHBoxLayout()
        self.temp_ban_label_chat_log = QLabel(self)
        self.temp_ban_label_chat_log.setText("임시 제한 수:")
        self.temp_ban_label_chat_log.hide()
        ban_num_layout.addWidget(self.temp_ban_label_chat_log)
        self.ban_label_chat_log = QLabel(self)
        self.ban_label_chat_log.setText("활동 제한 수:")
        ban_num_layout.addWidget(self.ban_label_chat_log)
        layout.addLayout(ban_num_layout)

        fol_sub_layout = QHBoxLayout()
        self.follow_date_label_chat_log = QLabel(self)
        self.follow_date_label_chat_log.setText("팔로우 날짜:")
        fol_sub_layout.addWidget(self.follow_date_label_chat_log)
        self.subscribe_label_chat_log = QLabel(self)
        self.subscribe_label_chat_log.setText("구독:")
        fol_sub_layout.addWidget(self.subscribe_label_chat_log)
        layout.addLayout(fol_sub_layout)

        self.first_chat_date_label_chat_log = QLabel(self)
        self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜:")
        layout.addWidget(self.first_chat_date_label_chat_log)

        self.time_elapsed_label_chat_log = QLabel(self)
        self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간:")
        layout.addWidget(self.time_elapsed_label_chat_log)

        self.setLayout(layout)
        
        self.moa_volume_tts.setValue(self.main_window.moa_volume_tts.value())
        self.search_chat_all.setChecked(self.main_window.search_chat_all.isChecked())
        self.search_chat_partial.setChecked(self.main_window.search_chat_partial.isChecked())
        self.ignore_space_check.setChecked(self.main_window.ignore_space_check.isChecked())
        self.moa_chat_read_tts.setChecked(self.main_window.moa_chat_read_tts.isChecked())

        ### 임시제한, 활동제한, 일부 정보 숨김 [공식API 지원 시 업데이트 예정]
        self.temp_restrict_duration_combo_box.hide()
        self.temp_ban_button_cm.hide()
        self.temp_ban_duration_combo_box.hide()
        self.ban_button_cm.hide()
        self.ban_label_chat_log.hide()
        self.follow_date_label_chat_log.hide()
        self.subscribe_label_chat_log.hide()



    def update_ui_for_mode(self, text):
        if text == "채팅 내용":
            self.input_box_chat_log.setPlaceholderText("검색할 키워드를 입력하세요.")
        else:
            self.input_box_chat_log.setPlaceholderText("닉네임 또는 아이디를 입력하세요.")


    def get_id_nick(self, chat):
        id = ""
        nick = ""
        if ")> " in chat:
            id_start = chat.index(" (") + 2
            id_end = chat.index(")> ")
            id = chat[id_start:id_end]
            nick_start = chat.index("] <") + 3
            nick_end = chat.index(" (")
            nick = chat[nick_start:nick_end]
        else:
            id_start = chat.index("] <") + 3
            id_end = chat.index("> ")
            id = chat[id_start:id_end]
            nick = id
        return id, nick

    def toggle_chatMoa(self):
        if self.search_button_chat_moa.text() == "채팅 모아보기":
            self.search_button_chat_moa.setText("채팅 모아보기 정지")
            self.input_box_chat_log.setDisabled(True)
            self.input_num_box_chat_log.setDisabled(True)
            self.ignore_space_check.setDisabled(True)
            self.search_button_chat_log.setDisabled(True)
            if self.moa_chat_read_tts.isChecked():
                self.stop_tts_button1.show()
                self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum())
        else:
            self.search_button_chat_moa.setText("채팅 모아보기")
            self.input_box_chat_log.setEnabled(True)
            self.input_num_box_chat_log.setEnabled(True)
            self.search_chat_all.setEnabled(True)
            self.search_chat_partial.setEnabled(True)
            self.ignore_space_check.setEnabled(True)
            self.search_button_chat_log.setEnabled(True)

    def copy_id(self):
        clipboard.copy(self.main_window.user_id_chzzk_ban)
        self.copy_user_id_button.setText("아이디 복사 완료!")
        QApplication.processEvents()
        QTimer.singleShot(2000, lambda: self.copy_user_id_button.setText("아이디 복사"))
        QApplication.processEvents()

    def moa_chat_read_ttsfunc(self):
        if self.moa_chat_read_tts.isChecked():
            if self.search_button_chat_moa.text() == "채팅 모아보기 정지":
                self.stop_tts_button1.show()
                self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum())
    
    def search_stop(self):
        try:
            self.stop_signal = True
            self.search_button_chat_log.show()
            self.search_stop_button_chat_log.hide()
            self.chat_count_label_chat_log.setText("채팅 수: ")
            self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜:")
            self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간:")
            self.input_box_chat_log.setEnabled(True)
            self.input_num_box_chat_log.setEnabled(True)
            self.search_button_chat_log.setEnabled(True)
            self.search_chat_all.setEnabled(True)
            self.search_chat_partial.setEnabled(True)
            self.chzzk_user_profile_button.setEnabled(True)
            self.copy_user_id_button.setEnabled(True)
            self.studio_restriction_popup_button.setEnabled(True)
            self.temp_restrict_duration_combo_box.setEnabled(True)
            self.temp_ban_duration_combo_box.setEnabled(True)
            self.temp_ban_button_cm.setEnabled(True)
            self.ban_button_cm.setEnabled(True)
            self.search_button_chat_moa.setEnabled(True)
            self.ignore_space_check.setEnabled(True)
        except Exception as e:
            None
    
    def search_id(self, nick_to_search):
        search = nick_to_search # 검색할 닉네임/아이디
        file_list = os.listdir(self.main_window.file_path_box_chat_log.text())
        file_list.sort(reverse=True)
        file_list_log = [f"{os.path.join(self.main_window.file_path_box_chat_log.text(),file)}" for file in file_list if file.endswith(".log") and "custom" not in file and "-" in file]
        first_chat_date = None
        user_id = None
        if file_list_log:
            for file_name in file_list_log:
                QApplication.processEvents()
                if self.stop_signal: return None # Check for cancellation
                with open(file_name, 'r', encoding='utf-8') as f:
                    data = f.read()
                    chat_array = data.split("\n")
                    for chat in chat_array[::-1]:
                        QApplication.processEvents()
                        if self.stop_signal: return None # Check for cancellation
                        try:
                            if "<" not in chat: continue
                            id = ""
                            nick = ""
                            id, nick = self.get_id_nick(chat)
                            if nick == search or id == search:
                                user_id = id
                                break    
                        except Exception as e:
                            continue
                    if user_id == None:
                        continue
                    else: break
            return user_id
        else:
            return
    
    def search_log(self, moa):
        try:
            self.stop_signal = False
            self.result_chat_done = False
            self.input_box_chat_log.setDisabled(True)
            self.input_num_box_chat_log.setDisabled(True)
            self.ignore_space_check.setDisabled(True)
            if self.search_button_chat_moa.text() == "채팅 모아보기 정지": # 모아보기 실행 중
                self.search_stop_button_chat_log.hide()
                if moa == False: # 채팅 검색 실행 함. -> 모아보기를 정지함.
                    self.search_button_chat_log.hide()
                    self.search_button_chat_moa.setChecked(False)
                    self.search_button_chat_moa.setText("채팅 모아보기")
                    self.input_box_chat_log.setEnabled(True)
                    self.input_num_box_chat_log.setEnabled(True)
                    self.ignore_space_check.setEnabled(True)
                    self.search_button_chat_log.setEnabled(True)
                    self.search_chat_all.setEnabled(True)
                    self.search_chat_partial.setEnabled(True)
                else: ## 채팅 모아보기 실행 중 -> 모아보기 시작함.
                    self.search_button_chat_log.show()
            else: # 채팅 모아보기 실행중이지 않음
                self.search_button_chat_log.hide()
                self.search_chat_all.setDisabled(True)
                self.search_chat_partial.setDisabled(True)
                self.search_stop_button_chat_log.show()
            
            search = self.input_box_chat_log.text() # 검색할 닉네임/아이디
            chatnum = int(self.input_num_box_chat_log.text()) # 검색할 채팅 수
            search_type = self.search_type_combo.currentText()
            
            cutoff_time = datetime.now() - timedelta(hours=72)
            if search_type == "채팅 내용":
                self.loading_msg = "최근 72시간 채팅 내용 검색 중..."
            if datetime.now().minute >= 40:
                jeong_lee_time = str(int((datetime.now() + timedelta(hours=1)).strftime("%I")))
            else:
                jeong_lee_time = str(int(datetime.now().strftime("%I")))
            
            if moa == False:
                if search_type == "채팅 내용":
                    self.result_box_chat_log.setText(f"{self.loading_msg} \n로그 파일 불러오는 중....")
                    self.chat_count_label_chat_log.setText("")
                    self.first_chat_date_label_chat_log.setText("")
                    self.time_elapsed_label_chat_log.setText("")
                    self.temp_ban_label_chat_log.setText("")
                    self.ban_label_chat_log.setText("")
                    self.follow_date_label_chat_log.setText("")
                    self.subscribe_label_chat_log.setText("")
                else:
                    self.loading_msg = f"로딩 좀 하고 ({jeong_lee_time}시쯤)"
                    if not self.main_window.kanetv8.isChecked(): self.loading_msg = "로딩 중...."
                    self.result_box_chat_log.setText(f"{self.loading_msg} \n로그 파일 불러오는 중....")
                    self.chat_count_label_chat_log.setText("채팅 수: (확인 중 입니다....)")
                    self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜: (확인 중 입니다....)")
                    self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간: (확인 중 입니다....)")
                    self.temp_ban_label_chat_log.setText("임시 제한 수: (확인 중 입니다....)")
                    self.ban_label_chat_log.setText("활동 제한 수: (확인 중 입니다....)")
                    self.follow_date_label_chat_log.setText("팔로우 날짜: (확인 중 입니다....)")
                    self.subscribe_label_chat_log.setText("구독: (확인 중 입니다....)")
            QApplication.processEvents()  # 이벤트 루프 처리
            
            if not search:
                if search_type == "채팅 내용":
                    self.result_box_chat_log.setText("검색할 키워드를 입력해주세요.")
                else:
                    self.result_box_chat_log.setText("닉네임 또는 아이디를 입력해주세요.")
                self.search_button_chat_log.show()
                self.search_stop_button_chat_log.hide()
                self.chat_count_label_chat_log.setText("채팅 수: ")
                self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜: ")
                self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간: ")
                self.temp_ban_label_chat_log.setText("임시 제한 수: ")
                self.ban_label_chat_log.setText("활동 제한 수: ")
                self.follow_date_label_chat_log.setText("팔로우 날짜: ")
                self.subscribe_label_chat_log.setText("구독: ")
                self.input_box_chat_log.setEnabled(True)
                self.input_num_box_chat_log.setEnabled(True)
                self.search_button_chat_log.setEnabled(True)
                self.search_chat_all.setEnabled(True)
                self.search_chat_partial.setEnabled(True)
                
                
                self.temp_restrict_duration_combo_box.setDisabled(True)
                self.temp_ban_duration_combo_box.setDisabled(True)
                self.temp_ban_button_cm.setDisabled(True)
                self.temp_ban_duration_combo_box.setDisabled(True)
                self.ban_button_cm.setDisabled(True)
                self.ignore_space_check.setEnabled(True)
                return

            result = []
            chat_count = 0
            is_new_moa_chat = True # 모아보기 중에 채팅이 새로 들어오면 True로 바뀜.
            is_hit_limit_search_chat_partial = False # 최근 채팅 검색 시 검색할 채팅 수 만큼 채팅이 검색되었을 경우 True로 바뀜.
            original_nick = ""
            file_list = os.listdir(self.main_window.file_path_box_chat_log.text())
            file_list.sort(reverse=True)
            file_list_log = [f"{os.path.join(self.main_window.file_path_box_chat_log.text(),file)}" for file in file_list if file.endswith(".log") and "custom" not in file and "-" in file]
            first_chat_date = None
            user_id = None
            if self.search_button_chat_moa.text() != "채팅 모아보기 정지": ## 채팅 모아보기 하는 중이 아님
                
                
                self.temp_ban_button_cm.setDisabled(True)
                self.temp_ban_duration_combo_box.setDisabled(True)
                self.temp_restrict_duration_combo_box.setDisabled(True)
                self.temp_ban_duration_combo_box.setDisabled(True)
                self.ban_button_cm.setDisabled(True)
            else: ## 채팅 모아보기 중
                self.ignore_space_check.setDisabled(True)
            QApplication.processEvents()
            if moa == False:
                self.search_button_chat_moa.setDisabled(True)
                self.result_box_chat_log.setText(f"{self.loading_msg} \n아이디 검색 중....\n✅'검색 중지' 버튼 클릭 시 검색을 중단합니다.")
            QApplication.processEvents()

            if self.stop_signal == True:
                self.result_box_chat_log.setText("")
                return

            if self.ignore_space_check.isChecked():
                search = search.replace(" ","").lower() # 닉네임 공백/대소문자 무시

            if file_list_log:
                for file_name in file_list_log:
                    QApplication.processEvents()
                    if self.stop_signal == True:
                        self.result_box_chat_log.setText("")
                        return
                    with open(file_name, 'r', encoding='utf-8') as f:
                        data = f.read()
                        chat_array = data.split("\n")
                        for chat in chat_array[::-1]:
                            QApplication.processEvents()
                            try:
                                if self.stop_signal == True:
                                    self.result_box_chat_log.setText("")
                                    return
                                
                                if search_type == "채팅 내용":
                                    try:
                                        # Parse Timestamp & Content
                                        # Format: [2023-10-27 12:34:56] <Nick (ID)> Content
                                        parts = chat.split("] <")
                                        if len(parts) < 2: continue
                                        time_str = parts[0].strip("[")
                                        chat_date = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                                        right_part = parts[1] # Nick (ID)> Content
                                        meta_end_index = right_part.find("> ")
                                        if meta_end_index == -1: continue
                                        meta_part = right_part[:meta_end_index] # Nick (ID)
                                        content_part = right_part[meta_end_index+2:] # Content
                                        content_part = right_part[meta_end_index+2:] # Content
                                        # Strict Content Match (Exclude ID/Nick) & Ignore Space/Case
                                        content_to_check = content_part
                                        search_key = search
                                        if self.ignore_space_check.isChecked():
                                            content_to_check = content_part.replace(" ", "").lower()
                                            search_key = search.replace(" ", "").lower()
                                        if search_key in content_to_check:
                                            display_nick = meta_part
                                            if "(" in meta_part and meta_part.endswith(")"):
                                                display_nick = meta_part.rsplit(" (", 1)[0]
                                            display_line = f"[{time_str}] <{display_nick}> {content_part}"
                                            result.append(display_line)
                                            chat_count += 1
                                            if moa == True:
                                                if len(result) >= 100:
                                                    break
                                            elif chat_count >= chatnum:
                                                result.reverse()
                                                should_update = True
                                                if moa:
                                                    current_lines = self.result_box_chat_log.toPlainText().strip().split('\n')
                                                    if result and current_lines and result[-1].strip() == current_lines[-1].strip():
                                                        should_update = False
                                                if should_update:
                                                     self.result_box_chat_log.setText("\n".join(result))
                                                     self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum())
                                                self.result_chat_done = True
                                                self.search_button_chat_log.show()
                                                self.search_stop_button_chat_log.hide()
                                                if moa == False:
                                                    self.input_box_chat_log.setEnabled(True)
                                                    self.input_num_box_chat_log.setEnabled(True)
                                                    self.search_button_chat_log.setEnabled(True)
                                                    self.search_chat_all.setEnabled(True)
                                                    self.search_chat_partial.setEnabled(True)
                                                    self.ignore_space_check.setEnabled(True)
                                                    self.search_button_chat_moa.setEnabled(True)
                                                return 
                                        if chat_date < cutoff_time:
                                            result.reverse()
                                            if not result:
                                                self.result_box_chat_log.setText("검색 결과가 없습니다.")
                                            else:
                                                should_update = True
                                                if moa:
                                                    current_lines = self.result_box_chat_log.toPlainText().strip().split('\n')
                                                    if result and current_lines and result[-1].strip() == current_lines[-1].strip():
                                                        should_update = False
                                                if should_update:
                                                     self.result_box_chat_log.setText("\n".join(result))
                                                     self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum())
                                            self.result_chat_done = True
                                            self.search_button_chat_log.show()
                                            self.search_stop_button_chat_log.hide()
                                            if moa == False:
                                                self.input_box_chat_log.setEnabled(True)
                                                self.input_num_box_chat_log.setEnabled(True)
                                                self.search_button_chat_log.setEnabled(True)
                                                self.search_chat_all.setEnabled(True)
                                                self.search_chat_partial.setEnabled(True)
                                                self.ignore_space_check.setEnabled(True)
                                                self.search_button_chat_moa.setEnabled(True)
                                            return
                                    except Exception as e:
                                        continue
                                    continue # Skip ID logic

                                if "<" not in chat: continue
                                id = ""
                                nick = ""
                                id, nick = self.get_id_nick(chat)
                                original_nick = str(nick)
                                if self.ignore_space_check.isChecked(): # 닉네임 공백/대소문자 무시
                                    nick = nick.replace(" ","").lower()
                                if nick == search or id == search:
                                    user_id = id
                                    if moa == True:
                                        if chat.replace(f" ({user_id})", "") == self.result_box_chat_log.toPlainText().split("\n")[-1]:
                                            is_new_moa_chat = False
                                    break    
                            except Exception as e:
                                continue
                        if search_type == "채팅 내용": continue # File loop continue
                        if user_id == None:
                            continue
                        else: break
                if search_type == "채팅 내용":
                     result.reverse()
                     if not result:
                         self.result_box_chat_log.setText("검색 결과가 없습니다.")
                     else:
                         should_update = True
                         if moa:
                             current_lines = self.result_box_chat_log.toPlainText().strip().split('\n')
                             if result and current_lines and result[-1].strip() == current_lines[-1].strip():
                                 should_update = False
                         
                         if should_update:
                             self.result_box_chat_log.setText("\n".join(result))
                             QTimer.singleShot(100, lambda: self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum()))
                     self.search_button_chat_log.show()
                     self.search_stop_button_chat_log.hide()
                     if moa == False:
                         self.input_box_chat_log.setEnabled(True)
                         self.input_num_box_chat_log.setEnabled(True)
                         self.search_button_chat_log.setEnabled(True)
                         self.search_chat_all.setEnabled(True)
                         self.search_chat_partial.setEnabled(True)
                         self.ignore_space_check.setEnabled(True)
                         self.search_button_chat_moa.setEnabled(True)
                     return
                QApplication.processEvents()
                self.main_window.user_id_chzzk_ban = user_id
                self.main_window.user_nick_chzzk_ban = str(original_nick)
                if moa == False and search_type != "채팅 내용": ## 채팅 검색 (ID/Nick)
                    self.chat_count_label_chat_log.setText("채팅 수: (확인 중 입니다....)")
                    self.chat_count_label_chat_log.setText("채팅 수: (확인 중 입니다....)")
                    if user_id != None: # 유저 아이디를 검색하였음.
                        self.temp_ban_label_chat_log.setText("임시 제한 수: (확인 중 입니다....)")
                        self.ban_label_chat_log.setText("활동 제한 수: (확인 중 입니다....)")
                        self.follow_date_label_chat_log.setText("팔로우 날짜: (확인 중 입니다....)")
                        self.subscribe_label_chat_log.setText("구독: (확인 중 입니다....)")
                    else: # 유저 아이디를 검색하지 못함.
                        self.temp_ban_label_chat_log.setText("임시 제한 수: (확인할 수 없습니다)")
                        self.ban_label_chat_log.setText("활동 제한 수: (확인할 수 없습니다)")
                        self.follow_date_label_chat_log.setText("팔로우 날짜: (확인할 수 없습니다)")
                        self.subscribe_label_chat_log.setText("구독: (확인할 수 없습니다)")
                if user_id == None and search_type != "채팅 내용":
                    self.result_box_chat_log.setText("존재하지 않는 유저입니다. 닉네임 또는 아이디를 정확하게 입력하였는지, 로그 파일이 올바른지 확인해주세요.")
                    self.chat_count_label_chat_log.setText("채팅 수: ")
                    self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜: ")
                    self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간: ")
                    self.temp_ban_label_chat_log.setText("임시 제한 수: ")
                    self.ban_label_chat_log.setText("활동 제한 수: ")
                    self.follow_date_label_chat_log.setText("팔로우 날짜: ")
                    self.subscribe_label_chat_log.setText("구독: ")
                    self.input_box_chat_log.setEnabled(True)
                    self.input_num_box_chat_log.setEnabled(True)
                    self.search_button_chat_log.setEnabled(True)
                    self.search_chat_all.setEnabled(True)
                    self.search_chat_partial.setEnabled(True)
                    self.ignore_space_check.setEnabled(True)
                    self.search_button_chat_moa.setEnabled(True)
                    self.search_button_chat_log.show()
                    self.search_stop_button_chat_log.hide()
                    return
            else:
                self.result_box_chat_log.setText("로그 파일이 없습니다.")
                self.chat_count_label_chat_log.setText("채팅 수: ")
                self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜: ")
                self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간: ")
                self.temp_ban_label_chat_log.setText("임시 제한 수: ")
                self.ban_label_chat_log.setText("활동 제한 수: ")
                self.follow_date_label_chat_log.setText("팔로우 날짜: ")
                self.subscribe_label_chat_log.setText("구독: ")
                self.search_button_chat_log.show()
                self.search_stop_button_chat_log.hide()


            if moa == False:
                if search_type == "채팅 내용":
                     self.result_box_chat_log.setText(f"{self.loading_msg}\n키워드 '{search}' 검색 완료\n검색된 채팅 출력 시작...")
                     QTimer.singleShot(100, lambda: self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum()))
                else:
                    self.result_box_chat_log.setText(f"{self.loading_msg}\n아이디 검색 완료\n{original_nick} ({user_id})의 채팅 내역 검색 시작\n✅'검색 중지' 버튼 클릭 시 검색을 중단합니다.")
            QApplication.processEvents()

            if file_list_log:
                file_list_index = 0
                for file_name in file_list_log:
                    QApplication.processEvents()
                    if self.stop_signal == True:
                        if self.result_chat_done == False:
                            result.reverse()
                            result.append(f"이미 검색된 채팅 {len(result)}개만 표시하였습니다.")
                            self.result_box_chat_log.setText("\n".join(result))
                            self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum())
                        return
                    
                    if search_type == "채팅 내용": continue # Content search already handled above (inside file loop)

                    with open(file_name, 'r', encoding='utf-8') as f:
                        data = f.read()
                        chat_array = data.split("\n")
                        QApplication.processEvents()
                        for chat in chat_array[::-1]:
                            QApplication.processEvents()
                            try:
                                if self.stop_signal == True:
                                    if self.result_chat_done == False:
                                        result.reverse()
                                        result.append(f"이미 검색된 채팅 {len(result)}개만 표시하였습니다.")
                                        self.result_box_chat_log.setText("\n".join(result))
                                        self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum())
                                    return
                                if "<" not in chat: continue
                                id = ""
                                nick = ""
                                id, nick = self.get_id_nick(chat)
                                if id == user_id:
                                    if moa == True:
                                        if len(result) >= 100:
                                            break
                                        result.append(chat.replace(f" ({user_id})",""))
                                        chat_date_str = chat.split(" ")[0].strip("[]") + " " + chat.split(" ")[1].strip("[]")
                                        chat_date = datetime.strptime(chat_date_str, '%Y-%m-%d %H:%M:%S')
                                        if first_chat_date is None or chat_date < first_chat_date:
                                            first_chat_date = chat_date
                                        QApplication.processEvents()
                                    elif(self.search_chat_partial.isChecked()):
                                        if chat_count < chatnum:
                                            result.append((chat.replace(f" ({user_id})","")))
                                            self.result_box_chat_log.setText(f"{self.loading_msg}\n아이디 검색 완료\n{original_nick} ({user_id})의 채팅 내역 검색 시작\n검색된 채팅 수: {len(result)}/{chatnum}\n✅'검색 중지' 버튼 클릭 시 검색을 중단하고 현재까지 검색된 채팅로그만 표시됩니다.")
                                            QApplication.processEvents()
                                        if chat_count == chatnum:
                                            result.reverse()
                                            self.result_box_chat_log.setText("\n".join(result))
                                            self.result_chat_done = True
                                            is_hit_limit_search_chat_partial = True
                                            print("752")
                                            self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum())
                                            self.chzzk_user_profile_button.setEnabled(True)
                                            self.copy_user_id_button.setEnabled(True)
                                            self.studio_restriction_popup_button.setEnabled(True)
                                            self.temp_restrict_duration_combo_box.setEnabled(True)
                                            self.temp_ban_duration_combo_box.setEnabled(True)
                                            self.temp_ban_button_cm.setEnabled(True)
                                            self.ban_button_cm.setEnabled(True)
                                            self.search_button_chat_log.setEnabled(True)
                                            self.search_button_chat_moa.setEnabled(True)
                                            self.first_chat_date_label_chat_log.setText(f"첫 채팅을 친 날짜: (확인 중 입니다....)")
                                            self.time_elapsed_label_chat_log.setText(f"첫 채팅을 친 후 경과한 시간: (확인 중 입니다....)")
                                            QApplication.processEvents()
                                        chat_count+=1
                                        chat_date_str = chat.split(" ")[0].strip("[]") + " " + chat.split(" ")[1].strip("[]")
                                        chat_date = datetime.strptime(chat_date_str, '%Y-%m-%d %H:%M:%S')
                                        if first_chat_date is None or chat_date < first_chat_date:
                                            first_chat_date = chat_date
                                    elif(self.search_chat_all.isChecked()):
                                        result.append((chat.replace(f" ({user_id})","")))
                                        chat_count+=1
                                        chat_date_str = chat.split(" ")[0].strip("[]") + " " + chat.split(" ")[1].strip("[]")
                                        chat_date = datetime.strptime(chat_date_str, '%Y-%m-%d %H:%M:%S')
                                        if first_chat_date is None or chat_date < first_chat_date:
                                            first_chat_date = chat_date
                                        if len(result) < 1000 and len(result) % 10 == 0:
                                            self.result_box_chat_log.setText(f"{self.loading_msg}\n아이디 검색 완료\n{original_nick} ({user_id})의 채팅 내역 검색 시작\n검색된 채팅 수: {len(result)}\n✅'검색 중지' 버튼 클릭 시 검색을 중단하고 현재까지 검색된 채팅로그만 표시됩니다.")
                                            QApplication.processEvents()
                                        if len(result) % 1000 == 0:
                                            if len(result) > 10000:
                                                self.result_box_chat_log.setText(f"{self.loading_msg}\n아이디 검색 완료\n{original_nick} ({user_id})의 채팅 내역 검색 시작\n검색된 채팅 수: {len(result)}\n❗{self.CHAT_LOG_TOO_MUCH_TEXT}\n검색 완료 후 채팅 내역 출력 시 프로그램이 잠시 멈출 수 있으니 기다려 주세요.\n✅'검색 중지' 버튼 클릭 시 검색을 중단하고 현재까지 검색된 채팅로그만 표시됩니다.")
                                                QApplication.processEvents()
                                            else:
                                                self.result_box_chat_log.setText(f"{self.loading_msg}\n아이디 검색 완료\n{original_nick} ({user_id})의 채팅 내역 검색 시작\n검색된 채팅 수: {len(result)}\n✅'검색 중지' 버튼 클릭 시 검색을 중단하고 현재까지 검색된 채팅로그만 표시됩니다.")
                                                QApplication.processEvents()
                            except Exception as e:
                                continue
                    file_list_index+=1
                    if moa == True:
                        if len(result) >= 100 or file_list_index >= 3 or is_new_moa_chat == False : break
                        else: continue
                    elif self.search_chat_all.isChecked() or self.search_chat_partial.isChecked(): continue
                    else: break
            if self.main_window.user_id_chzzk_ban != user_id:
                self.chat_count_label_chat_log.setText("채팅 수:")
                self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜:")
                self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간:")
                self.temp_ban_label_chat_log.setText("임시 제한 수:")
                self.ban_label_chat_log.setText("활동 제한 수:")
                self.follow_date_label_chat_log.setText("팔로우 날짜:")
                self.subscribe_label_chat_log.setText("구독:")
            self.main_window.user_id_chzzk_ban = user_id
            self.main_window.user_nick_chzzk_ban = str(original_nick)
            self.chzzk_user_profile_button.setEnabled(True)
            self.copy_user_id_button.setEnabled(True)
            self.studio_restriction_popup_button.setEnabled(True)
            self.temp_restrict_duration_combo_box.setEnabled(True)
            self.temp_ban_duration_combo_box.setEnabled(True)
            self.temp_ban_button_cm.setEnabled(True)
            self.ban_button_cm.setEnabled(True)
            self.search_button_chat_moa.setEnabled(True)
            if len(result) != 0:
                if moa == False:
                    if is_hit_limit_search_chat_partial == False:
                        result.reverse()
                        self.result_box_chat_log.setText("\n".join(result))
                        self.result_chat_done = True
                    self.input_box_chat_log.setEnabled(True)
                    self.input_num_box_chat_log.setEnabled(True)
                    if self.search_button_chat_moa.text() == ("채팅 모아보기"):
                        self.search_button_chat_log.setEnabled(True)
                    self.search_chat_all.setEnabled(True)
                    self.search_chat_partial.setEnabled(True)
                    self.ignore_space_check.setEnabled(True)
                if moa == True:
                    if is_new_moa_chat == True: # 모아보기 중 새로운 채팅
                        if is_hit_limit_search_chat_partial == False:
                            result.reverse()
                            if self.result_box_chat_log.toPlainText().split("\n")[-1] != result[-1]:
                                self.main_window.user_id_moa_before = self.main_window.user_id_chzzk_ban
                                self.search_button_chat_moa.setEnabled(True)
                                self.result_box_chat_log.setText("\n".join(result))
                                self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum())
                                if self.moa_chat_read_tts.isChecked():
                                    try:
                                        chat = result[-1]
                                        id, nick = self.get_id_nick(chat)
                                        chat = chat.split(f"<{nick}> ")[1]
                                        if "🟥⭐" not in chat:
                                            if self.main_window.audio_thread and self.main_window.audio_thread.is_alive():
                                                self.main_window.stop_audio_event.set()
                                                self.main_window.audio_thread.join()
                                            self.main_window.stop_audio_event.clear()
                                            self.main_window.audio_thread = threading.Thread(target=lambda: asyncio.run(self.main_window.play_audio(chat, 1,)))
                                            self.main_window.audio_thread.start()
                                    except Exception as e:
                                        None
                            if self.chat_count_label_chat_log.text() != "채팅 수: (확인 중 입니다....)" and self.chat_count_label_chat_log.text() != "채팅 수:" :
                                None
                            else:
                                self.chat_count_label_chat_log.setText("채팅 수:")
                                self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜:")
                                self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간:")
                                self.temp_ban_label_chat_log.setText("임시 제한 수:")
                                self.ban_label_chat_log.setText("활동 제한 수:")
                                self.follow_date_label_chat_log.setText("팔로우 날짜:")
                                self.subscribe_label_chat_log.setText("구독:")
                else:
                    #if self.chat_count_label_chat_log.text().startswith("채팅 수: 9999+") and chat_count > 9999:
                    self.chat_count_label_chat_log.setText(f"채팅 수: {chat_count}")
                    self.first_chat_date_label_chat_log.setText(f"첫 채팅을 친 날짜: {first_chat_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    time_elapsed = datetime.now() - first_chat_date
                    days_elapsed = time_elapsed.days
                    hours_elapsed, remainder = divmod(time_elapsed.seconds, 3600)
                    minutes_elapsed, seconds_elapsed = divmod(remainder, 60)
                    self.time_elapsed_label_chat_log.setText(f"첫 채팅을 친 후 경과한 시간: {days_elapsed}일 {hours_elapsed}시간 {minutes_elapsed}분 {seconds_elapsed}초")
                    QApplication.processEvents()  # 이벤트 루프 처리
                    if self.search_chat_partial.isChecked():
                        print("870")
                        if is_hit_limit_search_chat_partial == False: self.result_box_chat_log.verticalScrollBar().setValue(self.result_box_chat_log.verticalScrollBar().maximum())
            elif is_new_moa_chat == False: return
            else:
                self.result_box_chat_log.setText("검색 결과가 없습니다.\n닉네임 또는 아이디를 정확하게 입력하였는지, 로그 파일이 올바른지 확인해주세요.")
                self.chat_count_label_chat_log.setText("채팅 수: ")
                self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜: ")
                self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간: ")
                self.temp_ban_label_chat_log.setText("임시 제한 수: ")
                self.ban_label_chat_log.setText("활동 제한 수: ")
                self.follow_date_label_chat_log.setText("팔로우 날짜: ")
                self.subscribe_label_chat_log.setText("구독: ")
                self.search_button_chat_moa.setEnabled(True)
                self.temp_restrict_duration_combo_box.setDisabled(True)
                self.temp_ban_duration_combo_box.setDisabled(True)
                self.temp_ban_button_cm.setDisabled(True)
                self.temp_ban_duration_combo_box.setDisabled(True)
                self.ban_button_cm.setDisabled(True)
                self.ignore_space_check.setEnabled(True)
                self.search_button_chat_log.show()
                self.search_stop_button_chat_log.hide()
            self.search_button_chat_log.show()
            self.search_stop_button_chat_log.hide()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            err = traceback.format_exc()
            errortime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.result_box_chat_log.setText(f"[{errortime}]\n❗오류 발생!{exc_type} {exc_tb.tb_lineno} {err} {fname}")
            self.chat_count_label_chat_log.setText("채팅 수: ")
            self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜: ")
            self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간: ")
            self.temp_ban_label_chat_log.setText("임시 제한 수: ")
            self.ban_label_chat_log.setText("활동 제한 수: ")
            self.follow_date_label_chat_log.setText("팔로우 날짜: ")
            self.subscribe_label_chat_log.setText("구독: ")
            self.input_box_chat_log.setEnabled(True)
            self.input_num_box_chat_log.setEnabled(True)
            self.search_button_chat_log.setEnabled(True)
            self.search_chat_all.setEnabled(True)
            self.search_chat_partial.setEnabled(True)
            self.temp_restrict_duration_combo_box.setDisabled(True)
            self.temp_ban_duration_combo_box.setDisabled(True)
            self.temp_ban_button_cm.setDisabled(True)
            self.temp_ban_duration_combo_box.setDisabled(True)
            self.ban_button_cm.setDisabled(True)
            self.ignore_space_check.setEnabled(True)
            self.search_button_chat_log.show()
            self.search_stop_button_chat_log.hide()

    
    @pyqtSlot(str)
    def search_log_check_moa(self, searchnick):
        try:
            if self.search_stop_button_chat_log.isVisible():
                self.search_stop_button_chat_log.click()
            self.main_window.show()
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.main_window.tabs.setCurrentWidget(self)
            if self.search_button_chat_moa.text() == "채팅 모아보기 정지":
                self.search_button_chat_moa.click()
                QTimer.singleShot(100, lambda: self.input_box_chat_log.setText(searchnick))
                self.chat_count_label_chat_log.setText("채팅 수:")
                self.temp_ban_label_chat_log.setText("임시 제한 수:")
                self.ban_label_chat_log.setText("활동 제한 수:")
                self.follow_date_label_chat_log.setText("팔로우 날짜:")
                self.subscribe_label_chat_log.setText("구독:")
                self.first_chat_date_label_chat_log.setText("첫 채팅을 친 날짜:")
                self.time_elapsed_label_chat_log.setText("첫 채팅을 친 후 경과한 시간:")
                QTimer.singleShot(200, lambda: self.search_button_chat_moa.click())
            else:
                QTimer.singleShot(100, lambda: self.input_box_chat_log.setText(searchnick))
                QTimer.singleShot(200, lambda: self.search_button_chat_moa.click())
        except Exception as e:
            print(e)
            None
    
    @pyqtSlot(str)
    def search_log_check(self, search_nick):
        try:
            self.main_window.show()
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.main_window.tabs.setCurrentWidget(self)
            if self.search_button_chat_moa.text() == "채팅 모아보기 정지":
                self.search_button_chat_moa.click()
            if self.search_stop_button_chat_log.isVisible():
                self.search_stop_button_chat_log.click()
            QTimer.singleShot(100, lambda: self.input_box_chat_log.setText(search_nick))
            QTimer.singleShot(200, lambda: self.search_button_chat_log.click())
        except Exception as e:
            None
     
    def chat_moa(self):
        try:
            if str(self.main_window.picked_user_nick) == "" and self.search_button_chat_moa.text() == "채팅 모아보기":
                return # 추첨 중이 아니고 채팅 모아보기 중이 아님 -> 스킵
            self.result_vote_temp = []
            self.result_vote_temp_donation = []
            result_pick_chat = []
            picked_user_nick = ""
            file_list = os.listdir(self.main_window.file_path_box_chat_log.text())
            file_list.sort(reverse=True)
            file_list_log = [f"{os.path.join(self.main_window.file_path_box_chat_log.text(),file)}" for file in file_list if file.endswith(".log") and "custom" not in file and "-" in file]
            temp_pick_nick = str(self.main_window.picked_user_nick)
            if self.search_button_chat_moa.text() == "채팅 모아보기 정지": self.search_log(True)
            QApplication.processEvents()  # 이벤트 루프 처리
            
            if file_list_log:
                for file_name in file_list_log[:3]:
                    with open(file_name, 'r', encoding='utf-8') as f:
                        data = f.read()
                        chat_array = data.split("\n")
                        index = len(chat_array)
                        for chat in chat_array[::-1]:
                            if temp_pick_nick != "" and len(result_pick_chat) < 10:
                                try:
                                    id = ""
                                    nick = ""
                                    id, nick = self.get_id_nick(chat)
                                    msg = chat.split(f"({id})> ")[1]
                                    if nick == temp_pick_nick:
                                        try:
                                            picked_user_nick = nick
                                            result_pick_chat.append(chat.replace(f" ({id})",""))
                                            QApplication.processEvents()
                                        except Exception as e:
                                            None
                                except Exception as e:
                                    None
                
                result_pick_chat.reverse()

                # 당첨자 채팅 출력
                if temp_pick_nick != "" and temp_pick_nick == self.main_window.picked_user_nick:
                    if len(result_pick_chat) >= 1:
                        try:
                            if self.main_window.result_box_chat_pick.toPlainText().split("\n")[-1] != result_pick_chat[-1].replace(f"<{picked_user_nick}>",""):
                                result_pick_array = []
                                for ra in result_pick_chat:
                                    result_pick_array.append(ra.replace(f"<{picked_user_nick}>",""))
                                self.main_window.result_box_chat_pick.setText("\n".join(result_pick_array))
                                self.main_window.result_box_chat_pick.verticalScrollBar().setValue(self.main_window.result_box_chat_pick.verticalScrollBar().maximum())
                                if self.main_window.pick_chat_read_tts.isChecked():
                                    try:
                                        chat = result_pick_chat[-1].split(f"<{picked_user_nick}> ")[1]
                                        if "🟥⭐" not in chat:
                                            if self.main_window.audio_thread and self.main_window.audio_thread.is_alive():
                                                self.main_window.stop_audio_event.set()
                                                self.main_window.audio_thread.join()
                                            self.main_window.stop_audio_event.clear()
                                            print(self.main_window.is_pick_clicked)
                                            if self.main_window.is_pick_clicked:
                                                self.main_window.is_pick_clicked = False
                                                self.main_window.audio_thread = threading.Thread(target=lambda: asyncio.run(self.main_window.play_audio(picked_user_nick + " 당첨!  " + chat, 0,)))
                                            else:
                                                self.main_window.audio_thread = threading.Thread(target=lambda: asyncio.run(self.main_window.play_audio(chat, 0,)))
                                            self.main_window.audio_thread.start()
                                    except Exception as e:
                                        print(e)
                                        None
                                QApplication.processEvents()
                        except Exception as e:
                            print(e)
                            None
                    else:
                        self.main_window.result_box_chat_pick.setText("이 유저의 채팅이 없습니다.")
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            err = traceback.format_exc()
            errortime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{errortime}]\n❗오류 발생!{exc_type} {exc_tb.tb_lineno} {err} {fname}\n")


    # --- 밴 관련 함수 ---
    def manager(self, type, cnt, time):
        if not self.main_window.user_id_chzzk_ban:
            QMessageBox.critical(self, '경고', '채팅부검 탭에서 유저를 먼저 검색해주세요.')
            return

        user_id_to_ban = self.main_window.user_id_chzzk_ban # Use the stored ID from search
        user_nick_to_ban = self.main_window.user_nick_chzzk_ban # Use stored nick for messages

        if type == "임시 제한":
            # 공식 API는 임시 제한 미지원
            QMessageBox.warning(self, '알림', '치지직 공식 API는 임시 제한 기능을 지원하지 않습니다.\n영구 제한 또는 스튜디오를 이용해주세요.')
            # reply = QMessageBox.question(self, '경고', f'{user_nick_to_ban}님을 {time} 임시 제한 하시겠습니까?',
            #                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            # if reply == QMessageBox.StandardButton.Yes:
            #     if self.chatroom_connector_instance:
            #         # self.chatroom_connector_instance.ban_user(user_id_to_ban, "temporary", cnt) # type="temporary" 추가 (connector에서 처리)
            #         self.temp_ban_button_cm.setText("임시 제한!") # UI 피드백
            #         QTimer.singleShot(2000, lambda: self.temp_ban_button_cm.setText("임시 제한"))

        elif type == "활동 제한":
            duration_text = self.temp_ban_duration_combo_box.currentText()
            duration_days = None
            if duration_text != "영구":
                # 공식 API는 영구 제한만 지원
                 QMessageBox.warning(self, '알림', '치지직 공식 API는 영구 활동 제한만 지원합니다.\n기간제 활동 제한은 스튜디오를 이용해주세요.')
                 return
                # duration_days = int(duration_text.split(" ")[0]) # 공식 API는 기간 미지원

            reply = QMessageBox.question(self, '경고', f'{user_nick_to_ban}님을 영구 활동 제한 하시겠습니까?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if hasattr(self.main_window, 'chatroom_connector_instance'):
                    # 공식 API 호출 (영구 제한만 가능)
                    self.main_window.chatroom_connector_instance.ban_user(user_id_to_ban, user_nick_to_ban, "permanent", reason="") # type="permanent"
                    self.ban_button_cm.setText("활동 제한 완료!") # UI 피드백
                    QTimer.singleShot(2000, lambda: self.ban_button_cm.setText("활동 제한"))