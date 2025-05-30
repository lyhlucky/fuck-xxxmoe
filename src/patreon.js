let IS_LOADED = false;
function loadDlBtn(item) {
    const title = item.querySelector('[data-tag="post-title"]');

    const oldBtn = item.querySelector('.itdl-btn')
    if (!oldBtn) {
        createDlBtn(item, title)
    }
}
function createDlBtn(container, title) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');

    // pattern /posts/xxx
    if (/^\/(posts\/[\w@-]+)$/.test(window.location.pathname)) {
        itdlBtn.addEventListener('click', sendToQT)

        function sendToQT () {
            if (typeof bridge === 'undefined') {
                initQWebChannel(qt.webChannelTransport);
            }

            const data = window.patreon.bootstrap;
            // console.log('@data', data)
            // console.log('@m3u8', data.post.data.attributes.post_file.url)
            const videoUrl = data.post.data.attributes.post_file.url;

            bridge.download(JSON.stringify({
                'url': appendQueryParam(videoUrl, 'media_title', sanitizeTitle(document.title)),
                'metadata': Base64.encode(JSON.stringify({
                    http_headers: {
                        'Referer': videoUrl,
                    }
                }))
            }));
        }
        if (getUrlParam('auto-download')) {
            const updatedUrl = updateUrlParameter(window.location.href, 'auto-download', null)
            window.history.pushState({}, document.title, updatedUrl);

            setTimeout(() => {
                console.log("IS_LOADED:", IS_LOADED);
                if (IS_LOADED) return;

                IS_LOADED = true;
                console.log("@itdlBtn.click()");
                itdlBtn.click();
            }, 500)
        }

    } else {
        itdlBtn.onclick = function () {
            console.log("itdlBtn.onclick location.href", IS_LOADED);
            location.href = appendQueryParam(title.querySelector('a').href, 'auto-download', 1)
        }
    }

    // pattern xxx/posts | /posts/xxx | home
    const urlPattern = /^\/(?:[\w@-]+\/posts|posts\/[\w@-]+|home)$/;

    const testUrl = window.location.pathname;
    if (urlPattern.test(testUrl)) {
        // append itl btn after repeat btn
        container.append(itdlBtn)
    }

}
function createStyle() {
    if (!document.getElementById('itubego_style')) {
        var css = `
            .itdl-btn {
                position: absolute;
                top: 1rem;
                right: .5rem;
                margin-left: 1rem;
                z-index: 99999;
                font-size: .875em;
                font-weight: 400;
                padding: 0.5rem .75rem;
                cursor: pointer;
                background: #00CF2E;
                color: white;
                border-radius: 1rem;
                border: none;
                box-shadow: 0 1rem 2rem 0 rgba(0, 0, 0, 0.2), 0 2rem 4rem 0 rgba(0, 0, 0, 0.19);
            }
            .itdl-btn:hover{ background-color: #00A625 }
            .itdl-btn:focus{ outline: none; }

            .itdl-btn > img {
                display: inline-block !important;
                width: 1.5em !important;
                height: 1.5em !important;
                vertical-align: middle !important;
            }
            .itl-relative {
                position: relative;
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

function _initDLButtons() {
    const itemContainers = document.querySelectorAll('div[data-tag="post-card"]')
    // 删除全局按钮
    const commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    itemContainers.forEach(function (element) {
        const rect = element.getBoundingClientRect();
        const visible = rect.top < window.innerHeight && rect.bottom >= 0;
        if (visible && element.querySelector('video')) {
            element.classList.add('itl-relative')
            createStyle();
            loadDlBtn(element);
        }
    });
}

if (typeof qt !== 'undefined') {
    initQWebChannel(qt.webChannelTransport);
}

function initQWebChannel(transport) {
    new QWebChannel(transport, function (channel) {
        window.bridge = channel.objects.bridge;
    })
}

createStyle();
if (!/^\/(posts\/[\w@-]+)$/.test(window.location.pathname)) {
    window.addEventListener('scroll', _initDLButtons)
}

if (document.readyState === 'loading') {  // 此时加载尚未完成
    document.addEventListener('DOMContentLoaded', _initDLButtons);
} else {  // 此时`DOMContentLoaded` 已经被触发
    _initDLButtons();
}
