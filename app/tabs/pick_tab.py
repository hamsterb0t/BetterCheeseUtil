import sys
import random
import os
import traceback
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFrame, QCheckBox, 
                             QSpinBox, QMessageBox, QTextEdit, QApplication, QSlider, QSizePolicy)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QTimer, QSize
from datetime import datetime

from app.constants import GLOBALFONTSIZE
from app.resources import resource_path
from app.ui_widgets import QToggle

class PickTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        
        self.main_window = main_window

        self.pick_list = []
        self.picked_users_set = set()
        self.pick_option_time_cnt = 0
        self.subscriber_list = []
        self.is_subscriber_list_loaded = False
        
        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        self.toggle_button_pick = QPushButton('모집 시작', self)
        self.toggle_button_pick.clicked.connect(self.pick_start)
        button_layout.addWidget(self.toggle_button_pick)

        self.result_button_chat_pick = QPushButton('추첨 종료', self)
        self.result_button_chat_pick.clicked.connect(self.pick_done_confirm)
        self.result_button_chat_pick.hide()
        button_layout.addWidget(self.result_button_chat_pick)

        self.result_button_pick = QPushButton('추첨하기', self)
        self.result_button_pick.clicked.connect(self.pick_user)
        self.result_button_pick.setDisabled(True)
        button_layout.addWidget(self.result_button_pick)
        self.result_button_pick.hide()

        layout.addLayout(button_layout)

        tts_layout = QHBoxLayout()
        self.pick_chat_read_tts = QToggle(self)
        self.pick_chat_read_tts.setText("TTS 읽어주기")
        self.pick_chat_read_tts.clicked.connect(self.pick_chat_read_ttsfunc)
        tts_layout.addWidget(self.pick_chat_read_tts)

        self.volume_label = QLabel('음량 ')
        tts_layout.addWidget(self.volume_label)

        self.volume_tts = QSlider(Qt.Orientation.Horizontal)
        self.volume_tts.setMinimum(0)
        self.volume_tts.setMaximum(100)
        self.volume_tts.setSingleStep(5)
        self.volume_tts.setFixedWidth(100)
        tts_layout.addWidget(self.volume_tts)

        self.stop_tts_button2 = QPushButton("TTS 넘기기", self)
        self.stop_tts_button2.clicked.connect(self.main_window.stop_tts) # 메인 윈도우 공용 함수
        self.stop_tts_button2.setIcon(QIcon(resource_path(r'.\resources\icon\skip.png')))
        self.stop_tts_button2.setFixedWidth(200)
        self.stop_tts_button2.setIconSize(QSize(20,20))
        tts_layout.addWidget(self.stop_tts_button2)
        tts_layout.addStretch()
        layout.addLayout(tts_layout)

        option_layout1 = QHBoxLayout()

        self.remote_duplicate_check = QToggle(self)
        self.remote_duplicate_check.setText("중복 당첨 제외")
        self.remote_duplicate_check.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        option_layout1.addWidget(self.remote_duplicate_check)

        self.only_subscriber_check = QToggle(self)
        self.only_subscriber_check.setText("구독자 전용")
        self.only_subscriber_check.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        option_layout1.addWidget(self.only_subscriber_check)

        option_layout1.addStretch()

        layout.addLayout(option_layout1)

        option_layout2 = QHBoxLayout()
        
        self.pick_option_check1 = QCheckBox("제한 시간: ")
        self.pick_option_check1.setChecked(False)
        self.pick_option_check1.stateChanged.connect(lambda: self.pick_option_time.setEnabled(self.pick_option_check1.isChecked()))
        option_layout2.addWidget(self.pick_option_check1)
        self.pick_option_time = QSpinBox(self)
        self.pick_option_time.setMinimum(0)
        self.pick_option_time.setMaximum(9999)
        self.pick_option_time.setSingleStep(10)
        self.pick_option_time.setValue(60)
        self.pick_option_time.setSuffix("초")
        self.pick_option_time.setFixedWidth(100)
        self.pick_option_time.setEnabled(False)
        option_layout2.addWidget(self.pick_option_time)

        self.pick_option_check2 = QCheckBox("제한 인원: ")
        self.pick_option_check2.setChecked(False)
        self.pick_option_check2.stateChanged.connect(lambda: self.pick_option_count.setEnabled(self.pick_option_check2.isChecked()))
        option_layout2.addWidget(self.pick_option_check2)
        self.pick_option_count = QSpinBox(self)
        self.pick_option_count.setMinimum(0)
        self.pick_option_count.setMaximum(9999)
        self.pick_option_count.setSingleStep(10)
        self.pick_option_count.setValue(100)
        self.pick_option_count.setSuffix("명")
        self.pick_option_count.setFixedWidth(100)
        self.pick_option_count.setEnabled(False)
        option_layout2.addWidget(self.pick_option_count)

        option_layout2.addStretch()
        layout.addLayout(option_layout2)

        self.result_box_pick = QTextEdit(self)
        self.result_box_pick.setReadOnly(True)
        self.result_box_pick.setMaximumHeight(40)
        self.result_box_pick.setFont(QFont('Pretendard JP', 15))
        self.result_box_pick.setText("'모집 시작' 버튼을 눌러 추첨에 참여할 시청자를 모집하세요.")
        layout.addWidget(self.result_box_pick)

        pick_timer_limit_layout = QHBoxLayout()
        self.pick_timer_box = QLabel(self)
        self.pick_timer_box.setMaximumHeight(30)
        self.pick_timer_box.setFont(QFont('Pretendard JP', 15))
        self.pick_timer_box.hide()
        pick_timer_limit_layout.addWidget(self.pick_timer_box)
        self.pick_limit_box = QLabel(self)
        self.pick_limit_box.setMaximumHeight(55)
        self.pick_limit_box.setFont(QFont('Pretendard JP', 15))
        self.pick_limit_box.hide()
        pick_timer_limit_layout.addWidget(self.pick_limit_box)
        pick_timer_limit_layout.addStretch()
        layout.addLayout(pick_timer_limit_layout)

        self.result_box_chat_pick = QTextEdit(self)
        self.result_box_chat_pick.setReadOnly(True)
        self.result_box_chat_pick.setFont(QFont('Pretendard JP', GLOBALFONTSIZE+2))
        self.result_box_chat_pick.setText("")
        layout.addWidget(self.result_box_chat_pick)
        self.result_box_chat_pick.hide()

        self.frame1_pick = QFrame(self)
        self.frame1_pick.setFrameShape(QFrame.Shape.StyledPanel)
        frame1_layout = QVBoxLayout(self.frame1_pick)
        count_layout = QHBoxLayout()
        self.result_count_text_p = QLabel("추첨 참여 인원: ")
        self.result_count_text_p.setFont(QFont('Pretendard JP', GLOBALFONTSIZE+2))
        count_layout.addWidget(self.result_count_text_p)
        self.result_count_p = QLabel("0명")
        self.result_count_p.setFont(QFont('Pretendard JP', GLOBALFONTSIZE+2))
        count_layout.addWidget(self.result_count_p)
        count_layout.addStretch()
        frame1_layout.addLayout(count_layout)

        self.result_box_list_pick = QTextEdit(self)
        self.result_box_list_pick.setReadOnly(True)
        frame1_layout.addWidget(self.result_box_list_pick)
        layout.addWidget(self.frame1_pick)
        
        self.setLayout(layout)
        
        self.load_settings_from_main()

        if self.main_window.chatroom_connector_instance:
            self.main_window.chatroom_connector_instance.subscribers_fetched.connect(self.on_subscribers_fetched)

    def on_subscribers_fetched(self, data):
        self.subscriber_list = data
        self.is_subscriber_list_loaded = True


    ##### 추첨 탭 관련 함수 #####

    def load_settings_from_main(self):
        """메인 윈도우의 설정 값을 이 탭의 위젯에 적용하고, 위젯 참조를 교체합니다."""
        mw = self.main_window
        
        # 값 로드
        self.pick_chat_read_tts.setChecked(mw.pick_chat_read_tts.isChecked())
        self.volume_tts.setValue(mw.volume_tts.value())
        
        mw.pick_chat_read_tts = self.pick_chat_read_tts
        mw.volume_tts = self.volume_tts
        
        mw.pick_list = self.pick_list
        mw.toggle_button_pick = self.toggle_button_pick
        mw.pick_option_check2 = self.pick_option_check2
        mw.pick_option_count = self.pick_option_count
        
        mw.result_box_chat_pick = self.result_box_chat_pick

        self.remote_duplicate_check.setChecked(mw.remote_duplicate_check.isChecked())
        mw.remote_duplicate_check = self.remote_duplicate_check


    def pick_chat_read_ttsfunc(self):
        if self.pick_chat_read_tts.isChecked():
            if self.main_window.picked_user_nick != "":
                self.stop_tts_button2.show()
                self.result_box_chat_pick.verticalScrollBar().setValue(self.result_box_chat_pick.verticalScrollBar().maximum())

    def pick_done_confirm(self):
        reply = QMessageBox.question(self, '경고', '추첨을 정말 종료하시겠습니까?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.pick_done()
    
    def pick_done(self):
        self.result_box_chat_pick.setText("")
        self.result_box_list_pick.setText("")
        self.result_box_list_pick.setMaximumHeight(500000)
        self.frame1_pick.setMaximumHeight(500000)
        self.result_box_pick.setText("'모집 시작' 버튼을 눌러 추첨에 참여할 시청자를 모집하세요.")
        self.result_box_pick.setMaximumHeight(40)
        self.result_box_pick.setFont(QFont('Pretendard JP', 15))
        self.result_box_chat_pick.hide()
        self.result_button_chat_pick.hide()
        self.main_window.picked_user_nick = ""
        self.pick_list.clear()
        self.subscriber_list = []
        self.is_subscriber_list_loaded = False
        self.result_count_p.setText("0명")
        self.result_button_pick.setText("추첨하기")
        self.result_button_pick.setDisabled(True)
        self.result_button_pick.hide()
        self.toggle_button_pick.show()
        self.toggle_button_pick.setDisabled(False)
        self.pick_timer_box.hide()
        self.pick_limit_box.hide()
        self.pick_option_check1.show()
        self.pick_option_check2.show()
        self.pick_option_time.show()
        self.pick_option_count.show()
        self.pick_option_check2.show()
        self.pick_option_time.show()
        self.pick_option_count.show()
        self.main_window.is_pick_clicked = False
        self.stop_timer_pick() # 타이머 중지
        QApplication.processEvents()

    def pick_start(self):
        self.pick_option_time_cnt = self.pick_option_time.value()
        if self.toggle_button_pick.text() == '모집 시작':
            self.toggle_button_pick.setText('모집 종료')
            self.result_box_pick.setText(f"유저 모집 중입니다. '모집 종료' 버튼을 눌러 모집을 종료하세요.")
            self.result_button_pick.setDisabled(True)
            self.result_box_pick.setMaximumHeight(40)
            self.result_box_pick.setFont(QFont('Pretendard JP', 15))
            self.start_time_pick = datetime.now()
            self.result_box_chat_pick.setText("")
            self.result_box_list_pick.setText("")
            self.result_box_chat_pick.hide()
            self.result_button_chat_pick.hide()
            self.main_window.picked_user_nick = ""
            self.result_button_chat_pick.hide()
            self.main_window.picked_user_nick = ""
            self.pick_list.clear()
            self.picked_users_set.clear() # 모집 시작 시 당첨자 목록 초기화
            self.pick_option_check1.hide()
            self.pick_option_check1.hide()
            self.pick_option_check2.hide()
            self.pick_option_time.hide()
            self.pick_option_count.hide()
            self.result_count_p.setText("0명")
            QApplication.processEvents()
            
            self.subscriber_list = []
            self.is_subscriber_list_loaded = False
            if self.main_window.chatroom_connector_instance:
                self.main_window.chatroom_connector_instance.request_all_subscribers()
            else:
                 pass

            if self.pick_option_check1.isChecked():
                    self.pick_timer_box.show()
                    self.pick_timer_box.setText(f"남은 시간: {int(self.pick_option_time_cnt/60)}분 {int(self.pick_option_time_cnt%60)}초")
            if self.pick_option_check2.isChecked():
                self.pick_limit_box.show()
                self.pick_limit_box.setText(f"제한 인원: {self.pick_option_count.value()}명")
            self.start_timer_pick()
        elif self.toggle_button_pick.text() == '모집 종료':
            self.stop_timer_pick()
            self.pick_timer_box.hide()
            self.pick_limit_box.hide()
            self.toggle_button_pick.setText('모집 시작')
            self.toggle_button_pick.hide()
            self.result_box_pick.setText(f"유저 모집이 완료되었습니다. '추첨하기' 버튼을 눌러 추첨을 진행하세요.")
            self.result_box_pick.setMaximumHeight(40)
            self.result_box_pick.setFont(QFont('Pretendard JP', 15))
            self.result_button_pick.setEnabled(True)
            self.result_button_pick.show()
            self.closeTimePick = datetime.now()
            QApplication.processEvents()
    
    def pick_user(self):
        self.stop_timer_pick()
        self.result_button_pick.setText("재추첨하기")
        self.pick_count()
        if len(self.pick_list) == 0:
            self.pick_done()
            QApplication.processEvents()
            self.result_box_pick.setText("모집된 인원이 없습니다. '모집 시작' 버튼을 눌러서 다시 모집해주세요.")
        QApplication.processEvents()

    def pick_count(self):
        try:
            candidates = self.pick_list[:] # 복사본 생성
            
            if self.only_subscriber_check.isChecked():
                if not self.is_subscriber_list_loaded:
                     self.result_box_pick.setText("❗ 구독자 목록이 아직 로드되지 않았습니다. 잠시 후 다시 시도해주세요.")
                     return
                
                sub_set = set(self.subscriber_list)
                candidates = [user for user in candidates if user in sub_set]
                
                if len(candidates) == 0:
                     self.result_box_pick.setText("참여자 중 구독자가 없습니다.")
                     self.result_box_pick.setAlignment(Qt.AlignmentFlag.AlignCenter)
                     self.result_button_chat_pick.show()
                     return

            if self.remote_duplicate_check.isChecked():
                candidates = [user for user in candidates if user not in self.picked_users_set]
            
            if len(candidates) > 0:
                picknick = candidates[random.randrange(len(candidates))]
                self.main_window.is_pick_clicked = True
                print("285")
                self.result_box_pick.show()
                self.result_box_pick.setText(f"{picknick} 당첨!")
                self.result_box_pick.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.result_box_pick.setMaximumHeight(55)
                self.result_box_pick.setFont(QFont('Pretendard JP', 23))
                self.result_box_list_pick.setMaximumHeight(100)
                self.frame1_pick.setMaximumHeight(120)
                self.result_box_chat_pick.show()
                self.result_button_chat_pick.show()
                self.result_box_chat_pick.setText("최근 채팅 불러오는 중...")
                self.main_window.picked_user_nick = picknick
                
                if self.remote_duplicate_check.isChecked():
                    self.picked_users_set.add(picknick)
                
                if self.pick_chat_read_tts.isChecked():
                    self.stop_tts_button2.show()
                QApplication.processEvents()
                self.main_window.chat_log_search_tab.chat_moa()
            else:
                if self.remote_duplicate_check.isChecked() and len(self.pick_list) > 0:
                    reply = QMessageBox.question(self, '알림', 
                                                 '남은 추첨 대상이 없습니다.\n당첨자 목록을 초기화하고, 기존 모집단에서 다시 추첨하시겠습니까?',
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                                 QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        self.picked_users_set.clear()
                        self.pick_count()
                        return
                    else:
                        self.result_box_pick.setText("남은 추첨 대상이 없습니다.")
                else:
                    self.result_box_pick.setText("모집된 인원이 없습니다. '모집 시작' 버튼을 눌러서 다시 모집해주세요.")
                QApplication.processEvents()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            err = traceback.format_exc()
            errortime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.result_box_pick.setText(f"[{errortime}]\n❗오류 발생!{exc_type} {exc_tb.tb_lineno} {err} {fname}")
    
    def pick_voters(self, voters, vote_number):
        """VoteTab에서 이 함수를 호출합니다."""
        self.pick_done() # 기존 추첨 종료
        self.pick_list.clear()
        for i in voters:
            self.pick_list.append(i)
        self.result_count_p.setText(f"{len(self.pick_list)}명")
        self.result_box_list_pick.setText((" , ".join(self.pick_list)))
        self.toggle_button_pick.setText('모집 시작')
        self.toggle_button_pick.setDisabled(True) # 투표 추첨 중에는 새로 모집 불가
        self.toggle_button_pick.hide()
        self.result_box_pick.setText(f"{vote_number}번에 투표한 유저를 추첨합니다.\n'추첨하기' 버튼을 눌러 추첨을 진행하세요.")
        self.result_box_pick.setMaximumHeight(65)
        self.result_box_pick.setFont(QFont('Pretendard JP', 15))
        self.result_button_pick.setEnabled(True)
        self.result_button_pick.show()
        self.result_button_chat_pick.show() # 추첨 종료 버튼도 표시
        self.main_window.tabs.setCurrentWidget(self) # 추첨 탭으로 이동
        QApplication.processEvents()

    ##### 타이머 함수 (이 탭 전용) #####
    def start_timer_pick(self):
        self.stop_timer_pick()
        self.timer_pick_refresh = QTimer(self)
        self.timer_pick_refresh.timeout.connect(self.pick_refresh)
        self.timer_pick_refresh.start(1000)
    
    def stop_timer_pick(self):
        if hasattr(self, 'timer_pick_refresh'):
            self.timer_pick_refresh.stop()
            if hasattr(self, 'timer_pick_refresh'): # stop() 이후에도 객체가 남아있을 수 있음
                del self.timer_pick_refresh
        self.pick_refresh() # 중지 시 마지막 갱신

    def pick_refresh(self):
        # 추첨 모집 중 값 갱신
        if self.toggle_button_pick.text() == "모집 종료":
            self.result_count_p.setText(f"{len(self.pick_list)}명")
            self.result_box_list_pick.setText((" , ".join(self.pick_list)))
            if self.pick_option_check1.isChecked():
                self.pick_option_time_cnt -= 1
                self.pick_timer_box.setText(f"남은 시간: {int(self.pick_option_time_cnt/60)}분 {int(self.pick_option_time_cnt%60)}초")
                if self.pick_option_time_cnt <= 0:
                    self.pick_timer_box.hide()
                    self.toggle_button_pick.click() # 시간 종료 시 모집 자동 마감
            
            # 인원 제한 체크 (pick_refresh에서)
            if self.pick_option_check2.isChecked():
                if len(self.pick_list) >= int(self.pick_option_count.value()):
                    self.pick_limit_box.hide()
                    self.toggle_button_pick.click() # 인원 도달 시 모집 자동 마감

    ##### 메인 윈도우에서 호출할 함수 #####
    def process_pick_message(self, msg_dict):
        """메인 윈도우의 message 핸들러가 호출 (추첨 관련 메시지 처리)"""
        
        # 추첨 모집 중이 아니면 아무것도 안 함
        if self.toggle_button_pick.text() != "모집 종료":
            return

        nick = msg_dict.get('nick', '')
        donation_type = msg_dict.get('donation_type', '')

        try:
            if donation_type == "채팅":
                if nick != "익명의 후원자" and nick not in self.pick_list:
                    self.pick_list.append(nick)
                    # (UI 갱신은 pick_refresh 타이머가 하도록 둠)
        
        except Exception as e:
            print(f"Error processing pick message: {e}")