/* PSX Engine Dashboard — candlestick chart (TICKET-U2 + U8, PLAN §7.4)
 * Simple mode (default): plain-language MAs, trend sentence, volume+heavy-day,
 * floor/ceiling, 52w band, RSI heat chip, ATR typical-move caption, dividend markers.
 * Analyst mode (toggle, localStorage): RSI subchart + Bollinger(20,2). No MACD.
 * U8: past-signal markers (▲ BUY / ▼ SELL / ◆ HOLD, colored by outcome), toggleable.
 */
(function () {
  "use strict";

  var LS_KEY = "psx_dashboard_chart_mode";
  var LS_KEY_MARKERS = "psx_dashboard_signal_markers";
  var RANGE_DAYS = { "6M": 126, "1Y": 252, "2Y": 504, Max: Infinity };

  function render(container, payload) {
    var ohlc = payload.ohlc || [];
    var signal = payload.signal || {};
    var fundamentals = payload.fundamentals || {};
    var history = payload.history || [];

    var mode = localStorage.getItem(LS_KEY) === "analyst" ? "analyst" : "simple";
    // Signal markers default ON; "off" is the only persisted opt-out value.
    var showMarkers = localStorage.getItem(LS_KEY_MARKERS) !== "off";
    var range = "1Y";

    container.innerHTML = buildShell();

    var canvasEl = container.querySelector("#chart-canvas");
    var chart = echarts.init(canvasEl, null, { renderer: "canvas" });

    var derived = computeDerived(ohlc);

    function paint() {
      var sliced = sliceRange(ohlc, range);
      var opts = buildOption(sliced, derived, signal, fundamentals, mode, showMarkers ? history : null);
      chart.setOption(opts, true);
      canvasEl.classList.toggle("tall", mode === "analyst");
      chart.resize();
      updateTrendSummary(container, derived, signal);
      updateRsiChip(container, signal.rsi);
      updateCaptions(container, derived, signal);
    }

    // Range toggle buttons
    container.querySelectorAll(".range-toggles button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        range = btn.getAttribute("data-range");
        container.querySelectorAll(".range-toggles button").forEach(function (b) {
          b.classList.toggle("active", b === btn);
        });
        paint();
      });
      if (btn.getAttribute("data-range") === range) btn.classList.add("active");
    });

    // Analyst mode toggle
    var modeToggle = container.querySelector("#mode-toggle-checkbox");
    modeToggle.checked = mode === "analyst";
    modeToggle.addEventListener("change", function () {
      mode = modeToggle.checked ? "analyst" : "simple";
      localStorage.setItem(LS_KEY, mode);
      paint();
    });

    // Signal-markers toggle (U8)
    var markersToggle = container.querySelector("#markers-toggle-checkbox");
    markersToggle.checked = showMarkers;
    markersToggle.addEventListener("change", function () {
      showMarkers = markersToggle.checked;
      localStorage.setItem(LS_KEY_MARKERS, showMarkers ? "on" : "off");
      paint();
    });

    window.addEventListener("resize", function () {
      chart.resize();
    });

    paint();
  }

  function buildShell() {
    return (
      '<div class="chart-header">' +
        '<h3 style="margin:0">Candlestick</h3>' +
        '<span id="rsi-chip" class="rsi-chip">RSI –</span>' +
      "</div>" +
      '<div id="trend-summary" class="trend-summary"></div>' +
      '<div id="chart-canvas"></div>' +
      '<div class="chart-toolbar">' +
        '<div class="range-toggles">' +
          '<button data-range="6M">6M</button>' +
          '<button data-range="1Y">1Y</button>' +
          '<button data-range="2Y">2Y</button>' +
          '<button data-range="Max">Max</button>' +
        "</div>" +
        '<label class="mode-toggle"><input type="checkbox" id="markers-toggle-checkbox"> Signal markers</label>' +
        '<label class="mode-toggle"><input type="checkbox" id="mode-toggle-checkbox"> Analyst mode</label>' +
      "</div>" +
      '<div id="chart-captions" class="chart-captions"></div>'
    );
  }

  // -----------------------------------------------------------------------
  // Derived series: MA20/50/200, 52w band, ATR(14), Bollinger(20,2)
  // -----------------------------------------------------------------------
  function computeDerived(ohlc) {
    var closes = ohlc.map(function (b) { return b.c; });
    var dates = ohlc.map(function (b) { return b.date; });
    var vols = ohlc.map(function (b) { return b.v; });

    var ma20 = sma(closes, 20);
    var ma50 = sma(closes, 50);
    var ma200 = sma(closes, 200);
    var vol20 = sma(vols, 20);
    var atr14 = atr(ohlc, 14);
    var boll = bollinger(closes, 20, 2);
    var rsi14 = rsiSeries(closes, 14);

    var window52 = ohlc.slice(Math.max(0, ohlc.length - 252));
    var hi52 = window52.length ? Math.max.apply(null, window52.map(function (b) { return b.h; })) : null;
    var lo52 = window52.length ? Math.min.apply(null, window52.map(function (b) { return b.l; })) : null;

    return {
      dates: dates, closes: closes, vols: vols,
      ma20: ma20, ma50: ma50, ma200: ma200,
      vol20: vol20, atr14: atr14, boll: boll, rsi14: rsi14,
      hi52: hi52, lo52: lo52
    };
  }

  function sma(arr, period) {
    var out = new Array(arr.length).fill(null);
    var sum = 0;
    for (var i = 0; i < arr.length; i++) {
      var v = arr[i];
      sum += (typeof v === "number" ? v : 0);
      if (i >= period) sum -= (typeof arr[i - period] === "number" ? arr[i - period] : 0);
      if (i >= period - 1) out[i] = round2(sum / period);
    }
    return out;
  }

  function atr(ohlc, period) {
    var trs = ohlc.map(function (b, i) {
      if (i === 0) return b.h - b.l;
      var prevClose = ohlc[i - 1].c;
      return Math.max(b.h - b.l, Math.abs(b.h - prevClose), Math.abs(b.l - prevClose));
    });
    return sma(trs, period);
  }

  function bollinger(closes, period, mult) {
    var mid = sma(closes, period);
    var upper = new Array(closes.length).fill(null);
    var lower = new Array(closes.length).fill(null);
    for (var i = period - 1; i < closes.length; i++) {
      var slice = closes.slice(i - period + 1, i + 1);
      var mean = mid[i];
      var variance = slice.reduce(function (acc, v) { return acc + Math.pow(v - mean, 2); }, 0) / period;
      var sd = Math.sqrt(variance);
      upper[i] = round2(mean + mult * sd);
      lower[i] = round2(mean - mult * sd);
    }
    return { mid: mid, upper: upper, lower: lower };
  }

  function rsiSeries(closes, period) {
    return wilderRsi(closes, period);
  }

  function wilderRsi(closes, period) {
    var out = new Array(closes.length).fill(null);
    if (closes.length <= period) return out;
    var gains = 0, losses = 0;
    for (var i = 1; i <= period; i++) {
      var ch = closes[i] - closes[i - 1];
      gains += Math.max(0, ch);
      losses += Math.max(0, -ch);
    }
    var avgG = gains / period, avgL = losses / period;
    out[period] = rsiFromAvg(avgG, avgL);
    for (var j = period + 1; j < closes.length; j++) {
      var change = closes[j] - closes[j - 1];
      var g = Math.max(0, change), l = Math.max(0, -change);
      avgG = (avgG * (period - 1) + g) / period;
      avgL = (avgL * (period - 1) + l) / period;
      out[j] = rsiFromAvg(avgG, avgL);
    }
    return out;
  }

  function rsiFromAvg(avgG, avgL) {
    if (avgL === 0) return 100;
    var rs = avgG / avgL;
    return round2(100 - 100 / (1 + rs));
  }

  function round2(v) { return Math.round(v * 100) / 100; }

  // -----------------------------------------------------------------------
  // Range slicing (client-side, no refetch)
  // -----------------------------------------------------------------------
  function sliceRange(ohlc, range) {
    var n = RANGE_DAYS[range];
    if (!isFinite(n)) return { data: ohlc, offset: 0 };
    var start = Math.max(0, ohlc.length - n);
    return { data: ohlc.slice(start), offset: start };
  }

  // -----------------------------------------------------------------------
  // ECharts option builder
  // -----------------------------------------------------------------------
  function buildOption(sliced, derived, signal, fundamentals, mode, history) {
    var data = sliced.data;
    var offset = sliced.offset;
    var dates = data.map(function (b) { return b.date; });
    var candleData = data.map(function (b) { return [b.o, b.c, b.l, b.h]; });

    function sub(arr) { return arr.slice(offset, offset + data.length); }

    var ma20 = sub(derived.ma20), ma50 = sub(derived.ma50), ma200 = sub(derived.ma200);
    var vol20 = sub(derived.vol20);
    var boll = { upper: sub(derived.boll.upper), lower: sub(derived.boll.lower), mid: sub(derived.boll.mid) };
    var rsi14 = sub(derived.rsi14);

    var heavyDayMarks = [];
    data.forEach(function (b, i) {
      var avg = vol20[i];
      if (avg && b.v >= 2 * avg) {
        heavyDayMarks.push({
          name: "heavy",
          xAxis: b.date,
          yAxis: b.h,
          value: "heavy trading — " + (b.v / avg).toFixed(1) + "x normal",
          label: { show: false }
        });
      }
    });

    var dividendMarks = buildDividendMarks(fundamentals, dates, data);
    var signalMarkerSeries = history ? buildSignalMarkerSeries(history, dates, data) : null;

    var grids, xAxes, yAxes, series;

    var supportVal = signal.support;
    var resistanceVal = signal.resistance;

    var candleSeries = {
      name: "Price",
      type: "candlestick",
      data: candleData,
      clip: false,
      itemStyle: {
        color: colorUp(),
        color0: colorDown(),
        borderColor: colorUp(),
        borderColor0: colorDown()
      },
      markLine: {
        symbol: "none",
        silent: true,
        label: { formatter: markLineLabel, position: "insideEndTop", distance: 4, align: "right", color: "#aab3c5" },
        lineStyle: { type: "dashed" },
        data: [
          supportVal != null ? { yAxis: supportVal, name: "floor", lineStyle: { color: "#2fbf71" } } : null,
          resistanceVal != null ? { yAxis: resistanceVal, name: "ceiling", lineStyle: { color: "#e0555e" } } : null
        ].filter(Boolean)
      },
      markPoint: {
        data: dividendMarks,
        label: { formatter: "💰", fontSize: 12, color: "#000" },
        tooltip: { formatter: function (p) { return p.data.value; } }
      }
    };

    var maSeries = [
      lineSeries("1-month trend (MA20)", ma20, "#4c8dff"),
      lineSeries("3-month trend (MA50)", ma50, "#c88bff"),
      lineSeries("long-term trend (MA200)", ma200, "#d8a441")
    ];

    var bandSeries = {
      name: "52w range",
      type: "line",
      data: dates.map(function () { return derived.hi52; }),
      lineStyle: { opacity: 0 },
      areaStyle: { color: "rgba(255,255,255,0.04)" },
      stack: "band",
      symbol: "none",
      silent: true,
      z: 0
    };
    var bandBase = {
      name: "52w range base",
      type: "line",
      data: dates.map(function () { return derived.lo52; }),
      lineStyle: { opacity: 0 },
      symbol: "none",
      silent: true,
      z: 0,
      tooltip: { show: false }
    };

    var volumeSeries = {
      name: "Volume",
      type: "bar",
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: data.map(function (b) {
        return { value: b.v, itemStyle: { color: b.c >= b.o ? colorUp() : colorDown() } };
      }),
      markPoint: {
        symbol: "circle",
        symbolSize: 6,
        label: { show: false },
        data: heavyDayMarks,
        tooltip: {
          formatter: function (p) { return p.data.value; }
        }
      }
    };

    var vol20Series = lineSeriesRaw("20-day avg volume", vol20, "#6f7889", 1, 1);

    if (mode === "analyst") {
      grids = [
        { left: 55, right: 30, top: 20, height: "42%" },
        { left: 55, right: 30, top: "50%", height: "14%" },
        { left: 55, right: 30, top: "68%", height: "16%" }
      ];
      xAxes = [
        catAxis(dates, 0, false),
        catAxis(dates, 1, false),
        catAxis(dates, 2, true)
      ];
      yAxes = [
        valAxis(0),
        valAxis(1, true),
        { gridIndex: 2, min: 0, max: 100, splitNumber: 2, axisLine: { show: false }, splitLine: { show: false } }
      ];
      var rsiSeries14 = {
        name: "RSI(14)",
        type: "line",
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: rsi14,
        showSymbol: false,
        lineStyle: { color: "#4c8dff", width: 1.5 },
        markLine: {
          symbol: "none",
          silent: true,
          lineStyle: { type: "dotted", color: "#6f7889" },
          data: [{ yAxis: 30 }, { yAxis: 70 }]
        }
      };
      series = [
        candleSeries, bandSeries, bandBase
      ].concat(maSeries).concat([
        lineSeriesRaw("Bollinger upper", boll.upper, "#6f7889", 0, 0, true),
        lineSeriesRaw("Bollinger lower", boll.lower, "#6f7889", 0, 0, true),
        volumeSeries, vol20Series, rsiSeries14
      ]);
    } else {
      grids = [
        { left: 55, right: 30, top: 20, height: "56%" },
        { left: 55, right: 30, top: "70%", height: "16%" }
      ];
      xAxes = [
        catAxis(dates, 0, false),
        catAxis(dates, 1, true)
      ];
      yAxes = [valAxis(0), valAxis(1, true)];
      series = [candleSeries, bandSeries, bandBase].concat(maSeries).concat([volumeSeries, vol20Series]);
    }

    if (signalMarkerSeries) series.push(signalMarkerSeries);

    return {
      backgroundColor: "transparent",
      animation: false,
      textStyle: { color: "#aab3c5", fontFamily: "inherit" },
      legend: {
        top: 0,
        left: 0,
        textStyle: { color: "#aab3c5", fontSize: 11 },
        data: mode === "analyst"
          ? ["1-month trend (MA20)", "3-month trend (MA50)", "long-term trend (MA200)", "RSI(14)"]
          : ["1-month trend (MA20)", "3-month trend (MA50)", "long-term trend (MA200)"]
      },
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      // Zoom (Ahmad request): wheel/pinch/drag-pan via `inside`, plus a visible
      // slider below the subcharts. Both span every x-axis so candle, volume and
      // (analyst) RSI panels zoom in lock-step. Range buttons re-slice the data and
      // this full setOption(true) rebuild resets the zoom window to the new slice —
      // so a range click naturally clears any manual zoom (no extra dispatch needed).
      dataZoom: [
        { type: "inside", xAxisIndex: mode === "analyst" ? [0, 1, 2] : [0, 1] },
        {
          type: "slider",
          xAxisIndex: mode === "analyst" ? [0, 1, 2] : [0, 1],
          bottom: 8,
          height: 18,
          borderColor: "#2a3140",
          fillerColor: "rgba(76,141,255,0.15)",
          handleStyle: { color: "#4c8dff" },
          dataBackground: { lineStyle: { color: "#3a4252" }, areaStyle: { color: "#232a38" } },
          textStyle: { color: "#8a93a5", fontSize: 10 }
        }
      ],
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
        backgroundColor: "#1a1f2b",
        borderColor: "#2a3140",
        textStyle: { color: "#e7ebf3" },
        formatter: function (params) {
          var p = params.find(function (x) { return x.seriesName === "Price"; });
          if (!p) return "";
          var idx = p.dataIndex;
          var bar = data[idx];
          var lines = [
            bar.date,
            "O " + bar.o + " H " + bar.h + " L " + bar.l + " C " + bar.c,
            "Vol " + bar.v.toLocaleString()
          ];
          if (bar.raw_close !== undefined && bar.raw_close !== bar.c) {
            lines.push("raw close " + bar.raw_close + " (split-adjusted above)");
          }
          // U8: append past-signal info when a marker sits on this bar
          var m = params.find(function (x) { return x.seriesName === "Engine signals"; });
          if (m && m.data && m.data.marker) {
            var mk = m.data.marker;
            lines.push("&mdash;");
            lines.push(mk.glyph + " " + mk.signal + " signal &middot; " + mk.result);
            if (mk.result_detail) lines.push(escapeTooltip(mk.result_detail));
            if (mk.why) lines.push("why: " + escapeTooltip(mk.why));
          }
          return lines.join("<br>");
        }
      },
      series: series
    };
  }

  function markLineLabel(p) {
    var v = Math.round(p.value);
    if (p.data.name === "floor") return "floor " + v;
    if (p.data.name === "ceiling") return "ceiling " + v;
    return "";
  }

  function catAxis(dates, gridIndex, showLabel) {
    return {
      type: "category",
      data: dates,
      gridIndex: gridIndex,
      boundaryGap: true,
      axisLine: { lineStyle: { color: "#2a3140" } },
      axisLabel: { show: showLabel, color: "#6f7889" },
      axisTick: { show: false },
      splitLine: { show: false }
    };
  }
  function valAxis(gridIndex, isVolume) {
    return {
      scale: true,
      gridIndex: gridIndex,
      splitLine: { lineStyle: { color: "#232937" } },
      axisLabel: { color: "#6f7889", show: !isVolume },
      axisLine: { show: false }
    };
  }

  function lineSeries(name, data, color) {
    return {
      name: name, type: "line", data: data,
      showSymbol: false, smooth: false,
      lineStyle: { color: color, width: 1.4 },
      z: 3
    };
  }
  function lineSeriesRaw(name, data, color, xIdx, yIdx, dashed) {
    return {
      name: name, type: "line", data: data,
      xAxisIndex: xIdx, yAxisIndex: yIdx,
      showSymbol: false,
      lineStyle: { color: color, width: 1, type: dashed ? "dashed" : "solid" },
      z: 2
    };
  }

  function colorUp() { return "#2fbf71"; }
  function colorDown() { return "#e0555e"; }

  function buildDividendMarks(fundamentals, visibleDates, sliced) {
    var payouts = (fundamentals && fundamentals.payouts) || [];
    var marks = [];
    payouts.forEach(function (p) {
      var exDate = parseExDate(p.ex_or_bc);
      if (!exDate) return;
      // snap to nearest visible bar date on/after ex-date (mechanical dip point)
      var idx = visibleDates.findIndex(function (d) { return d >= exDate; });
      if (idx === -1) return;
      var barHigh = sliced && sliced[idx] ? sliced[idx].h : null;
      marks.push({
        name: "dividend",
        coord: [idx, barHigh],
        value: p.pct + "% dividend — price dip here is normal",
        symbol: "pin",
        symbolSize: 26,
        itemStyle: { color: "#d8a441" }
      });
    });
    return marks;
  }

  // -----------------------------------------------------------------------
  // U8: past-signal markers — ▲ BUY / ▼ SELL / ◆ HOLD, colored by outcome
  // -----------------------------------------------------------------------
  function buildSignalMarkerSeries(history, dates, data) {
    var OUTCOME_COLOR = { HIT: "#2fbf71", MISS: "#e0555e", PENDING: "#6f7889" };
    var points = [];
    history.forEach(function (h) {
      // only markers inside the current range slice render; a signal dated after the
      // last bar (G3 freshness divergence) snaps back to the nearest earlier session
      var idx = dates.indexOf(h.date);
      if (idx === -1) {
        for (var i = dates.length - 1; i >= 0; i--) {
          if (dates[i] < h.date) { idx = i; break; }
        }
        if (idx === -1 || daysBetween(dates[idx], h.date) > 3) return;
      }
      var bar = data[idx];
      var isSell = h.signal === "SELL";
      var isHold = h.signal === "HOLD";
      var result = h.result === "HIT" || h.result === "MISS" ? h.result : "PENDING";
      points.push({
        value: [idx, isSell ? bar.l : bar.h],
        symbol: isHold ? "diamond" : "triangle",
        symbolRotate: isSell ? 180 : 0,
        symbolSize: isHold ? 9 : 12,
        symbolOffset: [0, isSell ? 12 : -12],
        itemStyle: {
          color: OUTCOME_COLOR[result],
          borderColor: "#0b0e14",
          borderWidth: 1
        },
        marker: {
          glyph: isSell ? "&#9660;" : isHold ? "&#9670;" : "&#9650;",
          signal: h.signal,
          result: result + (result === "PENDING" && h.grade_on_date ? " (grades " + h.grade_on_date + ")" : ""),
          result_detail: h.result_detail || null,
          why: h.why || null
        }
      });
    });
    if (!points.length) return null;
    return {
      name: "Engine signals",
      type: "scatter",
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: points,
      clip: false,
      z: 12,
      cursor: "pointer",
      emphasis: { scale: 1.4 }
    };
  }

  function daysBetween(a, b) {
    return Math.abs(new Date(b) - new Date(a)) / 86400000;
  }

  function escapeTooltip(s) {
    return String(s).replace(/[&<>]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c];
    });
  }

  // Parse "dd/mm/yyyy  - dd/mm/yyyy" -> ISO yyyy-mm-dd of the START date
  function parseExDate(range) {
    if (!range) return null;
    var first = range.split("-")[0].trim();
    var parts = first.split("/");
    if (parts.length !== 3) return null;
    var dd = parts[0], mm = parts[1], yyyy = parts[2];
    return yyyy + "-" + mm + "-" + dd;
  }

  // -----------------------------------------------------------------------
  // Trend summary sentence, RSI chip, ATR/52w captions (Simple-mode plain language)
  // -----------------------------------------------------------------------
  function updateTrendSummary(container, derived, signal) {
    var host = container.querySelector("#trend-summary");
    var lastIdx = derived.closes.length - 1;
    var close = derived.closes[lastIdx];
    var m20 = derived.ma20[lastIdx], m50 = derived.ma50[lastIdx], m200 = derived.ma200[lastIdx];
    var text;
    if (m20 == null || m50 == null || m200 == null) {
      text = "Not enough history yet to judge trend.";
    } else if (close > m20 && close > m50 && close > m200) {
      text = "Uptrend — price above all three trend lines.";
    } else if (close < m20 && m20 < m50) {
      text = "Weakening — fell below 1-month trend.";
    } else if (close < m50 && close < m200) {
      text = "Downtrend — price below the 3-month and long-term trend lines.";
    } else {
      text = "Mixed — trend lines are not aligned.";
    }
    host.textContent = text;
  }

  function updateRsiChip(container, rsiVal) {
    var chip = container.querySelector("#rsi-chip");
    if (rsiVal == null) {
      chip.textContent = "RSI –";
      chip.className = "rsi-chip";
      return;
    }
    var cls = "", label;
    if (rsiVal > 70) { cls = "hot"; label = "overheated"; }
    else if (rsiVal < 30) { cls = "cold"; label = "beaten down"; }
    else label = "normal";
    chip.className = "rsi-chip" + (cls ? " " + cls : "");
    chip.title = "RSI " + rsiVal;
    chip.textContent = label + " (RSI " + rsiVal + ")";
  }

  function updateCaptions(container, derived, signal) {
    var host = container.querySelector("#chart-captions");
    var lastIdx = derived.atr14.length - 1;
    var atrVal = derived.atr14[lastIdx];
    var close = derived.closes[lastIdx];
    var caps = [];
    if (atrVal != null && close) {
      var pct = ((atrVal / close) * 100).toFixed(1);
      caps.push("normally moves &plusmn;" + atrVal.toFixed(2) + " (" + pct + "%) per day");
    }
    if (signal.pos52 != null) {
      caps.push("trading at " + signal.pos52.toFixed(0) + "% of its 1-year range");
    }
    host.innerHTML = caps.map(function (c) { return "<span>" + c + "</span>"; }).join("");
  }

  window.PSXChart = { render: render };
})();
