param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = "Stop"

function Show-Usage {
@"
Usage: tools/setup/bootstrap.ps1 [--doctor|--install] [--with-optional] [--non-interactive]

Modes:
  --doctor            Validate required/optional tools (default)
  --install           Attempt best-effort installation, then validate

Options:
  --with-optional     Also install optional tools
  --non-interactive   Use non-interactive install flags where possible
  --help              Show this help

Exit codes:
  0: required toolchain satisfied
  2: missing/old required dependencies remain
  3: installation attempted but failed/partial
"@
}

 $mode = "doctor"
 $WithOptional = $false
 $NonInteractive = $false
 $ShowHelp = $false
 $seenDoctor = $false
 $seenInstall = $false

 foreach ($arg in $CliArgs) {
    switch -Regex ($arg) {
        "^(--doctor|-doctor)$" {
            if ($seenInstall) { throw "Use either --doctor or --install, not both." }
            $seenDoctor = $true
            $mode = "doctor"
            continue
        }
        "^(--install|-install)$" {
            if ($seenDoctor) { throw "Use either --doctor or --install, not both." }
            $seenInstall = $true
            $mode = "install"
            continue
        }
        "^(--with-optional|-with-optional|-withoptional)$" {
            $WithOptional = $true
            continue
        }
        "^(--non-interactive|-non-interactive|-noninteractive)$" {
            $NonInteractive = $true
            continue
        }
        "^(--help|-h|-help)$" {
            $ShowHelp = $true
            continue
        }
        default {
            throw "Unknown argument: $arg"
        }
    }
 }

if ($ShowHelp) {
    Show-Usage
    exit 0
}

function Test-VersionAtLeast {
    param([string]$Current, [string]$Minimum)
    try {
        return ([version]$Current -ge [version]$Minimum)
    } catch {
        return $false
    }
}

function Get-CommandVersion {
    param([string]$Command, [string[]]$Args, [string]$Regex)
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        return $null
    }
    $output = & $Command @Args 2>&1 | Out-String
    $m = [regex]::Match($output, $Regex)
    if ($m.Success) { return $m.Groups[1].Value }
    return $null
}

$requiredIssues = New-Object System.Collections.Generic.List[string]
$optionalIssues = New-Object System.Collections.Generic.List[string]

function Run-Checks {
    $script:requiredIssues.Clear()
    $script:optionalIssues.Clear()

    Write-Host "== Toolchain doctor =="

    $cmakeVersion = Get-CommandVersion -Command "cmake" -Args @("--version") -Regex "([0-9]+\.[0-9]+(\.[0-9]+)?)"
    if ($cmakeVersion) {
        if (Test-VersionAtLeast -Current $cmakeVersion -Minimum "3.20") {
            Write-Host "[ok] cmake $cmakeVersion"
        } else {
            $script:requiredIssues.Add("cmake version too old ($cmakeVersion < 3.20)")
            Write-Host "[err] cmake $cmakeVersion (need >= 3.20)"
        }
    } else {
        $script:requiredIssues.Add("cmake not found")
        Write-Host "[err] cmake not found"
    }

    $compilerOk = $false

    $gccVersion = Get-CommandVersion -Command "gcc" -Args @("--version") -Regex "([0-9]+\.[0-9]+(\.[0-9]+)?)"
    if ($gccVersion) {
        if (Test-VersionAtLeast -Current $gccVersion -Minimum "11.0") {
            $compilerOk = $true
            Write-Host "[ok] gcc $gccVersion"
        } else {
            Write-Host "[warn] gcc $gccVersion (need >= 11)"
        }
    }

    $clangVersion = Get-CommandVersion -Command "clang" -Args @("--version") -Regex "([0-9]+\.[0-9]+(\.[0-9]+)?)"
    if ($clangVersion) {
        if (Test-VersionAtLeast -Current $clangVersion -Minimum "14.0") {
            $compilerOk = $true
            Write-Host "[ok] clang $clangVersion"
        } else {
            Write-Host "[warn] clang $clangVersion (need >= 14)"
        }
    }

    $msvcVersion = Get-CommandVersion -Command "cl" -Args @() -Regex "Version\s+([0-9]+\.[0-9]+)"
    if ($msvcVersion) {
        if (Test-VersionAtLeast -Current $msvcVersion -Minimum "19.34") {
            $compilerOk = $true
            Write-Host "[ok] msvc $msvcVersion"
        } else {
            Write-Host "[warn] msvc $msvcVersion (need >= 19.34)"
        }
    }

    if (-not $compilerOk) {
        $script:requiredIssues.Add("no supported compiler at required baseline (GCC >=11, Clang >=14, or MSVC >=19.34)")
        Write-Host "[err] compiler baseline unmet"
    }

    if (Get-Command ninja -ErrorAction SilentlyContinue) {
        Write-Host "[ok] ninja"
    } else {
        $script:optionalIssues.Add("ninja not found (optional, recommended)")
        Write-Host "[warn] ninja not found (optional)"
    }

    if (Get-Command clang-format -ErrorAction SilentlyContinue) {
        Write-Host "[ok] clang-format"
    } else {
        $script:optionalIssues.Add("clang-format not found (optional)")
        Write-Host "[warn] clang-format not found (optional)"
    }

    if ($IsWindows) {
        $script:optionalIssues.Add("ccache not evaluated on Windows (optional)")
    } elseif (Get-Command ccache -ErrorAction SilentlyContinue) {
        Write-Host "[ok] ccache"
    } else {
        $script:optionalIssues.Add("ccache not found (optional)")
        Write-Host "[warn] ccache not found (optional)"
    }

    Write-Host ""
    if ($script:requiredIssues.Count -eq 0) {
        Write-Host "Required dependencies: satisfied"
    } else {
        Write-Host "Required dependencies: missing/invalid"
        $script:requiredIssues | ForEach-Object { Write-Host "  - $_" }
    }

    if ($script:optionalIssues.Count -eq 0) {
        Write-Host "Optional dependencies: satisfied"
    } else {
        Write-Host "Optional dependencies: recommendations"
        $script:optionalIssues | ForEach-Object { Write-Host "  - $_" }
    }
}

function Install-WithWinget {
    param([string[]]$Ids)
    foreach ($id in $Ids) {
        $args = @("install", "--id", $id)
        if ($NonInteractive) {
            $args += @("--silent", "--accept-source-agreements", "--accept-package-agreements")
        }
        & winget @args
    }
}

function Install-WithChoco {
    param([string[]]$Packages)
    foreach ($pkg in $Packages) {
        $args = @("install", $pkg, "-y")
        if ($NonInteractive) { $args += "--no-progress" }
        & choco @args
    }
}

function Run-Install {
    Write-Host "== Install mode =="

    if ($IsWindows) {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            $required = @("Kitware.CMake")
            if ($WithOptional) { $optional = @("Ninja-build.Ninja", "LLVM.LLVM") } else { $optional = @() }
            Install-WithWinget -Ids $required
            if ($optional.Count -gt 0) { Install-WithWinget -Ids $optional }
            return
        }

        if (Get-Command choco -ErrorAction SilentlyContinue) {
            $required = @("cmake")
            if ($WithOptional) { $optional = @("ninja", "llvm") } else { $optional = @() }
            Install-WithChoco -Packages $required
            if ($optional.Count -gt 0) { Install-WithChoco -Packages $optional }
            return
        }

        throw "No supported Windows package manager found (winget/choco)."
    }

    if ($IsMacOS) {
        if (-not (Get-Command brew -ErrorAction SilentlyContinue)) {
            throw "Homebrew not found. Install brew first: https://brew.sh"
        }
        & brew install cmake
        if ($WithOptional) {
            & brew install ninja clang-format ccache
        }
        return
    }

    if ($IsLinux) {
        if (Get-Command apt-get -ErrorAction SilentlyContinue) {
            & sudo apt-get update
            & sudo apt-get install -y cmake build-essential
            if ($WithOptional) { & sudo apt-get install -y ninja-build clang-format ccache }
            return
        }
        if (Get-Command dnf -ErrorAction SilentlyContinue) {
            & sudo dnf install -y cmake gcc-c++ make
            if ($WithOptional) { & sudo dnf install -y ninja-build clang-tools-extra ccache }
            return
        }
        if (Get-Command pacman -ErrorAction SilentlyContinue) {
            & sudo pacman -Sy --noconfirm cmake base-devel
            if ($WithOptional) { & sudo pacman -Sy --noconfirm ninja clang ccache }
            return
        }
        throw "No supported Linux package manager found (apt/dnf/pacman)."
    }

    throw "Unsupported OS for install mode."
}

Run-Checks
if ($mode -eq "doctor") {
    if ($requiredIssues.Count -eq 0) { exit 0 }
    exit 2
}

try {
    Run-Install
} catch {
    Write-Host "[err] $($_.Exception.Message)"
    exit 3
}

Write-Host ""
Write-Host "== Re-check after install =="
Run-Checks
if ($requiredIssues.Count -eq 0) { exit 0 }
exit 3
