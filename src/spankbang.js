setTimeout(function () {
    __init();
}, 2000)

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = function () {
        let videoUrl = "";

        const videoEle = document.getElementsByTagName('video')[0];
        if (videoEle) {
            if (!videoEle.src.startsWith("blob:")) {
                videoUrl = videoEle.src;
            }
        }

        if (videoUrl.length === 0) {

            const scriptTags = document.getElementsByTagName('script');
            const keyword = 'var stream_data =';

            for (const scriptTag of scriptTags) {
                if (scriptTag.textContent && scriptTag.textContent.includes(keyword)) {
                    const lines = scriptTag.textContent.split(';');
                    for (const line of lines) {
                        if (line.includes(keyword)) {
                            const value = line.substring(23);
                            const jsonData = eval("(" + value + ")");
                            videoUrl = jsonData.m3u8.toString();
                            break;
                        }
                    }
                    break;
                }
            }
        }

        console.log("videoUrl:", videoUrl);
        if (videoUrl.length > 0) {
            bridge.download(JSON.stringify({
                'url': appendQueryParam(videoUrl, 'media_title', sanitizeTitle(document.title)),
                'metadata': Base64.encode(JSON.stringify({
                    http_headers: {
                        'Referer': videoUrl,
                    }
                }))
            }));
        }
    }
    container.appendChild(itdlBtn);
}

function loadDlBtn() {
    var vpContainer = document.getElementById('player_wrapper_outer');
    if (vpContainer) {
        var oldBtn = vpContainer.querySelector('.itdl-btn');
        if (!oldBtn) {
            createDlBtn(vpContainer);
        }
    }
}

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