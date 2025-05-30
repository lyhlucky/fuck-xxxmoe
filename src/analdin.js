setTimeout(function () {
    __init();
}, 2000)

function createStyle() {
    if (!document.getElementById('itubego_style')) {
        var css = `
            .itdl-btn {
                position: absolute;
                top: 1%;
                right: 1%;
                z-index: 99999;
                font-size: 25px;
                padding: 10px 20px;
                cursor: pointer;
                background: #00CF2E;
                color: white;
                border-radius: 5px;
                border: none;
                box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
            }
            .itdl-btn:hover{ background-color: #00A625 }
            .itdl-btn:focus{ outline: none; }

            .itdl-btn > img {
                width: 30px !important;
                height: 30px !important;
                vertical-align: text-bottom !important;
            }
        `;
        var style = document.createElement('style');
        style.id = 'itubego_style';

        if (style.styleSheet) {
            style.styleSheet.cssText = css;
        } else {
            style.appendChild(document.createTextNode(css));
        }
        document.getElementsByTagName('head')[0].appendChild(style);
    }
}

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = function () {
        var videoEle = document.getElementsByTagName('video')[0];
        if (videoEle) {
            var videoUrl = appendQueryParam(videoEle.src, 'itdl_ext', "mp4");
            videoUrl = appendQueryParam(videoUrl, 'itdl_title', sanitizeTitle(document.title));
            bridge.download(JSON.stringify({
                'url': videoUrl,
                'metadata': Base64.encode(JSON.stringify({
                    http_headers: {
                        'Referer': videoEle.src,
                    }
                }))
            }));
        }
    }
    container.appendChild(itdlBtn);
}

function loadDlBtn() {
    document.querySelectorAll('.fp-player').forEach(function (item, index, list) {
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
