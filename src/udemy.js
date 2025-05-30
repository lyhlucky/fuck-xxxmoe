
setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    setInterval(function () {
        loadDlBtn();
    }, 1000)
}, 1)

function onClickDownload() {
    var videoDiv = document.querySelector('video');
    var takingDIv = document.querySelector('div[data-module-id="course-taking"]');

    var title = ''
    var titleDiv = document.querySelector('li[aria-current="true"]');
    if (titleDiv) {
        var titleItem = titleDiv.querySelector('span[data-purpose="item-title"]');
        if (titleItem) {
            title = titleItem.innerText;
        }
    } else {
        titleDiv = document.querySelector('section.lecture-view--container--mrZSm');
        if (titleDiv) {
            title = titleDiv.getAttribute('aria-label');
        }
    }

    if (title === '') {
        title = document.title;
    }
    console.log('@title:', title);
    title = encodeURIComponent(sanitizeTitle(title));

    if (!videoDiv.src.startsWith('blob:') && videoDiv.src.indexOf('.m3u8') == -1) {
        var finalUrl = updateUrlParameter(videoDiv.src, 'itdl_title', title);
        finalUrl = updateUrlParameter(finalUrl, 'itdl_ext', 'mp4');
        console.log("@finalUrl", finalUrl);

        result = {
            url: finalUrl,
            metadata: ''
        }

        bridge.download(JSON.stringify(result));
    } else {
        var argdata = takingDIv.getAttribute('data-module-args');
        const jsonObj = JSON.parse(argdata);
        var courseid = jsonObj.courseId;
        console.log('@courseid', courseid);

        var itemtype = jsonObj.initialCurriculumItemType;
        var itemid = location.href.split('/').pop().split('#').shift();
        console.log('@itemid:', itemid);

        result = {
            url: location.href,
            metadata: Base64.encode(JSON.stringify({
                courseId: courseid,
                type: itemtype,
                itemId: itemid,
                title: title
            }))
        }

        bridge.download(JSON.stringify(result));
    }
}

function loadDlBtn() {
    var commonBtn = document.getElementById('itdl-btn');
    var videoDiv = document.querySelector('video');
    var takingDIv = document.querySelector('div[data-module-id="course-taking"]');

    if (videoDiv && takingDIv) {
        if (!commonBtn) {
            createDlBtn(onClickDownload);
        }
    } else {
        // 删除全局按钮
        commonBtn && commonBtn.remove();
    }
}
