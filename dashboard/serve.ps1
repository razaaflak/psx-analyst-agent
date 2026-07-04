# Launch the PSX dashboard dev server (PLAN.md I1, port per §11 = 8000)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
php -S localhost:8000 -t (Join-Path $root 'public')
