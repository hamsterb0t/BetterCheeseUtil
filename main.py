# MIT License

# Copyright (c) 2025 hamsterbot

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import os
import threading
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtCore import Qt
import qdarktheme
from app.main_window import BetterCheeseUtil
from app.services import web_server
from app.constants import GLOBALFONTSIZE
from app.resources import resource_path
from app.constants import GLOBALFONTSIZE, USERPATH
import shutil
from engineio.async_drivers import gevent ## [삭제 금지] pyinstaller exe 생성 시 오류 방지를 위해 필요

if __name__ == '__main__':
    # Ensure chat_emoticons.json exists in user directory
    user_json_path = os.path.join(USERPATH, "BCU", "chat_emoticons.json")
    if not os.path.exists(user_json_path):
        try:
            default_json_path = resource_path('resources/chat_emoticons.json')
            shutil.copy2(default_json_path, user_json_path)
            print(f"Copied default chat_emoticons.json to {user_json_path}")
        except Exception as e:
            print(f"Failed to copy chat_emoticons.json: {e}")

    os.environ["QTWEBENGINE_REMOTE_DEBUGGING_PORT"] = "9222"
    FLAGS = (
        "--remote-debugging-port=9222 "
        "--enable-features=ProprietaryCodecs "
        "--ffmpeg-branding=Chrome "
        "--disable-background-timer-throttling "
        "--disable-renderer-backgrounding "
        "--disable-backgrounding-occluded-windows"
    )
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = FLAGS
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    for flag in FLAGS.split():
        sys.argv.append(flag)
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(theme='light', custom_colors={"primary": "#69b989"})
    QFontDatabase.addApplicationFont(resource_path(r'.\resources\fonts\PretendardJP-Regular.ttf'))
    font = QFont('Pretendard JP', GLOBALFONTSIZE)
    app.setFont(font)
    ex = BetterCheeseUtil()
    web_server.set_main_app(ex)
    flask_thread = threading.Thread(target=web_server.run_flask_server, daemon=True)
    flask_thread.start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ex.show()
    sys.exit(app.exec())