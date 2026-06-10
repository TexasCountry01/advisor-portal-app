# ==============================================================================
# run_doc_export_audit.ps1
# ==============================================================================
# Runs the doc_export_audit management command on the PROD server via SSH
# and saves the full output to a timestamped local file.
#
# Usage:
#   From the project root:
#   .\run_doc_export_audit.ps1
#
#   To run against TEST server instead:
#   .\run_doc_export_audit.ps1 -Target test
#
# Output:
#   A timestamped .txt file is saved to the current directory, e.g.:
#   doc_export_audit_PROD_2026-06-10_1430.txt
#
# This script is READ-ONLY — it runs no migrations, makes no DB changes,
# and does not modify any files on the server.
# ==============================================================================

param(
    [ValidateSet('prod', 'test')]
    [string]$Target = 'prod'
)

# ── Server Configuration ──────────────────────────────────────────────────────
$servers = @{
    prod = @{
        Host        = '104.248.126.74'
        User        = 'dev'
        ProjectPath = '/var/www/advisor-portal'
        VenvPython  = '/var/www/advisor-portal/venv/bin/python'
        Label       = 'PRODUCTION'
        Color       = 'Red'
    }
    test = @{
        Host        = '157.245.141.42'
        User        = 'dev'
        ProjectPath = '/home/dev/advisor-portal-app'
        VenvPython  = '/home/dev/advisor-portal-app/venv/bin/python'
        Label       = 'TEST'
        Color       = 'Yellow'
    }
}

$server     = $servers[$Target]
$timestamp  = Get-Date -Format 'yyyy-MM-dd_HHmm'
$outputFile = "doc_export_audit_$($server.Label)_${timestamp}.txt"

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ''
Write-Host ('=' * 60) -ForegroundColor Cyan
Write-Host '  TRAINING DOCUMENT EXPORT AUDIT' -ForegroundColor Cyan
Write-Host ('=' * 60) -ForegroundColor Cyan
Write-Host ''
Write-Host "Target:      $($server.Label)  ($($server.Host))" -ForegroundColor $server.Color
Write-Host "Project:     $($server.ProjectPath)"
Write-Host "Output file: $outputFile"
Write-Host ''

if ($Target -eq 'prod') {
    Write-Host '⚠  Connecting to PRODUCTION server (read-only query).' -ForegroundColor Red
    Write-Host ''
}

# ── Run the command via SSH ───────────────────────────────────────────────────
$remoteCmd = "cd $($server.ProjectPath) && $($server.VenvPython) manage.py doc_export_audit"

Write-Host 'Running audit on remote server...' -ForegroundColor Yellow
Write-Host ''

try {
    $output = ssh "$($server.User)@$($server.Host)" $remoteCmd 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host 'ERROR: SSH command returned a non-zero exit code.' -ForegroundColor Red
        Write-Host 'Check that:'
        Write-Host '  - You have SSH key access to the server'
        Write-Host '  - The project path is correct'
        Write-Host '  - The management command exists (git pull first if needed)'
        exit 1
    }

    # Print to console
    $output | ForEach-Object { Write-Host $_ }

    # Save to file
    $header = @(
        "TRAINING DOCUMENT EXPORT AUDIT",
        "Server:    $($server.Label) ($($server.Host))",
        "Run at:    $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (local time)",
        "Command:   $remoteCmd",
        "",
        ("=" * 72),
        ""
    )

    ($header + $output) | Out-File -FilePath $outputFile -Encoding UTF8

    Write-Host ''
    Write-Host ('─' * 60) -ForegroundColor Green
    Write-Host "✓  Audit complete." -ForegroundColor Green
    Write-Host "   Output saved to: $outputFile" -ForegroundColor Green
    Write-Host ('─' * 60) -ForegroundColor Green
    Write-Host ''
    Write-Host 'Next steps:'
    Write-Host '  1. Review Section 3 (timeouts) and Section 5 (FFF coverage).'
    Write-Host '  2. Check Section 6 for per-scenario case counts.'
    Write-Host '  3. Check Section 7 for unicorn case results.'
    Write-Host '  4. Answer the open questions in Section 9.'
    Write-Host '  5. Share this file when deciding which Option to build.'
    Write-Host ''

} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host ''
    Write-Host 'If the management command is not yet deployed to the server:'
    Write-Host "  1. Commit and push this file:"
    Write-Host '        git add cases/management/commands/doc_export_audit.py'
    Write-Host '        git commit -m "Add doc_export_audit management command"'
    Write-Host '        git push origin main'
    Write-Host "  2. Deploy to the target server:"
    Write-Host '        .\deploy_to_production.ps1   (or deploy_to_test_server.ps1)'
    Write-Host "  3. Re-run this script."
    exit 1
}
