(function() {
    const titles = document.querySelectorAll('[class^="live_setting_title"]');
    for (const title of titles) {
        if (title.textContent.trim() === '영상 후원') {
            const item = title.closest('[class^="live_setting_item"]');
            if (item) {
                const toggle = item.querySelector('input[type="checkbox"]');
                if (toggle.checked) { 
                        toggle.click();
                    }
            }
            break;
        }
    }
})();