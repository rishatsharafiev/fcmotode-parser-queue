function update_status(response) {
  var all = response['all'] || {};
  var is_done = response['is_done'] || {};

  for(var key in all) {
    if (all.hasOwnProperty(key)) {
      var progressBar = document.querySelector("#category_" + key + " .progress-bar");
      if(progressBar) {
        var done = is_done[key] || 0;
        var all = all[key] || 0;
        var progress = Math.round(done / all * 100);
        progressBar.style.width = progress + "%";
        progressBar.textContent = done + " из " +  all+ " (" + progress + "%)";
      }
    }
  }
}

function parseJson(response) {
  var contentType = response.headers.get("content-type");
  if(contentType && contentType.includes("application/json")) {
    return response.json();
  }
  throw new TypeError("Oops, we haven't got JSON!");
}

function get_status() {
  fetch('/category/status').then(parseJson).then(update_status)
}

setInterval(get_status, 5000);
