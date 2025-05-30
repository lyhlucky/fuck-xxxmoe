
setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    createStyle();

    setInterval(function () {
        loadDlBtn();
    }, 1500)
}, 1)

function onClickDownload() {
    var videoDiv = document.querySelector('div[id="player_container"]');
    var videoItem = videoDiv.querySelector('video');

    // 获取下载URL
    const videoUrl = videoItem.src;
    console.log("@videoUrl", videoUrl);

    // 获取标题
    var titleItem = document.querySelector('li[class="breadcrumb-item active"]');
    let videoTitle = titleItem.childNodes.item(0).innerText;
    console.log("@videoTitle:", videoTitle);

    // 获取缩略图
    let thumbnailUrl = '';
    const infoScript = document.querySelector('script[type="application/ld+json"]');
    if (infoScript) {
        try {
            const data = JSON.parse(infoScript.innerText);
            thumbnailUrl = data['thumbnailUrl'];
        } catch (e) {
            console.log("@Parse json failed", e);
        }
    }
    console.log("@thumbnailUrl", thumbnailUrl);

    var finalUrl = updateUrlParameter(videoUrl, 'itdl_title', encodeURIComponent(sanitizeTitle(videoTitle)));
    finalUrl = updateUrlParameter(finalUrl, 'itdl_ext', "mp4");
    if (thumbnailUrl.length > 0) {
        finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbnailUrl);
    }
    console.log("@finalUrl", finalUrl);

    result = {
        url: finalUrl,
        metadata: Base64.encode(JSON.stringify({
            http_headers: {
                Referer: location.href
            }
        }))
    }

    bridge.download(JSON.stringify(result));
}

function loadDlBtn() {
    var commonBtn = document.getElementById('itdl-btn');
    var videoDiv = document.querySelector('div[id="player_container"]');

    if (videoDiv) {
        if (!commonBtn) {
            var iframeArry = document.querySelectorAll('iframe');
            var iframeLast = iframeArry.item(iframeArry.length - 1);

            if (iframeLast) {
                var itdlBtn = document.createElement('button');
                itdlBtn.innerHTML = ITL_BUTTON;
                itdlBtn.classList.add('itdl-btn');
                itdlBtn.id = 'itdl-btn';
                itdlBtn.onclick = onClickDownload;
                iframeLast.parentNode.insertBefore(itdlBtn, iframeLast);
            } else {
                createDlBtn(onClickDownload);
            }
        }
    } else {
        // 删除全局按钮
        commonBtn && commonBtn.remove();
    }
}

function createStyle() {
    if (!document.getElementById('itubego_style')) {
        var css = `
            .itdl-btn {
                
                z-index: 99999;
                position: relative;
                font-size: .875em;
                font-weight: 100;
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
                width: 1.5em !important;
                height: 1.5em !important;
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
