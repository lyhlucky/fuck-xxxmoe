function unicodeToChar(text) {
    return text.replace(/\\u[\dA-F]{4}/gi,
        function (match) {
            return String.fromCharCode(parseInt(match.replace(/\\u/g, ''), 16));
        });
}

var prev = null;
setInterval(function () {
    if (location.href == prev) {
        return;
    }

    prev = location.href;

    var scripts = document.getElementsByTagName('script');
    for (let i = 0; i < scripts.length; ++i) {
        var script = scripts[i];
        var text = script.innerText;
        if (text.indexOf("HasteSupportData") != -1 && text.indexOf("playable_url_quality_hd") != -1) {
            var myRegexp = /"playable_url_quality_hd":"(.*)","spherical_video_fallback_urls/g;
            var match = myRegexp.exec(text);
            var videoUrl = match[1].replace(/\\/g, '');

            if (videoUrl.indexOf('","spherical_video_fallback_urls') != -1) {
                videoUrl = videoUrl.split('","spherical_video_fallback_urls')[0];
            }

            var title = "facebook video";
            try {
                myRegexp = /"title_with_entities":{"text":"(.*)"},"target/
                match = myRegexp.exec(text);
                var matchStr = match[1];
                if (matchStr.indexOf('"},"target')) {
                    matchStr = matchStr.split('"},"target')[0].substr(1);
                }
                title = unicodeToChar(matchStr);
                title = title.replace(/[/\\?%*:|"<>]/g, '-');
            } catch (e) {
                console.log(e);
            }

            var result = {
                url: videoUrl + '&itdl_ext=mp4' + '&itdl_title=' + encodeURIComponent(title),
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

            createDlBtn(function () {
                console.log(result);
                bridge.download(JSON.stringify(result));
            });

            break;
        }
    }

    // var metas = document.getElementsByTagName('meta');
    // for (let i = 0; i < metas.length; ++i) {
    //     const meta = metas[i];
    //     if (meta.content.indexOf('.mp4') != -1) {
    //         var result = {
    //             url: meta.content + '&itdl_ext=mp4' + '&itdl_title=' + encodeURIComponent(document.title),
    //             metadata: Base64.encode(JSON.stringify({
    //                 http_headers: {
    //                     'Referer': window.location.href,
    //                 }
    //             })),
    //         };

    //         // if exits, remove
    //         var dlBtn = document.getElementById('itdl-btn');
    //         if (dlBtn) {
    //             dlBtn.remove();
    //         }

    //         createDlBtn(function () {
    //             console.log(result);
    //             bridge.download(JSON.stringify(result));
    //         });

    //         break;
    //     }
    // }
}, 500);
