var ITL_BUTTON = "<img src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAAXNSR0IArs4c6QAABE1JREFUeF7tm1vIZWMcxn+PY4pQhpRjQ85CuJgLxIUoE0YxkiQ1XEgmN6IcihtTjsnhgpJMk0NySIpolENRJmmcxjQTklNCGTGP9f9ae7e/Ne/ee+2919qH2eu9+vbuPfyfZ//P7/uJOR+ac/w0BDQaMOcMTMQEbO8O3AZcCfwHPA2skRR/j3VMioD7gFsKSG+XdM9Y0cNknKDtX4H9C2A3SzpypyfA9t7AHwmg2yXt2hAwZgbG7gMaDWhMoPEBjRNsokATBps8oEmEmkxwRwaaVLipBZpiaMarQdu7AMfm5r1R0vaiqQ9TDNmOMvl44J+si/SlJFdVNFZWDdo+DHgBOD0X7mPgCklfdwo7KAG2T8hIXQucmO/zHnCZpB+rIKFKAt4Azi8I9T1wjqSvWt8PQoDtk4G3gAMK+66TdPnUEGB7D+AvYLeEUItIKEtAD/BxxJ+S9pkaAkIQ278B+3URqk1CGQL6gI8jtkoKkxt5VGkCd2TS3NlDogUSgB96VYMlwMcRN0t6YGT0VXaFc0/9DLCyDwkXAeEgiyMixqldbL5z7hPA9VVFgso0IDeDCFf9SPgJWJIgIELbLwmHVxv42LhSAgYgYRjtrfSXbwlQOQE1kVAL+Fo0oCPelzGHMppQG/haCahIE57Mosaqqhxeiu1aTKDzoJLRISVb7eBr14ARzGEs4MdGwIDmMDbwiwiwfSjwcJ6tfZeFyLskrSvjpcrOKWEOtYC3fQlwNxAY12f5xo2SNrcJsB1FzCdZOXtSB5hITM6V9E5ZgGXm5STEi5CrCvMfB26o2uHZXpaDjl5Fa2wETpG0bcEJ2j4D+CgB4ClJ15YBNugc25EyX5o/kYny9sVB9ygz3/ajQWxi7lmS1rcIuBh4KTHpTUnFGr/MuVMzx/bLmXYvTwi0UtLahoDcBBoNaExgzn3AhcBrCUfxduYpz5sajzaEILZfBy5ILF0RkaflBE/r0qWJHvwxQ5w7NUtsbyjkNy3ZlmUR7v0WAQdmsbJbn32ppE1Tg2gAQWwfAmzp0vg5PMtxtrSrQdufA8cl9n9VUvTxZm7Yfh5YkRB8k6Sl8X0nAfcCt3ZBGbnzI7PEgO3rgKgtUuN+SauLBMQ73ciR45IjNZ7Li4hoXE7tsB13Ew8CV3cR8t+4ZpP0xSIC4kO2OHrtN/VA9zfwLvBtpi3bpoyFPbNn90cAZwN79ZDtsexesV0bLOoI2d4X+KDjhnfKMI4szjfAmZLitfrC2KElZvvoLG5+mHjOPvLpE97gdyBCXzj79kj2BG3HHf8rwFETFrqq48Nkl0v6rLhh16ao7fiHhjXANVk3pbOZUJVQ49gnrtueBVZL+jl1YN+ucP5AIRxj1NQHjUPqCs6I67fQ4Ickfdprv74EtBbnz1+iZRZ9tYP7eNoKMAy8RUSouHnemnWaNqSe5wylAQOLMWMLSmvAjOEqLW5DQGmqdtKJc68B/wObasxQckkEeAAAAABJRU5ErkJggg=='/> Download"
var imgBs64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAAXNSR0IArs4c6QAABE1JREFUeF7tm1vIZWMcxn+PY4pQhpRjQ85CuJgLxIUoE0YxkiQ1XEgmN6IcihtTjsnhgpJMk0NySIpolENRJmmcxjQTklNCGTGP9f9ae7e/Ne/ee+2919qH2eu9+vbuPfyfZ//P7/uJOR+ac/w0BDQaMOcMTMQEbO8O3AZcCfwHPA2skRR/j3VMioD7gFsKSG+XdM9Y0cNknKDtX4H9C2A3SzpypyfA9t7AHwmg2yXt2hAwZgbG7gMaDWhMoPEBjRNsokATBps8oEmEmkxwRwaaVLipBZpiaMarQdu7AMfm5r1R0vaiqQ9TDNmOMvl44J+si/SlJFdVNFZWDdo+DHgBOD0X7mPgCklfdwo7KAG2T8hIXQucmO/zHnCZpB+rIKFKAt4Azi8I9T1wjqSvWt8PQoDtk4G3gAMK+66TdPnUEGB7D+AvYLeEUItIKEtAD/BxxJ+S9pkaAkIQ278B+3URqk1CGQL6gI8jtkoKkxt5VGkCd2TS3NlDogUSgB96VYMlwMcRN0t6YGT0VXaFc0/9DLCyDwkXAeEgiyMixqldbL5z7hPA9VVFgso0IDeDCFf9SPgJWJIgIELbLwmHVxv42LhSAgYgYRjtrfSXbwlQOQE1kVAL+Fo0oCPelzGHMppQG/haCahIE57Mosaqqhxeiu1aTKDzoJLRISVb7eBr14ARzGEs4MdGwIDmMDbwiwiwfSjwcJ6tfZeFyLskrSvjpcrOKWEOtYC3fQlwNxAY12f5xo2SNrcJsB1FzCdZOXtSB5hITM6V9E5ZgGXm5STEi5CrCvMfB26o2uHZXpaDjl5Fa2wETpG0bcEJ2j4D+CgB4ClJ15YBNugc25EyX5o/kYny9sVB9ygz3/ajQWxi7lmS1rcIuBh4KTHpTUnFGr/MuVMzx/bLmXYvTwi0UtLahoDcBBoNaExgzn3AhcBrCUfxduYpz5sajzaEILZfBy5ILF0RkaflBE/r0qWJHvwxQ5w7NUtsbyjkNy3ZlmUR7v0WAQdmsbJbn32ppE1Tg2gAQWwfAmzp0vg5PMtxtrSrQdufA8cl9n9VUvTxZm7Yfh5YkRB8k6Sl8X0nAfcCt3ZBGbnzI7PEgO3rgKgtUuN+SauLBMQ73ciR45IjNZ7Li4hoXE7tsB13Ew8CV3cR8t+4ZpP0xSIC4kO2OHrtN/VA9zfwLvBtpi3bpoyFPbNn90cAZwN79ZDtsexesV0bLOoI2d4X+KDjhnfKMI4szjfAmZLitfrC2KElZvvoLG5+mHjOPvLpE97gdyBCXzj79kj2BG3HHf8rwFETFrqq48Nkl0v6rLhh16ao7fiHhjXANVk3pbOZUJVQ49gnrtueBVZL+jl1YN+ucP5AIRxj1NQHjUPqCs6I67fQ4Ickfdprv74EtBbnz1+iZRZ9tYP7eNoKMAy8RUSouHnemnWaNqSe5wylAQOLMWMLSmvAjOEqLW5DQGmqdtKJc68B/wObasxQckkEeAAAAABJRU5ErkJggg==";

setTimeout(function () {
    if (window.webkit) {
        window.bridge = window.webkit.messageHandlers.download;
        window.bridge.download = window.webkit.messageHandlers.download.postMessage;
    } else {
        function initQWebChannel(transport) {
            new QWebChannel(transport, function (channel) {
                window.bridge = channel.objects.bridge;
            })
        }

        initQWebChannel(qt.webChannelTransport);
    }

    createDlBtn(function () {
        console.log('common handler');
        bridge.download(JSON.stringify({ 'url': location.href, 'metadata': '' }));
    });
}, 0);

function createDlBtn(clickHandler) {
    var css = `
    #itdl-btn {
        position: fixed;
        bottom: 30px;
        z-index: 99999;
        right: 30px;
        font-size: 25px;
        padding: 10px 20px;
        cursor: pointer;
        background: #00CF2E;
        color: white;
        border-radius: 5px;
        border: none;
        box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
        display: flex;
        align-items: center;
    }
    #itdl-btn:hover{ background-color: #00A625 }
    #itdl-btn:focus{ outline: none; }

    #itdl-btn img {
        width: 30px;
        height: 30px;
        margin-right: 4px;
        vertical-align: text-bottom;
    }
    `;

    if (!document.getElementById('itd_btn_style')) {
        var style = document.createElement('style');
        style.id = 'itd_btn_style'

        if (style.styleSheet) {
            style.styleSheet.cssText = css;
        } else {
            style.appendChild(document.createTextNode(css));
        }
        document.getElementsByTagName('head')[0].appendChild(style);
    }


    var body = document.getElementsByTagName('body')[0]
    var itdlBtn = document.createElement('button');
    var img = document.createElement('img');
    var txt = document.createElement('span');
    txt.innerText = 'Download';
    img.src = imgBs64
    itdlBtn.appendChild(img)
    itdlBtn.appendChild(txt)

    itdlBtn.id = 'itdl-btn';
    itdlBtn.onclick = clickHandler;
    body.appendChild(itdlBtn);
}

function sanitizeTitle(title) {
    return title.replace(/[\/?:*"><|]/g, "");
}

function appendQueryParam(url, key, value) {
    // 检查 URL 是否已包含问号（?）
    const hasQuery = url.indexOf("?") !== -1;

    // 如果 URL 包含问号，使用 & 符号追加参数，否则使用 ? 符号
    const separator = hasQuery ? "&" : "?";

    // 将参数追加到 URL
    return url + separator + encodeURIComponent(key) + "=" + encodeURIComponent(value);
}

/**
 * 如果参数值为空，则删除参数；否则，更新或添加参数
 * @param  url
 * @param  parameter
 * @param  value
 * @returns  {string}
 */
function updateUrlParameter(url, parameter, value) {
    // 使用URL类解析URL
    const urlObj = new URL(url);

    // 如果参数值为空，则删除参数；否则，更新或添加参数
    if (value === '' || value === null || value === undefined) {
        urlObj.searchParams.delete(parameter);
    } else {
        urlObj.searchParams.set(parameter, value);
    }

    // 返回更新后的URL
    return urlObj.toString();
}

function getUrlParam(name) {
    const url = window.location.href;
    name = name.replace(/[\[\]]/g, '\\$&');
    const regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)');
    const results = regex.exec(url);

    if (!results) return null;
    if (!results[2]) return '';

    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

function createStyle() {
    if (!document.getElementById('itubego_style')) {
        var css = `
            .itdl-btn {
                position: absolute;
                top: 1%;
                right: 1%;
                z-index: 99999;
                font-size: 25px;
                padding: 10px 20px;
                cursor: pointer;
                background: #00CF2E;
                color: white;
                border-radius: 5px;
                border: none;
                box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
                display: flex-end;
                align-items: center;
            }
            .itdl-btn:hover{ background-color: #00A625 }
            .itdl-btn:focus{ outline: none; }

            .itdl-btn > img {
                width: 30px !important;
                height: 30px !important;
                vertical-align: text-bottom !important;
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

function getCookie(cname) {
    var name = cname + "=";
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(";");
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) === " ") {
            c = c.substring(1);
        }
        if (c.indexOf(name) === 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

async function sha1(message) {
    const msgUint8 = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-1', msgUint8);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

function debounce(fn, wait) {
    let timer;
    return function (...args) {
        if (timer) {
            clearTimeout(timer); // clear any pre-existing timer
        }
        const context = this; // get the current context
        timer = setTimeout(() => {
            fn.apply(context, args); // call the function if time expires
        }, wait);
    }
}

function throttle(func, limit) {
    let inThrottle;
    return function () {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}
function sleep(second) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            resolve();
        }, second * 1000);
    });
}

/**
 *
 *  Base64 encode / decode
 *  http://www.webtoolkit.info/
 *
 **/
var Base64 = {

    // private property
    _keyStr: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",

    // public method for encoding
    encode: function (input) {
        var output = "";
        var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
        var i = 0;

        input = Base64._utf8_encode(input);

        while (i < input.length) {

            chr1 = input.charCodeAt(i++);
            chr2 = input.charCodeAt(i++);
            chr3 = input.charCodeAt(i++);

            enc1 = chr1 >> 2;
            enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
            enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
            enc4 = chr3 & 63;

            if (isNaN(chr2)) {
                enc3 = enc4 = 64;
            } else if (isNaN(chr3)) {
                enc4 = 64;
            }

            output = output +
                this._keyStr.charAt(enc1) + this._keyStr.charAt(enc2) +
                this._keyStr.charAt(enc3) + this._keyStr.charAt(enc4);

        }

        return output;
    },

    // private method for UTF-8 encoding
    _utf8_encode: function (string) {
        string = string.replace(/\r\n/g, "\n");
        var utftext = "";

        for (var n = 0; n < string.length; n++) {

            var c = string.charCodeAt(n);

            if (c < 128) {
                utftext += String.fromCharCode(c);
            }
            else if ((c > 127) && (c < 2048)) {
                utftext += String.fromCharCode((c >> 6) | 192);
                utftext += String.fromCharCode((c & 63) | 128);
            }
            else {
                utftext += String.fromCharCode((c >> 12) | 224);
                utftext += String.fromCharCode(((c >> 6) & 63) | 128);
                utftext += String.fromCharCode((c & 63) | 128);
            }

        }

        return utftext;
    },

}