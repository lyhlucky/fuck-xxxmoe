(function (){
    // 删除全局按钮
    setTimeout(() => {
       const commonBtn = document.getElementById('itdl-btn');
       commonBtn && commonBtn.remove();
    }, 10)

    const videoContainer = document.querySelector('.container .plyr');
    if (!videoContainer || videoContainer.querySelector('.itdl-btn')) {
        console.log('undefined video container or itdl-btn is exists.')
        return;
    }

    createStyle();
    const itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');

    itdlBtn.onclick = function () {
        let url;
        if (typeof hlsUrl === 'undefined') {
            console.log('undefined hlsUrl')
            return;
        }

        const mediaTitle = document.title;
        url = hlsUrl;

        console.log('@media', url, mediaTitle);
        bridge.download(JSON.stringify({
            'url': appendQueryParam(url, 'media_title', sanitizeTitle(mediaTitle)),
            'metadata': Base64.encode(JSON.stringify({
                http_headers: {
                    'Referer': url,
                }
            }))
        }));
    }

    videoContainer.append(itdlBtn);
})();

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
