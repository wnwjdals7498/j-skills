<#
.SYNOPSIS
    Injects the Unity AI Development Pipeline Kit into a Unity project.

.DESCRIPTION
    Copies templates into the target project and wires AGENTS.md / CLAUDE.md so the coding agent
    finds the kit. Existing files are never overwritten unless -Force is given: the point of the
    kit is to add rules, not to clobber a project's own conventions.

    CLAUDE.md is created as a link to AGENTS.md, falling back through three strategies because
    symlinks on Windows need admin rights or Developer Mode:
        1. symlink   (true link, survives git as a symlink)
        2. hardlink  (no admin needed; some editors break it on save)
        3. import    (a one-line CLAUDE.md that imports AGENTS.md)

.PARAMETER ProjectRoot
    The Unity project root — the directory containing Packages/manifest.json.

.PARAMETER Profile
    '3d' or '2d'. Selects which VISUAL_SPEC template is installed.

.PARAMETER Mode
    'greenfield' (new project) or 'rebase' (existing project being visually rebuilt).

.PARAMETER Force
    Overwrite files that already exist. Off by default.

.PARAMETER WhatIf
    Show what would happen without writing anything.

.EXAMPLE
    ./apply-kit.ps1 -ProjectRoot "D:\games\MyGame" -Profile 3d -Mode greenfield

.EXAMPLE
    ./apply-kit.ps1 -ProjectRoot "D:\games\MyGame" -Profile 2d -Mode rebase -WhatIf
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [Parameter(Mandatory = $true)]
    [ValidateSet('3d', '2d')]
    [string]$Profile,

    [ValidateSet('greenfield', 'rebase')]
    [string]$Mode = 'greenfield',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$KitRoot = Split-Path -Parent $PSScriptRoot
$Templates = Join-Path $KitRoot 'templates'

# ── Validation ────────────────────────────────────────────────────────────────

if (-not (Test-Path $ProjectRoot)) {
    throw "ProjectRoot not found: $ProjectRoot"
}

$manifest = Join-Path $ProjectRoot 'Packages\manifest.json'
if (-not (Test-Path $manifest)) {
    Write-Warning "Packages/manifest.json not found under $ProjectRoot."
    Write-Warning "This does not look like a Unity project root. Kit files will still be written."
}

Write-Host ""
Write-Host "Unity AI Development Pipeline Kit" -ForegroundColor Cyan
Write-Host "  Kit    : $KitRoot"
Write-Host "  Project: $ProjectRoot"
Write-Host "  Profile: $Profile"
Write-Host "  Mode   : $Mode"
Write-Host ""

# ── Helpers ───────────────────────────────────────────────────────────────────

$script:Created = @()
$script:Skipped = @()

function New-KitDirectory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        if ($PSCmdlet.ShouldProcess($Path, 'create directory')) {
            New-Item -ItemType Directory -Force -Path $Path | Out-Null
        }
    }
}

function Copy-KitFile {
    param(
        [string]$Source,
        [string]$Destination,
        [hashtable]$Replace = @{}
    )

    if (-not (Test-Path $Source)) {
        Write-Warning "template missing: $Source"
        return
    }

    if ((Test-Path $Destination) -and -not $Force) {
        $script:Skipped += $Destination
        return
    }

    if (-not $PSCmdlet.ShouldProcess($Destination, 'write')) { return }

    New-KitDirectory (Split-Path -Parent $Destination)

    if ($Replace.Count -gt 0) {
        $content = Get-Content -Path $Source -Raw -Encoding UTF8
        foreach ($key in $Replace.Keys) {
            $content = $content.Replace($key, $Replace[$key])
        }
        # UTF8 without BOM keeps Unity and git diffs clean.
        [System.IO.File]::WriteAllText($Destination, $content, (New-Object System.Text.UTF8Encoding($false)))
    }
    else {
        Copy-Item -Path $Source -Destination $Destination -Force
    }

    $script:Created += $Destination
}

function New-AgentLink {
    <#
        Creates CLAUDE.md pointing at AGENTS.md. Returns the strategy that worked.
    #>
    param([string]$Target, [string]$Link)

    if ((Test-Path $Link) -and -not $Force) { return 'skipped (exists)' }
    if (-not $PSCmdlet.ShouldProcess($Link, 'link to AGENTS.md')) { return 'whatif' }

    if (Test-Path $Link) { Remove-Item $Link -Force }

    try {
        New-Item -ItemType SymbolicLink -Path $Link -Target $Target -ErrorAction Stop | Out-Null
        return 'symlink'
    }
    catch {
        try {
            New-Item -ItemType HardLink -Path $Link -Target $Target -ErrorAction Stop | Out-Null
            return 'hardlink'
        }
        catch {
            $import = "# CLAUDE.md`n`n" +
                      "This project's agent instructions live in AGENTS.md.`n`n" +
                      "@AGENTS.md`n"
            [System.IO.File]::WriteAllText($Link, $import, (New-Object System.Text.UTF8Encoding($false)))
            return 'import'
        }
    }
}

# ── Layout ────────────────────────────────────────────────────────────────────

$dirs = @(
    'Docs',
    'Docs\Visual',
    'Docs\Visual\Reference',
    'Docs\Visual\Reference\GoldenViews',
    'Docs\Code',
    'Docs\Code\Tasks',
    'Assets\Editor\AIVisual',
    'Assets\VisualTests',
    'Assets\VisualTests\Screenshots',
    'Assets\Art\Approved',
    'Assets\Art\Experimental',
    'Assets\Art\Missing',
    'Tools',
    '.claude\skills\visual-director',
    '.claude\skills\unity-task-runner',
    '.agents\skills\visual-director',
    '.agents\skills\unity-task-runner'
)

foreach ($dir in $dirs) {
    New-KitDirectory (Join-Path $ProjectRoot $dir)
}

# ── Root agent docs ───────────────────────────────────────────────────────────

$replace = @{
    '{KIT_ROOT}'     = $KitRoot
    '{PROJECT_NAME}' = (Split-Path -Leaf $ProjectRoot)
    '{3d|2d}'        = $Profile
    '{greenfield|rebase}' = $Mode
}

Copy-KitFile `
    -Source (Join-Path $Templates 'project-root\AGENTS.md') `
    -Destination (Join-Path $ProjectRoot 'AGENTS.md') `
    -Replace $replace

$linkResult = New-AgentLink `
    -Target (Join-Path $ProjectRoot 'AGENTS.md') `
    -Link (Join-Path $ProjectRoot 'CLAUDE.md')

# ── Pipeline state and specs ──────────────────────────────────────────────────

Copy-KitFile `
    -Source (Join-Path $Templates 'project-root\Docs\PIPELINE_STATE.md') `
    -Destination (Join-Path $ProjectRoot 'Docs\PIPELINE_STATE.md') `
    -Replace @{
        '{KIT_ROOT}' = $KitRoot
        '{NAME}'     = (Split-Path -Leaf $ProjectRoot)
        '{PATH}'     = $ProjectRoot
        'profile: 3d            # 3d | 2d'          = "profile: $Profile            # 3d | 2d"
        'mode: greenfield       # greenfield | rebase' = "mode: $Mode       # greenfield | rebase"
    }

Copy-KitFile `
    -Source (Join-Path $Templates "project-root\Docs\Visual\VISUAL_SPEC.$Profile.yaml") `
    -Destination (Join-Path $ProjectRoot 'Docs\Visual\VISUAL_SPEC.yaml') `
    -Replace @{ '{KIT_ROOT}' = $KitRoot }

Copy-KitFile `
    -Source (Join-Path $Templates 'project-root\Docs\Visual\CONCEPT_ANALYSIS.yaml') `
    -Destination (Join-Path $ProjectRoot 'Docs\Visual\CONCEPT_ANALYSIS.yaml')

Copy-KitFile `
    -Source (Join-Path $Templates 'project-root\Docs\Visual\ASSET_CATALOG.json') `
    -Destination (Join-Path $ProjectRoot 'Docs\Visual\ASSET_CATALOG.json') `
    -Replace @{ '{KIT_ROOT}' = $KitRoot.Replace('\', '\\') }

Copy-KitFile `
    -Source (Join-Path $Templates 'project-root\Docs\Code\TASK_TEMPLATE.yaml') `
    -Destination (Join-Path $ProjectRoot 'Docs\Code\TASK_TEMPLATE.yaml') `
    -Replace @{ '{KIT_ROOT}' = $KitRoot }

# ── Skills ────────────────────────────────────────────────────────────────────

# Both agents get the orchestration skills: Claude Code reads .claude/skills,
# Codex and the other agent CLIs read .agents/skills.
foreach ($skill in @('visual-director', 'unity-task-runner')) {
    foreach ($base in @('.claude\skills', '.agents\skills')) {
        Copy-KitFile `
            -Source (Join-Path $Templates "skills\$skill\SKILL.md") `
            -Destination (Join-Path $ProjectRoot "$base\$skill\SKILL.md") `
            -Replace @{ '{KIT_ROOT}' = $KitRoot }
    }
}

# ── Editor tools ──────────────────────────────────────────────────────────────

foreach ($file in @('GameViewCapture.cs', 'ConceptOverlay.cs', 'VisualLinter.cs',
                    'AIVisual.Editor.asmdef', 'README.md')) {
    Copy-KitFile `
        -Source (Join-Path $Templates "unity\Editor\$file") `
        -Destination (Join-Path $ProjectRoot "Assets\Editor\AIVisual\$file")
}

# ── Report ────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Created ($($script:Created.Count))" -ForegroundColor Green
foreach ($file in $script:Created) {
    Write-Host "  + $($file.Replace($ProjectRoot, '').TrimStart('\'))"
}

if ($script:Skipped.Count -gt 0) {
    Write-Host ""
    Write-Host "Skipped — already exists ($($script:Skipped.Count)); use -Force to overwrite" -ForegroundColor Yellow
    foreach ($file in $script:Skipped) {
        Write-Host "  = $($file.Replace($ProjectRoot, '').TrimStart('\'))"
    }
}

Write-Host ""
Write-Host "CLAUDE.md link strategy: $linkResult" -ForegroundColor Cyan
if ($linkResult -eq 'hardlink') {
    Write-Host "  Note: some editors break hardlinks on save. To get a true symlink, enable" -ForegroundColor DarkGray
    Write-Host "  Windows Developer Mode or run this script as administrator, then re-run with -Force." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Next steps" -ForegroundColor Cyan
Write-Host "  1. Put concept art in Docs\Visual\Reference\Concept_Master.png"
Write-Host "  2. Tell the agent: 'read AGENTS.md and continue the pipeline'"
Write-Host "  3. The agent runs S0 bootstrap, then stops at the first decision it cannot make."
Write-Host ""
