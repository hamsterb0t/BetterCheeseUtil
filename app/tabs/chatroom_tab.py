from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QTextEdit, QLabel, QMessageBox)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import pyqtSlot, QUrl, QTimer
from app.constants import GLOBALFONTSIZE
from app.resources import resource_path
from app.ui_widgets import CustomWebEnginePage, TestPopup
from app.ui_chat_counter import ChatCounterWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage


class InterceptWebEnginePage(CustomWebEnginePage):
    def __init__(self, profile, parent=None, url_callback=None):
        super().__init__(profile, parent)
        self.url_callback = url_callback

    def createWindow(self, _type):
        page = QWebEnginePage(self.profile(), self)
        page.urlChanged.connect(self.on_url_changed)
        return page

    def on_url_changed(self, url):
        if self.url_callback:
            self.url_callback(url.toString())

class ChatroomTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        
        self.main_window = main_window

        self.chatroom_layout = QVBoxLayout()

        info_layout = QHBoxLayout()
        self.channel_label = QLabel("연결된 채널: (연결 안 됨)")
        self.channel_label.setFont(QFont('Pretendard JP', GLOBALFONTSIZE))
        info_layout.addWidget(self.channel_label)
        self.input_id_box_chat = QLineEdit() 
        info_layout.addWidget(self.input_id_box_chat)
        self.chatroom_layout.addLayout(info_layout)

        button_layout = QHBoxLayout()
        self.toggle_button_chat = QPushButton("채팅창 접속")
        self.toggle_button_chat.setCheckable(True)
        self.toggle_button_chat.toggled.connect(self.handle_chat_toggle)
        button_layout.addWidget(self.toggle_button_chat)

        self.chat_pop_up_button = QPushButton("  채팅창 팝업", self)
        self.chat_pop_up_button.clicked.connect(self.open_chat_popup)
        self.chat_pop_up_button.setIcon(QIcon(resource_path(r'.\resources\icon\popup.png')))
        button_layout.addWidget(self.chat_pop_up_button)

        self.chat_counter_button = QPushButton("채팅 통계 분석", self)
        self.chat_counter_button.clicked.connect(self.open_chat_counter)
        button_layout.addWidget(self.chat_counter_button)

        self.chatroom_layout.addLayout(button_layout)

        self.test_popup_button = QPushButton('채팅창 테스트', self)
        self.test_popup_button.clicked.connect(self.run_test_popup)
        self.chatroom_layout.addWidget(self.test_popup_button)

        self.test_overlay_button = QPushButton('오버레이 테스트', self)
        self.test_overlay_button.clicked.connect(self.run_test_overlay)
        self.chatroom_layout.addWidget(self.test_overlay_button)
        if not self.main_window.devmode_toggle.isChecked():
            self.test_overlay_button.hide()

        self.result_box_chat_temp = QTextEdit(self)
        self.result_box_chat_temp.hide()
        self.chatroom_signal = QTextEdit(self)
        self.chatroom_signal.hide()
        self.result_box_chat = QTextEdit(self)
        self.result_box_chat.setReadOnly(True)
        self.result_box_chat.setFont(QFont('Pretendard JP', GLOBALFONTSIZE-1))
        self.result_box_chat.setText(f"채팅창 접속 버튼을 누르면 API 인증 및 채팅창 접속을 시작합니다.\n설정 탭에서 프로그램 시작 시 자동 접속하도록 설정하실 수 있습니다.")
        self.chatroom_layout.addWidget(self.result_box_chat, 1)

        chat_input_layout = QHBoxLayout()

        self.chat_input = QLineEdit(self)
        self.chat_input.setPlaceholderText("채팅 메시지를 입력하세요.")
        self.chat_input.returnPressed.connect(lambda: self.send_chat_message(False))
        chat_input_layout.addWidget(self.chat_input)

        self.chat_send_and_pin_notice_button = QPushButton("공지등록", self)
        self.chat_send_and_pin_notice_button.clicked.connect(lambda: self.send_chat_message(True))
        chat_input_layout.addWidget(self.chat_send_and_pin_notice_button)

        self.chat_send_button = QPushButton("전송", self)
        self.chat_send_button.clicked.connect(lambda: self.send_chat_message(False))
        chat_input_layout.addWidget(self.chat_send_button)

        self.chatroom_layout.addLayout(chat_input_layout)

        self.login_browser = QWebEngineView()
        self.login_browser.setPage(CustomWebEnginePage(self.main_window.persistent_profile, self.login_browser))
        self.chatroom_layout.addWidget(self.login_browser, 2)
        self.login_browser.hide()

        self.error_box_chat = QTextEdit(self)
        self.error_box_chat.setReadOnly(True)
        self.error_box_chat.setMaximumHeight(100)
        self.error_box_chat.setFont(QFont('Pretendard JP', GLOBALFONTSIZE-1))
        self.error_box_chat.setText("에러 로그 입니다.")
        self.error_box_chat.hide()
        self.chatroom_layout.addWidget(self.error_box_chat)
        
        self.error_hide_chat = QPushButton("에러창 가리기")
        self.error_hide_chat.clicked.connect(lambda: (self.error_hide_chat.hide(), self.error_box_chat.hide()))
        self.error_hide_chat.hide()
        self.chatroom_layout.addWidget(self.error_hide_chat)

        self.chatroom_chzzk_browser = QWebEngineView(self)
        self.chatroom_chzzk_browser.setPage(InterceptWebEnginePage(self.main_window.persistent_profile, self.chatroom_chzzk_browser, self.handle_popup_url))
        settings = self.chatroom_chzzk_browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True) # [NEW]
        # 브라우저를 숨기지 않고 화면 밖으로 이동시킴 (스크립트 동작 보장)
        self.chatroom_chzzk_browser.setGeometry(-2000, -2000, 1280, 800)
        self.setLayout(self.chatroom_layout)

        self.load_settings_from_main()
        
        if not self.main_window.devmode_toggle.isChecked():
            self.test_popup_button.hide()
            
        self.prediction_scraper_injected = False # Prevent duplicate injection

    def load_settings_from_main(self):
        """메인 윈도우의 설정 값을 이 탭의 위젯에 적용하고, 위젯 참조를 교체합니다."""
        mw = self.main_window
        self.input_id_box_chat.setText(mw.input_id_box_chat.text())
        self.chatroom_chzzk_browser.setUrl(QUrl(f"https://chzzk.naver.com/live/{self.input_id_box_chat.text()}/chat"))
    
    ##### 채팅창 탭 관련 함수 #####
    
    def open_chat_popup(self):
        self.main_window.open_chat()

    def open_chat_counter(self):
        self.chat_counter_window = ChatCounterWindow(self.main_window)
        self.chat_counter_window.show()

    def send_chat_message(self, is_pin_notice):
        message = self.chat_input.text()
        if message and hasattr(self.main_window, 'chatroom_connector_instance'):
            try:
                self.main_window.chatroom_connector_instance.send_chat(message, is_pin_notice)
            except Exception as e:
                print(f"Error sending chat message: {e}")
            self.chat_input.clear()
    
    def send_chat_message_connected(self):
        message = "[BCU] 채팅 연결됨!"
        if message and hasattr(self.main_window, 'chatroom_connector_instance'):
            try:
                self.main_window.chatroom_connector_instance.send_chat(message, False)
            except Exception as e:
                print(f"Error sending chat message: {e}")

    def run_test_popup(self):
        self.test_popup = TestPopup()
        self.test_popup.simulator.test_message.connect(self.main_window.message)
        self.test_popup.show()

    def run_test_overlay(self):
        from app.ui_widgets import TestOverlayDialog
        if not hasattr(self, 'test_overlay_dialog') or self.test_overlay_dialog is None:
             self.test_overlay_dialog = TestOverlayDialog(self.main_window.persistent_profile)
        
        self.test_overlay_dialog.show()
        self.test_overlay_dialog.activateWindow()
    
    def chatroom_get_popup_url(self):
        self.chatroom_chzzk_browser.setUrl(QUrl(f"https://chzzk.naver.com/live/{self.input_id_box_chat.text()}/chat"))
        js_file_path = resource_path(r'.\resources\script\chatroom_get_popup.js')
        with open(js_file_path, 'r', encoding='utf-8') as file:
            script = file.read()
        QTimer.singleShot(5000, lambda: self.chatroom_chzzk_browser.page().runJavaScript(script))
    
    def handle_popup_url(self, url):
        print(f"Captured Popup URL: {url}")
        self.main_window.userProfileUrl = url.split("/")[4]
        self.chatroom_chzzk_browser.setUrl(QUrl(f"https://chzzk.naver.com/live/{self.input_id_box_chat.text()}/chat"))

    def inject_prediction_scraper(self, success=True):
        """Injects the comprehensive prediction scraper (AutoPredictionMaster) [Manual Trigger]"""
        print(f"[ChatroomTab] inject_prediction_scraper called.")
        
        current_url = self.chatroom_chzzk_browser.url().toString()
        if "chzzk.naver.com/live" not in current_url: 
            print("[ChatroomTab] URL does not match target. Skipping injection.")
            return

        print("[ChatroomTab] Injecting AutoPredictionMaster V6 Scraper...")
        
        js_code = """
        (function autoPredictionMasterV6() {
            // [Duplicate Check - window level]
            if (window.bcu_prediction_scraper_running) {
                console.log("[BCU] Scraper already running. Skipping.");
                return;
            }
            window.bcu_prediction_scraper_running = true;

            // 1. 선택자 정의 (Robust Selectors)
            const SELECTORS = {
                triggerBtn: '[class*="live_chatting_fixed_prediction_title__"]',
                bannerStatus: '[class*="live_chatting_fixed_prediction_status_text__"]',
                popupContainer: '[class*="live_chatting_popup_prediction_container__"]',
                popupTitle: 'strong[class*="live_chatting_popup_prediction_title__"]', // [Fixed] Explicitly target strong tag to avoid containers
                timer: '[class*="live_chatting_popup_prediction_timer__"]',
                refreshBtn: '[class*="live_chatting_popup_prediction_refresh_button__"]',
                winnerItem: '[class*="live_chatting_popup_prediction_winner__"]',
                optionTitle: '[class*="live_chatting_popup_prediction_option_title__"]',
                optionPercent: '[class*="live_chatting_popup_prediction_percentage__"]',
                optionItem: '[class*="live_chatting_popup_prediction_option__"]',
                popupCloseBtn: '[class*="popup_button__"]' // [Added] Close button selector
            };

            let isWinnerPrinted = false; 
            
            // API Send Helper
            const sendUpdate = (payload) => {
                fetch('http://127.0.0.1:5000/update_prediction_stats', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                }).catch(err => console.error("Stats update failed:", err));
            };

            const sendWinner = (winnerName) => {
                fetch('http://127.0.0.1:5000/update_prediction_winner', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ winner: winnerName })
                }).catch(err => console.error("Winner update failed:", err));
            };

            console.clear();
            console.log("%c[치지직 승부예측 봇 V6] 가동 시작", "color: #fff; background: #000; font-size: 14px; padding: 4px; font-weight: bold;");

            // 통합 메인 루프 (1초마다 실행)
            setInterval(() => {
                try {
                    const triggerBtn = document.querySelector(SELECTORS.triggerBtn);
                    const popup = document.querySelector(SELECTORS.popupContainer);
                    
                    // [Result Phase Check] - Moved Logic Down
                    // const bannerText ... (removed duplicate)
                    // const isResultPhase ... (removed duplicate)

                    // 1. 배너 자체가 없는 경우 (대기)
                    if (!triggerBtn) {
                        isWinnerPrinted = false; 
                        sendUpdate({ state: 'WAITING' });
                        return; 
                    }

                    // 2. 팝업이 닫혀있으면 엽니다.
                    if (!popup) {
                        triggerBtn.click();
                        return; 
                    }

                    // 3. 현재 팝업의 데이터 읽기
                    // [Fixed] Use innerText of the strong tag directly if span is missing, and strip '새로고침'
                    let title = document.querySelector(SELECTORS.popupTitle)?.innerText.trim() || "제목없음";
                    title = title.replace(/새로고침/g, '').trim();
                    
                    // [Refined] Remove text after '후' (e.g. "35분 21초 후 참여 마감" -> "35분 21초")
                    let timerText = document.querySelector(SELECTORS.timer)?.innerText.replace(/\\n/g, ' ').trim() || "";
                    timerText = timerText.replace(/후.*$/, '').trim();

                    // [Moved UP & Enhanced] Determine Global Winner Name first
                    let globalWinnerName = null;
                    const globalWinnerEl = document.querySelector(SELECTORS.winnerItem);
                    if (globalWinnerEl) {
                        globalWinnerName = globalWinnerEl.querySelector(SELECTORS.optionTitle)?.innerText.trim();
                    } else {
                        // Fallback: Check for checked input with winner class logic
                        const checkedInput = document.querySelector('input[name="prediction"]:checked');
                        if (checkedInput) {
                            const parentLabel = checkedInput.closest('label');
                            if (parentLabel && parentLabel.className.includes('prediction_winner')) { 
                                globalWinnerName = parentLabel.querySelector(SELECTORS.optionTitle)?.innerText.trim();
                            }
                        }
                    }

                    // [Stale Check Strategy]
                    // If Banner says 'Result' but no Winner found for 3 seconds -> Force Re-open Popup
                    const bannerTextForCheck = document.querySelector(SELECTORS.bannerStatus)?.innerText || "";
                    if ((bannerTextForCheck.includes("결과") || bannerTextForCheck.includes("확인하기")) && !globalWinnerName) {
                        if (typeof window.staleWinnerCount === 'undefined') window.staleWinnerCount = 0;
                        window.staleWinnerCount++;
                        console.log(`[BCU] Result Phase but no winner... (${window.staleWinnerCount}/3)`);
                        
                        if (window.staleWinnerCount > 3) {
                             console.log("[BCU] Stale Result Detected. Forcing Popup Close/Re-open.");
                             
                             const closeBtn = document.querySelector(SELECTORS.popupContainer).childNodes[2].childNodes[0]
                             if (closeBtn) closeBtn.click();
                             else triggerBtn.click(); // Fallback
                             
                             window.staleWinnerCount = 0;
                             return; // Skip this loop, next loop will re-open
                        }
                    } else {
                        window.staleWinnerCount = 0;
                    }
                    // [Result Phase Check] - Check banner text for '결과' OR if we found a winner
                    const bannerText = document.querySelector(SELECTORS.bannerStatus)?.innerText || "";
                    const isResultPhase = bannerText.includes("결과") || bannerText.includes("확인하기") || !!globalWinnerName;
                    
                    const items = [];
                    const itemEls = document.querySelectorAll(SELECTORS.optionItem);
                    itemEls.forEach(el => {
                        const name = el.querySelector(SELECTORS.optionTitle)?.innerText.trim();
                        const percent = el.querySelector(SELECTORS.optionPercent)?.innerText.trim();
                        
                        // Check for winner class directly OR match with global winner name
                        let isWinner = el.className.includes("live_chatting_popup_prediction_winner__");
                        if (!isWinner && globalWinnerName && name === globalWinnerName) {
                            isWinner = true;
                        }
                        
                        if (name) items.push({ 'name': name, 'percent': percent, 'isWinner': isWinner });
                    });

                    // 4. 상태별 처리
                    
                    // Helper for Refresh
                    const tryRefresh = () => {
                        const refreshBtn = document.querySelector(SELECTORS.refreshBtn);
                        if (refreshBtn) refreshBtn.click();
                    };

                    // 4. 상태별 처리
                    
                    // [상태 A] 결과 발표 (우선순위 높음)
                    if (isResultPhase) {
                        // Continuously send data during result phase so overlay stays populated
                        sendUpdate({
                            state: 'RESULT', 
                            title: title, 
                            items: items,
                            timer: '' // Hide timer
                        });

                        const winnerEl = document.querySelector(SELECTORS.winnerItem);
                        if (winnerEl) {
                            if (!isWinnerPrinted) {
                                const winnerName = winnerEl.querySelector(SELECTORS.optionTitle)?.innerText.trim();
                                console.log(`%c🎉 [결과] 우승: ${winnerName}`, "color: yellow; background: #ff0055; font-size: 18px; padding: 8px; font-weight: bold;");
                                sendWinner(winnerName);
                                isWinnerPrinted = true; 
                            }
                        } else {
                             // Fallback: If no winner element found despite Result Phase, try to find checked input
                             const checkedInput = document.querySelector('input[name="prediction"]:checked');
                             if (checkedInput && !isWinnerPrinted) {
                                  const parentLabel = checkedInput.closest('label');
                                  if (parentLabel && parentLabel.classList.contains('live_chatting_popup_prediction_winner__vdCPq')) { // Winner class check
                                      const winnerName = parentLabel.querySelector(SELECTORS.optionTitle)?.innerText.trim();
                                      if (winnerName) {
                                          sendWinner(winnerName);
                                          isWinnerPrinted = true;
                                      }
                                  }
                             }
                        }
                        
                        // [CRITICAL] Try refresh if winner not found yet, or just to keep data fresh
                        tryRefresh();
                        return;
                    }

                    // [상태 B] 참여 마감 (Only if NOT Result Phase)
                    if (timerText.includes('마감') && !timerText.includes('후')) {
                         // Send items even if closed, but hide timer
                         sendUpdate({ 
                             state: 'CLOSED',
                             title: title,
                             timer: '', 
                             items: items 
                         });
                         // [CRITICAL] Try refresh to catch transition to Result
                         tryRefresh();
                         return;
                    }

                    // [상태 C] 진행 중
                    if (items.length > 0) {
                        console.clear(); 
                        console.log(`%c🔴 실시간 | ${title} | ${timerText}`, "color: #00ffa3; font-weight: bold;");
                        sendUpdate({
                            state: 'ONGOING',
                            title: title,
                            timer: timerText,
                            items: items
                        });
                    }

                    // 5. 다음 데이터를 위해 새로고침 클릭
                    tryRefresh();

                } catch (err) {
                    console.warn("봇 실행 중 오류:", err);
                }
            }, 1000);

        })();
        """
        self.chatroom_chzzk_browser.page().runJavaScript(js_code)



    ##### 시그널 핸들러 / 슬롯 #####

    @pyqtSlot(str, str)
    def update_nicknames_labels(self, api_user_nick, channel_nick):
        """Chatroom_Connector에서 받은 닉네임 정보로 UI 라벨을 업데이트합니다."""
        self.channel_label.setText(f"연결된 채널: {channel_nick}")
        if self.main_window.chatroom_connector_instance:
            self.input_id_box_chat.setText(self.main_window.chatroom_connector_instance.streamer_ID)
            print(f"update_nicknames_labels: streamer_ID = {self.input_id_box_chat.text()}")

    @pyqtSlot(str)
    def start_oauth_server(self, state):
        """임시 OAuth 서버를 시작합니다."""
        self.main_window.start_oauth_server(state)

    @pyqtSlot()
    def stop_oauth_server(self):
        """임시 OAuth 서버를 중지합니다."""
        self.main_window.stop_oauth_server()
    
    @pyqtSlot()
    def on_server_stopped(self):
        """서버 스레드 종료 시 정리 작업"""
        self.main_window.on_server_stopped()

    @pyqtSlot(str, str)
    def on_code_received(self, code, state):
        """임시 서버로부터 인증 코드를 수신"""
        self.append_result_chat("인증 코드 수신됨. 토큰 교환 시도...")
        self.hide_login_browser() # 브라우저 숨김
        
        self.stop_oauth_server()
        
        if self.main_window.chatroom_connector_instance:
            self.main_window.chatroom_connector_instance.exchange_code_for_token_threadsafe(code, state)

    @pyqtSlot(str, str)
    def prompt_manual_login(self, auth_url, oauth_state):
        """Chatroom_Connector가 수동 로그인을 요청하면 호출됩니다."""
        self.result_box_chat.append("❗네이버/치지직 로그인이 필요합니다❗\n하단 브라우저에서 로그인을 완료하고 권한을 승인해주세요.\n(로그인 상태 유지 체크 권장)")
        self.show_login_browser()
        self.login_browser.setUrl(QUrl(auth_url))

    @pyqtSlot(bool)
    def handle_chat_toggle(self, checked):
        """채팅 접속/해제 버튼 토글 상태 변경 시 호출되는 슬롯"""
        if checked:
            client_id = self.main_window.chzzk_api_client_id.text()
            client_secret = self.main_window.chzzk_api_client_secret.text()

            if not client_id or not client_secret:
                self.result_box_chat.setText("Client ID와 Secret을 설정 탭에서 입력해주세요.")
                QMessageBox.warning(self, "API 키 필요", "치지직 API 사용을 위한 Client ID와 Client Secret 키가 필요합니다.\n설정 탭에서 입력해주세요.")
                self.main_window.tabs.setCurrentWidget(self.main_window.tab_widgets['설정'])
                self.toggle_button_chat.setChecked(False)
                return

            self.toggle_button_chat.setText("채팅창 접속 해제")
            self.main_window.login_reset_button.setDisabled(True)

            if self.main_window.chatroom_connector_instance:
                self.main_window.chatroom_connector_instance.start_async_operations(self.main_window)
            else:
                self.result_box_chat.setText("오류: Chatroom Connector 초기화 실패.")
                self.toggle_button_chat.setChecked(False)

        else: 
            self.toggle_button_chat.setText("채팅창 접속")
            self.main_window.login_reset_button.setEnabled(True)
            self.result_box_chat.setText("채팅창 접속 버튼을 누르면 채팅창에 접속합니다.")
            self.chatroom_signal.setText("")

            if self.main_window.chatroom_connector_instance:
                self.main_window.chatroom_connector_instance.stop()
            
            self.login_browser.hide()
            self.stop_oauth_server()

    @pyqtSlot(str)
    def on_login_failure(self, error_message):
        """(슬롯) Chatroom_Connector에서 인증 실패 시 호출됨"""
        self.result_box_chat.append(f"❗ 인증 실패: {error_message}")
        if self.toggle_button_chat.isChecked():
            self.toggle_button_chat.setChecked(False)
        self.stop_oauth_server()
        
    @pyqtSlot()
    def on_login_success(self):
        """(슬롯) Chatroom_Connector에서 인증 성공 시 호출됨"""
        self.result_box_chat.append("✅ 네이버/치지직 인증 성공")
        self.hide_login_browser()

    @pyqtSlot()
    def handle_reconnect_signal(self):
        """(슬롯) Chatroom_Connector에서 재연결 요청 시 호출됨"""
        self.result_box_chat.append("❗ 연결 문제 감지됨. 5초 후 재연결 시도...")
        if self.toggle_button_chat.isChecked():
             self.toggle_button_chat.setChecked(False)
             QTimer.singleShot(1000, lambda: QTimer.singleShot(4000, self._attempt_reconnect))
        else:
             QTimer.singleShot(5000, self._attempt_reconnect)

    def _attempt_reconnect(self):
        """Attempts to reconnect by simulating a button press."""
        if not self.toggle_button_chat.isChecked() and not self.main_window.chatroom_connector_instance.is_running:
            self.result_box_chat.append("🔄 재연결 시도...")
            self.toggle_button_chat.setChecked(True)
        else:
            print("Reconnect aborted, connector might still be running/stopping.")

    @pyqtSlot()
    def show_login_browser(self):
        """로그인 브라우저를 표시"""
        self.login_browser.show()
        self.result_box_chat.setMaximumHeight(150)

    @pyqtSlot()
    def hide_login_browser(self):
        """로그인 브라우저를 숨김"""
        self.login_browser.hide()
        self.result_box_chat.setMaximumHeight(2000)

    # --- 커넥터 시그널을 직접 받을 슬롯 ---
    
    @pyqtSlot(str)
    def append_result_chat(self, text):
        list = self.result_box_chat.toPlainText().split("\n")
        chat_result = ""
        idx = 0
        for i in list:
            idx += 1
            if len(list) >= 50 and idx == 1: continue
            chat_result += (i + "\n")
        chat_result += text
        self.result_box_chat.setText(chat_result)
        self.result_box_chat.verticalScrollBar().setValue(self.result_box_chat.verticalScrollBar().maximum())

    @pyqtSlot(str)
    def set_text_result_chat(self, text):
        self.result_box_chat.setText(text)
        self.result_box_chat.verticalScrollBar().setValue(self.result_box_chat.verticalScrollBar().maximum())