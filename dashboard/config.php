<?php
/**
 * Dashboard config — read-only consumer of the pipeline's data/ folder.
 * HARD RULE (PLAN.md D6): nothing under DATA_DIR is ever written by the dashboard.
 */

declare(strict_types=1);

// Pipeline data folder (dashboard/ sits next to data/ inside psx-analyst-agent/)
define('DATA_DIR', realpath(__DIR__ . '/../data'));

if (DATA_DIR === false) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['error' => 'data_dir_not_found']);
    exit;
}

define('DASHBOARD_VERSION', '1.0.0');

// Symbol validation (PLAN.md D1 — path-traversal guard)
define('SYM_PATTERN', '/^[A-Z0-9]{1,12}$/');

// API responses must never be cached (PLAN.md D7)
function api_headers(): void
{
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
}
