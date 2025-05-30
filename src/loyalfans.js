setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    createStyle();
    loadDlBtn();
}, 1000)

function createDlBtn(container, player) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');

    itdlBtn.onclick = function () {
        const url = container.querySelector('source').getAttribute('src')
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
    player.append(itdlBtn)
}

function loadDlBtn() {
    const videos = document.querySelectorAll('video')
    videos.forEach(function (item, index, list) {
        const player = item.parentNode;
        const oldBtn = player.querySelector('.itdl-btn')
        if (!oldBtn) {
            createDlBtn(item, player)
        }
    })
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

window.addEventListener('scroll', function () {
    loadDlBtn();
})

