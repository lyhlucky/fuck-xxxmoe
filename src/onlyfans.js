setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    createStyle();
    loadDlBtn();

    setInterval(function () {
        loadDlBtn();
    }, 1000);
}, 1000);

function loadDlBtn() {
    // 删除全局按钮
    const commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    var login_content = document.getElementsByClassName("login_content");
    if(login_content.length != 0) {
        return;
    }

    const isChat = location.href.indexOf('/my/chats/chat/') !== -1;

    if (isChat) {
        messagesWrapper = document.querySelector('div.b-chat__messages-wrapper');
        if (messagesWrapper) {
            messagesMediaWrapperList = messagesWrapper.querySelectorAll('div.b-chat__message__media-wrapper');
            messagesMediaWrapperList.forEach(function (messageItem) {
                messageItem.querySelectorAll('div.b-post__media__item-inner').forEach(function (mediaItem) {
                    var video = mediaItem.querySelector('video');
                    var img = mediaItem.querySelector('img');
                    if (video || img)  {
                        var oldBtn = mediaItem.querySelector('.itdl-btn');
                        if (!oldBtn) {
                            createDownloadButton(mediaItem);
                        }
                    }
                });

                messageItem.querySelectorAll('div.video-wrapper').forEach(function (videoWrapperItem) {
                    var oldBtn = videoWrapperItem.querySelector('.itdl-btn');
                    if (!oldBtn) {
                        createDownloadButton(videoWrapperItem);
                    }
                });
            });
            return;
        }
    } else {
        postWrapper = document.querySelector('div.vue-recycle-scroller__item-wrapper');
        if (postWrapper) {
            postViewList = postWrapper.querySelectorAll('div.vue-recycle-scroller__item-view');
            postViewList.forEach(function (postItem) {
                postItem.querySelectorAll('div.b-post__media__item-inner').forEach(function (mediaItem) {
                    var video = mediaItem.querySelector('video');
                    var img = mediaItem.querySelector('img');
                    if (video || img) {
                        var oldBtn = mediaItem.querySelector('.itdl-btn');
                        if (!oldBtn) {
                            createDownloadButton(mediaItem);
                        }
                    }
                });

                postItem.querySelectorAll('div.video-wrapper').forEach(function (videoWrapperItem) {
                    var oldBtn = videoWrapperItem.querySelector('.itdl-btn');
                    if (!oldBtn) {
                        createDownloadButton(videoWrapperItem);
                    }
                });
            })
            return;
        }
    }

    document.querySelectorAll('.video-wrapper').forEach(function (item, index, list) {
        var oldBtn = item.querySelector('.itdl-btn');
        if (!oldBtn) {
            createDownloadButton(item);
        }
    });

    // 包含多个视频和图片
    document.querySelectorAll('.swiper-slide').forEach(function (item, index, list) {
        var video = item.querySelector('video');
        var img = item.querySelector('img');

        if (video || img) {
            if ((video && video.closest('.b-recommended')) || (img && img.closest('.b-recommended'))) {
                console.log("skip recommended list");
                return;        
            }

            var oldBtn = item.querySelector('.itdl-btn');
            if (!oldBtn) {
                createDownloadButton(item);
            }
        }
    });

    document.querySelectorAll('div.post_media').forEach(function (item, index, list) {
        var video = item.querySelector('video');
        var img = item.querySelector('img');

        if (video || img) {
            var oldBtn = item.querySelector('.itdl-btn');
            if (!oldBtn) {
                createDownloadButton(item);
            }
        }
    });
}

function createDownloadButton(container) {
    const itdlBtn = document.createElement('button');
    itdlBtn.innerHTML = ITL_BUTTON;
    itdlBtn.classList.add('itdl-btn');

    // 重试次数
    const maxRetries = 10;

    const download = () => {
        let retryCount = 0; // 初始化重试次数
        let hasPlay = false;

        const attemptDownload = () => {
            var interval = 1;
            const playBtn = container.querySelector('.vjs-big-play-button');
            if (playBtn) {
                hasPlay = true;
                playBtn.click();
                interval = 1200;
            }
    
            setTimeout(async () => {
                const isChat = location.href.indexOf('/my/chats/chat/') !== -1;

                // 获取标题
                let title = '';
                let titleWrapper = null;
                if (isChat) {
                    const messageBody = container.closest('.b-chat__message__body');
                    if (messageBody) {
                        titleWrapper = messageBody.querySelector('div.b-chat__message__text-wrapper');
                    }
                } else {
                    const postWrapper = container.closest('.b-post__wrapper');
                    if (!postWrapper) {
                        postWrapper = container.closest('.b-post__text')
                    }
                    if (postWrapper) {
                        titleWrapper = postWrapper.querySelector('div.g-truncated-text');
                    }                    
                }
    
                if (titleWrapper && titleWrapper.hasChildNodes()) {
                    const elements = titleWrapper.childNodes;
                    elements.forEach(function(node) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            title += node.textContent + ' ';
                        } else if (node.nodeType === Node.TEXT_NODE) {
                            title += node.nodeValue + ' ';
                        }
                    });
                    title = title.trim();
                }
    
                if (title.length === 0) {
                    title = document.title + "-" + new Date().getTime();
                }
                console.log('@title:', title);

                const videoItem = container.querySelector('video');
                
                if (!hasPlay && !videoItem) { //下载图片
                    const imgItem = container.querySelector('img');
                    if (imgItem) {
                        console.log("this is a photo");
                        const imgUrl = imgItem?.src;
                        if (imgUrl) {
                            console.log("ready download photo...");
                            bridge.download(JSON.stringify({
                                url: imgUrl,
                                metadata: Base64.encode(JSON.stringify({
                                    'title': encodeURIComponent(sanitizeTitle(title)),
                                    'type':'photo',
                                    'thumbnail': ''
                                }))
                            }));
                            return;              
                        }
                    }
                }   

                // 如果视频没有加载或不存在，尝试重试
                if (!videoItem && retryCount < maxRetries) {
                    console.log(`Retrying... Attempt ${retryCount + 1}`);
                    retryCount++;
                    attemptDownload();
                    return;
                }

                console.log("this is a video");
                // 获取视频缩略图URL
                let thumbnailUrl = videoItem?.hasAttribute('poster') ? videoItem.poster : '';
                console.log('@thumbnailUrl:', thumbnailUrl);
    
                if (videoItem.src.startsWith('blob:') || videoItem.src.indexOf('.m3u8') !== -1) { // 被加密的视频
                    const arr = videoItem.id.split('_')[0].split('-');
                    const videoId = arr[1];
                    const postId = arr[2];
                    console.log('@videoId:', videoId);
                    console.log('@postId:', postId);
                    var isPaid = false;
    
                    if (location.pathname === '/' || location.pathname === '/search') {
                        const tabsNav = document.querySelector('div.m-single-current');
    
                        if (tabsNav) {
                            tabsNav.querySelectorAll('li.b-tabs__nav__item').forEach(function (item, index) {
                                console.log("@tabItem", item);
                                if (index == 1) {
                                    const classList = item.querySelector('button.b-tabs__nav__link').classList;
                                    if (classList) {
                                        classList.forEach(function (className) {
                                            if (className === 'm-current') {
                                                console.log("@已购买");
                                                isPaid = true;
                                            }
                                        });
                                    }
                                }
                            });
                        }
                    }
    
                    console.log("ready download drm video...");
                    bridge.download(JSON.stringify({
                        url: location.href,
                        metadata: Base64.encode(JSON.stringify({
                            'type': 'video',
                            'title': encodeURIComponent(sanitizeTitle(title)),
                            'thumbnail': thumbnailUrl,
                            'post_id': postId,
                            'video_id': videoId,
                            'user-agent': navigator.userAgent,
                            'is_chat': isChat,
                            'is_paid': isPaid
                        }))
                    }));
                } else {
                    // 获取视频下载URL
                    const videoSources = videoItem.querySelectorAll('source');
                    const videoUrl = videoSources[videoSources.length - 1].src;
                    console.log('@videoUrl:', videoUrl);
                    // 给下载URL添加参数
                    var finalUrl = updateUrlParameter(videoUrl, 'itdl_title', encodeURIComponent(sanitizeTitle(title)));
                    finalUrl = updateUrlParameter(finalUrl, 'itdl_ext', 'mp4');
                    if (thumbnailUrl.length > 0) {
                        finalUrl = updateUrlParameter(finalUrl, 'itdl_thumbnail', thumbnailUrl);
                    }
                    console.log('@finalUrl:', finalUrl);
    
                    bridge.download(JSON.stringify({
                        url: finalUrl,
                        metadata: '',
                    }));
                }
            }, interval);
        }

        attemptDownload();  // 初次尝试下载
    }
    itdlBtn.onclick = debounce(download, 500);

    container.appendChild(itdlBtn);
}