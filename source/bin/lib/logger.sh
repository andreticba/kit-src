#!/usr/bin/env bash
# logger.sh | Vitalia SDD v0.6.0 | 31-10-2026
# Biblioteca de logging padronizado com suporte ANSI, compatível com bash 3.2+ e set -euo pipefail.
# Referência: FR-006, NF-001, NF-002.

[ -n "${_VITALIA_LOGGER_LOADED:-}" ] && return 0
_VITALIA_LOGGER_LOADED=1

_VIT_RED='\033[0;31m'
_VIT_GREEN='\033[0;32m'
_VIT_YELLOW='\033[1;33m'
_VIT_CYAN='\033[0;36m'
_VIT_BOLD='\033[1m'
_VIT_NC='\033[0m'

log_ok() {
    echo -e "${_VIT_GREEN}   ✅ $*${_VIT_NC}"
}

log_warn() {
    echo -e "${_VIT_YELLOW}   ⚠️  $*${_VIT_NC}"
}

log_error() {
    echo -e "${_VIT_RED}   ❌ $*${_VIT_NC}" >&2
}

log_step() {
    local step_num="${1:-}"
    local step_desc="${2:-}"
    echo -e "\n${_VIT_BOLD}${_VIT_CYAN}🔷 PASSO ${step_num} — ${step_desc}${_VIT_NC}"
}
