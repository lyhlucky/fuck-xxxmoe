setTimeout(function () {
    // 删除全局按钮
    var commonBtn = document.getElementById('itdl-btn');
    commonBtn && commonBtn.remove();

    createStyle();
    loadDlBtn();

    setInterval(function () {
        loadDlBtn();
    }, 1000)
}, 1500)

function requestVideo(metadata) {
    let timeDiv = metadata.articleItem.querySelector('time')       //一般视频 发推时间找链接

    var locationId
    if (timeDiv) {
        let url1 = timeDiv.parentNode.href
        url1_sec = url1.split('/')
        locationId = url1_sec[url1_sec.length - 1]
    }

    var requestUrl = combineUrl(locationId)
    console.log('@requestUrl:', requestUrl)

    var xToken = document.cookie.split(';')

    for (let i = 0; i < xToken.length; i++) {
        let parts = xToken[i].split('=');
        if (parts.shift().trim() === 'ct0') {
            parts.join('')
            xToken = parts
            break
        }
    }

    fetch(requestUrl, {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'X-Csrf-Token': xToken
        }
    })
        .then(response => response.json())
        .then(
            function (data) {
                console.log('data:', data)
                var entriesArry = data.data
                    .threaded_conversation_with_injections_v2
                    .instructions[0]
                    .entries

                var article_index = -1;
                var videoUrl = null;
                var thumbUrl = null;
                console.log('item index:', metadata.itemindex)

                for (let i = 0; i < entriesArry.length; i++) {
                    if (entriesArry[i]['entryId'].includes(locationId)) {
                        if (entriesArry[i].content.itemContent.tweet_results.result.tweet) {
                            videoUrl = entriesArry[i].content.itemContent.tweet_results.result.tweet.legacy.entities.media[metadata.subMedia].video_info.variants[0].url
                            thumbUrl = entriesArry[i].content.itemContent.tweet_results.result.tweet.legacy.entities.media[metadata.subMedia].media_url_https
                        } else {
                            videoUrl = entriesArry[i].content.itemContent.tweet_results.result.legacy.entities.media[metadata.subMedia].video_info.variants[0].url
                            thumbUrl = entriesArry[i].content.itemContent.tweet_results.result.legacy.entities.media[metadata.subMedia].media_url_https
                        }
                    }

                }

                console.log('videourl', videoUrl)
                if (videoUrl) {
                    if (thumbUrl === null) {
                        var videodiv = metadata.videoItem.querySelector('video[aria-label]');
                        thumbUrl = videodiv.poster;
                    }

                    var title
                    var tw_text_elem = metadata.videoItem.querySelector('div[data-testid="tweetText"]');
                    if (tw_text_elem) {
                        title = tw_text_elem.innerText;
                    } else {
                        if (metadata.articleItem.querySelector('div[data-testid="tweetText"]')) {
                            title = metadata.articleItem.querySelector('div[data-testid="tweetText"]').innerText;
                        } else {
                            let user_div = metadata.articleItem.querySelector('div[data-testid="User-Name"]')
                            if (user_div && user_div.querySelector('span')) {

                                title = user_div.querySelector('span').innerText
                            } else {
                                title = 'unknown'
                            }

                        }

                    }

                    download(title, videoUrl, thumbUrl, 'm3u8')
                }

            }
        )
}


function download(title, videoUrl, thumbUrl, format) {
    title = encodeURIComponent(sanitizeTitle(`${title}`))
    console.log('@title', title);

    var finalUrl
    if (format === 'm3u8') {
        finalUrl = updateUrlParameter(videoUrl, 'media_title', title);
    } else {
        finalUrl = updateUrlParameter(videoUrl, 'itdl_title', title);

        finalUrl = updateUrlParameter(finalUrl, 'itdl_ext', 'mp4');
    }

    if (thumbUrl) {
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

function onClickDownload(metadata) {

    var tweetPhotoDiv = metadata.videoItem.querySelectorAll('div[data-testid="tweetPhoto"]').item(metadata.subMedia)
    // console.log('tweetPhotoDiv:',tweetPhotoDiv,metadata.videoItem)

    var childDiv = metadata.videoItem.childNodes.item(0).childNodes.item(0).childNodes.item(0).childNodes.item(0)
    // var className = tweetPhotoDiv.parentNode.parentNode.parentNode.parentNode.className   //通过 div classname 长短判断是否限制视频

    console.log('className', childDiv.className)
    if (childDiv.childNodes.length >= 2) {   //限制视频
        requestVideo(metadata);
    } else {
        let videoDiv = tweetPhotoDiv.querySelector('video')

        if (videoDiv) {
            let videoUrl = videoDiv.src
            if (!videoUrl.startsWith('blob') && videoUrl.endsWith(".mp4")) {     //mp4链接
                let title = videoDiv.getAttribute('aria-label');
                let poster = videoDiv.poster
                download(title, videoUrl, poster, 'mp4')

            } else {
                let avatDiv = metadata.videoItem.querySelector('div[data-testid="Tweet-User-Avatar"]')
                if (avatDiv) {
                    let textDiv = metadata.videoItem.querySelector('div[data-testid="tweetText"]')    //评论带转推视频 页面跳转
                    textDiv.click()
                } else {

                    if (metadata.subMedia > 0) {
                        requestVideo(metadata);
                    } else {
                        let timeDiv = metadata.articleItem.querySelector('time')       //一般视频 发推时间找链接

                        let url
                        if (timeDiv) {
                            url = timeDiv.parentNode.href

                            console.log('common handler', url);
                            bridge.download(JSON.stringify({ 'url': url, 'metadata': '' }));
                        }
                    }
                }
            }
        }
    }
}

function combineUrl(locationId) {
    var queryId = 'QVo2zKMcLZjXABtcYpi0mA'; //7Bl7Pu9C4U-kjbsuzH-EzA  QVo2zKMcLZjXABtcYpi0mA

    var url = 'https://x.com/i/api/graphql/' + queryId + '/TweetDetail'
    //var locationSec = document.location.toString().split('/');

    let varibDict = {
        'focalTweetId': locationId,
        'with_rux_injections': false,
        // "rankingMode":"Relevance",
        'includePromotedContent': true,
        'withCommunity': true,
        'withQuickPromoteEligibilityTweetFields': true,
        'withBirdwatchNotes': true,
        'withVoice': true
    }
    url += ('?variables=' + encodeURIComponent(JSON.stringify(varibDict)))

    let feature = {
        "rweb_tipjar_consumption_enabled": true,
        'responsive_web_graphql_exclude_directive_enabled': true,
        'verified_phone_label_enabled': false,
        'creator_subscriptions_tweet_preview_api_enabled': true,
        'responsive_web_graphql_timeline_navigation_enabled': true,
        'responsive_web_graphql_skip_user_profile_image_extensions_enabled': false,
        'communities_web_enable_tweet_community_results_fetch': true,
        'c9s_tweet_anatomy_moderator_badge_enabled': true,
        'articles_preview_enabled': true,
        'tweetypie_unmention_optimization_enabled': true,
        'responsive_web_edit_tweet_api_enabled': true,
        'graphql_is_translatable_rweb_tweet_is_translatable_enabled': true,
        'view_counts_everywhere_api_enabled': true,
        'longform_notetweets_consumption_enabled': true,
        'responsive_web_twitter_article_tweet_consumption_enabled': true,
        'tweet_awards_web_tipping_enabled': false,
        'creator_subscriptions_quote_tweet_preview_enabled': false,
        'freedom_of_speech_not_reach_fetch_enabled': true,
        'standardized_nudges_misinfo': true,
        'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': true,
        'rweb_video_timestamps_enabled': true,
        'longform_notetweets_rich_text_read_enabled': true,
        'longform_notetweets_inline_media_enabled': true,
        'responsive_web_enhance_cards_enabled': false
    }

    url += ('&features=' + encodeURIComponent(JSON.stringify(feature)))

    let fieldTogglesDict = {
        'withArticleRichContentState': true,
        'withArticlePlainText': false,
        'withGrokAnalyze': false
    }

    url += ('&fieldToggles=' + encodeURIComponent(JSON.stringify(fieldTogglesDict)))
    return url
}

function loadDlBtn() {
    var videoItems = document.querySelectorAll('article[aria-labelledby]') //

    for (let i = 0; i < videoItems.length; i++) {
        let articleItem = videoItems.item(i)
        let videoItem = articleItem.querySelector('div[aria-labelledby]')
        var itemArry = articleItem.querySelectorAll('div[data-testid="tweetPhoto"]');

        for (let j = 0; j < itemArry.length; j++) {
            let videoBtDiv = itemArry.item(j).querySelector('div[data-testid="videoPlayer"]')
            if (videoBtDiv) {

                if (!videoBtDiv.querySelector('.itdl-btn')) {
                    var itdlBtn = document.createElement('button');
                    itdlBtn.innerHTML = ITL_BUTTON;
                    itdlBtn.classList.add('itdl-btn');

                    var metadata = {
                        videoItem: videoItem,
                        articleItem: articleItem,
                        itemindex: i,
                        subMedia: j,
                    }
                    itdlBtn.metadata = metadata

                    itdlBtn.onclick = function (event) {
                        onClickDownload(event.target.metadata)
                    }

                    videoBtDiv.insertBefore(itdlBtn, videoBtDiv.childNodes.item(0))
                }
            }
        }
    }
}

function createStyle() {
    if (!document.getElementById('itubego_style')) {
        var css = `
            .itdl-btn {
                position: absolute;
                top: 0em;
                right: 0em;
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
