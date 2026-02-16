(function () {
    // console.log('스크립트 실행 중 (v12)...');

    // --- 1. 주요 요소 선택 ---
    const header = document.querySelector('[class^="header_wrap"]');
    const nav = document.getElementById('navigation_bar');

    // [핵심] 너비를 리셋할 모든 부모 요소
    const layoutContent = document.querySelector('[class^="layout_content"]');
    const layoutSection = document.querySelector('[class^="layout_section"]');
    const mainArea = document.querySelector('[class^="layout_area"]');
    const layoutInner = document.querySelector('[class^="layout_inner"]');
    const infoColumn = document.querySelector('[class^="live_information_column"]');
    const infoInner = document.querySelector('[class^="live_information_inner"]');
    const infoSection = document.querySelector('[class^="live_information_section"]');

    // 숨길 요소들
    const videoPlayer = document.querySelector('[class^="live_information_main"]');
    const adTimeline = document.querySelector('[class^="live_information_aside"]');
    const entireRightColumn = document.querySelector('[class^="live_aside_columns"]');
    const resizeHandles = document.querySelectorAll('[class^="handle"]');

    // '빠른 설정' (이동할 요소)
    const quickSettings = document.querySelectorAll('[class^="live_aside_container"]')[1];
    const infoFormContent = document.querySelector('[class^="live_form_content"]');

    // --- 2. 유효성 검사 ---
    if (!quickSettings || !infoFormContent || !entireRightColumn) {
        console.error('스크립트 오류: "빠른 설정" 또는 "방송 정보 폼" 요소를 찾을 수 없습니다.');
        return;
    }

    // --- 3. 불필요한 요소 숨기기 ---
    if (header) header.style.display = 'none';
    if (nav) nav.style.display = 'none';
    if (videoPlayer) videoPlayer.style.display = 'none';
    if (adTimeline) adTimeline.style.display = 'none';
    if (entireRightColumn) entireRightColumn.style.display = 'none';
    resizeHandles.forEach(handle => handle.style.display = 'none');

    // --- 4. [핵심] 너비 고정 문제 해결 (모든 상위 요소 너비 리셋) ---
    [layoutContent, layoutSection, mainArea, layoutInner, infoColumn, infoInner, infoSection].forEach(el => {
        if (el) {
            el.style.padding = '0px';
            el.style.margin = '0px';
            el.style.width = '100%';
            el.style.minWidth = '0';
            el.style.maxWidth = 'none'; // 630px 같은 최대 너비 제한 해제
        }
    });
    // layoutSection은 flex 컨테이너로 유지
    if (layoutSection) layoutSection.style.display = 'flex';
    if (mainArea) mainArea.style.display = 'flex';


    // --- 5. DOM 구조 변경 (빠른 설정 이동) ---
    const quickSettingsHeader = quickSettings.querySelector('[class^="live_component_header"]');
    if (quickSettingsHeader) quickSettingsHeader.style.display = 'none';
    quickSettings.style.height = 'auto';

    const infoFormParent = infoFormContent.parentElement;
    if (infoFormParent) {
        infoFormParent.insertBefore(quickSettings, infoFormContent);
        // console.log('✅ DOM 이동 완료: "빠른 설정"을 "방송 정보 폼" 앞으로 이동');
    }

    // --- 6. "빠른 설정" 내부 항목 숨기기 ('방송 설정' 섹션) ---
    const quickSettingsList = quickSettings.querySelector('[class^="live_setting_list"]');

    const hideBroadcastSettingsItems = () => {
        if (!quickSettingsList) return;

        let hideFollowing = false;
        for (const child of quickSettingsList.children) {
            // 1. '방송 설정' 헤더 찾기
            if (child.matches('[class^="live_setting_header"]') && child.textContent.includes('방송 설정')) {
                hideFollowing = true;
            }

            // 2. 숨기기 로직
            if (hideFollowing) {
                child.style.display = 'none';
            }
            // 3. '승부예측' 등 특정 키워드 포함 시 숨기기 (헤더 인식 실패 대비)
            else if (child.textContent.includes('승부예측')) {
                child.style.display = 'none';
            }
        }
    };

    if (quickSettingsList) {
        // 1. 초기 실행
        hideBroadcastSettingsItems();

        // 2. 동적 변경 감지 (MutationObserver)
        const observer = new MutationObserver((mutations) => {
            hideBroadcastSettingsItems();
        });

        observer.observe(quickSettingsList, { childList: true });
    }

    // --- 7. '방송 정보' 내부 항목 토글 기능 ---
    let settingsHidden = false;

    window.toggleBroadcastSettings = function () {
        settingsHidden = !settingsHidden;
        if (!infoFormContent) return;

        const allFormAreas = infoFormContent.querySelectorAll('[class^="form_area"]');

        for (const area of allFormAreas) {
            const label = area.querySelector('label');
            let isKeeper = false;

            if (label) {
                const labelFor = label.getAttribute('for');
                if (labelFor === 'title' || labelFor === 'category') isKeeper = true;
            }

            if (!isKeeper) {
                const defaultDisplay = area.className.includes('horizontal') ? 'flex' : 'block';
                area.style.display = settingsHidden ? 'none' : defaultDisplay;
            }
        }

        const partyArea = infoSection.querySelector('[class^="live_form_party_area"]');
        if (partyArea) partyArea.style.display = settingsHidden ? 'none' : 'block';

        const toggleBtn = document.getElementById('customToggleBtn');
        if (toggleBtn) toggleBtn.textContent = settingsHidden ? '방송 세부 설정 보이기' : '방송 세부 설정 숨기기';
    };

    // --- 8. 토글 버튼 UI에 추가 (중복 방지 및 위치 수정) ---
    if (infoFormParent && !document.getElementById('customToggleBtn')) {
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'customToggleBtn';
        toggleBtn.textContent = '방송 세부 설정 보이기';

        // 스타일
        toggleBtn.style.width = '100%';
        toggleBtn.style.padding = '12px';
        toggleBtn.style.fontSize = '15px';
        toggleBtn.style.fontWeight = 'bold';
        toggleBtn.style.backgroundColor = '#00D685';
        toggleBtn.style.color = '#101014';
        toggleBtn.style.border = 'none';
        toggleBtn.style.borderRadius = '8px';
        toggleBtn.style.cursor = 'pointer';
        toggleBtn.style.margin = '10px 0 15px 0';

        toggleBtn.onclick = window.toggleBroadcastSettings;

        infoFormParent.insertBefore(toggleBtn, infoFormContent);

        // 최초 실행 시 숨김 처리
        window.toggleBroadcastSettings();

        // console.log('✅ 토글 버튼 생성 완료.');
    }

    // console.log('✅ (v12) 레이아웃 재구성 및 너비 제한 해제 완료.');

    // --- 9. webplayer-internal-video 자동 정지 (리소스 절약) ---
    const pauseInternalVideo = (video) => {
        if (video && !video.paused) {
            video.pause();
            // console.log('✅ webplayer-internal-video 자동 정지됨');
        }
    };

    const setupVideoAutoPause = (video) => {
        if (!video || video.dataset.autoPauseSet) return;
        video.dataset.autoPauseSet = 'true';

        // 이미 재생 중이면 즉시 정지
        pauseInternalVideo(video);

        // play 이벤트 발생 시 정지
        video.addEventListener('play', () => {
            video.pause();
            // console.log('✅ webplayer-internal-video 재생 시도 감지 → 자동 정지');
        });
    };

    // 현재 존재하는 비디오 처리
    const existingVideos = document.querySelectorAll('.webplayer-internal-video');
    existingVideos.forEach(setupVideoAutoPause);

    // 동적으로 추가되는 비디오 감지 (MutationObserver)
    const videoObserver = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.classList && node.classList.contains('webplayer-internal-video')) {
                        setupVideoAutoPause(node);
                    }
                    // 자식 요소 중에서도 찾기
                    const childVideos = node.querySelectorAll ? node.querySelectorAll('.webplayer-internal-video') : [];
                    childVideos.forEach(setupVideoAutoPause);
                }
            }
        }
    });

    videoObserver.observe(document.body, { childList: true, subtree: true });


})();