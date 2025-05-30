//********************************************************************************************
// @Brief pornzog站是一个搬运站
// https://pornzog.com
// 支持站点：
// [
//     https://manysex.com/, https://txxx.me/, https://fuxxx.com/, https://upornia.com/,
//     https://hclips.com/, https://hdzog.com/, https://hotmovs.com/, https://ooxxx.com/,
//     https://pornl.com/, https://voyeurhit.com/, https://voyeurhit.com/, https://tubepornclassic.com/,
//     https://vjav.com/, https://tporn.xxx/, https://thegay.com/, https://shemalez.com/
//     https://vxxx.com/, https://porntop.com/
// ]
// @Create 2025/4/9 
//********************************************************************************************

setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    createStyle();
    loadDlBtn();

    setInterval(function () {
        loadDlBtn();
    }, 1000)
}, 1000)

function createDlBtn(container, isCross) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = function () {
        if (isCross) {
            const iframe = container.querySelector('iframe');
            const src = iframe?.src;
            if (!src) {
                console.error('no iframe');
                return;
            }
            window.location.href = src; // 页面跳转
        } else {
            const videoItem = container.querySelector('video');
            let videoUrl = videoItem?.src;
            if (!videoUrl) {
                console.log('no video');
                return;
            }
            console.log('@videoUrl:', videoUrl);
    
            let thumbnailUrl = '';
            const previewDiv = document.querySelector('.jw-preview');
            if (previewDiv) {
                const style = window.getComputedStyle(previewDiv);
                const backgroundImage = style.backgroundImage;
                
                // 提取 url() 里的地址
                const match = backgroundImage.match(/url\(["']?(.*?)["']?\)/);
                
                if (match && match[1]) {
                    thumbnailUrl = match[1];
                    console.log('@thumbnailUrl:', thumbnailUrl);
                }
            }

            let title = document.title;
            console.log('@title:', title);
            title = encodeURIComponent(sanitizeTitle(title));

            if (!videoUrl.startsWith("blob:")) {
                let finalUrl = updateUrlParameter(videoUrl, 'itdl_title', title);
                finalUrl = updateUrlParameter(finalUrl, 'itdl_ext', 'mp4');
                if (thumbnailUrl.length > 0) {
                    finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbnailUrl)
                }
    
                bridge.download(JSON.stringify({
                    url: finalUrl,
                    'metadata': Base64.encode(JSON.stringify({
                        http_headers: {
                            'Referer': location.href
                        }
                    }))
                })); 
            } else {
                let finalUrl = updateUrlParameter(location.href, 'itdl_from', 'pornzog');
                bridge.download(JSON.stringify({
                    url: finalUrl,
                    'metadata': Base64.encode(JSON.stringify({
                        http_headers: {
                            'Referer': location.href
                        },
                        title: title,
                        thumbnail: thumbnailUrl
                    }))
                })); 
            }
        }
    }
    container.appendChild(itdlBtn);
}

function loadDlBtn() {
    // pornzog.com 查找iframe定位到视频播放链接
    const iframeContainers = ['.fluid-width-video-wrapper', '.video__player'];

    iframeContainers.forEach(function (selector) {
        document.querySelectorAll(selector).forEach(function (item) {
            const iframe = item.querySelector('iframe');
            if (iframe && !item.querySelector('.itdl-btn')) {
                createDlBtn(item, true);
            }
        });
    });

    // 非iframe
    const videoContainers = ['.pplayer-container', '.player-wrap', '.videoplayer-container', '.videoplayer-wrapper'];

    videoContainers.forEach(function (selector) {
        document.querySelectorAll(selector).forEach(function (item) {
            const videoItem = item.querySelector('video');
            if (videoItem && !item.querySelector('.itdl-btn')) {
                createDlBtn(item, false);
            }
        });
    });
}
