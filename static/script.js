/* ==========================================================
   KRT AI TERMINAL — frontend logic
   Polls /api/dashboard every 5s and renders the UI.
   ========================================================== */
(function () {
  "use strict";

  var REFRESH_MS = 5000;
  var $ = function (id) { return document.getElementById(id); };

  var inr = function (n) {
    return Number(n).toLocaleString("en-IN", {
      minimumFractionDigits: 2, maximumFractionDigits: 2
    });
  };
  var vol = function (n) {
    n = Number(n) || 0;
    if (n >= 1e7) return (n / 1e7).toFixed(2) + " Cr";
    if (n >= 1e5) return (n / 1e5).toFixed(2) + " L";
    return n.toLocaleString("en-IN");
  };
  var chgSpan = function (c) {
    var cls = c >= 0 ? "up" : "down";
    var sign = c >= 0 ? "+" : "";
    return '<span class="' + cls + ' mono">' + sign + c.toFixed(2) + "%</span>";
  };
  var esc = function (s) {
    return String(s).replace(/[&<>"']/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
    });
  };

  /* ---------- renderers ---------- */

  function renderConn(mode, updated) {
    var dot = $("connDot"), txt = $("connText");
    dot.className = "dot " + (mode === "live" ? "live" : "demo");
    txt.textContent = mode === "live"
      ? "LIVE \u00B7 ANGEL ONE \u00B7 " + updated
      : "DEMO MODE \u00B7 " + updated;
  }

  function renderTicker(indices) {
    $("tickerStrip").innerHTML = indices.map(function (x) {
      return '<div class="ticker-item">' +
        '<span class="sym">' + esc(x.symbol) + "</span>" +
        '<span class="mono">' + inr(x.ltp) + "</span>" +
        chgSpan(x.chg) + "</div>";
    }).join("");
  }

  function renderIndices(indices) {
    $("indices").innerHTML = indices.map(function (x) {
      var pill = x.chg >= 0
        ? '<span class="pill up">▲ BULLISH</span>'
        : '<span class="pill down">▼ BEARISH</span>';
      return '<div class="card">' +
        '<div class="name">' + esc(x.symbol) + "</div>" +
        '<div class="val mono">' + inr(x.ltp) + "</div>" +
        '<div class="chg-row">' + chgSpan(x.chg) + pill + "</div>" +
        "</div>";
    }).join("");
  }

  function stockRow(x) {
    return '<div class="row">' +
      "<span><span class=\"sym\">" + esc(x.symbol) + "</span>" +
      '<div class="sub">H ' + inr(x.high || 0) + " \u00B7 L " + inr(x.low || 0) + "</div></span>" +
      '<span class="right"><span class="mono">' + inr(x.ltp) + "</span><br>" +
      chgSpan(x.chg) + "</span></div>";
  }

  function renderLists(d) {
    $("gainers").innerHTML = d.gainers.map(stockRow).join("");
    $("losers").innerHTML = d.losers.map(stockRow).join("");
    $("volume").innerHTML = d.volume.map(function (x) {
      return '<div class="row"><span class="sym">' + esc(x.symbol) + "</span>" +
        '<span class="mono muted">' + vol(x.volume) + " sh</span></div>";
    }).join("");
  }

  function renderAlerts(alerts) {
    $("alertCount").textContent = alerts.length ? alerts.length + " active" : "";
    if (!alerts.length) {
      $("alerts").innerHTML =
        '<div class="row muted">No confluence alerts right now \u2014 ' +
        "conditions \u0BAA\u0BCA\u0BB0\u0BC1\u0BA8\u0BCD\u0BA4\u0BC1\u0BAE\u0BCD\u0BAA\u0BCB\u0BA4\u0BC1 \u0B87\u0B99\u0BCD\u0B95 \u0BB5\u0BB0\u0BC1\u0BAE\u0BCD.</div>";
      return;
    }
    $("alerts").innerHTML = alerts.map(function (a) {
      return '<div class="row">' +
        '<span><span class="badge ' + esc(a.type) + '">' + esc(a.type) + "</span>" +
        ' <span class="sym" style="margin-left:8px">' + esc(a.symbol) + "</span>" +
        '<div class="sub">' + esc(a.reason) + "</div></span>" +
        chgSpan(a.chg) + "</div>";
    }).join("");
  }

  function renderPulse(d) {
    var stocks = d.gainers.concat(d.losers);
    var adv = stocks.filter(function (s) { return s.chg > 0; }).length;
    var dec = stocks.filter(function (s) { return s.chg < 0; }).length;
    var vix = (d.indices.filter(function (i) { return i.symbol === "INDIA VIX"; })[0] || {});
    var breadth = adv >= dec ? "Positive" : "Negative";
    var cells = [
      ["ADVANCES", '<span class="up">' + adv + "</span>"],
      ["DECLINES", '<span class="down">' + dec + "</span>"],
      ["BREADTH", breadth === "Positive"
        ? '<span class="up">' + breadth + "</span>"
        : '<span class="down">' + breadth + "</span>"],
      ["INDIA VIX", '<span class="mono">' + (vix.ltp ? inr(vix.ltp) : "\u2014") + "</span>"],
      ["ACTIVE ALERTS", '<span style="color:var(--gold)">' + d.alerts.length + "</span>"],
      ["FEED", d.mode === "live"
        ? '<span class="up">Angel One</span>'
        : '<span style="color:var(--gold)">Demo</span>']
    ];
    $("pulse").innerHTML = cells.map(function (c) {
      return '<div class="pulse-cell"><div class="k">' + c[0] + '</div><div class="v">' + c[1] + "</div></div>";
    }).join("");
    $("pulseUpdated").textContent = "updated " + d.updated;
  }

  function renderChartink(items) {
    $("ckCount").textContent = items.length ? items.length + " recent" : "";
    if (!items.length) {
      $("chartink").innerHTML =
        '<div class="row muted">Scanner webhook connect \u0B86\u0BA9\u0BA4\u0BC1\u0BAE\u0BCD ' +
        "LIVE JACKPOT SIGNALS \u0B87\u0B99\u0BCD\u0B95 \u0BB5\u0BB0\u0BC1\u0BAE\u0BCD 🚨</div>";
      return;
    }
    $("chartink").innerHTML = items.slice(0, 8).map(function (a) {
      var v = a.verdict || "WATCH";
      var badgeCls = v === "BUY" ? "BUY" : v === "SELL" ? "SELL" : "WATCH";
      var rs = (a.reasons || []).slice(0, 3).join(" \u00B7 ");
      var opt = "";
      if (a.option) {
        var o = a.option;
        opt = '<div class="sub" style="color:var(--gold)">\uD83C\uDFAF ' +
          esc(o.instrument) + " \u00B7 Entry " + esc(o.entry) +
          " \u00B7 T " + o.t1 + "/" + o.t2 + "/" + o.t3 + " \u00B7 SL " + o.sl +
          (o.prem_src === "est" ? " (est.)" : "") + "</div>";
      }
      return '<div class="row">' +
        '<span><span class="badge ' + badgeCls + '">' + esc(v) + "</span>" +
        ' <span class="sym" style="margin-left:8px">' + esc(a.symbol) + "</span>" +
        '<div class="sub">' + esc(a.scan) + (rs ? " \u2014 " + esc(rs) : "") + "</div>" + opt + "</span>" +
        '<span class="right"><span class="mono">' +
        (a.price ? "\u20B9" + esc(a.price) : "") + "</span>" +
        '<div class="sub">' + esc(a.time) + "</div></span></div>";
    }).join("");
  }

  function bkRow(x, up) {
    var lvl = up ? "PDH " + inr(x.pdh) : "PDL " + inr(x.pdl);
    return '<div class="row">' +
      "<span><span class=\"sym\">" + esc(x.symbol) + "</span>" +
      '<div class="sub">' + lvl + "</div></span>" +
      '<span class="right"><span class="mono">' + inr(x.ltp) + "</span><br>" +
      chgSpan(x.chg) + "</span></div>";
  }

  function renderScanner(s) {
    $("breakouts").innerHTML = s.breakouts.length
      ? s.breakouts.map(function (x) { return bkRow(x, true); }).join("")
      : '<div class="row muted">No PDH breaks yet</div>';
    $("breakdowns").innerHTML = s.breakdowns.length
      ? s.breakdowns.map(function (x) { return bkRow(x, false); }).join("")
      : '<div class="row muted">No PDL breaks yet</div>';
    $("conviction").innerHTML = s.conviction.length
      ? s.conviction.map(function (x) {
          return '<div class="row">' +
            "<span><span class=\"badge BUY\">" + x.score + "/100</span>" +
            ' <span class="sym" style="margin-left:8px">' + esc(x.symbol) + "</span>" +
            '<div class="sub">PDH break \u00B7 momentum \u00B7 volume confluence</div></span>' +
            '<span class="right"><span class="mono">' + inr(x.ltp) + "</span><br>" +
            chgSpan(x.chg) + "</span></div>";
        }).join("")
      : '<div class="row muted">Score \u2265 70 \u0BB5\u0BA8\u0BCD\u0BA4\u0BBE \u0BAE\u0B9F\u0BCD\u0B9F\u0BC1\u0BAE\u0BCD \u0B87\u0B99\u0BCD\u0B95 \u0BB5\u0BB0\u0BC1\u0BAE\u0BCD \u2014 quality over quantity.</div>';
  }

  function renderNews(items) {
    if (!items.length) {
      $("news").innerHTML = '<div class="row muted">Loading news…</div>';
      return;
    }
    $("news").innerHTML = items.slice(0, 10).map(function (n) {
      var cls = n.tag === "Positive" ? "up" : n.tag === "Negative" ? "down" : "muted";
      var stocks = (n.stocks || []).join(" \u00B7 ");
      return '<div class="row">' +
        '<span style="flex:1;padding-right:12px">' +
        '<a href="' + esc(n.link) + '" target="_blank" rel="noopener" ' +
        'style="color:inherit;text-decoration:none">' + esc(n.title) + "</a>" +
        '<div class="sub">' + esc(n.source) +
        (stocks ? " \u00B7 " + esc(stocks) : "") + "</div></span>" +
        '<span class="right"><span class="pill ' +
        (cls === "up" ? "up" : cls === "down" ? "down" : "") + '" style="' +
        (cls === "muted" ? "background:var(--panel-2);color:var(--dim)" : "") + '">' +
        esc(n.tag) + "</span>" +
        '<div class="sub mono">impact ' + n.impact + "/10</div></span></div>";
    }).join("");
  }

  /* ---------- v3: AI engine ---------- */

  function scoreColor(v) {
    return v >= 70 ? "var(--green)" : v >= 45 ? "var(--gold)" : "var(--red)";
  }
  function stars(n) {
    return '<span class="stars">' + "★".repeat(n) + "☆".repeat(5 - n) + "</span>";
  }

  function renderBestCall(bc, risk) {
    $("aiRisk").textContent = risk ? "Market Risk: " + risk : "";
    if (!bc || bc.status !== "CALL") {
      $("bestCall").innerHTML = '<div class="bc-empty">' +
        esc(bc && bc.note ? bc.note : "Waiting for AI signal…") + "</div>";
      return;
    }
    var timingCls = bc.timing.indexOf("BUY NOW") === 0 ? "now" : "wait";
    $("bestCall").innerHTML =
      '<div class="bc-top">' +
        '<span class="badge BUY">' + esc(bc.side) + "</span>" +
        '<span class="bc-sym">' + esc(bc.symbol) + "</span>" +
        '<span class="bc-conf"><div class="n">' + bc.confidence + '%</div><div class="k">CONFIDENCE</div></span>' +
      "</div>" +
      '<div class="bc-grid">' +
        '<div class="bc-cell"><div class="k">ENTRY</div><div class="v mono">' + inr(bc.entry) + "</div></div>" +
        '<div class="bc-cell"><div class="k">STOP LOSS</div><div class="v mono down">' + inr(bc.sl) + "</div></div>" +
        '<div class="bc-cell"><div class="k">TARGET 1</div><div class="v mono up">' + inr(bc.t1) + "</div></div>" +
        '<div class="bc-cell"><div class="k">TARGET 2</div><div class="v mono up">' + inr(bc.t2) + "</div></div>" +
        '<div class="bc-cell"><div class="k">TARGET 3</div><div class="v mono up">' + inr(bc.t3) + "</div></div>" +
        '<div class="bc-cell"><div class="k">TRADE RISK</div><div class="v">' +
          stars(bc.risk === "LOW" ? 5 : bc.risk === "MEDIUM" ? 3 : 2) + "</div></div>" +
      "</div>" +
      '<div class="bc-reasons">' + bc.reasons.map(function (r) {
        return '<span class="chip">✔ ' + esc(r) + "</span>";
      }).join("") + "</div>" +
      '<div class="bc-timing"><span class="timing-pill ' + timingCls + '">' +
        esc(bc.timing) + '</span><span class="muted mini mono">probability ' +
        bc.timing_prob + "%</span></div>";
  }

  function renderAiScores(list) {
    $("aiScores").innerHTML = list.slice(0, 8).map(function (s) {
      return '<div class="row"><span style="flex:1">' +
        '<span class="sym">' + esc(s.symbol) + "</span>" +
        '<span class="muted mini" style="margin-left:8px">RSI ' + s.rsi +
        " \u00B7 RVol " + s.rvol + "x</span>" +
        '<div class="scorebar"><div style="width:' + s.score +
        "%;background:" + scoreColor(s.score) + '"></div></div></span>' +
        '<span class="right" style="min-width:74px">' +
        '<span class="mono" style="font-weight:900;color:' + scoreColor(s.score) + '">' +
        s.score + "/100</span><br>" + chgSpan(s.chg) + "</span></div>";
    }).join("");
  }

  function renderRvol(list) {
    $("rvol").innerHTML = list.length ? list.map(function (s) {
      return '<div class="row"><span class="sym">' + esc(s.symbol) + "</span>" +
        '<span class="right"><span class="mono" style="color:var(--gold);font-weight:900">' +
        s.rvol + "x</span><br>" + chgSpan(s.chg) + "</span></div>";
    }).join("") : '<div class="row muted">RVol \u2265 1.2x stocks \u0B87\u0BB2\u0BCD\u0BB2</div>';
  }

  function renderSectors(list) {
    $("sectors").innerHTML = list.map(function (s) {
      return '<div class="row"><span class="sym">' + esc(s.sector) + "</span>" +
        '<span class="right">' + stars(s.stars) + "<br>" + chgSpan(s.avg) + "</span></div>";
    }).join("");
  }

  function renderRadar(list) {
    $("radar").innerHTML = list.length ? list.map(function (s, i) {
      return '<div class="row"><span><span class="badge BUY">#' + (i + 1) + "</span>" +
        ' <span class="sym" style="margin-left:8px">' + esc(s.symbol) + "</span>" +
        '<div class="sub">' + esc((s.reasons || []).slice(0, 3).join(" \u00B7 ")) + "</div></span>" +
        '<span class="mono right" style="font-weight:900;color:var(--gold)">' +
        s.score + "%</span></div>";
    }).join("") : '<div class="row muted">Score \u2265 80 setups \u0B87\u0BAA\u0BCD\u0BAA \u0B87\u0BB2\u0BCD\u0BB2 \u2014 patience.</div>';
  }

  function loadAI() {
    fetch("/api/ai")
      .then(function (r) { return r.json(); })
      .then(function (a) {
        if (a.error) return;
        renderBestCall(a.best_call, a.risk_market);
        renderAiScores(a.scores || []);
        renderRvol(a.rvol || []);
        renderSectors(a.sectors || []);
        renderRadar(a.radar || []);
      })
      .catch(function () {});
  }

  /* ---------- main loops ---------- */

  function load() {
    fetch("/api/dashboard")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.error) throw new Error(d.error);
        renderConn(d.mode, d.updated);
        renderTicker(d.indices);
        renderIndices(d.indices);
        renderLists(d);
        renderAlerts(d.alerts);
        renderChartink(d.chartink || []);
        renderPulse(d);
      })
      .catch(function (e) {
        $("connDot").className = "dot err";
        $("connText").textContent = "ERROR";
        $("alerts").innerHTML =
          '<div class="err-box">Server error: ' + esc(e.message) +
          "<br>Render \u2192 Logs tab check \u0BAA\u0BA3\u0BCD\u0BA3\u0BC1\u0B99\u0BCD\u0B95.</div>";
      });
  }

  function loadScanner() {
    fetch("/api/scanner")
      .then(function (r) { return r.json(); })
      .then(function (s) { if (!s.error) renderScanner(s); })
      .catch(function () {});
  }

  function renderNewsSignals(list) {
    $("newsSignals").innerHTML = list.length ? list.map(function (s) {
      var good = s.verdict.indexOf("CALL-WORTHY") === 0;
      return '<div class="row"><span style="flex:1;padding-right:10px">' +
        '<span class="badge ' + (good ? "BUY" : "WATCH") + '">' +
        (good ? "CALL-WORTHY" : "WAIT") + "</span>" +
        ' <span class="sym" style="margin-left:8px">' + esc(s.symbol) + "</span>" +
        '<div class="sub">' + esc(s.headline) + "</div></span>" +
        '<span class="right"><span class="mono" style="color:var(--gold);font-weight:900">' +
        s.score + "/100</span><br>" + chgSpan(s.chg) + "</span></div>";
    }).join("") :
      '<div class="row muted">High-impact positive news + AI confirm \u0BB5\u0BA8\u0BCD\u0BA4\u0BBE \u0B87\u0B99\u0BCD\u0B95 \u0BB5\u0BB0\u0BC1\u0BAE\u0BCD \u26A1</div>';
  }

  function loadNews() {
    fetch("/api/news")
      .then(function (r) { return r.json(); })
      .then(function (n) {
        renderNews(n.items || []);
        renderNewsSignals(n.signals || []);
      })
      .catch(function () {});
  }

  load();
  loadScanner();
  loadNews();
  loadAI();
  setInterval(load, REFRESH_MS);
  setInterval(loadScanner, 15000);   // scanner: 15s
  setInterval(loadNews, 45000);      // news: 45s
  setInterval(loadAI, 20000);        // AI engine: 20s
})();
