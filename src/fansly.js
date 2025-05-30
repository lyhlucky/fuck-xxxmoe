setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    createStyle();
    loadDlBtn();

    setInterval(function () {
        loadDlBtn();
    }, 1000)
}, 1000)

// 点击事件处理函数
function handleDescriptionItemClick(event) {
    console.log("@handleDescriptionItemClick");
    setTimeout(download, 1200, event.target.metadata);
}

function download(metadata) {
    if (!metadata) {
        console.log("@metadata is null")
        return;
    }

    var result;
    var title = metadata.title;
    if (title.length === 0) {
        title = document.title + "_" + new Date().getTime();
    }

    if (metadata.videoNode && metadata.videoNode.getAttribute('src') && !metadata.videoNode.src.startsWith("blob:") && !metadata.videoNode.src.includes("m3u8")) {
        result = {
            url: metadata.videoNode.src + '&itdl_ext=mp4' + '&itdl_title=' + encodeURIComponent(sanitizeTitle(title)),
            metadata: Base64.encode(JSON.stringify({
                http_headers: {
                    Referer: metadata.videoNode.src
                }
            }))
        }
    } else {
        let userName = "";
        if (location.pathname.split('/')[1] === 'home') {
            const userNameEle = metadata.videoFeedNode.querySelector("span.user-name");
            if (userNameEle) {
                userName = userNameEle.innerText.split(" ")[0].slice(1);
            }
        }

        result = {
            url: location.href,
            metadata: Base64.encode(JSON.stringify({
                http_headers: {
                    Referer: location.href,
                    authorization: JSON.parse(localStorage.getItem('session_active_session')).token,
                    cookie: document.cookie
                },
                media_info: {
                    user_name: userName,
                    title: encodeURIComponent(sanitizeTitle(title)),
                    video_index: metadata.videoIndex,
                    message_index: metadata.messageIndex,
                    limit: metadata.messageCount,
                }
            }))
        }
    }
    console.log('result', result);
    bridge.download(JSON.stringify(result));
}

function createDownloadBtn(metadata) {
    var itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');
    var videoWrap = metadata.videoNode.closest('.video-element-wrap');
    const repeatBtn = videoWrap.querySelector('div.video-footer div.repeat');
    if (!repeatBtn) {
        console.log('[itdl] undefined repeat button');
        return;
    }
    repeatBtn.after(itdlBtn);
    itdlBtn.metadata = metadata;

    itdlBtn.onclick = function (event) {
        var metadata = event.target.metadata;
        console.log("@onclick metadata:", metadata);
        if (metadata.isMessage) {
            const messageTextTag = metadata.videoFeedNode.querySelector(".message-text");
            if (messageTextTag) {
                metadata.title = messageTextTag.innerText;
            }
            download(metadata);
        } else {
            var descriptionItem = metadata.videoFeedNode.querySelector(".feed-item-description");
            console.log("@descriptionItem", descriptionItem);
            if (descriptionItem) {
                metadata.title = descriptionItem.innerText;
                var pathNames = location.pathname.split('/');

                if (pathNames.includes('home') || pathNames.includes('posts')) {
                    descriptionItem.metadata = metadata;
                    descriptionItem.addEventListener('click', handleDescriptionItemClick);
                    descriptionItem.click();
                    descriptionItem.removeEventListener('click', handleDescriptionItemClick);
                } else {
                    download(metadata);
                }
            } else {
               // Bundle
               const backDrop = document.querySelector('.back-drop');
               if (backDrop) {
                   backDrop.click();
                   setTimeout(function (metadata) {
                       const descriptionItem = metadata.videoFeedNode.querySelector(".feed-item-description");
                       if (descriptionItem) {
                           metadata.title = descriptionItem.innerText;
                           var pathNames = location.pathname.split('/');

                           if (pathNames.includes('home') || pathNames.includes('posts')) {
                                descriptionItem.metadata = metadata;
                                descriptionItem.addEventListener('click', handleDescriptionItemClick);
                                descriptionItem.click();
                                descriptionItem.removeEventListener('click', handleDescriptionItemClick);
                                return;
                           }
                       }
                   }, 1200, metadata);
               }
            }
        }
    }
}

function loadDlBtn() {
    let videoItems;
    let isMessage = false;
    let bundleIndex = -1;

    if (location.pathname.indexOf("/messages/") !== -1) {
        videoItems = document.querySelectorAll('.messages-content-wrapper .message-collection');
        isMessage = true;
    } else {
        if (location.pathname.split('/')[1] === 'home') {
            videoItems = document.querySelectorAll('.feed-content .feed-item');
        } else if (location.pathname.indexOf("/post/") !== -1) {
            const activeModal = document.querySelector('app-media-browser-modal.active-modal');
            let hasBundle = false;
            if (activeModal) {
                videoItems = activeModal.querySelectorAll('.media-slider .media-wrapper');
                const mediaGalleryItems = activeModal.querySelectorAll('.media-gallery-item');
                if (mediaGalleryItems.length > 0) {
                    mediaGalleryItems.forEach(function (item, index) {
                        const appAccountMedia = item.getElementsByTagName('app-account-media')[0];
                        const className = appAccountMedia.getAttribute('class');
                        if (className === 'view-content') { // 当前选中
                            bundleIndex = index;
                        }
                    })
                    hasBundle = true;
                }
            }

            if (!hasBundle) {
                videoItems = document.querySelectorAll('.post-content-wrapper .feed-item');
            }
        } else {
            videoItems = document.querySelectorAll('.profile-content-wrapper .feed-item');
        }
    }

    videoItems.forEach(function (item, index) {
        if (isMessage) {
            var mediaList1 = item.querySelectorAll('app-account-media.feed-item-preview-media');
            var mediaList2 = item.querySelectorAll('.message-attachment');
            findVideo(mediaList1, item, isMessage, index, videoItems.length, bundleIndex);
            findVideo(mediaList2, item, isMessage, index, videoItems.length, bundleIndex);
        } else {
            var mediaList1 = item.querySelectorAll('app-account-media.feed-item-preview-media');
            var mediaList2 = item.querySelectorAll('app-post-attachment.feed-item-preview-media');
            var mediaList3 = item.querySelectorAll('app-account-media.feed-item-media');
            var mediaList4 = item.querySelectorAll('app-post-attachment.feed-item-media');
            var mediaList5 = item.querySelectorAll('app-account-media-bundle-gallery.view-content');
            findVideo(mediaList1, item, isMessage, index, videoItems.length, bundleIndex);
            findVideo(mediaList2, item, isMessage, index, videoItems.length, bundleIndex);
            findVideo(mediaList3, item, isMessage, index, videoItems.length, bundleIndex);
            findVideo(mediaList4, item, isMessage, index, videoItems.length, bundleIndex);
            findVideo(mediaList5, item, isMessage, index, videoItems.length, bundleIndex);
        }
    })
}

function findVideo(mediaList, videoFeedNode, isMessage, messageIndex, messageCount, bundleIndex) {
    let videoCount = 0;

    for (var i = 0; i < mediaList.length; i++) {
        const media = mediaList[i];
        var videos = media.getElementsByTagName('video');
        if (videos.length > 0) {
            videoCount++;
            const videoIndex = bundleIndex > -1 ? bundleIndex : i;
            var videoItem = videos[0];
            var videoWrap = videoItem.closest('.video-element-wrap');
            var oldBtn = videoWrap.querySelector('.itdl-btn');
            if (!oldBtn) {
                var metadata = {
                    videoNode: videoItem,
                    videoIndex: videoIndex,
                    videoFeedNode: videoFeedNode,
                    isMessage: isMessage,
                    messageIndex: messageIndex,
                    messageCount: messageCount,
                    title: ''
                }
                createDownloadBtn(metadata);
            }
        }
    }

    if ((location.pathname.indexOf("/post/") === -1) && videoCount === 0 && mediaList.length > 1) {
        const feedItemPreview = videoFeedNode.querySelector('.feed-item-preview');
        if (feedItemPreview) {
            var oldItdlBtn = feedItemPreview.querySelector('.itdl-btn');
            if (!oldItdlBtn) {
                var itdlBtn = document.createElement('button');
                itdlBtn.innerHTML = ITL_BUTTON;
                itdlBtn.classList.add('itdl-btn');
                itdlBtn.onclick = function (event) {
                    var descriptionItem = videoFeedNode.querySelector(".feed-item-description")
                    if (descriptionItem) {
                        var pathNames = location.pathname.split('/');

                        if (pathNames.includes('home') || pathNames.includes('posts')) {
                            descriptionItem.metadata = null;
                            descriptionItem.addEventListener('click', handleDescriptionItemClick);
                            descriptionItem.click();
                            descriptionItem.removeEventListener('click', handleDescriptionItemClick);
                        }
                    }
                }

                feedItemPreview.appendChild(itdlBtn);
            }
        }
    }
}

function createStyle() {
    if (!document.getElementById('itubego_style')) {
        var css = `
            .itdl-btn {
                position: absolute;
                top: 1em;
                left: 15em;
                z-index: 99999;
                font-size: .875em;
                font-weight: 100;
                padding: 0.5rem .75rem;
                cursor: pointer;
                background: #00CF2E;
                color: white;
                border-radius: 1rem;
                border: none;
                box-shadow: 0 1rem 2rem 0 rgba(0, 0, 0, 0.2), 0 2rem 4rem 0 rgba(0, 0, 0, 0.19);
            }
            .itdl-btn:hover{ background-color: #00A625 }
            .itdl-btn:focus{ outline: none; }

            .itdl-btn > img {
                width: 1.5em !important;
                height: 1.5em !important;
                vertical-align: middle !important;
            }
        `;
        var style = document.createElement('style');
        style.id = 'itubego_style';

        if (style.styleSheet) {
            style.styleSheet.cssText = css;
        } else {
            style.appendChild(document.createTextNode(css));
        }
        document.getElementsByTagName('head')[0].appendChild(style);
    }
}
