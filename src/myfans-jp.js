async function __itl_init__() {
    // page: home, elements: div.swiper-slide.swiper-slide-visible.swiper-slide-active
    if (isAtHome()) {
        const firstSwiperContainer = document.querySelector('.swiper.swiper-initialized.swiper-horizontal')
        const firstSwiper = firstSwiperContainer.swiper;
        // recommendation | following container
        for (let i = 0; i < firstSwiper.slides.length; i++) {
            const swiperContainer = firstSwiper.slides[i].querySelector('.swiper.swiper-initialized.swiper-vertical.swiper-watch-progress')
            const swiper = swiperContainer.swiper;
            const isFollow = i !== 0;
            if (i === 0) {
                // 为了解决初次加载时第一个视频无法监听到资源
                swiper.slideNext()
                continue;
            }

            let apiData = await loadNewData(swiper, isFollow);
            loadDlButton(swiper, apiData)

            swiper.on('slideChangeTransitionEnd', () => loadDlButton(swiper, apiData))
            swiper.on('slidesLengthChange', async () => {
                const newData = await loadNewData(swiper, isFollow);
                apiData.push(...newData)
            })
        }

        async function loadNewData(swiper, isFollow = false) {
            // recommendation item
            if (!isFollow) {
                const streamExplorerApi = 'https://api.myfans.jp/api/v2/stream/explorer';
                return await sendRequest(streamExplorerApi, 'GET');
            }

            // following item
            const slidesLength = swiper.slides.length;
            const page = Math.floor(slidesLength / 20);
            console.log('page', page)
            const followApi = `https://api.myfans.jp/api/v2/stream/follow?page=${page}`;
            const data = await sendRequest(followApi, 'GET');
            return data?.data ? data.data : [];
        }
        function loadDlButton(swiper, apiData) {
            console.log('swiperContainer', swiper)
            const activeIndex = swiper.activeIndex;
            const slide = swiper.slides[activeIndex]
            console.log('clickedSlide', slide)

            const buttonContainer = slide.querySelector('.pointer-events-auto.absolute.right-0.z-10.flex.flex-col.items-center.gap-2.p-4');
            console.log('buttonContainer', buttonContainer)
            if (!buttonContainer) {
                return;
            }
            if (buttonContainer?.querySelector('.itdl-btn')) {
                return;
            }

            const videoEle = document?.querySelector('video');
            console.log(videoEle)
            if (!videoEle || videoEle.src === 'https://myfans.jp/movies/dummy.mp4') {
                console.log('this item is not video')
                return;
            }

            const downloadBtn = createDownloadButton();

            downloadBtn.addEventListener('click', () => {
                console.log('activeIndex', activeIndex)
                console.log('apiData', apiData)

                const item = apiData.length > activeIndex ? apiData[activeIndex] : null;
                const videos = item?.videos?.main ? item.videos.main : item?.videos?.trial;
                console.log('videos', videos)
                // 按 height 降序排序
                videos.sort((a, b) => b.height - a.height);

                const video = videos.find(item => item.height === 1080 || item.height === 780 || item.height === 720 || item.height === 640 || item.height === 480 || item.height === 360 || item.height === 240 || item)
                console.log('video', video)

                const mediaTitle = slide.querySelector('.noSwipingClass').innerText
                const url = updateUrlParameter(video.url, 'media_title', encodeURIComponent(sanitizeTitle(mediaTitle)))
                const json = JSON.stringify({url});
                console.log('json', json)
                // notify QT
                bridge.download(json);
            })
            console.log('downloadBtn', downloadBtn)
            buttonContainer.prepend(downloadBtn)
        }
    }

    // page: post
    const isAtPost = matchPost();
    if (isAtPost.matches) {
        const postId = isAtPost.id;
        const videosApi = `https://api.myfans.jp/api/v2/posts/${postId}/videos`;
        const apiData = await sendRequest(videosApi, 'GET');
        console.log('apiData', apiData)
        await sleep(0.5)

        let playerContainer = document.querySelector('.reel-player-contain');
        playerContainer = playerContainer ? playerContainer : document.querySelector('.reel-player-cover');

        if (!playerContainer) {
            console.log('undefined video container')
            return;
        }

        const container = playerContainer?.parentElement

        const buttonContainer = container.querySelector('.pointer-events-auto.absolute.right-0.z-10.flex.flex-col.items-center.gap-2.p-4');
        console.log('buttonContainer', buttonContainer)

        if (!buttonContainer) {
            console.log('undefined button container')
            return;
        }
        if (buttonContainer?.querySelector('.itdl-btn')) {
            console.log('itdl-btn is exists')
            return;
        }

        const downloadBtn = createDownloadButton();

        downloadBtn.addEventListener('click', () => {
            const videos = apiData?.main ? apiData.main : apiData?.trial;
            console.log('videos', videos)
            // 按 height 降序排序
            videos.sort((a, b) => b.height - a.height);

            const video = videos.find(item => item.height === 1080 || item.height === 780 || item.height === 720 || item.height === 640 || item.height === 480 || item.height === 360 || item.height === 240 || item )
            console.log('video', video)

            const mediaTitle = container.querySelector('.noSwipingClass').innerText

            const url = updateUrlParameter(video.url, 'media_title', encodeURIComponent(sanitizeTitle(mediaTitle)))
            const json = JSON.stringify({url});
            console.log('json', json);

            // notify QT
            bridge.download(json);
        })
        console.log('downloadBtn', downloadBtn)
        buttonContainer.prepend(downloadBtn)
    }
}

function sendRequest(url, method) {
    return new Promise((resolve, reject) => {
        var xhr = new XMLHttpRequest();
        xhr.open(method, url, true);

        xhr.setRequestHeader('Accept', 'application/json, text/plain, */*');
        xhr.setRequestHeader('Authorization', `Token token=${getCookie('_mfans_token')}`);
        xhr.setRequestHeader('Google-Ga-Data', 'event328');

        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(xhr.statusText));
            }
        };

        xhr.onerror = function() {
            reject(new Error('Network error'));
        };

        xhr.send();
    });
}

function isAtHome() {
    // 获取当前 URL 的路径部分
    const path = window.location.pathname;

    // 移除路径开头和结尾的斜杠（如果存在）
    const trimmedPath = path.startsWith('/') ? path.slice(1) : path;
    const normalizedPath = trimmedPath.endsWith('/') ? trimmedPath.slice(0, -1) : trimmedPath;

    // 将路径分割成部分
    const parts = normalizedPath.split('/');

    // 检查路径是否为 "/home" 或 "/[language]/home"
    if (parts.length === 1 && parts[0] === 'home') {
        // 情况 1: 直接是 "/home"
        return true;
    }
    return parts.length === 2 && parts[1] === 'home';
}

function matchPost() {
    const regex = /^\/(?:[a-z]{2}(?:-[A-Z]{2})?\/)?posts\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/;
    const currentURL = window.location.pathname;
    const match = currentURL.match(regex);

    return match ? {matches: true, id: match[1]} : {matches: false, id: null};
}

function createDownloadButton() {
    // 删除全局按钮
    const commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    const downloadBtn = document.createElement('button');
    downloadBtn.classList.add('MuiButtonBase-root', 'MuiIconButton-root', 'MuiIconButton-colorWhite', 'MuiIconButton-sizeMedium', 'css-3vsei4', 'itdl-btn')
    downloadBtn.setAttribute('tabindex', 0)
    downloadBtn.setAttribute('type', 'button')
    downloadBtn.innerHTML = '<img class="w-7 h-7 inline-block" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAYAAAByDd+UAAAAAXNSR0IArs4c6QAAAERlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAHKADAAQAAAABAAAAHAAAAABkvfSiAAACx0lEQVRIDb2WPWhTURTH//fm5aOtVsRBqCBKIxHEIWKlDmpFFAQRoboURVBbh05OLg4O4iQuTrYOIiiCCg4WBV2KiBGHrhZTHLQWh6Kg+TLJuz3nNu/lvWeT3OQFDyT343z8cm7uxxEwkNy9ZBo2TgmoAzawRQAD7KaA7xJYVBBvIfG871J2rlU48m0s+enkadjqhhJINbaqa4TCPKS41juefVqf9ffWBBamU9ttVXlEpsN+c+NRRgprrGd8/kvQ4x9gYSp5yBbqGa3XpqBxW2OBZanEaM9Edtbr5wNqGNRrMoh6jUL0yxLiqBfqAvUyovIxdGbBX8eZwhpylpc22aro/yzsMjrBvC3FrO0HPauBeje2s0FkBOCPuQzXGHR6WGjrm/sC8eP39acdH4dh8aFWtjI6Zw5A9m91usYtn2VmSb5BjL3CGhJL8nUVNo6pP7Mk342mDmHtmEUZrl7EjYJZu85Bbt7TSO3OW8mTiAw0vwmZ5Z5D19PbsRKI7buKxImHiGw75tX4+tH0JGKHb8PafcE3HxwQUEl+YoIKd1wpovRmko5NFfEjd8BZBIVh0b1XoH5/w99314Nq35iWdElSiou+2cCg+nUWpVcXgWoJsZFbsFJnXAsvrPhiDOpP49/OTsyiDOnxbCHVpQ8ovjwPVc4hdvAmXe3rgNh6NzMTGCOYJfmlbsHTavvHHEozZ6GKvyDiGyBi/XoZTWE6CLHofwTydwc/mb7qcuMOJEZntH/h8UjLZdSG9MXVQO/lhZ2WnqCyAEo9cZTNWvvnZ+QfpGl9aAuUC81M/TpmkOgMuZObGnxPTfODxIadSaZvYmE/u7rnkGsQwi93Fq+JFz/AHLsmLpBfZK5BaL7sKLvQlnVd4ymmXCAH59qDa5CuZKpLC389wwwfsA61hqif4XGHktF1TKBi41juplkr8H8rhIPwbpb6Ky/T/aQW0AMwAAAAAElFTkSuQmCC"/>';

    return downloadBtn;
}

// 对于XMLHttpRequest
const originalSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.send = function(...args) {
    this.addEventListener('load', () => {
        // console.log('XHR请求完成', this);
        // 这里可以记录请求信息
        if (isValidURL(this.responseURL) && isAtHome()) {
            console.log('url', this.responseURL)

            const firstSwiperContainer = document.querySelector('.swiper.swiper-initialized.swiper-horizontal')
            const firsSwActiveIndex = firstSwiperContainer.swiper.activeIndex;
            const recommendationSlide = firstSwiperContainer.swiper.slides[firsSwActiveIndex]
            const swiperContainer = recommendationSlide.querySelector('.swiper.swiper-initialized.swiper-vertical.swiper-watch-progress')

            const swiper = swiperContainer.swiper;

            const activeIndex = swiper.activeIndex;
            const slide = swiper.slides[activeIndex]
            console.log('clickedSlide', slide)

            const buttonContainer = slide.querySelector('.pointer-events-auto.absolute.right-0.z-10.flex.flex-col.items-center.gap-2.p-4');
            console.log('buttonContainer', buttonContainer)
            if (!buttonContainer) {
                return;
            }
            if (buttonContainer?.querySelector('.itdl-btn')) {
                return;
            }

            const videoEle = document.querySelector('video');
            console.log(videoEle)
            if (!videoEle || videoEle.src === 'https://myfans.jp/movies/dummy.mp4') {
                console.log('this item is not video')
                return;
            }

            const downloadBtn = createDownloadButton();

            downloadBtn.addEventListener('click', () => {
                // notify QT
                console.log('video', this.responseURL)
                const mediaTitle = slide.querySelector('.noSwipingClass').innerText
                const url = updateUrlParameter(this.responseURL, 'media_title', encodeURIComponent(sanitizeTitle(mediaTitle)))
                const json = JSON.stringify({url});
                console.log('json', json)

                bridge.download(json);
            })

            console.log('downloadBtn', downloadBtn)

            buttonContainer.prepend(downloadBtn)

        }
    });
    originalSend.apply(this, args);
};

function isValidURL(str) {
    const regex = /^https:\/\/content\.mfcdn\.jp\/videos\/processed\/hls\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.m3u8$/;
    return regex.test(str);
}

function triggerCustomEvent() {
    var event = new CustomEvent('urlChange', {detail: {href: window.location.href}});
    window.dispatchEvent(event);
}

// 拦截pushState和replaceState以触发自定义事件
(function(history){
    var pushState = history.pushState;
    var replaceState = history.replaceState;

    history.pushState = function(state) {
        pushState.apply(history, arguments);
        triggerCustomEvent(); // 调用自定义事件
    };

    history.replaceState = function(state) {
        replaceState.apply(history, arguments);
        triggerCustomEvent(); // 调用自定义事件
    };
})(window.history);

// 监听自定义事件
window.addEventListener('urlChange', function(event) {
    console.log('URL改变了:', event.detail.href);
    __itl_init__()
});

function waitForElementToDisappear(selector) {
    return new Promise((resolve, reject) => {
        // 检查元素是否已经不在页面上
        if (!document.querySelector(selector)) {
            resolve();
            return;
        }

        // 创建一个观察器实例并传入回调函数
        const observer = new MutationObserver((mutations, obs) => {
            if (!document.querySelector(selector)) {
                // 停止观察
                obs.disconnect();
                // 元素已消失，完成 Promise
                resolve();
            }
        });

        // 配置观察器选项：子树和属性变化
        const config = { childList: true, subtree: true };

        // 开始观察整个文档
        observer.observe(document.body, config);
    });
}

// 首先等待带有 'is18' 类的元素消失
waitForElementToDisappear('.flex.h-full.animate-fade-in-bottom.flex-col.items-center.justify-center.p-5.opacity-0').then(() => {
    console.log('18 tips is gone, waiting for progress');
    // 然后等待带有 'MuiCircularProgress-root' 类的元素消失
    return waitForElementToDisappear('.MuiCircularProgress-root');
}).then(() => {
    console.log('Progress is gone, itl begin init');
    __itl_init__()
});