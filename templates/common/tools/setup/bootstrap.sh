#!/usr/bin/env bash
set -euo pipefail

MODE="doctor"
WITH_OPTIONAL=0
NON_INTERACTIVE=0

usage() {
  cat <<'USAGE'
Usage: tools/setup/bootstrap.sh [--doctor|--install] [--with-optional] [--non-interactive]

Modes:
  --doctor            Validate required/optional tools (default)
  --install           Attempt best-effort installation, then validate

Options:
  --with-optional     Also install optional tools
  --non-interactive   Use non-interactive install flags where possible
  -h, --help          Show this help

Exit codes:
  0: required toolchain satisfied
  2: missing/old required dependencies remain
  3: installation attempted but failed/partial
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --doctor)
      MODE="doctor"
      shift
      ;;
    --install)
      MODE="install"
      shift
      ;;
    --with-optional)
      WITH_OPTIONAL=1
      shift
      ;;
    --non-interactive)
      NON_INTERACTIVE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

ver_ge() {
  # shellcheck disable=SC2018,SC2019
  [[ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" == "$2" ]]
}

cmake_ok=0
compiler_ok=0
ninja_ok=0
clang_format_ok=0
ccache_ok=0

required_issues=()
optional_issues=()

check_cmake() {
  if command -v cmake >/dev/null 2>&1; then
    local ver
    ver="$(cmake --version | head -n1 | grep -Eo '[0-9]+(\.[0-9]+)+')"
    if ver_ge "$ver" "3.20"; then
      cmake_ok=1
      echo "[ok] cmake $ver"
    else
      required_issues+=("cmake version too old ($ver < 3.20)")
      echo "[err] cmake $ver (need >= 3.20)"
    fi
  else
    required_issues+=("cmake not found")
    echo "[err] cmake not found"
  fi
}

check_compilers() {
  local found_any=0

  if command -v gcc >/dev/null 2>&1; then
    found_any=1
    local gver
    gver="$(gcc -dumpfullversion -dumpversion)"
    if ver_ge "$gver" "11"; then
      compiler_ok=1
      echo "[ok] gcc $gver"
    else
      echo "[warn] gcc $gver (need >= 11)"
    fi
  fi

  if command -v clang >/dev/null 2>&1; then
    found_any=1
    local cver
    cver="$(clang --version | head -n1 | grep -Eo '[0-9]+(\.[0-9]+)+' | head -n1)"
    if ver_ge "$cver" "14"; then
      compiler_ok=1
      echo "[ok] clang $cver"
    else
      echo "[warn] clang $cver (need >= 14)"
    fi
  fi

  if command -v cl >/dev/null 2>&1; then
    found_any=1
    local cl_raw cl_ver
    cl_raw="$(cl 2>&1 | head -n2 | tr -d '\r')"
    cl_ver="$(printf '%s\n' "$cl_raw" | grep -Eo '[0-9]+\.[0-9]+' | head -n1 || true)"
    if [[ -n "$cl_ver" ]] && ver_ge "$cl_ver" "19.34"; then
      compiler_ok=1
      echo "[ok] msvc $cl_ver"
    else
      echo "[warn] msvc detected but version parse/minimum failed (need >= 19.34)"
    fi
  fi

  if [[ $found_any -eq 0 ]]; then
    required_issues+=("no supported compiler found (need GCC >=11, Clang >=14, or MSVC >=19.34)")
    echo "[err] no supported compiler found"
  elif [[ $compiler_ok -ne 1 ]]; then
    required_issues+=("compiler found but below minimum (need GCC >=11, Clang >=14, or MSVC >=19.34)")
    echo "[err] compiler found but below minimum"
  fi
}

check_optional() {
  if command -v ninja >/dev/null 2>&1; then
    ninja_ok=1
    echo "[ok] ninja $(ninja --version 2>/dev/null || echo unknown)"
  else
    optional_issues+=("ninja not found (optional, recommended for ninja presets)")
    echo "[warn] ninja not found (optional)"
  fi

  if command -v clang-format >/dev/null 2>&1; then
    clang_format_ok=1
    echo "[ok] clang-format"
  else
    optional_issues+=("clang-format not found (optional, recommended)")
    echo "[warn] clang-format not found (optional)"
  fi

  if [[ "$(uname -s)" != "MINGW"* && "$(uname -s)" != "MSYS"* && "$(uname -s)" != "CYGWIN"* ]]; then
    if command -v ccache >/dev/null 2>&1; then
      ccache_ok=1
      echo "[ok] ccache"
    else
      optional_issues+=("ccache not found (optional)")
      echo "[warn] ccache not found (optional)"
    fi
  fi
}

install_with_manager() {
  local manager="$1"
  shift
  local pkgs=("$@")

  if [[ ${#pkgs[@]} -eq 0 ]]; then
    return 0
  fi

  echo "Installing via $manager: ${pkgs[*]}"
  case "$manager" in
    brew)
      brew install "${pkgs[@]}"
      ;;
    apt)
      sudo apt-get update
      if [[ $NON_INTERACTIVE -eq 1 ]]; then
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${pkgs[@]}"
      else
        sudo apt-get install -y "${pkgs[@]}"
      fi
      ;;
    dnf)
      sudo dnf install -y "${pkgs[@]}"
      ;;
    pacman)
      sudo pacman -Sy --noconfirm "${pkgs[@]}"
      ;;
    *)
      echo "Unsupported manager: $manager" >&2
      return 1
      ;;
  esac
}

run_install() {
  local uname_s
  uname_s="$(uname -s)"

  local required_pkgs=()
  local optional_pkgs=()

  if [[ "$uname_s" == "Darwin" ]]; then
    if ! command -v brew >/dev/null 2>&1; then
      echo "[err] Homebrew not found. Install brew first: https://brew.sh"
      return 1
    fi
    required_pkgs=(cmake)
    if [[ $compiler_ok -ne 1 ]]; then
      echo "[warn] Compiler baseline unmet. Install Xcode Command Line Tools manually: xcode-select --install"
    fi
    optional_pkgs=(ninja clang-format ccache)
    install_with_manager brew "${required_pkgs[@]}"
    if [[ $WITH_OPTIONAL -eq 1 ]]; then
      install_with_manager brew "${optional_pkgs[@]}"
    fi
    return 0
  fi

  if [[ "$uname_s" == "Linux" ]]; then
    if command -v apt-get >/dev/null 2>&1; then
      required_pkgs=(cmake build-essential)
      optional_pkgs=(ninja-build clang-format ccache)
      install_with_manager apt "${required_pkgs[@]}"
      if [[ $WITH_OPTIONAL -eq 1 ]]; then
        install_with_manager apt "${optional_pkgs[@]}"
      fi
      return 0
    fi

    if command -v dnf >/dev/null 2>&1; then
      required_pkgs=(cmake gcc-c++ make)
      optional_pkgs=(ninja-build clang-tools-extra ccache)
      install_with_manager dnf "${required_pkgs[@]}"
      if [[ $WITH_OPTIONAL -eq 1 ]]; then
        install_with_manager dnf "${optional_pkgs[@]}"
      fi
      return 0
    fi

    if command -v pacman >/dev/null 2>&1; then
      required_pkgs=(cmake base-devel)
      optional_pkgs=(ninja clang ccache)
      install_with_manager pacman "${required_pkgs[@]}"
      if [[ $WITH_OPTIONAL -eq 1 ]]; then
        install_with_manager pacman "${optional_pkgs[@]}"
      fi
      return 0
    fi

    echo "[err] No supported Linux package manager detected (apt/dnf/pacman)."
    return 1
  fi

  echo "[err] Install mode unsupported in this shell for OS: $uname_s"
  echo "      On Windows, use tools/setup/bootstrap.ps1"
  return 1
}

run_checks() {
  required_issues=()
  optional_issues=()
  cmake_ok=0
  compiler_ok=0
  ninja_ok=0
  clang_format_ok=0
  ccache_ok=0

  echo "== Toolchain doctor =="
  check_cmake
  check_compilers
  check_optional

  echo
  if [[ ${#required_issues[@]} -eq 0 ]]; then
    echo "Required dependencies: satisfied"
  else
    echo "Required dependencies: missing/invalid"
    for issue in "${required_issues[@]}"; do
      echo "  - $issue"
    done
  fi

  if [[ ${#optional_issues[@]} -eq 0 ]]; then
    echo "Optional dependencies: satisfied"
  else
    echo "Optional dependencies: recommendations"
    for issue in "${optional_issues[@]}"; do
      echo "  - $issue"
    done
  fi
}

run_checks

if [[ "$MODE" == "doctor" ]]; then
  if [[ ${#required_issues[@]} -eq 0 ]]; then
    exit 0
  fi
  exit 2
fi

echo
echo "== Install mode =="
if ! run_install; then
  echo "[err] Installation attempt failed."
  exit 3
fi

echo
echo "== Re-check after install =="
run_checks

if [[ ${#required_issues[@]} -eq 0 ]]; then
  exit 0
fi
exit 3
