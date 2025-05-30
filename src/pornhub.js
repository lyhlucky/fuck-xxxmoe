setTimeout(function () {
    __init();
}, 2000)

function createDlBtn(container) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    itdlBtn.onclick = async function () {
        var player = document.getElementById("player");
        var videoId = player.dataset['video-id'];
        console.log('videoId', videoId)
        if (!player) {
            console.log('undefined')
            return;
        }

        var strList = player.querySelector('script').innerHTML.split("var ");
        console.log('strList', strList)
        let URLs = [];
        const regex = /.*flashvars_(\d+).*/;
        for (let i = 0; i < strList.length; i++) {
            var str = strList[i];
            if (regex.test(str)) {
                console.log('@@@@@@', str);
                URLs.push(str)
            }
        }

        if (URLs.length === 0) {
            console.log('undefined')
            return;
        }
        console.log('@URLs', URLs);
        const mediaStr = URLs[0];
        const videoJson = eval(mediaStr);
        console.log('@flashvars', videoJson)
        // const desiredMedia = videoJson.mediaDefinitions.find(media => {
        //     const defaultQuality = media.defaultQuality;
        //     return defaultQuality !== false && defaultQuality !== true;
        // });
        // const desiredMedia = videoJson.mediaDefinitions[0];

        let videoUrl = videoJson.mediaDefinitions[0].videoUrl;
        let maxQuality = 0;
        for (let i = 0; i < videoJson.mediaDefinitions.length; i++) {
            const item = videoJson.mediaDefinitions[i];
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

        const thumbnailUrl = videoJson['image_url']
        console.log("@thumbnailUrl", thumbnailUrl)
        if (thumbnailUrl.length > 0) {
            finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbnailUrl)
        }

        const json = JSON.stringify({
            'url': finalUrl,
            'metadata': Base64.encode(JSON.stringify({
                http_headers: {
                    'Referer': location.href,
                }
            }))
        });
        console.log('@send bridge data', json)
        bridge.download(json);
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