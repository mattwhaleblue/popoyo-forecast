(function () {
  var TZ = "America/Managua";
  var dataEl = document.getElementById("tide-data");
  var out = document.getElementById("tide-now");
  if (!dataEl || !out) return;
  var data = JSON.parse(dataEl.textContent);
  var extrema = (data.extrema || []).slice().sort(function (a, b) { return a.min - b.min; });
  if (!extrema.length) return;

  function todayIso() {
    return new Date().toLocaleDateString("en-CA", { timeZone: TZ });
  }

  function nowMin() {
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: TZ,
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23"
    }).formatToParts(new Date());
    var h = 0, m = 0;
    for (var i = 0; i < parts.length; i++) {
      if (parts[i].type === "hour") h = +parts[i].value;
      if (parts[i].type === "minute") m = +parts[i].value;
    }
    return h * 60 + m;
  }

  function clock(min) {
    var m = ((min % 1440) + 1440) % 1440;
    var h = Math.floor(m / 60);
    var mi = m % 60;
    var suffix = h >= 12 ? "pm" : "am";
    var h12 = h % 12;
    if (!h12) h12 = 12;
    return h12 + ":" + String(mi).padStart(2, "0") + suffix;
  }

  function tideAt(t) {
    if (t <= extrema[0].min) return extrema[0].ft;
    if (t >= extrema[extrema.length - 1].min) return extrema[extrema.length - 1].ft;
    for (var i = 0; i < extrema.length - 1; i++) {
      var a = extrema[i], b = extrema[i + 1];
      if (a.min <= t && t <= b.min) {
        var span = b.min - a.min;
        if (!span) return a.ft;
        var phase = (t - a.min) / span;
        return a.ft + (b.ft - a.ft) * (1 - Math.cos(Math.PI * phase)) / 2;
      }
    }
    return extrema[extrema.length - 1].ft;
  }

  function bucket(t) {
    var nearest = extrema[0];
    var best = Math.abs(t - nearest.min);
    var idx = 0;
    for (var i = 1; i < extrema.length; i++) {
      var d = Math.abs(t - extrema[i].min);
      if (d < best) {
        best = d;
        nearest = extrema[i];
        idx = i;
      }
    }
    if (best <= 45) {
      var prev = extrema[idx - 1];
      var next = extrema[idx + 1];
      var isHigh = (prev && nearest.ft > prev.ft) || (next && nearest.ft > next.ft);
      return isHigh ? "high" : "low";
    }
    var prevE = extrema[0];
    var nextE = null;
    for (var i = 0; i < extrema.length; i++) {
      if (extrema[i].min <= t) prevE = extrema[i];
      if (extrema[i].min > t && !nextE) nextE = extrema[i];
    }
    if (!nextE) return prevE.ft > extrema[extrema.length - 1].ft ? "outgoing" : "incoming";
    return nextE.ft > prevE.ft ? "incoming" : "outgoing";
  }

  function xAt(t) {
    return data.x0 + (t - data.t_start) / (data.t_end - data.t_start) * (data.x1 - data.x0);
  }

  function yAt(h) {
    if (data.h_max <= data.h_min) return (data.y_top + data.y_bot) / 2;
    return data.y_top + (data.h_max - h) / (data.h_max - data.h_min) * (data.y_bot - data.y_top);
  }

  function render() {
    if (data.date !== todayIso()) {
      out.hidden = true;
      var mark = document.getElementById("tide-now-mark");
      if (mark) mark.setAttribute("hidden", "");
      return;
    }
    var t = nowMin();
    var ft = tideAt(t);
    var b = bucket(t);
    out.hidden = false;
    out.innerHTML = "Now " + clock(t) + " · <b>" + ft.toFixed(1) + "ft " + b + "</b>";

    var mark = document.getElementById("tide-now-mark");
    var line = document.getElementById("tide-now-line");
    var dot = document.getElementById("tide-now-dot");
    if (mark && line && dot && t >= data.t_start && t <= data.t_end) {
      var x = xAt(t);
      var y = yAt(ft);
      line.setAttribute("x1", x.toFixed(1));
      line.setAttribute("x2", x.toFixed(1));
      line.setAttribute("y1", y.toFixed(1));
      line.setAttribute("y2", String(data.y_fill));
      dot.setAttribute("cx", x.toFixed(1));
      dot.setAttribute("cy", y.toFixed(1));
      mark.removeAttribute("hidden");
    } else if (mark) {
      mark.setAttribute("hidden", "");
    }
  }

  render();
  setInterval(render, 30000);
})();
