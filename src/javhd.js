setTimeout(function () {
    __init();
}, 2000)

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = function () {
        var player = document.getElementsByTagName('video')[0];
        if (player) {
            var videoUrl = player.src;
            videoUrl += videoUrl.indexOf("?") === -1 ? "?" : "&";
            console.log("video url:", videoUrl);

            bridge.download(JSON.stringify({
                'url': videoUrl + 'itdl_ext=mp4' + '&itdl_title=' + encodeURIComponent(sanitizeTitle(document.title)),
                'metadata': Base64.encode(JSON.stringify({
                    http_headers: {
                        'Referer': videoUrl,
                    }
                }))
            }));
            return true;
        }

        console.log('undefined')
        return false;

    }
    container.appendChild(itdlBtn);
}

function loadDlBtn() {
    document.querySelectorAll('.jplayer__player-container').forEach(function (item, index, list) {
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