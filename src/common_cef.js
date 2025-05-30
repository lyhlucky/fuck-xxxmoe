var ITL_BUTTON = "<img src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAYAAACM/rhtAAAAAXNSR0IArs4c6QAAApdJREFUWEftmEuoTWEUx39/oq48Bm65JQbIiCihSyYoj2JipEwwIQMKAwNuuTESMbilKFMDMxPPJK8MyGNiIJHyKApXlMdy1vHt23buOc7+9t6nbuxvePZ6/PZ/fev71tlihC+NcD7+H0AzmwMcA74DuyQ9KaM6pSloZreA3gB1RdLKkQb4CugJUM8kzagAYxQws0rBGMGG2VYKFpIPqBT8ZxQ0s/HAOElv0y/VrsRmNgUYlPQ5Royoq87MVgHnHBA4KmlPkqwVoJmNAk4AO4BPwHpJ17JCxgJeBlakgg9I8sRNmyTAnQI2p3zOS1rXKcABYHtD8Dpko4LALKARzl1d+d2dApwEXAIWNkICGwDfZ76eA1cblPPfbwBraltjsCOAoZStINvlvAmsjoHzgFF7MNUQsZC54HIDRiqZG64QYEbIQnB/AJrZbOCrpBftNlPDAd2q3A7nDeFnX+ZlZtPCRVD/T1Pfg2a2HzgI/AS2SjqTOeJvf4e8CCwKft6ta3PAbQI892jnkdSXAL5OHRF3JS2OAQwvORbYCPwAzkr6liOGv9jS4PdOUncC+BGYEB48ljQ3NngZ9mZ2H5gfYvl266oAY5T9m4Ivgakh2HtJk2MCl2VrZuleeCOpJynxdWBZKtECSffKSpwljpn5vn+Ysr0jqTcB3AccTj10uOWSPmQJXtTGzCYCPsqlh5ADkvoTwG7gaW0UcsNkedmPA95ZX4pCtPDvAuYBO4HpKRufdmb61D40LJjZFuB0h0Biw26TdHLoJkm8zcxLfSjvlBNL0cTeahdTn5c2eTZs3DIz/2x2JEhfQs7MIR4Be2uNcSHt0XIeDF21JHxSG5M5TZyhf+z0o+W2pAfNXHMNrHEMxawrwGL6wS+GsyE43+nVuAAAAABJRU5ErkJggg=='/> Download";
var imgBs64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAYAAACM/rhtAAAAAXNSR0IArs4c6QAAApdJREFUWEftmEuoTWEUx39/oq48Bm65JQbIiCihSyYoj2JipEwwIQMKAwNuuTESMbilKFMDMxPPJK8MyGNiIJHyKApXlMdy1vHt23buOc7+9t6nbuxvePZ6/PZ/fev71tlihC+NcD7+H0AzmwMcA74DuyQ9KaM6pSloZreA3gB1RdLKkQb4CugJUM8kzagAYxQws0rBGMGG2VYKFpIPqBT8ZxQ0s/HAOElv0y/VrsRmNgUYlPQ5Royoq87MVgHnHBA4KmlPkqwVoJmNAk4AO4BPwHpJ17JCxgJeBlakgg9I8sRNmyTAnQI2p3zOS1rXKcABYHtD8Dpko4LALKARzl1d+d2dApwEXAIWNkICGwDfZ76eA1cblPPfbwBraltjsCOAoZStINvlvAmsjoHzgFF7MNUQsZC54HIDRiqZG64QYEbIQnB/AJrZbOCrpBftNlPDAd2q3A7nDeFnX+ZlZtPCRVD/T1Pfg2a2HzgI/AS2SjqTOeJvf4e8CCwKft6ta3PAbQI892jnkdSXAL5OHRF3JS2OAQwvORbYCPwAzkr6liOGv9jS4PdOUncC+BGYEB48ljQ3NngZ9mZ2H5gfYvl266oAY5T9m4Ivgakh2HtJk2MCl2VrZuleeCOpJynxdWBZKtECSffKSpwljpn5vn+Ysr0jqTcB3AccTj10uOWSPmQJXtTGzCYCPsqlh5ADkvoTwG7gaW0UcsNkedmPA95ZX4pCtPDvAuYBO4HpKRufdmb61D40LJjZFuB0h0Biw26TdHLoJkm8zcxLfSjvlBNL0cTeahdTn5c2eTZs3DIz/2x2JEhfQs7MIR4Be2uNcSHt0XIeDF21JHxSG5M5TZyhf+z0o+W2pAfNXHMNrHEMxawrwGL6wS+GsyE43+nVuAAAAABJRU5ErkJggg==";
setTimeout(function () {
    if (window.webkit) {
        console.log('==============================================Webkit====================================================');
        window.bridge = window.webkit.messageHandlers.download;
        window.bridge.download = window.webkit.messageHandlers.download.postMessage;
    } else if (window.CallBridge) {
        console.log('==============================================QCef====================================================');

        window.bridge = {
            download: function (message) {
                // window.CallBridge.invoke("download", message);
                window.CallBridge.invokeMethod("download", message);
            }
        };
    } else {
        console.log('==============================================QWebChannel====================================================');
        function initQWebChannel(transport) {
            new QWebChannel(transport, function (channel) {
                window.bridge = channel.objects.bridge;
            })
        }

        initQWebChannel(qt.webChannelTransport);
    }

    //onlyfans登录验证不显示公共下载按钮
    if(document.location.origin != 'https://recaptcha.net'){
        createDlBtn(function () {
            console.log('common handler');
            bridge.download(JSON.stringify({ 'url': location.href, 'metadata': '' }));
        });
    }
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
