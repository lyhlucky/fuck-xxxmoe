
setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();


    setInterval(function () {
        loadDlBtn();
    }, 1000)
}, 1)

var css_candfans = `
    #itdl-btn {
        position: fixed;
        bottom: 30px;
        z-index: 99999;
        right: 30px;
        display: flex;
        align-items: center;
        font-size: 25px;
        padding: 10px 20px;
        cursor: pointer;
        background: #00CF2E;
        color: white;
        border-radius: 5px;
        border: none;
        box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
    }
    #itdl-btn:hover{ background-color: #00A625 }
    #itdl-btn:focus{ outline: none; }

    #itdl-btn img {
        width: 30px;
        height: 30px;
        vertical-align: text-bottom;
        float: left;
        margin-right:10px;
    }
    `;


function onClickDownload() {
    // const div = document.getElementsByClassName('slide swiper-slide swiper-slide-active');

    var slideArry = document.querySelectorAll('div[class="slide keen-slider__slide"]')
    var curSlide = null
    for (let i = 0; i < slideArry.length; i++) {
        let progbar = slideArry.item(i).querySelector('div[role="progressbar"]')
        if (progbar) {
            if (progbar.className != 'v-progress-linear indicator theme--light') {
                curSlide = slideArry.item(i)
                break
            }
        } else {
            console.log('progress bar not found!')
        }

    }

    if (slideArry.length > 0 && curSlide === null) {
        curSlide = slideArry.item(0)
    }

    var videoArry = curSlide.querySelectorAll('video')
    console.log('curSlide:', curSlide)
    console.log('style:', videoArry.item(0).getAttribute('style'))

    var thumbUrl = null
    var videoUrl = null
    var videoDiv = null
    if (videoArry.length > 1) {
        var curVideo = null
        for (let i = 0; i < videoArry.length; i++) {
            let styleElem = videoArry.item(i).getAttribute('style')
            if (styleElem === null || styleElem === '') {
                videoDiv = videoArry.item(i)

                break
            }
        }
    }

    if (videoDiv === null) {
        videoDiv = videoArry.item(0)
    }

    thumbUrl = videoDiv.poster
    videoUrl = videoDiv.src

    var title = null
    var descElem = curSlide.querySelector('div[class="reel-description"]')
    if (descElem) {
        title = descElem.innerText
    } else {
        title = location.href.remove('https://')
        console.log('div reel-description not found!')
    }

    // 获取标题
    title = encodeURIComponent(sanitizeTitle(`${title} `))
    console.log("@title", title);
    console.log("video:", videoUrl, "thumUrl:", thumbUrl);

    var finalUrl = updateUrlParameter(videoUrl, 'itdl_title', title);

    finalUrl = updateUrlParameter(finalUrl, 'itdl_ext', 'mp4');
    finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbUrl);



    console.log("@url:", finalUrl);

    if (finalUrl != '') {
        bridge.download(JSON.stringify({
            url: finalUrl,
            metadata: ''
        }));
    }


}

function onClickDownloadBuy() {
    // const cookie = document.cookie;
    const localurl = window.location.href;
    const arry = localurl.split('/');

    fetch('https://candfans.jp/api/contents/get-timeline/' + arry[arry.length - 1], {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            // 'Cookie' : cookie,
            'Referer': localurl
        }
    })
        .then(response => response.json())
        .then(
            function (data) {
                var urlM3u8 = data.data.post.contents_path1;

                if (urlM3u8 != '') {
                    urlM3u8 = 'https://video.candfans.jp' + urlM3u8;
                    console.log('m3u8:', urlM3u8)
                    var h1Elem = document.querySelector('h1')
                    var title = null
                    if (h1Elem) {
                        title = h1Elem.innerText;
                    } else {
                        title = location.href.remove('https://')
                    }

                    title = encodeURIComponent(sanitizeTitle(`${title} `))
                    console.log('@title:', title);

                    const videoElem = document.querySelector('video');
                    console.log('videoElem:', videoElem);

                    const thumbUrl = videoElem.getAttribute("poster");
                    console.log('thumbUrl:', thumbUrl);

                    let finalUrl = updateUrlParameter(urlM3u8, 'media_title', title);
                    if (thumbUrl.length > 0) {
                        finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbUrl);
                    }
                    console.log("@url:", finalUrl);

                    if (finalUrl != '') {
                        bridge.download(JSON.stringify({
                            url: finalUrl,
                            metadata: ''
                        }));
                    }

                }
            }
        )
        .catch(error => console.error('Error:', error));

}

function onClickDownloadMp4() {
    const videoElm = document.querySelector('video');
    const thumbUrl = videoElm.getAttribute('poster')
    console.log(thumbUrl)
    const videoUrl = videoElm.getAttribute('src')
    console.log('src:', videoUrl)

    // 获取标题
    const elem = document.querySelector('div.content-describe')

    var title;
    if (elem) {
        title = elem.innerText.split('\n')[0]
    } else {
        const elemReel = document.querySelector('h1')
        if (elemReel) {
            title = elemReel.innerText
        } else {
            title = location.href
        }

    }

    title = encodeURIComponent(sanitizeTitle(`${title}`))

    console.log("@title", title);
    console.log("video:", videoUrl, "thumUrl:", thumbUrl);

    var finalUrl = updateUrlParameter(videoUrl, 'itdl_title', title);

    finalUrl = updateUrlParameter(finalUrl, 'itdl_ext', 'mp4');
    finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbUrl);

    console.log("@url:", finalUrl);

    if (finalUrl != '') {
        bridge.download(JSON.stringify({
            url: finalUrl,
            metadata: ''
        }));
    }
}

function loadDlBtn() {
    var commonBtn = document.getElementById('itdl-btn');
    // const div = document.getElementsByClassName('slide swiper-slide swiper-slide-active');
    var slideArry = document.querySelectorAll('div[class="slide keen-slider__slide"]')
    // const playDiv = document.getElementsByClassName('video-player-component');   //收费播放组件
    const videoElm = document.querySelector('video');

    if (slideArry.length > 0) {
        if (!commonBtn) {
            createDlBtn(onClickDownload);
            var styleId = document.getElementById('itd_btn_style');
            if (styleId) {
                styleId.innerText = css_candfans;
            }

        }
    }
    else if (videoElm) {
        if (!commonBtn) {
            createDlBtn(onClickDownloadBuy);
            var styleId = document.getElementById('itd_btn_style');
            if (styleId) {
                styleId.innerText = css_candfans;
            }
        }
    }
    // else if(videoElm){
    //     if (!commonBtn) {
    //         createDlBtn(onClickDownloadMp4);
    //     }
    // }
    else {
        // 删除全局按钮
        commonBtn && commonBtn.remove();
    }
}
