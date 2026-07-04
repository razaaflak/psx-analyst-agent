<?php
/**
 * TICKET-D3 — News relevance: symbol -> sector keyword map + matcher.
 *
 * PLAN.md §4.2: news has no structured symbol tag. Relevance rule:
 *   1. Headline/impact/note/ticker_or_sector text contains the ticker
 *      (word-boundary, case-insensitive), OR
 *   2. Text contains a sector keyword mapped from the symbol's sector.
 * Fallback: latest N market-wide items (macro-eligible = lens:"E" OR a
 * bucket-present older-shape line — those pre-date the lens field).
 *
 * Field-shape fact (verified by Lead): news_archive.jsonl has TWO shapes —
 *   older: {headline, note, ticker_or_sector, bucket, read}
 *   newer: {headline, impact}
 * Matcher scans headline + impact + note + ticker_or_sector. Output item's
 * `impact` field = impact ?? note.
 */

declare(strict_types=1);

/**
 * @return array<string, string[]> symbol ticker => sector keyword list
 *         (does not need to include the ticker itself; the matcher always
 *         checks the ticker literal too).
 */
function sector_keyword_map(): array
{
    $sectors = [
        'E&P' => [
            'tickers' => ['OGDC', 'PPL', 'MARI', 'POL'],
            'keywords' => ['E&P', 'exploration', 'oil and gas', 'brent', 'crude', 'wti', 'hydrocarbon'],
        ],
        'CEMENT' => [
            'tickers' => ['LUCK', 'DGKC', 'MLCF', 'CHCC', 'FCCL', 'KOHC', 'PIOC', 'BWCL', 'ATLH', 'GAL'],
            'keywords' => ['cement', 'clinker'],
        ],
        'BANKS' => [
            'tickers' => ['ABL', 'MEBL', 'UBL', 'MCB', 'HBL', 'FABL', 'BAFL', 'BAHL', 'AKBL', 'BOP', 'NBP', 'SCBPL', 'PABC', 'HMB', 'IBFL', 'SSOM'],
            'keywords' => ['bank', 'banking', 'sbp', 'monetary policy', 'interest rate', 'discount rate', 'kibor'],
        ],
        'OMC' => [
            'tickers' => ['PSO', 'APL', 'HASCOL', 'GHGL'],
            'keywords' => ['omc', 'oil marketing', 'petroleum product', 'furnace oil', 'diesel', 'petrol price'],
        ],
        'FERTILIZER' => [
            'tickers' => ['FFC', 'EFERT', 'ENGROH', 'FATIMA'],
            'keywords' => ['fertilizer', 'urea', 'dap', 'gas curtailment'],
        ],
        'TEXTILE' => [
            'tickers' => ['NML', 'GADT', 'GHNI', 'ILP', 'KTML', 'NPL', 'SRVI'],
            'keywords' => ['textile', 'yarn', 'spinning'],
        ],
        'AUTO' => [
            'tickers' => ['INDU', 'HCAR', 'AGP', 'ATRL'],
            'keywords' => ['auto', 'automobile', 'car sales', 'vehicle'],
        ],
        'POWER' => [
            'tickers' => ['HUBC', 'KAPCO', 'KEL', 'POWER', 'SSGC', 'SNGP'],
            'keywords' => ['power sector', 'circular debt', 'ipp', 'electricity', 'gas tariff'],
        ],
        'PHARMA' => [
            'tickers' => ['ABOT', 'GLAXO', 'HINOON', 'SEARL', 'HALEON', 'FHAM'],
            'keywords' => ['pharma', 'pharmaceutical', 'drug pricing'],
        ],
        'FOOD_FMCG' => [
            'tickers' => ['NESTLE', 'COLG', 'RMPL', 'MUREB'],
            'keywords' => ['fmcg', 'consumer goods', 'food inflation'],
        ],
        'TECH_TELECOM' => [
            'tickers' => ['SYS', 'TRG', 'AIRLINK', 'PTC'],
            'keywords' => ['it export', 'technology sector', 'telecom'],
        ],
        'MACRO' => [
            'tickers' => [],
            'keywords' => ['budget', 'imf', 'current account', 'rupee', 'inflation', 'gdp', 'finance bill', 'sbp mpc'],
        ],
    ];

    $map = [];
    foreach ($sectors as $info) {
        foreach ($info['tickers'] as $ticker) {
            $map[$ticker] = array_merge($map[$ticker] ?? [], $info['keywords']);
        }
    }
    return $map;
}

/**
 * Extract the searchable text blob from one news item, handling both the
 * older and newer news_archive.jsonl line shapes.
 */
function news_item_text(array $item): string
{
    $parts = [
        $item['headline'] ?? '',
        $item['impact'] ?? '',
        $item['note'] ?? '',
        $item['ticker_or_sector'] ?? '',
    ];
    return implode(' ', array_filter($parts, static fn ($p) => is_string($p) && $p !== ''));
}

/** Normalized `impact` field for API output: impact ?? note. */
function news_item_impact(array $item): ?string
{
    if (isset($item['impact']) && is_string($item['impact'])) {
        return $item['impact'];
    }
    if (isset($item['note']) && is_string($item['note'])) {
        return $item['note'];
    }
    return null;
}

/** True if the item is macro-eligible: lens:"E", OR older-shape (bucket present, no lens). */
function news_item_is_macro_eligible(array $item): bool
{
    if (isset($item['lens'])) {
        return $item['lens'] === 'E';
    }
    return array_key_exists('bucket', $item);
}

function word_boundary_contains(string $haystack, string $needle): bool
{
    if ($needle === '') {
        return false;
    }
    $pattern = '/\b' . preg_quote($needle, '/') . '\b/i';
    return preg_match($pattern, $haystack) === 1;
}

/**
 * Classify one news item's relevance to $ticker.
 * @return 'symbol'|'sector'|null (null = no match; caller decides on macro fallback)
 */
function news_item_match(array $item, string $ticker, array $keywordMap): ?string
{
    $text = news_item_text($item);
    if ($text === '') {
        return null;
    }

    if (word_boundary_contains($text, $ticker)) {
        return 'symbol';
    }

    $keywords = $keywordMap[$ticker] ?? [];
    foreach ($keywords as $kw) {
        // Multi-word keywords: substring (case-insensitive) is fine, word
        // boundary regex still works for these since they're phrases.
        if (stripos($text, $kw) !== false) {
            return 'sector';
        }
    }

    return null;
}

/**
 * Build the news[] section for a symbol per §6.2: symbol/sector matches
 * first (newest-first, already assumed pre-sorted by caller or sorted here
 * by date desc), then macro fallback fill to $limit if still short.
 *
 * @param array<int,array> $allItems raw decoded news_archive.jsonl lines
 * @param int $limit max items to return
 * @param int $macroFallbackCount how many macro items to add if zero/few direct matches
 * @return array<int,array{date:?string,headline:string,impact:?string,source:?string,match:string}>
 */
function build_symbol_news(array $allItems, string $ticker, int $limit = 10, int $macroFallbackCount = 5): array
{
    $keywordMap = sector_keyword_map();

    $direct = [];
    $macroPool = [];

    foreach ($allItems as $item) {
        if (!is_array($item)) {
            continue;
        }
        $match = news_item_match($item, $ticker, $keywordMap);
        $row = [
            'date' => $item['date'] ?? ($item['_snapshot'] ?? null),
            'headline' => (string) ($item['headline'] ?? ''),
            'impact' => news_item_impact($item),
            'source' => isset($item['source']) ? (string) $item['source'] : null,
        ];

        if ($match !== null) {
            $row['match'] = $match;
            $direct[] = $row;
        } elseif (news_item_is_macro_eligible($item)) {
            $row['match'] = 'macro';
            $macroPool[] = $row;
        }
    }

    // Newest-first: sort by date string descending (ISO-ish dates sort
    // lexically fine; missing dates sink to the end).
    $byDateDesc = static function (array $a, array $b): int {
        return strcmp((string) ($b['date'] ?? ''), (string) ($a['date'] ?? ''));
    };
    usort($direct, $byDateDesc);
    usort($macroPool, $byDateDesc);

    $result = $direct;
    if (count($result) < $limit) {
        $need = $limit - count($result);
        $macroToAdd = array_slice($macroPool, 0, max($need, min($macroFallbackCount, count($macroPool))));
        $result = array_merge($result, $macroToAdd);
    }

    return array_slice($result, 0, $limit);
}
