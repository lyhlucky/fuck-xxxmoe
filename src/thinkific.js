
setTimeout(function () {
    if (location.href.indexOf('l-team') !== -1) {
        // 删除全局按钮
        var commonBtn = document.getElementById('itdl-btn');
        commonBtn && commonBtn.remove();
        loadDlBtn();
    }
}, 1000)

function onClickDownload() {
    const iframe = document.querySelector("iframe");
    if (iframe) {
        let result = {
            url: location.href,
            metadata: Base64.encode(JSON.stringify({
                videoSrc: iframe.src
            }))
        }

        console.log("result:", result);
        bridge.download(JSON.stringify(result));
    } else {
        console.log("未找到 iframe");
    }
}

function loadDlBtn() {
    var commonBtn = document.getElementById('itdl-btn');  
    if (!commonBtn) {
        createDlBtn(onClickDownload);
    }
}
