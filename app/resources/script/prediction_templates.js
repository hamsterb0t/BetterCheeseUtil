(function () {
    console.log("[BCU] Prediction Templates Script Loaded (UI Overhaul V3: CSS Fixes)");

    const SELECTORS = {
        POPUP_CONTAINER: '.popup_container__Aqx-3',
        FORM_LIST: ('.form_list__0xtml'), // Injects below this
        TITLE_INPUT: '#prediction-name',
        TIME_BUTTON: '#prediction-time',
        ADD_OPTION_BTN: '.prediction_create_add_button__7EQoQ button',
        OPTION_LIST: 'ol',
        OPTION_INPUT: 'input[id^="prediction-item-"]',
    };

    const STYLE_COLOR = '#463ac5';

    let templates = [];

    // --- Data Management ---
    async function fetchData() {
        try {
            const res = await fetch('http://127.0.0.1:5000/api/prediction/templates');
            const data = await res.json();
            templates = data.templates || [];
            renderUI();
        } catch (e) {
            console.error("[BCU] Failed to fetch templates", e);
        }
    }

    async function saveTemplate(name, formData) {
        try {
            const payload = { name, ...formData };
            await fetch('http://127.0.0.1:5000/api/prediction/template', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            fetchData();
        } catch (e) {
            console.error("[BCU] Failed to save template", e);
        }
    }

    async function deleteTemplate(id) {
        try {
            await fetch(`http://127.0.0.1:5000/api/prediction/template?id=${id}`, {
                method: 'DELETE'
            });
            fetchData();
        } catch (e) {
            console.error("[BCU] Failed to delete template", e);
        }
    }

    async function updateAllTemplates(newTemplates) {
        try {
            await fetch('http://127.0.0.1:5000/api/prediction/templates', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newTemplates)
            });
            fetchData();
        } catch (e) {
            console.error("[BCU] Failed to update templates", e);
        }
    }

    // --- Form Automation ---
    function getFormState() {
        const title = document.querySelector(SELECTORS.TITLE_INPUT)?.value || "";
        const timeBtn = document.querySelector(SELECTORS.TIME_BUTTON);
        const time = timeBtn ? timeBtn.innerText.trim() : "10분";

        const options = [];
        const inputs = document.querySelectorAll(SELECTORS.OPTION_INPUT);
        inputs.forEach(input => {
            if (input.value.trim()) options.push(input.value.trim());
        });

        return { title, options, time };
    }

    async function applyData(data) {
        // 1. Title
        const titleInput = document.querySelector(SELECTORS.TITLE_INPUT);
        if (titleInput) {
            setNativeValue(titleInput, data.title);
        }

        // 2. Options
        const optionList = document.querySelector(SELECTORS.OPTION_LIST);
        if (optionList) {
            let currentInputs = Array.from(document.querySelectorAll(SELECTORS.OPTION_INPUT));
            const targetCount = data.options.length;

            // Remove extra
            while (currentInputs.length > targetCount && currentInputs.length > 2) {
                const lastItem = currentInputs[currentInputs.length - 1].closest('li');
                const delBtn = lastItem.querySelector('button');
                if (delBtn) {
                    delBtn.click();
                    await sleep(50);
                    currentInputs = Array.from(document.querySelectorAll(SELECTORS.OPTION_INPUT));
                } else {
                    break;
                }
            }

            // Add new
            const addBtn = document.querySelector(SELECTORS.ADD_OPTION_BTN);
            while (currentInputs.length < targetCount) {
                if (addBtn) {
                    addBtn.click();
                    await sleep(50);
                    currentInputs = Array.from(document.querySelectorAll(SELECTORS.OPTION_INPUT));
                } else {
                    break;
                }
            }

            // Set values
            currentInputs.forEach((input, idx) => {
                if (idx < targetCount) {
                    setNativeValue(input, data.options[idx]);
                } else {
                    setNativeValue(input, "");
                }
            });
        }

        // 3. Time
        const timeBtn = document.querySelector(SELECTORS.TIME_BUTTON);
        if (timeBtn && timeBtn.innerText.trim() !== data.time) {
            timeBtn.click();
            await sleep(200);

            // Heuristic to find dropdown options
            let found = false;
            const options = document.querySelectorAll('button');
            for (let btn of options) {
                if (btn.innerText.trim() === data.time) {
                    if (btn.closest('[class*="selectbox_list"], [role="listbox"]')) {
                        btn.click();
                        found = true;
                        break;
                    }
                }
            }
            if (!found) timeBtn.click();
        }
    }

    function setNativeValue(element, value) {
        const lastValue = element.value;
        element.value = value;
        const event = new Event('input', { bubbles: true });
        const tracker = element._valueTracker;
        if (tracker) {
            tracker.setValue(lastValue);
        }
        element.dispatchEvent(event);
    }

    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    // --- Modal Component ---
    function showAddModal() {
        // Overlay using Object.assign
        const modal = document.createElement('div');
        Object.assign(modal.style, {
            position: 'fixed', top: '0', left: '0', width: '100%', height: '100%',
            background: 'rgba(0,0,0,0.5)', zIndex: '9999', display: 'flex',
            justifyContent: 'center', alignItems: 'center'
        });

        // Inner HTML with explicit CSS (kebab-case)
        modal.innerHTML = `
            <div style="background: white; width: 500px; border: 2px solid ${STYLE_COLOR}; display: flex; flex-direction: column;">
                <div style="background: ${STYLE_COLOR}; color: white; padding: 15px; text-align: center; font-size: 20px; font-weight: bold;">프리셋 추가</div>
                <div style="padding: 30px; color: #333;">
                    <div style="margin-bottom: 30px;">
                        <label style="display:block; margin-bottom: 10px; font-weight:bold; font-size: 16px;">프리셋 제목:</label>
                        <input type="text" id="bcu-new-tpl-name" style="width:100%; padding: 10px; border:1px solid #ccc; background:#f5f5f5; color:#333; border-radius:4px; font-size: 16px; box-sizing: border-box;">
                    </div>
                    <div style="text-align:center; color:#666; font-size: 14px; line-height: 1.5;">
                        현재 입력된 설정값으로<br>
                        새로운 프리셋을 추가합니다.
                    </div>
                </div>
                <div style="padding: 20px; display: flex; justify-content: center; gap: 20px; border-top: 1px solid #eee;">
                    <button id="bcu-modal-confirm" style="background: ${STYLE_COLOR}; color: white; border: none; padding: 10px 40px; font-size: 16px; cursor: pointer; border-radius: 4px; font-weight: bold;">예</button>
                    <button id="bcu-modal-cancel" style="background: #ccc; color: #333; border: none; padding: 10px 40px; font-size: 16px; cursor: pointer; border-radius: 4px; font-weight: bold;">아니오</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        document.getElementById('bcu-modal-cancel').onclick = () => document.body.removeChild(modal);
        document.getElementById('bcu-modal-confirm').onclick = () => {
            const name = document.getElementById('bcu-new-tpl-name').value;
            if (name) {
                saveTemplate(name, getFormState());
                document.body.removeChild(modal);
            } else {
                alert("프리셋 제목을 입력해주세요.");
            }
        };
    }

    function showEditModal() {
        let localTemplates = [...templates];

        const renderList = (container) => {
            container.innerHTML = '';
            localTemplates.forEach((tpl, index) => {
                const item = document.createElement('div');
                Object.assign(item.style, {
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '12px', borderBottom: '1px solid #eee', background: 'white', marginBottom: '8px',
                    borderRadius: '4px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                });

                item.innerHTML = `
                    <div style="flex: 1; overflow: hidden; padding-right: 15px;">
                        <div style="font-weight: bold; color: ${STYLE_COLOR}; margin-bottom: 4px; font-size: 15px;">${tpl.name}</div>
                        <div style="font-size: 13px; color: #666;">${tpl.title || "제목없음"} (항목 ${tpl.options.length}개 | ${tpl.time})</div>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <div style="display: flex; flex-direction: column; gap: 2px;">
                            <button class="move-up" style="background: white; border: 1px solid #ddd; cursor: pointer; width: 30px; height: 30px; display: flex; justify-content: center; align-items: center; border-radius: 4px;" ${index === 0 ? 'disabled' : ''}>▲</button>
                            <button class="move-down" style="background: white; border: 1px solid #ddd; cursor: pointer; width: 30px; height: 30px; display: flex; justify-content: center; align-items: center; border-radius: 4px;" ${index === localTemplates.length - 1 ? 'disabled' : ''}>▼</button>
                        </div>
                        <button class="delete" style="background: white; border: 1px solid #ff4444; color: #ff4444; cursor: pointer; width: 40px; height: 62px; display: flex; justify-content: center; align-items: center; border-radius: 4px; margin-left: 5px;">X</button>
                    </div>
                `;

                // Add hover states manually
                const btns = item.querySelectorAll('button:not([disabled])');
                btns.forEach(btn => {
                    btn.onmouseenter = () => btn.style.background = '#f5f5f5';
                    btn.onmouseleave = () => btn.style.background = 'white';
                });

                item.querySelector('.move-up').onclick = () => {
                    if (index > 0) {
                        [localTemplates[index], localTemplates[index - 1]] = [localTemplates[index - 1], localTemplates[index]];
                        renderList(container);
                    }
                };
                item.querySelector('.move-down').onclick = () => {
                    if (index < localTemplates.length - 1) {
                        [localTemplates[index], localTemplates[index + 1]] = [localTemplates[index + 1], localTemplates[index]];
                        renderList(container);
                    }
                };
                item.querySelector('.delete').onclick = () => {
                    // if (confirm(`'${tpl.name}' 프리셋을 삭제하시겠습니까?`)) { // Removed confirm
                    localTemplates.splice(index, 1);
                    renderList(container);
                    // }
                };

                container.appendChild(item);
            });
        };

        const modal = document.createElement('div');
        Object.assign(modal.style, {
            position: 'fixed', top: '0', left: '0', width: '100%', height: '100%',
            background: 'rgba(0,0,0,0.5)', zIndex: '9999', display: 'flex',
            justifyContent: 'center', alignItems: 'center'
        });

        // increased width to 500px
        modal.innerHTML = `
            <div style="background: white; width: 500px; border: 2px solid ${STYLE_COLOR}; display: flex; flex-direction: column; max-height: 80vh;">
                <div style="background: ${STYLE_COLOR}; color: white; padding: 15px; text-align: center; font-size: 20px; font-weight: bold;">프리셋 편집</div>
                <div style="padding: 20px; color: #333; overflow-y: auto; background: #f5f5f5; flex: 1;">
                    <div id="bcu-edit-list"></div>
                </div>
                <div style="padding: 20px; display: flex; justify-content: center; gap: 20px; border-top: 1px solid #eee; background: white;">
                    <button id="bcu-edit-save" style="background: ${STYLE_COLOR}; color: white; border: none; padding: 10px 40px; font-size: 16px; cursor: pointer; border-radius: 4px; font-weight: bold;">저장</button>
                    <button id="bcu-edit-cancel" style="background: #ccc; color: #333; border: none; padding: 10px 40px; font-size: 16px; cursor: pointer; border-radius: 4px; font-weight: bold;">취소</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        const listContainer = document.getElementById('bcu-edit-list');
        renderList(listContainer);

        document.getElementById('bcu-edit-cancel').onclick = () => document.body.removeChild(modal);
        document.getElementById('bcu-edit-save').onclick = () => {
            updateAllTemplates(localTemplates);
            document.body.removeChild(modal);
        };
    }


    // --- UI Render ---
    function renderUI() {
        let container = document.getElementById('bcu-template-container');
        if (!container) return;

        container.innerHTML = '';

        // Header Row
        const headerRow = document.createElement('div');
        Object.assign(headerRow.style, {
            display: 'flex', alignItems: 'center', marginBottom: '15px'
        });

        const label = document.createElement('span');
        label.innerText = '프리셋';
        Object.assign(label.style, {
            fontWeight: 'bold', fontSize: '18px', marginRight: '15px', color: '#333'
        });
        headerRow.appendChild(label);

        const createBtn = (text, onClick) => {
            const btn = document.createElement('button');
            btn.innerText = text;
            btn.onclick = onClick;
            Object.assign(btn.style, {
                background: STYLE_COLOR, color: 'white', border: 'none',
                borderRadius: '4px', padding: '6px 16px', marginRight: '8px',
                cursor: 'pointer', fontSize: '14px', fontWeight: 'bold',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            });
            btn.onmouseenter = () => btn.style.transform = 'translateY(-1px)';
            btn.onmouseleave = () => btn.style.transform = 'translateY(0)';
            btn.style.transition = 'transform 0.1s';
            return btn;
        };

        headerRow.appendChild(createBtn('추가', showAddModal));
        headerRow.appendChild(createBtn('편집', showEditModal));

        container.appendChild(headerRow);

        // Scroll Container
        const scrollContainer = document.createElement('div');
        Object.assign(scrollContainer.style, {
            position: 'relative', display: 'flex', alignItems: 'center',
            background: '#f9f9f9', padding: '10px 0', borderRadius: '8px'
        });

        const navBtnStyle = {
            background: 'white', border: '1px solid #ddd', color: '#555', fontSize: '18px',
            cursor: 'pointer', padding: '0', width: '32px', height: '32px',
            borderRadius: '50%', display: 'flex', justifyContent: 'center', alignItems: 'center',
            boxShadow: '0 2px 4px rgba(0,0,0,0.05)', marginLeft: '5px', marginRight: '5px'
        };

        const leftBtn = document.createElement('button');
        leftBtn.innerText = '◀';
        Object.assign(leftBtn.style, navBtnStyle);
        leftBtn.onclick = () => {
            document.getElementById('bcu-scroll-content').scrollBy({ left: -200, behavior: 'smooth' });
        };

        const rightBtn = document.createElement('button');
        rightBtn.innerText = '▶';
        Object.assign(rightBtn.style, navBtnStyle);
        rightBtn.onclick = () => {
            document.getElementById('bcu-scroll-content').scrollBy({ left: 200, behavior: 'smooth' });
        };

        const content = document.createElement('div');
        content.id = 'bcu-scroll-content';
        Object.assign(content.style, {
            display: 'flex', gap: '15px', overflowX: 'auto',
            scrollBehavior: 'smooth', padding: '5px 10px', width: '100%',
            // scrollbarWidth: 'none' removed to show scrollbar
        });

        templates.forEach(tpl => {
            const card = document.createElement('div');
            Object.assign(card.style, {
                background: 'white', border: `1px solid ${STYLE_COLOR}`,
                borderRadius: '6px', minWidth: '160px', maxWidth: '160px',
                padding: '0', cursor: 'pointer', display: 'flex', flexDirection: 'column',
                boxShadow: '0 4px 6px rgba(0,0,0,0.05)', overflow: 'hidden'
            });
            card.onclick = () => applyData(tpl);
            card.onmouseenter = () => {
                card.style.transform = 'translateY(-4px)';
                card.style.boxShadow = '0 8px 12px rgba(0,0,0,0.1)';
            };
            card.onmouseleave = () => {
                card.style.transform = 'translateY(0)';
                card.style.boxShadow = '0 4px 6px rgba(0,0,0,0.05)';
            };
            card.style.transition = 'all 0.2s';

            // Template Name
            const name = document.createElement('div');
            name.innerText = tpl.name;
            Object.assign(name.style, {
                background: STYLE_COLOR, color: 'white',
                padding: '10px', fontSize: '14px', fontWeight: 'bold',
                whiteSpace: 'pre-wrap', wordBreak: 'break-all', textAlign: 'center'
            });

            // Details
            const sub = document.createElement('div');
            Object.assign(sub.style, {
                padding: '10px', fontSize: '12px', color: '#555',
                display: 'flex', flexDirection: 'column', gap: '6px', flex: '1',
                justifyContent: 'center'
            });

            const pTitle = document.createElement('div');
            pTitle.innerText = tpl.title || "(제목 없음)";
            Object.assign(pTitle.style, {
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 'bold'
            });

            const pInfo = document.createElement('div');
            pInfo.innerText = `항목 ${tpl.options.length}개 | ${tpl.time}`;

            sub.appendChild(pTitle);
            sub.appendChild(pInfo);

            card.appendChild(name);
            card.appendChild(sub);
            content.appendChild(card);
        });

        scrollContainer.appendChild(leftBtn);
        scrollContainer.appendChild(content);
        scrollContainer.appendChild(rightBtn);

        container.appendChild(scrollContainer);
    }

    // --- Observer & Injection ---
    const observer = new MutationObserver((mutations) => {
        const isPredictionPage = window.location.href.includes('/prediction');
        if (!isPredictionPage) return;

        const popup = document.querySelector(SELECTORS.POPUP_CONTAINER);
        const formList = document.querySelector(SELECTORS.FORM_LIST);

        if (formList && !document.getElementById('bcu-template-container')) {
            console.log("[BCU] Prediction Form Detected - Injecting UI (Overhaul V3: CSS Fixes)");

            const container = document.createElement('div');
            container.id = 'bcu-template-container';
            Object.assign(container.style, {
                marginTop: '30px', marginBottom: '30px',
                borderTop: '1px solid #ddd', paddingTop: '20px', maxWidth: '100%'
            });

            const style = document.createElement('style');
            style.innerHTML = `
                #bcu-scroll-content::-webkit-scrollbar { height: 6px; }
                #bcu-scroll-content::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
                #bcu-scroll-content::-webkit-scrollbar-thumb { background: #888; border-radius: 3px; }
                #bcu-scroll-content::-webkit-scrollbar-thumb:hover { background: #555; }
            `;
            container.appendChild(style);

            formList.parentNode.insertBefore(container, formList.nextSibling);

            fetchData();
        }
    });

    // --- Initial Template Injection (with Retry) ---
    // This handles cases where the form is already present when script loads
    function tryInjectTemplates() {
        const isPredictionPage = window.location.href.includes('/prediction');
        if (!isPredictionPage) return false;

        const formList = document.querySelector(SELECTORS.FORM_LIST);

        if (formList && !document.getElementById('bcu-template-container')) {
            console.log("[BCU] Prediction Form Detected (Initial) - Injecting UI");

            const container = document.createElement('div');
            container.id = 'bcu-template-container';
            Object.assign(container.style, {
                marginTop: '30px', marginBottom: '30px',
                borderTop: '1px solid #ddd', paddingTop: '20px', maxWidth: '100%'
            });

            const style = document.createElement('style');
            style.innerHTML = `
                .bcu-scroll-content::-webkit-scrollbar { display: none; }
            `;
            container.appendChild(style);

            formList.parentNode.insertBefore(container, formList.nextSibling);

            fetchData();
            return true;
        }
        return false;
    }

    // Try immediately
    if (!tryInjectTemplates()) {
        // Retry every 500ms for up to 10 seconds
        let retryCount = 0;
        const retryInterval = setInterval(() => {
            retryCount++;
            if (tryInjectTemplates() || retryCount >= 20) {
                clearInterval(retryInterval);
            }
        }, 500);
    }

    observer.observe(document.body, { childList: true, subtree: true });

    // --- Cooldown Popup Timer (안내 팝업에서 실시간 쿨타임 표시) ---
    let cooldownTimerInterval = null;
    let cooldownSecondsRemaining = 0;
    let lastProcessedPopupText = '';

    async function fetchCooldownTime() {
        try {
            // Extract channel ID from current URL
            const channelMatch = window.location.href.match(/studio\.chzzk\.naver\.com\/([^/]+)/);
            console.log("[BCU] Channel ID:", channelMatch);
            if (!channelMatch) {
                console.log("[BCU] Could not extract channel ID from URL");
                return null;
            }
            const channelId = channelMatch[1];
            const apiUrl = `https://api.chzzk.naver.com/manage/v1/channels/${channelId}/log-power/prediction/status`;

            console.log("[BCU] Fetching cooldown from:", apiUrl);
            const response = await fetch(apiUrl, { credentials: 'include' });
            const data = await response.json();
            console.log("[BCU] API Response:", data);

            if (data.code === 200 && data.content) {
                return data.content.waitTimeSecondsToCreate || 0;
            }
            return null;
        } catch (e) {
            console.error("[BCU] Failed to fetch cooldown time", e);
            return null;
        }
    }

    function formatCooldownTime(seconds) {
        if (seconds <= 0) return "0초";
        const min = Math.floor(seconds / 60);
        const sec = seconds % 60;
        if (min > 0 && sec > 0) {
            return `${min}분 ${sec}초`;
        } else if (min > 0) {
            return `${min}분`;
        } else {
            return `${sec}초`;
        }
    }

    function findCooldownPopup() {
        // Find the popup container with flexible class matching to handle hash changes
        const popup = document.querySelector('[class*="popup_dimmed"] [class*="popup_container"][role="alertdialog"]');
        if (!popup) return null;

        // Check if title is "안내"
        const title = popup.querySelector('[class*="popup_title"]');
        if (!title || title.innerText.trim() !== '안내') return null;

        // Check if it contains the cooldown message
        const textElement = popup.querySelector('[class*="popup_text"]');
        if (!textElement || !textElement.innerText.includes('승부예측 생성이')) return null;

        return popup;
    }

    function findCooldownTextElement() {
        const popup = findCooldownPopup();
        if (!popup) return null;
        return popup.querySelector('[class*="popup_text"]');
    }

    function updateCooldownPopupText() {
        const el = findCooldownTextElement();
        if (el) {
            const timeStr = formatCooldownTime(cooldownSecondsRemaining);
            // Use inline style for color to avoid dependency on volatile class hashes like live_setting_highlight__fF0jj
            el.innerHTML = `<strong style="color: #4e41db; font-weight: 700;">${timeStr}</strong> 뒤에 새로운 승부예측 생성이 가능합니다.`;
            console.log("[BCU] Updated popup text to:", timeStr);
            return true;
        }
        return false;
    }

    function findPopupWithGuideTitle() {
        return findCooldownPopup();
    }

    function startCooldownPopupTimer(initialSeconds) {
        // Clear any existing timer
        if (cooldownTimerInterval) {
            clearInterval(cooldownTimerInterval);
        }

        cooldownSecondsRemaining = initialSeconds;
        updateCooldownPopupText();

        cooldownTimerInterval = setInterval(() => {
            cooldownSecondsRemaining--;

            // Check if popup is still visible
            const popup = findPopupWithGuideTitle();

            if (!popup || cooldownSecondsRemaining <= 0) {
                console.log("[BCU] Stopping cooldown timer (popup closed or timer finished)");
                clearInterval(cooldownTimerInterval);
                cooldownTimerInterval = null;
                lastProcessedPopupText = '';
                if (cooldownSecondsRemaining <= 0 && popup) {
                    updateCooldownPopupText();
                }
                return;
            }

            updateCooldownPopupText();
        }, 1000);
    }

    // Observer for detecting "안내" popup with cooldown message
    const cooldownPopupObserver = new MutationObserver(async (mutations) => {
        // Check if a popup with "안내" title and cooldown message appeared
        const popup = findPopupWithGuideTitle();
        if (!popup) return;

        // Get current popup text to check if it's a new popup
        const currentPopupText = popup.innerText;
        if (currentPopupText === lastProcessedPopupText) return;

        // Only start if timer is not already running
        if (cooldownTimerInterval) return;

        lastProcessedPopupText = currentPopupText;

        console.log("[BCU] Cooldown popup detected! Fetching exact time...");
        const seconds = await fetchCooldownTime();
        console.log("[BCU] Fetched cooldown seconds:", seconds);

        if (seconds && seconds > 0) {
            console.log(`[BCU] Starting cooldown timer with ${seconds} seconds`);
            startCooldownPopupTimer(seconds);
        } else {
            console.log("[BCU] No valid cooldown time received");
        }
    });

    cooldownPopupObserver.observe(document.body, { childList: true, subtree: true });
    console.log("[BCU] Cooldown popup observer started");

})();
