function copyToClipboard(e, text) {
  navigator.clipboard
    .writeText(text)
    .then(function () {
      e.target.closest('.copy-btn').style.background = 'mediumseagreen';
      setTimeout(() => {
        e.target.closest('.copy-btn').style.background = 'cornflowerblue';
      }, 1000);
    })
    .catch(function (err) {
      console.error('Could not copy text: ', err);
      alert('Copy failed. Text: ' + text);
    });
}

function copyAnchorToClipboard(e, copyValue, text, linkKind) {
  let anchorHtml = '';
  if (linkKind === 'contact') {
    anchorHtml = `<a href="${copyValue}">${text}</a>`;
  } else if (linkKind === 'pdf') {
    anchorHtml = `<a href="${copyValue}" target="_blank" title="${text}. PDF format, opens in new window.">${text}</a>`;
  }

  navigator.clipboard
    .writeText(anchorHtml)
    .then(function () {
      e.target.closest('.copy-anchor-btn').style.filter = 'brightness(1.2)';
      setTimeout(() => {
        e.target.closest('.copy-anchor-btn').style.filter = 'brightness(1)';
      }, 1000);
    })
    .catch(function (err) {
      console.error('Could not copy anchor HTML: ', err);
      alert('Copy failed. HTML: ' + anchorHtml);
    });
}

function copyEmbedToClipboard(e, src, title) {
  const match = src.match(/player\.vimeo\.com\/video\/(\d+)/);
  const id = match ? match[1] : '';
  const snippet = `<iframe src="https://player.vimeo.com/video/${id}?badge=0&autopause=0&player_id=0&app_id=58479&texttrack=en" frameborder="0" allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media; web-share" style="position:absolute;top:0;left:0;width:100%;height:100%;" title="${title}"></iframe>`;
  navigator.clipboard
    .writeText(snippet)
    .then(function () {
      e.target.closest('.copy-btn').style.background = 'mediumseagreen';
      setTimeout(() => {
        e.target.closest('.copy-btn').style.background = 'cornflowerblue';
      }, 1000);
    })
    .catch(function (err) {
      console.error('Could not copy embed HTML: ', err);
      alert('Copy failed. HTML: ' + snippet);
    });
}
