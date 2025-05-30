function __init() {
    // 删除全局按钮
    const commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    createStyle();
    loadDlBtn();
}

window.addEventListener('scroll', loadDlBtn);

if (document.readyState === 'loading') {  // 此时加载尚未完成
    document.addEventListener('DOMContentLoaded', __init);
} else {  // 此时`DOMContentLoaded` 已经被触发
    __init();
}

function loadDlBtn() {
    const videoContainer = document.getElementById('html5video')
    var oldBtn = videoContainer.querySelector('.itdl-btn');
    if (!oldBtn) {
        createDlBtn(videoContainer)
    }
}

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = function () {
        const videoUrl = extractHLSUrl();
        console.log("videoUrl:", videoUrl);

        let friendlyTitle = sanitizeTitle(document.title);
        console.log("original title:", friendlyTitle);
        const maxTitleLength = 120;
        if (friendlyTitle.length > maxTitleLength) {
            friendlyTitle = friendlyTitle.substring(0, maxTitleLength);
            console.log("simplefy title:", friendlyTitle);
        }

        bridge.download(JSON.stringify({
            'url': appendQueryParam(videoUrl, 'media_title', friendlyTitle),
            'metadata': Base64.encode(JSON.stringify({
                http_headers: {
                    'Referer': videoUrl,
                }
            }))
        }));
    }
    container.appendChild(itdlBtn);
}

function extractHLSUrl() {
    const scriptTags = document.getElementsByTagName('script');
    const keyword = 'html5player.setVideoHLS';
    let url = '';

    for (const scriptTag of scriptTags) {
        if (scriptTag.textContent && scriptTag.textContent.includes(keyword)) {
            const regex = new RegExp(`${keyword}\\('(.*?)'\\)`, 'i');
            const match = scriptTag.textContent.match(regex);

            if (match && match[1]) {
                url = match[1];
                break;
            }
        }
    }

    return url;
}
