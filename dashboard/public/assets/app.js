/* PSX Engine Dashboard — app orchestration (TICKET-U1/U3/U4/U5/U6/U7)
 * Data source: one function getSymbolPayload(sym) — fixture now, live API at integration (flip DEV_FIXTURES).
 */
(function () {
  "use strict";

  // ---------------------------------------------------------------------
  // Data source switch (PLAN §12.1 fixture-first). Flip to false at D4 integration.
  // ---------------------------------------------------------------------
  var DEV_FIXTURES = false; // flipped at D4 integration 2026-07-03 — live API is the source
  var FIXTURE_SYMBOLS = ["OGDC", "EFERT", "LUCK", "ABL"];
  var FIXTURE_MAP = {
    // Frontend dev-copy under public/ so the built-in PHP server (docroot-bound) can serve it.
    // Source of truth stays in ../fixtures/ (Lead-owned); keep both in sync until D4 flips the flag.
    OGDC: "fixtures/symbol_OGDC.json",
    EFERT: "fixtures/symbol_EFERT.json"
  };

  function getSymbolPayload(sym) {
    sym = (sym || "").toUpperCase();
    if (DEV_FIXTURES) {
      var path = FIXTURE_MAP[sym];
      if (!path) {
        // Symbol not in our small fixture set — synthesize a not-found payload,
        // matching the live contract's `found:false` shape (PLAN §6.2).
        return Promise.resolve({ meta: { ticker: sym, found: false } });
      }
      return fetchJson(path);
    }
    return fetchJson("api/symbol.php?sym=" + encodeURIComponent(sym));
  }

  function getSearchResults(query) {
    query = (query || "").trim();
    if (query.length < 2) return Promise.resolve([]);
    if (DEV_FIXTURES) {
      var names = {
        OGDC: "Oil & Gas Development Company Limited",
        EFERT: "Engro Fertilizers Limited",
        LUCK: "Lucky Cement Limited",
        ABL: "Allied Bank Limited"
      };
      var q = query.toUpperCase();
      var prefix = [];
      var substr = [];
      FIXTURE_SYMBOLS.forEach(function (t) {
        var name = names[t] || t;
        if (t.indexOf(q) === 0) prefix.push({ ticker: t, name: name });
        else if (t.indexOf(q) > -1 || name.toUpperCase().indexOf(q) > -1) substr.push({ ticker: t, name: name });
      });
      return Promise.resolve(prefix.concat(substr).slice(0, 10));
    }
    return fetchJson("api/search.php?q=" + encodeURIComponent(query));
  }

  function fetchJson(url) {
    return fetch(url, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("http_" + res.status);
      return res.json();
    });
  }

  // ---------------------------------------------------------------------
  // DOM refs
  // ---------------------------------------------------------------------
  var el = {
    searchInput: document.getElementById("search-input"),
    searchResults: document.getElementById("search-results"),
    asOf: document.getElementById("as-of"),
    banner: document.getElementById("freshness-banner"),
    bannerText: document.getElementById("freshness-banner-text"),
    main: document.getElementById("app-main"),
    landing: document.getElementById("landing"),
    footerStat: document.getElementById("footer-engine-stat")
  };

  var state = {
    activeIndex: -1,
    results: [],
    debounceTimer: null
  };

  // ---------------------------------------------------------------------
  // Search / typeahead (U1)
  // ---------------------------------------------------------------------
  el.searchInput.addEventListener("input", function () {
    clearTimeout(state.debounceTimer);
    var q = el.searchInput.value;
    state.debounceTimer = setTimeout(function () {
      getSearchResults(q).then(renderResults);
    }, 150);
  });

  el.searchInput.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      moveActive(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      moveActive(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      var pick = state.results[state.activeIndex] || state.results[0];
      if (pick) selectSymbol(pick.ticker);
    } else if (e.key === "Escape") {
      closeResults();
    }
  });

  document.addEventListener("click", function (e) {
    if (!el.searchResults.contains(e.target) && e.target !== el.searchInput) {
      closeResults();
    }
  });

  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      selectSymbol(chip.getAttribute("data-symbol"));
    });
  });

  function moveActive(delta) {
    if (!state.results.length) return;
    state.activeIndex = Math.max(0, Math.min(state.results.length - 1, state.activeIndex + delta));
    renderResults(state.results);
  }

  function renderResults(results) {
    state.results = results || [];
    if (state.activeIndex >= state.results.length) state.activeIndex = -1;
    el.searchResults.innerHTML = "";
    if (!state.results.length) {
      closeResults();
      return;
    }
    state.results.forEach(function (r, i) {
      var item = document.createElement("div");
      item.className = "search-result-item" + (i === state.activeIndex ? " active" : "");
      item.setAttribute("role", "option");
      item.innerHTML =
        '<span class="ticker">' + escapeHtml(r.ticker) + "</span>" +
        '<span class="name">' + escapeHtml(r.name || "") + "</span>";
      item.addEventListener("mousedown", function (e) {
        e.preventDefault();
        selectSymbol(r.ticker);
      });
      el.searchResults.appendChild(item);
    });
    openResults();
  }

  function openResults() {
    el.searchResults.classList.add("open");
    el.searchInput.setAttribute("aria-expanded", "true");
  }
  function closeResults() {
    el.searchResults.classList.remove("open");
    el.searchInput.setAttribute("aria-expanded", "false");
    state.activeIndex = -1;
  }

  function selectSymbol(ticker) {
    ticker = (ticker || "").toUpperCase();
    if (!ticker) return;
    closeResults();
    el.searchInput.value = ticker;
    window.location.hash = ticker;
  }

  // ---------------------------------------------------------------------
  // Routing (URL hash = deep link / refresh-safe, PLAN §7.2)
  // ---------------------------------------------------------------------
  window.addEventListener("hashchange", loadFromHash);

  function loadFromHash() {
    var sym = window.location.hash.replace(/^#/, "").toUpperCase();
    if (!sym) {
      showLanding();
      return;
    }
    loadSymbol(sym);
  }

  function showLanding() {
    el.landing.style.display = "flex";
    el.main.classList.remove("show");
    el.banner.classList.remove("show");
    el.asOf.textContent = "";
  }

  // ---------------------------------------------------------------------
  // Symbol load + render
  // ---------------------------------------------------------------------
  function loadSymbol(sym) {
    el.landing.style.display = "none";
    renderSkeleton();
    el.main.classList.add("show");

    getSymbolPayload(sym)
      .then(function (payload) {
        renderPayload(sym, payload);
      })
      .catch(function (err) {
        renderDataError(sym, err);
      });
  }

  function renderSkeleton() {
    el.main.innerHTML =
      '<div class="panel signal-banner">' +
        skeletonLines(2) +
      "</div>" +
      '<div class="layout-grid">' +
        '<div class="layout-main"><div class="panel chart-panel">' + skeletonBlock(420) + "</div></div>" +
        '<div class="layout-side">' +
          '<div class="panel">' + skeletonLines(4) + "</div>" +
          '<div class="panel">' + skeletonLines(3) + "</div>" +
        "</div>" +
      "</div>" +
      '<div class="panel">' + skeletonLines(4) + "</div>";
    el.banner.classList.remove("show");
    el.asOf.textContent = "";
  }

  function skeletonLines(n) {
    var out = "";
    for (var i = 0; i < n; i++) out += '<div class="skeleton skeleton-line" style="width:' + (90 - i * 12) + '%"></div>';
    return out;
  }
  function skeletonBlock(h) {
    return '<div class="skeleton skeleton-block" style="height:' + h + 'px"></div>';
  }

  function renderDataError(sym, err) {
    el.main.innerHTML =
      '<div class="data-error">Could not load data for ' + escapeHtml(sym) + ". Try again or pick another symbol.</div>";
  }

  function renderPayload(sym, payload) {
    var meta = payload.meta || { ticker: sym, found: false };

    if (!meta.found) {
      renderNotFound(sym);
      return;
    }

    el.asOf.textContent = "as of " + (meta.as_of || "–");

    // Freshness banner (G3)
    if (meta.warnings && meta.warnings.length) {
      el.bannerText.textContent = meta.warnings.join(" • ");
      el.banner.classList.add("show");
    } else {
      el.banner.classList.remove("show");
    }

    el.main.innerHTML =
      '<div id="signal-banner-panel"></div>' +
      '<div class="layout-grid">' +
        '<div class="layout-main"><div id="chart-panel" class="panel chart-panel"></div></div>' +
        '<div class="layout-side">' +
          '<div class="side-two-col">' +
            '<div id="fundamentals-panel" class="panel"></div>' +
            '<div id="news-panel" class="panel"></div>' +
          "</div>" +
        "</div>" +
      "</div>" +
      '<div id="history-panel" class="panel"></div>';

    renderSignalBanner(meta, payload.signal, payload.filings);
    renderFundamentals(payload.fundamentals);
    renderNews(payload.news);
    renderHistory(payload.history);
    renderFooterStat();

    if (window.PSXChart && payload.ohlc) {
      window.PSXChart.render(document.getElementById("chart-panel"), payload);
    } else if (document.getElementById("chart-panel")) {
      document.getElementById("chart-panel").innerHTML = '<div class="empty-state">Chart data unavailable.</div>';
    }
  }

  function renderNotFound(sym) {
    el.banner.classList.remove("show");
    el.asOf.textContent = "";
    el.main.innerHTML =
      '<div class="panel"><div class="empty-state">No engine data found for "' +
      escapeHtml(sym) +
      '". Check the ticker or try one of: OGDC, EFERT, LUCK, ABL.</div></div>';
  }

  // ---------------------------------------------------------------------
  // U3 — Signal banner + STALE + glossary
  // ---------------------------------------------------------------------
  var FACTOR_GLOSSARY = {
    trend: "Trend — where price sits relative to its moving averages (uptrend/downtrend strength).",
    rsi: "RSI — momentum gauge; high = overheated (may pull back), low = beaten down (may bounce).",
    "52w": "52-week position — how close price is to its 1-year high/low.",
    pos52w: "52-week position — how close price is to its 1-year high/low.",
    mom20: "20-day momentum — recent short-term price direction.",
    eps: "EPS trend — is reported earnings per share rising, flat, or falling.",
    yield: "Dividend yield — annualized cash payout relative to price.",
    rules: "Rule-scorecard bonus/penalty from the engine's transparent rulebook."
  };

  function renderSignalBanner(meta, signal, filings) {
    var host = document.getElementById("signal-banner-panel");
    if (!signal) {
      host.innerHTML = '<div class="panel signal-banner"><div class="empty-state">No signal available for this symbol.</div></div>';
      return;
    }
    var sigClass = (signal.signal || "").toLowerCase();
    var pips = pipString(signal.conviction);
    var stale = isStale(signal, filings);

    host.innerHTML =
      '<div class="panel signal-banner">' +
        '<div class="top-row">' +
          '<span class="ticker">' + escapeHtml(meta.ticker) + "</span>" +
          '<span class="name">' + escapeHtml(meta.name || "") + "</span>" +
          '<span class="signal-chip ' + sigClass + '">' + escapeHtml(signal.signal || "–") + "</span>" +
          '<span class="conviction-pips" title="Conviction ' + (signal.conviction || 0) + '/3">' +
            pips + " " + (signal.conviction || 0) + "/3" +
          "</span>" +
          (stale ? '<a class="stale-chip" href="#" title="Open filing needs review">&#9888; STALE — open filing</a>' : "") +
        "</div>" +
        '<div class="stats-row tabular">' +
          "<span>close <b>" + fmtNum(signal.close) + "</b></span>" +
          "<span>RSI <b>" + fmtNum(signal.rsi, 1) + "</b></span>" +
          "<span>yield <b>" + fmtNum(signal.yield_pct, 1) + "%</b></span>" +
          "<span>pos52w <b>" + fmtNum(signal.pos52, 1) + "%</b></span>" +
        "</div>" +
        '<div class="why-row">' +
          '<span>why: ' + escapeHtml(signal.why || "–") + "</span>" +
          '<button class="glossary-btn" id="glossary-btn" aria-haspopup="true" aria-expanded="false" title="Factor glossary">i</button>' +
          '<div id="glossary-popover" class="glossary-popover" role="tooltip"><dl>' + glossaryHtml() + "</dl></div>" +
        "</div>" +
      "</div>";

    var btn = document.getElementById("glossary-btn");
    var pop = document.getElementById("glossary-popover");
    function toggle(open) {
      pop.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    }
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggle(!pop.classList.contains("open"));
    });
    btn.addEventListener("keydown", function (e) {
      if (e.key === "Escape") toggle(false);
    });
    document.addEventListener("click", function (e) {
      if (!pop.contains(e.target) && e.target !== btn) toggle(false);
    });
  }

  function glossaryHtml() {
    var out = "";
    var order = ["trend", "rsi", "pos52w", "mom20", "eps", "yield", "rules"];
    order.forEach(function (k) {
      out += "<dt>" + k + "</dt><dd>" + FACTOR_GLOSSARY[k] + "</dd>";
    });
    return out;
  }

  function isStale(signal, filings) {
    if (signal.diligence && signal.diligence !== "OK") return true;
    if (filings && filings.some(function (f) { return f.materiality === "MATERIAL" && !f.reviewed; })) return true;
    return false;
  }

  function pipString(conviction) {
    conviction = conviction || 0;
    var full = "●".repeat(Math.max(0, Math.min(3, conviction)));
    var empty = "○".repeat(Math.max(0, 3 - conviction));
    return full + empty;
  }

  // ---------------------------------------------------------------------
  // U4 — Fundamentals panel
  // ---------------------------------------------------------------------
  function renderFundamentals(f) {
    var host = document.getElementById("fundamentals-panel");
    if (!f) {
      host.innerHTML = "<h3>Fundamentals</h3>" + '<div class="empty-state">No fundamentals data for this symbol.</div>';
      return;
    }
    var payouts = (f.payouts || []).slice(0, 6).map(function (p) {
      return "<li><span>" + fmtNum(p.pct, 1) + "% (" + escapeHtml(p.interim_label || "") + ")</span><b>" + escapeHtml(exDateOnly(p.ex_or_bc)) + "</b></li>";
    }).join("");
    var quarterly = (f.quarterly_results || []).slice(0, 4).map(function (q) {
      return "<li><span>" + escapeHtml(q.period_type || "") + " " + escapeHtml(q.period || "") + "</span><b>EPS " + fmtNum(q.eps, 2) + "</b></li>";
    }).join("");

    host.innerHTML =
      "<h3>Fundamentals</h3>" +
      '<div class="fund-eps tabular">' + fmtNum(f.latest_eps, 2) + "</div>" +
      '<div class="fund-period">' + escapeHtml(f.latest_period || "") + "</div>" +
      '<div class="fund-trend">trend: ' + escapeHtml(f.eps_trend || "unknown") + "</div>" +
      (quarterly ? '<ul class="quarterly-list">' + quarterly + "</ul>" : "") +
      (payouts ? '<ul class="payout-list">' + payouts + "</ul>" : '<div class="empty-state">No payout history.</div>');
  }

  // parse "dd/mm/yyyy  - dd/mm/yyyy" -> first date, dd/mm/yyyy (already that format)
  function exDateOnly(range) {
    if (!range) return "–";
    return range.split("-")[0].trim();
  }

  // ---------------------------------------------------------------------
  // U5 — News panel
  // ---------------------------------------------------------------------
  function renderNews(news) {
    var host = document.getElementById("news-panel");
    if (!news || !news.length) {
      host.innerHTML = "<h3>News</h3>" + '<div class="empty-state">No relevant news for this symbol.</div>';
      return;
    }
    var items = news.map(function (n) {
      var tag = n.match === "macro" ? '<span class="macro-tag">market-wide</span>' : "";
      return (
        '<li class="news-item">' +
          '<div class="headline">' + escapeHtml(n.headline || "") + "</div>" +
          (n.impact ? '<div class="impact">' + escapeHtml(n.impact) + "</div>" : "") +
          '<div class="meta"><span>' + escapeHtml(n.source || "") + "</span><span>" + escapeHtml(n.date || "") + "</span>" + tag + "</div>" +
        "</li>"
      );
    }).join("");
    host.innerHTML = "<h3>News</h3>" + '<ul class="news-list">' + items + "</ul>";
  }

  // ---------------------------------------------------------------------
  // U6 — Signal history table
  // ---------------------------------------------------------------------
  function renderHistory(history) {
    var host = document.getElementById("history-panel");
    if (!history || !history.length) {
      host.innerHTML = "<h3>Signal History</h3>" + '<div class="empty-state">No signal history yet for this symbol.</div>';
      return;
    }
    var rows = history.map(function (h) {
      var badge = resultBadge(h);
      var title = h.result_detail ? ' title="' + escapeAttr(h.result_detail) + '"' : "";
      return (
        "<tr" + title + ">" +
          "<td>" + escapeHtml(h.date) + "</td>" +
          "<td>" + escapeHtml(h.signal) + "</td>" +
          "<td>" + badge + "</td>" +
          '<td class="why-cell">' + escapeHtml(h.why || "") + "</td>" +
        "</tr>"
      );
    }).join("");
    host.innerHTML =
      "<h3>Signal History</h3>" +
      '<table class="history-table"><thead><tr><th>Date</th><th>Signal</th><th>Result</th><th>Why</th></tr></thead><tbody>' +
      rows +
      "</tbody></table>";
  }

  function resultBadge(h) {
    if (h.result === "HIT") return '<span class="result-badge hit">&#10003; HIT</span>';
    if (h.result === "MISS") return '<span class="result-badge miss">&#10007; MISS</span>';
    return '<span class="result-badge pending">&#8987; PENDING' + (h.grade_on_date ? " (" + escapeHtml(h.grade_on_date) + ")" : "") + "</span>";
  }

  // ---------------------------------------------------------------------
  // U7 — Footer engine stat (optional, absent gracefully — no rolling_stats in fixtures)
  // ---------------------------------------------------------------------
  function renderFooterStat() {
    // Fixtures carry no rolling_stats.json equivalent; render nothing (graceful absence).
    // Live integration: fetch rolling_stats via payload or a small endpoint and populate here.
    el.footerStat.textContent = "";
  }

  // ---------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------
  function fmtNum(v, digits) {
    if (v === null || v === undefined || Number.isNaN(v)) return "–";
    return Number(v).toFixed(digits === undefined ? 2 : digits);
  }
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function escapeAttr(s) {
    return escapeHtml(s);
  }

  // ---------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------
  loadFromHash();
})();
