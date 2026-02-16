## 빌드 방법

### 1. 환경 설정 및 소스 코드 가져오기

**권장 버전: Python 3.11**

1.  프로젝트를 위한 폴더를 생성하고 터미널을 엽니다.
2.  가상 환경(venv)을 생성하고 활성화합니다.
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```
3.  Git을 통해 소스 코드를 가져옵니다.
    ```bash
    git clone https://github.com/hamsterb0t/BetterCheeseUtil.git
    ```
4.  필요한 Python 패키지를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```

### 2. (선택) Qt6 코덱 지원 추가하여 컴파일

기본 `pip install PyQt6`로 설치되는 라이브러리는 H.264, AAC 코덱을 지원하지 않습니다.
영상후원 오버레이에서 치지직 클립을 재생하려면, 기본 PyQt6 라이브러리 대신 **Proprietary Codecs (H.264, AAC 등)** 가 포함된 PyQt6를 직접 컴파일해야 합니다.
영도 리모컨 및 영상후원 오버레이를 사용하지 않을 경우 이 단계는 스킵해도 무방합니다.

*   **다음 가이드를 참고하세요**: [StackOverflow - Building Qt6 with proprietary codecs](https://stackoverflow.com/questions/79831860/building-qt6-with-proprietary-codecs-for-qtwebengine)
*   **권장 버전**: **Qt 6.9**

Qt6 컴파일이 완료되면, 생성된 라이브러리 파일을 가상 환경의 PyQt6 폴더로 복사해야 합니다.

**1) DLL, exe 파일 교체**
`C:\opt\qt\6.9\bin` (또는 빌드된 경로) 폴더에서 아래 파일들을 찾아 `.venv\Lib\site-packages\PyQt6\Qt6\bin` 폴더로 복사(덮어쓰기) 합니다.

*   **교체 파일**:
    *   `Qt6WebEngineCore.dll`
    *   `Qt6WebEngineWidgets.dll`
    *   `Qt6WebEngineQuick.dll`
    *   `QtWebEngineProcess.exe`

**2) 리소스 파일 교체**
`C:\opt\qt\6.9\resources` (또는 빌드된 경로) 폴더에서 아래 파일들을 찾아 `.venv\Lib\site-packages\PyQt6\Qt6\resources` 폴더로 복사(덮어쓰기) 합니다.

*   **교체 파일**:
    *   `qtwebengine_resources.pak`
    *   `qtwebengine_resources_100p.pak`
    *   `qtwebengine_resources_200p.pak`
    *   `icudtl.dat`

### 3. 빌드 실행

설정과 라이브러리 교체가 완료되면, 아래 내용을 `compile.bat` 파일로 저장하여 실행하거나 터미널에 직접 입력하여 빌드합니다.

```batch
@echo off
cd /d "%~dp0"
echo Building with virtual environment...
".venv\Scripts\python.exe" -m PyInstaller --clean main.spec
echo Build complete.
pause
```

빌드가 완료되면 `dist` 폴더 내에 생성된 실행 파일(`BetterCheeseUtil.exe`)을 확인합니다.
