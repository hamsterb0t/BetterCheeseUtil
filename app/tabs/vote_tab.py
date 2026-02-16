import sys
import os
import traceback
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QLabel, QFrame, QCheckBox, 
                             QSpinBox, QMessageBox, QTableWidget, 
                             QTableWidgetItem, QAbstractItemView, QScrollArea, QSizePolicy, QTextEdit,
                             QComboBox, QHeaderView)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer
from collections import OrderedDict
from datetime import datetime

from app.ui_widgets import QToggle, VoteBar
from app.ui_dialogs import VotingResultWindow 

class VoteTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        
        self.main_window = main_window

        self.vote_num_list = []
        self.items_text_vote = []
        self.result_vote = {}
        self.result_vote_donation = {}
        self.result_vote_total = {}
        self.result_vote_total = {}
        self.vote_option_time_cnt = 0
        self.is_sorted_by_rank = False
        
        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        self.toggle_button_vote = QPushButton('투표 시작', self)
        self.toggle_button_vote.clicked.connect(self.vote_start)
        button_layout.addWidget(self.toggle_button_vote)

        self.toggle_button_end_vote = QPushButton('투표 종료', self)
        self.toggle_button_end_vote.clicked.connect(lambda: self.vote_done_confirm())
        button_layout.addWidget(self.toggle_button_end_vote)
        self.toggle_button_end_vote.hide()

        self.result_button_vote = QToggle(self)
        self.result_button_vote.setText("결과 보이기/숨기기")
        self.result_button_vote.setDisabled(True)
        self.result_button_vote.hide()
        button_layout.addWidget(self.result_button_vote)
        layout.addLayout(button_layout)

        option_layout = QHBoxLayout()
        self.vote_option_check1 = QCheckBox("제한 시간: ")
        self.vote_option_check1.setChecked(False)
        self.vote_option_check1.stateChanged.connect(lambda: self.vote_option_time.setEnabled(self.vote_option_check1.isChecked()))
        option_layout.addWidget(self.vote_option_check1)
        self.vote_option_time = QSpinBox(self)
        self.vote_option_time.setMinimum(0)
        self.vote_option_time.setMaximum(9999)
        self.vote_option_time.setSingleStep(10)
        self.vote_option_time.setValue(60)
        self.vote_option_time.setSuffix("초")
        self.vote_option_time.setFixedWidth(100)
        self.vote_option_time.setEnabled(False)
        option_layout.addWidget(self.vote_option_time)

        self.vote_option_check2 = QCheckBox("제한 인원: ")
        self.vote_option_check2.setChecked(False)
        self.vote_option_check2.stateChanged.connect(lambda: self.vote_option_count.setEnabled(self.vote_option_check2.isChecked()))
        option_layout.addWidget(self.vote_option_check2)
        self.vote_option_count = QSpinBox(self)
        self.vote_option_count.setMinimum(0)
        self.vote_option_count.setMaximum(9999)
        self.vote_option_count.setSingleStep(10)
        self.vote_option_count.setValue(100)
        self.vote_option_count.setSuffix("명")
        self.vote_option_count.setFixedWidth(100)
        self.vote_option_count.setEnabled(False)
        option_layout.addWidget(self.vote_option_count)
        option_layout.addStretch()
        layout.addLayout(option_layout)

        chat_vote_layout = QHBoxLayout()
        self.chat_vote_check = QToggle(self)
        self.chat_vote_check.setText("채팅 투표 ")
        self.chat_vote_check.setChecked(True)
        self.chat_vote_multiple = QCheckBox("복수 투표")
        self.chat_vote_multiple.setChecked(False)
        self.chat_vote_multiple.setEnabled(True)
        self.chat_vote_check.stateChanged.connect(lambda: self.chat_vote_multiple.setEnabled(self.chat_vote_check.isChecked()))
        
        # 인당 항목 수 제한
        self.chat_vote_limit_label = QLabel("인당 ")
        self.chat_vote_limit_label.setFont(QFont('Pretendard JP', 10))
        self.chat_vote_limit = QSpinBox(self)
        self.chat_vote_limit.setMinimum(2)
        self.chat_vote_limit.setMaximum(30)
        self.chat_vote_limit.setValue(3)
        self.chat_vote_limit.setSuffix("개 항목")
        self.chat_vote_limit.setFixedWidth(90)
        self.chat_vote_limit.setEnabled(False)
        self.chat_vote_multiple.stateChanged.connect(lambda: self.chat_vote_limit.setEnabled(self.chat_vote_multiple.isChecked() and self.chat_vote_check.isChecked()))
        self.chat_vote_check.stateChanged.connect(lambda: self.chat_vote_limit.setEnabled(self.chat_vote_multiple.isChecked() and self.chat_vote_check.isChecked()))
        
        chat_vote_layout.addWidget(self.chat_vote_check)
        chat_vote_layout.addWidget(self.chat_vote_multiple)
        chat_vote_layout.addWidget(self.chat_vote_limit_label)
        chat_vote_layout.addWidget(self.chat_vote_limit)
        chat_vote_layout.addStretch()
        layout.addLayout(chat_vote_layout)

        donation_vote_layout = QHBoxLayout()
        self.donation_vote_check = QToggle(self)
        self.donation_vote_check.setText("도네 투표 ")
        self.donation_vote_check.setChecked(False)
        self.donation_vote_number = QSpinBox(self)
        self.donation_vote_number.setMinimum(10)
        self.donation_vote_number.setMaximum(999999)
        self.donation_vote_number.setSingleStep(1000)
        self.donation_vote_number.setValue(1000)
        self.donation_vote_number.setSuffix("치즈")
        self.donation_vote_number.setFixedWidth(120)
        self.donation_vote_number.setEnabled(False)
        self.donation_vote_check.stateChanged.connect(lambda: self.donation_vote_number.setEnabled(self.donation_vote_check.isChecked()))
        self.donation_vote_multiple = QCheckBox("치즈 금액 배수로 복수 투표")
        self.donation_vote_multiple.setChecked(False)
        self.donation_vote_multiple.setEnabled(False)
        self.donation_vote_check.stateChanged.connect(lambda: self.donation_vote_multiple.setEnabled(self.donation_vote_check.isChecked()))
        donation_vote_layout.addWidget(self.donation_vote_check)
        donation_vote_layout.addWidget(self.donation_vote_number)
        donation_vote_layout.addWidget(self.donation_vote_multiple)
        donation_vote_layout.addStretch()
        layout.addLayout(donation_vote_layout)

        self.result_box_vote = QTextEdit(self)
        self.result_box_vote.setReadOnly(True)
        self.result_box_vote.setFixedHeight(40)
        self.result_box_vote.setFont(QFont('Pretendard JP', 15))
        self.result_box_vote.setText("목록을 더블클릭하여 투표 항목을 입력하세요.")
        layout.addWidget(self.result_box_vote)

        vote_timer_limit_layout = QHBoxLayout()
        self.vote_timer_box = QLabel(self)
        self.vote_timer_box.setMaximumHeight(30)
        self.vote_timer_box.setFont(QFont('Pretendard JP', 15))
        self.vote_timer_box.hide()
        vote_timer_limit_layout.addWidget(self.vote_timer_box)
        self.vote_limit_box = QLabel(self)
        self.vote_limit_box.setMaximumHeight(55)
        self.vote_limit_box.setFont(QFont('Pretendard JP', 15))
        self.vote_limit_box.hide()
        vote_timer_limit_layout.addWidget(self.vote_limit_box)
        vote_timer_limit_layout.addStretch()
        layout.addLayout(vote_timer_limit_layout)

        self.frame_vote_input = QFrame(self)
        self.frame_vote_input.setFrameShape(QFrame.Shape.StyledPanel)
        frame_layout = QVBoxLayout(self.frame_vote_input)
        count_layout = QHBoxLayout()
        self.result_count_text_vote = QLabel("투표 인원: ")
        self.result_count_text_vote.setFont(QFont('Pretendard JP', 15))
        count_layout.addWidget(self.result_count_text_vote)
        self.result_count_vote = QLabel("0명")
        self.result_count_vote.setFont(QFont('Pretendard JP', 15))
        count_layout.addWidget(self.result_count_vote)
        count_layout.addStretch()
        frame_layout.addLayout(count_layout)

        # 투표 항목 수 자동 입력 드롭다운
        auto_fill_layout = QHBoxLayout()
        auto_fill_label = QLabel("항목 수 자동 입력:")
        auto_fill_label.setFont(QFont('Pretendard JP', 12))
        auto_fill_layout.addWidget(auto_fill_label)
        
        self.vote_item_count_combo = QComboBox(self)
        self.vote_item_count_combo.setFont(QFont('Pretendard JP', 12))
        self.vote_item_count_combo.setFixedWidth(80)
        self.vote_item_count_combo.addItem("선택")  # 기본 선택 항목
        for i in range(2, 11):  # 2부터 10까지
            self.vote_item_count_combo.addItem(str(i))
        self.vote_item_count_combo.currentIndexChanged.connect(self.auto_fill_vote_items)
        auto_fill_layout.addWidget(self.vote_item_count_combo)
        auto_fill_layout.addStretch()
        frame_layout.addLayout(auto_fill_layout)

        title_layout = QHBoxLayout()
        self.vote_title = QLineEdit(self)
        self.vote_title.setPlaceholderText("제목을 입력하세요.")
        self.vote_title.setFont(QFont('Pretendard JP', 19))
        self.vote_title.setFixedHeight(40)
        title_layout.addWidget(self.vote_title)
        frame_layout.addLayout(title_layout)

        self.result_table_vote = QTableWidget(self)
        self.result_table_vote.setColumnCount(2)
        self.result_table_vote.setHorizontalHeaderLabels(['번호', '항목'])
        self.result_table_vote.setFont(QFont('Pretendard JP', 18))
        self.result_table_vote.horizontalHeader().setStretchLastSection(True)
        self.result_table_vote.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.result_table_vote.setColumnWidth(0, 60)
        frame_layout.addWidget(self.result_table_vote)
        layout.addWidget(self.frame_vote_input)

        self.result_table_vote.setRowCount(30)
        for i in range(30):
            item = QTableWidgetItem(f"{str(i+1)}번")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.result_table_vote.setItem(i, 0, item)
            self.result_table_vote.setItem(i, 1, QTableWidgetItem(""))
            self.result_table_vote.setRowHeight(i, 40)
        self.vote_num_list = [str(i+1) for i in range(30)]

        self.vote_count_frame = QFrame(self)
        self.vote_count_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.vote_count_frame.setContentsMargins(0, 0, 0, 0)
        self.vote_count_layout = QVBoxLayout(self.vote_count_frame)
        self.vote_count_layout.setContentsMargins(0, 0, 0, 0)

        frameM = QFrame(self)
        frameM.setFrameShape(QFrame.Shape.StyledPanel)
        frameM.setContentsMargins(0, 0, 0, 0)
        frameM_layout = QVBoxLayout(frameM)
        frame0 = QFrame(self)
        frame0.setFrameShape(QFrame.Shape.StyledPanel)
        frame0_layout = QVBoxLayout(frame0)

        self.vote_titlet = QLabel(self)
        self.vote_titlet.setFont(QFont('Pretendard JP', 19))
        self.vote_titlet.setFixedHeight(30)
        frame0_layout.addWidget(self.vote_titlet)

        self.vote_total = QLabel(self)
        self.vote_total.setFont(QFont('Pretendard JP', 15))
        self.vote_total.setFixedHeight(30)
        frame0_layout.addWidget(self.vote_total)

        self.vote_frame1 = QFrame(self)
        self.vote_frame1.setFrameShape(QFrame.Shape.StyledPanel)
        self.vote_frame1_layout = QVBoxLayout(self.vote_frame1)
        self.vote_frame1_layout.addStretch()

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_area.setWidget(self.vote_frame1)
        frame0_layout.addWidget(scroll_area)
        frameM_layout.addWidget(frame0)

        buttons_layout = QHBoxLayout()
        self.vote_sort_button = QPushButton()
        self.vote_sort_button.setText("순위순 정렬")
        self.vote_sort_button.setFont(QFont('Pretendard JP', 14))
        self.vote_sort_button.clicked.connect(self.toggle_sort_rank)
        buttons_layout.addWidget(self.vote_sort_button)

        self.vote_user_list_button = QPushButton()
        self.vote_user_list_button.setText("투표자 명단")
        self.vote_user_list_button.setFont(QFont('Pretendard JP', 14))
        self.vote_user_list_button.clicked.connect(lambda : self.show_voters(self.result_vote_total))
        buttons_layout.addWidget(self.vote_user_list_button)

        frameM_layout.addLayout(buttons_layout)

        self.vote_frame2 = QFrame(self)
        self.vote_frame2.setFrameShape(QFrame.Shape.StyledPanel)
        self.vote_frame2_layout = QVBoxLayout(self.vote_frame2)
        self.vote_pick_layout = QHBoxLayout()
        vote_user_pick_label = QLabel("투표 항목 별 유저 추첨하기")
        vote_user_pick_label.setFont(QFont('Pretendard JP', 14))
        self.vote_frame2_layout.addWidget(vote_user_pick_label)
        self.vote_pick_layout.addStretch()
        self.vote_frame2_layout.addLayout(self.vote_pick_layout)
        frameM_layout.addWidget(self.vote_frame2)
        frameM.setLayout(frameM_layout)
        self.vote_count_layout.addWidget(frameM)
        layout.addWidget(self.vote_count_frame)
        self.vote_count_frame.setVisible(False)

        self.result_button_vote.clicked.connect(
            lambda: (
                self.frame_vote_input.setVisible(not self.result_button_vote.isChecked()),
                self.vote_count_frame.setVisible(self.result_button_vote.isChecked())
            )
        )
        
        self.setLayout(layout)
        
        self.load_settings_from_main()

    ##### 투표 탭 관련 함수 #####

    def load_settings_from_main(self):
        """메인 윈도우의 설정 값을 이 탭의 위젯에 적용하고, 위젯 참조를 교체합니다."""
        mw = self.main_window
        
        mw.toggle_button_vote = self.toggle_button_vote
        mw.VOTE_STOP_BUTTON_TEXT = mw.VOTE_STOP_BUTTON_TEXT
        mw.chat_vote_check = self.chat_vote_check
        mw.donation_vote_check = self.donation_vote_check
        mw.chat_vote_multiple = self.chat_vote_multiple
        mw.result_vote = self.result_vote
        mw.vote_num_list = self.vote_num_list
        mw.donation_vote_multiple = self.donation_vote_multiple
        mw.donation_vote_number = self.donation_vote_number
        mw.result_vote_donation = self.result_vote_donation
        mw.vote_option_check1 = self.vote_option_check1
        mw.vote_option_count = self.vote_option_count

    def auto_fill_vote_items(self, index):
        """드롭다운에서 항목 수를 선택하면 투표 항목을 리셋하고 숫자로 자동 입력"""
        if index == 0:  # "선택" 항목이 선택된 경우 무시
            return
        
        count = int(self.vote_item_count_combo.currentText())
        
        # 모든 항목 초기화 후 선택된 수만큼 숫자로 입력
        for i in range(30):
            if i < count:
                self.result_table_vote.setItem(i, 1, QTableWidgetItem(str(i + 1)))
            else:
                self.result_table_vote.setItem(i, 1, QTableWidgetItem(""))
        
        # 드롭다운을 다시 "선택"으로 리셋
        self.vote_item_count_combo.blockSignals(True)
        self.vote_item_count_combo.setCurrentIndex(0)
        self.vote_item_count_combo.blockSignals(False)

    def vote_done_confirm(self):
        reply = QMessageBox.question(self, '경고', '투표를 정말 종료하시겠습니까?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.vote_done()

    def vote_done(self):
        self.result_box_vote.setText("목록을 더블클릭하여 투표 항목을 입력하세요.")
        self.result_box_vote.setFixedHeight(40)
        self.toggle_button_vote.show()
        self.toggle_button_end_vote.hide()
        if self.result_button_vote.isChecked():
            self.result_button_vote.click()
        self.result_button_vote.setDisabled(True)
        self.result_button_vote.hide()
        self.vote_title.setText("")
        self.vote_title.setReadOnly(False)

        for i in range(10):
            item = QTableWidgetItem(f"{str(i+1)}번")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.result_table_vote.setItem(i, 0, item)
            self.result_table_vote.setItem(i, 1, QTableWidgetItem(""))
            self.result_table_vote.setRowHeight(i, 40)
        for i in range(10, 30):
            self.result_table_vote.setItem(i, 1, QTableWidgetItem(""))
            
        self.result_count_vote.setText("0명")
        self.result_table_vote.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self.vote_timer_box.hide()
        self.vote_limit_box.hide()
        self.vote_option_check1.show()
        self.vote_option_check2.show()
        self.vote_option_time.show()
        self.vote_option_count.show()
        self.donation_vote_check.show()
        self.donation_vote_number.show()
        self.donation_vote_multiple.show()
        self.chat_vote_check.show()
        self.chat_vote_multiple.show()
        self.chat_vote_limit_label.show()
        self.chat_vote_limit.show()
        
        self.stop_timer_vote()
    
    def vote_start(self):
        self.items_text_vote = []
        self.vote_num_list = []
        self.vote_option_time_cnt = self.vote_option_time.value()
        for i in range(30):
            if self.result_table_vote.item(i,1) != None:
                if self.result_table_vote.item(i,1).text() != '':
                    self.items_text_vote.append(self.result_table_vote.item(i,1).text())
                    self.vote_num_list.append(str(i+1))
                else:
                    break
                    
        VOTE_STOP_BUTTON_TEXT = self.main_window.VOTE_STOP_BUTTON_TEXT
        
        if self.toggle_button_vote.text() == '투표 시작':
            if self.chat_vote_check.isChecked() == False and self.donation_vote_check.isChecked() == False:
                self.result_box_vote.setText("채팅 투표와 도네 투표 둘 중 적어도 하나를 선택하세요.")
            elif len(self.items_text_vote) <=1: self.result_box_vote.setText("투표 항목을 2개 이상으로 설정하세요.")
            else:
                self.result_vote = {item: [] for item in self.vote_num_list}
                self.result_vote_donation = {item: [] for item in self.vote_num_list}
                self.result_vote_total = {item: [] for item in self.vote_num_list}
                self.vote_title.setReadOnly(True)
                self.toggle_button_vote.setText(VOTE_STOP_BUTTON_TEXT)
                
                if self.chat_vote_check.isChecked() and not self.donation_vote_check.isChecked():
                    self.result_box_vote.setFixedHeight(150)
                    if self.chat_vote_multiple.isChecked(): # 채팅 투표(복수 허용)
                        limit = self.chat_vote_limit.value()
                        self.result_box_vote.setText(f"투표 진행 중입니다. {VOTE_STOP_BUTTON_TEXT} 버튼을 눌러 투표를 종료하세요.\n명령어: !투표 (숫자)\n[[💬채팅 투표]]\n  ✅1인당 최대 {limit}개 항목까지 투표 가능합니다.\n  ✅항목당 1회만 투표됩니다. (중복 투표 불가)")
                    else: # 채팅 투표(복수 불가)
                        self.result_box_vote.setText(f"투표 진행 중입니다. {VOTE_STOP_BUTTON_TEXT} 버튼을 눌러 투표를 종료하세요.\n명령어: !투표 (숫자)\n[[💬채팅 투표]]\n  ✅재입력시 본인 투표 수정이 가능합니다.\n  🚫복수 투표 불가합니다.")

                elif not self.chat_vote_check.isChecked() and self.donation_vote_check.isChecked():
                    self.result_box_vote.setFixedHeight(200)
                    if self.donation_vote_multiple.isChecked(): # 도네 투표(복수 허용)
                        self.result_box_vote.setText(f"투표 진행 중입니다. {VOTE_STOP_BUTTON_TEXT} 버튼을 눌러 투표를 종료하세요.\n명령어: !투표 (숫자)\n[[💸도네 투표]]\n  {self.donation_vote_number.value()}치즈 당 투표 1번입니다. (복수 투표 가능)\n  ✅익명 후원 투표 가능합니다.\n  ✅여러 번 후원하여 복수 투표 가능합니다.\n  ✅한 사람이 여러 항목에 투표하는 것도 가능합니다.")
                    else: # 도네 투표(복수 불가)
                        self.result_box_vote.setText(f"투표 진행 중입니다. {VOTE_STOP_BUTTON_TEXT} 버튼을 눌러 투표를 종료하세요.\n명령어: !투표 (숫자)\n[[💸도네 투표]]\n  {self.donation_vote_number.value()}치즈 이상 후원 시 1회 투표됩니다. (1인당 1투표)\n  🚫복수 투표 불가합니다.\n  🚫익명 후원 투표 불가합니다.\n  🚫투표 수정 불가합니다.")

                elif self.chat_vote_check.isChecked() and self.donation_vote_check.isChecked():
                    self.result_box_vote.setFixedHeight(280)
                    if self.chat_vote_multiple.isChecked() and self.donation_vote_multiple.isChecked(): # 채팅 투표(복수 허용) + 도네 투표(복수 허용)
                        limit = self.chat_vote_limit.value()
                        self.result_box_vote.setText(f"투표 진행 중입니다. {VOTE_STOP_BUTTON_TEXT} 버튼을 눌러 투표를 종료하세요.\n명령어: !투표 (숫자)\n[[💬채팅 투표]]\n  ✅1인당 최대 {limit}개 항목까지 투표 가능합니다.\n  ✅항목당 1회만 투표됩니다. (중복 투표 불가)\n[[💸도네 투표]]\n  {self.donation_vote_number.value()}치즈 당 투표 1번입니다. (복수 투표 가능)\n  ✅익명 후원 투표 가능합니다.\n  ✅여러 번 후원하여 복수 투표 가능합니다.\n  ✅한 사람이 여러 항목에 투표하는 것도 가능합니다.")
                    elif self.chat_vote_multiple.isChecked() and not self.donation_vote_multiple.isChecked(): # 채팅 투표(복수 허용) + 도네 투표(복수 불가)
                        limit = self.chat_vote_limit.value()
                        self.result_box_vote.setText(f"투표 진행 중입니다. {VOTE_STOP_BUTTON_TEXT} 버튼을 눌러 투표를 종료하세요.\n명령어: !투표 (숫자)\n[[💬채팅 투표]]\n  ✅1인당 최대 {limit}개 항목까지 투표 가능합니다.\n  ✅항목당 1회만 투표됩니다. (중복 투표 불가)\n[[💸도네 투표]]\n  {self.donation_vote_number.value()}치즈 이상 후원 시 1회 투표됩니다. (1인당 1투표)\n  🚫복수 투표 불가합니다.\n  🚫익명 후원 투표 불가합니다.\n  🚫투표 수정 불가합니다.")
                    elif not self.chat_vote_multiple.isChecked() and self.donation_vote_multiple.isChecked(): # 채팅 투표(복수 불가) + 도네 투표(복수 허용)
                        self.result_box_vote.setText(f"투표 진행 중입니다. {VOTE_STOP_BUTTON_TEXT} 버튼을 눌러 투표를 종료하세요.\n명령어: !투표 (숫자)\n[[💬채팅 투표]]\n  ✅재입력시 본인 투표 수정이 가능합니다.\n  🚫복수 투표 불가합니다.\n[[💸도네 투표]]\n  {self.donation_vote_number.value()}치즈 당 투표 1번입니다. (복수 투표 가능)\n  ✅익명 후원 투표 가능합니다.\n  ✅여러 번 후원하여 복수 투표 가능합니다.\n  ✅한 사람이 여러 항목에 투표하는 것도 가능합니다.")
                    else: # 채팅 투표(복수 불가) + 도네 투표(복수 불가)
                        self.result_box_vote.setText(f"투표 진행 중입니다. {VOTE_STOP_BUTTON_TEXT} 버튼을 눌러 투표를 종료하세요.\n명령어: !투표 (숫자)\n[[💬채팅 투표]]\n  ✅재입력시 본인 투표 수정이 가능합니다.\n  🚫복수 투표 불가합니다.\n[[💸도네 투표]]\n  {self.donation_vote_number.value()}치즈 이상 후원 시 1회 투표됩니다. (1인당 1투표)\n  🚫복수 투표 불가합니다.\n  🚫익명 후원 투표 불가합니다.\n  🚫투표 수정 불가합니다.")
                
                self.vote_option_check1.hide()
                self.vote_option_check2.hide()
                self.vote_option_time.hide()
                self.vote_option_count.hide()
                self.donation_vote_check.hide()
                self.donation_vote_number.hide()
                self.donation_vote_multiple.hide()
                self.chat_vote_check.hide()
                self.chat_vote_multiple.hide()
                self.chat_vote_limit_label.hide()
                self.chat_vote_limit.hide()
                self.result_table_vote.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                self.result_button_vote.setEnabled(True)
                self.result_button_vote.show()
                self.start_time_vote = datetime.now()
                self.toggle_button_vote.show()
                if self.vote_option_check1.isChecked():
                    self.vote_timer_box.show()
                    self.vote_timer_box.setText(f"남은 시간: {int(self.vote_option_time_cnt/60)}분 {int(self.vote_option_time_cnt%60)}초")
                if self.vote_option_check2.isChecked():
                    self.vote_limit_box.show()
                    self.vote_limit_box.setText(f"제한 인원: {self.vote_option_count.value()}명")
                self.start_timer_vote()
                self.vote_count()

        elif self.toggle_button_vote.text() == VOTE_STOP_BUTTON_TEXT:
            self.toggle_button_vote.setText('투표 시작')
            self.vote_timer_box.hide()
            self.vote_limit_box.hide()
            self.result_box_vote.setFixedHeight(65)
            self.result_box_vote.setText(f"투표 집계가 완료되었습니다.\n결과를 확인하세요.")
            self.toggle_button_end_vote.show()
            self.toggle_button_vote.hide()
            self.result_button_vote.setEnabled(True)
            self.closeTimeVote = datetime.now()
            self.stop_timer_vote()

    def toggle_sort_rank(self):
        self.is_sorted_by_rank = not self.is_sorted_by_rank
        if self.is_sorted_by_rank:
            self.vote_sort_button.setText("번호순 정렬")
        else:
            self.vote_sort_button.setText("순위순 정렬")
        self.vote_count()

    def vote_people_count(self):
        try:
            all_keys = list(self.result_vote.keys()) + [
                key for key in self.result_vote_donation.keys() if key not in self.result_vote
            ]
            self.result_vote_total = OrderedDict(
                (key, self.result_vote.get(key, []) + self.result_vote_donation.get(key, []))
                for key in all_keys
            )
            self.vote_titlet.setText(self.vote_title.text())
            if self.vote_titlet.text() == "":
                self.vote_titlet.hide()
            else: self.vote_titlet.show()
            total_votes = sum(len(voters) for voters in self.result_vote_total.values())
            return total_votes
        except:
            return 0

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self.clear_layout(sub_layout)

    def vote_count(self):
        try:
            total_votes = self.vote_people_count()
            self.vote_total.setText(f"투표 인원: {total_votes}명")
            self.result_count_vote.setText(f"{total_votes}명")
            self.clear_layout(self.vote_frame1_layout)
            
            if len(self.items_text_vote) < len(self.vote_num_list):
                print("Warning: 투표 항목 텍스트가 부족합니다.")
                for i in range(len(self.items_text_vote), len(self.vote_num_list)):
                    self.items_text_vote.append(f"항목 {i+1}")
            
            # 정렬 로직
            sorted_items = []
            if self.is_sorted_by_rank:
                # 득표수 내림차순 정렬 (득표수 같으면 번호순)
                # self.result_vote_total.items()는 (번호, 투표자목록) 튜플 리스트
                # 번호는 문자열이므로 int로 변환해 비교해야 함. 
                # 득표수 내림차순(-len), 번호 오름차순(int key)
                sorted_items = sorted(
                    self.result_vote_total.items(), 
                    key=lambda item: (-len(item[1]), int(item[0]))
                )
            else:
                # 번호순 정렬
                sorted_items = self.result_vote_total.items()

            current_rank = 1
            last_count = -1
            same_rank_stack = 0 # 동점자 수 누적
            
            for index, (vote_number, voters) in enumerate(sorted_items):
                vote_index = int(vote_number) - 1
                if vote_index < 0 or vote_index >= len(self.items_text_vote):
                    print(f"Error: 유효하지 않은 투표 번호 {vote_number}")
                    continue
                    
                item_text = self.items_text_vote[vote_index]
                vote_count_val = len(voters)
                
                # 순위 계산 (정렬 상태일 때만 의미 있음, 하지만 항상 계산해도 무방)
                if self.is_sorted_by_rank:
                    if last_count != vote_count_val:
                        current_rank += same_rank_stack
                        same_rank_stack = 1
                    else:
                        same_rank_stack += 1
                    last_count = vote_count_val
                    rank_text = f"[{current_rank}위]"
                else:
                    rank_text = ""

                if total_votes == 0: 
                    label = QLabel(f'{rank_text} {vote_number}번: {vote_count_val}명 (0%)\n{item_text}')
                else: 
                    label = QLabel(f'{rank_text} {vote_number}번: {vote_count_val}명 ({round(vote_count_val*100/total_votes, 3)}%)\n{item_text}')
                
                label.setFont(QFont('Pretendard JP', 18))
                if total_votes == 0: self.vote_bar = VoteBar(1, voters, self)
                else: self.vote_bar = VoteBar(total_votes, voters, self)
                self.vote_frame1_layout.addWidget(label)
                self.vote_frame1_layout.addWidget(self.vote_bar)
            
            self.vote_frame1_layout.addStretch()
            self.clear_layout(self.vote_pick_layout)
            
            for vote_number, voters in self.result_vote_total.items():
                if int(vote_number) > 10: continue
                button_p = QPushButton()
                button_p.setText(f"{vote_number}번")
                button_p.clicked.connect(lambda checked, v=voters, vn=vote_number : self.main_window.pick_tab.pick_voters(v,vn))
                button_p.setFont(QFont('Pretendard JP', 14))
                button_p.setFixedWidth(50)
                self.vote_pick_layout.addWidget(button_p)
                if len(voters) == 0:
                    button_p.setDisabled(True)
            self.vote_pick_layout.addStretch()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            err = traceback.format_exc()
            errortime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.result_box_vote.setText(f"[{errortime}]\n❗오류 발생!{exc_type} {exc_tb.tb_lineno} {err} {fname}")
    
    def show_voters(self, result):
        self.voting_result_window = VotingResultWindow(result)
        self.voting_result_window.setWindowFlags(self.voting_result_window.windowFlags())
        self.voting_result_window.setGeometry(
                self.main_window.geometry().center().x() - 500 // 2,
                self.main_window.geometry().center().y() - 500 // 2,
                500, 500
            )
        self.voting_result_window.show()

    ##### 타이머 함수 (이 탭 전용) #####
    def start_timer_vote(self):
        self.stop_timer_vote()
        self.timer_vote_refresh = QTimer(self)
        self.timer_vote_refresh.timeout.connect(self.vote_refresh)
        self.timer_vote_refresh.start(1000)
    
    def stop_timer_vote(self):
        if hasattr(self, 'timer_vote_refresh'):
            self.timer_vote_refresh.stop()
            if hasattr(self, 'timer_vote_refresh'):
                del self.timer_vote_refresh
        self.vote_refresh()

    def vote_refresh(self):
        if self.toggle_button_vote.text() == self.main_window.VOTE_STOP_BUTTON_TEXT:
            if self.vote_option_check1.isChecked():
                self.vote_option_time_cnt -= 1
                self.vote_timer_box.setText(f"남은 시간: {int(self.vote_option_time_cnt/60)}분 {int(self.vote_option_time_cnt%60)}초")
                if self.vote_option_time_cnt <= 0:
                    self.toggle_button_vote.click()

    def process_vote_message(self, msg_dict):
        """메인 윈도우의 message 핸들러가 호출 (투표 관련 메시지 처리)"""
        if self.toggle_button_vote.text() != self.main_window.VOTE_STOP_BUTTON_TEXT:
            return

        nick = msg_dict.get('nick', '')
        msg = msg_dict.get('msg', '')
        donation_type = msg_dict.get('donation_type', '')
        cheese = msg_dict.get('cheese', 0)

        try:
            if donation_type == "채팅" and self.chat_vote_check.isChecked() and msg.startswith("!투표"):
                vote_num_str = msg.replace("!투표", "").strip()
                if not vote_num_str: return
                vote_num = int(vote_num_str)
                vote_num_str = str(vote_num)
                
                if vote_num_str in self.vote_num_list:
                    if self.chat_vote_multiple.isChecked():
                        # 복수 투표: 인당 항목 수 제한 적용
                        # 1. 이미 해당 항목에 투표했는지 확인 (항목당 1회만)
                        if nick in self.result_vote[vote_num_str]:
                            return  # 이미 이 항목에 투표함
                        
                        # 2. 투표한 항목 수 확인
                        voted_items_count = sum(1 for voters in self.result_vote.values() if nick in voters)
                        if voted_items_count >= self.chat_vote_limit.value():
                            return  # 이미 제한 개수만큼 투표함
                        
                        self.result_vote[vote_num_str].append(nick)
                    else: # 복수 투표 불허
                        for num, voters in self.result_vote.items():
                            if nick in voters:
                                voters.remove(nick)
                                break
                        self.result_vote[vote_num_str].append(nick)
                    self.vote_count() # UI 갱신

            elif donation_type == '치즈' and self.donation_vote_check.isChecked() and msg.startswith("!투표"):
                vote_num_str = msg.replace("!투표", "").strip()
                if not vote_num_str: return
                vote_num = int(vote_num_str)
                vote_num_str = str(vote_num)
                
                if vote_num_str not in self.vote_num_list: return
                    
                if self.donation_vote_multiple.isChecked():
                    vote_quantity = int(int(cheese) / self.donation_vote_number.value())
                    if vote_quantity > 0:
                        for _ in range(vote_quantity):
                            self.result_vote_donation[vote_num_str].append(nick)
                else: # 복수 투표 불허 (익명 투표도 불허)
                    if nick != "익명의 후원자" and int(cheese) >= self.donation_vote_number.value():
                        has_voted = False
                        for item_voters in self.result_vote_donation.values():
                            if nick in item_voters:
                                has_voted = True
                                break
                        if not has_voted:
                            self.result_vote_donation[vote_num_str].append(nick)
                self.vote_count() # UI 갱신

            # 인원 제한 체크
            if self.vote_option_check2.isChecked():
                total_votes = self.vote_people_count()
                if total_votes >= self.vote_option_count.value():
                    self.toggle_button_vote.click() # 인원 도달 시 투표 자동 마감

        except (ValueError, IndexError):
            return
        except Exception as e:
            print(f"Error processing vote message: {e}")