
setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    setInterval(function () {
        loadDlBtn();
    }, 1000)
}, 1)

function onClickDownload() {
    var video_pc = document.querySelector("div#video_pc")
    var options_list = video_pc.querySelectorAll("li.option-item")
    if (options_list.length > 0) {
        // 本地最新播放缓存信息
        const userInfo = JSON.parse(localStorage.getItem('userInfo'))
        const uid = userInfo['uid']
        const hist = JSON.parse(localStorage.getItem(`${uid}_hist`))
        if (hist.length < 1) {
            console.log("@error: not find hist")
            return;
        }
        const lastHist = hist[0]

        // 获取集数 比如第1集
        const searchParams = new URLSearchParams(window.location.search);
        var idx = searchParams.get('idx');
        if (!idx) {
            idx = lastHist["lastChapterIndex"]
        }
        console.log("@idx", idx)

        // 获取标题
        const title = encodeURIComponent(sanitizeTitle(`Episode ${idx} - ${document.title}`))
        console.log("@title", title)

        // 获取缩略图URL
        const thumbnailUrl = lastHist['start_play']['video_pic']
        console.log("@thumbnailUrl", thumbnailUrl)

        // 获取下载URL
        const videoUrl = options_list[options_list.length - 1].getAttribute("url")
        console.log("@videoUrl", videoUrl)

        var finalUrl = updateUrlParameter(videoUrl, 'media_title', title)
        if (thumbnailUrl.length > 0) {
            finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbnailUrl)
        }
        console.log("@finalUrl", finalUrl)

        bridge.download(JSON.stringify({
            url: finalUrl,
            metadata: ''
        }));
    }
}

function loadDlBtn() {
    var commonBtn = document.getElementById('itdl-btn');

    if (location.href.indexOf("/episodes/") !== -1 || location.href.indexOf("videos?book_id=") !== -1) {
        if (!commonBtn) {
            createDlBtn(onClickDownload);
        }
    } else {
        // 删除全局按钮
        commonBtn && commonBtn.remove()
    }
}
