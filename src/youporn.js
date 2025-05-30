setTimeout(function () {
    __init();
}, 2000)

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = async function () {
        const hls = page_params.video.playerParams.mainRoll.mediaDefinition.find(item => item.format === 'hls' || item.format === 'mp4');
        console.log('hls', hls);
        if (!hls?.videoUrl) {
            console.log('undefined hls')
            return;
        }
        const response = await fetch(hls?.videoUrl)
            .then(response => response.json())
            .then(response => {
                console.log('response', response)
                // const urlObj = response.find(item => Array.isArray(item.quality) || item.quality === '1080' || item.quality === '720' || item.quality === '480' || item.quality === '240')
                let videoUrl = response[0].videoUrl;
                let maxQuality = 0;
                for (let i = 0; i < response.length; i++) {
                    const item = response[i];
                    const quality = Number(item.quality);
                    if (isNaN(quality))
                        continue;

                    if (quality > maxQuality) {
                        videoUrl = item.videoUrl;
                        maxQuality = quality;
                    }
                }
                console.log('@quality:', maxQuality);
                console.log('@videoUrl:', videoUrl);

                let finalUrl = appendQueryParam(videoUrl, 'media_title', encodeURIComponent(sanitizeTitle(document.title)));

                //image_url
                const thumbnailUrl = page_params.video.playerParams.mainRoll.poster;
                console.log("@thumbnailUrl", thumbnailUrl)
                if (thumbnailUrl.length > 0) {
                    finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbnailUrl)
                }

                const data = JSON.stringify({
                    'url': finalUrl,
                    'metadata': Base64.encode(JSON.stringify({
                        http_headers: {
                            'Referer': 'https://www.youporn.com/',
                        }
                    }))
                });
                console.log('@send bridge data', data)

                bridge.download(data);
                return true;
            })
    }
    container.appendChild(itdlBtn);
}
function loadDlBtn() {
    document.querySelectorAll('.video-wrapper').forEach(function (item, index, list) {
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

async function getMedia(url) {
    try {
        const response = await fetch(url);

        if (!response.ok) {
            console.log(`HTTP error! Status: ${response.status}`);
            return null;
        }

        const data = await response.json();
        console.log('Data:', data);
        return data[data.length - 1].videoUrl;
    } catch (error) {
        console.error('Error fetching data:', error);
        return null;
    }
}