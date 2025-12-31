import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
from PyQt6.QtCore import QObject, pyqtSignal
from http.server import BaseHTTPRequestHandler, HTTPServer # For OAuth server

from app.constants import AUTH_REDIRECT_URI

class OAuthHttpServerHandler(BaseHTTPRequestHandler):
    main_signal = None  # BetterCheeseUtil의 code_received 시그널을 담을 클래스 변수
    expected_state = None # CSRF 방지를 위한 state 값

    def do_GET(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_path.query)

            if parsed_path.path == urllib.parse.urlparse(AUTH_REDIRECT_URI).path:
                code = query_params.get('code', [None])[0]
                received_state = query_params.get('state', [None])[0]

                if received_state != self.expected_state:
                    self.send_error_response(400, "State 불일치. CSRF 공격 가능성이 있습니다.")
                    print(f"OAuth Error: State mismatch. Expected {self.expected_state}, got {received_state}")
                    return

                if code:
                    self.send_success_response()
                    if self.main_signal:
                        # 메인 스레드로 code와 state 전송
                        self.main_signal.emit(code, received_state) 
                else:
                    error = query_params.get('error', ["-"])[0]
                    error_desc = query_params.get('error_description', ["-"])[0]
                    self.send_error_response(400, f"인증 실패: {error_desc} ({error})")
                    print(f"OAuth Error: {error} - {error_desc}")
            else:
                self.send_error_response(404, "Not Found")

        except Exception as e:
            print(f"HTTP Server Handler Error: {e}")
            self.send_error_response(500, f"Internal Server Error: {e}")

    def send_success_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        message = "<html><head><title>인증 성공</title><style>" \
                  "body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #222; color: #eee; }" \
                  "div { text-align: center; border: 1px solid #555; padding: 30px; border-radius: 10px; }" \
                  "</style></head>" \
                  "<body><div><h1>✅ 인증 성공!</h1><p>Better Cheese 유틸리티로 돌아가세요.<br>이 창은 수동으로 닫아도 됩니다.</p></div></body></html>"
        self.wfile.write(message.encode('utf-8'))

    def send_error_response(self, code, text):
        self.send_response(code)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        message = f"<html><body><h1>❌ 인증 실패</h1><p>{text}</p></body></html>"
        self.wfile.write(message.encode('utf-8'))

    def log_message(self, format, *args):
        # HTTP 서버 로그를 콘솔에 출력하지 않도록 오버라이드
        pass

class OAuthHttpServerWorker(QObject):
    code_received_signal = pyqtSignal(str, str) # code, state
    server_stopped_signal = pyqtSignal()
    
    def __init__(self, state, host='localhost', port=8080):
        super().__init__()
        self.expected_state = state
        self.host = host
        self.port = port
        self.httpd = None

    def run(self):
        """QThread의 start()에 의해 호출될 메인 함수"""
        try:
            OAuthHttpServerHandler.main_signal = self.code_received_signal
            OAuthHttpServerHandler.expected_state = self.expected_state
            
            # HTTPServer 인스턴스 생성 시 reuse_address=True 설정 (권장)
            self.httpd = HTTPServer((self.host, self.port), OAuthHttpServerHandler)
            self.httpd.allow_reuse_address = True 
            
            print(f"Starting OAuth server on http://{self.host}:{self.port}...")
            self.httpd.serve_forever() # 블로킹 호출
            print("OAuth server stopped.")

        except OSError as e:
            if e.winerror == 10048 or e.errno == 98: # 주소 이미 사용 중 (Win/Unix)
                print(f"Error: Port {self.port} is already in use.")
                # 메인 스레드에서 QMessageBox를 띄우도록 시그널을 보낼 수 있음
                # 여기서는 그냥 콘솔 출력
            else:
                print(f"HTTP Server Worker Error: {e}")
        except Exception as e:
            print(f"HTTP Server Worker Error: {e}")
        finally:
            OAuthHttpServerHandler.main_signal = None # 정리
            self.server_stopped_signal.emit()

    def stop(self):
        """서버를 안전하게 종료 (다른 스레드에서 호출 필요)"""
        if self.httpd:
            print("Shutting down OAuth server...")
            try:
                # shutdown()은 serve_forever()를 실행 중인 스레드와 다른 스레드에서 호출되어야 함
                threading.Thread(target=self.httpd.shutdown, daemon=True).start()
            except Exception as e:
                 print(f"Error shutting down server: {e}")