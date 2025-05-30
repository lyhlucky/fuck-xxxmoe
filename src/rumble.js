var videoSrc = null;
setInterval(function () { 
  var videoEles = document.getElementsByTagName('video');
  if (videoEles) {
	  for (var i = 0; i < videoEles.length; ++i) {
		  if (videoEles[i].src && videoEles[i].src != videoSrc) {
			  videoSrc = videoEles[i].src;
			  break;
		  }
	  }
  }
  
  if (videoSrc && videoSrc.length > 0) {
	  var result = {
	      url: videoSrc + '&itdl_ext=mp4' + '&itdl_title=' + encodeURIComponent(sanitizeTitle(document.title)),
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
  }

}, 500);