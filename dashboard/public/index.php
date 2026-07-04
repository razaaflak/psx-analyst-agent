<?php
// TICKET-U1 — shell replaces I1 placeholder
// Cache-bust local assets by mtime so JS/CSS edits are never served stale by the browser.
function asset_v(string $rel): string {
    $t = @filemtime(__DIR__ . '/' . $rel);
    return htmlspecialchars($rel . '?v=' . ($t ?: '1'));
}
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PSX Engine — Dashboard</title>
  <link rel="stylesheet" href="<?= asset_v('assets/styles.css') ?>">
</head>
<body>
  <header class="app-header">
    <div class="brand">PSX ENGINE</div>
    <div class="search-wrap">
      <input
        id="search-input"
        class="search-input"
        type="text"
        placeholder="Search symbol… (e.g. OGDC)"
        autocomplete="off"
        aria-label="Search KSE-100 symbol"
        aria-expanded="false"
        aria-controls="search-results"
        role="combobox"
      >
      <div id="search-results" class="search-results" role="listbox"></div>
    </div>
    <div id="as-of" class="as-of tabular"></div>
  </header>

  <div id="freshness-banner" class="banner" role="status">
    <span class="icon">&#9888;</span>
    <span id="freshness-banner-text"></span>
  </div>

  <main id="app-main" class="app-main"></main>

  <div id="landing" class="landing">
    <h1>PSX Universe Prediction Engine</h1>
    <p>Type a KSE-100 symbol to see its candlestick chart, current signal, fundamentals, news, and graded signal history.</p>
    <div class="example-chips">
      <button class="chip" data-symbol="OGDC">OGDC</button>
      <button class="chip" data-symbol="LUCK">LUCK</button>
      <button class="chip" data-symbol="ABL">ABL</button>
    </div>
  </div>

  <footer id="app-footer" class="app-footer">
    <div id="footer-disclaimer">Layer-1 engine signal &middot; TRAINING ONLY, not trade advice</div>
    <div id="footer-engine-stat" class="engine-stat"></div>
  </footer>

  <script src="<?= asset_v('assets/vendor/echarts.min.js') ?>"></script>
  <script src="<?= asset_v('assets/chart.js') ?>"></script>
  <script src="<?= asset_v('assets/app.js') ?>"></script>
</body>
</html>
