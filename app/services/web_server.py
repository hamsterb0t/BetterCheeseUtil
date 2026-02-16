import webbrowser
from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO

from app.services import prediction_timer_service
from app.services.prediction_template_service import prediction_template_service


appW = Flask(__name__)
socketio = SocketIO(appW, cors_allowed_origins="*")
CORS(appW)

# 이 변수에 main_window 인스턴스를 저장할 것입니다.
main_app_instance = None 

def set_main_app(app_instance):
    """main.py에서 호출되어 main_window 인스턴스를 설정합니다."""
    global main_app_instance
    main_app_instance = app_instance

# --- Prediction Overlay State ---
prediction_state = {
    "status": "WAITING", # WAITING, ONGOING, CLOSED, RESULT
    "title": "승부예측 대기중",
    "timer": "",
    "items": [], # [{name, ratio, percent, vote_count}, ...]
    "winner": None,
    "result_ts": 0, # Timestamp when result was declared
    "prev_status": "WAITING" # Track previous status for state change detection
}





@appW.route('/update_prediction_stats', methods=['POST'])
def update_prediction_stats():
    """Received from Prediction Popup Scraper"""
    data = request.get_json()
    if not data: return {"error": "No data"}, 400
    
    prev_status = prediction_state.get("prev_status", "WAITING")
    new_status = data.get("state", "ONGOING")
    
    prediction_state["status"] = new_status
    prediction_state["title"] = data.get("title", "승부예측")
    prediction_state["timer"] = data.get("timer", "")
    prediction_state["items"] = data.get("items", [])
    
    # [NEW] Start result selection timer when state changes to CLOSED
    if new_status == "CLOSED" and prev_status != "CLOSED":
        prediction_timer_service.start_result_selection_timer()
    
    prediction_state["prev_status"] = new_status
    
    # When status becomes WAITING (chat clears the prediction info), clear overlay
    if new_status == "WAITING":
        prediction_state["winner"] = None
        prediction_state["result_ts"] = 0
        prediction_state["items"] = []
    elif new_status == "ONGOING":
        # New prediction started - clear previous winner
        prediction_state["winner"] = None
        prediction_state["result_ts"] = 0
    import time
    is_recent_result = (time.time() - prediction_state["result_ts"] < 600)
    
    if is_recent_result and prediction_state["status"] != "ONGOING" and prediction_state["winner"]:
        prediction_state["status"] = "RESULT"
        data = request.get_json()
        winner_name = data.get("winner")
        
        if winner_name:
            import time
            
            # [FIX] Check if this is a duplicate call with the same winner
            # Skip if already in RESULT state with same winner - prevents timer restart
            current_winner = prediction_state.get("winner")
            current_status = prediction_state.get("status")
            
            if current_status == "RESULT" and current_winner == winner_name:
                # Already processed this result, skip timer restart
                return {"msg": "winner already set, skipping"}, 200
            
            prediction_state["winner"] = winner_name
            prediction_state["status"] = "RESULT"
            prediction_state["prev_status"] = "RESULT"
            prediction_state["timer"] = "" # Hide timer on result
            prediction_state["result_ts"] = time.time()
            
            print("[WebServer] Result announced - winner: {}".format(winner_name))
    try:
        socketio.emit('prediction_update', prediction_state)
    except Exception:
        print("[WebServer] Failed to emit prediction_update")  # Ignore socket errors
    return {"msg": "ok"}, 200

@appW.route('/update_prediction_winner', methods=['POST'])
def update_prediction_winner():
    """Received from Chat Browser Scraper"""
    data = request.get_json()
    winner_name = data.get("winner")
    
    if winner_name:
        import time
        
        # [FIX] Check if this is a duplicate call with the same winner
        # Skip if already in RESULT state with same winner - prevents timer restart
        current_winner = prediction_state.get("winner")
        current_status = prediction_state.get("status")
        
        if current_status == "RESULT" and current_winner == winner_name:
            # Already processed this result, skip timer restart
            return {"msg": "winner already set, skipping"}, 200
        
        prediction_state["winner"] = winner_name
        prediction_state["status"] = "RESULT"
        prediction_state["prev_status"] = "RESULT"
        prediction_state["timer"] = "" # Hide timer on result
        prediction_state["result_ts"] = time.time()
        
        print("[WebServer] Result announced - winner: {}".format(winner_name))

        # NOTE: Removed auto-hide after 5 minutes. Overlay hides when chat clears (WAITING state).
        
        try:
            socketio.emit('prediction_update', prediction_state)
        except Exception:
            print("[WebServer] Failed to emit prediction_update")  # Ignore socket errors
        return {"msg": "winner updated"}, 200
    return {"error": "no winner"}, 400

@appW.route('/prediction_timer_status', methods=['GET'])
def prediction_timer_status():
    """Returns remaining seconds for prediction timers"""
    status = prediction_timer_service.get_timer_status()
    return status, 200

@appW.route('/prediction_cancelled', methods=['POST'])
def prediction_cancelled():
    """Called when prediction is cancelled (예측 취소)"""
    import time
    print("[WebServer] Prediction cancelled detected!")
    
    # Update prediction state to CANCELLED
    prediction_state["status"] = "CANCELLED"
    prediction_state["prev_status"] = "CANCELLED"
    prediction_state["timer"] = ""
    prediction_state["cancelled_ts"] = time.time()

    # Emit to overlay so it hides (initial)
    print("[WebServer] Emitting prediction_update...")
    try:
        socketio.emit('prediction_update', prediction_state)
        print("[WebServer] prediction_update emitted.")
    except Exception:
        print("[WebServer] Failed to emit prediction_update")  # Ignore socket errors
    
    return {"msg": "prediction cancelled acknowledged"}, 200

# --- Prediction Template Endpoints ---

@appW.route('/api/prediction/templates', methods=['GET'])
def get_prediction_templates():
    """Get all templates"""
    data = prediction_template_service.get_all()
    # Ensure history key existence is not relied upon in new frontend, 
    # but service returns full data dict.
    return data, 200

@appW.route('/api/prediction/templates', methods=['PUT'])
def update_prediction_templates():
    """Update all templates (reorder/batch update)"""
    templates = request.get_json()
    if not isinstance(templates, list): return {"error": "Data must be a list"}, 400
    data = prediction_template_service.update_all_templates(templates)
    return data, 200

@appW.route('/api/prediction/template', methods=['POST'])
def add_prediction_template():
    """Add a new template"""
    template = request.get_json()
    if not template: return {"error": "No data"}, 400
    data = prediction_template_service.add_template(template)
    return data, 200

@appW.route('/api/prediction/template', methods=['DELETE'])
def delete_prediction_template():
    """Delete a template by ID"""
    template_id = request.args.get('id')
    if not template_id: return {"error": "No id"}, 400
    data = prediction_template_service.delete_template(template_id)
    return data, 200


@appW.route('/open_url', methods=['POST'])
def open_url():
    data = request.get_json()  # JSON 데이터 가져오기
    url = data.get('url')  # 'url' 키의 값 가져오기
    if url:
        webbrowser.open(url)  # URL 기본 브라우저에서 열기
        return {"message": "URL opened successfully!"}, 200
    return {"error": "No URL provided!"}, 400

@appW.route('/usersearch', methods=['POST'])
def usersearch():
    data = request.get_json()  # JSON 데이터 가져오기
    type = data.get('type')  # 'url' 키의 값 가져오기
    nickname = data.get('nickname')  # 'nickname' 키의 값 가져오기
    if nickname:
        from PyQt6.QtCore import QMetaObject, Q_ARG, Qt
        if type == 0:
            QMetaObject.invokeMethod(main_app_instance.chat_log_search_tab, "search_log_check",
                                     Qt.ConnectionType.QueuedConnection,
                                     Q_ARG(str, nickname))
        elif type == 1:
             QMetaObject.invokeMethod(main_app_instance.chat_log_search_tab, "search_log_check_moa",
                                     Qt.ConnectionType.QueuedConnection,
                                     Q_ARG(str, nickname))
        return {"message": "opened successfully!"}, 200
    return {"error": "No provided!"}, 400

@appW.route('/update_image', methods=['POST'])
def update_image():
    data = request.get_json()  # JSON 데이터 가져오기
    image_path = data.get('image_path')  # 전달받은 이미지 경로
    back_image_path = data.get('back_image_path')  # 전달받은 이미지 경로
    if image_path:
        socketio.emit('image_update', {'path': image_path, 'backpath': back_image_path})  # WebSocket으로 데이터 전송
        return {"message": "Image updated successfully!"}, 200
    return {"error": "No image path provided!"}, 400

@appW.route('/update_text', methods=['POST'])
def update_text():
    data = request.get_json()  # JSON 데이터 가져오기
    text = data.get('text')  # 전달받은 텍스트
    if text or text == "":
        socketio.emit('text_update', {'text': text})  # WebSocket으로 데이터 전송
        return {"message": "Text updated successfully!"}, 200
    return {"error": "No text provided!"}, 400

# --- OBS Dock Integration ---

OBS_DOCK_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>치지직 영도 음량</title>
    <style>
        body {
            font-family: 'Pretendard', sans-serif;
            background-color: #2b2b2b;
            color: white;
            display: flex;
            flex-direction: row; /* 가로 배치 */
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            padding: 0 10px;
        }
        input[type=range] {
            flex-grow: 1; /* 슬라이더가 남은 공간 차지 */
            accent-color: #53af77;
            margin-right: 10px;
            cursor: pointer;
        }
        #vol-label { 
            font-size: 1rem; 
            font-weight: bold; 
            white-space: nowrap;
            min-width: 35px; /* 공간 확보 */
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <input type="range" id="volume-slider" min="0" max="100" value="50">
    <div id="vol-label">50%</div>

    <script>
        const slider = document.getElementById('volume-slider');
        const label = document.getElementById('vol-label');
        const socket = io();

        // 0. 초기 로딩 시 현재 음량 가져오기
        fetch('/get_current_volume')
            .then(response => response.json())
            .then(data => {
                if (data.volume !== undefined) {
                    slider.value = data.volume;
                    label.textContent = data.volume + '%';
                }
            })
            .catch(err => console.error('Failed to fetch volume:', err));

        // 1. 슬라이더 조작 시 앱으로 전송
        slider.addEventListener('input', function() {
            label.textContent = this.value + '%';
            fetch('/update_volume_from_dock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({volume: parseInt(this.value)})
            });
        });

        // 2. 앱에서 변경 시 업데이트
        socket.on('volume_update', function(data) {
            slider.value = data.volume;
            label.textContent = data.volume + '%';
        });
    </script>
</body>
</html>
"""

@appW.route('/obs_volume_control')
def obs_volume_control():
    return OBS_DOCK_HTML

@appW.route('/get_current_volume')
def get_current_volume():
    if main_app_instance and hasattr(main_app_instance, 'video_donation_tab'):
        try:
            # 메인 스레드 UI 접근이므로 주의가 필요하나 읽기는 보통 안전함
            # 혹은 안전하게 getter 메서드를 통해 접근할 수도 있음
            vol = main_app_instance.video_donation_tab.video_volume_slider.value()
            return {"volume": vol}, 200
        except Exception as e:
            print(f"Error getting volume: {e}")
            return {"error": str(e)}, 500
    return {"volume": 50}, 200 # 기본값

@appW.route('/update_volume_from_dock', methods=['POST'])
def update_volume_from_dock():
    data = request.get_json()
    volume = data.get('volume')
    if volume is not None and main_app_instance:
        try:
           from PyQt6.QtCore import QMetaObject, Q_ARG, Qt
           # RemoteTab 슬라이더 업데이트
           QMetaObject.invokeMethod(main_app_instance.video_donation_tab.video_volume_slider, 
                                    "setValue", 
                                    Qt.ConnectionType.QueuedConnection,
                                    Q_ARG(int, int(volume)))
        except Exception as e:
            print(f"Error updating volume from dock: {e}")
            return {"error": str(e)}, 500
            
        return {"message": "Volume updated"}, 200
    return {"error": "Invalid request"}, 400

def emit_volume_update(volume):
    """앱에서 음량 변경 시 호출하여 Dock에 알림"""
    socketio.emit('volume_update', {'volume': volume})

def run_flask_server():
    socketio.run(appW, host='127.0.0.1', port=5000)   # Flask 서버 실행 (스레드 지원)

