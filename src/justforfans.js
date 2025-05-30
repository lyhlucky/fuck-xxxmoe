setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    createStyle();
    loadDlBtn();
}, 1000)

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');

    itdlBtn.onclick = function () {
        if (/^\/(previews)$/.test(window.location.pathname)) {
            const onclickString = container.getAttribute('onclick');
            console.log('@@@click', onclickString)
            const regex = /mediaSheet\(([^)]+)\)/;
            const match = regex.exec(onclickString);
            console.log('@match', match)
            if (match) {
                const argumentsString = match[1];
                const regexQuote = /['"]([^'"]+)['"]/g;
                const argumentsArray = [];
                let quoteMatch;

                while ((quoteMatch = regexQuote.exec(argumentsString)) !== null) {
                    argumentsArray.push(quoteMatch[1]);
                }
                const link = argumentsArray[argumentsArray.length - 1];
                console.log('@get link', link)
                const mediaTitle = container.querySelector('.mediaTitle').innerText || document.title;
                bridge.download(JSON.stringify({
                    'url': appendQueryParam(link, 'media_title', sanitizeTitle(mediaTitle)),
                    'metadata': Base64.encode(JSON.stringify({
                        http_headers: {
                            'Referer': link,
                        }
                    }))
                }));
            } else {
                console.log('not found')
                return false;
            }
        } else {
            let url, mediaTitle;

            const videoBlock = container.querySelector('.videoBlock a')
            if (!videoBlock) {
                console.log('undefine videoBlock')
                const preview = container.querySelector('.videoPreview');
                url = preview?.src
                if (!preview) {
                    url = container.querySelector('video').src
                }
                console.log('@video url', url)
            } else {
                const onclickContent = videoBlock.getAttribute('onclick');

                // 查找参数的开始和结束位置
                const startIdx = onclickContent.indexOf("{");
                const endIdx = onclickContent.lastIndexOf("}");

                if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
                    const argumentJson = onclickContent.substring(startIdx, endIdx + 1);
                    const parsedArgument = JSON.parse(argumentJson);

                    console.log(parsedArgument);
                    url = parsedArgument['1080p'] || parsedArgument['540p'];
                    console.log('@url', url)
                } else {
                    console.log("undefined url");
                    return;
                }
            }

            mediaTitle = container.querySelector('.fr-view')?.innerText || document.title;
            console.log('@mediaTitle', mediaTitle);
            bridge.download(JSON.stringify({
                'url': appendQueryParam(url, 'media_title', sanitizeTitle(mediaTitle)),
                'metadata': Base64.encode(JSON.stringify({
                    http_headers: {
                        'Referer': url,
                    }
                }))
            }));
        }

    }

    // append itl btn after repeat btn
    const repaetBtn = container.querySelector('.mbsc-card-header') || container
    if (repaetBtn != null) {
        repaetBtn.append(itdlBtn)
    }
}

function loadDlBtn() {
    let postAreaAutoScroll, items;
    if (/^\/(previews)$/.test(window.location.pathname)) {
        postAreaAutoScroll = document.getElementById('exploreArea');
        items = postAreaAutoScroll.querySelectorAll('li a')
    } else {
        postAreaAutoScroll = document.getElementById('mainPage')
        items = postAreaAutoScroll.querySelectorAll('div.video')
    }
    if (items.length === 0) {
        postAreaAutoScroll = document.getElementById('postAreaPlaylist')
        items = postAreaAutoScroll.querySelectorAll('div.mbsc-card')
    }
    items.forEach(function (item, index, list) {
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
                position: absolute !important;
                top: 1rem !important;
                right: 2.5rem !important;
                z-index: 99999 !important;
                font-size: .875em !important;
                font-weight: 400 !important;
                padding: 0.5rem .75rem !important;
                cursor: pointer !important;
                background: #00CF2E !important;
                color: white !important;
                border-radius: 1rem !important;
                border: none !important;
                box-shadow: 0 1rem 2rem 0 rgba(0, 0, 0, 0.2), 0 2rem 4rem 0 rgba(0, 0, 0, 0.19) !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                gap: .5rem !important;
            }
            .itdl-btn:hover{ background-color: #00A625 }
            .itdl-btn:focus{ outline: none; }
    
            .itdl-btn > img {
                position: unset !important;
                display: inline-block !important;
                width: 1.2rem !important;
                height: 1.2rem !important;
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


window.addEventListener('scroll', loadDlBtn)

if (document.readyState === 'loading') {  // 此时加载尚未完成
    document.addEventListener('DOMContentLoaded', loadDlBtn);
} else {  // 此时`DOMContentLoaded` 已经被触发
    loadDlBtn();
}