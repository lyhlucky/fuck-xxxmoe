setTimeout(__init, 1000)

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = function () {

        setTimeout(function () {

            var videoEle = container.querySelector('video');
            var source = videoEle.querySelector("source")
            var url = source ? source.getAttribute('src') : videoEle.getAttribute('src');
            console.log(url);

            bridge.download(JSON.stringify({
                'url': url + '&itdl_ext=mp4' + '&itdl_title=' + encodeURIComponent(sanitizeTitle(document.title)),
                'metadata': Base64.encode(JSON.stringify({
                    http_headers: {
                        'Referer': url,
                    }
                }))
            }));

        }, 1000)

    }
    container.appendChild(itdlBtn);
}

function loadDlBtn() {
    document.querySelectorAll('.card-horizontal').forEach(function (item, index, list) {
        var oldBtn = item.querySelector('.itdl-btn');
        if (!oldBtn) {
            createDlBtn(item)
        }
    })

    document.querySelectorAll('.card-vertical').forEach(function (item, index, list) {
        var oldBtn = item.querySelector('.itdl-btn');
        if (!oldBtn) {
            createDlBtn(item)
        }
    })
}

function loadDlBtnForUserPage() {
    document.querySelectorAll('.gif-preview').forEach(function (item, index, list) {
        var oldBtn = item.querySelector('.itdl-btn');
        if (!oldBtn) {
            createDlBtn(item)
        }
    })
}

function loadDlBtnForDetailPage() {
    document.querySelectorAll('.player-video').forEach(function (item, index, list) {
        var oldBtn = item.querySelector('.itdl-btn');
        if (!oldBtn) {
            createDlBtn(item)
        }
    })
}

function createStyle() {
    if (!document.getElementById('itubego_style')) {
        var css = `
            .itdl-btn {
                position: absolute;
                top: 1%;
                right: 1%;
                z-index: 99999;
                padding: .5rem;
                font-size: 1rem;
                vertical-align: middle;
                cursor: pointer;
                background: #00CF2E;
                color: white;
                border-radius: 16px;
                border: none;
                box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
            }
            .itdl-btn:hover{ background-color: #00A625 }
            .itdl-btn:focus{ outline: none; }
    
            .itdl-btn > img {
                width: 1.5rem !important;
                height: 1.5rem !important;
                vertical-align: middle !important;
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


function __init() {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    createStyle();

    const path = location.pathname;
    if (path.search('/') !== -1) {
        loadDlBtn()
    }
    if (path.search('/users/') !== -1) {
        loadDlBtnForUserPage()
    }

    if (path.search('/watch/') !== -1) {
        loadDlBtnForDetailPage();
    }
}

window.addEventListener('scroll', __init);

if (document.readyState === 'loading') {  // 此时加载尚未完成
    document.addEventListener('DOMContentLoaded', __init);
} else {  // 此时`DOMContentLoaded` 已经被触发
    __init();
}