import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QFileDialog, 
    QProgressBar, QLabel, QTableWidget, QTableWidgetItem, QFormLayout, 
    QMessageBox, QHeaderView, QSpinBox, QDialog, QAbstractItemView, QDateEdit, QMainWindow,
    QSizePolicy, QGroupBox, QRadioButton, QComboBox, QButtonGroup, QCompleter
)
import json
from PyQt6.QtWebEngineWidgets import QWebEngineView
from app.constants import USERPATH
import sys
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QDate, QSize, QUrl
from PyQt6.QtGui import QIcon
from app.resources import resource_path

def getIDNick(chat):
    """채팅 로그에서 ID와 닉네임을 추출합니다."""
    id_val, nick_val = "", ""
    try:
        if ")> " in chat:
            id_start = chat.index(" (") + 2
            id_end = chat.index(")> ")
            id_val = chat[id_start:id_end]
            nick_start = chat.index("] <") + 3
            nick_end = chat.index(" (")
            nick_val = chat[nick_start:nick_end]
        else:
            id_start = chat.index("] <") + 3
            id_end = chat.index("> ")
            id_val = chat[id_start:id_end]
            nick_val = id_val
    except ValueError:
        return "", ""
    return id_val, nick_val

class LogAnalyzerWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, log_dir, start_date, end_date):
        super().__init__()
        self.log_dir = log_dir
        self.start_date = start_date
        self.end_date = end_date
        self.is_running = True

    def run(self):
        try:
            result = {}
            elapsecondS = 0
            
            all_files = os.listdir(self.log_dir)
            
            filtered_files = []
            for f_name in all_files:
                if f_name.endswith(".log") and "custom" not in f_name and "-" in f_name:
                    try:
                        date_str = f_name[:10]
                        file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        if self.start_date <= file_date <= self.end_date:
                            filtered_files.append(f_name)
                    except (ValueError, IndexError):
                        continue
            
            filtered_files.sort(reverse=True)
            
            total_files = len(filtered_files)
            if total_files == 0:
                self.error.emit("선택한 기간에 해당하는 분석할 .log 파일이 없습니다.")
                return

            for i, file_name in enumerate(filtered_files):
                if not self.is_running:
                    break
                
                self.progress.emit(i + 1, total_files, file_name)
                
                file_path = os.path.join(self.log_dir, file_name)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                prev_chat_date = None

                for line in lines:
                    try:
                        chat_date_str = line.split("]")[0].split("[")[1]
                        chat_date = datetime.strptime(chat_date_str, '%Y-%m-%d %H:%M:%S')

                        # [NEW] 30분(1800초) 이상 공백 시 세션 분리 (방송 꺼짐 처리)
                        if prev_chat_date:
                            diff = (chat_date - prev_chat_date).total_seconds()
                            if 0 <= diff <= 1800:
                                elapsecondS += diff
                        
                        prev_chat_date = chat_date
                        
                        if "<" not in line: continue
                        id_val, nick = getIDNick(line)
                        if not id_val: continue

                        if f"{id_val})> " in line:
                            msg = line.split(f"{id_val})> ")[1].strip()
                        elif f"{id_val}> " in line:
                            msg = line.split(f"{id_val}> ")[1].strip()
                        else:
                            continue
                        msgg = msg.replace(" ", "")
                        if "🟥⭐" in msgg or "Cheer" in msgg: continue
                        if msgg:
                            result[msgg] = result.get(msgg, 0) + 1
                    except (IndexError, ValueError):
                        continue
                


            if not self.is_running:
                return

            sorted_result = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
            totchat = sum(sorted_result.values())
            
            final_data = {
                "total_seconds": elapsecondS,
                "total_chats": totchat,
                "sorted_result": sorted_result
            }
            self.finished.emit(final_data)
        except Exception as e:
            self.error.emit(f"오류가 발생했습니다: {e}")

    def stop(self):
        self.is_running = False

class CharCountWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, log_dir, start_date, end_date, target, is_emoticon=False):
        super().__init__()
        self.log_dir = log_dir
        self.start_date = start_date
        self.end_date = end_date
        self.target = target
        self.is_emoticon = is_emoticon
        self.is_running = True

    def run(self):
        try:
            total_count = 0
            total_chats = 0
            total_chars = 0
            elapsecondS = 0
            
            all_files = os.listdir(self.log_dir)
            filtered_files = []
            for f_name in all_files:
                if f_name.endswith(".log") and "custom" not in f_name and "-" in f_name:
                    try:
                        date_str = f_name[:10]
                        file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        if self.start_date <= file_date <= self.end_date:
                            filtered_files.append(f_name)
                    except (ValueError, IndexError):
                        continue
            
            filtered_files.sort(reverse=True)
            total_files = len(filtered_files)
            
            if total_files == 0:
                self.error.emit("선택한 기간에 해당하는 분석할 .log 파일이 없습니다.")
                return

            for i, file_name in enumerate(filtered_files):
                if not self.is_running: break
                
                self.progress.emit(i + 1, total_files, file_name)
                
                file_path = os.path.join(self.log_dir, file_name)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                prev_chat_date = None

                for line in lines:
                    try:
                        chat_date_str = line.split("]")[0].split("[")[1]
                        chat_date = datetime.strptime(chat_date_str, '%Y-%m-%d %H:%M:%S')

                        # [NEW] 30분(1800초) 이상 공백 시 세션 분리
                        if prev_chat_date:
                            diff = (chat_date - prev_chat_date).total_seconds()
                            if 0 <= diff <= 1800:
                                elapsecondS += diff
                        
                        prev_chat_date = chat_date
                        
                        if "<" not in line: continue
                        id_val, nick = getIDNick(line)
                        if not id_val: continue

                        if f"{id_val})> " in line:
                            msg = line.split(f"{id_val})> ")[1].strip()
                        elif f"{id_val}> " in line:
                            msg = line.split(f"{id_val}> ")[1].strip()
                        else:
                            continue
                        
                        if "🟥⭐" in msg or "Cheer" in msg: continue # 제외 로직 유지

                        total_chats += 1
                        
                        # 띄어쓰기 제외한 전체 글자 수 집계
                        msg_clean_for_total = msg.replace(" ", "")
                        total_chars += len(msg_clean_for_total)

                        # 이모티콘 모드
                        if self.is_emoticon:
                            # target이 '{:kane1Soak:}' 형태면 그대로 사용, 아니면 '{: :}'로 감싸기
                            search_term = self.target
                            if not (search_term.startswith("{:") and search_term.endswith(":}")):
                                search_term = f"{{:{self.target}:}}"
                            total_count += msg.count(search_term)
                        else:
                            # 텍스트 모드 (띄어쓰기 무시)
                            msg_clean = msg.replace(" ", "")
                            target_clean = self.target.replace(" ", "")
                            
                            if target_clean == '헉':
                                total_count += msg_clean.count('헉')
                                total_count += msg.count('{:lck_28:}') # 이모티콘은 원본 msg에서 찾음
                            elif target_clean == '뭉':
                                # '뭉', '뭉탱', '뭉탱이' -> '뭉' 글자 세면 포함됨
                                total_count += msg_clean.count('뭉')
                            elif target_clean == '뭉탱':
                                total_count += msg_clean.count('뭉탱')
                            elif target_clean == '뭉탱이':
                                total_count += msg_clean.count('뭉탱이')
                            else:
                                total_count += msg_clean.count(target_clean)

                    except (IndexError, ValueError):
                        continue
                


            if not self.is_running: return

            final_data = {
                "target": self.target,
                "is_emoticon": self.is_emoticon,
                "count": total_count,
                "total_chats": total_chats,
                "total_chars": total_chars,
                "total_seconds": elapsecondS
            }
            self.finished.emit(final_data)
        except Exception as e:
            self.error.emit(f"오류가 발생했습니다: {e}")

    def stop(self):
        self.is_running = False

class ResultsDialog(QDialog):
    def __init__(self, result_data, rank_limit, parent=None):
        super().__init__(parent)
        from app.resources import resource_path

        self.setWindowTitle("분석 결과")
        self.resize(1000, 800)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

        # Centering
        if parent:
             geo = parent.geometry()
             center = geo.center()
             self.move(center - self.rect().center())

        
        # 이모티콘 데이터 로드
        self.emoticons = {}
        try:
            json_path = os.path.join(USERPATH, "BCU", "chat_emoticons.json")
            with open(json_path, 'r', encoding='utf-8') as f:
                self.emoticons = json.load(f)
        except Exception as e:
            print(f"이모티콘 로드 실패: {e}")

        layout = QVBoxLayout(self)

        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(10, 10, 10, 5) # 여백 줄임
        summary_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed) # 높이 고정
        layout.addWidget(summary_widget)

        line1_layout = QHBoxLayout()
        self.total_chats_label = QLabel()
        self.total_time_label = QLabel()
        line1_layout.addWidget(self.total_chats_label)
        line1_layout.addWidget(self.total_time_label)
        summary_layout.addLayout(line1_layout)

        line2_layout = QHBoxLayout()
        self.chats_per_sec_label = QLabel()
        self.chats_per_min_label = QLabel()
        self.chats_per_hour_label = QLabel()
        line2_layout.addWidget(self.chats_per_sec_label)
        line2_layout.addWidget(self.chats_per_min_label)
        line2_layout.addWidget(self.chats_per_hour_label)
        summary_layout.addLayout(line2_layout)

        self.scroll_button = QPushButton("자동 스크롤 시작")
        self.scroll_button.clicked.connect(self.toggle_auto_scroll)
        layout.addWidget(self.scroll_button)

        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.web_view.hide()
        self.web_view.loadFinished.connect(self.on_load_finished)
        layout.addWidget(self.web_view)

        self.loading_label = QLabel("로딩 중...", self)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
        layout.addWidget(self.loading_label)

        self.scroll_timer = QTimer(self)
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.scroll_step)
        self.current_scroll_rank = 0
        self.max_rows = 0

        self.populate_data(result_data, rank_limit)

    def populate_data(self, result_data, rank_limit):
        total_seconds = result_data["total_seconds"]
        total_chats = result_data["total_chats"]

        self.total_chats_label.setText(f"<b>총 채팅 수:</b> {total_chats:,}")
        
        td = timedelta(seconds=total_seconds)
        days, remainder = divmod(int(td.total_seconds()), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        self.total_time_label.setText(f"<b>총 방송 시간:</b> {days}일 {hours}시간 {minutes}분 {seconds}초")

        if total_seconds > 0:
            self.chats_per_sec_label.setText(f"<b>초당:</b> {total_chats / total_seconds:.3f}개")
            self.chats_per_min_label.setText(f"<b>분당:</b> {total_chats / total_seconds * 60:.3f}개")
            self.chats_per_hour_label.setText(f"<b>시간당:</b> {total_chats / total_seconds * 3600:.3f}개")
        else:
            self.chats_per_sec_label.setText("<b>초당:</b> 0.000개")
            self.chats_per_min_label.setText("<b>분당:</b> 0.000개")
            self.chats_per_hour_label.setText("<b>시간당:</b> 0.000개")

        sorted_result = result_data["sorted_result"]
        result_items = list(sorted_result.items())[:rank_limit]
        self.max_rows = len(result_items)

        # HTML 생성
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: 'Pretendard JP', sans-serif; margin: 0; padding: 10px; }
                table { width: 100%; border-collapse: collapse; }
                th { background-color: #f2f2f2; padding: 10px; position: sticky; top: 0; z-index: 10; border-bottom: 2px solid #ddd; text-align: left;}
                td { padding: 8px; border-bottom: 1px solid #ddd; }
                tr { content-visibility: auto; contain-intrinsic-size: 30px; scroll-margin-top: 40px; }
                tr.highlight { background-color: #fff9c4; font-weight: bold; }
                img.emoticon { height: 24px; vertical-align: middle; }
                .rank-col { width: 60px; text-align: center; }
                .count-col { width: 100px; text-align: right; }
                .percent-col { width: 100px; text-align: right; }
            </style>
            <script>
                function highlightRow(index) {
                    // 모든 하이라이트 제거
                    var highlighted = document.querySelectorAll('tr.highlight');
                    highlighted.forEach(function(row) {
                        row.classList.remove('highlight');
                    });
                    
                    var row = document.getElementById('row-' + index);
                    if (row) {
                        row.classList.add('highlight');
                        row.scrollIntoView({behavior: "smooth", block: "start"});
                    }
                }
                
                function scrollToBottom() {
                    window.scrollTo(0, document.body.scrollHeight);
                }
            </script>
        </head>
        <body>
            <table>
                <thead>
                    <tr>
                        <th class="rank-col">순위</th>
                        <th>채팅 내용</th>
                        <th class="count-col">횟수</th>
                        <th class="percent-col">비율 (%)</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # 이모티콘 치환 및 행 생성
        for i, (key, value) in enumerate(result_items):
            percentage = (value / total_chats) * 100 if total_chats > 0 else 0
            
            # 이모티콘 치환
            display_text = key
            for code, url in self.emoticons.items():
                if code in display_text:
                    display_text = display_text.replace(code, f'<img src="{url}" class="emoticon">')
            
            html_content += f"""
                <tr id="row-{i}">
                    <td class="rank-col">{i+1}</td>
                    <td>{display_text}</td>
                    <td class="count-col">{value:,}</td>
                    <td class="percent-col">{percentage:.3f}%</td>
                </tr>
            """
            
        html_content += """
                </tbody>
            </table>
        </body>
        </html>
        """
        
        self.web_view.setHtml(html_content)
        
    def on_load_finished(self, ok):
        if ok:
             QTimer.singleShot(100, lambda: self.web_view.page().runJavaScript("scrollToBottom()"))
             QTimer.singleShot(200, self.show_webview)

    def show_webview(self):
        self.loading_label.hide()
        self.web_view.show()

    def toggle_auto_scroll(self):
        if self.scroll_timer.isActive():
            self.scroll_timer.stop()
            self.scroll_button.setText("자동 스크롤 시작")
        else:
            if self.max_rows < 1: return
            
            self.current_scroll_rank = self.max_rows
            self.scroll_button.setText("정지")
            self.highlight_and_schedule_next()

    def highlight_and_schedule_next(self):
        row_index = self.current_scroll_rank - 1
        
        # JS 호출하여 하이라이트 및 스크롤
        self.web_view.page().runJavaScript(f"highlightRow({row_index})")

        interval = 100
        if 50 < self.current_scroll_rank <= 100:
            interval = 300
        elif 20 < self.current_scroll_rank <= 50:
            interval = 500
        elif 10 < self.current_scroll_rank <= 20:
            interval = 1000
        elif 5 < self.current_scroll_rank <= 10:
            interval = 2000           
        elif 1 <= self.current_scroll_rank <= 5:
            interval = 3000

        self.current_scroll_rank -= 1
        
        if self.current_scroll_rank >= 0:
            self.scroll_timer.start(interval)
        else:
            self.scroll_button.setText("자동 스크롤 시작")

    def scroll_step(self):
        if self.current_scroll_rank < 0:
            self.scroll_timer.stop()
            self.scroll_button.setText("자동 스크롤 시작")
            return
        self.highlight_and_schedule_next()
    
    def closeEvent(self, event):
        self.scroll_timer.stop()
        super().closeEvent(event)



class UserCountWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, log_dir, start_date, end_date):
        super().__init__()
        self.log_dir = log_dir
        self.start_date = start_date
        self.end_date = end_date
        self.is_running = True

    def run(self):
        try:
            user_counts = {} # {id: count}
            user_nicks = {}  # {id: latest_nick}
            total_chats = 0
            
            all_files = os.listdir(self.log_dir)
            filtered_files = []
            for f_name in all_files:
                if f_name.endswith(".log") and "custom" not in f_name and "-" in f_name:
                    try:
                        date_str = f_name[:10]
                        file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        if self.start_date <= file_date <= self.end_date:
                            filtered_files.append(f_name)
                    except (ValueError, IndexError):
                        continue
            
            filtered_files.sort() # 오름차순 (옛날 -> 최신)
            total_files = len(filtered_files)
            
            if total_files == 0:
                self.error.emit("선택한 기간에 해당하는 분석할 .log 파일이 없습니다.")
                return

            for i, file_name in enumerate(filtered_files):
                if not self.is_running: break
                self.progress.emit(i + 1, total_files, file_name)
                
                file_path = os.path.join(self.log_dir, file_name)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if "<" not in line: continue
                        id_val, nick = getIDNick(line)
                        if not id_val: continue
                        
                        if f"{id_val})> " in line:
                            msg = line.split(f"{id_val})> ")[1].strip()
                        elif f"{id_val}> " in line:
                            msg = line.split(f"{id_val}> ")[1].strip()
                        else:
                            continue
                        
                        if "🟥⭐" in msg or "Cheer" in msg: continue # 제외
                        
                        total_chats += 1
                        user_counts[id_val] = user_counts.get(id_val, 0) + 1
                        user_nicks[id_val] = nick # 계속 덮어씀 -> 마지막이 최신

            if not self.is_running: return

            # 결과 정렬 (채팅 수 내림차순)
            sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
            
            result_list = []
            for uid, count in sorted_users:
                nick = user_nicks.get(uid, "Unknown")
                result_list.append((uid, count, nick))

            final_data = {
                "total_chats": total_chats,
                "total_users": len(sorted_users),
                "sorted_result": result_list
            }
            self.finished.emit(final_data)

        except Exception as e:
            self.error.emit(f"오류가 발생했습니다: {e}")

    def stop(self):
        self.is_running = False

class ChatCounterWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("채팅 통계 분석")
        self.resize(600, 400)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))
        
        self.internal_mode = False
        if parent and hasattr(parent, 'kanetv8'):
             self.internal_mode = parent.kanetv8.isChecked()
        
        self.force_close = False
        
        # Data
        self.log_dir = ""
        self.analysis_result = None # General
        self.char_count_result = None # Specific
        self.user_count_result = None # User
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        date_group = QGroupBox("기간 설정")
        date_layout = QVBoxLayout()
        
        year_layout = QHBoxLayout()
        self.year_combo = QComboBox()
        self.year_combo.addItem("직접 선택")
        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        year_layout.addWidget(QLabel("년도 선택:"))
        year_layout.addWidget(self.year_combo)
        year_layout.addStretch()
        
        range_layout = QHBoxLayout()
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-7))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        
        range_layout.addWidget(QLabel("시작:"))
        range_layout.addWidget(self.start_date_edit)
        range_layout.addWidget(QLabel("종료:"))
        range_layout.addWidget(self.end_date_edit)
        range_layout.addStretch()
        
        date_layout.addLayout(year_layout)
        date_layout.addLayout(range_layout)
        date_group.setLayout(date_layout)
        self.main_layout.addWidget(date_group)

        mode_group = QGroupBox("분석 모드 선택")
        mode_layout = QVBoxLayout()
        
        self.rb_frequency = QRadioButton("가장 많은 채팅은?")
        self.rb_frequency.setChecked(True)
        self.rb_frequency.toggled.connect(self.toggle_mode_ui)
        mode_layout.addWidget(self.rb_frequency)
        
        self.group_frequency = QWidget()
        freq_layout = QHBoxLayout(self.group_frequency)
        freq_layout.setContentsMargins(20, 0, 0, 0)
        freq_layout.addWidget(QLabel("상위 표시 개수:"))
        self.rank_limit_spinbox = QSpinBox()
        self.rank_limit_spinbox.setRange(1, 10000)
        self.rank_limit_spinbox.setValue(1000)
        freq_layout.addWidget(self.rank_limit_spinbox)
        freq_layout.addStretch()
        mode_layout.addWidget(self.group_frequency)

        self.rb_specific = QRadioButton("채팅에서 특정 단어/이모티콘이 나온 횟수는?")
        self.rb_specific.toggled.connect(self.toggle_mode_ui)
        mode_layout.addWidget(self.rb_specific)
        
        self.group_specific = QWidget()
        spec_layout = QVBoxLayout(self.group_specific)
        spec_layout.setContentsMargins(20, 0, 0, 0)
        
        type_layout = QHBoxLayout()
        self.spec_radio_text = QRadioButton("단어/문장")
        self.spec_radio_emote = QRadioButton("이모티콘")
        self.spec_radio_text.setChecked(True)
        self.spec_radio_bg = QButtonGroup(self)
        self.spec_radio_bg.addButton(self.spec_radio_text)
        self.spec_radio_bg.addButton(self.spec_radio_emote)
        self.spec_radio_text.toggled.connect(self.toggle_specific_input)
        type_layout.addWidget(self.spec_radio_text)
        type_layout.addWidget(self.spec_radio_emote)
        type_layout.addStretch()
        spec_layout.addLayout(type_layout)
        
        input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        if self.internal_mode:
            self.search_input.setPlaceholderText("검색할 단어 (예: 코, 헉, 뭉, 게이, 자숙)")
        else:
             self.search_input.setPlaceholderText("검색할 단어를 입력하세요.")
        self.selected_emote_btn = QPushButton("이모티콘 선택")
        self.selected_emote_btn.clicked.connect(self.open_emoticon_selector)
        self.selected_emote_label = QLabel("")
        
        input_layout.addWidget(self.search_input)
        input_layout.addWidget(self.selected_emote_btn)
        input_layout.addWidget(self.selected_emote_label)
        spec_layout.addLayout(input_layout)
        
        mode_layout.addWidget(self.group_specific)

        self.rb_user = QRadioButton("채팅을 가장 많이 친 사람은?")
        self.rb_user.toggled.connect(self.toggle_mode_ui)
        mode_layout.addWidget(self.rb_user)
        
        self.group_user = QWidget()
        user_layout = QVBoxLayout(self.group_user)
        user_layout.setContentsMargins(20, 0, 0, 0)
        
        mask_layout = QHBoxLayout()
        mask_layout.addWidget(QLabel("닉네임:"))
        self.mask_full = QRadioButton("가리기(***)")
        self.mask_half = QRadioButton("반만(홍**)")
        self.mask_none = QRadioButton("표시(홍길동)")
        self.mask_full.setChecked(True)
        self.mask_bg = QButtonGroup(self)
        self.mask_bg.addButton(self.mask_full)
        self.mask_bg.addButton(self.mask_half)
        self.mask_bg.addButton(self.mask_none)
        mask_layout.addWidget(self.mask_full)
        mask_layout.addWidget(self.mask_half)
        mask_layout.addWidget(self.mask_none)
        user_layout.addLayout(mask_layout)
        
        urank_layout = QHBoxLayout()
        urank_layout.addWidget(QLabel("표시 인원:"))
        self.user_rank_limit = QSpinBox()
        self.user_rank_limit.setRange(1, 10000)
        self.user_rank_limit.setValue(1000)
        urank_layout.addWidget(self.user_rank_limit)
        urank_layout.addStretch()
        user_layout.addLayout(urank_layout)
        
        mode_layout.addWidget(self.group_user)
        
        mode_group.setLayout(mode_layout)
        self.main_layout.addWidget(mode_group)
        
        self.main_layout.addStretch()

        bottom_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("대기 중...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("분석 시작")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.start_btn.clicked.connect(self.on_start_clicked)
        
        self.result_btn = QPushButton("결과 표시")
        self.result_btn.setMinimumHeight(40)
        self.result_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.result_btn.setEnabled(False)
        self.result_btn.clicked.connect(self.on_result_clicked)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.result_btn)
        
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.progress_label)
        bottom_layout.addLayout(btn_layout)
        
        self.main_layout.addLayout(bottom_layout)

        self.selected_emote_data = None
        self.load_last_directory()
        self.toggle_mode_ui()
        self.toggle_specific_input()

    def load_years(self):
        """Scan log_dir for files like Chat_YYYY... and populate year_combo."""
        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        
        if not self.log_dir or not os.path.isdir(self.log_dir):
            self.year_combo.addItem("직접 선택")
            self.year_combo.blockSignals(False)
            return

        years = set()
        try:
            for f in os.listdir(self.log_dir):
                if f.endswith(".log") and "custom" not in f and "-" in f:
                    try:
                        parts = f.replace("Chat_", "").split("-")
                        if len(parts) >= 1:
                            y = parts[0]
                            if y.isdigit() and len(y) == 4:
                                years.add(y)
                    except:
                        continue
        except Exception as e:
            print(f"Error scanning years: {e}")

        sorted_years = sorted(list(years), reverse=True)
        self.year_combo.addItems([y + "년" for y in sorted_years])
        self.year_combo.addItem("직접 선택")
        
        current_year = str(datetime.now().year)
        found_idx = -1
        for i, y in enumerate(sorted_years):
            if y == current_year:
                found_idx = i
                break
        
        if found_idx != -1:
            self.year_combo.setCurrentIndex(found_idx)
        else:
            self.year_combo.setCurrentIndex(0)

        self.year_combo.blockSignals(False)
        self.on_year_changed()

    def on_year_changed(self):
        text = self.year_combo.currentText()
        if "년" not in text: return
        
        year = text.replace("년", "")
        if year.isdigit():
            start = QDate(int(year), 1, 1)
            end = QDate(int(year), 12, 31)
            self.start_date_edit.setDate(start)
            self.end_date_edit.setDate(end)

    def toggle_mode_ui(self):
        self.group_frequency.hide()
        self.group_specific.hide()
        self.group_user.hide()
        
        is_result_ready = False
        
        if self.rb_frequency.isChecked():
            self.group_frequency.show()
            if self.analysis_result: is_result_ready = True
            
        elif self.rb_specific.isChecked():
            self.group_specific.show()
            if self.char_count_result: is_result_ready = True
            
        elif self.rb_user.isChecked():
            self.group_user.show()
            if self.user_count_result: is_result_ready = True
            
        self.result_btn.setEnabled(is_result_ready)

    def toggle_specific_input(self):
        is_emote = self.spec_radio_emote.isChecked()
        self.search_input.setVisible(not is_emote)
        self.selected_emote_btn.setVisible(is_emote)
        self.selected_emote_label.setVisible(is_emote)
        self.selected_emote_btn.setEnabled(is_emote) 

    def on_start_clicked(self):
        if self.rb_frequency.isChecked():
            self.start_analysis()
        elif self.rb_specific.isChecked():
            self.start_char_count()
        elif self.rb_user.isChecked():
            self.start_user_analysis()

    def on_result_clicked(self):
        if self.rb_frequency.isChecked():
            self.open_results_dialog()
            
        elif self.rb_specific.isChecked():
            if not self.char_count_result: return
            self.open_char_results_dialog()
                
        elif self.rb_user.isChecked():
            self.open_user_results_dialog()
    
    def open_char_results_dialog(self):
        if not self.char_count_result: return
        res = self.char_count_result
        
        target_url = ""
        target = res["target"]
        if res.get("is_emoticon"):
             if self.selected_emote_data and self.selected_emote_data[0] == target:
                 target_url = self.selected_emote_data[1]
        elif target == '헉':
            target_url = "https://ssl.pstatic.net/static/nng/glive/icon/a_37.png"
        elif target in ['뭉', '뭉탱', '뭉탱이']:
             target_url = "https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Kane1mung_1740411891638.png"

        dialog = CharCountResultDialog(res, target_url, self.internal_mode, self)
        dialog.show()
        
    def closeEvent(self, event):
        if self.force_close:
            try:
                pass
            except: pass
            event.accept()
        else:
            super().closeEvent(event)

    def open_emoticon_selector(self):
        dialog = EmoticonSelectorDialog(self.internal_mode, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_emoticon:
             name, url = dialog.selected_emoticon
             self.selected_emote_data = (name, url)
             self.selected_emote_label.setText(f"선택됨: {name}")

    def start_char_count(self):
        if not self.log_dir or not os.path.isdir(self.log_dir):
            QMessageBox.warning(self, "경고", "로그 폴더가 설정되지 않았습니다.")
            return

        target = ""
        is_emoticon = self.spec_radio_emote.isChecked()

        if is_emoticon:
            if not self.selected_emote_data:
                QMessageBox.warning(self, "경고", "이모티콘을 선택해주세요.")
                return
            target = self.selected_emote_data[0]
        else:
            target = self.search_input.text().strip()
            if not target:
                QMessageBox.warning(self, "경고", "검색할 단어를 입력해주세요.")
                return
        
        self.start_btn.setEnabled(False)
        self.result_btn.setEnabled(False)
        self.reset_ui(specific=True)
        self.char_count_result = None

        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()

        self.char_worker = CharCountWorker(self.log_dir, start_date, end_date, target, is_emoticon)
        self.char_worker.progress.connect(self.update_progress)
        self.char_worker.finished.connect(self.on_char_count_finished)
        self.char_worker.error.connect(self.on_char_count_error)
        self.char_worker.start()

    def on_char_count_finished(self, result_data):
        self.start_btn.setEnabled(True)
        self.result_btn.setEnabled(True)
        self.char_count_result = result_data
        
        self.progress_label.setText("분석 완료! '결과 표시' 버튼으로 결과를 확인하세요.")
        QMessageBox.information(self, "완료", "분석 완료! '결과 표시' 버튼으로 결과를 확인하세요.")

    def on_char_count_error(self, error_message):
        self.start_btn.setEnabled(True)
        self.progress_label.setText("오류 발생")
        QMessageBox.critical(self, "오류", error_message)

    def load_last_directory(self):
        parent = self.parent()
        path = ""
        if parent:
            if hasattr(parent, 'file_path_box_chat_log'):
                 path = parent.file_path_box_chat_log.text()
        
        if path and os.path.isdir(path):
            self.log_dir = path
            self.load_years()

    def start_analysis(self):
        if not self.log_dir or not os.path.isdir(self.log_dir):
            QMessageBox.warning(self, "경고", "로그 폴더가 설정되지 않았습니다.")
            return

        self.start_btn.setEnabled(False)
        self.result_btn.setEnabled(False)
        self.reset_ui()
        self.analysis_result = None

        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()

        self.worker = LogAnalyzerWorker(self.log_dir, start_date, end_date)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.error.connect(self.analysis_error)
        self.worker.start()

    def update_progress(self, current, total, filename):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"처리 중... ({current}/{total}): {filename}")

    def analysis_finished(self, result_data):
        self.analysis_result = result_data
        self.progress_label.setText("분석 완료! '결과 표시' 버튼으로 결과를 확인하세요.")
        self.start_btn.setEnabled(True)
        self.result_btn.setEnabled(True)
        self.save_results_to_file(result_data["sorted_result"], result_data["total_chats"])
        QMessageBox.information(self, "완료", "분석 완료! '결과 표시' 버튼으로 결과를 확인하세요.")

    def open_results_dialog(self):
        if not self.analysis_result:
            QMessageBox.information(self, "알림", "먼저 로그 분석을 시작해주세요.")
            return
        
        rank_limit = self.rank_limit_spinbox.value()
        dialog = ResultsDialog(self.analysis_result, rank_limit, self)
        dialog.show()

    def save_results_to_file(self, sorted_result, total_chats):
        output_lines = []
        for rank, (key, value) in enumerate(sorted_result.items(), start=1):
            percentage = (value / total_chats) * 100 if total_chats > 0 else 0
            output_lines.append(f"{rank}위: {key} ({value}개, {percentage:.3f}%)")

        try:
            with open('sorted_result.txt', 'w', encoding='utf-8') as file:
                file.write('\n'.join(output_lines))
        except Exception as e:
            QMessageBox.critical(self, "파일 저장 오류", f"결과를 파일에 저장하는 중 오류가 발생했습니다: {e}")

    def analysis_error(self, error_message):
        self.progress_label.setText("오류 발생")
        self.start_btn.setEnabled(True)
        QMessageBox.critical(self, "오류", error_message)

    def reset_ui(self, specific=False):
        self.progress_bar.setValue(0)
        self.progress_label.setText("대기 중...")

    def start_user_analysis(self):
        if not self.log_dir or not os.path.isdir(self.log_dir):
            QMessageBox.warning(self, "경고", "로그 폴더가 설정되지 않았습니다.")
            return

        self.start_btn.setEnabled(False)
        self.result_btn.setEnabled(False)
        self.reset_ui(specific=True)
        self.user_count_result = None

        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()

        self.user_worker = UserCountWorker(self.log_dir, start_date, end_date)
        self.user_worker.progress.connect(self.update_progress)
        self.user_worker.finished.connect(self.on_user_analysis_finished)
        self.user_worker.error.connect(self.on_user_analysis_error)
        self.user_worker.start()

    def on_user_analysis_finished(self, result_data):
        self.start_btn.setEnabled(True)
        self.result_btn.setEnabled(True)
        self.user_count_result = result_data 
        self.progress_label.setText("분석 완료! '결과 표시' 버튼으로 결과를 확인하세요.")
        QMessageBox.information(self, "완료", "분석 완료! '결과 표시' 버튼으로 결과를 확인하세요.")

    def open_user_results_dialog(self):
        if not self.user_count_result:
            return

        mask_type = "full"
        if self.mask_half.isChecked(): mask_type = "half"
        elif self.mask_none.isChecked(): mask_type = "none"
        
        limit = self.user_rank_limit.value()

        self.user_stats_dialog = UserStatsResultDialog(self.user_count_result, mask_type, limit, self)
        self.user_stats_dialog.show()

    def on_user_analysis_error(self, error_message):
        self.start_btn.setEnabled(True)
        self.progress_label.setText("오류 발생")
        QMessageBox.critical(self, "오류", error_message)

class CharCountResultDialog(QDialog):
    def __init__(self, result_data, target_url, internal_mode=False, parent=None):
        super().__init__(parent)
        self.internal_mode = internal_mode
        self.setWindowTitle("분석 결과")
        self.resize(960, 540)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))
        
        if parent:
             geo = parent.geometry()
             center = geo.center()
             self.move(center - self.rect().center())
        
        self.web_view = QWebEngineView(self)
        self.web_view.setZoomFactor(0.75)
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Enable autoplay with sound
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)
        
        self.populate_html(result_data, target_url)

    def closeEvent(self, event):
        self.web_view.setUrl(QUrl("about:blank"))
        super().closeEvent(event)

    def populate_html(self, data, target_url):
        import json
        target = data["target"]
        count = data["count"]
        total_chats = data["total_chats"]
        total_chars = data.get("total_chars", 0)
        
        match_len = 0
        if data["is_emoticon"]:
             search_term = target
             if not (search_term.startswith("{:") and search_term.endswith(":}")):
                search_term = f"{{:{target}:}}"
             match_len = len(search_term)
        else:
             match_len = len(target.replace(" ", ""))

        percent = (count * match_len / total_chars * 100) if total_chars > 0 else 0
        
        extra_html = ""
        
        particle_type = "default" # text, image, emoji
        particle_data = "[]" 
        bg_color = "#f9f9f9"
        text_particle_color = "#333333"
        
        title_html = f"총 '{target}' 개수"

        def is_match(keywords):
            if isinstance(keywords, str): keywords = [keywords]
            target_clean = target.replace(" ", "")
            for k in keywords:
                if k.replace(" ", "") == target_clean:
                    return True
            return False
        
        # YouTube Background Logic
        youtube_vid = ""
        
        # (Keywords, Video ID)
        YOUTUBE_MAPPINGS = [
            (['죄송합니다', 'ㅈㅅㅎㄴㄷ', '자숙', '정리좀하고', '지금부터는', '318', '321'], "GLwDtB-1Ya8"),
            ('코', "Y3Ml7iqP6bw"),
            ('헉', "dGF08Euma1A"),
            (['뭉', '뭉탱', '뭉탱이', 'ㅁㅌㅇ', '뭉탱이월드', 'ㅁㅌㅇㅇㄷ', '{:kane1Kane1mung:}'], "eIVnOIVt5qA"),
            (['{:kane1Mumtoe:}', '{:kane1Toe:}', '{:kane1Kane1gukhyum:}', '{:d_126:}', '역사왜곡', '김곰곰', '김곰곰나가', '김곰곰 나가'], "epuhedW_6Sk"),
            (['게이', 'ㄱㅇㅈㅇㄱ', '남자', '게이조이고', '숫말', '여자는안돼요', '조여', '조이기해', '조이기'], "rWKNq8K2TXU"),
            (['사기', '정답사기', '괘씸성공', '괘씸실패'], "KDu9ep9DAp8"),
            (['춘잣', '마하9'], "jh_HER0zLIM"),
            (['대지누', '대진우'], "e8LZjch5GsQ"),
            (['너이게이씨', '게이씨'], "OtFN7bKWnCU"),
            (['도금', '도배', '오때론난', '그긴거'], "aYHWdg8yMSw"),
            (['어딜가미', '어딜감히', 'ㅇㄷㄱㅁ'], "2tye1jz9xmM"),
            (['니게', '니게그런사라미', '니니게그사그런사라미', '케경호'], "9Td0jWsEtvM"),
            (['유썩', 'ㅇㅆ'], "97f3IeMxt6o"),
            (['짱구', '아라썩', '초카무이', '준비', '아이고나', '스노보드', '오게이', '오게이오게이', '보드', '세숫대야' ,'세숫대야로타겠다고', '아라썩', '각자위치로', '호호이', '호호이터치', '음미음미', '이겨따이겨따', '제자로받아줘', '보드를타고내려가서'], "Trx6-Arxymg"),
            (['오옹나이스','으시안오옹'], "_Yf2opMwF_g"),
            (['{:kane1Hal:}', 'ㅗㅜㅑ', '으흐흐', '{:d_108:}'], "ZMEZlaVK1Bw"),
            (['한탕', '한탕이', 'NFT', '두탕이', '계약서', '까따구', '{:kane1Kane1kka:}', '{:kane1Kane1hantang:}'], "aUZw2yd-xn0"),
            (['11', '11수'], "aozyf8izLrE"),
            (['클로버', '클로버핏', '{:d_237:}', '해킹'], "0bsKim2MDZs"),
            (['저스틴썩', '저스틴썬', '코인', '🍌', '바나나'], "V7PEqL95DP4"),
            (['그짤', '짤그'], "lWjsAuU-08k"),
            (['잔뇨', '코넬의힘'], "1ym3tWO5-qE"),
            (['스킵', '스키비야'], "hYrZhW1_gKw"),
            (['AI고난', 'AI', 'Viggle', '비글AI', '비글'], "Zxx6CXA8sDE"),
            (['타지리', '타하', '남편', '녹즙', '지리야', '지리'], "qqH-2hZ2XMA"),
            (['김성근', '한화', '야금', '야구금지', '야구', "ㅖ", "{:kane1Eagles:}"], "m3ifTMuF3_E"),
            (['EFT', '설기뭉', '설기문'], "wnsVjZXGuAc"),
            (['alfos', '알포스', '영도올림'], "P862QJP6WJQ"),
            (['sofla', '소플라'], "Nke2uG7WBA"),
            (['뭉추', '영도내림', '괘씸', 'ㅁㅊ'], "zpBu1mfJDjM"),
            (['이걸왜해', '이걸왜해ㅋㅋ', '케범수', '죽을만큼', '주글만큼', '죽을만큼보고', '주글만큼보고', '{:d_92:}', '{:d_93:}'], "XlVw-bqN-5A"),
            (['바누', '바보지누'], "EwXZygncQk8"),
            (['0000', '유찰', '0독'], "0YojGu5l8fc"),
            (['제가', 'JEGA', '재가'], "nhByQSoYw80"),
            (['찌'], "omAy1YZRtXI"),
            (['지누텔라', '으악', 'ㄸㄸㅆ'], "SJn0LC_SnOE"),
            (['지하실'], "8PbRkUDq-00"),
            (['잔오'], "C29rEqc-Qvw"),
            (['슈라이'], "uTmS1bJhqpQ"),
            (['지누', '지누야'], "49kj-zpkKT4"),
            (['아', '이', '고', '난', '아이고난', 'ㅇㅇㄱㄴ', '{:kane1Ah:}', '{:kane1E:}', '{:kane1Go:}', '{:kane1Nan:}'], "T6y-wFSsy3U")
        ]

        for keywords, video_id in YOUTUBE_MAPPINGS:
            if is_match(keywords):
                youtube_vid = video_id
                break
        youtube_bg_html = ""
        if self.internal_mode:
            if youtube_vid:
                youtube_bg_html = f"""
            <div id="youtube-player" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;"></div>
            <script src="https://www.youtube.com/iframe_api"></script>
            <script>
                var player;
                function onYouTubeIframeAPIReady() {{
                    player = new YT.Player('youtube-player', {{
                        height: '100%',
                        width: '100%',
                        host: 'https://www.youtube-nocookie.com',
                        videoId: '{youtube_vid}',
                        playerVars: {{
                            'autoplay': 1,
                            'controls': 1,
                            'loop': 1,
                            'playlist': '{youtube_vid}',
                            'origin': 'https://www.youtube-nocookie.com',
                            'enablejsapi': 1,
                            'rel': 0
                        }},
                        events: {{
                            'onReady': onPlayerReady
                        }}
                    }});
                }}
                function onPlayerReady(event) {{
                    event.target.setVolume(50);
                    event.target.playVideo();
                }}
            </script>
            """

        # Particle/Effect Logic
        # (Keywords, Type, Data, TextColor, BgColor, ExtraHtmlLambda)
        PARTICLE_MAPPINGS = [
            # Apology (Green BG)
            (['죄송합니다', 'ㅈㅅㅎㄴㄷ', '자숙', '제가', '정리좀하고', '지금부터는', '318', '321'], 
             "emoji", "['🕴️']", "#ffffff", "#f9f9f9", None),
            
            # Memes with specific effects
            ('코', "emoji", "['👃', '🥸', '👺']", "#333333", "#f9f9f9", 
             lambda: f"<div class='extra'>아사람이 코세금으로 한탕한 돈: <br>{count * 3000:,}원</div>"),
             
            ('헉', "image", json.dumps(["https://ssl.pstatic.net/static/nng/glive/icon/a_37.png"]), "#333333", "#f9f9f9",
             lambda: "<div class='stat'>('헉'과 '<img src='https://ssl.pstatic.net/static/nng/glive/icon/a_37.png' style='height:24px; vertical-align:middle;'>' 합산)</div>"),
             
            (['뭉', '뭉탱', '뭉탱이', 'ㅁㅌㅇ', '뭉탱이월드', 'ㅁㅌㅇㅇㄷ', '{:kane1Kane1mung:}'], 
             "image", "['https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Kane1mung_1740411891638.png']", "#333333", "#f9f9f9", None),
             
            (['게이', 'ㄱㅇㅈㅇㄱ', '남자', '게이조이고'], 
             "emoji", "['👯‍♂️', '🙅‍♂️', '👨‍❤️‍💋‍👨', '♂️']", "#333333", "#f9f9f9", None),
             
            (['한탕', '한탕이', 'NFT', '두탕이', '{:kane1Kane1hantang:}'], 
             "image", "['https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Kane1hantang_1740769742403.png']", "#333333", "#f9f9f9", None),
             
            (['계약서', '까따구', '{:kane1Kane1kka:}'], 
             "image", "['https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Kane1kka_1740411866700.png', 'https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Kane1hantang_1740769742403.png']", "#333333", "#f9f9f9", None),
             
            (['클로버', '클로버핏', '{:d_237:}', '해킹'], 
             "image", "['https://ssl.pstatic.net/static/nng/glive/icon/f_18.png']", "#333333", "#f9f9f9", None),
             
            (['이걸왜해', '이걸왜해ㅋㅋ', '케범수', '죽을만큼', '주글만큼', '죽을만큼보고', '주글만큼보고', '{:d_92:}', '{:d_93:}'], 
             "image", "['https://ssl.pstatic.net/static/nng/glive/icon/c_20.png', 'https://ssl.pstatic.net/static/nng/glive/icon/c_21.png']", "#333333", "#f9f9f9", None),
             
            (['{:kane1Mumtoe:}', '{:kane1Toe:}', '{:kane1Kane1gukhyum:}', '{:d_126:}', '역사왜곡', '김곰곰', '김곰곰나가', '김곰곰 나가'], 
             "image", "['https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/2/kane1Mumtoe_1743694855263.png', 'https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/Toe_1743694600765.gif', 'https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Kane1gukhyum_1740769537609.png']", "#333333", "#f9f9f9", None),
             
            (['김성근', '한화', '야금', '야구금지', '야구', "ㅖ", "{:kane1Eagles:}"], 
             "image", "['https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Eagles.png']", "#333333", "#f9f9f9", None),
             
            (['지누텔라', '으악', 'ㄸㄸㅆ'], 
             "emoji", "['💩']", "#333333", "#f9f9f9", None),

            (['저스틴썩', '저스틴썬', '코인', '🍌', '바나나'],
             "emoji", "['🍌']", "#333333", "#f9f9f9", None),
            
            (['지하실'], 
             "image", "['https://ssl.pstatic.net/static/nng/glive/icon/a_37.png']", "#333333", "#f9f9f9", None),
             
            (['아', '이', '고', '난', '아이고난', 'ㅇㅇㄱㄴ', '{:kane1Ah:}', '{:kane1E:}', '{:kane1Go:}', '{:kane1Nan:}'], 
             "image", "['https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Ah.png', 'https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1E.png', 'https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Go.png', 'https://nng-phinf.pstatic.net/glive/subscription/emoji/7b1acb37b35928ff690d011296a9e5ab/1/kane1Nan.png']", "#333333", "#f9f9f9", None),

            (['?'], 
             "emoji", "['❓']", "#333333", "#f9f9f9", None)
        ]

        if data["is_emoticon"]:
            particle_type = "image"
            particle_data = json.dumps([target_url])
            title_html = f"총 <img src='{target_url}' style='vertical-align:middle; height:60px;'> 개수"
        else:
            found_match = False
            if self.internal_mode:
                for keywords, p_type, p_data, t_color, b_color, extra_func in PARTICLE_MAPPINGS:
                    if is_match(keywords):
                        particle_type = p_type
                        particle_data = p_data
                        text_particle_color = t_color
                        bg_color = b_color
                        if extra_func:
                            extra_html = extra_func()
                        found_match = True
                        break
            
            if not found_match:
                # 기본 텍스트 파티클: 글자 하나하나 분해해서 나오도록 수정
                particle_type = "text"
                # target이 '안녕'이면 ['안', '녕']으로 분해
                particle_data = json.dumps(list(target))

        count_str = f"{count:,}"
        percent_str = f"{percent:.3f}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="referrer" content="strict-origin-when-cross-origin">
            <base href="https://www.youtube-nocookie.com/">
            <style>
                body, html {{ margin:0; padding:0; width:100%; height:100%; overflow:hidden; background:{bg_color}; font-family: 'Pretendard JP', sans-serif; }}
                #result-container {{
                    display: block;
                    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                    background: rgba(255, 255, 255, 0.50);
                    padding: 80px 100px; border-radius: 40px;
                    box-shadow: 0 30px 60px rgba(0,0,0,0.2);
                    z-index: 10; text-align: center;
                    min-width: 700px;
                    max-width: 90%;
                    backdrop-filter: blur(15px);
                    border: 1px solid rgba(255, 255, 255, 0.5);
                }}
                #fireworks {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; pointer-events: none; }}
                .title {{ font-size: 3.5rem; color: #444; margin-bottom: 40px; font-weight: bold; display: flex; align-items: center; justify-content: center; gap: 10px; }}
                .count {{ font-size: 8rem; font-weight: 900; color: #444; margin: 10px 0; text-shadow: 2px 2px 0px rgba(0,0,0,0.05); }}
                .stat {{ font-size: 2.5rem; color: #555; margin-top: 15px; }}
                .extra {{ margin-top: 35px; font-size: 2.5rem; color: #d32f2f; font-weight: bold; line-height: 1.5; }}
            </style>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            {youtube_bg_html}
            <canvas id="fireworks"></canvas>
            <div id="result-container">
                <div class="title">{title_html}</div>
                <div class="count">{count_str}개</div>
                <div class="stat">전체 채팅 {total_chars:,}글자 중 {percent_str}%</div>
                {extra_html}
            </div>
            <script>
                const canvas = document.getElementById('fireworks');
                const ctx = canvas.getContext('2d');
                let width, height;
                const particleType = "{particle_type}"; 
                const particleSource = {particle_data};
                const particleTextColor = "{text_particle_color}";
                const assets = []; 
                const assetContainer = document.createElement('div');
                assetContainer.style.cssText = 'position:fixed; top:0; left:0; width:1px; height:1px; opacity:0.01; pointer-events:none; overflow:hidden; z-index:-1;';
                document.body.appendChild(assetContainer);
                
                function loadAssets(callback) {{
                    let loadedCount = 0;
                    let totalCount = particleSource.length;
                    
                    if (totalCount === 0) {{
                        callback();
                        return;
                    }}

                    function onAssetLoaded() {{
                        loadedCount++;
                        if (loadedCount >= totalCount) {{
                            // Ensure dimensions are ready before starting
                            if (width > 100 && height > 100) {{
                                callback();
                            }} else {{
                                setTimeout(onAssetLoaded, 100);
                                loadedCount--; // Retry check later
                            }}
                        }}
                    }}

                    particleSource.forEach(src => {{
                        const img = new Image();
                        if (particleType === 'image') {{
                            img.src = src;
                            assetContainer.appendChild(img); // GIF Animation Trick
                        }} else {{
                            // emoji or text
                            const canvasTemp = document.createElement('canvas');
                            canvasTemp.width = 64;
                            canvasTemp.height = 64;
                            const ctxTemp = canvasTemp.getContext('2d');
                            ctxTemp.font = "48px Arial";
                            ctxTemp.textAlign = "center";
                            ctxTemp.textBaseline = "middle";
                            ctxTemp.fillStyle = particleTextColor;
                            ctxTemp.fillText(src, 32, 36);
                            img.src = canvasTemp.toDataURL();
                        }}
                        img.onload = onAssetLoaded;
                        img.onerror = onAssetLoaded;
                        assets.push(img);
                    }});
                }}

                function resize() {{
                    var w = window.innerWidth;
                    var h = window.innerHeight;
                    
                    // Force minimum size check to avoid 100x30 default
                    if (w > 100 && h > 100) {{
                         width = canvas.width = w;
                         height = canvas.height = h;
                    }} else {{
                        // console.log("Suspicious size: " + w + "x" + h + ". Retrying...");
                        setTimeout(resize, 100);
                    }}
                }}
                window.addEventListener('resize', resize);
                
                // Multiple triggers to ensure size is caught after layout
                resize();
                window.onload = resize;
                setTimeout(resize, 500);

                class Particle {{
                    constructor() {{
                        this.init();
                    }}
                    
                    init() {{
                        // Check resize on particle init too
                        if (canvas.width !== window.innerWidth && window.innerWidth > 100) resize();

                        this.x = Math.random() * width;
                        this.y = height + Math.random() * 100; 
                        this.vx = Math.random() * 4 - 2;
                        this.vy = -(Math.random() * 12 + 12); 
                        this.gravity = 0.25;
                        this.alpha = 1;
                        this.rotation = Math.random() * Math.PI * 2;
                        this.rotationSpeed = Math.random() * 0.1 - 0.05;
                        this.size = Math.random() * 30 + 30; 
                        
                        if (assets.length > 0) {{
                            this.img = assets[Math.floor(Math.random() * assets.length)];
                        }}
                    }}
                    
                    update() {{
                        this.x += this.vx;
                        this.y += this.vy;
                        this.vy += this.gravity;
                        this.rotation += this.rotationSpeed;
                        
                        if (this.y > height + 200) {{
                            this.init();
                        }}
                    }}
                    
                    draw(ctx) {{
                        if (!this.img) return; 
                        
                        ctx.save();
                        ctx.translate(this.x, this.y);
                        ctx.rotate(this.rotation);
                        ctx.globalAlpha = this.alpha;
                        
                        ctx.drawImage(this.img, -this.size/2, -this.size/2, this.size, this.size);
                        
                        ctx.restore();
                    }}
                }}

                const particles = [];
                let animationId;

                function animate() {{
                    ctx.clearRect(0, 0, width, height);
                    particles.forEach(p => {{
                        p.update();
                        p.draw(ctx);
                    }});
                    animationId = requestAnimationFrame(animate);
                }}

                // Start sequence
                loadAssets(() => {{
                    for(let i=0; i<150; i++) {{
                        particles.push(new Particle());
                    }}
                    animate();
                }});

            </script>
        </body>
        </html>
        """
        from PyQt6.QtCore import QUrl
        self.web_view.setHtml(html, QUrl("https://www.youtube-nocookie.com/"))

class UserStatsResultDialog(QDialog):
    def __init__(self, result_data, mask_type, limit, parent=None):
        super().__init__(parent)
        self.setWindowTitle("유저별 채팅 분석 결과")
        self.resize(1000, 800)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))
        
        if parent:
             geo = parent.geometry()
             center = geo.center()
             self.move(center - self.rect().center())
        
        layout = QVBoxLayout(self)

        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(10, 10, 10, 5) 
        summary_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(summary_widget)

        line1_layout = QHBoxLayout()
        self.total_chats_label = QLabel()
        self.total_users_label = QLabel()
        line1_layout.addWidget(self.total_chats_label)
        line1_layout.addWidget(self.total_users_label)
        summary_layout.addLayout(line1_layout)

        self.scroll_button = QPushButton("자동 스크롤 시작")
        self.scroll_button.clicked.connect(self.toggle_auto_scroll)
        layout.addWidget(self.scroll_button)

        self.web_view = QWebEngineView(self)
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.web_view.hide()
        self.web_view.loadFinished.connect(self.on_load_finished)
        layout.addWidget(self.web_view)

        self.loading_label = QLabel("로딩 중...", self)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
        layout.addWidget(self.loading_label)

        self.scroll_timer = QTimer(self)
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.scroll_step)
        self.current_scroll_rank = 0
        self.max_rows = 0

        self.populate_data(result_data, mask_type, limit)

    def populate_data(self, result_data, mask_type, limit):
        import json
        import traceback
        import html
        
        try:
            total_chats = result_data.get("total_chats", 0)
            user_list = result_data.get("sorted_result", [])
            total_users = result_data.get("total_users", len(user_list))

            self.total_chats_label.setText(f"<b>총 채팅 수:</b> {total_chats:,}개")
            self.total_users_label.setText(f"<b>참여 유저:</b> {total_users:,}명")
            
            has_more = False
            if len(user_list) > limit:
                user_list = user_list[:limit]
            
            self.max_rows = len(user_list)

            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: 'Pretendard JP', sans-serif; margin: 0; padding: 10px; }
                    table { width: 100%; border-collapse: collapse; }
                    th { background-color: #f2f2f2; padding: 10px; position: sticky; top: 0; z-index: 10; border-bottom: 2px solid #ddd; text-align: left;}
                    td { padding: 8px; border-bottom: 1px solid #ddd; }
                    tr { content-visibility: auto; contain-intrinsic-size: 30px; scroll-margin-top: 40px; }
                    tr.highlight { background-color: #fff9c4; font-weight: bold; }
                    .rank-col { width: 60px; text-align: center; }
                    .count-col { width: 100px; text-align: right; }
                    .percent-col { width: 100px; text-align: right; }
                </style>
                <script>
                    function highlightRow(index) {
                        var highlighted = document.querySelectorAll('tr.highlight');
                        highlighted.forEach(function(row) {
                            row.classList.remove('highlight');
                        });
                        
                        var row = document.getElementById('row-' + index);
                        if (row) {
                            row.classList.add('highlight');
                            row.scrollIntoView({behavior: "smooth", block: "start"});
                        }
                    }
                    
                    function scrollToBottom() {
                        window.scrollTo(0, document.body.scrollHeight);
                    }
                </script>
            </head>
            <body>
                <table>
                    <thead>
                        <tr>
                            <th class="rank-col">순위</th>
                            <th>닉네임</th>
                            <th class="count-col">채팅수</th>
                            <th class="percent-col">점유율 (%)</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for i, (user_id, count, nickname) in enumerate(user_list):
                percentage = (count / total_chats) * 100 if total_chats > 0 else 0
                
                display_name = nickname
                if mask_type == "full":
                    display_name = "*****"
                elif mask_type == "half":
                    if len(nickname) > 1:
                        display_name = nickname[0] + "*" * (len(nickname) - 1)
                    else:
                        display_name = "*"
                
                html_content += f"""
                    <tr id="row-{i}">
                        <td class="rank-col">{i+1}</td>
                        <td>{html.escape(display_name)}</td>
                        <td class="count-col">{count:,}</td>
                        <td class="percent-col">{percentage:.3f}%</td>
                    </tr>
                """
                
            html_content += """
                    </tbody>
                </table>
            </body>
            </html>
            """
            
            self.web_view.setHtml(html_content)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "오류", f"HTML 생성 중 오류가 발생했습니다: {e}")
            return

    def on_load_finished(self, ok):
        if ok:
             QTimer.singleShot(100, lambda: self.web_view.page().runJavaScript("scrollToBottom()"))
             QTimer.singleShot(200, self.show_webview)

    def show_webview(self):
        self.loading_label.hide()
        self.web_view.show()

    def toggle_auto_scroll(self):
        if self.scroll_timer.isActive():
            self.scroll_timer.stop()
            self.scroll_button.setText("자동 스크롤 시작")
        else:
            if self.max_rows < 1: return
            self.current_scroll_rank = self.max_rows
            self.scroll_button.setText("정지")
            self.highlight_and_schedule_next()

    def highlight_and_schedule_next(self):
        row_index = self.current_scroll_rank - 1
        
        self.web_view.page().runJavaScript(f"highlightRow({row_index})")

        interval = 100
        if 50 < self.current_scroll_rank <= 100:
            interval = 300
        elif 10 < self.current_scroll_rank <= 50:
            interval = 500
        elif 3 < self.current_scroll_rank <= 10:
            interval = 1000
        elif self.current_scroll_rank <= 3:
            interval = 3000
            
        self.scroll_timer.setInterval(interval)
        self.scroll_timer.start()

    def scroll_step(self):
        self.current_scroll_rank -= 1
        if self.current_scroll_rank > 0:
            self.highlight_and_schedule_next()
        else:
            self.scroll_button.setText("자동 스크롤 완료")
            self.scroll_timer.stop()



class EmoticonSelectorDialog(QDialog):
    def __init__(self, internal_mode=False, parent=None):
        super().__init__(parent)
        self.internal_mode = internal_mode
        self.setWindowTitle("이모티콘 선택")
        self.resize(700, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView(self)
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.web_view)
        
        self.web_view.titleChanged.connect(self.on_title_changed)
        
        self.selected_emoticon = None
        
        self.load_and_show_html()

    def on_title_changed(self, title):
        if title.startswith("SELECTED|"):
            parts = title.split("|")
            if len(parts) >= 3:
                name = parts[1]
                url = "|".join(parts[2:])
                self.selected_emoticon = (name, url)
                self.accept()

    def load_and_show_html(self):
        try:
            json_path = os.path.join(USERPATH, "BCU", "chat_emoticons.json")
            with open(json_path, 'r', encoding='utf-8') as f:
                emoticons = json.load(f)
            
            categories = {
                "kane": {"title": "케인 구독티콘", "items": []},
                "lck": {"title": "LCK 이모티콘", "items": []},
                "mlb": {"title": "MLB 이모티콘", "items": []},
                "sd": {"title": "CHZZK 구독티콘", "items": []},
                "d": {"title": "CHZZK 이모티콘", "items": []},
                "others": {"title": "기타", "items": []}
            }
            order = ["kane", "lck", "mlb", "sd", "d", "others"]
            
            if not self.internal_mode:
                if "kane" in categories:
                    del categories["kane"]
                if "kane" in order:
                    order.remove("kane")
            
            for key, url in emoticons.items():
                lower_key = key.lower()
                found = False
                if lower_key.startswith("{:kane"):
                    if "kane" in categories:
                        categories["kane"]["items"].append((key, url))
                    found = True
                elif lower_key.startswith("{:lck"):
                    categories["lck"]["items"].append((key, url))
                    found = True
                elif lower_key.startswith("{:mlb"):
                    categories["mlb"]["items"].append((key, url))
                    found = True
                elif lower_key.startswith("{:sd"):
                    categories["sd"]["items"].append((key, url))
                    found = True
                
                if not found:
                    if lower_key.startswith("{:d"):
                         categories["d"]["items"].append((key, url))
                    else:
                         categories["others"]["items"].append((key, url))

            tabs_html = ""
            contents_html = ""
            
            active_set = False
            
            for key in order:
                cat_data = categories[key]
                if not cat_data["items"]: continue
                
                cat_id = f"tab-{key}"
                active_class = "active" if not active_set else ""
                
                tabs_html += f'<button class="tab-link {active_class}" onclick="openTab(event, \'{cat_id}\')">{cat_data["title"]}</button>'
                
                grid_items = ""
                for name, url in cat_data["items"]:
                    grid_items += f"""
                        <div class="grid-item" onclick="selectEmoticon('{name}', '{url}')">
                            <img src="{url}" loading="lazy">
                            <div class="name">{name}</div>
                        </div>
                    """
                
                contents_html += f"""
                    <div id="{cat_id}" class="tab-content" style="display: {'block' if not active_set else 'none'};">
                        <div class="grid-container">
                            {grid_items}
                        </div>
                    </div>
                """
                active_set = True

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ 
                        margin: 0; padding: 0; font-family: 'Pretendard JP', sans-serif; 
                        background: #f0f0f0; display: flex; flex-direction: column; height: 100vh;
                        user-select: none;
                    }}
                    .tabs {{
                        display: flex; background: #fff; border-bottom: 2px solid #ddd;
                        position: sticky; top: 0; z-index: 100; overflow-x: auto;
                        white-space: nowrap; flex-shrink: 0;
                    }}
                    .tab-link {{
                        background: none; border: none; padding: 15px 20px;
                        font-size: 14px; font-weight: bold; color: #666; cursor: pointer;
                        transition: 0.3s;
                    }}
                    .tab-link:hover {{ background: #f9f9f9; color: #333; }}
                    .tab-link.active {{ 
                        color: #1976D2; border-bottom: 3px solid #1976D2; 
                    }}
                    .tab-content {{
                        flex: 1; overflow-y: auto; padding: 10px;
                    }}
                    .grid-container {{
                        display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
                        gap: 10px;
                    }}
                    .grid-item {{
                        background: #fff; border-radius: 8px; padding: 10px;
                        display: flex; flex-direction: column; align-items: center; justify-content: center;
                        cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;
                        border: 1px solid #eee;
                    }}
                    .grid-item:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                        border-color: #1976D2;
                    }}
                    .grid-item img {{
                        width: 64px; height: 64px; object-fit: contain; margin-bottom: 5px;
                    }}
                    .grid-item .name {{
                        font-size: 12px; color: #555; text-align: center;
                        word-break: break-all;
                    }}
                </style>
            </head>
            <body>
                <div class="tabs">
                    {tabs_html}
                </div>
                {contents_html}
                
                <script>
                    function selectEmoticon(name, url) {{
                         document.title = "SELECTED|" + name + "|" + url;
                    }}

                    function openTab(evt, tabId) {{
                        var i, tabcontent, tablinks;
                        tabcontent = document.getElementsByClassName("tab-content");
                        for (i = 0; i < tabcontent.length; i++) {{
                            tabcontent[i].style.display = "none";
                        }}
                        tablinks = document.getElementsByClassName("tab-link");
                        for (i = 0; i < tablinks.length; i++) {{
                            tablinks[i].className = tablinks[i].className.replace(" active", "");
                        }}
                        document.getElementById(tabId).style.display = "block";
                        evt.currentTarget.className += " active";
                    }}
                </script>
            </body>
            </html>
            """
            
            self.web_view.setHtml(html)

        except Exception as e:
            QMessageBox.critical(self, "오류", f"이모티콘 로드 실패: {e}")
            self.reject()

    def populate_html(self, data, mask_type):
        import json
        
        total_chats = data["total_chats"]
        total_users = data["total_users"]
        user_stats = data["user_stats"]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Pretendard JP', sans-serif; margin: 0; padding: 20px; background: #f9f9f9; }}
                h2 {{ text-align: center; color: #333; }}
                .summary {{ text-align: center; margin-bottom: 20px; font-size: 1.1em; color: #555; }}
                .summary strong {{ color: #d32f2f; font-size: 1.3em; }}
                table {{ width: 100%; border-collapse: collapse; background: #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                th, td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
                th {{ background: #f0f0f0; position: sticky; top: 0; z-index: 10; font-weight: bold; color: #444; }}
                tr:nth-child(even) {{ background: #fcfcfc; }}
                tr:hover {{ background: #f0f5ff; }}
                .rank-1 {{ color: #DAA520; font-weight: bold; font-size: 1.2em; }}
                .rank-2 {{ color: #C0C0C0; font-weight: bold; font-size: 1.1em; }}
                .rank-3 {{ color: #CD7F32; font-weight: bold; font-size: 1.1em; }}
            </style>
        </head>
        <body>
            <h2>🏆 유저별 채팅 순위 🏆</h2>
            <div class="summary">
                총 채팅 수: <strong>{total_chats:,}</strong>개 / 
                총 참여 유저: <strong>{total_users:,}</strong>명
            </div>
            <table>
                <thead>
                    <tr>
                        <th width="15%">순위</th>
                        <th width="40%">닉네임</th>
                        <th width="25%">채팅 수</th>
                        <th width="20%">비율</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for i, user in enumerate(user_stats):
            rank = i + 1
            nick = user["nick"]
            count = user["count"]
            percent = (count / total_chats * 100) if total_chats > 0 else 0
            
            masked_nick = nick
            if mask_type == "full":
                masked_nick = "***"
            elif mask_type == "half":
                if len(nick) > 1:
                    masked_nick = nick[0] + "*" * (len(nick) - 1)
                else:
                    masked_nick = "*"
            
            rank_class = f"class='rank-{rank}'" if rank <= 3 else ""
            
            html += f"""
                <tr>
                    <td {rank_class}>{rank}</td>
                    <td>{masked_nick}</td>
                    <td>{count:,}</td>
                    <td>{percent:.3f}%</td>
                </tr>
            """
            
        html += """
                </tbody>
            </table>
            
            <script>
                // Auto-scroll logic
                function autoScroll() {
                    window.scrollBy(0, 1);
                    scrolldelay = setTimeout(autoScroll, 50); // Adjust speed
                }
                // Start auto-scroll after 2 seconds
                setTimeout(autoScroll, 2000);
            </script>
        </body>
        </html>
        """
        
        self.web_view.setHtml(html)
