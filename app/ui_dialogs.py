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
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QCloseEvent, QAction, QMouseEvent
from PyQt6.QtCore import Qt, QSettings, QUrl, QTimer, pyqtSignal, QSize, QEvent, QPointF

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript, QWebEnginePage, QWebEngineSettings


from app.resources import resource_path
from app.constants import USERPATH, VERSION, BUILDNUMBER
from app.ui_widgets import QToggle

class TabManagementDialog(QDialog):
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

# 주입할 자바스크립트 (수정됨: 안전하게 실행)
INJECT_JS = """
(function() {
    if (window.top === window.self) console.log('[Overlay] INJECT_JS STARTED');

    // Force PC User-Agent (Navigator Override)
    try {
        const newUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0";
        const newPlatform = "Win32";
        const newVendor = "";

        const overrideNavigator = (nav) => {
            try {
                Object.defineProperty(nav, 'userAgent', { get: () => newUserAgent, configurable: true });
                Object.defineProperty(nav, 'platform', { get: () => newPlatform, configurable: true });
                Object.defineProperty(nav, 'maxTouchPoints', { get: () => 0, configurable: true });
                Object.defineProperty(nav, 'vendor', { get: () => newVendor, configurable: true });
                Object.defineProperty(nav, 'deviceMemory', { get: () => 8, configurable: true });
                Object.defineProperty(nav, 'hardwareConcurrency', { get: () => 8, configurable: true });
                if (nav.userAgentData) {
                    delete nav.userAgentData;
                }
            } catch (e) {}
        };

        overrideNavigator(navigator);
        
        // Disable Touch Events if they exist
        if ('ontouchstart' in window) { window.ontouchstart = undefined; }
        if ('ontouchend' in window) { window.ontouchend = undefined; }
        if ('ontouchmove' in window) { window.ontouchmove = undefined; }
        if ('ontouchcancel' in window) { window.ontouchcancel = undefined; }
        if (window.top === window.self) console.log("[Overlay] Forced PC User-Agent overrides applied to current frame.");
    } catch (e) {
        console.error("[Overlay] Failed to override User-Agent:", e);
    }

    // Force Viewport for PC
    try {
        if (window.top === window.self) {
            const meta = document.createElement('meta');
            meta.name = 'viewport';
            meta.content = 'width=1280, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
            
            const head = document.head || document.getElementsByTagName('head')[0] || document.documentElement;
            head.appendChild(meta);
            console.log('[Overlay] Forced Viewport: width=1280');
        }
    } catch(e) {
        console.error("[Overlay] Failed to inject viewport:", e);
    }

    // Only run the following logic in the TOP frame
    if (window.top !== window.self) {
        return;
    }

    // 1. 영상 후원 스킵 로직 (즉시 실행 필요)
    const TARGET_MIN = 2500;
    const TARGET_MAX = 3500;
    const SKIP_COOLDOWN = 500;
    let lastSkipTime = 0;
    const originalSetTimeout = window.setTimeout;

    if (window.top === window.self) console.log('[Overlay] Script Loaded. Overwriting setTimeout...');

    window.setTimeout = function(callback, delay, ...args) {
        const numericDelay = parseInt(delay, 10);
        if (!isNaN(numericDelay) && numericDelay >= TARGET_MIN && numericDelay <= TARGET_MAX) {
            const now = Date.now();
            if (now - lastSkipTime > SKIP_COOLDOWN) {
                console.log(`[Overlay] Skipped ${numericDelay}ms timer.`);
                lastSkipTime = now;
                return originalSetTimeout(callback, 0, ...args);
            }
        }
        return originalSetTimeout(callback, delay, ...args);
    };

    // 2. 투명 배경 및 커스텀 CSS 강제 적용 - DOM 로드 대기 후 실행
    function injectCustomCSS() {
        if (document.head) {
            const style = document.createElement('style');
            style.innerHTML = `
                * {
                    margin: 0 !important;
                    padding: 0 !important;
                    box-sizing: border-box !important;
                }

                html, body {
                    line-height: 0 !important;
                    width: 100%;
                    height: 100%;
                    overflow: hidden;
                    background-color: rgba(0, 0, 0, 0) !important;
                }

                [class*="overlay_donation_alarm"] {
                    position: relative !important;
                    width: 1280px;
                    height: 1254px;
                    overflow: hidden !important;
                }

                [class*="overlay_donation_alarm"] * {
                    pointer-events: none;
                }

                /* 기본(가로) 모드: 영상은 상단 1280x720 유지 (혹은 화면 꽉 차게 하려면 수정 필요하지만, 기존 유지) */
                iframe[src*="youtube.com"],
                iframe[src*="youtube-nocookie.com"],
                iframe[src*="/embed-clip-donation/"],
                iframe#chzzk_player {
                    display: block !important; /* 추가 */
                    position: absolute !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 1280px !important;
                    height: 720px !important;
                    border: none !important;
                    box-shadow: none !important;
                    outline: none !important;
                    pointer-events: auto !important;
                    display: block !important;
                    background-color: transparent !important;
                    /* vertical-align: bottom !important; */
                }

                [class*="overlay_donation_contents"] {
                    position: absolute !important;
                    top: 720px !important;
                    left: 0 !important;
                    width: 100% !important;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 10px;
                    padding: 10px 30px 20px 30px;
                    overflow: visible !important;
                }

                /* ... 폰트 등 기존 유지 ... */
                [class*="overlay_donation_description"],
                [class*="overlay_donation_video_title"] {
                    width: 100% !important;
                    font-size: 36px !important;
                    line-height: 56px !important;
                    font-weight: bold !important;
                    color: white !important;
                    text-align: center !important;
                    word-break: keep-all;
                }

                [class*="overlay_donation_description"],
                [class*="overlay_donation_text"] span,
                [class*="overlay_donation_video_title"] {
                    text-shadow: 0 0 7px black, 0 0 12px black !important;
                }

                [class*="overlay_donation_icon_cheese"],
                [class*="badge_container"] img,
                [class*="live_chatting_username_icon"] img {
                    height: 48px !important;
                    width: 48px !important;
                    position: relative;
                    top: 2px;
                }

                [class*="live_chatting_username_wrapper"],
                [class*="live_chatting_username_container"] {
                    display: inline-flex !important;
                    align-items: center !important;
                }

                [class*="overlay_donation_description"] {
                    padding: 0 20px !important;
                }

                [class*="overlay_donation_text"] {
                    width: max-content !important;
                    min-width: 100% !important;
                    white-space: nowrap !important;
                    font-size: 40px !important;
                    line-height: 50px !important;
                    font-weight: normal !important;
                    color: white !important;
                    padding: 15px 10px 5px 10px !important;
                    display: flex !important;
                    justify-content: center !important;
                    align-items: center !important;
                }

                [class*="live_chatting_username_wrapper"] {
                    gap: 6px !important;
                    margin-right: 5px !important;
                }

                [class*="overlay_donation_video_title"] {
                    padding: 20px 30px !important;
                }

                [class*="overlay_donation_money"] {
                    margin-right: 5px !important;
                }

                /* 세로 모드 (Portrait) */
                body.portrait [class*="overlay_donation_alarm"] {
                    /* width는 main과 동일하게 1280 유지, height도 1254 유지 */
                }

                body.portrait iframe[src*="youtube.com"],
                body.portrait iframe[src*="youtube-nocookie.com"],
                body.portrait iframe[src*="/embed-clip-donation/"],
                body.portrait iframe#chzzk_player {
                    width: 576px !important;
                    height: 1024px !important;
                }

                body.portrait [class*="overlay_donation_contents"] {
                    top: 1024px !important; /* 영상 아래에 배치 */
                    width: 576px !important; /* 영상 너비에 맞춤 */
                    overflow: visible !important;
                }

                /* 정렬 클래스 - 1280 너비 기준 */
                body.portrait.align-center iframe,
                body.portrait.align-center #chzzk_player,
                body.portrait.align-center [class*="overlay_donation_contents"] {
                   position: absolute !important;
                   left: 352px !important; /* (1280-576)/2 */
                   margin: 0 !important;
                   transform: none !important;
                }
                body.portrait.align-left iframe,
                body.portrait.align-left #chzzk_player,
                body.portrait.align-left [class*="overlay_donation_contents"] {
                   position: absolute !important;
                   left: 0px !important;
                   margin: 0 !important;
                   transform: none !important;
                }
                body.portrait.align-right iframe,
                body.portrait.align-right #chzzk_player,
                body.portrait.align-right [class*="overlay_donation_contents"] {
                   position: absolute !important;
                   left: 704px !important; /* 1280-576 */
                   margin: 0 !important;
                   transform: none !important;
                }
            `;
            document.head.appendChild(style);
            console.log('[Overlay] Custom CSS Injected.');
        } else {
            // 아직 head가 없으면 다음 프레임에 재시도
            requestAnimationFrame(injectCustomCSS);
        }
    }
    injectCustomCSS();
    
    // 혹시 모를 상황 대비 window loaded 이벤트에도 추가
    window.addEventListener('load', injectCustomCSS);
})();


function toggleOrientation(isPortrait) {
    if (isPortrait) {
        document.body.classList.add('portrait');
    } else {
        document.body.classList.remove('portrait');
    }
}

function setAlignment(alignment) {
    document.body.classList.remove('align-left', 'align-center', 'align-right');
    document.body.classList.add('align-' + alignment);
}

// 3. 비디오 재생 상태 모니터링 (MutationObserver)
(function() {
    function startMonitoring() {
        const targetNode = document.getElementById('root');
        if (!targetNode) {
            setTimeout(startMonitoring, 500); 
            return;
        }

        let isVideoPlaying = false;
        let lastVideoSrc = ""; // Track src to detect changes

        // 설정: 자식 요소의 추가/삭제 및 속성 변경(src)을 감시
        const config = { childList: true, subtree: true, attributes: true, attributeFilter: ['src'] };

        const callback = function(mutationsList, observer) {
            // #root 내부에서 iframe 요소를 찾음
            const iframe = targetNode.querySelector('iframe');
            
            // 현재 재생 상태 확인 (iframe이 있으면 재생 중)
            const currentPlayingState = !!iframe;
            const currentSrc = iframe ? iframe.src : "";

            // 상태가 변했거나, 재생 중인데 src가 변한 경우
            if (currentPlayingState !== isVideoPlaying || (currentPlayingState && currentSrc !== lastVideoSrc)) {
                if (currentPlayingState) {
                    // 영상이 막 재생되기 시작한 경우 OR 다른 영상으로 바뀐 경우
                    // 중복 로그 방지: src가 다를 때만 로그 출력
                    if (currentSrc !== lastVideoSrc) {
                         console.log("유튜브 영상 재생 시작됨. 영상 주소:", currentSrc);
                         lastVideoSrc = currentSrc;
                    }
                } else {
                    // 영상 재생이 끝난 경우
                    console.log("유튜브 영상 재생 종료됨");
                    lastVideoSrc = "";
                }
                isVideoPlaying = currentPlayingState;
            }
        };

        const observer = new MutationObserver(callback);
        observer.observe(targetNode, config);

        console.log("%c[감지 시작] 치지직 영상후원 상태를 모니터링합니다.");
        
        // 추가: 자동 재생이 안 되었을 경우를 대비한 강제 클릭 (Fallback)
        setTimeout(() => {
            const iframe = targetNode.querySelector('iframe');
            if (iframe && !isVideoPlaying) {
                 console.log("[Overlay] Autoplay fallback: attempting to click iframe...");
                 // iframe의 위치를 찾아 클릭 이벤트를 보냄 (혹은 focus)
                 iframe.focus(); 
                 // 유튜브 iframe 내부는 cross-origin이라 직접 클릭이 어려울 수 있음.
                 // 하지만 WebEngineSettings.PlaybackRequiresUserGesture = False면 
                 // src가 로드되는 순간 대부분 해결됨.
                 // 여기서는 '혹시나' 하는 마음에 iframe이 로드되었는데 재생 상태가 아니면 로그만 남김.
            }
        }, 3000);
    }



    if (document.readyState === 'loading') {
        window.addEventListener('DOMContentLoaded', startMonitoring);
    } else {
        startMonitoring();
    }
})();

// 5. Chzzk Smart Resolution Detection (Auto-Rotation)
(function() {
    let lastResolutionType = null;

    function reportResolution(video) {
        if (!video || video.videoWidth === 0 || video.videoHeight === 0) return;
        
        const ratio = video.videoWidth / video.videoHeight;
        let type = "landscape";
        if (ratio < 0.6) { // Loose check for 9:16 (0.5625)
            type = "portrait";
        }
        
        // Report only if changed or first time
        if (lastResolutionType !== type) {
            console.log(`[ChzzkResolution] ${type} (${video.videoWidth}x${video.videoHeight})`);
            lastResolutionType = type;
        }
    }

    function setupChzzkObserver() {
        const iframe = document.getElementById('chzzk_player');
        if (!iframe) {
            window._bcuChzzkObserved = false;
            return;
        }
        if (window._bcuChzzkObserved) return;
        
        window._bcuChzzkObserved = true;
        try {
            const innerDoc = iframe.contentWindow.document;
            
            // 1. Check existing video
            const existingVideo = innerDoc.querySelector('video');
            if (existingVideo) {
                reportResolution(existingVideo);
                existingVideo.addEventListener('loadedmetadata', () => reportResolution(existingVideo));
            }

            // 2. Observe for new video elements in iframe
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.tagName === 'VIDEO') {
                            reportResolution(node);
                            node.addEventListener('loadedmetadata', () => reportResolution(node));
                        } else if (node.querySelectorAll) {
                            const vids = node.querySelectorAll('video');
                            vids.forEach(v => {
                                reportResolution(v);
                                v.addEventListener('loadedmetadata', () => reportResolution(v));
                            });
                        }
                    });
                });
            });
            const obsTarget = innerDoc.body || innerDoc.documentElement;
            if (obsTarget) {
                observer.observe(obsTarget, { childList: true, subtree: true });
            }
            console.log('[Overlay] Chzzk Iframe Observer Attached');

            // Re-attach on load (for 2nd video navigation)
            iframe.addEventListener('load', () => {
                console.log('[Overlay] Chzzk iframe loaded, re-attaching observer...');
                lastResolutionType = null; // Reset state
                window._bcuChzzkObserved = false;
                setupChzzkObserver();
            }, { once: true });
            
        } catch(e) {
            window._bcuChzzkObserved = false;
        }
    }

    function init() {
         setupChzzkObserver();
         const mainObserver = new MutationObserver(() => {
            setupChzzkObserver();
         });
         if (document.body) {
             mainObserver.observe(document.body, { childList: true, subtree: true });
         } else {
             console.error("[Overlay] document.body is null during init");
         }
    }

    if (document.readyState === 'loading') {
        window.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Periodic fallback (just in case) - 1000ms
    setInterval(() => {
        const iframe = document.getElementById('chzzk_player');
        if(iframe) {
             try {
                const v = iframe.contentWindow.document.querySelector('video');
                if(v) reportResolution(v);
             } catch(e){}
        }
    }, 1000);
    // 6. Force Iframe Permissions (Encrypted Media for YouTube)
    (function() {
        // console.log('[Overlay] Permission Fixer Loaded');
        function fixPermissions() {
            const iframes = document.getElementsByTagName('iframe');
            for (let i = 0; i < iframes.length; i++) {
                const iframe = iframes[i];
                if (iframe.src && (iframe.src.includes('youtube.com') || iframe.src.includes('youtu.be') || iframe.id === 'chzzk_player')) {
                    const currentAllow = iframe.getAttribute('allow') || "";
                    const required = "autoplay; encrypted-media; clipboard-write; picture-in-picture";
                    
                    
                    // Force PC Version (Rewrite m.youtube.com to www.youtube.com)
                    if (iframe.src && iframe.src.includes('//m.youtube.com')) {
                        console.log(`[Overlay] Detected Mobile YouTube URL. Forcing PC version...`);
                        iframe.src = iframe.src.replace('//m.youtube.com', '//www.youtube.com');
                        return; 
                    }

                    if (!currentAllow.includes('encrypted-media')) {
                        console.log(`[Overlay] Fixing permissions for ${iframe.src}`);
                        // 기존 allow 값에 빠진 권한 추가
                        let newAllow = currentAllow;
                        if (newAllow) newAllow += "; ";
                        newAllow += required;
                        
                        iframe.setAttribute('allow', newAllow);
                        
                        // 권한 적용을 위해 src 리로드 (필요한 경우)
                        // 주의: 리로드는 재생을 초기화하므로 신중해야 함.
                        // 보통은 초기에 적용되면 문제 없음.
                        // iframe.src = iframe.src; 
                    }
                }
            }
        }

        // 초기 실행
        fixPermissions();

        // 동적 추가 감지
        const observer = new MutationObserver((mutations) => {
             mutations.forEach((m) => {
                 m.addedNodes.forEach((n) => {
                     if (n.tagName === 'IFRAME') {
                         fixPermissions();
                     } else if (n.getElementsByTagName) {
                         if (n.getElementsByTagName('iframe').length > 0) fixPermissions();
                     }
                 });
             });
        });
        const obsTarget = document.body || document.documentElement;
        if (obsTarget) {
            observer.observe(obsTarget, { childList: true, subtree: true });
        }
        
        // Polling fallback
        setInterval(fixPermissions, 2000);
    })();
})();

"""

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

        self.setFixedSize(1280, 1254)

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
        if self.parent() and self.parent().main_window:
            if self.parent().main_window.remote_tab.toggle_reserve_pause_video_button.text() == "정지 예약 해제":
                QTimer.singleShot(1500, lambda: self.parent().main_window.remote_tab.control_pause_button.click())
                QTimer.singleShot(1500, lambda: self.parent().main_window.remote_tab.toggle_reserve_pause_video_button.click())
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

    def refresh_page(self):
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

    def closeEvent(self, event: QCloseEvent):
        self.closed.emit()
        self.browser.stop()
        self.browser.deleteLater()
        event.accept()

    def inject_script(self):
        script = QWebEngineScript()
        script.setSourceCode(INJECT_JS)
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
        
        print(f"[Overlay] Simulating Skip (Blind Click) - Mode: {'Portrait' if is_port else 'Landscape'}, Align: {align}")
        for x, y in coords_to_click:
            self.simulate_click(x, y)

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