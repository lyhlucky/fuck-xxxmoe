setTimeout(function () {
    __init();
}, 2000)

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = async function () {
        const playerId = Object.keys(page_params.video_player_setup)[0]
        const playerDiv = Object.getOwnPropertyDescriptor(page_params.video_player_setup, playerId).value
        const hls = playerDiv.createPlayerSetup.mainRoll.mediaDefinition.find(item => item.format === 'hls' || item.format === 'mp4');

        if (!hls?.videoUrl) {
            console.log('undefined hls')
            return;
        }

        const title = playerDiv.createPlayerSetup.mainRoll.title;
        console.log('@title', title);

        // 获取缩略图URL
        const thumbnailUrl = playerDiv.createPlayerSetup.mainRoll.poster
        console.log("@thumbnailUrl", thumbnailUrl)

        const hlsUrl = document.location.origin + hls?.videoUrl

        await fetch(hlsUrl)
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

                let finalUrl = updateUrlParameter(videoUrl, 'media_title', encodeURIComponent(sanitizeTitle(title)))
                if (thumbnailUrl.length > 0) {
                    finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbnailUrl)
                }
                console.log("@finalUrl", finalUrl)

                const data = JSON.stringify({
                    'url': finalUrl,
                    'metadata': Base64.encode(JSON.stringify({
                        http_headers: {
                            'Referer': 'https://www.redtube.com/',
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
    const player = document.getElementById('redtube-player');
    var oldBtn = player.querySelector('.itdl-btn');

    if (!oldBtn) {
        createDlBtn(player)
    }
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

