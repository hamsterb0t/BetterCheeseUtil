(function () {
    // 1. 채팅창의 모든 닉네임 요소 선택
    const nicknames = document.querySelectorAll('[class*="live_chatting_message_nickname__"]');

    if (nicknames.length === 0) {
        console.log('채팅 메시지가 없습니다.');
        return;
    }

    // 2. 가장 마지막(최신) 닉네임 선택
    const lastNickname = nicknames[0];

    // 3. 팝업이 뜨는 것을 감지하는 감시자(Observer) 정의
    const observer = new MutationObserver((mutations, obs) => {
        // DOM에 변화가 생길 때마다 실행되는 부분
        const popupBtn = document.querySelector('button[aria-label="팝업으로 열기"]');

        if (popupBtn) {
            console.log('팝업 버튼 감지 성공! 클릭합니다.');
            popupBtn.click();

            // 목적을 달성했으므로 감시를 중단합니다 (성능 최적화)
            obs.disconnect();
        }
    });

    // 4. 감시 시작 (body 전체의 변화를 감시하여 팝업이 추가되는지 확인)
    observer.observe(document.body, {
        childList: true, // 자식 노드 추가/제거 감지
        subtree: true    // 하위 모든 요소 감지
    });

    // 5. 감시를 켜둔 상태에서 닉네임 클릭
    console.log('마지막 채팅 유저 클릭:', lastNickname.textContent);
    lastNickname.click();

    // (선택사항) 만약 5초가 지나도 팝업이 안 뜨면 감시를 강제로 종료하는 안전장치
    setTimeout(() => {
        observer.disconnect();
    }, 5000);
})();