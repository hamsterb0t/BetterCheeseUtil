function clickMissionTab() {
    const missionTab = document.querySelectorAll('button[class^="remote_control_tab"]')[2];
    missionTab.click();
    setTimeout(() => {
        clickMissionSuccessButton();
    }, 1000);
}

function clickMissionTabTest() {
    const missionTab = document.querySelectorAll('button[class^="remote_control_tab"]')[2];
    missionTab.click();
    setTimeout(() => {
        clickMissionFailButton();
    }, 1000);
}

function clickMissionSuccessButton() {
    const buttonArea = document.querySelector('[class^="remote_control_feed_button_area"]');
    if (buttonArea) {
        const successButton = buttonArea.querySelectorAll('[class^="button_inner"]')[0];
        if (successButton && successButton.textContent.includes('수락하기')) {
            successButton.click();
        }
    }
}

function clickMissionFailButton() {
    const buttonArea = document.querySelector('[class^="remote_control_feed_button_area"]');
    if (buttonArea) {
        const successButton = buttonArea.querySelectorAll('[class^="button_inner"]')[1];
        if (successButton && successButton.textContent.includes('거절하기')) {
            successButton.click();
        }
    }
}