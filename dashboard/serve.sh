#!/usr/bin/env sh
# Launch the PSX dashboard dev server (PLAN.md I1, port per §11 = 8000)
cd "$(dirname "$0")"
php -S localhost:8000 -t public
