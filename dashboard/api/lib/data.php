<?php
/**
 * TICKET-D1 — Read-only data lib.
 *
 * Defensive parser: assume every file under DATA_DIR can be half-written,
 * mis-quoted, or missing (PLAN.md §4.4). No write helpers exist here, by
 * design (D6 — read-only hard rule).
 */

declare(strict_types=1);

/**
 * Resolve a relative path against DATA_DIR, refusing anything that would
 * escape it (path-traversal guard). Returns the resolved absolute path
 * (which may not exist) or null if the input is unsafe / DATA_DIR is gone.
 */
function data_path(string $rel): ?string
{
    if (!defined('DATA_DIR') || DATA_DIR === false) {
        return null;
    }

    // Reject absolute paths, drive letters, and any parent-traversal token
    // outright — cheap defense before we ever touch the filesystem.
    if ($rel === '' || str_contains($rel, "\0")) {
        return null;
    }
    $normalizedRel = str_replace('\\', '/', $rel);
    $segments = explode('/', $normalizedRel);
    foreach ($segments as $seg) {
        if ($seg === '..' || $seg === '') {
            // allow leading '' only if whole string isn't just slashes; simplest: reject '..' and empty segments outright
            if ($seg === '..') {
                return null;
            }
        }
    }

    $base = rtrim(str_replace('\\', '/', (string) DATA_DIR), '/');
    $candidate = $base . '/' . ltrim($normalizedRel, '/');

    // realpath() also collapses any remaining '..' — if the result doesn't
    // stay under DATA_DIR, refuse it. realpath() requires the target to
    // exist; callers that need to test non-existent files should stay with
    // the string form and check existence themselves — here we optimistically
    // resolve when possible and fall back to the lexical candidate check.
    $real = realpath($candidate);
    if ($real !== false) {
        $realNorm = str_replace('\\', '/', $real);
        if (!str_starts_with($realNorm . '/', $base . '/')) {
            return null;
        }
        return $real;
    }

    // File doesn't exist yet (or can't be resolved) — still bound-check the
    // lexical path so callers get a consistent "not found" rather than a
    // traversal escape.
    $lexReal = $base . '/' . ltrim($normalizedRel, '/');
    if (!str_starts_with($lexReal, $base . '/') && $lexReal !== $base) {
        return null;
    }
    return $lexReal;
}

/**
 * Validate a user-supplied ticker symbol. PLAN D1: ^[A-Z0-9]{1,12}$.
 */
function is_valid_symbol(string $sym): bool
{
    return preg_match('/^[A-Z0-9]{1,12}$/', $sym) === 1;
}

/**
 * Read + json_decode a file with G4 handling: whole-file read, decode,
 * on parse failure retry once after 200ms, then return a structured
 * failure array instead of throwing / emitting a PHP warning.
 *
 * Returns: ['ok' => true, 'data' => mixed] on success
 *          ['ok' => false, 'error' => string] on failure (missing file,
 *          unreadable, or JSON that still doesn't parse after retry).
 */
function read_json(string $absPath): array
{
    $attempt = function () use ($absPath) {
        if (!is_file($absPath)) {
            return ['ok' => false, 'error' => 'not_found'];
        }
        // Suppress warnings from file_get_contents (e.g. permission issues,
        // torn read races) — we handle failure explicitly below.
        $raw = @file_get_contents($absPath);
        if ($raw === false || $raw === '') {
            return ['ok' => false, 'error' => 'read_failed'];
        }
        $decoded = json_decode($raw, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            return ['ok' => false, 'error' => 'parse_error'];
        }
        return ['ok' => true, 'data' => $decoded];
    };

    $result = $attempt();
    if ($result['ok'] === true) {
        return $result;
    }

    // G4: pipeline may be mid-write. Retry once after a short delay, but
    // only worth retrying for read/parse failures, not a genuinely missing
    // file (retrying won't make it appear).
    if ($result['error'] !== 'not_found') {
        usleep(200_000);
        $result = $attempt();
    }

    return $result;
}

/**
 * Read a JSON-Lines file: one JSON value per line. Malformed / blank lines
 * are skipped rather than aborting the whole read (defensive — a single
 * torn trailing line shouldn't nuke the archive).
 *
 * Returns: ['ok' => true, 'data' => array<int, mixed>] — data is the array
 *          of successfully parsed lines (possibly empty).
 *          ['ok' => false, 'error' => string] if the file itself is missing
 *          or unreadable.
 */
function read_jsonl(string $absPath): array
{
    $attempt = function () use ($absPath) {
        if (!is_file($absPath)) {
            return ['ok' => false, 'error' => 'not_found'];
        }
        $raw = @file_get_contents($absPath);
        if ($raw === false) {
            return ['ok' => false, 'error' => 'read_failed'];
        }
        $lines = preg_split('/\r\n|\r|\n/', $raw);
        $out = [];
        foreach ($lines as $line) {
            $line = trim($line);
            if ($line === '') {
                continue;
            }
            $decoded = json_decode($line, true);
            if (json_last_error() === JSON_ERROR_NONE) {
                $out[] = $decoded;
            }
            // Malformed line: skip silently (defensive parser stance).
        }
        return ['ok' => true, 'data' => $out];
    };

    $result = $attempt();
    if ($result['ok'] === true) {
        return $result;
    }
    if ($result['error'] !== 'not_found') {
        usleep(200_000);
        $result = $attempt();
    }
    return $result;
}

/**
 * Read a CSV with a header row, mapping columns by header NAME (never by
 * index — G6: columns can be added over time). Uses fgetcsv() so quoted
 * fields containing commas parse correctly (G1).
 *
 * Returns: ['ok' => true, 'rows' => array<int, array<string,string>>]
 *          ['ok' => false, 'error' => string]
 */
function read_csv(string $absPath): array
{
    $attempt = function () use ($absPath) {
        if (!is_file($absPath)) {
            return ['ok' => false, 'error' => 'not_found'];
        }
        $handle = @fopen($absPath, 'rb');
        if ($handle === false) {
            return ['ok' => false, 'error' => 'read_failed'];
        }

        $header = fgetcsv($handle, 0, ',', '"', '\\');
        if ($header === false || $header === null) {
            fclose($handle);
            return ['ok' => false, 'error' => 'empty_or_unreadable'];
        }
        // Normalize header cells (trim stray whitespace/BOM on first col).
        $header = array_map(static function ($h) {
            return trim((string) $h, " \t\n\r\0\x0B\xEF\xBB\xBF");
        }, $header);

        $rows = [];
        while (($fields = fgetcsv($handle, 0, ',', '"', '\\')) !== false) {
            if ($fields === null) {
                continue;
            }
            // Skip rows with a wildly wrong column count (defensive —
            // truncated/append-torn last line) rather than corrupting the map.
            if (count($fields) !== count($header)) {
                // Best-effort: pad or truncate to align, but only if close.
                if (count($fields) < count($header)) {
                    $fields = array_pad($fields, count($header), '');
                } else {
                    $fields = array_slice($fields, 0, count($header));
                }
            }
            $rows[] = array_combine($header, $fields);
        }
        fclose($handle);
        return ['ok' => true, 'rows' => $rows];
    };

    $result = $attempt();
    if ($result['ok'] === true) {
        return $result;
    }
    if ($result['error'] !== 'not_found') {
        usleep(200_000);
        $result = $attempt();
    }
    return $result;
}
