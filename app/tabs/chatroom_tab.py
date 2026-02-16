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
        
        # [NEW] 브라우저 로드 완료 시 승부예측 스크래퍼 자동 시작
        self.chatroom_chzzk_browser.loadFinished.connect(self._on_chatroom_browser_loaded)
        
        # [NEW] 10분마다 userProfileUrl 갱신 타이머
        self.profile_refresh_timer = QTimer(self)
        self.profile_refresh_timer.timeout.connect(self._refresh_user_profile_url)
        self.profile_refresh_timer.start(10 * 60 * 1000)  # 10분 = 600,000ms
        
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
        QTimer.singleShot(10000, lambda: self.chatroom_chzzk_browser.page().runJavaScript(script))
    
    def handle_popup_url(self, url):
        print(f"Captured Popup URL: {url}")
        self.main_window.userProfileUrl = url.split("/")[4]
        self.chatroom_chzzk_browser.setUrl(QUrl(f"https://chzzk.naver.com/live/{self.input_id_box_chat.text()}/chat"))

    def _on_chatroom_browser_loaded(self, success):
        """브라우저 로드 완료 시 호출 - 승부예측 스크래퍼 자동 시작 및 userProfileUrl 갱신"""
        if success:
            current_url = self.chatroom_chzzk_browser.url().toString()
            if "chzzk.naver.com/live" in current_url and "/chat" in current_url:
                print("[ChatroomTab] 채팅창 로드 완료 - 승부예측 스크래퍼 자동 주입...")
                # 페이지가 완전히 로드된 후 1.5초 뒤에 스크래퍼 주입
                QTimer.singleShot(1500, self.inject_prediction_scraper)
                
                # [NEW] 처음 로드 시에도 userProfileUrl 갱신
                print("[ChatroomTab] 채팅창 로드 완료 - userProfileUrl 갱신 스크립트 실행...")
                QTimer.singleShot(3000, self._refresh_user_profile_url)
    
    def _refresh_user_profile_url(self):
        """10분마다 userProfileUrl 갱신"""
        print("[ChatroomTab] 10분 주기 - userProfileUrl 갱신 시작...")
        js_file_path = resource_path(r'.\resources\script\chatroom_get_popup.js')
        try:
            with open(js_file_path, 'r', encoding='utf-8') as file:
                script = file.read()
            self.chatroom_chzzk_browser.page().runJavaScript(script)
            print("[ChatroomTab] userProfileUrl 갱신 스크립트 실행됨")
        except Exception as e:
            print(f"[ChatroomTab] userProfileUrl 갱신 실패: {e}")

    def inject_prediction_scraper(self, success=True):
        """Injects the comprehensive prediction scraper (AutoPredictionMaster) [Manual Trigger]"""
        print(f"[ChatroomTab] inject_prediction_scraper called.")
        
        current_url = self.chatroom_chzzk_browser.url().toString()
        if "chzzk.naver.com/live" not in current_url: 
            print("[ChatroomTab] URL does not match target. Skipping injection.")
            return

        print("[ChatroomTab] Injecting AutoPredictionMaster V6 Scraper...")
        
        js_code = """
        (function autoPredictionMasterV7() {
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
                popupTitle: 'strong[class*="live_chatting_popup_prediction_title__"]', 
                timer: '[class*="live_chatting_popup_prediction_timer__"]',
                refreshBtn: '[class*="live_chatting_popup_prediction_refresh_button__"]',
                winnerItem: '[class*="live_chatting_popup_prediction_winner__"]',
                optionTitle: '[class*="live_chatting_popup_prediction_option_title__"]',
                optionPercent: '[class*="live_chatting_popup_prediction_percentage__"]',
                optionItem: '[class*="live_chatting_popup_prediction_option__"]',
                popupCloseBtn: '[class*="popup_button__"]',
                cancelledMessage: '[class*="live_chatting_prediction_message_description__"]',
                chatListItems: '[class*="live_chatting_list_item__"]'
            };

            let isWinnerPrinted = false;
            let previousState = null; 
            let closedStateRefreshDone = false;
            let isCancelledSent = false; // [NEW] 취소 상태 전송 여부
            let lastPayloadStr = ""; // [NEW] Change detection
            
            // [NEW] CLOSED 상태에서 퍼센트 변화 감시용 변수
            let closedStateStartTime = null; // CLOSED 상태 진입 시간
            let closedStateMonitoringActive = false; // 모니터링 활성화 여부
            let lastPercentValues = null; // 마지막 퍼센트 값 저장
            let popupToggleInterval = null; // 팝업 토글 인터벌
            const CLOSED_MONITORING_DURATION = 60000; // 1분간 모니터링
            const POPUP_TOGGLE_INTERVAL = 5000; // 5초마다 팝업 토글

            // API Send Helper
            const sendUpdate = (payload) => {
                const currentStr = JSON.stringify(payload);
                if (currentStr === lastPayloadStr) return; // Skip duplicates

                lastPayloadStr = currentStr;
                
                // Log significant changes
                if (payload.state === 'CLOSED') {
                     console.log("[BCU] CLOSED state update detected (Percentages changed).");
                }

                fetch('http://127.0.0.1:5000/update_prediction_stats', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: currentStr
                }).catch(err => console.error("Stats update failed:", err));
            };

            const sendWinner = (winnerName) => {
                fetch('http://127.0.0.1:5000/update_prediction_winner', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ winner: winnerName })
                }).catch(err => console.error("Winner update failed:", err));
            };

            // [NEW] 승부예측 취소 전송 함수
            const sendCancelled = () => {
                if (isCancelledSent) return;
                isCancelledSent = true;
                console.log("%c[BCU] 승부예측 취소 감지됨! 5분 쿨타임 시작...", "color: #ff6b6b; font-weight: bold;");
                
                fetch('http://127.0.0.1:5000/prediction_cancelled', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ cancelled: true })
                }).catch(err => console.error("Cancelled notification failed:", err));
            };

            // [NEW] Robust Cancellation Check
            const checkCancellation = () => {
                // 1. Precise Class Check
                const cancelledMsgs = document.querySelectorAll(SELECTORS.cancelledMessage);
                for (const msg of cancelledMsgs) {
                    if (msg.textContent && msg.textContent.includes('예측 취소')) return true;
                }
                
                // 2. Broad Text Search in recent chat items
                // Look for items containing both "승부예측" and "취소"
                const chatItems = document.querySelectorAll(SELECTORS.chatListItems);
                // Check only last 10 items to save performance
                const startIdx = Math.max(0, chatItems.length - 10);
                for (let i = startIdx; i < chatItems.length; i++) {
                    const text = chatItems[i].innerText || "";
                    if (text.includes('승부예측') && text.includes('취소')) {
                         return true;
                    }
                }
                return false;
            };

            console.clear();
            console.log("%c[치지직 승부예측 봇 V7] 가동 시작 (변화 감지 모드)", "color: #fff; background: #000; font-size: 14px; padding: 4px; font-weight: bold;");

            // 통합 메인 루프 (1초마다 실행)
            setInterval(() => {
                try {
                    const triggerBtn = document.querySelector(SELECTORS.triggerBtn);
                    const popup = document.querySelector(SELECTORS.popupContainer);
                    
                    // [NEW] 0. 채팅창에서 '예측 취소' 메시지 감지
                    if (checkCancellation()) {
                        sendCancelled();
                        // [FIX] If cancelled, do NOT proceed to send "ONGOING". 
                        // We assume cancellation means we should stop tracking the "result" or "ongoing" part for this iteration.
                        return; 
                    }

                    // 1. 배너 자체가 없는 경우 (대기)
                    if (!triggerBtn) {
                        // [NEW] State Transition Check: ONGOING/CLOSED -> WAITING (No Result) implies Cancellation
                        // If we were ONGOING or CLOSED and suddenly the banner is gone (WAITING) and we didn't go through RESULT...
                        // It's likely a cancellation.
                        if (previousState === 'ONGOING' || previousState === 'CLOSED') {
                             console.log("%c[BCU] " + previousState + " -> WAITING transition detected. Inferred Cancellation.", "color: #ff6b6b; font-weight: bold;");
                             sendCancelled();
                        }
                        
                        previousState = 'WAITING';
                        isWinnerPrinted = false;
                        isCancelledSent = false; // [FIX] Reset flag on WAITING so next cancellation can be detected
                        sendUpdate({ state: 'WAITING' });
                        return; 
                    }

                    // 2. 팝업이 닫혀있으면 엽니다.
                    if (!popup) {
                        triggerBtn.click();
                        return; 
                    }

                    // 3. 현재 팝업의 데이터 읽기
                    let title = document.querySelector(SELECTORS.popupTitle)?.innerText.trim() || "제목없음";
                    title = title.replace(/새로고침/g, '').trim();
                    
                    // [NEW] Conflict Check: Banner shows "진행중" but Popup shows OLD result
                    // If banner says "진행" but popup has winner/dimmed elements, close popup.
                    const bannerTextCheck = document.querySelector(SELECTORS.bannerStatus)?.innerText || "";
                    
                    if (popup && bannerTextCheck.includes("진행")) {
                        // Check if popup is showing a result (has winner element or dimmed options)
                        const popupHasWinner = popup.querySelector('[class*="prediction_winner__"]') !== null;
                        const popupHasDimmed = popup.querySelector('[class*="prediction_dimmed__"]') !== null;
                        const popupIsResult = popupHasWinner || popupHasDimmed;
                        
                        // Banner says "진행중" but popup shows result -> new prediction started, close old result
                        if (popupIsResult) {
                             console.log("[BCU] Banner shows '진행중' but popup shows result state. Closing old result popup.");
                             const closeBtn = popup.querySelector('[class*="popup_action__"] button') || popup.childNodes[2]?.childNodes[0];
                             if (closeBtn) {
                                 closeBtn.click();
                                 return;
                             }
                        }
                    }
                    
                    let timerText = document.querySelector(SELECTORS.timer)?.innerText.replace(/\\n/g, ' ').trim() || "";
                    timerText = timerText.replace(/후.*$/, '').trim();

                    // [Winner Check]
                    let globalWinnerName = null;
                    const globalWinnerEl = document.querySelector(SELECTORS.winnerItem);
                    if (globalWinnerEl) {
                        globalWinnerName = globalWinnerEl.querySelector(SELECTORS.optionTitle)?.innerText.trim();
                    } else {
                        const checkedInput = document.querySelector('input[name="prediction"]:checked');
                        if (checkedInput) {
                            const parentLabel = checkedInput.closest('label');
                            if (parentLabel && parentLabel.className.includes('prediction_winner')) { 
                                globalWinnerName = parentLabel.querySelector(SELECTORS.optionTitle)?.innerText.trim();
                            }
                        }
                    }

                    // [Stale Check Strategy]
                    const bannerTextForCheck = document.querySelector(SELECTORS.bannerStatus)?.innerText || "";
                    if ((bannerTextForCheck.includes("결과") || bannerTextForCheck.includes("확인하기")) && !globalWinnerName) {
                        console.log("[BCU] Result Phase but no winner - Forcing Popup Close/Re-open immediately.");
                        const closeBtn = document.querySelector(SELECTORS.popupContainer)?.childNodes[2]?.childNodes[0];
                        if (closeBtn) closeBtn.click();
                        else triggerBtn.click(); 
                        return; 
                    }

                    const bannerText = document.querySelector(SELECTORS.bannerStatus)?.innerText || "";
                    const isResultPhase = bannerText.includes("결과") || bannerText.includes("확인하기") || !!globalWinnerName;
                    
                    const items = [];
                    const itemEls = document.querySelectorAll(SELECTORS.optionItem);
                    itemEls.forEach(el => {
                        const name = el.querySelector(SELECTORS.optionTitle)?.innerText.trim();
                        const percent = el.querySelector(SELECTORS.optionPercent)?.innerText.trim();
                        
                        let isWinner = el.className.includes("live_chatting_popup_prediction_winner__");
                        if (!isWinner && globalWinnerName && name === globalWinnerName) {
                            isWinner = true;
                        }
                        
                        if (name) items.push({ 'name': name, 'percent': percent, 'isWinner': isWinner });
                    });

                    // Helper for Refresh
                    const tryRefresh = () => {
                        const refreshBtn = document.querySelector(SELECTORS.refreshBtn);
                        if (refreshBtn) refreshBtn.click();
                    };

                    // 4. 상태별 처리
                    
                    // [상태 A] 결과 발표
                    if (isResultPhase) {
                        previousState = 'RESULT'; // [NEW] Track Result State
                        
                        sendUpdate({
                            state: 'RESULT', 
                            title: title, 
                            items: items,
                            timer: '' 
                        });

                        if (globalWinnerName && !isWinnerPrinted) {
                            console.log(`%c🎉 [결과] 우승: ${globalWinnerName}`, "color: yellow; background: #ff0055; font-size: 18px; padding: 8px; font-weight: bold;");
                            sendWinner(globalWinnerName);
                            isWinnerPrinted = true; 
                        }
                        
                        tryRefresh();
                        return;
                    }

                    // [상태 B] 참여 마감 (CLOSED) - 결과 대기중
                    if (timerText.includes('마감') && !timerText.includes('후')) {
                         // [NEW] CLOSED 상태 처음 진입 시 모니터링 시작
                         if (previousState === 'ONGOING' || previousState === null) {
                             if (previousState === 'ONGOING') {
                                 console.log("%c[BCU] 상태 전환 감지: 진행중 -> 결과 대기중. 1분간 퍼센트 변화 감시 시작...", "color: #ff9900; font-weight: bold;");
                             }
                             
                             // 모니터링 초기화
                             closedStateStartTime = Date.now();
                             closedStateMonitoringActive = true;
                             lastPercentValues = items.map(i => i.percent).join(',');
                             
                             // 기존 인터벌 정리
                             if (popupToggleInterval) {
                                 clearInterval(popupToggleInterval);
                             }
                             
                             // 5초마다 팝업 닫았다 열기 인터벌 설정
                             popupToggleInterval = setInterval(() => {
                                 if (!closedStateMonitoringActive) {
                                     clearInterval(popupToggleInterval);
                                     return;
                                 }
                                 
                                 // 1분 경과 체크
                                 if (Date.now() - closedStateStartTime > CLOSED_MONITORING_DURATION) {
                                     console.log("%c[BCU] 1분 경과 - 퍼센트 변화 감시 종료", "color: #00ff00; font-weight: bold;");
                                     closedStateMonitoringActive = false;
                                     clearInterval(popupToggleInterval);
                                     return;
                                 }
                                 
                                 // 팝업 닫기
                                 const popup = document.querySelector(SELECTORS.popupContainer);
                                 if (popup) {
                                     const closeBtn = popup.querySelector('[class*="popup_button__"]') || popup.childNodes[2]?.childNodes[0];
                                     if (closeBtn) {
                                         console.log("[BCU] 퍼센트 갱신을 위해 팝업 닫는 중...");
                                         closeBtn.click();
                                     }
                                 }
                             }, POPUP_TOGGLE_INTERVAL);
                         }
                         
                         previousState = 'CLOSED';
                         
                         // [NEW] 퍼센트 변화 감지 및 로그
                         const currentPercentValues = items.map(i => i.percent).join(',');
                         if (closedStateMonitoringActive && lastPercentValues !== currentPercentValues) {
                             console.log("%c[BCU] 퍼센트 값 변화 감지!", "color: #00ff00; font-weight: bold;");
                             console.log("  이전:", lastPercentValues);
                             console.log("  현재:", currentPercentValues);
                             lastPercentValues = currentPercentValues;
                         }
                         
                         // [UPDATE] Even in CLOSED state, we send updates if items change (detected by sendUpdate)
                         sendUpdate({ 
                             state: 'CLOSED',
                             title: title,
                             timer: '', 
                             items: items 
                         });
                         
                         tryRefresh();
                         return;
                    }

                    // [상태 C] 진행 중 (ONGOING)
                    if (items.length > 0) {
                        // console.clear(); // Removed clear to see logs better
                        // console.log(`%c🔴 실시간 | ${title} | ${timerText}`, "color: #00ffa3; font-weight: bold;");
                        
                        previousState = 'ONGOING';
                        closedStateRefreshDone = false; 
                        isCancelledSent = false; // [FIX] Reset cancelled flag when new prediction starts 
                        
                        // [NEW] CLOSED 모니터링 리셋
                        if (closedStateMonitoringActive) {
                            closedStateMonitoringActive = false;
                            if (popupToggleInterval) {
                                clearInterval(popupToggleInterval);
                                popupToggleInterval = null;
                            }
                        }
                        closedStateStartTime = null;
                        lastPercentValues = null;
                        
                        sendUpdate({
                            state: 'ONGOING',
                            title: title,
                            timer: timerText,
                            items: items
                        });
                    }

                    tryRefresh();

                } catch (err) {
                    console.warn("봇 실행 중 오류:", err);
                }
            }, 1000);

        })();
        """
        self.chatroom_chzzk_browser.page().runJavaScript(js_code)
        
        # [NEW] Register bcuRefreshForClosedState function for CLOSED state transition
        refresh_callback_code = """
        window.bcuRefreshForClosedState = function() {
            console.log("[BCU] Refresh requested but disabled by user request. Doing nothing.");
        };
        """
        self.chatroom_chzzk_browser.page().runJavaScript(refresh_callback_code)
         
        # [REMOVED] Page refresh handler setup and methods related to re-injection for closed state




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