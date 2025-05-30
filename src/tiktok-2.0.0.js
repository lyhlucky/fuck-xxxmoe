function loadDlBtn(item) {
    var anchorItem = item.querySelector('a.avatar-anchor')
    if (!anchorItem) {
        anchorItem = item.querySelector('a[data-e2e="video-author-avatar"]')
    }
    var author = extractSubstring(anchorItem.href)
    console.log('@author', author)
    const videoContainer = item.querySelector('div.tiktok-web-player');
    const videoContainerId = videoContainer.id;
    const videoId = videoContainerId.substring(videoContainerId.lastIndexOf('-') + 1);
    console.log('@videoId', videoId)

    const URI = `https://${window.location.host}/${author}/video/${videoId}`
    console.log('@URI', URI)
    var playerWrapper = item.querySelector('div.css-1fofj7p-DivBasicPlayerWrapper');
    const oldBtn = playerWrapper.querySelector('.itdl-btn')
    if (!oldBtn) {
        createDlBtn(playerWrapper, URI, true)
    }
}

function createDlBtn(container, url, is_absolute = false) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    if (is_absolute) {
        itdlBtn.classList.add('itdl-absolute')
    }

    itdlBtn.onclick = function () {
        console.log('#url', url)
        bridge.download(JSON.stringify({
            'url': url,
            'metadata': Base64.encode(JSON.stringify({
                http_headers: {
                    'Referer': url,
                }
            }))
        }));
    }
    // append itl btn after repeat btn
    container.append(itdlBtn)
}

function createStyle() {
    if (!document.getElementById('itubego_style')) {
        var css = `
            .itdl-btn {
                margin: .5rem 0;
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
            .itdl-absolute {
                position: absolute;
                top: 3.5rem;
                right: 1rem;
                z-index: 9999;
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

function extractSubstring(str) {
    var atPosition = str.indexOf('@');
    var slashPosition = str.indexOf('/live');

    if (atPosition === -1) {
        return '';
    }

    if (slashPosition === -1) {
        return str.substring(atPosition);
    }

    return str.substring(atPosition, slashPosition);
}

createStyle();

function _initDLButtons() {
    // video info page
    // if (/\/@[a-zA-Z0-9_.-]+\/video\/[a-zA-Z0-9_.-]+$/.test(location.pathname)) {
    if (location.href.indexOf('/video/') !== -1) {
        const container = document.querySelector('div.tiktok-web-player');
        console.log("@container", container);
        const oldBtn = container.querySelector('.itdl-btn')
        if (!oldBtn) {
            createDlBtn(container, location.href, true)
        }
    } else {
        const itemContainers = document.querySelectorAll('article[data-e2e="recommend-list-item-container"]')
        // 删除全局按钮
        const commonBtn = document.getElementById('itdl-btn');
        commonBtn && commonBtn.remove();

        itemContainers.forEach(function (element) {
            if (isInViewport(element)) {
                createStyle();
                loadDlBtn(element);
            }
        });
    }
}

function isInViewport(element) {
    const video = element.querySelector('video')
    if (!video) {
        return false;
    }
    const rect = video.getBoundingClientRect();
    return (rect.top >= 0) && (rect.bottom <= window.innerHeight);
}

// if (document.readyState === 'loading') {  // 此时加载尚未完成
//     document.addEventListener('DOMContentLoaded', _initDLButtons);
// } else {  // 此时`DOMContentLoaded` 已经被触发
//     _initDLButtons();
// }

// window.addEventListener('scroll', _initDLButtons)

setInterval(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    if (location.href.indexOf('/video/') !== -1) {
        const container = document.querySelector('div.tiktok-web-player');
        const oldBtn = container.querySelector('.itdl-btn')
        if (!oldBtn) {
            createDlBtn(container, location.href, true)
        }
    } else {
        const itemContainers = document.querySelectorAll('article[data-e2e="recommend-list-item-container"]')
        itemContainers.forEach(function (element) {
            if (isInViewport(element)) {
                createStyle();
                loadDlBtn(element);
            } else {
                console.log("Not in Viewport!");
            }
        });
    }
}, 1000)
