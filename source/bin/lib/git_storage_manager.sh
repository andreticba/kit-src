#!/usr/bin/env bash
# git_storage_manager.sh | Vitalia SDD v0.6.0 | 31-10-2026
# Gestão modular de repositórios Git de memória (session e data_storage).
# Referência: FR-011, NF-001, NF-002.

[ -n "${_VITALIA_GIT_STORAGE_LOADED:-}" ] && return 0
_VITALIA_GIT_STORAGE_LOADED=1

# Carrega logger se disponível
_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v log_ok &>/dev/null && [ -f "${_LIB_DIR}/logger.sh" ]; then
    # shellcheck source=/dev/null
    source "${_LIB_DIR}/logger.sh"
else
    log_ok()    { echo "   ✅ $*"; }
    log_warn()  { echo "   ⚠️  $*"; }
    log_error() { echo "   ❌ $*" >&2; }
fi

setup_git_repo() {
    local repo_path="${1:-}"
    local remote_url="${2:-}"
    local commit_msg="${3:-init: storage}"
    local initial_subdirs="${4:-}"

    if [ -z "${repo_path}" ]; then
        log_error "setup_git_repo requer o caminho do repositório"
        return 1
    fi

    mkdir -p "${repo_path}"

    # Cria subdiretórios se solicitados
    if [ -n "${initial_subdirs}" ]; then
        for sub in ${initial_subdirs}; do
            mkdir -p "${repo_path}/${sub}"
        done
    fi

    if [ -d "${repo_path}/.git" ]; then
        if [ -n "${remote_url}" ]; then
            git -C "${repo_path}" remote set-url origin "${remote_url}" 2>/dev/null \
                || git -C "${repo_path}" remote add origin "${remote_url}" 2>/dev/null \
                || true
        fi
        return 0
    fi

    # Inicialização de novo repo Git
    git -C "${repo_path}" init -b main 2>/dev/null || git -C "${repo_path}" init 2>/dev/null || true

    if [ -n "${remote_url}" ]; then
        git -C "${repo_path}" remote add origin "${remote_url}" 2>/dev/null || true
    fi

    touch "${repo_path}/.gitkeep"
    git -C "${repo_path}" add . 2>/dev/null || true
    git -C "${repo_path}" commit -m "${commit_msg}" 2>/dev/null || true

    if [ -n "${remote_url}" ]; then
        git -C "${repo_path}" push -u origin main 2>/dev/null || true
    fi

    return 0
}

setup_session_repo() {
    local memory_dir="${1:-}"
    local remote_url="${2:-}"

    local session_path="${memory_dir}/session"
    setup_git_repo "${session_path}" "${remote_url}" "init: session tracking" ""

    if [ -n "${remote_url}" ]; then
        log_ok "Sessão: ${remote_url}"
    else
        log_ok "Sessão: ${session_path} (local)"
    fi
}

setup_data_repo() {
    local memory_dir="${1:-}"
    local remote_url="${2:-}"

    local data_path="${memory_dir}/data_storage"
    setup_git_repo "${data_path}" "${remote_url}" "init: data storage" "reviews research specs handoffs"

    if [ -n "${remote_url}" ]; then
        log_ok "Dados: ${remote_url}"
    else
        log_ok "Dados: ${data_path} (local)"
    fi
}
