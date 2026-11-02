#!/usr/bin/env bash
# redis_detector.sh | Vitalia SDD v0.6.0 | 31-10-2026
# Detecção e probe resiliente de Redis com leitura prévia do .env, sanitização de senhas e fallback.
# Referência: FR-010, FR-017, P06, NF-001, NF-002.

[ -n "${_VITALIA_REDIS_DETECTOR_LOADED:-}" ] && return 0
_VITALIA_REDIS_DETECTOR_LOADED=1

# Carrega dependências se disponíveis
_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v log_ok &>/dev/null && [ -f "${_LIB_DIR}/logger.sh" ]; then
    # shellcheck source=/dev/null
    source "${_LIB_DIR}/logger.sh"
fi
if ! command -v has_env_var &>/dev/null && [ -f "${_LIB_DIR}/env_manager.sh" ]; then
    # shellcheck source=/dev/null
    source "${_LIB_DIR}/env_manager.sh"
fi

detect_redis() {
    local env_file="${1:-}"
    local default_url="redis://localhost:6379/0"

    # 1. Lê REDIS_URL do .env existente antes de fazer o probe (FR-010)
    if [ -n "${env_file}" ] && [ -f "${env_file}" ]; then
        if command -v has_env_var &>/dev/null && has_env_var "REDIS_URL" "${env_file}"; then
            REDIS_URL="$(get_env_var "REDIS_URL" "${env_file}")"
        fi
    fi
    REDIS_URL="${REDIS_URL:-${default_url}}"

    # Sanitização mandatória de senha para console/logs (P06, SEC-01)
    local masked_url
    if command -v mask_credential &>/dev/null; then
        masked_url="$(mask_credential "${REDIS_URL}")"
    else
        masked_url="$(echo "${REDIS_URL}" | sed -E 's/(:\/\/[^:]+:)[^@]+(@)/\1****\2/')"
    fi

    REDIS_ENABLED="false"

    if command -v redis-cli &>/dev/null; then
        if redis-cli -u "${REDIS_URL}" ping 2>/dev/null | grep -q "PONG"; then
            log_ok "Redis detectado em ${masked_url}"
            local choice="S"
            if [ -t 0 ]; then
                read -r -p "   Ativar modo Redis-first (estado do workflow via Redis)? [S/n]: " choice
            fi
            choice="${choice:-S}"
            if [[ "${choice}" =~ ^[Ss]$ ]]; then
                REDIS_ENABLED="true"
                log_ok "Modo Redis-first ativado"
            else
                log_ok "Usando modo arquivo (fallback)"
            fi
        else
            log_warn "Redis não respondeu em ${masked_url}. Usando modo arquivo."
        fi
    else
        log_warn "redis-cli não instalado. Usando modo arquivo."
    fi

    export REDIS_ENABLED
    export REDIS_URL
}
