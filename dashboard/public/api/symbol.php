<?php
/**
 * TICKET-D4 — GET /api/symbol.php?sym=<TICKER>
 * Merged single-symbol payload per PLAN.md §6.2. This is the core deliverable.
 *
 * Contract recap:
 *  - unknown symbol -> 200 {"meta":{"found":false,...}}
 *  - partial data-layer failure -> section null + meta.warnings entry (G4)
 *  - ohlc.o/h/l/c = adjusted series (G5); raw_close only when it differs
 *  - history[].result normalized to HIT|MISS|PENDING, newest-first (G2)
 *  - freshness check: feed as_of vs ohlc last-bar date (G3)
 */

declare(strict_types=1);

ini_set('display_errors', '0');
error_reporting(E_ALL);

require __DIR__ . '/../../config.php';
require __DIR__ . '/../../api/lib/data.php';
require __DIR__ . '/../../api/lib/sector_keywords.php';

api_headers();

$symRaw = isset($_GET['sym']) ? (string) $_GET['sym'] : '';
$sym = strtoupper(trim($symRaw));

if (!is_valid_symbol($sym)) {
    http_response_code(200);
    echo json_encode([
        'meta' => ['found' => false, 'ticker' => $symRaw, 'error' => 'invalid_symbol'],
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$warnings = [];

// ---- 1. dashboard_feed.json (signal + name + as_of) ----------------------
$feedPath = data_path('dashboard_feed.json');
$feedResult = $feedPath !== null ? read_json($feedPath) : ['ok' => false, 'error' => 'invalid_path'];

$feedAsOf = null;
$symbolFeed = null;
if ($feedResult['ok'] === true) {
    $feedAsOf = $feedResult['data']['_meta']['_generated'] ?? null;
    $symbolFeed = $feedResult['data']['symbols'][$sym] ?? null;
} else {
    $warnings[] = 'dashboard_feed_unavailable: ' . $feedResult['error'];
}

if ($symbolFeed === null) {
    // Unknown symbol (not in the feed at all) -> found:false per contract.
    // Still 200, still valid JSON.
    echo json_encode([
        'meta' => ['found' => false, 'ticker' => $sym],
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$name = (string) ($symbolFeed['name'] ?? $sym);

// ---- 2. OHLC (adjusted series) --------------------------------------------
$ohlcPath = data_path('ohlc/' . $sym . '.json');
$ohlcResult = $ohlcPath !== null ? read_json($ohlcPath) : ['ok' => false, 'error' => 'invalid_path'];

$ohlcOut = null;
$ohlcLastDate = null;
if ($ohlcResult['ok'] === true && is_array($ohlcResult['data'])) {
    $bars = $ohlcResult['data'];
    $ohlcOut = [];
    foreach ($bars as $bar) {
        if (!is_array($bar)) {
            continue;
        }
        $date = $bar['date'] ?? null;
        // Prefer adjusted fields (G5); fall back to raw if adj_* absent so a
        // symbol with no corporate actions still charts correctly.
        $o = $bar['adj_open'] ?? $bar['open'] ?? null;
        $h = $bar['adj_high'] ?? $bar['high'] ?? null;
        $l = $bar['adj_low'] ?? $bar['low'] ?? null;
        $c = $bar['adj_close'] ?? $bar['close'] ?? null;
        $v = $bar['volume'] ?? null;

        $row = [
            'date' => $date,
            'o' => $o,
            'h' => $h,
            'l' => $l,
            'c' => $c,
            'v' => $v,
        ];

        $rawClose = $bar['close'] ?? null;
        if ($rawClose !== null && $c !== null && (float) $rawClose !== (float) $c) {
            $row['raw_close'] = $rawClose;
        }

        $ohlcOut[] = $row;
        if ($date !== null) {
            $ohlcLastDate = $date; // bars assumed chronological; last wins
        }
    }
} else {
    $warnings[] = 'ohlc_unavailable: ' . $ohlcResult['error'];
}

// G3 — freshness check: feed as_of vs OHLC last-bar date.
if ($feedAsOf !== null && $ohlcLastDate !== null && $feedAsOf !== $ohlcLastDate) {
    $warnings[] = "ohlc_last_bar {$ohlcLastDate} != feed as_of {$feedAsOf}";
}

// ---- 3. Signal history (universe_signals.csv, filtered by symbol) --------
$csvPath = data_path('universe_signals.csv');
$csvResult = $csvPath !== null ? read_csv($csvPath) : ['ok' => false, 'error' => 'invalid_path'];

$history = null;
if ($csvResult['ok'] === true) {
    $history = [];
    foreach ($csvResult['rows'] as $row) {
        if (($row['symbol'] ?? null) !== $sym) {
            continue;
        }

        $status = $row['status'] ?? '';
        $rawResult = $row['result'] ?? '';

        if ($status === 'graded') {
            if (stripos($rawResult, 'HIT') === 0) {
                $resultEnum = 'HIT';
            } elseif (stripos($rawResult, 'MISS') === 0) {
                $resultEnum = 'MISS';
            } else {
                // Graded but unparsed text — don't invent a verdict.
                $resultEnum = 'PENDING';
            }
        } else {
            $resultEnum = 'PENDING';
        }

        $history[] = [
            'date' => $row['date'] ?? null,
            'signal' => $row['signal'] ?? null,
            'conviction' => isset($row['conviction']) && $row['conviction'] !== ''
                ? (int) $row['conviction'] : null,
            'score' => isset($row['score']) && $row['score'] !== '' ? (int) $row['score'] : null,
            'status' => $status !== '' ? $status : null,
            'result' => $resultEnum,
            'result_detail' => $rawResult !== '' ? $rawResult : null,
            'grade_on_date' => $row['grade_on_date'] ?? null,
            'why' => $row['why'] ?? null,
        ];
    }

    // Newest-first.
    usort($history, static function (array $a, array $b): int {
        return strcmp((string) ($b['date'] ?? ''), (string) ($a['date'] ?? ''));
    });
} else {
    $warnings[] = 'signal_history_unavailable: ' . $csvResult['error'];
}

// ---- 4. Fundamentals -------------------------------------------------------
$fundPath = data_path('fundamentals/' . $sym . '.json');
$fundResult = $fundPath !== null ? read_json($fundPath) : ['ok' => false, 'error' => 'invalid_path'];

$fundamentals = null;
if ($fundResult['ok'] === true && is_array($fundResult['data'])) {
    $fd = $fundResult['data'];
    $quarterly = $fd['quarterly_results'] ?? [];
    $latest = is_array($quarterly) && count($quarterly) > 0 ? $quarterly[0] : null;

    $fundamentals = [
        'latest_eps' => $latest['eps'] ?? null,
        'latest_period' => $latest !== null
            ? trim(($latest['period_type'] ?? '') . ' ' . ($latest['period'] ?? ''))
            : null,
        'eps_trend' => $symbolFeed['eps_trend'] ?? 'unknown',
        'quarterly_results' => $quarterly,
        'payouts' => $fd['payouts'] ?? [],
    ];
} elseif ($fundResult['error'] === 'not_found') {
    // G7 — ~3/100 symbols legitimately lack fundamentals. Not an error.
    $fundamentals = null;
} else {
    $warnings[] = 'fundamentals_unavailable: ' . $fundResult['error'];
}

// ---- 5. News (sector/symbol relevance filter, TICKET-D3) ------------------
$newsPath = data_path('news_archive.jsonl');
$newsResult = $newsPath !== null ? read_jsonl($newsPath) : ['ok' => false, 'error' => 'invalid_path'];

$news = null;
if ($newsResult['ok'] === true) {
    $news = build_symbol_news($newsResult['data'], $sym, 10, 5);
} else {
    $warnings[] = 'news_unavailable: ' . $newsResult['error'];
}

// ---- 6. Filings / diligence ledger ----------------------------------------
$ledgerPath = data_path('diligence_ledger.json');
$ledgerResult = $ledgerPath !== null ? read_json($ledgerPath) : ['ok' => false, 'error' => 'invalid_path'];

$filings = null;
$hasUnreviewedMaterial = false;
if ($ledgerResult['ok'] === true && is_array($ledgerResult['data'])) {
    $allFilings = $ledgerResult['data']['filings'] ?? [];
    $filings = [];
    if (is_array($allFilings)) {
        foreach ($allFilings as $f) {
            if (!is_array($f) || ($f['symbol'] ?? null) !== $sym) {
                continue;
            }
            $filings[] = [
                'date' => $f['date'] ?? null,
                'title' => $f['title'] ?? null,
                'materiality' => $f['materiality'] ?? null,
                'reviewed' => (bool) ($f['reviewed'] ?? false),
                'pdf_url' => $f['pdf_url'] ?? null,
            ];
            if (($f['materiality'] ?? null) === 'MATERIAL' && !($f['reviewed'] ?? false)) {
                $hasUnreviewedMaterial = true;
            }
        }
        usort($filings, static function (array $a, array $b): int {
            return strcmp((string) ($b['date'] ?? ''), (string) ($a['date'] ?? ''));
        });
    }
} else {
    $warnings[] = 'filings_unavailable: ' . $ledgerResult['error'];
}

// ---- Assemble signal block --------------------------------------------------
$diligence = $symbolFeed['diligence'] ?? 'OK';
if ($hasUnreviewedMaterial) {
    // STALE precedence rule (§7.2): either source alone triggers it.
    $diligence = 'STALE';
}

$signal = [
    'signal' => $symbolFeed['signal'] ?? null,
    'conviction' => $symbolFeed['conviction'] ?? null,
    'score' => $symbolFeed['score'] ?? null,
    'close' => $symbolFeed['close'] ?? null,
    'ma20' => $symbolFeed['ma20'] ?? null,
    'ma50' => $symbolFeed['ma50'] ?? null,
    'ma200' => $symbolFeed['ma200'] ?? null,
    'rsi' => $symbolFeed['rsi'] ?? null,
    'pos52' => $symbolFeed['pos52'] ?? null,
    'yield_pct' => $symbolFeed['yield_pct'] ?? null,
    'mom20' => $symbolFeed['mom20'] ?? null,
    'support' => $symbolFeed['support'] ?? null,
    'resistance' => $symbolFeed['resistance'] ?? null,
    'eps_trend' => $symbolFeed['eps_trend'] ?? null,
    'diligence' => $diligence,
    'why' => $symbolFeed['why'] ?? null,
    'factors' => $symbolFeed['factors'] ?? null,
];

$meta = [
    'ticker' => $sym,
    'name' => $name,
    'as_of' => $feedAsOf,
    'found' => true,
    'warnings' => $warnings,
];

echo json_encode([
    'meta' => $meta,
    'signal' => $signal,
    'ohlc' => $ohlcOut,
    'history' => $history,
    'fundamentals' => $fundamentals,
    'news' => $news,
    'filings' => $filings,
], JSON_UNESCAPED_UNICODE);
