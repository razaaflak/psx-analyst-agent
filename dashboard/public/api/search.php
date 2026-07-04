<?php
/**
 * TICKET-D2 — GET /api/search.php?q=<str>
 * Typeahead over universe.json. Prefix matches first, then name-substring.
 * KSE100 excluded (G8). Cap 10 results.
 */

declare(strict_types=1);

// display_errors off for the API path (§6 preamble) — a PHP warning must
// never corrupt the JSON body.
ini_set('display_errors', '0');
error_reporting(E_ALL);

require __DIR__ . '/../../config.php';
require __DIR__ . '/../../api/lib/data.php';

api_headers();

$q = isset($_GET['q']) ? trim((string) $_GET['q']) : '';

if (mb_strlen($q) < 2) {
    echo json_encode([], JSON_UNESCAPED_UNICODE);
    exit;
}

$path = data_path('universe.json');
$result = $path !== null ? read_json($path) : ['ok' => false, 'error' => 'invalid_path'];

if ($result['ok'] !== true) {
    // Data-layer failure: return an empty list rather than crash — typeahead
    // is non-critical and a structured empty result is safe here.
    http_response_code(200);
    echo json_encode([], JSON_UNESCAPED_UNICODE);
    exit;
}

$symbols = $result['data']['symbols'] ?? [];
if (!is_array($symbols)) {
    echo json_encode([], JSON_UNESCAPED_UNICODE);
    exit;
}

$qLower = mb_strtolower($q);
$prefixMatches = [];
$substringMatches = [];

foreach ($symbols as $entry) {
    if (!is_array($entry)) {
        continue;
    }
    $ticker = (string) ($entry['ticker'] ?? '');
    $name = (string) ($entry['name'] ?? '');
    if ($ticker === '' || strcasecmp($ticker, 'KSE100') === 0) {
        continue; // G8 — index, not a stock
    }

    $tickerLower = mb_strtolower($ticker);
    $nameLower = mb_strtolower($name);

    if (str_starts_with($tickerLower, $qLower)) {
        $prefixMatches[] = ['ticker' => $ticker, 'name' => $name];
    } elseif (str_contains($nameLower, $qLower)) {
        $substringMatches[] = ['ticker' => $ticker, 'name' => $name];
    }
}

$combined = array_slice(array_merge($prefixMatches, $substringMatches), 0, 10);

echo json_encode($combined, JSON_UNESCAPED_UNICODE);
