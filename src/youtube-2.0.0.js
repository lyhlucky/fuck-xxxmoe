var dragImgBs64 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAYAAAAYCAYAAADZEIyjAAAAAXNSR0IArs4c6QAAACBJREFUKFNj/P///38GBgYGRkZGRhAN549KjAYJ+YkBADuiv7nan665AAAAAElFTkSuQmCC';
var DRAG_BUTTON = document.createElement('img');
DRAG_BUTTON.src = dragImgBs64;

function parseQuery(queryString) {
    if (!queryString) {
        return {};
    }

    var query = {};
    var pairs = (queryString[0] === '?' ? queryString.substr(1) : queryString).split('&');
    for (var i = 0; i < pairs.length; i++) {
        var pair = pairs[i].split('=');
        query[decodeURIComponent(pair[0])] = decodeURIComponent(pair[1] || '');
    }
    return query;
}

var escapeRegExp = function (s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

var parseDecsig = function (data) {
    try {
        if (data.startsWith('var script')) {
            // they inject the script via script tag
            var obj = {}
            var document = {
                createElement: () => obj,
                head: { appendChild: () => { } }
            }
            eval(data)
            data = obj.innerHTML
        }
        var fnnameresult = /=([a-zA-Z0-9\$]+?)\(decodeURIComponent/.exec(
            data
        )
        var fnname = fnnameresult[1]
        var _argnamefnbodyresult = new RegExp(
            escapeRegExp(fnname) + '=function\\((.+?)\\){(.+?)}'
        ).exec(data)
        var [_, argname, fnbody] = _argnamefnbodyresult
        var helpernameresult = /;(.+?)\..+?\(/.exec(fnbody)
        var helpername = helpernameresult[1]
        var helperresult = new RegExp(
            'var ' + escapeRegExp(helpername) + '={[\\s\\S]+?};'
        ).exec(data)
        var helper = helperresult[0]
        console.log(
            `parsedecsig result: %s=>{%s\n%s}`,
            argname,
            helper,
            fnbody
        )
        return new Function([argname], helper + '\n' + fnbody)
    } catch (e) {
        console.error('parsedecsig error: %o', e)
        console.info('script content: %s', data)
        console.info(
            'If you encounter this error, please copy the full "script content" to https://pastebin.com/ for me.'
        )
    }
}

var getVideo = async (id, decsig) => {
    var resp = await fetch(`https://www.youtube.com/get_video_info?video_id=${id}&el=detailpage`)
    var data = await resp.text()

    if (!data) return 'Adblock conflict'
    var obj = parseQuery(data)
    var playerResponse = JSON.parse(obj.player_response)
    console.log(`video %s data: %o`, id, obj)
    console.log(`video %s playerResponse: %o`, id, playerResponse)
    if (obj.status === 'fail') {
        throw obj
    }

    if (playerResponse.streamingData && (playerResponse.streamingData.formats || playerResponse.streamingData.adaptiveFormats)) {

    } else {
        playerResponse = JSON.parse(ytplayer.config.args.player_response);
    }

    var stream = []
    if (playerResponse.streamingData.formats) {
        stream = playerResponse.streamingData.formats.map(x =>
            Object.assign({}, x, parseQuery(x.cipher || x.signatureCipher))
        )
        console.log('video %s stream: %o', id, stream)
        if (stream[0].sp && stream[0].sp.includes('sig')) {
            for (var obj of stream) {
                obj.s = decsig(obj.s)
                obj.url += '&sig=' + obj.s;
            }
        }
    }

    var adaptive = []
    if (playerResponse.streamingData.adaptiveFormats) {
        adaptive = playerResponse.streamingData.adaptiveFormats.map(x =>
            Object.assign({}, x, parseQuery(x.cipher || x.signatureCipher))
        )
        console.log('video %s adaptive: %o', id, adaptive)
        if (adaptive[0].sp && adaptive[0].sp.includes('sig')) {
            for (var obj of adaptive) {
                obj.s = decsig(obj.s)
                obj.url += '&sig=' + obj.s
            }
        }
    }
    console.log(`video %s result: %o`, id, { stream, adaptive })
    return { stream, adaptive, title: playerResponse.videoDetails.title.split('+').join(' '), thumbnail: playerResponse.videoDetails.thumbnail.thumbnails[0] }
}

var metadata = {};

var load = async id => {
    try {
        var basejs =
            typeof ytplayer !== 'undefined' && ytplayer.config && ytplayer.config.assets
                ? 'https://' + location.host + ytplayer.config.assets.js
                : document.querySelector('script[src$="base.js"]').src

        var resp = await fetch(basejs)
        var text = await resp.text()

        var decsig = parseDecsig(text);

        metadata = await getVideo(id, decsig)

        console.log('@metadata---start')
        console.log(JSON.stringify(metadata))
        console.log('@metadata---end')


        var result = {
            url: location.href,
            metadata: Base64.encode(JSON.stringify(metadata)),
        };

        console.log('@result---start')
        console.log(JSON.stringify(result))
        console.log('@result---end')

        // if exits, remove
        var dlBtn = document.getElementById('itdl-btn');
        if (dlBtn) {
            dlBtn.remove();
        }

        createDlBtn(function () {
            console.log(result);
            bridge.download(JSON.stringify(result));
        });
    } catch (err) {
        console.error(err);

        var dlBtn = document.getElementById('itdl-btn');
        if (dlBtn) {
            dlBtn.remove();
        }

        createDlBtn(function () {
            bridge.download(JSON.stringify({ 'url': location.href, 'metadata': '' }));
        });
    }
}

// load download url
var prev = null
var interval = setInterval(() => {
    if (location.href !== prev) {
        prev = location.href
        if (location.pathname === '/watch') {
            var id = parseQuery(location.search).v;
            load(id);
        } else {
            // if exits, remove
            var dlBtn = document.getElementById('itdl-btn');
            if (dlBtn) {
                dlBtn.remove();
            }

            var simpleDlBtn = document.getElementById('simple-itdl-btn');
            if (!simpleDlBtn) {
                createDlBtn(function () {
                    console.log('common handler');
                    bridge.download(JSON.stringify({ 'url': location.href, 'metadata': '' }));
                });
            }
        }
    }
}, 100);

// add button to videos
function addDownloadBtn() {
    function addBtns(eles, style) {
        for (var i = 0; i < eles.length; ++i) {
            var ele = eles[i];
            var isPlayPage = false;
            if (window.location.href.indexOf('?v=') != -1) {
                isPlayPage = true;
            }

            if (isPlayPage) {
                break;
            }

            if (ele.innerHTML.indexOf('simple-itdl-btn') == -1) {
                var button = document.createElement('button');
                button.id = 'simple-itdl-btn';
                button.innerText = 'Download';
                button.setAttribute('style', style);
                button.onclick = function (e) {
                    var parentSubs = e.target.parentElement.getElementsByTagName('a');
                    for (var i = 0; i < parentSubs.length; ++i) {
                        var value = parentSubs[i].getAttribute('href');

                        if (value && (value.indexOf('/watch?v=') !== -1 || value.indexOf('/shorts/') !== -1)) {
                            console.log({ 'url': 'https://www.youtube.com' + value, 'metadata': '' });
                            bridge.download(JSON.stringify({ 'url': 'https://www.youtube.com' + value, 'metadata': '' }));
                            break;
                        }
                    }
                }

                ele.appendChild(button);
            }
        }
    }

    var videoEles = document.getElementsByTagName('ytd-rich-item-renderer');
    addBtns(videoEles, 'position: relative; cursor: pointer; border:0px; font-size: 15px; bottom: 15px; left: 50%; transform: translateX(-50%); display: block; padding: 6px; border-radius: 5px; background: #00CF2E; color: #fff;');

    var searchEles = document.getElementsByTagName('ytd-video-renderer');
    addBtns(searchEles, 'position: relative; cursor: pointer; border:0px;f ont-size: 15px; bottom: 10px left: 50%; transform: translateX(-50%); display: block; padding: 6px; border-radius: 5px; background: #00CF2E; color: #fff;');
}

document.onscroll = addDownloadBtn;

window.scroll(0, 20);
window.scroll(0, -20);

// editor
function setEditorStyle() {
    var css = `

    #editor-wrapper {
        height: 28px;
        background: #333333;
        border-radius: 4px;
        z-index: 40;
        margin: 0 0 10px 0;
        position: relative
    }

    #editor-container {
        height: 20px;
        background: #566EFF;
        border-radius: 4px;
        z-index: 50;
        margin: 30px 0 10px 0;
        position: relative;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }

    #start-padding {
        position: absolute;
        width: 0;
        background: #333333;
        height: 100%;
    }

    #start-time {
        position: absolute;
        top: -23px;
        left: 0px;
        padding: 1px;
        -webkit-user-select: none;
        user-select: none;
        cursor: pointer;
        font-size: 12px;
    }

    #start-btn {
        width: 10px;
        background: #333333;
        height: 100%;
        display: inline-block;
        position: absolute;
        left: 0px;
        cursor: pointer;
    }

    #start-btn img {
        width: 4px;
        height: 12px;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }

    #end-time {
        position: absolute;
        top: -23px;
        padding: 1px;
        -webkit-user-select: none;
        user-select: none;
        cursor: pointer;
        font-size: 12px;
    }

    #end-btn {
        width: 10px;
        background: #333333;
        height: 100%;
        display: inline-block;
        position: absolute;
        cursor: pointer;
        right: 0px;
    }

    #end-btn img {
        width: 4px;
        height: 12px;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }

    #end-padding {
        position: absolute;
        right: 0;
        background: #333333;
        height: 100%;
    }

    #dl-seg-btn {
        margin: 0px auto;
        margin-bottom: 15px;
        background: #566EFF;
        color: white;
        padding: 8px 5px;
        border-radius: 4px;
        cursor: pointer;
        width: 56px;
        text-align: center;
        box-shadow: 0 1px 1px 0 rgba(0, 0, 0, 0.2), 0 4px 10px 0 rgba(0, 0, 0, 0.19);;
        -webkit-user-select: none;
        user-select: none;
        font-size: 14px;
    }
    #dl-seg-btn:hover{ background-color: #4A63FF }
    #dl-seg-btn:focus{ outline: none; }
    `;
    if (!document.getElementById('itubego_style')) {
        var style = document.createElement('style');
        style.id = 'itubego_style'

        if (style.styleSheet) {
            style.styleSheet.cssText = css;
        } else {
            style.appendChild(document.createTextNode(css));
        }
        document.getElementsByTagName('head')[0].appendChild(style);
    }

}

function hmsToSecond(hms) {
    var a = hms.split(':');


    var second = 0;
    if (a.length == 3) {
        second = (+a[0]) * 60 * 60 + (+a[1]) * 60 + (+a[2]);
    }
    if (a.length == 2) {
        second = (+a[0]) * 60 + (+a[1]);
    }

    return second;
}

function secondToHMS(second) {
    var hms = new Date(second * 1000).toISOString().substr(11, 8);

    var hmsArr = hms.split(':');
    if (hmsArr.length == 3 && hmsArr[0] == '00') {
        return hmsArr[1] + ':' + hmsArr[2];
    }

    return hms;
}

function initSegmentEditor() {
    setEditorStyle();

    var video = document.getElementsByTagName('video')[0];
    var duration = 100;
    if (video) {
        duration = video?.duration ? video.duration : 0;
        // console.log('duration', duration)
    }

    var infoContentEle = document.querySelector('ytd-app div#content div#primary div#above-the-fold');
    if (!infoContentEle) {
        infoContentEle = document.querySelector('ytd-app div#content div#primary div#info-contents');
    }
    // console.log('@info content ele', infoContentEle)

    var editorWrapper = document.getElementById('editor-wrapper');
    if (!editorWrapper) {
        var editorWrapper = document.createElement('div');
        editorWrapper.id = 'editor-wrapper';
    }

    var editorContainerEle = document.createElement('div');
    editorContainerEle.id = 'editor-container';
    editorWrapper.appendChild(editorContainerEle);

    var startPadding = document.createElement('div');
    startPadding.id = 'start-padding';
    editorContainerEle.appendChild(startPadding);

    var startTimeEle = document.createElement('div');
    startTimeEle.id = 'start-time';
    startTimeEle.innerText = '00:00';
    editorContainerEle.appendChild(startTimeEle);

    var startBtnEle = document.createElement('div');
    var startDragImg = document.createElement('img');
    startDragImg.src = dragImgBs64
    startBtnEle.appendChild(startDragImg);
    startBtnEle.id = 'start-btn';
    startBtnEle.title = 'start time';
    editorContainerEle.appendChild(startBtnEle);

    var endTimeEle = document.createElement('div');
    endTimeEle.id = 'end-time';
    endTimeEle.innerText = secondToHMS(duration);
    editorContainerEle.appendChild(endTimeEle);

    var endBtnEle = document.createElement('div');
    endBtnEle.appendChild(DRAG_BUTTON);
    endBtnEle.id = 'end-btn'
    endBtnEle.title = 'end time';
    editorContainerEle.appendChild(endBtnEle);

    var endPadding = document.createElement('div');
    endPadding.id = 'end-padding';
    editorContainerEle.appendChild(endPadding);

    startTimeEle.style.left = - (startTimeEle.offsetWidth / 2) + 'px';
    endTimeEle.style.left = editorContainerEle.offsetWidth - (endTimeEle.offsetWidth / 2) + 'px';
    endBtnEle.style.right = editorContainerEle.offsetWidth - endBtnEle.offsetWidth + 'px';

    console.log('create div#dl-seg-btn --- start')

    infoContentEle.insertBefore(editorWrapper, infoContentEle.firstChild);

    var dlSegmentBtnEle = document.createElement('div');
    dlSegmentBtnEle.id = 'dl-seg-btn';
    dlSegmentBtnEle.innerText = 'Cut';
    dlSegmentBtnEle.addEventListener('click', function () {
        var result = {
            url: location.href + '&segment_start=' + hmsToSecond(startTimeEle.innerText) + '&segment_end=' + hmsToSecond(endTimeEle.innerText),
            metadata: Base64.encode(JSON.stringify(metadata)),
        };
        console.log(result);
        bridge.download(JSON.stringify(result));
    })
    infoContentEle.insertBefore(dlSegmentBtnEle, editorWrapper.nextSibling);
    console.log('create div#dl-seg-btn --- end')
}

function draggable(element, followEle, refEle, isStart) {
    var offset = 0;
    var isMouseDown = false;
    var mouseX;
    var elementX = element.offsetLeft;

    var duration = 0;
    var video = null;
    setInterval(() => {
        if (video == null) {
            video = document.getElementsByTagName('video')[0];
        }

        if (video && video.src != document.getElementsByTagName('video')[0].src) {
            video = document.getElementsByTagName('video')[0];
        }

        if (video && duration != video.duration) {
            duration = video.duration;
        }
    }, 1000);

    element.addEventListener('mousedown', onMouseDown);
    followEle.addEventListener('mousedown', onMouseDown);

    function onMouseDown(event) {
        mouseX = event.clientX;
        isMouseDown = true;

        document.addEventListener('mouseup', onMouseUp);
    }

    element.addEventListener('mouseup', onMouseUp);
    followEle.addEventListener('mouseup', onMouseUp);

    function onMouseUp(event) {
        isMouseDown = false;
        elementX = parseInt(element.offsetLeft);

        video.currentTime = duration * offset;

        document.removeEventListener('mouseup', onMouseUp);
    }

    window.addEventListener("resize", displayWindowSize);

    function displayWindowSize() {
        elementX = parseInt(element.offsetLeft);
    }

    document.addEventListener('mousemove', onMouseMove);

    function onMouseMove(event) {
        if (!isMouseDown) return;

        var deltaX = event.clientX - mouseX;

        if (isStart) {
            if (elementX + deltaX + 10 > document.getElementById('end-btn').offsetLeft) {
                return;
            }
        } else {
            if (elementX + deltaX - 10 < document.getElementById('start-btn').offsetLeft) {
                return;
            }
        }

        offset = (elementX + deltaX) / refEle.offsetWidth;
        var left = (elementX + deltaX) * 100 / refEle.offsetWidth;
        if (left > 100) {
            left = 100;
            offset = 1;
        }
        if (left < 0) {
            left = 0;
            offset = 0;
        }
        element.style.left = left + '%';

        if (isStart) {
            document.getElementById('start-padding').style.width = element.style.left;
        } else {
            document.getElementById('end-padding').style.left = (elementX + deltaX + element.offsetWidth) * 100 / refEle.offsetWidth + '%';
        }

        followEle.style.left = left - (followEle.offsetWidth / 2) * 100 / refEle.offsetWidth + '%';
        followEle.innerText = secondToHMS(duration * offset);

        video.currentTime = duration * offset;
        console.log(element.style.left);
    }
}

function removeElement(elementId) {
    // Removes an element from the document
    var element = document.getElementById(elementId);
    if (element) {
        element.parentNode.removeChild(element);
    }
}

var preVideoSrc = '';
setInterval(() => {
    loadSegBtn()
}, 1000);

window.addEventListener('scroll', function () {
    loadSegBtn()
})

function loadSegBtn() {
    try {
        if ((preVideoSrc !== document.getElementsByTagName('video')[0].src) || !document.getElementById('editor-container')) {
            preVideoSrc = document.getElementsByTagName('video')[0].src;

            removeElement('editor-container');
            removeElement('dl-seg-btn');
            initSegmentEditor();
            draggable(document.getElementById('start-btn'), document.getElementById('start-time'), document.getElementById('editor-container'), true);
            draggable(document.getElementById('end-btn'), document.getElementById('end-time'), document.getElementById('editor-container'));
        }
    } catch (err) {
        console.log(err);
    }
}
