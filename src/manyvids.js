var videoSrc = null;
setInterval(function () {
    const path = location.pathname;
    if (path.search('/Video/') === -1) {
        return;
    }

    var isChanged = false;
    var videoEle = document.getElementsByTagName('video')[0];
    if (videoEle && videoEle.src !== videoSrc) {
        videoSrc = videoEle.src;
        isChanged = true;
    } else {
        var vpContainer = document.getElementsByTagName('mv-video-player')[0];
        if (vpContainer) {
            videoEle = vpContainer.shadowRoot.querySelector('video');
            if (videoEle) {
                if (videoEle && videoSrc !== videoEle.src) {
                    videoSrc = videoEle.src;
                    isChanged = true;
                }
            }
        }
    }

    if (isChanged) {
        var result = {
            url: videoSrc + '&itdl_ext=mp4' + '&itdl_title=' + encodeURIComponent(sanitizeTitle(document.title)),
            metadata: Base64.encode(JSON.stringify({
                http_headers: {
                    'Referer': window.location.href,
                }
            })),
        };

        // if exits, remove
        var dlBtn = document.getElementById('itdl-btn');
        if (dlBtn) {
            dlBtn.remove();
        }

        createDlBtn(function () {
            console.log('result:', result);
            bridge.download(JSON.stringify(result));
        });
    }
}, 1000);

function createDlBtn(clickHandler) {
    var css = `
        #itdl-btn {
            position: fixed;
            bottom: 30px;
            z-index: 99999;
            right: 30px;
            font-size: 25px;
            padding: 10px 20px;
            cursor: pointer;
            background: #00CF2E;
            color: white;
            border-radius: 5px;
            border: none;
            box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
        }
        #itdl-btn:hover{ background-color: #00A625 }
        #itdl-btn:focus{ outline: none; }
    
        #itdl-btn img {
            display: inline-block;
            width: 30px;
            height: 30px;
            vertical-align: text-bottom;
        }
    `;

    if (!document.getElementById('itd_btn_style')) {
        var style = document.createElement('style');
        style.id = 'itd_btn_style'

        if (style.styleSheet) {
            style.styleSheet.cssText = css;
        } else {
            style.appendChild(document.createTextNode(css));
        }
        document.getElementsByTagName('head')[0].appendChild(style);
    }


    var body = document.getElementsByTagName('body')[0]
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.id = 'itdl-btn';
    itdlBtn.onclick = clickHandler;
    body.appendChild(itdlBtn);
}
