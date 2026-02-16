import os
import profile
import shutil
import types
from PyQt6.QtWidgets import (QCheckBox,
                             QComboBox, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QPushButton, QSpinBox, QVBoxLayout, QWidget,
                             QGroupBox, QFormLayout, QAbstractItemView)
from PyQt6.QtGui import QPen, QPainterPath, QFontMetrics, QFont, QIcon, QDrag, QColor, QBrush, QPainter, QColor
from PyQt6.QtCore import QRect, Qt, QMimeData, QUrl, QPoint, pyqtProperty, QPropertyAnimation, QEasingCurve, QSettings, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineCore import QWebEngineSettings
from datetime import datetime, timedelta

from app.resources import resource_path
from app.constants import USERPATH
from app.utils.simulator import ChatSimulator

class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)

    def featurePermissionRequested(self, security_origin, feature):
        self.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionGrantedByUser)
        if feature == QWebEnginePage.Clipboard:
            self.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionGrantedByUser)

    def createWindow(self, _type):
        popup = PopupWindow(self.profile(), self.parent())
        new_page = popup.browser.page()
        new_page.geometryChangeRequested.connect(popup.resize_and_recenter)
        popup.move_to_parent()
        popup.show()
        popup.move_to_parent()
        popup.show()
        return new_page

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[Console] {message}")
        if message == "BCU_ALLOW_CLOSE":
            # Attempt to find the PopupWindow parent
            # self.parent() is typically the QWebEngineView
            view = self.parent()
            if view and view.parent():
                popup = view.parent()
                if hasattr(popup, 'allow_close_override'):
                    popup.allow_close_override = True  # Set flag to bypass prevent_close
                print("[CustomWebEnginePage] Received BCU_ALLOW_CLOSE. Force closing popup in 500ms.")
                QTimer.singleShot(500, popup.close)
        elif message == "BCU_CANCEL_PREDICTION":
            # 승부예측 취소 시 즉시 팝업창 강제 닫기
            view = self.parent()
            if view and view.parent():
                popup = view.parent()
                if hasattr(popup, 'allow_close_override'):
                    popup.allow_close_override = True
                print("[CustomWebEnginePage] Received BCU_CANCEL_PREDICTION. Force closing popup immediately.")
                QTimer.singleShot(100, popup.close)
    
class PopupWindow(QWidget):
    def __init__(self, profile: QWebEngineProfile, parent=None):
        super().__init__(parent)
        self.setWindowTitle("팝업창")
        self.setGeometry(0, 0, 1280, 960)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))
        flags = Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint
        flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.browser = QWebEngineView(self)

        self.custom_page = CustomWebEnginePage(profile, self.browser)
        self.custom_page.zoomFactorChanged.connect(self._on_zoom_changed)
        
        self.custom_page.windowCloseRequested.connect(self.on_close_requested)
        
        self.browser.setPage(self.custom_page)
        
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)
        self.setLayout(layout)
        
        self.browser.urlChanged.connect(self._on_url_changed)
        self.browser.loadFinished.connect(self._inject_scraper)
        
        self.prevent_close = False
        self.settings_id = None
        self.allow_close_override = False

    def _on_url_changed(self, url):
        url_str = url.toString()
        if "/prediction" in url_str:
            self.setWindowTitle("승부예측")

    def on_close_requested(self):
        """웹 페이지에서 window.close() 요청 시 호출됨"""
        current_url = self.browser.url().toString()
        is_prediction = "/prediction" in current_url
        
        if (self.prevent_close or is_prediction) and not self.allow_close_override:
            print("[PopupWindow] Close requested but prevented. Reloading page instead.")
            self.browser.reload()
        else:
            self.close()
    
    def setUrl(self, url):
        self.browser.setUrl(url)
    
    def move_to_parent(self):
        if self.parent():
            parent_local_center = self.parent().rect().center()
            parent_global_center = self.parent().mapToGlobal(parent_local_center)
            popup_frame_rect = self.frameGeometry()
            popup_frame_rect.moveCenter(parent_global_center)
            self.move(popup_frame_rect.topLeft())
    
    def run_script(self, script):
        print(f"[PopupWindow] run_script called. Script length: {len(script)}")
        def _callback(result):
            print(f"[PopupWindow] runJavaScript executed. Result: {result}")
        
        # 페이지가 로드되었는지 확인 (URL이 비어있지 않으면 로드됨)
        current_url = self.browser.url().toString()
        if current_url and current_url != "about:blank":
            print("[PopupWindow] Page already loaded. Running script immediately.")
            self.browser.page().runJavaScript(script, 0, _callback)
        else:
            print("[PopupWindow] Page loading. Connecting to loadFinished.")
            self.browser.loadFinished.connect(lambda: self.browser.page().runJavaScript(script, 0, _callback))
    
    
    def set_title(self, title):
        self.setWindowTitle(title)

    def _on_zoom_changed(self, zoom_factor):
        """줌 변경 시 설정 저장"""
        if self.settings_id:
            settings = QSettings(os.path.join(USERPATH, "BCU", "browser_zoom.ini"), QSettings.Format.IniFormat)
            settings.setValue(self.settings_id, zoom_factor)

    def _inject_scraper(self, success):
        """페이지 로드 완료 시 스크립트 재주입 (Refresh only)"""
        if not success: return
        # Click the internal refresh button every second
        # AND allow closing if Result/Cancel popup confirm buttons are clicked
        script = """
            if (window.refreshInterval) clearInterval(window.refreshInterval);
            if (window.checkResultInterval) clearInterval(window.checkResultInterval);
            if (window.bcuTimerInterval) clearInterval(window.bcuTimerInterval);
            
            // 1. Auto Refresh Logic
            window.refreshInterval = setInterval(function() {
                const btn = document.querySelector('button[class*="prediction_component_refresh_button"]');
                if (btn) {
                    btn.click();
                }
            }, 1000);

            // 2. Result Selection Timer Display (fetches from Python backend)
            window.bcuTimerInterval = setInterval(async function() {
                try {
                    const response = await fetch('http://127.0.0.1:5000/prediction_timer_status');
                    const data = await response.json();
                    const remaining = data.result_selection_remaining;
                    
                    // Find the "결과 선택" button
                    const buttons = document.querySelectorAll('button');
                    let resultBtn = null;
                    buttons.forEach(btn => {
                        if (btn.innerText.includes('결과 선택')) {
                            resultBtn = btn;
                        }
                    });
                    
                    if (resultBtn) {
                        let timerEl = document.getElementById('bcu-result-timer');
                        
                        if (remaining > 0) {
                            // Timer is running - show countdown
                            if (!timerEl) {
                                timerEl = document.createElement('span');
                                timerEl.id = 'bcu-result-timer';
                                timerEl.style.cssText = 'margin-left: 10px; color: #ff6b6b; font-weight: bold; font-size: 14px;';
                                resultBtn.parentElement.insertBefore(timerEl, resultBtn.nextSibling);
                            }
                            const min = Math.floor(remaining / 60);
                            const sec = remaining % 60;
                            timerEl.textContent = '결과 선택까지 ' + min + ':' + sec.toString().padStart(2, '0') + ' 남음';
                            timerEl.style.color = '#ff6b6b';
                        } else {
                            // Timer ended or never started - remove the element entirely
                            if (timerEl) {
                                timerEl.remove();
                            }
                        }
                    }
                } catch (e) {
                    // Silently fail if server is unavailable
                }
            }, 200);
            
            // 3. Auto Close Result Logic (New Feature)
            // If Result Popup is open AND New Prediction matches (Voting/Participating), close popup.
            window.checkResultInterval = setInterval(function() {
                const popups = document.querySelectorAll('[class*="popup_container"]');
                let resultPopup = null;
                
                popups.forEach(p => {
                    const title = p.querySelector('[class*="popup_title"]');
                    if (title && title.innerText.includes("승부예측 결과 발표")) {
                        resultPopup = p;
                    }
                });
                
                if (resultPopup) {
                    const bodyText = document.body.innerText;
                    // "진행" indicates a new prediction has started
                    if (bodyText.includes("진행")) {
                        console.log("[BCU] New prediction detected! Closing Result Popup...");
                        const btns = resultPopup.querySelectorAll('button');
                        btns.forEach(b => {
                            if (b.innerText.trim() === "확인" || b.className.includes("popup_action__")) {
                                b.click();
                            }
                        });
                    }
                }
            }, 1000);
            
            // 3. Allow Close Logic (Click Listener)
            document.body.addEventListener('click', function(e) {
                // Check if target is inside a button (handle 'span' inside 'button')
                let target = e.target.closest('button');
                if (!target) return;
                
                // Helper to check text content
                let text = target.innerText.trim();
                
                // Check if inside a popup container
                let popup = target.closest('[class*="popup_container"]');
                if (!popup) return;
                
                let titleEl = popup.querySelector('[class*="popup_title"]');
                if (!titleEl) return;
                let title = titleEl.innerText.trim();

                // Check for Action Button (Confirm/Cancel) - Use wildcard for robustness
                // e.g. popup_action__KDxfm -> popup_action__
                let isActionButton = target.className.includes("popup_action__");
                // or popup_box__ if exists
                if (target.className.includes("popup_box__")) {
                    isActionButton = true;
                }
                
                console.log("isValidClick check - title: " + title + ", text: " + text);
                
                // 승부예측 취소 팝업에서 "예" 버튼 클릭 시 즉시 닫기 요청
                if (title.includes("승부예측 취소") && (text === "예" || isActionButton)) {
                    console.log("BCU_CANCEL_PREDICTION");
                    return;
                }
                
                // Specific Check: Result Announcement (Confirm)
                let isValidClick = false;
                if (title.includes("승부예측 결과 발표") && (text === "확인" || isActionButton)) {
                    isValidClick = true;
                }

                if (isValidClick) {
                     // [Check 1-Minute Warning]
                     // Wait 300ms to see if a warning toast appears
                     setTimeout(() => {
                        const bodyText = document.body.innerText;
                        if (bodyText.includes("1분")) {
                            console.log("[BCU] Warning Detected: 1-minute Result Delay. canceling Close.");
                        } else {
                            console.log("BCU_ALLOW_CLOSE");
                        }
                     }, 300);
                }
            }, true); // Capture phase
        """
        self.browser.page().runJavaScript(script)
        
        # [NEW] Inject Prediction Templates Script for Prediction Popup
        current_url = self.browser.url().toString()
        if "/prediction" in current_url:
            print(f"[PopupWindow] Prediction page detected ({current_url}). Injecting templates script...")
            try:
                tpl_script_path = resource_path(os.path.join('resources', 'script', 'prediction_templates.js'))
                if os.path.exists(tpl_script_path):
                    with open(tpl_script_path, "r", encoding="utf-8") as file:
                        tpl_script_content = file.read()
                    self.browser.page().runJavaScript(tpl_script_content)
                    print("[PopupWindow] prediction_templates.js injected successfully.")
                else:
                    print(f"[PopupWindow] Error: prediction_templates.js not found at {tpl_script_path}")
            except Exception as e:
                print(f"[PopupWindow] Failed to inject prediction templates: {e}")

    def resize_and_recenter(self, geometry):
        """새 창 열림 시 크기/위치 조정"""
        self.resize(geometry.width(), geometry.height())
        self.move_to_parent()
        self.show()


class TestOverlayDialog(QWidget):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("오버레이 테스트 컨트롤러")
        self.setGeometry(100, 100, 400, 600)
        self.overlay_window = None
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

        layout = QVBoxLayout()

        # 1. Overlay Window Control
        btn_layout = QHBoxLayout()
        self.btn_open_overlay = QPushButton("오버레이 창 열기")
        self.btn_open_overlay.clicked.connect(self.open_overlay_window)
        btn_layout.addWidget(self.btn_open_overlay)
        layout.addLayout(btn_layout)

        # 2. Data Inputs
        form_layout = QFormLayout()
        
        self.input_status = QComboBox()
        self.input_status.addItems(["WAITING", "ONGOING", "CLOSED", "RESULT"])
        form_layout.addRow("상태 (Status):", self.input_status)

        self.input_title = QLineEdit("승부예측 테스트 제목")
        form_layout.addRow("제목 (Title):", self.input_title)

        self.input_timer = QLineEdit("05:00")
        form_layout.addRow("타이머 (Timer):", self.input_timer)
        
        self.input_winner = QLineEdit("")
        self.input_winner.setPlaceholderText("승리 항목 이름 (RESULT 상태일 때)")
        form_layout.addRow("승자 (Winner):", self.input_winner)

        layout.addLayout(form_layout)

        # 3. Items Input
        layout.addWidget(QLabel("항목 설정 (Items):"))
        self.items_layout = QVBoxLayout()
        self.item_widgets = []
        
        # Add initial 2 items
        self.add_item_widget("항목 1", "50%", "1.9")
        self.add_item_widget("항목 2", "50%", "1.9")

        layout.addLayout(self.items_layout)

        # Item Control Buttons
        item_btn_layout = QHBoxLayout()
        self.btn_add_item = QPushButton("+ 항목 추가")
        self.btn_add_item.clicked.connect(lambda: self.add_item_widget(f"항목 {len(self.item_widgets)+1}", "0%", "1.0"))
        item_btn_layout.addWidget(self.btn_add_item)
        
        self.btn_clear_items = QPushButton("초기화")
        self.btn_clear_items.clicked.connect(self.clear_items)
        item_btn_layout.addWidget(self.btn_clear_items)
        layout.addLayout(item_btn_layout)

        # 4. Send Button
        self.btn_send = QPushButton("데이터 전송 (Update)")
        self.btn_send.clicked.connect(self.send_data)
        self.btn_send.setStyleSheet("background-color: #00ce7c; color: white; font-weight: bold; padding: 10px;")
        layout.addWidget(self.btn_send)

        self.setLayout(layout)

    def open_overlay_window(self):
        # Check if window exists and is valid
        is_open = False
        try:
            if self.overlay_window is not None and self.overlay_window.isVisible():
                is_open = True
        except RuntimeError:
            # Object has been deleted (WA_DeleteOnClose)
            self.overlay_window = None
            is_open = False

        if not is_open:
            self.overlay_window = PopupWindow(self.profile)
            self.overlay_window.setWindowTitle("OBS Overlay Test View")
            self.overlay_window.resize(1000, 200)
            file_path = os.path.join(USERPATH, "BCU", "prediction_overlay.html")
            self.overlay_window.setUrl(QUrl.fromLocalFile(file_path))
            self.overlay_window.show()
        else:
            self.overlay_window.activateWindow()

    def add_item_widget(self, name="", percent="", ratio=""):
        row_widget = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0,0,0,0)
        
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("이름")
        percent_edit = QLineEdit(percent)
        percent_edit.setPlaceholderText("%")
        percent_edit.setFixedWidth(60)
        
        del_btn = QPushButton("X")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda: self.remove_item_widget(row_widget))
        
        row_layout.addWidget(name_edit)
        row_layout.addWidget(percent_edit)
        row_layout.addWidget(del_btn)
        
        row_widget.setLayout(row_layout)
        self.items_layout.addWidget(row_widget)
        self.item_widgets.append((row_widget, name_edit, percent_edit))

    def remove_item_widget(self, widget):
        self.items_layout.removeWidget(widget)
        widget.deleteLater()
        self.item_widgets = [w for w in self.item_widgets if w[0] != widget]

    def clear_items(self):
        for w_tuple in self.item_widgets:
            w_tuple[0].deleteLater()
        self.item_widgets = []

    def send_data(self):
        import requests
        
        status = self.input_status.currentText()
        title = self.input_title.text()
        timer = self.input_timer.text()
        winner = self.input_winner.text()
        
        items = []
        for _, name_edit, percent_edit in self.item_widgets:
            items.append({
                "name": name_edit.text(),
                "percent": percent_edit.text(),
                "ratio": "0" # ratio_edit.text() if needed
            })
        
        payload = {
            "state": status,
            "title": title,
            "timer": timer,
            "items": items
        }
        
        try:
            # 1. Update stats
            requests.post("http://127.0.0.1:5000/update_prediction_stats", json=payload, timeout=1)
            
            # 2. Update winner if RESULT and winner specified
            if status == "RESULT" and winner:
                 requests.post("http://127.0.0.1:5000/update_prediction_winner", json={"winner": winner}, timeout=1)
                 
            print("[TestController] Data sent:", payload)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to send data: {e}")



class VoteBar(QWidget):
    def __init__(self, total_votes, voters, parent=None):
        super().__init__(parent)
        self.total_votes = total_votes
        self.voters = voters
        self.setMinimumHeight(15)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        background_rect = QRect(0, 0, self.width(), self.height())
        painter.setBrush(QColor(220, 220, 220))
        painter.drawRect(background_rect)

        progress_width = int((len(self.voters) / self.total_votes) * self.width())
        progress_rect = QRect(0, 0, progress_width, self.height())
        painter.setBrush(QColor(115, 249, 174))
        painter.drawRect(progress_rect)

class QListWidgetDonationImg(QListWidget):
    def __init__(self,e):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
    def startDrag(self, event):
        item = self.currentItem()
        if not item:
            return

        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and "file_path" in data:
            file_path = data["file_path"]
        elif isinstance(data, str):
            file_path = data
        else:
            file_path = None
        if file_path:
            mime_data = QMimeData()
            url = QUrl.fromLocalFile(file_path)
            mime_data.setUrls([url])
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                destination = os.path.join("C:/", os.path.basename(file_path))
                shutil.copy(file_path, destination)
            event.acceptProposedAction()
        else:
            event.ignore()

    def findItemByText(self, text):
        list = []
        for index in range(self.count()):
            item = self.item(index)
            if item.text() == text:
                list.append(item)
        return list

class QToggle(QCheckBox):
    bg_color = pyqtProperty(
        QColor, lambda self: self._bg_color,
        lambda self, col: setattr(self, '_bg_color', col))
    circle_color = pyqtProperty(
        QColor, lambda self: self._circle_color,
        lambda self, col: setattr(self, '_circle_color', col))
    active_color = pyqtProperty(
        QColor, lambda self: self._active_color,
        lambda self, col: setattr(self, '_active_color', col))
    disabled_color = pyqtProperty(
        QColor, lambda self: self._disabled_color,
        lambda self, col: setattr(self, '_disabled_color', col))
    text_color = pyqtProperty(
        QColor, lambda self: self._text_color,
        lambda self, col: setattr(self, '_text_color', col))

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_color, self._circle_color, self._active_color, \
            self._disabled_color, self._text_color = QColor("#0BF"), \
            QColor("#DDD"), QColor('#777'), QColor("#CCC"), QColor("#000")
        self._circle_pos, self._intermediate_bg_color = None, None
        self.setFixedHeight(18)
        self._animation_duration = 300
        self.stateChanged.connect(self.start_transition)
        self._user_checked = False

    def set_circle_pos(self, pos):
        setattr(self, '_circle_pos', pos)
        self.update()
        return None

    circle_pos = pyqtProperty(
        float, lambda self: self._circle_pos,
        set_circle_pos)
    intermediate_bg_color = pyqtProperty(
        QColor, lambda self: self._intermediate_bg_color,
        lambda self, col: setattr(self, '_intermediate_bg_color', col))

    def setDuration(self, duration: int):
        """
        Set the duration for the animation.
        :param duration: Duration in milliseconds.
        """
        self._animation_duration = duration

    def update_pos_color(self, checked=None):
        self._circle_pos = self.height() * (1.1 if checked else 0.1)
        if self.isChecked():
            self._intermediate_bg_color = self._active_color
        else:
            self._intermediate_bg_color = self._bg_color

    def start_transition(self, state):
        if not self._user_checked:
            self.update_pos_color(state)
            return
        for anim in [self.create_animation, self.create_bg_color_animation]:
            animation = anim(state)
            animation.start()
        self._user_checked = False

    def mousePressEvent(self, event):
        self._user_checked = True
        super().mousePressEvent(event)

    def create_animation(self, state):
        return self._create_common_animation(
            state, b'circle_pos', self.height() * 0.1, self.height() * 1.1)

    def create_bg_color_animation(self, state):
        return self._create_common_animation(
            state, b'intermediate_bg_color', self._bg_color, self._active_color)

    def _create_common_animation(self, state, prop, start_val, end_val):
        animation = QPropertyAnimation(self, prop, self)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.setDuration(self._animation_duration)
        animation.setStartValue(start_val if state else end_val)
        animation.setEndValue(end_val if state else start_val)
        return animation

    def showEvent(self, event):
        super().showEvent(event)
        self.update_pos_color(self.isChecked())

    def resizeEvent(self, event):
        self.update_pos_color(self.isChecked())

    def sizeHint(self):
        size = super().sizeHint()
        text_width = QFontMetrics(
            self.font()).boundingRect(self.text()).width()
        size.setWidth(int(self.height() * 2 + text_width * 1.075))
        return size

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        circle_color = QColor(
            self.disabled_color if not self.isEnabled() else self.circle_color)
        bg_color = QColor(
            self.disabled_color if not self.isEnabled() else
            self.intermediate_bg_color)
        text_color = QColor(
            self.disabled_color if not self.isEnabled() else self.text_color)

        bordersradius = self.height() / 2
        togglewidth = self.height() * 2
        togglemargin = self.height() * 0.3
        circlesize = self.height() * 0.8

        bg_path = QPainterPath()
        bg_path.addRoundedRect(
            0, 0, togglewidth, self.height(), bordersradius, bordersradius)
        painter.fillPath(bg_path, QBrush(bg_color))

        circle = QPainterPath()
        circle.addEllipse(
            self.circle_pos, self.height() * 0.1, circlesize, circlesize)
        painter.fillPath(circle, QBrush(circle_color))

        painter.setPen(QPen(QColor(text_color)))
        painter.setFont(self.font())
        text_rect = QRect(int(togglewidth + togglemargin), 0, self.width() -
                          int(togglewidth + togglemargin), self.height())
        text_rect.adjust(
            0, (self.height() - painter.fontMetrics().height()) // 2, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft |
                         Qt.AlignmentFlag.AlignVCenter, self.text())
        painter.end()


class DraggableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.file_path = None

    def setFilePath(self, file_path):
        self.file_path = file_path

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.startDrag(event)

    def startDrag(self, event):
        if self.file_path:
            mimeData = QMimeData()
            url = QUrl.fromLocalFile(self.file_path)
            mimeData.setUrls([url])
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec(Qt.DropAction.CopyAction)
            self.setStyleSheet("background-color: transparent")

class LabelButtonWidget(QWidget):
    def __init__(self, label_text, file_path, amount_path, highlight, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.label = DraggableLabel(self)
        self.label.setText(label_text)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setFilePath(file_path)
        if highlight: self.label.setStyleSheet("background-color:rgba(255, 255, 0, 0.4)")
        self.btn = QPushButton('+', self)
        self.btn.setFixedWidth(40)
        self.btn.setFixedHeight(80)
        self.btn.setFont(QFont('Pretendard JP', 20))
        from app.main_window import BetterCheeseUtil 
        if isinstance(parent, BetterCheeseUtil):
            image_setter_object = parent.remote_tab
        else:
            image_setter_object = parent
        if amount_path.endswith('.gif'):
            self.btn.clicked.connect(lambda checked=False,
                                            target=image_setter_object, 
                                            ap=amount_path, 
                                            fp=file_path: 
                                    [target.set_image(ap, fp.replace(".png", "_alt.png")), 
                                    self.label.setStyleSheet("background-color: transparent")])
        else:
            self.btn.clicked.connect(lambda checked=False,
                                            target=image_setter_object, 
                                            fp=file_path: 
                                    [target.set_image(fp, ""), 
                                    self.label.setStyleSheet("background-color: transparent")])
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.btn)
        self.setLayout(self.layout)


class TestPopup(QWidget):
    def __init__(self):
        super().__init__()
        instance_mock = types.SimpleNamespace()
        self.simulator = ChatSimulator(instance_mock)
        
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('채팅/후원 테스트')
        self.setGeometry(200, 200, 700, 400)
        self.setWindowIcon(QIcon(resource_path(r'.\resources\icon\icon_BCU.ico')))

        input_group = QGroupBox("입력 데이터")
        form_layout = QFormLayout()
        self.nickname_input = QLineEdit("테스트 유저")
        self.userid_input = QLineEdit("user_hash_123")
        self.tier_input = QSpinBox()
        self.tier_input.setRange(1, 2)
        self.sub_months_input = QSpinBox()
        self.sub_months_input.setRange(1, 12000)
        self.sub_months_input.setValue(6)
        self.sub_quantity_input = QSpinBox()
        self.sub_quantity_input.setRange(1, 10000)
        self.sub_quantity_input.setValue(10)
        self.receiver_nick_input = QLineEdit("받는사람 닉네임")
        self.receiver_id_input = QLineEdit("receiver_hash_456")
        self.selection_type_input = QComboBox()
        self.selection_type_input.addItems(["RANDOM", "MANUAL"])
        self.message_input = QLineEdit("안녕하세요. 테스트 메시지입니다.")
        self.cheese_amount_input = QSpinBox()
        self.cheese_amount_input.setRange(1, 100000000)
        self.cheese_amount_input.setValue(5000)
        self.mission_add_cheese_input = QSpinBox()
        self.mission_add_cheese_input.setRange(1, 100000000)
        self.mission_add_cheese_input.setValue(1000)
        self.mission_pnum_input = QSpinBox()
        self.mission_pnum_input.setRange(0, 1000)
        self.mission_pnum_input.setValue(5)
        self.mission_success_checkbox = QCheckBox()
        self.mission_success_checkbox.setChecked(True)

        form_layout.addRow(QLabel("닉네임:"), self.nickname_input)
        form_layout.addRow(QLabel("아이디:"), self.userid_input)
        form_layout.addRow(QLabel("구독 티어:"), self.tier_input)
        form_layout.addRow(QLabel("구독 개월 수:"), self.sub_months_input)
        form_layout.addRow(QLabel("구독 선물 개수:"), self.sub_quantity_input)
        form_layout.addRow(QLabel("구독 받는 사람 닉네임:"), self.receiver_nick_input)
        form_layout.addRow(QLabel("구독 받는 사람 ID:"), self.receiver_id_input)
        form_layout.addRow(QLabel("선물 선택 방식:"), self.selection_type_input)
        form_layout.addRow(QLabel("메시지 (영상/미션 제목):"), self.message_input)
        form_layout.addRow(QLabel("치즈 개수 (미션 총액):"), self.cheese_amount_input)
        form_layout.addRow(QLabel("미션 추가금:"), self.mission_add_cheese_input)
        form_layout.addRow(QLabel("미션 참가 인원:"), self.mission_pnum_input)
        form_layout.addRow(QLabel("미션 성공 여부:"), self.mission_success_checkbox)
        input_group.setLayout(form_layout)

        action_group = QGroupBox("테스트 실행")
        grid_layout = QGridLayout()
        self.btn_chat = QPushButton('일반 채팅')
        self.btn_sub = QPushButton('구독')
        self.btn_sub_gift = QPushButton('구독 선물')
        self.btn_donation = QPushButton('치즈 후원')
        self.btn_video_donation = QPushButton('영상 후원')
        self.btn_mission_pending = QPushButton('미션 요청')
        self.btn_mission_approved = QPushButton('미션 수락')
        self.btn_mission_rejected = QPushButton('미션 거부')
        self.btn_mission_update = QPushButton('미션 추가금')
        self.btn_mission_completed = QPushButton('미션 결과')

        grid_layout.addWidget(self.btn_chat, 0, 0)
        grid_layout.addWidget(self.btn_sub, 0, 1)
        grid_layout.addWidget(self.btn_sub_gift, 1, 0)
        grid_layout.addWidget(self.btn_donation, 1, 1)
        grid_layout.addWidget(self.btn_video_donation, 2, 0)
        grid_layout.addWidget(self.btn_mission_pending, 3, 0)
        grid_layout.addWidget(self.btn_mission_approved, 3, 1)
        grid_layout.addWidget(self.btn_mission_rejected, 4, 0)
        grid_layout.addWidget(self.btn_mission_update, 4, 1)
        grid_layout.addWidget(self.btn_mission_completed, 5, 0, 1, 2)
        action_group.setLayout(grid_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(input_group)
        main_layout.addWidget(action_group)
        self.setLayout(main_layout)

    def connect_signals(self):
        self.btn_chat.clicked.connect(self.run_chat_test)
        self.btn_sub.clicked.connect(self.run_subscription_test)
        self.btn_sub_gift.clicked.connect(self.run_subscription_gift_test)
        self.btn_donation.clicked.connect(self.run_donation_test)
        self.btn_video_donation.clicked.connect(self.run_video_donation_test)
        self.btn_mission_pending.clicked.connect(self.run_mission_pending_test)
        self.btn_mission_approved.clicked.connect(self.run_mission_approved_test)
        self.btn_mission_rejected.clicked.connect(self.run_mission_rejected_test)
        self.btn_mission_update.clicked.connect(self.run_mission_update_test)
        self.btn_mission_completed.clicked.connect(self.run_mission_completed_test)

    # --- 각 버튼에 연결될 테스트 실행 함수들 (입력 필드 값 사용) ---
    def run_chat_test(self):
        mock_message = types.SimpleNamespace(
            profile=types.SimpleNamespace(
                nickname=self.nickname_input.text(), 
                user_id_hash=self.userid_input.text()
            ),
            time=datetime.now() - timedelta(hours=9),
            content=self.message_input.text()
        )
        self.simulator.on_chat(mock_message)

    def run_subscription_test(self):
        mock_message = types.SimpleNamespace(
            profile=types.SimpleNamespace(
                nickname=self.nickname_input.text(), 
                user_id_hash=self.userid_input.text()
            ),
            time=datetime.now() - timedelta(hours=9),
            extras=types.SimpleNamespace(
                month=self.sub_months_input.value(), 
                tier_no=self.tier_input.value()
            ),
            content=self.message_input.text()
        )
        self.simulator.on_subscription(mock_message)
    
    def run_subscription_gift_test(self):
        mock_message = types.SimpleNamespace(
            profile=types.SimpleNamespace(nickname=self.nickname_input.text(), user_id_hash=self.userid_input.text()),
            time=datetime.now() - timedelta(hours=9),
            extras=types.SimpleNamespace(quantity=self.sub_quantity_input.value(), gift_tier_no=self.tier_input.value(), selection_type=self.selection_type_input.currentText(), receiver_user=self.receiver_nick_input.text(), receiver_user_id=self.receiver_id_input.text(), sender_user_id=self.userid_input.text(), sender_user_nick=self.nickname_input.text())
        )
        self.simulator.on_subscription_gift(mock_message)

    def run_donation_test(self):
        mock_message = types.SimpleNamespace(
            profile=types.SimpleNamespace(
                nickname=self.nickname_input.text(), 
                user_id_hash=self.userid_input.text()
            ),
            time=datetime.now() - timedelta(hours=9),
            extras=types.SimpleNamespace(
                is_anonymous=False, 
                pay_amount=self.cheese_amount_input.value(),
                donation_type='CHAT'
            ),
            content=self.message_input.text()
        )
        self.simulator.on_donation(mock_message)
        
    def run_anonymous_donation_test(self):
        mock_message = types.SimpleNamespace(
            profile=None, # 익명
            time=datetime.now() - timedelta(hours=9),
            extras=types.SimpleNamespace(
                is_anonymous=True, 
                pay_amount=self.cheese_amount_input.value(),
                donation_type='CHAT'
            ),
            content=self.message_input.text()
        )
        self.simulator.on_donation(mock_message)
    
    def run_video_donation_test(self):
        mock_message = types.SimpleNamespace(
            profile=types.SimpleNamespace(nickname=self.nickname_input.text(), user_id_hash=self.userid_input.text(), tier=self.tier_input.value()),
            time=datetime.now() - timedelta(hours=9),
            extras=types.SimpleNamespace(is_anonymous=False, pay_amount=self.cheese_amount_input.value(), donation_type='VIDEO'),
            content=self.message_input.text() # 영상 제목으로 사용
        )
        self.simulator.on_donation(mock_message)

    def run_mission_completed_test(self):
        mock_mission = types.SimpleNamespace(
            is_anonymous=False, nickname=self.nickname_input.text(), user_id_hash=self.userid_input.text(),
            total_pay_amount=self.cheese_amount_input.value(),
            participation_count=self.mission_pnum_input.value(),
            mission_text=self.message_input.text(),
            success=self.mission_success_checkbox.isChecked()
        )
        self.simulator.on_mission_completed(mock_mission)

    def run_mission_pending_test(self):
        mock_mission = types.SimpleNamespace(
            is_anonymous=False, nickname=self.nickname_input.text(), user_id_hash=self.userid_input.text(),
            total_pay_amount=self.cheese_amount_input.value(),
            mission_text=self.message_input.text()
        )
        self.simulator.on_mission_pending(mock_mission)
        
    def run_mission_approved_test(self):
        mock_mission = types.SimpleNamespace(
            is_anonymous=False, nickname=self.nickname_input.text(), user_id_hash=self.userid_input.text(),
            total_pay_amount=self.cheese_amount_input.value(),
            mission_text=self.message_input.text()
        )
        self.simulator.on_mission_approved(mock_mission)
    
    def run_mission_rejected_test(self):
        mock_mission = types.SimpleNamespace(
            is_anonymous=False, nickname=self.nickname_input.text(), user_id_hash=self.userid_input.text(),
            total_pay_amount=self.cheese_amount_input.value(),
            mission_text=self.message_input.text()
        )
        self.simulator.on_mission_rejected(mock_mission)
        
    def run_mission_update_test(self):
        mock_mission = types.SimpleNamespace(
            is_anonymous=False, nickname=self.nickname_input.text(), user_id_hash=self.userid_input.text(),
            pay_amount=self.mission_add_cheese_input.value(), # 추가금
            total_pay_amount=self.cheese_amount_input.value(), # 총액
            mission_text=self.message_input.text()
        )
        self.simulator.on_mission_update_cost(mock_mission)