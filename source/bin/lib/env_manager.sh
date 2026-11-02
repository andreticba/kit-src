#!/usr/bin/env bash
# env_manager.sh | Vitalia SDD v0.6.0 | 31-10-2026
# Biblioteca de gestão idempotente e segura de variáveis em .env (Matriz S1–S7).
# Referência: FR-007, FR-017, P06 (Secrets), NF-001, NF-002, NF-003.

[ -n "${_VITALIA_ENV_MANAGER_LOADED:-}" ] && return 0
_VITALIA_ENV_MANAGER_LOADED=1

# Carrega logger se disponível no mesmo diretório
if ! command -v log_ok &>/dev/null; then
    _LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "${_LIB_DIR}/logger.sh" ]; then
        # shellcheck source=/dev/null
        source "${_LIB_DIR}/logger.sh"
    else
        log_ok()    { echo "   ✅ $*"; }
        log_warn()  { echo "   ⚠️  $*"; }
        log_error() { echo "   ❌ $*" >&2; }
        log_step()  { echo -e "\n🔷 PASSO $1 — $2"; }
    fi
fi

mask_credential() {
    local val="${1:-}"
    if [ -z "$val" ]; then
        echo ""
        return 0
    fi
    # Se contiver URL com credenciais (ex: scheme://user:password@host:port)
    if echo "$val" | grep -E '://[^:]+:[^@]+@' >/dev/null 2>&1; then
        echo "$val" | sed -E 's/(:\/\/[^:]+:)[^@]+(@)/\1****\2/'
        return 0
    fi
    # Se for chave/token longo (> 12 chars), mascara o miolo
    local len="${#val}"
    if [ "$len" -gt 12 ]; then
        local prefix="${val:0:4}"
        local suffix="${val: -4}"
        echo "${prefix}****${suffix}"
        return 0
    fi
    echo "$val"
}

has_env_var() {
    local var_name="${1:-}"
    local env_file="${2:-}"
    [ -f "${env_file}" ] || return 1
    grep -E '^[[:space:]]*(export[[:space:]]+)?'"${var_name}"'[[:space:]]*=' "${env_file}" >/dev/null 2>&1
}

get_env_var() {
    local var_name="${1:-}"
    local env_file="${2:-}"
    [ -f "${env_file}" ] || return 1
    sed -n -E 's/^[[:space:]]*(export[[:space:]]+)?'"${var_name}"'[[:space:]]*=[[:space:]]*//p' "${env_file}" \
        | head -n 1 \
        | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

ensure_env_file() {
    local env_file="${1:-}"
    local template_content="${2:-}"

    local dir_path
    dir_path="$(dirname "${env_file}")"

    # S7: Sem permissão de escrita
    if [ -f "${env_file}" ] && [ ! -w "${env_file}" ]; then
        log_warn "[ALERTA] configure manualmente: sem permissão de escrita em ${env_file}"
        return 1
    fi
    if [ ! -f "${env_file}" ] && [ ! -w "${dir_path}" ]; then
        log_warn "[ALERTA] configure manualmente: sem permissão de criação em ${dir_path}"
        return 1
    fi

    # S1: .env ausente → cria a partir do template
    if [ ! -f "${env_file}" ]; then
        if [ -n "${template_content}" ]; then
            printf "%s\n" "${template_content}" > "${env_file}"
        else
            cat << 'EOF' > "${env_file}"
# .env | Vitalia SDD Kit
VITALIA_ENVIRONMENT=development
REDIS_URL=redis://localhost:6379/0
EOF
        fi
        log_ok "[CRIADO] ${env_file} inicializado a partir do template"
        return 0
    fi

    # S2 e S3: .env presente → gerenciar backup
    local bak_file="${env_file}.bak"
    if [ -e "${bak_file}" ]; then
        # S3: .env.bak já existe → preservar backup histórico
        log_ok "[BACKUP] preservado (${bak_file} histórico mantido)"
    else
        # S2: .env presente sem backup → criar .env.bak (NF-003: portável sem cp -n)
        cp "${env_file}" "${bak_file}"
        log_ok "[BACKUP] criado (${bak_file})"
    fi
    return 0
}

ensure_env_var() {
    local var_name="${1:-}"
    local default_val="${2:-}"
    local env_file="${3:-}"
    local comment="${4:-}"

    # S7: Sem permissão de escrita
    if [ -f "${env_file}" ] && [ ! -w "${env_file}" ]; then
        log_warn "[ALERTA] configure manualmente: sem permissão de escrita em ${env_file}"
        return 1
    fi

    if has_env_var "${var_name}" "${env_file}"; then
        local current_val
        current_val="$(get_env_var "${var_name}" "${env_file}")"
        local masked_val
        masked_val="$(mask_credential "${current_val}")"

        if [ "${current_val}" = "${default_val}" ]; then
            # S4: Variável com valor padrão mantida
            log_ok "[PRESERVADA] ${var_name} (valor padrão: ${masked_val})"
        else
            # S5: Variável customizada mantida e não duplicada
            log_ok "[PRESERVADA] valor customizado: ${var_name}=${masked_val}"
        fi
    else
        # S6: Variável ausente → acrescenta ao final
        local masked_default
        masked_default="$(mask_credential "${default_val}")"
        if [ -n "${comment}" ]; then
            printf "\n# %s\n" "${comment}" >> "${env_file}"
        fi
        printf "%s=%s\n" "${var_name}" "${default_val}" >> "${env_file}"
        log_ok "[ADICIONADA] ${var_name}=${masked_default}"
    fi
    return 0
}

manage_kit_env() {
    local env_file="${1:-}"
    local kit_dir_val="${2:-}"

    if [ -z "${env_file}" ]; then
        log_error "manage_kit_env requer o caminho do arquivo .env"
        return 1
    fi

    # Garante que o arquivo e backup existam (S1–S3, S7)
    ensure_env_file "${env_file}" || return 1

    # VITALIA_ENVIRONMENT (padrão: development)
    ensure_env_var "VITALIA_ENVIRONMENT" "development" "${env_file}" "Ambiente de execução do Vitalia Kit"

    # REDIS_URL unificado (FR-017: redis://localhost:6379/0)
    ensure_env_var "REDIS_URL" "redis://localhost:6379/0" "${env_file}" "Instância Redis local para estado e cache"

    # VITALIA_KIT_DIR (apenas se especificado)
    if [ -n "${kit_dir_val}" ]; then
        ensure_env_var "VITALIA_KIT_DIR" "${kit_dir_val}" "${env_file}" "Diretório de instalação global do Vitalia Kit"
    fi

    # GEMINI_API_KEY (pulada se GOOGLE_API_KEY existir; nunca preenchida com segredo)
    if has_env_var "GOOGLE_API_KEY" "${env_file}"; then
        log_ok "[PRESERVADA] GEMINI_API_KEY ignorada (GOOGLE_API_KEY já configurada no .env)"
    elif has_env_var "GEMINI_API_KEY" "${env_file}"; then
        local current_key
        current_key="$(get_env_var "GEMINI_API_KEY" "${env_file}")"
        log_ok "[PRESERVADA] GEMINI_API_KEY existente ($(mask_credential "${current_key}"))"
    else
        # S6: placeholder vazio com comentário
        ensure_env_var "GEMINI_API_KEY" "" "${env_file}" "Chave da API Google/Gemini (opcional se usar Ollama/local)"
    fi

    return 0
}
