var videoSrc = null;
setInterval(function() {
    var videoEle = document.getElementsByTagName('video')[0];

    if (videoEle) {
        if (videoEle.src && videoEle.src != videoSrc) {
            videoSrc = videoEle.src;
        } else {
            var sourceEle = videoEle.getElementsByTagName("source")[0];
            if (sourceEle && sourceEle.src != videoSrc) {
                videoSrc = sourceEle.src;
            }
        }
    }

    if (videoSrc.substring(0, 5) == "blob:") {
        var scriptList = document.getElementsByTagName("script");
        for (var n = 0; n < scriptList.length; ++n) {
            var data = scriptList[n].innerHTML;
            if (data.indexOf("\"video_url\":") != -1) {
                var value = data.substring(data.indexOf("\"video_url\":") + 12);
                var videoUrl = value.substring(0, value.indexOf(","));
                videoUrl = decodeURIComponent(JSON.parse(videoUrl));
                videoSrc = videoUrl;
                break;
            }
        }
    }

    if (videoSrc && videoSrc.length > 0) {
        var result = {
            url: videoSrc + '&itdl_ext=mp4' + '&itdl_title=' + encodeURIComponent(sanitizeTitle(document.title)),
            metadata: Base64.encode(JSON.stringify({
                http_headers: {
                    'Referer': window.location.href,
                }
            })),
        };

        // if exits, remove
        var dlBtn = document.getElementById('itdl-btn');
        if (dlBtn) {
            dlBtn.remove();
        }

        createDlBtn(function() {
            console.log(result);
            bridge.download(JSON.stringify(result));
        });
    }

}, 500);