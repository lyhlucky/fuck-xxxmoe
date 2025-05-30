setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    setInterval(function () {
        loadDlBtn();
    }, 1000)
}, 1)

function onClickDownload() {

    var metaTag = document.querySelector('meta[property="og:image"]');

    // 获取缩略图URL
    const thumbnailUrl = metaTag.content;
    console.log("@thumbnailUrl", thumbnailUrl)
    // 获取标题
    const title = document.title;
    console.log("@title", title)

    var scripts = document.getElementsByTagName('script');

    for(let i=0;i<scripts.length;i++){
        var script = scripts[i];
        var text = script.innerText;
        var finalUrl='';
        if(text.indexOf("window.scenario") !== -1 && text.indexOf("window.player.on") !== -1){

            var strs=text.split(/\n/);
            for(let j=0;j<strs.length;j++){
                var tmpstr=strs[j];
                if(tmpstr.indexOf('eval(function') !== -1){
                    console.log("@eval",tmpstr);
                    const videoUrl = eval(tmpstr);
                    finalUrl = updateUrlParameter(videoUrl, 'media_title', title);
                    if(thumbnailUrl.length>0){
                        finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbnailUrl);
                    }
                    console.log("@url:",finalUrl);                    
                    break;
                }
            }
        }
        if(finalUrl!=''){
            bridge.download(JSON.stringify({
                url: finalUrl,
                metadata: ''
            }));
            break;
        }
    }
}

function loadDlBtn() {
    var commonBtn = document.getElementById('itdl-btn');
    var div = document.getElementsByClassName("plyr__video-wrapper")
    if (div.length>0) {
        if (!commonBtn) {
            createDlBtn(onClickDownload);
        }
    } else {
        // 删除全局按钮
        commonBtn && commonBtn.remove()
    }
}

