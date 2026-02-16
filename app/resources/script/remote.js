var scrolling = false;
let observerRunning = false;
let firstNonTier2Index = 0;
let maintainItemsEnabled = loadFromLocalStorage('maintainItemsEnabled', true);

function clickStopNotificationButton() {
  const buttonArea = document.querySelector('[class*="remote_control_aside_footer"]');
  if (buttonArea) {
    const button = buttonArea.querySelectorAll('[class*="button_inner"]')[1];
    if (button) {
      button.click();
    }
  }
}

function clickSkipButton() {
  const buttonArea = document.querySelector('[class*="remote_control_aside_footer"]');
  if (buttonArea) {
    const button = buttonArea.querySelectorAll('[class*="button_inner"]')[0];
    if (button) {
      button.click();
    }
  }
}

function createLoadingOverlay(message, onCancel, autoCloseDuration = null) {
  const existingOverlay = document.querySelector('.loading-overlay');
  if (existingOverlay) {
    if (!existingOverlay.querySelector('.message-div').textContent.includes("재생 완료까지 이 창을")) {
      existingOverlay.style.animation = 'slideUp 0.3s ease-out forwards';
      setTimeout(() => existingOverlay.remove(), 300);
    }
  }

  const overlay = document.createElement('div');
  overlay.className = 'loading-overlay';
  overlay.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 1000;
    animation: slideDown 0.3s ease-out forwards;
  `;

  const messageContainer = document.createElement('div');
  messageContainer.className = 'message-container';
  messageContainer.style.cssText = `
    background: white;
    padding: 15px 30px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: bold;
    color: #333;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    white-space: pre-wrap;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  `;

  const messageDiv = document.createElement('div');
  messageDiv.className = 'message-div';
  messageDiv.textContent = message;
  messageContainer.appendChild(messageDiv);

  if (onCancel) {
    const cancelButton = document.createElement('button');
    cancelButton.textContent = '중지';
    cancelButton.style.cssText = `
      padding: 8px 12px;
      background-color: #ff6666;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
    `;
    cancelButton.addEventListener('click', () => {
      if (overlay.timeoutId) {
        clearTimeout(overlay.timeoutId);
      }
      scrolling = false;
      onCancel();
    });
    messageContainer.appendChild(cancelButton);
  } else {
    if (message !== "영상목록 준비 중..") {
      messageContainer.addEventListener('click', () => removeLoadingOverlay(overlay));
      messageContainer.style.cursor = 'pointer';
    }
  }

  overlay.appendChild(messageContainer);
  document.body.appendChild(overlay);

  if (autoCloseDuration !== null && typeof autoCloseDuration === 'number' && autoCloseDuration > 0) {
    overlay.timeoutId = setTimeout(() => removeLoadingOverlay(overlay), autoCloseDuration * 1000);
  }

  return overlay;
}

function updateLoadingOverlay(message) {
  const messageDiv = document.querySelector('.loading-overlay div div');
  if (messageDiv) {
    messageDiv.textContent = message;
  }
}

function removeLoadingOverlay(overlay) {
  if (overlay && overlay.parentNode) {
    if (overlay.timeoutId) {
      clearTimeout(overlay.timeoutId);
      overlay.timeoutId = null;
    }
    overlay.style.animation = 'slideUp 0.3s ease-out forwards';
    setTimeout(() => {
      if (overlay.parentNode) {
        overlay.remove();
      }
    }, 300);
  }
}

function createLoadingGreyOverlay() {
  const overlay = document.createElement('div');
  overlay.className = 'loading-overlay-grey';
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 900;
  `;
  document.body.appendChild(overlay);
  return overlay;
}

function removeLoadingGreyOverlay() {
  const overlay = document.querySelector('.loading-overlay-grey');
  if (overlay) {
    overlay.remove();
  }
}


function maintain200Items() {
  scrolling = true;
  const container = document.querySelector('[class*="remote_control_content"]');
  const list = container.querySelector('ol');

  if (!container || !list) {
    console.log('Container or list not found');
    scrolling = false;
    return;
  }

  // 설정이 꺼져있으면 실행하지 않음
  if (!maintainItemsEnabled) {
    console.log('maintain200Items is disabled by settings');
    scrolling = false;
    return;
  }
  createLoadingOverlay('영상목록 준비 중.. (0/100)', () => {
    clearInterval(checkInterval);
    removeLoadingOverlay(document.querySelector('.loading-overlay'));
    removeLoadingGreyOverlay();
  }, null);
  createLoadingGreyOverlay();

  let lim = 100;
  let checkInterval = null;

  container.scrollTop = 0;
  console.log("scroll top before starting");

  before = 0;

  function checkAndScroll() {
    scrolling = true;
    container.scrollTop = 0;
    const itemCount = list.children.length;
    updateLoadingOverlay(`영상목록 준비 중.. (${itemCount}/100)`);

    if (itemCount < 100 && lim > 0) {
      container.scrollTop = container.scrollHeight;
      lim--;
      console.log("updating", itemCount);
      console.log(before);
      if (before === itemCount) {
        lim -= 10;
      }
      before = itemCount;
    } else {
      container.scrollTop = 0;
      updateLoadingOverlay(`영상목록 준비 완료 (${itemCount}/100)`);
      removeLoadingOverlay(document.querySelector('.loading-overlay'));
      removeLoadingGreyOverlay();
      scrolling = false;
      console.log('128');
      reapplyPlaybackIndicators();
      console.log('맨 위로 스크롤했습니다.');
      console.log(lim);
      console.log(itemCount);
      before = 0;
      clearInterval(checkInterval);
    }
  }

  checkAndScroll();
  checkInterval = setInterval(checkAndScroll, 350);


  if (observerRunning) { return; }

  // Monitor list changes for refresh (e.g., window restoration)
  const listObserver = new MutationObserver((mutations) => {
    let listRefreshed = false;
    mutations.forEach((mutation) => {
      if (mutation.target === list && (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0)) {
        listRefreshed = true;
      }
    });

    if (listRefreshed && toggleButton && !scrolling && maintainItemsEnabled) {
      console.log('Video list refreshed, rechecking item count...');
      const itemCount = list.children.length;
      if (itemCount >= 100) {
        console.log('영상이 100개 이상입니다..');
        reapplyPlaybackIndicators();
        return;
      }
      scrolling = true;
      createLoadingOverlay('영상목록 준비 중.. (0/100)', () => {
        clearInterval(checkInterval);
        removeLoadingOverlay(document.querySelector('.loading-overlay'));
        removeLoadingGreyOverlay();
      }, null);
      createLoadingGreyOverlay();
      lim = 30; // Reset limit
      clearInterval(checkInterval);
      checkInterval = setInterval(checkAndScroll, 350);
    }
  });

  observerRunning = true;
  listObserver.observe(list, { childList: true, subtree: true });
}

function insertAfter(newNode, existingNode) {
  existingNode.parentNode.insertBefore(newNode, existingNode.nextSibling);
}

let currentButtonObserver = null;
let currentPlayStatusObserver = null;
let predefinedArray = [];
let timeoutIds = [];
let searchResults = [];
let currentSearchIndex = -1;
let toggleButton = false;
let activeSearchMode = null;

function isVideoSupportTabActive() {
  return toggleButton;
}

function toggleButtonsVisibility() {
  console.log("toggleButtonVisibility");
  const isActive = toggleButton;
  if (scrollToPlayingButton) {
    scrollToPlayingButton.style.display = isActive ? 'inline-block' : 'none';
  }
  if (searchButton) {
    searchButton.style.display = isActive ? 'inline-block' : 'none';
  }
  if (unplayedSearchButton) {
    unplayedSearchButton.style.display = isActive ? 'inline-block' : 'none';
  }
  if (searchContainer) {
    searchContainer.style.display = isActive ? 'flex' : 'none';
  }
}

function toggleButtonsVisibilityTrue() {
  toggleButton = true;
  toggleButtonsVisibility();
}

const videoSupportButton = Array.from(
  document.querySelectorAll('[class*="remote_control_tablist"] button')
).find(button =>
  button.querySelector('[class*="remote_control_label"]').textContent === '영상 후원'
);

document.querySelectorAll('[class*="remote_control_tablist"] button').forEach(button => {
  if (button !== videoSupportButton) {
    button.addEventListener('click', () => {
      toggleButton = false;
      toggleButtonsVisibility();
      updateSearchBarsVisibility();
      closeSearchBar();
    });
  } else {
    button.addEventListener('click', () => {
      setTimeout(() => {
        console.log('208');
        if (maintainItemsEnabled) {
          maintain200Items();
        }
        toggleButton = true;
        toggleButtonsVisibility();
        updateSearchBarsVisibility();
        console.log('213');
      }, 100);
    });
  }
});

const style = document.createElement('style');
style.textContent = `
  @keyframes slideDown {
    from { transform: translateY(-100px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
  @keyframes slideUp {
    from { transform: translateY(0); opacity: 1; }
    to { transform: translateY(-100px); opacity: 0; }
  }
`;
document.head.appendChild(style);

let scrollToPlayingButton = null;
let searchButton = null;
let unplayedSearchButton = null;
let searchContainer = null;

if (!document.querySelector('#sidebarToggle')) {
  const remotemain = document.querySelector('[class*="remote_control_content"]');
  remotemain.style.padding = '10px 0px';

  const remoteTitle = document.querySelector('[class*="remote_control_title"]');
  remoteTitle.style.display = 'none';

  const remoteHeader = document.querySelector('[class*="remote_control_header"]');
  remoteHeader.style.padding = '0 0px 0 0px';

  const sidebar_element = document.querySelector('[class*="remote_control_aside_container"]');
  sidebar_element.style.padding = '5px';

  const sidebarToggle = document.createElement('input');
  sidebarToggle.type = 'checkbox';
  sidebarToggle.checked = loadFromLocalStorage('sidebarToggle', false); // [MODIFIED] Load state
  sidebarToggle.id = 'sidebarToggle';
  sidebarToggle.style.marginRight = '5px';

  const sidebarLabel = document.createElement('label');
  sidebarLabel.htmlFor = 'sidebarToggle';
  sidebarLabel.innerText = '사이드바';
  sidebarLabel.style.cursor = 'pointer';

  scrollToPlayingButton = document.createElement('button');
  scrollToPlayingButton.textContent = '현재 재생중';
  scrollToPlayingButton.style.cssText = `
    margin-left: 10px;
    padding: 8px 12px;
    background-color: #28a745;
    color: #fff;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    display: ${isVideoSupportTabActive() ? 'inline-block' : 'none'};
  `;
  scrollToPlayingButton.addEventListener('click', () => {
    const container = document.querySelector('[class*="remote_control_content"]');
    // remote_control_feed_active 클래스를 가진 요소 중 가장 상단(첫 번째)의 것을 찾음
    const activeItems = Array.from(document.querySelectorAll('[class*="remote_control_feed_item"][class*="remote_control_feed_active"]'));
    let targetItem = activeItems.length > 0 ? activeItems[0] : null;

    if (targetItem && container) {
      const itemRect = targetItem.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      container.scrollTop += itemRect.top - containerRect.top - 20;
      console.log('현재 재생 중인 영상으로 스크롤했습니다.');
      const overlay = createLoadingOverlay("현재 재생 중인 영상으로 이동했습니다.", null, 2);
    } else {
      console.log('재생 중인 영상을 찾을 수 없거나 컨테이너가 없습니다.');
      const overlay = createLoadingOverlay("재생 중인 영상을 찾을 수 없습니다.\n잠시 후 다시 시도해보세요.", null, 2);
    }
  });

  searchButton = document.createElement('button');
  searchButton.textContent = '검색';
  searchButton.style.cssText = `
    margin-left: 10px;
    padding: 8px 12px;
    background-color: ${activeSearchMode === 'videoSearch' ? '#0044cc' : '#0066ff'};
    color: #fff;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    display: ${isVideoSupportTabActive() ? 'inline-block' : 'none'};
    position: relative;
  `;

  unplayedSearchButton = document.createElement('button');
  unplayedSearchButton.textContent = '미재생 영상';
  unplayedSearchButton.style.cssText = `
    margin-left: 10px;
    padding: 8px 12px;
    background-color: ${activeSearchMode === 'unplayedSearch' ? '#cc5200' : '#ff6600'};
    color: #fff;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    display: ${isVideoSupportTabActive() ? 'inline-block' : 'none'};
    position: relative;
  `;

  const searchResultDisplay = document.createElement('span');
  searchResultDisplay.id = 'search-result-display';
  searchResultDisplay.style.cssText = `
    margin-left: 5px;
    margin-right: 10px;
    font-size: 14px;
    color: #333;
    vertical-align: middle;
    display: none;
  `;

  function addVideoSearchBar() {
    if (activeSearchMode === 'videoSearch' && document.querySelector('.search-container')) {
      closeSearchBar();
      return;
    }

    closeSearchBar();
    activeSearchMode = 'videoSearch';
    updateButtonStyles();

    const newSearchContainer = document.createElement('div');
    newSearchContainer.className = 'search-container';
    newSearchContainer.style.cssText = `
      display: ${isVideoSupportTabActive() ? 'flex' : 'none'};
      align-items: center;
      margin-left: 10px;
      margin-top: 5px;
    `;
    searchContainer = newSearchContainer;

    const searchOptionSelect = document.createElement('select');
    searchOptionSelect.style.cssText = `
      padding: 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 14px;
      margin-right: 10px;
    `;
    const options = [
      { value: 'all', text: '통합 검색' },
      { value: 'nickname', text: '닉네임만 검색' },
      { value: 'title', text: '영상 제목만 검색' },
      { value: 'description', text: '영상 설명만 검색' }
    ];
    options.forEach(opt => {
      const option = document.createElement('option');
      option.value = opt.value;
      option.textContent = opt.text;
      searchOptionSelect.appendChild(option);
    });

    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = '검색어를 입력하세요';
    searchInput.style.cssText = `
      padding: 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 14px;
      margin-right: 10px;
      width: 200px;
    `;

    const searchActionButton = document.createElement('button');
    searchActionButton.textContent = '검색';
    searchActionButton.style.cssText = `
      padding: 8px 12px;
      background-color: #0066ff;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 5px;
    `;

    const prevButton = document.createElement('button');
    prevButton.textContent = '이전';
    prevButton.style.cssText = `
      padding: 8px 12px;
      background-color: #4e41db;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 5px;
      display: none;
    `;

    const nextButton = document.createElement('button');
    nextButton.textContent = '다음';
    nextButton.style.cssText = `
      padding: 8px 12px;
      background-color: #4e41db;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 5px;
      display: none;
    `;

    const closeButton = document.createElement('button');
    closeButton.textContent = 'X';
    closeButton.style.cssText = `
      padding: 8px 12px;
      background-color: #ff6666;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
    `;

    searchActionButton.addEventListener('click', () => {
      const query = searchInput.value.trim().toLowerCase().replace(/\s+/g, '');
      const searchOption = searchOptionSelect.value;
      if (!query) {
        console.log('검색어를 입력해주세요.');
        const overlay = createLoadingOverlay('검색어를 입력해주세요.', null, 1);
        return;
      }

      const localSearchResults = [];
      let localSearchIndex = -1;

      const items = Array.from(document.querySelectorAll('[class*="remote_control_feed_item"]'));
      items.forEach((item, index) => {
        const nameTextElement = item.querySelector('[class*="name_text"]');
        const titleElement = item.querySelector('[class*="remote_control_feed_video_information"]').querySelector('[class*="remote_control_feed_text"]');
        const descriptionElement = item.querySelector('[class*="remote_control_feed_text"]');
        const nameText = nameTextElement ? nameTextElement.textContent.trim().toLowerCase() : '';
        const titleText = titleElement ? titleElement.textContent.trim().toLowerCase() : '';
        let descriptionText = descriptionElement ? descriptionElement.textContent.trim().toLowerCase() : '';
        if (descriptionText === titleText) {
          descriptionText = "";
        }
        const blindElement = item.querySelector('.blind');
        const donationType = blindElement ? blindElement.textContent.trim() : '';

        let matchesQuery = false;
        if (searchOption === 'all') {
          matchesQuery = nameText.replace(/\s+/g, '').includes(query) ||
            titleText.replace(/\s+/g, '').includes(query) ||
            descriptionText.replace(/\s+/g, '').includes(query);
        } else if (searchOption === 'nickname') {
          matchesQuery = nameText.replace(/\s+/g, '').includes(query);
        } else if (searchOption === 'title') {
          matchesQuery = titleText.replace(/\s+/g, '').includes(query);
        } else if (searchOption === 'description') {
          matchesQuery = descriptionText.replace(/\s+/g, '').includes(query);
        }

        if (donationType === '영상 후원' && matchesQuery) {
          localSearchResults.push({ item, index });
        }
      });

      if (localSearchResults.length === 0) {
        console.log('검색 결과가 없습니다.');
        const overlay = createLoadingOverlay('검색 결과가 없습니다.', null, 1);
        prevButton.style.display = 'none';
        nextButton.style.display = 'none';
        searchResultDisplay.textContent = '';
        searchResultDisplay.style.display = 'none';
        return;
      }

      localSearchIndex = 0;
      scrollToSearchResult(localSearchResults, localSearchIndex, true);
      prevButton.style.display = localSearchResults.length > 1 ? 'inline-block' : 'none';
      nextButton.style.display = localSearchResults.length > 1 ? 'inline-block' : 'none';
      searchResultDisplay.style.display = 'inline-block';
      searchResultDisplay.textContent = `${localSearchIndex + 1}/${localSearchResults.length}`;

      prevButton.onclick = () => {
        if (localSearchIndex > 0) {
          localSearchIndex--;
        } else {
          localSearchIndex = localSearchResults.length - 1;
        }
        scrollToSearchResult(localSearchResults, localSearchIndex, true);
        searchResultDisplay.textContent = `${localSearchIndex + 1}/${localSearchResults.length}`;
      };

      nextButton.onclick = () => {
        if (localSearchIndex < localSearchResults.length - 1) {
          localSearchIndex++;
        } else {
          localSearchIndex = 0;
        }
        scrollToSearchResult(localSearchResults, localSearchIndex, true);
        searchResultDisplay.textContent = `${localSearchIndex + 1}/${localSearchResults.length}`;
      };
    });

    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        searchActionButton.click();
      }
    });

    closeButton.addEventListener('click', () => closeSearchBar());

    newSearchContainer.appendChild(searchOptionSelect);
    newSearchContainer.appendChild(searchInput);
    newSearchContainer.appendChild(searchActionButton);
    searchActionButton.parentNode.insertBefore(searchResultDisplay, searchActionButton.nextSibling);
    newSearchContainer.appendChild(prevButton);
    newSearchContainer.appendChild(nextButton);
    newSearchContainer.appendChild(closeButton);

    appendSearchContainer(newSearchContainer);
  }

  function addUnplayedSearchBar() {
    if (activeSearchMode === 'unplayedSearch' && document.querySelector('.search-container')) {
      closeSearchBar();
      return;
    }

    closeSearchBar();
    activeSearchMode = 'unplayedSearch';
    updateButtonStyles();

    const newSearchContainer = document.createElement('div');
    newSearchContainer.className = 'search-container';
    newSearchContainer.style.cssText = `
      display: ${isVideoSupportTabActive() ? 'flex' : 'none'};
      align-items: center;
      margin-left: 10px;
      margin-top: 5px;
    `;
    searchContainer = newSearchContainer;

    const searchOptionSelect = document.createElement('select');
    searchOptionSelect.style.cssText = `
      padding: 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 14px;
      margin-right: 10px;
      display: none;
    `;
    const options = [
      { value: 'all', text: '모두 보기' }
    ];
    options.forEach(opt => {
      const option = document.createElement('option');
      option.value = opt.value;
      option.textContent = opt.text;
      searchOptionSelect.appendChild(option);
    });

    const searchActionButton = document.createElement('button');
    searchActionButton.textContent = '검색';
    searchActionButton.style.cssText = `
      padding: 8px 12px;
      background-color: #ff6600;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 5px;
    `;

    const prevButton = document.createElement('button');
    prevButton.textContent = '이전';
    prevButton.style.cssText = `
      padding: 8px 12px;
      background-color: #4e41db;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 5px;
      display: none;
    `;

    const nextButton = document.createElement('button');
    nextButton.textContent = '다음';
    nextButton.style.cssText = `
      padding: 8px 12px;
      background-color: #4e41db;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 5px;
      display: none;
    `;

    const closeButton = document.createElement('button');
    closeButton.textContent = 'X';
    closeButton.style.cssText = `
      padding: 8px 12px;
      background-color: #ff6666;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
    `;

    function performUnplayedSearch() {
      const searchOption = searchOptionSelect.value;
      let localSearchResults = [];
      let localSearchIndex = -1;

      const items = Array.from(document.querySelectorAll('[class*="remote_control_feed_item"]'));
      items.forEach((item, index) => {
        const blindElement = item.querySelector('.blind');
        const donationType = blindElement ? blindElement.textContent.trim() : '';
        const details = getVideoDetails(item, index);

        const isPlayed = playedVideos.some(video =>
          video.title === details.title &&
          video.nickname === details.nickname &&
          video.index === index
        );

        if (donationType === '영상 후원' && !isPlayed) {
          localSearchResults.push({ item, index, details });
        }
      });

      if (searchOption !== 'all') {
        localSearchResults.sort((a, b) => {
          const field = searchOption;
          const aValue = a.details[field] || '';
          const bValue = b.details[field] || '';
          return aValue.localeCompare(bValue);
        });
      }

      localSearchResults = localSearchResults.map(({ item, index }) => ({ item, index }));

      if (localSearchResults.length === 0) {
        console.log('재생 미완료 영상이 없습니다.');
        const overlay = createLoadingOverlay('재생 미완료 영상이 없습니다.', null, 1);
        prevButton.style.display = 'none';
        nextButton.style.display = 'none';
        searchResultDisplay.textContent = '';
        searchResultDisplay.style.display = 'none';
        return;
      }

      localSearchIndex = 0;
      scrollToSearchResult(localSearchResults, localSearchIndex, true);
      prevButton.style.display = localSearchResults.length > 1 ? 'inline-block' : 'none';
      nextButton.style.display = localSearchResults.length > 1 ? 'inline-block' : 'none';
      searchResultDisplay.style.display = 'inline-block';
      searchResultDisplay.textContent = `${localSearchIndex + 1}/${localSearchResults.length}`;

      prevButton.onclick = () => {
        if (localSearchIndex > 0) {
          localSearchIndex--;
        } else {
          localSearchIndex = localSearchResults.length - 1;
        }
        scrollToSearchResult(localSearchResults, localSearchIndex, true);
        searchResultDisplay.textContent = `${localSearchIndex + 1}/${localSearchResults.length}`;
      };

      nextButton.onclick = () => {
        if (localSearchIndex < localSearchResults.length - 1) {
          localSearchIndex++;
        } else {
          localSearchIndex = 0;
        }
        scrollToSearchResult(localSearchResults, localSearchIndex, true);
        searchResultDisplay.textContent = `${localSearchIndex + 1}/${localSearchResults.length}`;
      };
    }

    searchActionButton.addEventListener('click', performUnplayedSearch);
    searchOptionSelect.addEventListener('change', performUnplayedSearch);
    closeButton.addEventListener('click', () => closeSearchBar());

    newSearchContainer.appendChild(searchOptionSelect);
    newSearchContainer.appendChild(searchActionButton);
    searchActionButton.parentNode.insertBefore(searchResultDisplay, searchActionButton.nextSibling);
    newSearchContainer.appendChild(prevButton);
    newSearchContainer.appendChild(nextButton);
    newSearchContainer.appendChild(closeButton);

    appendSearchContainer(newSearchContainer);
    performUnplayedSearch();
  }

  function closeSearchBar() {
    const existingSearchContainer = document.querySelector('.search-container');
    if (existingSearchContainer) {
      existingSearchContainer.remove();
    }
    const searchArea = document.querySelector('.custom-search-area');
    if (searchArea && !searchArea.querySelector('.search-container')) {
      searchArea.remove();
      updateContentHeight(false);
    }
    searchResultDisplay.style.display = 'none';
    searchResultDisplay.textContent = '';
    activeSearchMode = null;
    updateButtonStyles();
  }

  function updateButtonStyles() {
    searchButton.style.backgroundColor = activeSearchMode === 'videoSearch' ? '#0044cc' : '#0066ff';
    unplayedSearchButton.style.backgroundColor = activeSearchMode === 'unplayedSearch' ? '#cc5200' : '#ff6600';
  }

  function appendSearchContainer(container) {
    let searchArea = document.querySelector('.custom-search-area');
    if (!searchArea) {
      searchArea = document.createElement('div');
      searchArea.className = 'custom-search-area';
      searchArea.style.cssText = `
        width: 100%;
        height: 5%;
        background: #f9f9f9;
        display: ${isVideoSupportTabActive() ? 'flex' : 'none'};
        align-items: center;
        padding: 20px 5px 25px 5px;
        box-sizing: border-box;
        border-bottom: 1px solid #ddd;
      `;
      const main = document.querySelector('[class*="remote_control_main"]');
      const content = document.querySelector('[class*="remote_control_content"]');
      if (main && content && content.parentNode === main) {
        main.insertBefore(searchArea, content);
      }
    }
    searchArea.appendChild(container);
    updateContentHeight(true);
  }

  searchButton.addEventListener('click', addVideoSearchBar);
  unplayedSearchButton.addEventListener('click', addUnplayedSearchBar);

  const tablist = document.querySelector('[class*="remote_control_box"]');
  if (tablist) {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.alignItems = 'center';
    container.style.marginLeft = '10px';

    container.appendChild(sidebarToggle);
    container.appendChild(sidebarLabel);
    container.appendChild(scrollToPlayingButton);
    container.appendChild(searchButton);
    container.appendChild(unplayedSearchButton);
    insertAfter(container, tablist);
  }

  function updateSearchBarsVisibility() {
    const isActive = isVideoSupportTabActive();
    document.querySelectorAll('.search-container').forEach(container => {
      container.style.display = isActive ? 'flex' : 'none';
    });
    const searchArea = document.querySelector('.custom-search-area');
    if (searchArea) {
      searchArea.style.display = isActive ? 'flex' : 'none';
      updateContentHeight(searchArea.style.display !== 'none');
    }
  }

  function updateContentHeight(isSearchVisible) {
    const content = document.querySelector('[class*="remote_control_content"]');
    if (content) {
      content.style.height = isSearchVisible ? '92.8%' : '100%';
    }
  }

  document.querySelectorAll('[class*="remote_control_header"]').forEach(function (element) {
    element.style.right = sidebarToggle.checked ? '220px' : '0px'; // [MODIFIED] Respect state
    element.style.justifyContent = '';
  });
  document.querySelectorAll('[class*="remote_control_aside_container"]').forEach(function (element) {
    element.style.display = sidebarToggle.checked ? 'flex' : 'none'; // [MODIFIED] Respect state
  });

  const tablistElement = document.querySelector('[class*="remote_control_list"]');
  if (tablistElement) {
    tablistElement.style.alignItems = 'self-end';
    tablistElement.style.marginRight = 'auto';
    tablistElement.style.marginLeft = '20px';
  }

  sidebarToggle.addEventListener('change', function () {
    saveToLocalStorage('sidebarToggle', sidebarToggle.checked); // Save state
    if (sidebarToggle.checked) {
      document.querySelectorAll('[class*="remote_control_header"]').forEach(function (element) {
        element.style.right = '220px';
      });
      document.querySelectorAll('[class*="remote_control_aside_container"]').forEach(function (element) {
        element.style.display = 'flex';
      });
    } else {
      document.querySelectorAll('[class*="remote_control_header"]').forEach(function (element) {
        element.style.right = '0px';
      });
      document.querySelectorAll('[class*="remote_control_aside_container"]').forEach(function (element) {
        element.style.display = 'none';
      });
    }
  });
}

function loadFromLocalStorage(key, defaultValue) {
  try {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : defaultValue;
  } catch (e) {
    console.error(`Error loading ${key} from localStorage:`, e);
    return defaultValue;
  }
}

function saveToLocalStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.error(`Error saving ${key} to localStorage:`, e);
  }
}

let playedVideos = loadFromLocalStorage('playedVideos', []);
let previousVideos = loadFromLocalStorage('previousVideos', []);
let aa = 0;

function getVideoDetails(item, index) {
  const titleElement = item.querySelector('[class*="remote_control_feed_video_information"] [class*="remote_control_feed_text"]');
  const nicknameElement = item.querySelector('[class*="name_text"]');
  return {
    title: titleElement ? titleElement.textContent.trim() : '',
    nickname: nicknameElement ? nicknameElement.textContent.trim().replace('✅', '').replace('🟥2️⃣', '') : '',
    index: index
  };
}

function savePlayedVideo(item, index) {
  const details = getVideoDetails(item, index);
  if (!playedVideos.some(video =>
    video.title === details.title &&
    video.nickname === details.nickname &&
    video.index === index
  )) {
    playedVideos.push({ ...details, completed: true });
    saveToLocalStorage('playedVideos', playedVideos);
    console.log(`Saved played video: ${JSON.stringify(details)}`);
  }
}

function togglePlayedStatus(item, index) {
  const details = getVideoDetails(item, index);
  const nameTextElement = item.querySelector('[class*="name_text"]');
  const thumbnailElement = item.querySelector('[class*="remote_control_feed_thumbnail"]');
  const currentText = nameTextElement.textContent.trim();
  const isPlayed = playedVideos.some(video =>
    video.title === details.title &&
    video.nickname === details.nickname &&
    video.index === index
  );

  if (isPlayed) {
    playedVideos = playedVideos.filter(video =>
      !(video.title === details.title &&
        video.nickname === details.nickname &&
        video.index === index)
    );
    nameTextElement.textContent = currentText.replace('✅', '');
    if (thumbnailElement) {
      thumbnailElement.style.border = '5px solid darkgrey';
    }
    console.log(`Unmarked played video: ${JSON.stringify(details)}`);
  } else {
    playedVideos.push({ ...details, completed: true });
    if (!currentText.includes('✅')) {
      nameTextElement.textContent = '✅' + currentText;
    }
    if (thumbnailElement) {
      thumbnailElement.style.border = '5px solid #73e373';
    }
    console.log(`Marked played video: ${JSON.stringify(details)}`);
  }

  saveToLocalStorage('playedVideos', playedVideos);
}

function updatePreviousVideos() {
  const items = Array.from(document.querySelectorAll('[class*="remote_control_feed_item"]'));
  if (toggleButton) {
    const skipCount = 0;
    previousVideos = items.slice(skipCount).map((item, i) => {
      const index = i;
      const details = getVideoDetails(item, index);
      return details;
    });
    saveToLocalStorage('previousVideos', previousVideos);
    console.log(`Updated previousVideos with ${previousVideos.length} items`);
  }
}

function reapplyPlaybackIndicators() {
  if (!toggleButton) { return; }
  const items = Array.from(document.querySelectorAll('[class*="remote_control_feed_item"]'));
  const currentVideos = items.map((item, index) => ({ item, ...getVideoDetails(item, index) }));

  console.log("Calculating offset...");
  //console.log(`currentVideos.length: ${currentVideos.length}, previousVideos.length: ${previousVideos.length}`);

  // Log currentVideos and previousVideos without circular references
  const currentVideosLog = currentVideos.map(v => ({
    title: v.title,
    nickname: v.nickname,
    index: v.index
  }));
  const previousVideosLog = previousVideos.map(v => ({
    title: v.title,
    nickname: v.nickname,
    index: v.index
  }));
  //console.log("Current videos (safe):", JSON.stringify(currentVideosLog, null, 2));
  //console.log("Previous videos:", JSON.stringify(previousVideosLog, null, 2));
  //console.log("Played videos:", JSON.stringify(playedVideos, null, 2));

  let offset = 0;
  const checkLimit = Math.min(5, currentVideos.length, previousVideos.length);
  //console.log(`checkLimit: ${checkLimit}`);

  if (checkLimit > 0) {
    const currentDetails = currentVideos.slice(0, checkLimit).map(v => ({
      title: v.title,
      nickname: v.nickname,
    }));
    const prevDetails = previousVideos.slice(0, checkLimit).map(v => ({
      title: v.title,
      nickname: v.nickname,
    }));

    // console.log("Current details:", JSON.stringify(currentDetails, null, 2));
    // console.log("Previous details:", JSON.stringify(prevDetails, null, 2));

    // Manual check at offset 1
    if (checkLimit > 1) {
      //console.log("Manual check at offset 1:");
      for (let j = 0; j < checkLimit - 1; j++) {
        const current = currentDetails[j + 1] || {};
        const prev = prevDetails[j] || {};
        //console.log(`current[${j + 1}]: ${JSON.stringify(current)}, prev[${j}]: ${JSON.stringify(prev)}`);
        if (
          current.title === prev.title &&
          current.nickname === prev.nickname
        ) {
          //console.log(`Match at j=${j}`);
        } else {
          //console.log(`Mismatch at j=${j}: title=${current.title === prev.title}, nickname=${current.nickname === prev.nickname}`);
        }
      }
    }

    let matchFound = false;
    for (let i = 0; i <= checkLimit; i++) {
      try {
        //console.log(`Checking offset: ${i}`);
        let matches = true;
        for (let j = 0; j < checkLimit - i; j++) {
          try {
            const current = currentDetails[j + i] || {};
            const prev = prevDetails[j] || {};
            //console.log(`Comparing current[${j + i}]: ${JSON.stringify(current)} with prev[${j}]: ${JSON.stringify(prev)}`);
            if (
              current.title !== prev.title ||
              current.nickname !== prev.nickname
            ) {
              matches = false;
              //console.log(`Mismatch at j=${j}: title=${current.title === prev.title}, nickname=${current.nickname === prev.nickname}`);
              break;
            }
          } catch (e) {
            //console.error(`Inner loop error at offset ${i}, j=${j}:`, e);
            matches = false;
            break;
          }
        }
        if (matches) {
          offset = i;
          matchFound = true;
          //console.log(`Match found at offset: ${i}`);
          break;
        }
      } catch (e) {
        //console.error(`Outer loop error at offset ${i}:`, e);
        continue;
      }
    }

    if (!matchFound) {
      //console.warn("No matching offset found, defaulting to offset = 0");
      offset = 0; // Fallback to 0 if no match is found
    }
  } else {
    //console.warn("checkLimit is 0, skipping offset calculation");
  }

  console.log(`Offset calculated: ${offset}`);

  const matchedVideoIndices = new Set();

  items.forEach((item, index) => {
    const details = getVideoDetails(item, index);
    const nameTextElement = item.querySelector('[class*="name_text"]');
    const thumbnailElement = item.querySelector('[class*="remote_control_feed_thumbnail"]');
    const blindElement = item.querySelector('.blind');
    const donationType = blindElement ? blindElement.textContent.trim() : '';

    if (donationType === '영상 후원' && !details.nickname.includes('2️⃣')) {
      const matchedVideoIndex = playedVideos.findIndex(video => {
        const match = video.title === details.title &&
          video.nickname === details.nickname &&
          (video.index + offset === index);
        return match;
      });

      if (matchedVideoIndex !== -1) {
        if (!nameTextElement.textContent.includes('✅')) {
          nameTextElement.textContent = '✅' + nameTextElement.textContent.trim();
        }
        if (thumbnailElement) {
          thumbnailElement.style.border = '5px solid #73e373';
        }
        console.log(`Reapplied ✅ to ${details.nickname} at index ${index}`);
        matchedVideoIndices.add(matchedVideoIndex);
      }
    }
  });

  playedVideos = playedVideos
    .map((video, idx) => matchedVideoIndices.has(idx) ? { ...video, index: video.index + offset } : null)
    .filter(video => video !== null);
  saveToLocalStorage('playedVideos', playedVideos);

  updatePreviousVideos();
}

function addTier2Indicator() {
  const items = document.querySelectorAll('[class*="remote_control_feed_item"]');
  items.forEach((item) => {
    const nameTextElement = item.querySelector('[class*="name_text"]');
    const secondaryElement = item.querySelector('[class*="remote_control_feed_secondary"]');
    const blindElement = item.querySelector('.blind');

    if (nameTextElement && secondaryElement && blindElement) {
      const textContent = nameTextElement.textContent.trim();
      const isAnonymous = secondaryElement.textContent.trim();
      const donationType = blindElement ? blindElement.textContent.trim() : '';

      if (!textContent.includes('2️⃣') && predefinedArray.includes(textContent) && isAnonymous !== "(익명)" && donationType === "영상 후원") {
        nameTextElement.textContent = '🟥2️⃣' + textContent;
        console.log("Adding!!");
      }
    }
  });
}

function initializeCombinedFeatures() {
  const items = document.querySelectorAll('[class*="remote_control_feed_item"]');
  items.forEach((item) => {
    const nameTextElement = item.querySelector('[class*="name_text"]');
    const blindElement = item.querySelector('.blind');

    const thumbnailElement = item.querySelector('[class*="remote_control_feed_thumbnail"]');
    if (thumbnailElement) {
      thumbnailElement.style.cursor = 'pointer'; // Make thumbnail appear clickable
      thumbnailElement.addEventListener('click', () => {
        const style = thumbnailElement.getAttribute('style');
        const urlMatch = style.match(/url\(["']?([^"')]+)["']?\)/);
        if (urlMatch) {
          const url = urlMatch[1];
          // Check if it's a YouTube thumbnail URL
          const youtubeMatch = url.match(/https:\/\/i\.ytimg\.com\/vi\/([A-Za-z0-9_-]+)/);
          if (youtubeMatch) {
            const videoId = youtubeMatch[1];
            const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`;
            console.log(`Link Open: ${youtubeUrl}`);
          }
          // No action for Chzzk or other URLs
        }
      });
    }

    if (nameTextElement && blindElement) {
      const textContent = nameTextElement.textContent.trim();
      const donationType = blindElement.textContent.trim();

      addTier2Indicator();
      if (donationType === "영상 후원" && !textContent.includes('2️⃣')) {
        addPlayAllButton(item);
      }
      addBanButton(item);
      removeHrefFromLinks(item);
      monitorPlayButton(item);
    }
  });

  console.log('813');
  reapplyPlaybackIndicators();
}

function togglePlayAllButtons(disable) {
  const playAllButtons = document.querySelectorAll('.custom-play-all-button');
  playAllButtons.forEach(button => {
    button.disabled = disable;
    button.style.backgroundColor = disable ? '#cccccc' : '#4e41db';
    button.style.cursor = disable ? 'not-allowed' : 'pointer';
  });
}

function addBanButton(element) {
  const targetDiv = element.querySelector('[class*="remote_control_feed_inner"]');
  const nameTextSpan = element.querySelector('[class*="name_text"]');

  if (targetDiv && nameTextSpan && element.querySelector('[class*="remote_control_feed_link"]').getElementsByClassName("ban-button").length == 0 && element.querySelector('[class*="remote_control_feed_link"]').getElementsByClassName('search-button').length == 0) {
    const banButton = document.createElement('button');
    banButton.textContent = '밴';
    banButton.className = 'ban-button';
    banButton.type = "button";
    banButton.style.cssText = `
      padding: 8px 12px;
      background-color: #ff6666;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 10px;
    `;

    banButton.addEventListener('click', () => {
      const nameText = nameTextSpan.textContent;
      if (nameText) {
        console.log(`SEARCH_REQUEST:ban_${nameText}`);
      }
    });

    targetDiv.parentNode.insertBefore(banButton, targetDiv.nextSibling);

    const banButton2 = document.createElement('button');
    banButton2.textContent = '부검';
    banButton2.className = 'search-button';
    banButton2.type = "button";
    banButton2.style.cssText = `
      padding: 8px 12px;
      background-color: #0066ff;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 10px;
    `;

    banButton2.addEventListener('click', () => {
      const nameText = nameTextSpan.textContent;
      if (nameText) {
        console.log(`SEARCH_REQUEST:search_${nameText}`);
      }
    });

    targetDiv.parentNode.insertBefore(banButton2, targetDiv.nextSibling);
  }
}

function addPlayAllButton(element) {
  const button = element.querySelector('button[class*="remote_control_feed_button"]');
  const items = Array.from(document.querySelectorAll('[class*="remote_control_feed_item"]'));
  const index = items.indexOf(element);

  if (button && !element.querySelector('.custom-play-all-button')) {
    const playAllButton = document.createElement('button');
    playAllButton.textContent = '이 영상부터 끝까지 재생';
    playAllButton.className = 'custom-play-all-button';
    playAllButton.style.cssText = `
      margin-left: 10px;
      padding: 8px 12px;
      background-color: #4e41db;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 10px;
    `;

    let isClicked = false;

    playAllButton.addEventListener('click', () => {
      if (isClicked) return;
      isClicked = true;

      // Check for unplayed Tier 2 videos
      let hasUnplayedTier2 = false;
      for (let i = index - 1; i >= 0; i--) {
        const item = items[i];
        const targetNameText = item.querySelector('[class*="name_text"]');
        const targetTextContent = targetNameText ? targetNameText.textContent.trim() : '';
        const targetBlindElement = item.querySelector('.blind');
        const targetDonationType = targetBlindElement ? targetBlindElement.textContent.trim() : '';
        if (targetDonationType === "영상 후원" && targetTextContent.includes('🟥') && !targetTextContent.includes('✅')) {
          hasUnplayedTier2 = true;
          break;
        }
      }

      // if (hasUnplayedTier2) {
      //   const proceed = confirm('재생되지 않은 2티어 영상이 있는 것 같습니다.\n계속하시겠습니까?');
      //   if (proceed) {
      //     console.log('PLAY ALL CLICKED');
      //     proceedWithPlayAll();
      //   } else {
      //     isClicked = false;
      //     togglePlayAllButtons(false);
      //     console.log('재생 프로세스가 취소되었습니다.');
      //   }
      // } else {
      //   console.log('PLAY ALL CLICKED');
      //   proceedWithPlayAll();
      // }

      console.log('PLAY ALL CLICKED');
      proceedWithPlayAll();

      function proceedWithPlayAll() {
        togglePlayAllButtons(true);
        timeoutIds = [];

        const overlay = createLoadingOverlay('영도 오버레이 새로고침 완료. 2초 뒤 재생 시작..\n⚠️재생 완료까지 이 창을 떠나지 마세요!', () => {
          timeoutIds.forEach(clearTimeout);
          timeoutIds = [];
          removeLoadingOverlay(overlay);
          isClicked = false;
          togglePlayAllButtons(false);
          console.log('재생 프로세스가 취소되었습니다.');
        }, null);

        timeoutIds.push(setTimeout(() => {
          updateLoadingOverlay('영도 오버레이 새로고침 완료. 1초 뒤 재생 시작..\n⚠️재생 완료까지 이 창을 떠나지 마세요!');
        }, 1000));
        timeoutIds.push(setTimeout(() => {
          const container = document.querySelector('[class*="remote_control_content"]');
          const items = Array.from(container.querySelectorAll('[class*="remote_control_feed_item"]'));
          const index = items.indexOf(element);
          const totalVideos = items.slice(0, index + 1).filter(item => {
            const targetBlindElement = item.querySelector('.blind');
            const targetNameText = item.querySelector('[class*="name_text"]');
            const targetDonationType = targetBlindElement ? targetBlindElement.textContent.trim() : '';
            const targetTextContent = targetNameText ? targetNameText.textContent.trim() : '';
            return targetDonationType === "영상 후원" && !targetTextContent.includes('2️⃣');
          }).length;

          let currentVideoIndex = 0;
          updateLoadingOverlay(`순서대로 재생 클릭 중..(${currentVideoIndex + 1}/${index + 1})\n⚠️재생 완료까지 이 창을 떠나지 마세요!`);

          for (let i = index; i >= 0; i--) {
            const targetItem = items[i];
            const targetButton = targetItem.querySelector('button[class*="remote_control_feed_button"]');
            const targetBlindElement = targetItem.querySelector('.blind');
            const targetNameText = targetItem.querySelector('[class*="name_text"]');
            const targetMarkButton = targetItem.querySelector('.custom-mark-played-button');
            const targetDonationType = targetBlindElement ? targetBlindElement.textContent.trim() : '';
            const targetTextContent = targetNameText ? targetNameText.textContent.trim() : '';

            if (targetButton && targetDonationType === "영상 후원") {
              const timeoutId = setTimeout(() => {
                currentVideoIndex++;
                if (targetTextContent.includes('2️⃣')) {
                  updateLoadingOverlay(`순서대로 재생 클릭 중..(${currentVideoIndex}/${index + 1})\n⚠️재생 완료까지 이 창을 떠나지 마세요!`);
                  if (currentVideoIndex === index + 1) {
                    const finalTimeoutId = setTimeout(() => {
                      removeLoadingOverlay(overlay);
                      isClicked = false;
                      togglePlayAllButtons(false);
                    }, 1000);
                    timeoutIds.push(finalTimeoutId);
                  }
                } else {
                  updateLoadingOverlay(`순서대로 재생 클릭 중..(${currentVideoIndex}/${index + 1})\n⚠️재생 완료까지 이 창을 떠나지 마세요!`);
                  targetButton.click();
                  let targetButtonText = targetButton && targetButton.querySelector('.blind') ? targetButton.querySelector('.blind').innerText : '';
                  if (targetButtonText.includes('재생 정지')) {
                    const stopTimeoutId = setTimeout(() => {
                      targetMarkButton.click();
                      targetButton.click();
                    }, 500);
                    timeoutIds.push(stopTimeoutId);
                  }
                  if (currentVideoIndex === index + 1) {
                    const finalTimeoutId = setTimeout(() => {
                      removeLoadingOverlay(overlay);
                      isClicked = false;
                      togglePlayAllButtons(false);
                    }, 1000);
                    timeoutIds.push(finalTimeoutId);
                  }
                }
              }, (index - i) * 1000);
              timeoutIds.push(timeoutId);
            }
          }
        }, 2000));
      }
    });

    const markPlayedButton = document.createElement('button');
    markPlayedButton.textContent = '재생 완료 표시';
    markPlayedButton.className = 'custom-mark-played-button';
    markPlayedButton.style.cssText = `
      margin-left: 10px;
      padding: 8px 12px;
      background-color: #28a745;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      margin-right: 10px;
    `;

    markPlayedButton.addEventListener('click', () => {
      togglePlayedStatus(element, index);
    });

    button.parentNode.appendChild(playAllButton);
    button.parentNode.appendChild(markPlayedButton);
  }
}

function removeHrefFromLinks(element) {
  const links = element.querySelectorAll('[class*="remote_control_feed_link"]');
  links.forEach((link) => {
    if (link.tagName === 'A') {
      link.removeAttribute('href');
      link.style.textDecoration = 'none';
    }
  });

  const texts = element.querySelectorAll('[class*="remote_control_feed_inner"] strong, [class*="remote_control_feed_inner"] span');
  texts.forEach((text) => {
    text.style.textDecoration = 'none';
  });
}

function monitorPlayButton(element) {
  const targetButton = element.querySelector('button[class*="remote_control_feed_button"]');
  const nameTextElement = element.querySelector('[class*="name_text"]');
  const thumbnailElement = element.querySelector('[class*="remote_control_feed_thumbnail"]');
  const items = Array.from(document.querySelectorAll('[class*="remote_control_feed_item"]'));
  const index = items.indexOf(element);

  if (thumbnailElement) {
    thumbnailElement.style.border = '5px solid darkgrey';
  }

  if (!targetButton || !nameTextElement) return;

  let wasPlaying = false;
  let wasPlaying2 = false;

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      const buttonText = targetButton.querySelector('.blind')?.innerText;
      if (buttonText) {
        console.log(buttonText, wasPlaying);
        if (buttonText.includes('재생 정지')) { // 재생 중인 상태
          if (wasPlaying) {
            console.log("재생 중임...")
            wasPlaying = true;
          }
          else {
            console.log("재생 시작..")
            wasPlaying = true;
          }
        } else if (wasPlaying && !buttonText.includes('재생 정지')) { // 재생 방금 막 완료된 상태 (재생 중이었고, 재생 완료 상태가 됨)
          console.log("재생 완료!")
          wasPlaying = false;
          const textContent = nameTextElement.textContent.trim();
          Is2Tier = "False";
          if (textContent.includes("2️⃣")) {
            Is2Tier = "True";
          }
          console.log(`재생 완료:: Is2Tier=${Is2Tier}`);
          if (!textContent.includes('✅')) {
            nameTextElement.textContent = '✅' + textContent;
            console.log(`Added ✅ to ${textContent}`);
            if (thumbnailElement) {
              thumbnailElement.style.border = '5px solid #73e373';
            }
            savePlayedVideo(element, index);
            // Check if this is the topmost non-Tier 2 video
            console.log("재생 완료된 영상이 마지막 영도인지 확인");
            console.log(items.length);
            console.log(index);
            for (let i = 0; i < items.length; i++) {
              const item = items[i];
              const targetNameText = item.querySelector('[class*="name_text"]');
              const targetTextContent = targetNameText ? targetNameText.textContent.trim() : '';
              const targetBlindElement = item.querySelector('.blind');
              const targetDonationType = targetBlindElement ? targetBlindElement.textContent.trim() : '';
              if (targetDonationType === "영상 후원" && !targetTextContent.includes('2️⃣')) {
                firstNonTier2Index = i;
                break;
              }
            }
            console.log("firstNonTier2Index:");
            console.log(firstNonTier2Index);
            if (index === firstNonTier2Index) {
              const targetBlindElement = element.querySelector('.blind');
              const targetDonationType = targetBlindElement ? targetBlindElement.textContent.trim() : '';
              if (targetDonationType === "영상 후원" && !textContent.includes('2️⃣')) {
                console.log('ydEnd');
              }
            }
          }
          //observer.disconnect();
        }
      }
    });
  });

  observer.observe(targetButton, { childList: true, subtree: true });



  const observer2 = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
        const className = mutation.target.className;
        if (typeof className === 'string' && className.includes('remote_control_feed_item') && className.includes('remote_control_feed_active')) { // 재생 중인 상태
          if (wasPlaying2) {
            console.log("진짜 재생 중임...");
          } else {
            console.log("진짜 재생 시작..");
            wasPlaying2 = true;
            console.log(thumbnailElement);
            if (thumbnailElement) {
              console.log("thumbnailElement found");
              const style = thumbnailElement.getAttribute('style');
              const urlMatch = style.match(/url\(["']?([^"')]+)["']?\)/);
              console.log("urlMatch: ", urlMatch);
              if (urlMatch) {
                console.log("url found");
                const url = urlMatch[1];
                const youtubeMatch = url.match(/https:\/\/i\.ytimg\.com\/vi\/([A-Za-z0-9_-]+)/);
                console.log("youtubeMatch: ", youtubeMatch);
                if (youtubeMatch) {
                  console.log("youtubeMatch found");
                  const videoId = youtubeMatch[1];
                  console.log(`재생 시작:: VideoId=${videoId}`);
                }
                else { // 치지직 클립
                  console.log("chzzk clip");
                  console.log(`재생 시작:: ChzzkVideoThumbnail=${url}`);
                }
              }
            }
          }
        } else {
          console.log("재생 안하는 중..");
          wasPlaying2 = false;
        }
      }
    });
  });

  observer2.observe(element, { attributes: true, attributeFilter: ['class'] });
}

function scrollToSearchResult(results, index, highlight = false) {
  if (index >= 0 && index < results.length) {
    const { item } = results[index];
    const container = document.querySelector('[class*="remote_control_content"]');
    if (item && container) {
      const itemRect = item.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      container.scrollTop += itemRect.top - containerRect.top - 20;
      if (highlight) {
        item.style.transition = '';
        item.style.backgroundColor = '#FFFF00';
        setTimeout(() => {
          item.style.transition = 'background-color 0.5s ease';
          item.style.backgroundColor = '';
        }, 200);
      }
      console.log(`${index + 1}/${results.length}`);
    }
  }
}

let observer;
let targetNode = document.body;
let config = { childList: true, subtree: true };

observer = new MutationObserver((mutations) => {
  let listRefreshed = false;

  mutations.forEach((mutation) => {
    if (mutation.target.matches && mutation.target.matches('[class*="remote_control_content"]') &&
      mutation.addedNodes.length > 0 &&
      mutation.removedNodes.length > 0) {
      listRefreshed = true;
    }

    mutation.addedNodes.forEach((node) => {
      if (node.nodeType === Node.ELEMENT_NODE && node.matches && node.matches('[class*="remote_control_feed_item"]')) {
        const nameTextElement = node.querySelector('[class*="name_text"]');
        const secondaryElement = node.querySelector('[class*="remote_control_feed_secondary"]');
        const blindElement = node.querySelector('.blind');

        const thumbnailElement = node.querySelector('[class*="remote_control_feed_thumbnail"]');
        if (thumbnailElement) {
          thumbnailElement.style.cursor = 'pointer';
          thumbnailElement.addEventListener('click', () => {
            const style = thumbnailElement.getAttribute('style');
            const urlMatch = style.match(/url\(["']?([^"')]+)["']?\)/);
            if (urlMatch) {
              const url = urlMatch[1];
              const youtubeMatch = url.match(/https:\/\/i\.ytimg\.com\/vi\/([A-Za-z0-9_-]+)/);
              if (youtubeMatch) {
                const videoId = youtubeMatch[1];
                const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`;
                console.log(`Link Open: ${youtubeUrl}`);
              }
            }
          });
        }

        if (nameTextElement && secondaryElement && blindElement) {
          const textContent = nameTextElement.textContent.trim();
          const isAnonymous = secondaryElement.textContent.trim();
          const donationType = blindElement.textContent.trim();

          if (!textContent.includes('2️⃣') && predefinedArray.includes(textContent) && isAnonymous !== "(익명)" && donationType === "영상 후원") {
            nameTextElement.textContent = '🟥2️⃣' + textContent;
          }

          if (donationType === "영상 후원" && !textContent.includes('2️⃣')) {
            addPlayAllButton(node);
          }

          addBanButton(node);
          removeHrefFromLinks(node);
          monitorPlayButton(node);
        }
      }
    });
  });

  if (listRefreshed) {
    console.log('List refreshed, reapplying playback indicators...');
    if (!scrolling) {
      reapplyPlaybackIndicators();
    }
  }
});

initializeCombinedFeatures();
observer.observe(targetNode, config);