(function () {
    if (window.top === window.self) console.log('[Overlay] INJECT_JS STARTED');

    // Page Visibility API Spoofing - Prevent YouTube from detecting hidden window
    try {
        Object.defineProperty(document, 'hidden', { get: () => false, configurable: true });
        Object.defineProperty(document, 'visibilityState', { get: () => 'visible', configurable: true });
        // Block visibilitychange events from propagating
        document.addEventListener('visibilitychange', (e) => { e.stopImmediatePropagation(); }, true);
        // Also override hasFocus to always return true
        Document.prototype.hasFocus = function () { return true; };
        if (window.top === window.self) console.log('[Overlay] Page Visibility API spoofing applied.');
    } catch (e) {
        console.error('[Overlay] Failed to spoof Visibility API:', e);
    }

    // Force PC environment (touch events disabled)
    try {
        // Disable Touch Events if they exist
        if ('ontouchstart' in window) { window.ontouchstart = undefined; }
        if ('ontouchend' in window) { window.ontouchend = undefined; }
        if ('ontouchmove' in window) { window.ontouchmove = undefined; }
        if ('ontouchcancel' in window) { window.ontouchcancel = undefined; }
        if (window.top === window.self) console.log("[Overlay] Touch events disabled.");
    } catch (e) {
        console.error("[Overlay] Failed to disable touch events:", e);
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
    } catch (e) {
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

    // Default enabled
    window.bcu_skip_timer_enabled = true;

    if (window.top === window.self) console.log('[Overlay] Script Loaded. Overwriting setTimeout...');

    window.setTimeout = function (callback, delay, ...args) {
        // Skip logic only if enabled
        if (window.bcu_skip_timer_enabled) {
            const numericDelay = parseInt(delay, 10);
            if (!isNaN(numericDelay) && numericDelay >= TARGET_MIN && numericDelay <= TARGET_MAX) {
                const now = Date.now();
                if (now - lastSkipTime > SKIP_COOLDOWN) {
                    let cbCode = '';
                    try {
                        if (callback) {
                            cbCode = callback.toString();
                        }
                    } catch (e) { }

                    if (cbCode.includes("return new Promise") && cbCode.includes("var t=this,n=arguments")) {
                        console.log(`[Overlay] Skipped TARGET 3000ms timer.`);
                        lastSkipTime = now;
                        return originalSetTimeout(callback, 0, ...args);
                    }
                }
            }
        }
        return originalSetTimeout(callback, delay, ...args);
    };

    window.setSkipTimerEnabled = function (enabled) {
        window.bcu_skip_timer_enabled = enabled;
        console.log('[BCU] Skip Timer Enabled:', enabled);
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
                    /* height: 1254px;  <- Cutoff cause: Fixed height */
                    height: auto !important; /* Allow dynamic height */
                    min-height: 100vh;
                    overflow: visible !important; /* Allow content to flow */
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
                    gap: 0px !important;
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
                    padding: 0px 10px 5px 10px !important;
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

                [class*="overlay_donation_description"] {
                    margin-bottom: 5px !important;
                }
                [class*="overlay_donation_wrapper"] {
                    margin-top: 0px !important;
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
                
                /* 세로 정렬 (Vertical Align) - Portrait에서는 적용 안 함! */
                /* Portrait 모드에서 세로영상은 항상 top:0 고정. */
                /* v_align은 LANDSCAPE 모드에서만 적용됨. */
                
                /* Landscape Mode: Vertical Align Bottom */
                body:not(.portrait).align-v-bottom iframe,
                body:not(.portrait).align-v-bottom #chzzk_player {
                    /* 동적 CSS (setPortraitSize)에서 top 값 설정 */
                }
                body:not(.portrait).align-v-bottom [class*="overlay_donation_contents"] {
                    /* 동적 CSS (setPortraitSize)에서 top 값 설정 */
                }
                
                /* Landscape Mode: Vertical Align Center */
                body:not(.portrait).align-v-center iframe,
                body:not(.portrait).align-v-center #chzzk_player {
                    /* 동적 CSS (setPortraitSize)에서 top 값 설정 */
                }
                body:not(.portrait).align-v-center [class*="overlay_donation_contents"] {
                    /* 동적 CSS (setPortraitSize)에서 top 값 설정 */
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

// Global storage for portrait dimensions (used by setAlignment to regenerate CSS)
var _bcuPortraitWidth = 576;
var _bcuPortraitHeight = 1024;
var _bcuIncludeText = true;  // 후원텍스트 포함 여부
var _bcuVerticalAlign = 'center'; // Vertical Alignment State

// 후원텍스트 포함 여부 설정 함수
function setIncludeText(includeText) {
    _bcuIncludeText = includeText;
    console.log('[BCU] Include text set to:', includeText);
    // CSS 재생성
    setPortraitSize(_bcuPortraitWidth, _bcuPortraitHeight);
}

function setAlignment(alignment) {
    // Remove old alignment classes
    document.body.classList.remove('align-left', 'align-center', 'align-right');
    document.body.classList.remove('align-v-top', 'align-v-center', 'align-v-bottom');

    // Parse 9-grid alignment (e.g., "top-left", "center-center", "bottom-right")
    var parts = alignment.split('-');
    var vAlign = 'top';
    var hAlign = 'center';

    if (parts.length >= 2) {
        vAlign = parts[0];  // top, center, bottom
        hAlign = parts[1];  // left, center, right
    } else {
        // Legacy single value (left, center, right)
        hAlign = alignment;

        if (alignment === 'top' || alignment === 'bottom') {
            vAlign = alignment;
            hAlign = 'center';
        }
    }

    _bcuVerticalAlign = vAlign; // Store for setPortraitSize logic

    document.body.classList.add('align-' + hAlign);
    document.body.classList.add('align-v-' + vAlign);
    console.log('[BCU] Alignment set to: h=' + hAlign + ', v=' + vAlign);

    // Regenerate CSS with new alignment (uses cached dimensions)
    setPortraitSize(_bcuPortraitWidth, _bcuPortraitHeight);
}

// 세로 모드 크기 설정 함수 (동적 CSS 업데이트)
function setPortraitSize(width, height) {
    // height가 제공되지 않으면 기본 비율로 계산
    if (!height) {
        height = Math.round(width * 1024 / 576);
    }

    // Cache dimensions globally for setAlignment to use
    _bcuPortraitWidth = width;
    _bcuPortraitHeight = height;
    var centerOffset = Math.round((1280 - width) / 2);
    var rightOffset = 1280 - width;

    // 가로화면 높이: include_text에 따라 다름
    // true: 720(영상) + 162(텍스트) = 882
    // Physical text height (Always 162)
    var textH = 162;

    // Alignment text height
    // Rule: Include Text toggle only active if v=center. Else always Included.
    var effectiveInclude = _bcuIncludeText;
    if (_bcuVerticalAlign !== 'center') {
        effectiveInclude = true;
    }
    var alignTextH = effectiveInclude ? 162 : 0;

    // Landscape Alignment Height
    var landscapeAlignH = 720 + alignTextH;

    // Window Size Calculations (Always include text)
    var landscapePhysicalH = 720 + 162;
    var portraitPhysicalH = height + 162;

    // Use Physical Height for Window Size (maxH)
    var maxH = Math.max(landscapePhysicalH, portraitPhysicalH);

    // 기존 동적 스타일 제거
    var existingStyle = document.getElementById('bcu-portrait-size-style');
    if (existingStyle) existingStyle.remove();

    // 새 스타일 생성
    var style = document.createElement('style');
    style.id = 'bcu-portrait-size-style';
    style.textContent = `
        /* Portrait Mode Sizing */
        body.portrait iframe[src*="youtube.com"],
        body.portrait iframe[src*="youtube-nocookie.com"],
        body.portrait iframe[src*="/embed-clip-donation/"],
        body.portrait iframe#chzzk_player {
            width: ${width}px !important;
            height: ${height}px !important;
        }
        body.portrait [class*="overlay_donation_contents"] {
            top: ${height}px !important;
            width: ${width}px !important;
        }
        body.portrait.align-center iframe,
        body.portrait.align-center #chzzk_player,
        body.portrait.align-center [class*="overlay_donation_contents"] {
            left: ${centerOffset}px !important;
        }
        body.portrait.align-right iframe,
        body.portrait.align-right #chzzk_player,
        body.portrait.align-right [class*="overlay_donation_contents"] {
            left: ${rightOffset}px !important;
        }
        
        /* Portrait mode: 세로영상은 항상 top:0 고정. v_align 적용 안 함. */
        
        /* ========================================= */
        /* LANDSCAPE MODE - Vertical Alignment      */
        /* ========================================= */
        /* Landscape: Video 720 + Text 162 = 882    */
        /* Window height = maxH                      */
        /* Bottom: top = maxH - 882                 */
        /* Center: top = (maxH - 882) / 2           */
        
        /* Landscape Mode: Vertical Align Bottom */
        body:not(.portrait).align-v-bottom iframe,
        body:not(.portrait).align-v-bottom #chzzk_player {
            top: ${maxH - landscapeAlignH}px !important;
        }
        body:not(.portrait).align-v-bottom [class*="overlay_donation_contents"] {
            top: ${maxH - landscapeAlignH + 720}px !important;
        }
        
        /* Landscape Mode: Vertical Align Center */
        body:not(.portrait).align-v-center iframe,
        body:not(.portrait).align-v-center #chzzk_player {
            top: ${(maxH - landscapeAlignH) / 2}px !important;
        }
        body:not(.portrait).align-v-center [class*="overlay_donation_contents"] {
            top: ${(maxH - landscapeAlignH) / 2 + 720}px !important;
        }
    `;
    document.head.appendChild(style);
    console.log('[BCU] Portrait size set to:', width, 'x', height, 'maxH:', maxH);
}

// 후원알림 텍스트 표시/숨기기 함수
function setDonationTextVisible(visible) {
    var existingStyle = document.getElementById('bcu-donation-text-style');
    if (existingStyle) existingStyle.remove();

    if (!visible) {
        var style = document.createElement('style');
        style.id = 'bcu-donation-text-style';
        style.textContent = `
            [class*="overlay_donation_contents"] {
                display: none !important;
            }
        `;
        document.head.appendChild(style);
        console.log('[BCU] Donation text hidden');
    } else {
        console.log('[BCU] Donation text shown');
    }
}

// 3. 비디오 재생 상태 모니터링 (MutationObserver)
(function () {
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

        const callback = function (mutationsList, observer) {
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
(function () {
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

        } catch (e) {
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
    };

    // 8. BCU Force Connect (Buffer Reset) - 영상 강제 연결
    (function () {
        // Iframe Logic: Listen for force connect command
        if (window.top !== window.self) {
            window.addEventListener('message', function (e) {
                if (e.data === 'BCU_FORCE_CONNECT') {
                    console.log('[BCU] Force connect executing in iframe...');

                    // Strategy 1: Direct Player Object API (Best for YouTube)
                    var player = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
                    if (player && player.seekTo && typeof player.seekTo === 'function') {
                        console.log('[BCU] Using movie_player API');
                        try {
                            var dur = player.getDuration();
                            var curr = player.getCurrentTime();

                            // Seek to near end to clear "end" state
                            player.seekTo(dur - 3, true);

                            setTimeout(function () {
                                // Seek back to original time
                                player.seekTo(curr, true);
                                player.playVideo();
                            }, 10);
                            return; // Success
                        } catch (err) {
                            console.log('[BCU] Player API error:', err);
                        }
                    }

                    // Strategy 3: HTML5 Video Element (Ultimate Fallback)
                    var v = document.querySelector('video');
                    if (v && v.duration) {
                        console.log('[BCU] Using HTML5 Video API Fallback');
                        let t = v.currentTime;
                        let d = v.duration;

                        v.currentTime = d - 3;
                        setTimeout(function () {
                            v.currentTime = t;
                            v.play();
                        }, 10);
                    }
                }
            });
        }

        // Main Frame Logic
        window.bcuForceConnect = function () {
            console.log('[BCU] Force connect triggered');

            // 1. Send command to all iframes
            const iframes = document.getElementsByTagName('iframe');
            for (let i = 0; i < iframes.length; i++) {
                try {
                    iframes[i].contentWindow.postMessage('BCU_FORCE_CONNECT', '*');
                } catch (e) { }
            }

            // 2. Check local video tags (Direct video file or main frame only)
            // Just for safety, try player API here too
            var player = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
            if (player && player.seekTo && typeof player.seekTo === 'function') {
                try {
                    var dur = player.getDuration();
                    var curr = player.getCurrentTime();
                    player.seekTo(dur - 3, true);
                    setTimeout(function () {
                        player.seekTo(curr, true);
                        player.playVideo();
                    }, 10);
                    return;
                } catch (e) { }
            }

            document.querySelectorAll('video').forEach(v => {
                if (v.duration) {
                    let t = v.currentTime;
                    let d = v.duration;
                    v.currentTime = Math.max(0, d - 3);
                    setTimeout(() => {
                        v.currentTime = t;
                        v.play();
                    }, 10);
                }
            });
        };
    })();

    // 9. BCU Seek To Start - 영상 맨 앞으로 이동 및 일시정지
    (function () {
        // Iframe Logic
        if (window.top !== window.self) {
            window.addEventListener('message', function (e) {
                if (e.data === 'BCU_SEEK_TO_START') {
                    console.log('[BCU] Seek to start in iframe...');
                    var player = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
                    if (player && player.seekTo) {
                        try {
                            player.seekTo(0, true);
                            player.pauseVideo();
                            return;
                        } catch (e) { }
                    }
                    var v = document.querySelector('video');
                    if (v) {
                        v.currentTime = 0;
                        v.pause();
                    }
                }
            });
        }

        // Main Frame Logic
        window.bcuSeekToStart = function () {
            console.log('[BCU] Seek to start triggered');
            const iframes = document.getElementsByTagName('iframe');
            for (let i = 0; i < iframes.length; i++) {
                try { iframes[i].contentWindow.postMessage('BCU_SEEK_TO_START', '*'); } catch (e) { }
            }
            var player = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
            if (player && player.seekTo) {
                try { player.seekTo(0, true); player.pauseVideo(); return; } catch (e) { }
            }
            document.querySelectorAll('video').forEach(v => {
                v.currentTime = 0;
                v.pause();
            });
        };
    })();

    // 10. BCU Toggle Play/Pause - 재생/정지 토글
    (function () {
        // Iframe Logic
        if (window.top !== window.self) {
            window.addEventListener('message', function (e) {
                if (e.data === 'BCU_TOGGLE_PLAY_PAUSE') {
                    console.log('[BCU] Toggle play/pause in iframe...');
                    var player = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
                    if (player && player.getPlayerState) {
                        try {
                            var state = player.getPlayerState();
                            if (state === 1) { player.pauseVideo(); }
                            else { player.playVideo(); }
                            return;
                        } catch (e) { }
                    }
                    var v = document.querySelector('video');
                    if (v) {
                        if (v.paused) { v.play(); }
                        else { v.pause(); }
                    }
                }
            });
        }

        // Main Frame Logic
        window.bcuTogglePlayPause = function () {
            console.log('[BCU] Toggle play/pause triggered');
            const iframes = document.getElementsByTagName('iframe');
            for (let i = 0; i < iframes.length; i++) {
                try { iframes[i].contentWindow.postMessage('BCU_TOGGLE_PLAY_PAUSE', '*'); } catch (e) { }
            }
            var player = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
            if (player && player.getPlayerState) {
                try {
                    var state = player.getPlayerState();
                    if (state === 1) { player.pauseVideo(); } else { player.playVideo(); }
                    return;
                } catch (e) { }
            }
            document.querySelectorAll('video').forEach(v => {
                if (v.paused) { v.play(); } else { v.pause(); }
            });
        };
    })();

    // Periodic fallback (just in case) - 1000ms
    setInterval(() => {
        const iframe = document.getElementById('chzzk_player');
        if (iframe) {
            try {
                const v = iframe.contentWindow.document.querySelector('video');
                if (v) reportResolution(v);
            } catch (e) { }
        }
    }, 1000);
    // 6. Force Iframe Permissions (Encrypted Media for YouTube)
    (function () {
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

// 7. BCU Video End Control - 영상 종료 제어 기능
(function () {
    // 영상 강제 종료 함수 (재생바를 맨 뒤로 이동 - 기존 방식)
    window.bcuForceVideoEnd = function () {
        console.log('[BCU] Force video end triggered (seek to end)');

        // 1. YouTube iframe 찾기
        const ytIframe = document.querySelector('iframe[src*="youtube.com"], iframe[src*="youtube-nocookie.com"]');
        if (ytIframe) {
            try {
                ytIframe.contentWindow.postMessage(JSON.stringify({
                    event: 'command',
                    func: 'seekTo',
                    args: [99999, true]
                }), '*');
            } catch (e) { console.log('[BCU] postMessage error:', e); }
        }

        // 2. Chzzk 클립 iframe 찾기
        const chzzkIframe = document.getElementById('chzzk_player');
        if (chzzkIframe) {
            try {
                const video = chzzkIframe.contentWindow.document.querySelector('video');
                if (video) {
                    video.currentTime = video.duration || 99999;
                }
            } catch (e) { }
        }

        // 3. 직접 video 요소 찾기
        document.querySelectorAll('video').forEach(v => {
            try { v.currentTime = v.duration || 99999; } catch (e) { }
        });
    };

    // 강제 스킵 함수 (4개 API 순차 호출)
    window.bcuForceSkip = async function () {
        console.log('[BCU] Force skip triggered (4 API calls)');

        try {
            const url = window.location.href;
            const channelMatch = url.match(/video-donation\/([^?]+)/);
            const channelId = channelMatch ? channelMatch[1] : null;
            const donationId = window._bcuCurrentDonationId;
            const videoId = window._bcuCurrentVideoId || 'unknown';
            const payAmount = window._bcuCurrentPayAmount || 0;
            const videoType = window._bcuCurrentVideoType || 'YOUTUBE';

            if (!channelId || !donationId) {
                console.log('[BCU] No channelId or donationId found. channelId:', channelId, 'donationId:', donationId);
                return;
            }

            const neloHeaders = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site'
            };

            const neloBaseBody = {
                projectName: 'P519917_glive-fe-pc',
                projectVersion: '0.0.1',
                txtToken: '4d82d7d6ac304ac39a05387c9ad5d807',
                userAgent: navigator.userAgent.toLowerCase()
            };

            // 1. VIDEO_DONATION_STOPPED
            console.log('[BCU] Sending 1/4: VIDEO_DONATION_STOPPED');
            await fetch('https://kr-col-ext.nelo.navercorp.com/_store', {
                method: 'POST',
                headers: neloHeaders,
                referrer: url,
                referrerPolicy: 'unsafe-url',
                body: JSON.stringify({
                    ...neloBaseBody,
                    logLevel: 'DEBUG',
                    body: `VIDEO_DONATION_STOPPED channelId: ${channelId}, donationId: ${donationId}, videoId: ${videoId}, videoType: ${videoType}, playMode: VIDEO_PLAY, tierNo: undefined, payAmount: ${payAmount}, donationId: ${donationId}`
                }),
                mode: 'cors',
                credentials: 'omit'
            }).then(r => r.json()).then(d => console.log('[BCU] 1/4 response:', d)).catch(e => console.log('[BCU] 1/4 error:', e));

            // 2. VIDEO_DONATION_VIDEO_PLAYBACK_ENDED
            console.log('[BCU] Sending 2/4: VIDEO_DONATION_VIDEO_PLAYBACK_ENDED');
            await fetch('https://kr-col-ext.nelo.navercorp.com/_store', {
                method: 'POST',
                headers: neloHeaders,
                referrer: url,
                referrerPolicy: 'unsafe-url',
                body: JSON.stringify({
                    ...neloBaseBody,
                    logLevel: 'DEBUG',
                    body: `VIDEO_DONATION_VIDEO_PLAYBACK_ENDED channelId: ${channelId}, donationId: ${donationId}, videoId: ${videoId}, videoType: ${videoType}, playMode: VIDEO_PLAY, tierNo: undefined, payAmount: ${payAmount}`
                }),
                mode: 'cors',
                credentials: 'omit'
            }).then(r => r.json()).then(d => console.log('[BCU] 2/4 response:', d)).catch(e => console.log('[BCU] 2/4 error:', e));

            // 3. VIDEO_DONATION_VIDEO_END_ACTION
            console.log('[BCU] Sending 3/4: VIDEO_DONATION_VIDEO_END_ACTION');
            await fetch('https://kr-col-ext.nelo.navercorp.com/_store', {
                method: 'POST',
                headers: neloHeaders,
                referrer: url,
                referrerPolicy: 'unsafe-url',
                body: JSON.stringify({
                    ...neloBaseBody,
                    logLevel: 'INFO',
                    body: `VIDEO_DONATION_VIDEO_END_ACTION channelId: ${channelId}, donationId: ${donationId}, videoId: ${videoId}, videoType: ${videoType}, playMode: VIDEO_PLAY, tierNo: undefined, payAmount: ${payAmount}`
                }),
                mode: 'cors',
                credentials: 'omit'
            }).then(r => r.json()).then(d => console.log('[BCU] 3/4 response:', d)).catch(e => console.log('[BCU] 3/4 error:', e));

            // 4. PUT /end API
            console.log('[BCU] Sending 4/4: PUT /end API');
            await fetch(`https://api.chzzk.naver.com/manage/v1/video-session/${channelId}/donations/${donationId}/end`, {
                method: 'PUT',
                headers: {
                    'Accept': 'application/json, text/plain, */*',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'If-Modified-Since': 'Mon, 26 Jul 1997 05:00:00 GMT',
                    'Front-Client-Platform-Type': 'PC',
                    'Front-Client-Product-Type': 'web',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site'
                },
                referrer: url,
                referrerPolicy: 'unsafe-url',
                body: null,
                mode: 'cors',
                credentials: 'include'
            }).then(r => r.json()).then(d => console.log('[BCU] 4/4 response:', d)).catch(e => console.log('[BCU] 4/4 error:', e));

            console.log('[BCU] All 4 API calls completed!');

        } catch (e) { console.log('[BCU] Force skip API call error:', e); }
    };

    // fetch 인터셉터로 donationId, videoId, payAmount 추출
    (function () {
        const origFetch = window.fetch;
        window.fetch = function (url, options) {
            try {
                const urlStr = typeof url === 'string' ? url : (url && url.url ? url.url : String(url));

                // /donations/{donationId}/play 패턴에서 donationId 추출
                const donationMatch = urlStr.match(/\/donations\/([^\/]+)\/play/);
                if (donationMatch) {
                    window._bcuCurrentDonationId = donationMatch[1];
                    console.log('[BCU] Captured donationId from fetch:', window._bcuCurrentDonationId);
                }

                // NELO 로그에서 videoId, payAmount 추출
                if (urlStr.includes('nelo.navercorp.com') && options && options.body) {
                    try {
                        const bodyStr = typeof options.body === 'string' ? options.body : '';
                        if (bodyStr.includes('VIDEO_DONATION_RECEIVED') || bodyStr.includes('VIDEO_PLAY_MODE_START')) {
                            const videoIdMatch = bodyStr.match(/videoId:\s*([^,]+)/);
                            const payAmountMatch = bodyStr.match(/payAmount:\s*(\d+)/);
                            const donationIdMatch = bodyStr.match(/donationId:\s*([^,]+)/);
                            const videoTypeMatch = bodyStr.match(/videoType:\s*([^,]+)/);

                            if (videoIdMatch) {
                                window._bcuCurrentVideoId = videoIdMatch[1].trim();
                                console.log('[BCU] Captured videoId:', window._bcuCurrentVideoId);
                            }
                            if (payAmountMatch) {
                                window._bcuCurrentPayAmount = parseInt(payAmountMatch[1]);
                                console.log('[BCU] Captured payAmount:', window._bcuCurrentPayAmount);
                            }
                            if (donationIdMatch && !window._bcuCurrentDonationId) {
                                window._bcuCurrentDonationId = donationIdMatch[1].trim();
                                console.log('[BCU] Captured donationId from NELO:', window._bcuCurrentDonationId);
                            }
                            if (videoTypeMatch) {
                                window._bcuCurrentVideoType = videoTypeMatch[1].trim();
                                console.log('[BCU] Captured videoType:', window._bcuCurrentVideoType);
                            }
                        }
                    } catch (e) { }
                }
            } catch (e) { }
            return origFetch.apply(this, arguments);
        };
    })();

    // XMLHttpRequest 인터셉터 (백업)
    (function () {
        const origOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function (method, url) {
            try {
                const urlStr = typeof url === 'string' ? url : String(url);
                const donationMatch = urlStr.match(/\/donations\/([^\/]+)\/play/);
                if (donationMatch) {
                    window._bcuCurrentDonationId = donationMatch[1];
                    console.log('[BCU] Captured donationId from XHR:', window._bcuCurrentDonationId);
                }
            } catch (e) { }
            return origOpen.apply(this, arguments);
        };
    })();
})();