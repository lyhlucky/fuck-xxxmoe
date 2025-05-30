setTimeout(function () {
    __init();
}, 2000)

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = function () {
        var videoUrl = "";

        var videoEle = document.getElementsByTagName('video')[0];
        if (videoEle) {
            if (!videoEle.src.startsWith("blob:")) {
                videoUrl = videoEle.src;
            }
        }

        if (videoUrl.length === 0) {
            var videoPlayer = document.getElementsByClassName('video__player')[0];
            if (videoPlayer) {
                videoUrl = videoPlayer.getAttribute('data-el-hls-url');
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
    document.querySelectorAll('.video__player').forEach(function (item, index, list) {
        var oldBtn = item.querySelector('.itdl-btn');
        if (!oldBtn) {
            createDlBtn(item)
        }
    })
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