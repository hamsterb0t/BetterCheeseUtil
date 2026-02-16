import os
import re
import traceback
import threading
import types
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QTimer, QSettings, pyqtSignal, QThread
from datetime import datetime, timedelta
import asyncio
from chzzkpy.unofficial.chat import ChatClient as UnofficialChatClient
from chzzkpy import Client, UserClient, UserPermission
from chzzkpy.message import Message, Donation, Subscription
from chzzkpy.unofficial.chat import MissionDonation, MissionParticipationDonation, SubscriptionGiftMessage, SubscriptionMessage
from chzzkpy.error import HTTPException, ChatConnectFailed, NotFoundException
import secrets # For OAuth state

from app.constants import USERPATH, AUTH_REDIRECT_URI, AUTH_FILE_PATH

class AsyncWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(Exception)

    def __init__(self, coro, parent=None):
        super().__init__(parent)
        self.coro = coro
        self.loop = None

    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.coro)
        except asyncio.exceptions.CancelledError:
            # stop_loop()에 의해 루프가 중지될 때 발생하는 정상적인 예외입니다.
            # 오류로 처리하지 않고 정상 종료로 간주합니다.
            print("AsyncWorker: 루프가 정상적으로 취소되었습니다.")
            pass
        except Exception as e:
            self.error.emit(e)
        finally:
            if self.loop:
                self.loop.close()
            self.finished.emit()

    def stop_loop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            print("Asyncio loop stop requested.")

class Chatroom_Connector(QObject):
    # --- Signals ---
    refresh_remote = pyqtSignal()
    append_result_chat = pyqtSignal(str)
    setText_resultCHAT = pyqtSignal(str)
    run_chat_popup = pyqtSignal()
    two_tier_add = pyqtSignal()
    reconnect = pyqtSignal()
    message = pyqtSignal(str, dict)
    update_connection_status = pyqtSignal(str)
    login_success = pyqtSignal()
    login_failure = pyqtSignal(str)
    auto_mission = pyqtSignal()
    chatroom_get_popup_url = pyqtSignal()

    # --- New Signals ---
    update_nicknames = pyqtSignal(str, str) # signal(api_user_nickname, channel_nickname)
    manual_login_required = pyqtSignal(str, str) # signal(auth_url, oauth_state)
    start_temp_server = pyqtSignal(str) # signal(state)
    stop_temp_server = pyqtSignal() # signal()
    subscribers_fetched = pyqtSignal(list) # signal(list of detailed subscriber objects)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.client: Client | None = None # Official Client (for auth, official events)
        self.user_client: UserClient | None = None # Official User Client (authenticated)
        self.unofficial_client: UnofficialChatClient | None = None # Unofficial Client (for missions, sub gifts)

        self.streamer_ID = "" # Will be set after official auth
        self.streamer_nickname = ""
        self.api_user_nickname = "" # Nickname of the authenticated user

        self.is_live = False
        self.is_pin_notice = False
        self.async_worker: AsyncWorker | None = None
        self.instance = None # Reference to the main window
        self.log_file_path = ""
        self.live_check_task: asyncio.Task | None = None
        self.send_notice_task: asyncio.Task | None = None
        
        self.unofficial_client_thread: threading.Thread | None = None
        
        self.log_file_handle = None 
        self.current_log_path = None

    def start_async_operations(self, instance):
        """Starts the main async worker thread."""
        if self.async_worker and self.async_worker.isRunning():
            print("Async worker already running.")
            return

        self.instance = instance
        client_id = instance.settings_tab.chzzk_api_client_id.text().strip().replace(" ","")
        client_secret = instance.settings_tab.chzzk_api_client_secret.text().strip().replace(" ","")
        
        self.unofficial_client = None

        try:
            self.client = Client(client_id, client_secret)
            self._register_official_event_handlers()
        except Exception as e:
            self.append_result_chat.emit(f"❗ 공식 클라이언트 초기화 실패: {e}")
            self.update_connection_status.emit("채팅창: 🔴클라이언트 생성 오류")
            if instance.toggle_button_chat.isChecked():
                QTimer.singleShot(0, lambda: instance.toggle_button_chat.setChecked(False))
            return

        self.is_running = True
        self.update_connection_status.emit("채팅창: 🟡연결 하는 중")
        self.async_worker = AsyncWorker(self.async_auth_and_setup_flow(instance))
        self.async_worker.error.connect(self.handle_async_error)
        self.async_worker.finished.connect(self.handle_async_finished)
        self.async_worker.start()
    
    def handle_async_error(self, e):
        print(f"Async worker error: {e}")
        self.stop_internal()

    def handle_async_finished(self):
        print("Async worker finished.")
        if self.is_running:
             print("Warning: Async worker finished unexpectedly.")
             self.stop_internal()
        else:
             print("Async worker finished normally after stop request.")

    async def async_auth_and_setup_flow(self, instance):
        """
        인증 및 설정 비동기 흐름:
        1. (자동) 저장된 refresh_token으로 로그인 시도.
        2. (실패 시) (수동) 메인 UI에 임시 서버 시작 및 로그인 브라우저 표시 요청.
        3. (수동) 메인 UI가 코드를 받아 _exchange_code_for_token_threadsafe 호출 대기.
        4. (공통) 인증 성공 후 _post_auth_setup 실행 대기.
        5. (공통) self.is_running 플래그가 True인 동안 루프 유지 (작업 스레드 유지).
        """
        self.is_running = True
        QApplication.processEvents()

        auth_data = self.load_auth_token()
        if auth_data and 'refresh_token' in auth_data:
            self.append_result_chat.emit("🔄 저장된 인증 정보로 자동 로그인 중...")
            await self.refresh_official_token(auth_data['refresh_token'])
        
        if not self.user_client:
            self.append_result_chat.emit("수동 로그인이 필요합니다. 하단 브라우저를 확인해주세요...")
            oauth_state = secrets.token_urlsafe(16)
            self.start_temp_server.emit(oauth_state) 
            auth_url = self.client.generate_authorization_token_url(
                redirect_url=AUTH_REDIRECT_URI, # 메인 인스턴스에서 URI 가져오기
                state=oauth_state
            )
            self.manual_login_required.emit(auth_url, oauth_state)
            
            while self.is_running and not self.user_client:
                await asyncio.sleep(0.5)
            
            if not self.is_running:
                 await self.cleanup_async()
                 return
            
            print("Manual login flow completed.")

        while self.is_running:
            await asyncio.sleep(1)
        
        print("Main async flow stopping...")
        await self.cleanup_async()

    def load_auth_token(self):
        """auth.json에서 리프레시 토큰 로드"""
        try:
            if os.path.exists(AUTH_FILE_PATH):
                with open(AUTH_FILE_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading auth token: {e}")
        return None

    def save_auth_token(self, access_token: str, refresh_token: str):
        """auth.json에 토큰 저장"""
        try:
            os.makedirs(os.path.dirname(AUTH_FILE_PATH), exist_ok=True)
            auth_data = { 'access_token': access_token, 'refresh_token': refresh_token, 'saved_at': datetime.now().isoformat() }
            with open(AUTH_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(auth_data, f, indent=4)
            print("Auth token saved.")
        except Exception as e:
            print(f"Error saving auth token: {e}")
            self.append_result_chat.emit("❗ 인증 토큰 저장 실패.")

    async def refresh_official_token(self, refresh_token):
        """저장된 리프레시 토큰으로 UserClient 갱신 시도"""
        if not self.client:
             self.login_failure.emit("클라이언트 없음")
             return
        try:
            print("Attempting to refresh UserClient...")
            user_client = await self.client.refresh_user_client(refresh_token)
            
            self.save_auth_token( user_client.access_token.access_token, user_client.access_token.refresh_token )
            
            await self._post_auth_setup(user_client)
        
        except Exception as e:
            print(f"Token refresh error: {e}")
            self.append_result_chat.emit(f"❗ 토큰 갱신 중 오류 (인증 만료 가능성 높음): {e}")
            self.login_failure.emit(str(e))
            if os.path.exists(AUTH_FILE_PATH):
                try: os.remove(AUTH_FILE_PATH)
                except Exception as e_del: print(f"Failed to remove auth file on error: {e_del}")
            print(f"Refresh token invalid: {e}")
            self.append_result_chat.emit("❗ 자동 로그인 실패 (인증 만료). 수동 로그인이 필요합니다.")
            self.login_failure.emit("인증 만료")
            if os.path.exists(AUTH_FILE_PATH):
                try: os.remove(AUTH_FILE_PATH)
                except Exception as e_del: print(f"Failed to remove bad auth file: {e_del}")

    def exchange_code_for_token_threadsafe(self, code, state):
        """메인 스레드에서 호출되어 토큰 교환을 비동기 스레드에 예약"""
        if self.async_worker and self.async_worker.loop:
            coro = self._async_exchange_code(code, state)
            future = asyncio.run_coroutine_threadsafe(coro, self.async_worker.loop)
            future.add_done_callback(lambda f: print(f"Token exchange task finished. Result: {f.result() if not f.exception() else f.exception()}"))
        else:
            print("Error: Async worker not running, cannot exchange token.")

    async def _async_exchange_code(self, code, state):
        """(비동기) 인증 코드를 사용하여 UserClient 생성"""
        if not self.client:
            self.login_failure.emit("클라이언트 없음")
            return
        
        self.stop_temp_server.emit() # 토큰 교환 시도 시 서버 중지
        
        try:
            print("Attempting to generate UserClient from code...")
            user_client = await self.client.generate_user_client(code, state)
            
            self.save_auth_token( user_client.access_token.access_token, user_client.access_token.refresh_token )

            await self._post_auth_setup(user_client)
            
        except HTTPException as e:
            error_msg = f"토큰 교환 실패 (HTTP {e.status}): {e.message}"
            print(error_msg)
            self.login_failure.emit(error_msg)
        except Exception as e:
            error_msg = f"토큰 교환 중 오류: {e}"
            print(error_msg)
            traceback.print_exc()
            self.login_failure.emit(error_msg)

    async def _post_auth_setup(self, user_client: UserClient):
        """인증 성공 후 실행되는 공통 설정 로직 (비동기)"""
        try:
            self.user_client = user_client
            #self.login_success.emit()
            
            channel_info = await self.user_client.fetch_self()
            self.streamer_ID = channel_info.id
            self.streamer_nickname = channel_info.name
            self.api_user_nickname = channel_info.name
            
            print(f"Auth success. Channel ID: {self.streamer_ID}, Nickname: {self.streamer_nickname}")
            
            self.update_nicknames.emit(self.api_user_nickname, self.streamer_nickname)
            self.append_result_chat.emit(f"✅ [{self.api_user_nickname}] 계정 인증 성공!")

            # --- 비공식 API 흐름 시작 ---
            self.append_result_chat.emit("🔌 [비공식] 채팅 서버 연결 중...")
            await self.start_unofficial_flow()
            
            # --- 로그 파일 설정 ---
            try:
                current_date = datetime.now().strftime("%Y-%m-%d")
                path = self.instance.file_path_box_chat_log.text()
                if not os.path.exists(path): os.makedirs(path, exist_ok=True)
                base_log_name = f"{current_date}_#{self.streamer_ID}.log"
                log_file_path = os.path.join(path, base_log_name)
                self.log_file_path = log_file_path
            except Exception as e:
                self.append_result_chat.emit(f"❗ 로그 파일 설정 오류: {e}")
                self.log_file_path = ""

            await self.check_live_status_unofficial(self.instance, is_periodic=True) 
            await self._connect_chat_socket()

        except Exception as e:
            error_msg = f"인증 성공 후 처리 오류: {e}"
            print(error_msg)
            traceback.print_exc()
            self.login_failure.emit(error_msg)

    async def start_unofficial_flow(self):
        """비공식 클라이언트를 초기화하고 구독선물과 미션 이벤트만 등록 (로그인 없이)"""
        if not self.streamer_ID:
            self.append_result_chat.emit("❗ [비공식] 스트리머 ID가 없어 비공식 API를 시작할 수 없습니다.")
            return

        self.unofficial_client = UnofficialChatClient(channel_id=self.streamer_ID)

        @self.unofficial_client.event
        async def on_subscription(message: SubscriptionMessage):
            time = (message.time+timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
            nick = message.profile.nickname
            id = message.profile.user_id_hash
            month = message.extras.month
            tier_no = message.extras.tier_no
            chatmsg = message.content.replace("\n"," ")
            chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님이 {tier_no}티어 {month}개월 정기구독을 갱신하였습니다! ⭐🟥 기념 메시지: {chatmsg}")
            self.message.emit(chat, {'donation_type': '구독', 'time': time, 'nick': nick, 'id': id, 'tier': tier_no, 'month': month, 'msg': chatmsg})
            await self.logWrite(self.instance, chat, self.log_file_path)

        @self.unofficial_client.event
        async def on_subscription_gift(message: SubscriptionGiftMessage):
            gift_tier_no = message.extras.gift_tier_no
            sender_user_id = message.extras.sender_user_id
            sender_user_nick = ""
            gift_quantity = message.extras.quantity
            if gift_quantity == None: gift_quantity = 1

            if sender_user_id == None or message.profile == None:
                sender_user_nick = "익명의 후원자"
                sec = (message.time+timedelta(hours=9)).strftime("%H%M%S")
                sender_user_id = f"anon{sec}"
            else: sender_user_nick = message.profile.nickname

            try:
                receiver_user_id = message.extras.receiver_user_id
            except:
                receiver_user_id = "(받은이 아이디)"
            
            try:
                receiver_user_nick = message.extras.receiver_user
            except:
                receiver_user_nick = "(받은이 닉네임)"
            
            try:
                selection_type = message.extras.selection_type
            except:
                selection_type = "RANDOM"

            time = (message.time+timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

            if selection_type == "RANDOM": # 랜덤 선물
                chat = (f"[{time}] <{sender_user_nick} ({sender_user_id})> 🟥⭐ {sender_user_nick}님이 {gift_tier_no}티어 구독권 {gift_quantity}개를 선물했습니다! ⭐🟥")
                self.message.emit(chat, {'donation_type': '구독선물', 'time': time, 'nick': sender_user_nick, 'id': sender_user_id, 'selection_type': selection_type, 'quantity': gift_quantity, 'tier': gift_tier_no})
            else: # 지정 선물
                chat = (f"[{time}] <{sender_user_nick} ({sender_user_id})> 🟥⭐ {sender_user_nick}님이 {gift_tier_no}티어 구독권을 {receiver_user_nick}에게 선물했습니다! ⭐🟥")
                self.message.emit(chat, {'donation_type': '구독선물', 'time': time, 'nick': sender_user_nick, 'id': sender_user_id, 'selection_type': selection_type, 'receiver_nick': receiver_user_nick, 'quantity': gift_quantity, 'tier': gift_tier_no})
            await self.logWrite(self.instance, chat, self.log_file_path)

        @self.unofficial_client.event
        async def on_mission_completed(mission: MissionDonation): # 미션 성공/실패
            chat = ""
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sec = datetime.now().strftime("%H%M%S")
            if mission.is_anonymous == True:
                nick = "익명의 후원자"
                id = "anon"
                try:
                    id = mission.anonymous_token
                except:
                    None
            else:
                nick = mission.nickname
                id = mission.user_id_hash
            cheese_num = mission.total_pay_amount
            pnum = mission.participation_count

            if mission.success == True: # 성공
                chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님 외 {pnum}명의 미션 성공! {cheese_num}치즈 획득! ⭐🟥 미션 내용: {mission.mission_text}")
                self.message.emit(chat, {'donation_type': '미션성공', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'pnum': pnum, 'msg': mission.mission_text})
                await self.logWrite(self.instance, chat, self.log_file_path)
            else: # 실패
                chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님 외 {pnum}명의 미션 실패.. {cheese_num}치즈 획득 실패.. ⭐🟥 미션 내용: {mission.mission_text}")
                self.message.emit(chat, {'donation_type': '미션실패', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'pnum': pnum, 'msg': mission.mission_text})
                await self.logWrite(self.instance, chat, self.log_file_path)

        @self.unofficial_client.event
        async def on_mission_pending(mission: MissionDonation): # 미션 수락 대기중
            chat = ""
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sec = datetime.now().strftime("%H%M%S")
            if mission.is_anonymous == True:
                nick = "익명의 후원자"
                id = "anon"
                try:
                    id = mission.anonymous_token
                except:
                    None
            else:
                nick = mission.nickname
                id = mission.user_id_hash
            cheese_num = mission.total_pay_amount
            chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님의 미션 대기 중! {cheese_num}치즈 후원! ⭐🟥 미션 내용: {mission.mission_text}")
            self.message.emit(chat, {'donation_type': '미션대기', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'msg': mission.mission_text})
            await self.logWrite(self.instance, chat, self.log_file_path)
            self.auto_mission.emit()
        
        @self.unofficial_client.event
        async def on_mission_update_cost(mission: MissionParticipationDonation): # 미션 추가금
            chat = ""
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sec = datetime.now().strftime("%H%M%S")
            if mission.is_anonymous == True:
                nick = "익명의 후원자"
                id = "anon"
                try:
                    id =mission.anonymous_token
                except:
                    None
            else:
                nick = mission.nickname
                id = mission.user_id_hash
            cheese_num = mission.pay_amount
            cheese_num_sum = mission.total_pay_amount
            chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님이 미션 추가금 {cheese_num}치즈 후원! 미션금 총 {cheese_num_sum}치즈 ⭐🟥 미션 내용: {mission.mission_text}")
            self.message.emit(chat, {'donation_type': '미션', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'sum': cheese_num_sum, 'msg': mission.mission_text})
            await self.logWrite(self.instance, chat, self.log_file_path)
        
        @self.unofficial_client.event
        async def on_mission_approved(mission: MissionDonation): # 미션 수락
            chat = ""
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sec = datetime.now().strftime("%H%M%S")
            if mission.is_anonymous == True:
                nick = "익명의 후원자"
                id = "anon"
                try:
                    id = mission.anonymous_token
                except:
                    None
            else:
                nick = mission.nickname
                id = mission.user_id_hash
            cheese_num = mission.total_pay_amount
            chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님의 미션 수락! 미션금 총 {cheese_num}치즈 ⭐🟥 미션 내용: {mission.mission_text}")
            self.message.emit(chat, {'donation_type': '미션수락', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'msg': mission.mission_text})
            await self.logWrite(self.instance, chat, self.log_file_path)
        
        @self.unofficial_client.event
        async def on_mission_rejected(mission: MissionDonation): # 미션 거절
            chat = ""
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sec = datetime.now().strftime("%H%M%S")
            if mission.is_anonymous == True:
                nick = "익명의 후원자"
                id = "anon"
                try:
                    id = mission.anonymous_token
                except:
                    None
            else:
                nick = mission.nickname
                id = mission.user_id_hash
            cheese_num = mission.total_pay_amount
            chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님의 미션 거절! {cheese_num}치즈 획득 실패! ⭐🟥 미션 내용: {mission.mission_text}")
            self.message.emit(chat, {'donation_type': '미션거절', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'msg': mission.mission_text})
            await self.logWrite(self.instance, chat, self.log_file_path)
        
        @self.unofficial_client.event
        async def on_connect():
            self.append_result_chat.emit("✅ [비공식] 채팅 서버 연결 성공!")
            self.chatroom_get_popup_url.emit()

        # 비동기 연결 태스크 생성 (로그인 없이 연결)
        if self.async_worker and self.async_worker.loop:
            asyncio.run_coroutine_threadsafe(self.unofficial_connect(), self.async_worker.loop)
        else:
            self.append_result_chat.emit(f"❗ [비공식] 채팅 연결 중 오류")
            print("Warning: Could not schedule unofficial connect.")

    async def unofficial_connect(self):
        if self.unofficial_client:
            try:
                await self.unofficial_client.connect()  # 로그인 없이 연결 (읽기 전용 모드 가정)
            except Exception as e:
                self.append_result_chat.emit(f"❗ [비공식] 채팅 연결 실패: {e}")
                traceback.print_exc()

    async def _connect_chat_socket(self):
        """공식 채팅 웹소켓 연결"""
        if not self.user_client:
            self.append_result_chat.emit("❗ [공식] 채팅 연결 실패: 사용자 인증 필요.")
            self.update_connection_status.emit("채팅창: 🔴인증 필요")
            return
        if self.user_client.is_connected:
            print("[공식] 이미 채팅 서버에 연결되어 있습니다.")
            return

        try:
            self.append_result_chat.emit("🔌 [공식] 채팅 서버 연결 중...")
            QApplication.processEvents()
            print("Connecting official user client to chat server...")
            await self.user_client.connect(UserPermission.all())
        except ChatConnectFailed as e:
            self.append_result_chat.emit(f"❗ [공식] 채팅 연결 실패: {e}")
            self.instance.is_chat_connected = False
            self.update_connection_status.emit("채팅창: 🔴연결 실패")
        except Exception as e:
            self.append_result_chat.emit(f"❗ [공식] 채팅 연결 중 오류: {e}")
            traceback.print_exc()
            self.instance.is_chat_connected = False
            self.update_connection_status.emit("채팅창: 🔴연결 오류")
            
    def close_log_file(self):
        """열려 있는 로그 파일을 안전하게 닫습니다."""
        if self.log_file_handle:
            try:
                self.log_file_handle.close()
                print("Log file closed successfully.")
            except Exception as e:
                print(f"Error closing log file: {e}")
            finally:
                self.log_file_handle = None
                self.current_log_path = None

    async def cleanup_async(self):
        """모든 비동기 작업 및 연결 정리"""
        print("Running async cleanup...")
        self.is_running = False
        
        self.close_log_file()
        
        if self.live_check_task and not self.live_check_task.done():
            self.live_check_task.cancel()
            try: await self.live_check_task
            except asyncio.CancelledError: print("Live check task cancelled.")
        self.live_check_task = None

        if self.send_notice_task and not self.send_notice_task.done():
             self.send_notice_task.cancel()
             try: await self.send_notice_task
             except asyncio.CancelledError: print("Send notice task cancelled.")
        self.send_notice_task = None
        
        if self.user_client and self.user_client.is_connected:
            print("Disconnecting official user client...")
            try:
                await self.user_client.disconnect()
                print("Official user client disconnected.")
            except Exception as e: print(f"Error during user client disconnect: {e}")
        self.user_client = None

        if self.unofficial_client:
            print("Closing unofficial client session...")
            try: 
                await self.unofficial_client.close()
            except Exception as e: 
                print(f"Error closing unofficial client: {e}")
        
        if self.unofficial_client_thread and self.unofficial_client_thread.is_alive():
            print("Waiting for unofficial client thread to join...")
            self.unofficial_client_thread.join(timeout=2.0)
            if self.unofficial_client_thread.is_alive():
                print("Warning: Unofficial client thread did not terminate.")
        
        self.unofficial_client_thread = None
        self.unofficial_client = None

        self.client = None
        self.stop_temp_server.emit() # 임시 서버 종료
        print("Async cleanup finished.")
        self.async_worker.stop_loop()

    def stop(self):
        """외부에서 호출되는 메인 중지 함수"""
        print("Stop requested.")
        self.is_running = False
        
        if self.async_worker and self.async_worker.isRunning() and self.async_worker.loop:
            print("Scheduling cleanup_async on worker loop.")
            asyncio.run_coroutine_threadsafe(self.cleanup_async(), self.async_worker.loop)
            #self.async_worker.stop_loop()
        else:
            print("Worker not running. Attempting manual cleanup.")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.cleanup_async())
                loop.close()
            except Exception as e:
                print(f"Manual cleanup error: {e}")
        
        self.stop_internal()

    def stop_internal(self):
        """UI 즉시 정리 및 상태 초기화"""
        print("Running internal stop cleanup.")
        self.is_running = False
        
        self.close_log_file()
        
        self.client = None
        self.user_client = None
        self.unofficial_client = None
        self.live_check_task = None
        self.send_notice_task = None
        
        if self.instance:
            self.instance.is_chat_connected = False
            self.instance.is_live_started = False
            self.update_connection_status.emit("채팅창: 🔴연결 안 됨")
            if self.instance.chatroom_tab.toggle_button_chat.text() != "채팅창 접속":
                 self.instance.chatroom_tab.toggle_button_chat.setText("채팅창 접속")
            self.instance.remote_tab.user_count.setText("시청자")
            self.instance.remote_tab.uptime.setText("업타임")
            if hasattr(self.instance, 'channel_label'):
                self.instance.channel_label.setText("연결된 채널: (연결 안 됨)")

        print("Internal stop cleanup finished.")

    async def check_live_status_unofficial(self, instance, is_periodic=False):
        """비공식 API로 라이브 상태 확인 (쿠키 불필요)"""
        # streamer_ID가 설정되었는지 확인
        try:
            print("607")
            try:
                if not self.streamer_ID:
                    print("610")
                    if self.user_client:
                        try:
                            print("613")
                            channel_info = await self.user_client.fetch_self()
                            self.streamer_ID = channel_info.id
                            print("616")
                            print(f"Streamer ID set from user_client: {self.streamer_ID}")
                        except Exception as e:
                            print(f"Failed to get streamer_ID from user_client: {e}")
                            if not is_periodic: self.update_connection_status.emit("채팅창: 🔴인증된 채널 ID 없음")
                            return False
                    else:
                        print("623")
                        print("Cannot check live status: Streamer ID not set (auth pending).")
                        if not is_periodic: self.update_connection_status.emit("채팅창: 🔴인증 필요")
                        return False
                print("627")
                if not self.unofficial_client:
                    print("629")
                    self.unofficial_client = UnofficialChatClient(channel_id=self.streamer_ID)
                    print("631")
                    if not self.unofficial_client:
                        print("633")
                        print("Cannot check live status: Unofficial client initialization failed.")
                        if not is_periodic: self.update_connection_status.emit("채팅창: 🔴상태 확인 오류")
                        return instance.is_live_started
            except Exception as e:
                print("638")
                self.append_result_chat.emit(f"❗ [비공식] 방송 상태 확인 중 오류: {e}")
                traceback.print_exc()
                return instance.is_live_started
            
            try:
                print("644")
                if not is_periodic:
                    self.update_connection_status.emit("채팅창: 🟡방송 상태 확인 중")
                    QApplication.processEvents()
                print("648")
                live_status_data = await self.unofficial_client.live_status()
                print("650")
                if live_status_data and live_status_data.status == 'OPEN':
                    print("652")
                    user_count = live_status_data.concurrent_user_count
                    print("654")
                    try:
                        chat_date = datetime.strptime(live_status_data.openDate, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        chat_date = datetime.now()
                    print("659")
                    if not instance.is_live_started:
                        self.append_result_chat.emit("▶️ 방송 시작 감지됨.")
                        instance.is_live_started = True
                        self.is_live = True
                        instance.broadcast_start_time = chat_date
                    print("665")
                    uptime_delta = datetime.now() - chat_date
                    uptime = self.timedelta_to_hms(uptime_delta)
                    instance.remote_tab.user_count.setText(f"시청자 {user_count}명")
                    instance.remote_tab.uptime.setText(f"업타임 {uptime}")
                    print("670")
                    if not is_periodic:
                        self.update_connection_status.emit("채팅창: 🟡방송 켜짐")
                    return True
                else:
                    print("675")
                    if instance.is_live_started:
                        self.append_result_chat.emit("⏹️ 방송이 종료되었습니다.")
                    print("680")
                    instance.is_live_started = False
                    self.is_live = False
                    instance.broadcast_start_time = None
                    instance.remote_tab.user_count.setText("시청자")
                    instance.remote_tab.uptime.setText("업타임")
                    if not is_periodic:
                        self.update_connection_status.emit("채팅창: 🟡방송 꺼짐")
                    return False
            except Exception as e:
                print("688")
                self.append_result_chat.emit(f"❗ [비공식] 방송 상태 확인 중 오류: {e}")
                traceback.print_exc()
                try:
                    if self.unofficial_client: await self.unofficial_client.close()
                except: pass
                if self.streamer_ID:
                    self.unofficial_client = UnofficialChatClient(channel_id=self.streamer_ID)
                else:
                    self.unofficial_client = None
                return instance.is_live_started
        except Exception as e:
            print("700")
            self.append_result_chat.emit(f"❗ [비공식] 방송 상태 확인 중 오류: {e}")
            return True

    async def periodic_live_check(self, instance):
        """비공식 API로 주기적 라이브 상태 확인"""
        print("Starting periodic live check task (unofficial).")
        while self.is_running:
            if self.streamer_ID:
                await self.check_live_status_unofficial(instance, is_periodic=True)
            await asyncio.sleep(60)
        print("Stopping periodic live check task.")

    async def logWrite(self, instance, chat_string, log_file_path):
        """로그 파일 작성 (최적화: 파일 핸들 유지)"""
        if not log_file_path or not self.streamer_ID: return
        try:
            path = os.path.dirname(log_file_path)
            
            # 날짜/ID 체크 및 경로 갱신 로직
            current_date = datetime.now().strftime("%Y-%m-%d")
            target_log_path = log_file_path
            
            if current_date not in os.path.basename(log_file_path) or self.streamer_ID not in os.path.basename(log_file_path):
                base_log_name = f"{current_date}_#{self.streamer_ID}.log"
                target_log_path = os.path.join(path, base_log_name)
                self.log_file_path = target_log_path # 멤버 변수 업데이트

            # [핵심] 파일이 열려있지 않거나 경로가 바뀌었으면 새로 열기
            if self.log_file_handle is None or self.current_log_path != target_log_path:
                self.close_log_file() # 기존 파일 닫기
                os.makedirs(path, exist_ok=True)
                self.log_file_handle = open(target_log_path, "a", encoding="UTF8")
                self.current_log_path = target_log_path

            # 파일 쓰기 및 플러시(즉시 저장)
            self.log_file_handle.write(chat_string + "\n")
            self.log_file_handle.flush() 
            
            # QApplication.processEvents() # <- 렉 유발 원인이므로 제거함

        except Exception as e:
            print(f"Error writing to log file: {e}")
            self.close_log_file() # 에러 발생 시 핸들 초기화
            self.append_result_chat.emit(f"❗ 로그 쓰기 오류: {e}")

    def timedelta_to_hms(self, date_time):
        total_seconds = abs(int(date_time.total_seconds()))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def send_chat(self, message: str, is_pin_notice: bool = False):
        """메인 스레드에서 채팅 전송 요청"""
        print(message)
        if self.user_client and self.async_worker and self.async_worker.isRunning() and self.async_worker.loop:
            coro = self._async_send_chat(message, is_pin_notice)
            future = asyncio.run_coroutine_threadsafe(coro, self.async_worker.loop)
            future.add_done_callback(self._send_chat_done)
        else:
            self.append_result_chat.emit("❗ 채팅 보내기 실패: 연결되지 않음")

    async def _async_send_chat(self, message: str, is_pin_notice: bool):
        """비동기 스레드에서 실제 채팅 전송 실행"""
        if not self.user_client: return
        sent_message = None
        try:
            sent_message = await self.user_client.send_message(message)
            self.append_result_chat.emit(f"▶️ 메시지 전송됨: {message}")
        except HTTPException as e:
            self.append_result_chat.emit(f"❗ 메시지 전송 실패 (HTTP {e.status}): {e.message}")
            return
        except Exception as e:
            self.append_result_chat.emit(f"❗ 메시지 전송 중 오류: {e}")
            return
        
        if is_pin_notice and sent_message:
            try:
                await asyncio.sleep(1)
                await sent_message.pin()
                self.append_result_chat.emit(f"📌 메시지 고정됨.")
            except Exception as e:
                 self.append_result_chat.emit(f"❗ 메시지 고정 중 오류: {e}")

    def _send_chat_done(self, future):
        """채팅 전송 완료 후 콜백 (에러 확인)"""
        try: future.result()
        except Exception as e:
            self.append_result_chat.emit(f"❗ 메시지 전송 콜백 오류: {e}")

    def _register_official_event_handlers(self):
        """공식 API 이벤트 핸들러 등록"""
        if not self.client: return

        @self.client.event
        async def on_connect(session_id: str):
            """공식 이벤트 소켓 연결 성공"""
            #self.append_result_chat.emit(f"🔗 [공식] 이벤트 소켓 연결됨")

            if not self.user_client or not self.user_client.is_connected:
                raise ChatConnectFailed("채팅 서버 연결 확인 실패.")

            self.instance.is_chat_connected = True
            self.update_connection_status.emit("채팅창: 🟢연결됨")
            self.append_result_chat.emit("✅ [공식] 채팅 서버 연결 성공!")

            #self.append_result_chat.emit("✅ [공식] 라이브 상태 확인 중...")
            if self.async_worker and self.async_worker.loop:
                if self.live_check_task is None or self.live_check_task.done():
                    self.live_check_task = self.async_worker.loop.create_task(self.periodic_live_check(self.instance))
            
            if self.instance.settings_tab.auto_chat_popup_start.isChecked():
                self.run_chat_popup.emit()
            
            try:
                if self.user_client:
                    #self.append_result_chat.emit("📜 2티어 구독자 목록 조회 중...")
                    QApplication.processEvents()
                    page_no = 0
                    tier2_nicks = []
                    while True:
                        sub_result = await self.user_client.get_subscribers(size=50, page=page_no)
                        tier2_nicks.extend([sub.user_name for sub in sub_result.data if sub.tier_no == 2])
                        if sub_result.data is None or len(sub_result.data) < 50:
                            break
                        page_no += 1
                    self.instance.two_tier_user_list = tier2_nicks
                    self.two_tier_add.emit()
                    #self.append_result_chat.emit(f"✅ 2티어 구독자 {len(tier2_nicks)}명 로드 완료.")
            except Exception as e:
                self.append_result_chat.emit(f"❗ 구독자 목록 조회 오류: {e}")

            try:
                if self.user_client and self.instance and self.instance.auto_notice_toggle.isChecked():
                    notice_text = self.instance.auto_notice_textbox.text()
                    if notice_text:
                         self.send_chat(notice_text, is_pin_notice=True)
            except Exception as e:
                self.append_result_chat.emit(f"❗ 자동 공지 전송/고정 오류: {e}")

        @self.client.event
        async def on_chat(message: Message):
            """공식 API 채팅 메시지 수신"""
            try:
                nick = message.profile.nickname if message.profile else "알수없음"
                user_id = message.user_id
                time_str = (message.created_time+timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
                msg = message.content.replace('\n', " ") if message.content else ""

                chat_str = f"[{time_str}] <{nick} ({user_id})> {msg}"
                chat_data = {'donation_type': '채팅', 'time': time_str, 'nick': nick, 'id': user_id, 'msg': msg}

                self.message.emit(chat_str, chat_data)
                await self.logWrite(self.instance, chat_str, self.log_file_path)
                
                # # --- 자동 밴 로직 (공식 API 기준) ---
                # settings = QSettings(os.path.join(USERPATH, "BCU", "bansettings.ini"))
                # is_auto_ban = settings.value('is_auto_ban', False, type=bool)

                # if is_auto_ban and self.user_client:
                #     is_length_ban = settings.value('length_ban', False, type=bool)
                #     ban_length = settings.value('ban_length', 100, type=int)
                #     ban_duration_str = settings.value('ban_duration', '블라인드', type=str)
                #     is_word_ban = settings.value('is_word_ban', False, type=bool)
                #     words_str = settings.value('banned_words', '[]', type=str)
                #     try: banned_words = eval(words_str)
                #     except: banned_words = []

                #     ban_word_found = None
                #     ban_word_level_str = None
                #     if is_word_ban:
                #         current_level_idx = -1
                #         ban_levels_map = {'블라인드': 0, '임시제한': 1, '1일': 2, '3일': 3, '7일': 4, '15일': 5, '30일': 6, '90일': 7, '영구제한': 8}
                #         for word, duration_name in banned_words:
                #             if word in msg:
                #                  level_idx = ban_levels_map.get(duration_name, -1)
                #                  if level_idx > current_level_idx:
                #                       current_level_idx = level_idx
                #                       ban_word_found = word
                #                       ban_word_level_str = duration_name

                #     should_ban_permanently = False
                #     ban_reason = ""
                #     if ban_word_found and ban_word_level_str == '영구제한':
                #         should_ban_permanently = True
                #         ban_reason = f"금지 단어 사용 ({ban_word_found})"
                #     elif not ban_word_found and is_length_ban and len(re.sub(r'\{:.*?:\}', '.', msg)) > ban_length and ban_duration_str == '영구제한':
                #          should_ban_permanently = True
                #          ban_reason = f"채팅 길이 {ban_length}자 초과"

                #     if should_ban_permanently:
                #         try:
                #             await self.user_client.add_restrict_channel(user_id)
                #             self.append_result_chat.emit(f"🚫 사용자 영구 제한됨: {nick} ({user_id}), 사유: {ban_reason}")
                #         except HTTPException as e:
                #              if e.status == 403: print(f"사용자 {nick} 제한 시도 실패 (이미 제한/권한 부족): {e.message}")
                #              else: self.append_result_chat.emit(f"❗ 사용자 제한 실패 ({nick}): HTTP {e.status} {e.message}")
                #         except Exception as e: self.append_result_chat.emit(f"❗ 사용자 제한 중 오류 ({nick}): {e}")

            except Exception as e: print(f"Error in on_chat handler: {e}"); traceback.print_exc()


        # @self.client.event
        # async def on_subscription(subscription: Subscription):
        #     """공식 API 구독 메시지 수신"""
        #     try:
        #         time_str = ((subscription.created_time+timedelta(hours=9)) if hasattr(subscription, 'created_time') else datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        #         nick = subscription.subscriber_name
        #         user_id = subscription.subscriber_id
        #         month = subscription.month
        #         tier_no = subscription.tier_no
        #         chatmsg = ""

        #         chat_str = f"[{time_str}] <{nick} ({user_id})> 🟥⭐ {nick}님이 {tier_no}티어 {month}개월 구독! ⭐🟥"
        #         sub_data = {'donation_type': '구독', 'time': time_str, 'nick': nick, 'id': user_id, 'tier': tier_no, 'month': month, 'msg': chatmsg}

        #         self.message.emit(chat_str, sub_data)
        #         await self.logWrite(self.instance, chat_str, self.log_file_path)
        #     except Exception as e: print(f"Error in on_subscription handler: {e}"); traceback.print_exc()

        @self.client.event
        async def on_donation(donation: Donation):
            """공식 API 후원(치즈/영상) 메시지 수신"""
            try:
                time_obj = (donation.created_time+timedelta(hours=9)) if hasattr(donation, 'created_time') else datetime.now()
                time_str = time_obj.strftime("%Y-%m-%d %H:%M:%S")
                sec_str = time_obj.strftime("%H%M%S")
                
                is_anonymous = not bool(donation.donator_name)
                nick = donation.donator_name if not is_anonymous else "익명의 후원자"
                user_id = donation.donator_id if not is_anonymous else f"anon{sec_str}"
                cheese_num = donation.pay_amount
                donation_type_str = donation.type
                donation_text = donation.donation_text

                chat_str = ""
                donation_data = {}

                if donation_type_str == 'VIDEO':
                    tier = "1"
                    try:
                        if nick != "익명의 후원자":
                            if nick in self.instance.two_tier_user_list:
                                tier = "2"
                    except:
                        None
                    videotitle = donation_text
                    chat_str = f"[{time_str}] <{nick} ({user_id})> 🟥⭐ 영상후원 {cheese_num}치즈! ⭐🟥 영상 제목: {videotitle}"
                    donation_data = {'donation_type': '영상후원', 'time': time_str, 'nick': nick, 'id': user_id, 'cheese': cheese_num, 'sec': cheese_num, 'title': videotitle, 'tier': tier}
                elif donation_type_str == 'CHAT':
                    chatmsg = donation_text.replace('\n', " ") if donation_text else ""
                    chat_str = f"[{time_str}] <{nick} ({user_id})> 🟥⭐ 치즈후원 {cheese_num}치즈! ⭐🟥"
                    if chatmsg: chat_str += f" 메시지: {chatmsg}"
                    donation_data = {'donation_type': '치즈', 'time': time_str, 'nick': nick, 'id': user_id, 'msg': chatmsg, 'cheese': cheese_num}
                else:
                     chat_str = f"[{time_str}] <{nick} ({user_id})> 🟥⭐ 알 수 없는 후원 ({donation_type_str}) {cheese_num}치즈! ⭐🟥 내용: {donation_text}"
                     donation_data = {'donation_type': '기타후원', 'time': time_str, 'nick': nick, 'id': id, 'cheese': cheese_num, 'msg': donation_text}

                self.message.emit(chat_str, donation_data)
                await self.logWrite(self.instance, chat_str, self.log_file_path)
            except Exception as e: print(f"Error in on_donation handler: {e}"); traceback.print_exc()


        @self.client.event
        async def on_client_error(exception: Exception, *args, **kwargs):
            print(f"[공식] Client error event: {exception}")
            self.append_result_chat.emit(f"❗ [공식] 클라이언트 오류: {exception}")

        @self.client.event
        async def on_websocket_close(code: int, reason: str):
            print(f"[공식] WebSocket closed: Code={code}, Reason={reason}")
            self.append_result_chat.emit(f"🔌 [공식] 웹소켓 연결 끊김 (코드: {code}).")
            if self.is_running: self.reconnect.emit()

    def ban_user(self, user_id, user_nick, ban_type, duration_days=None, reason=""):
        if self.user_client and self.async_worker and self.async_worker.isRunning() and self.async_worker.loop:
            coro = self._async_ban_user(user_id, ban_type, duration_days, reason)
            asyncio.run_coroutine_threadsafe(coro, self.async_worker.loop)
        else: self.append_result_chat.emit(f"❗ 사용자 제한 실패: 연결되지 않음 ({user_nick})")

    async def _async_ban_user(self, user_id, ban_type, duration_days, reason):
         if not self.user_client: return
         try:
             if ban_type == "permanent":
                  await self.user_client.add_restrict_channel(user_id)
                  self.append_result_chat.emit(f"🚫 사용자 영구 제한됨: {user_id}, 사유: {reason}")
             else: self.append_result_chat.emit(f"⚠️ 제한 유형 미지원 (공식 API): {ban_type}")
         except HTTPException as e:
              if e.status == 403: self.append_result_chat.emit(f"⚠️ 사용자 제한 실패 ({user_id}): 이미 제한됨 또는 권한 없음")
              else: self.append_result_chat.emit(f"❗ 사용자 제한 실패 ({user_id}): HTTP {e.status} {e.message}")
         except Exception as e: self.append_result_chat.emit(f"❗ 사용자 제한 중 오류 ({user_id}): {e}")

    def unban_user(self, user_id):
        if self.user_client and self.async_worker and self.async_worker.isRunning() and self.async_worker.loop:
            coro = self._async_unban_user(user_id)
            asyncio.run_coroutine_threadsafe(coro, self.async_worker.loop)
        else: self.append_result_chat.emit(f"❗ 사용자 제한 해제 실패: 연결되지 않음 ({user_id})")

    async def _async_unban_user(self, user_id):
        if not self.user_client: return
        try:
            await self.user_client.remove_restrict_channel(user_id)
            self.append_result_chat.emit(f"✅ 사용자 제한 해제됨: {user_id}")
        except HTTPException as e:
            if e.status == 404: self.append_result_chat.emit(f"⚠️ 사용자 제한 해제 실패 ({user_id}): 제한되지 않음")
            else: self.append_result_chat.emit(f"❗ 사용자 제한 해제 실패 ({user_id}): HTTP {e.status} {e.message}")
        except Exception as e: self.append_result_chat.emit(f"❗ 사용자 제한 해제 중 오류 ({user_id}): {e}")

    def search_user_info(self, user_id_or_nick):
        if self.async_worker and self.async_worker.isRunning() and self.async_worker.loop:
            coro = self._async_search_user_info(user_id_or_nick)
            asyncio.run_coroutine_threadsafe(coro, self.async_worker.loop)
        else:
             self.append_result_chat.emit("❗ 유저 정보 검색 실패: 연결되지 않음")

    def request_all_subscribers(self):
        """메인 스레드에서 전체 구독자 목록 요청"""
        if self.async_worker and self.async_worker.isRunning() and self.async_worker.loop:
            coro = self._async_fetch_all_subscribers()
            asyncio.run_coroutine_threadsafe(coro, self.async_worker.loop)
        else:
            self.append_result_chat.emit("❗ 구독자 목록 요청 실패: 연결되지 않음")

    async def _async_fetch_all_subscribers(self):
        """(비동기) 전체 구독자 목록 순회 및 시그널 방출"""
        if not self.user_client:
            self.append_result_chat.emit("❗ 구독자 목록 조회 실패: 인증되지 않음")
            return

        try:
            self.append_result_chat.emit("📜 전체 구독자 목록 로딩 중... (시간이 걸릴 수 있습니다)")
            all_subscribers = []
            page_no = 0
            while True:
                # size=500 is unofficial limit? Safest is 50-100 usually, but let's try 50 loop
                sub_result = await self.user_client.get_subscribers(size=50, page=page_no)
                if not sub_result.data:
                    break
                
                # Store necessary data. 
                # We need nickname for filtering pick_list (which contains nicknames)
                # But nicknames can change. ideally ID.
                # But pick_tab stores nicknames.
                # So we store nicknames.
                for sub in sub_result.data:
                    all_subscribers.append(sub.user_name)
                    
                if len(sub_result.data) < 50:
                    break
                page_no += 1
                await asyncio.sleep(0.1) # Prevent rate limit
            
            self.append_result_chat.emit(f"✅ 전체 구독자 {len(all_subscribers)}명 로드 완료.")
            self.subscribers_fetched.emit(all_subscribers)
            
        except HTTPException as e:
            self.append_result_chat.emit(f"❗ 구독자 목록 조회 실패 (HTTP {e.status}): {e.message}")
        except Exception as e:
            self.append_result_chat.emit(f"❗ 구독자 목록 조회 중 오류: {e}")
            traceback.print_exc()

    async def _async_search_user_info(self, user_id_or_nick):
        self.instance.subscribe_label_chat_log.setText("구독: 조회 중...")
        self.instance.follow_date_label_chat_log.setText("팔로우 날짜: 조회 중...")
        self.instance.chat_count_label_chat_log.setText("채팅 수: (정보 없음)")
        self.instance.temp_ban_label_chat_log.setText("임시 제한 수: (정보 없음)")
        self.instance.ban_label_chat_log.setText("활동 제한 수: (정보 없음)")
        QApplication.processEvents()

        found_sub = None
        follow_date_str = "팔로우하지 않음 / 정보 없음"
        target_user_id = user_id_or_nick 
        target_user_nick = user_id_or_nick 

        is_searching_self = self.user_client and self.user_client.channel_id == self.streamer_ID

        if self.user_client and is_searching_self:
            try:
                sub_result = await self.user_client.get_subscribers(size=100) # Simplified
                for sub in sub_result.data:
                    if sub.user_name == user_id_or_nick or sub.user_id == user_id_or_nick:
                        found_sub = sub
                        target_user_nick = sub.user_name
                        target_user_id = sub.user_id # Official ID
                        break
                if found_sub:
                    subscribe_text = f"구독: {found_sub.tier_no}티어 {found_sub.month}개월 (플랫폼 구분 불가)"
                    self.instance.subscribe_label_chat_log.setText(subscribe_text)
                else:
                    self.instance.subscribe_label_chat_log.setText("구독: 구독하지 않음 / 정보 없음")
            except Exception as e:
                 self.instance.subscribe_label_chat_log.setText("구독: (조회 오류)")
                 print(f"Error searching subscribers: {e}")
        else:
             self.instance.subscribe_label_chat_log.setText("구독: (인증 필요/타채널 불가)")

        if not self.unofficial_client:
             if self.streamer_ID:
                self.unofficial_client = UnofficialChatClient(channel_id=self.streamer_ID)
             else:
                print("Cannot search follow date: streamer_ID not set.")
                self.instance.follow_date_label_chat_log.setText("팔로우 날짜: (조회 불가)")
                self.append_result_chat.emit(f"🔍 유저 정보 조회 완료: {target_user_nick} ({target_user_id})")
                return

        if self.unofficial_client:
             try:
                  user_profile_data = await self.unofficial_client.profile_card(user_id_or_nick) 
                  if user_profile_data and user_profile_data.streaming_property and user_profile_data.streaming_property.following_date:
                       follow_date_str = f"팔로우 날짜: {user_profile_data.streaming_property.following_date}"
                       if target_user_nick == user_id_or_nick and user_profile_data.nickname:
                            target_user_nick = user_profile_data.nickname
                  else:
                       follow_date_str = "팔로우 날짜: 팔로우하지 않음"
                  self.instance.follow_date_label_chat_log.setText(follow_date_str)
             except NotFoundException:
                  self.instance.follow_date_label_chat_log.setText("팔로우 날짜: (사용자 정보 없음)")
             except Exception as e:
                  self.instance.follow_date_label_chat_log.setText("팔로우 날짜: (조회 오류)")
                  print(f"Error fetching follow date (unofficial): {e}")
        else:
             self.instance.follow_date_label_chat_log.setText("팔로우 날짜: (조회 불가 - 내부 오류)")

        self.append_result_chat.emit(f"🔍 유저 정보 조회 완료: {target_user_nick} ({target_user_id})")