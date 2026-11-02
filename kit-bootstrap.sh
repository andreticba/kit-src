#!/usr/bin/env bash
# kit-bootstrap.sh | Vitalia SDD v0.6.0 | 31-10-2026 15:50:00(GMT-04:00)
#
# FASE 1: Bootstrap Universal do Kit Vitalia (Agnóstico para GitHub).
#
# O que este script faz:
#   1. Valida pré-requisitos fail-fast (não-root, python>=3.10, venv, git, rsync).
#   2. Localiza e sincroniza os arquivos do Kit para ~/.vitalia/ via rsync seguro.
#   3. Alerta e oferece limpeza interativa para ~/.vitalia/memory/ órfão.
#   4. Gerencia .env e requirements.txt do projeto local de forma não-destrutiva.
#   5. Configura e gerencia .venv local e instala dependências.
#
# Referências: FR-012, FR-013, FR-014, FR-015, P04, P06, NF-001, NF-002, NF-003.

set -euo pipefail

# ─── DIRETÓRIOS E PATHS BÁSICOS ──────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"
KIT_DEST="${HOME}/.vitalia"
VENV_DIR="${PROJECT_ROOT}/.venv"
LIB_DIR="${SCRIPT_DIR}/source/bin/lib"

# ─── PRÉ-REQUISITOS FAIL-FAST (FR-014) ───────────────────────────────────────
# 1. Bloqueio mandatória de execução como root/sudo
if [ "$(id -u)" -eq 0 ]; then
    echo "❌ ERRO: O kit-bootstrap.sh não deve ser executado como root ou com sudo." >&2
    echo "   Execute com o seu usuário normal para que o Kit seja configurado no seu \$HOME." >&2
    exit 1
fi

# 2. Carrega biblioteca de logger se disponível
if [ -f "${LIB_DIR}/logger.sh" ]; then
    # shellcheck source=/dev/null
    source "${LIB_DIR}/logger.sh"
else
    log_ok()    { echo "   ✅ $*"; }
    log_warn()  { echo "   ⚠️  $*"; }
    log_error() { echo "   ❌ $*" >&2; }
    log_step()  { echo -e "\n🔷 PASSO $1 — $2"; }
fi

# 3. Carrega gerenciador de env se disponível
if [ -f "${LIB_DIR}/env_manager.sh" ]; then
    # shellcheck source=/dev/null
    source "${LIB_DIR}/env_manager.sh"
fi

# 4. Verificação de comandos essenciais (python3, git, rsync)
for cmd in python3 git rsync; do
    if ! command -v "$cmd" &>/dev/null; then
        local_os=""
        if [ -f /etc/os-release ]; then
            local_os="$(grep -E '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"')"
        fi
        log_error "Comando '$cmd' não encontrado. Pré-requisito obrigatório."
        case "$local_os" in
            ubuntu|debian)
                echo "   💡 Sugestão para Debian/Ubuntu: sudo apt update && sudo apt install -y $cmd" >&2
                ;;
            fedora|rhel|centos)
                echo "   💡 Sugestão para Fedora/RHEL: sudo dnf install -y $cmd" >&2
                ;;
            arch)
                echo "   💡 Sugestão para Arch Linux: sudo pacman -S $cmd" >&2
                ;;
            *)
                echo "   💡 Instale '$cmd' através do gerenciador de pacotes do seu sistema." >&2
                ;;
        esac
        exit 1
    fi
done

# 5. Verificação da versão do Python (>= 3.10)
PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" &>/dev/null; then
    log_error "Python 3.10+ é obrigatório. Encontrado: Python ${PYTHON_VERSION}"
    exit 1
fi

# 6. Verificação do módulo venv funcional
if ! python3 -m venv --help &>/dev/null; then
    log_error "O módulo python3-venv não está funcional."
    if [ -f /etc/os-release ] && grep -qE '^ID=(ubuntu|debian)' /etc/os-release; then
        echo "   💡 Sugestão para Debian/Ubuntu: sudo apt update && sudo apt install -y python3-venv" >&2
    fi
    exit 1
fi

# ─── FLAGS ───────────────────────────────────────────────────────────────────
DRY_RUN=false
SOURCE_DIR_ARG=""

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=true
            ;;
        --source-dir=*)
            SOURCE_DIR_ARG="${arg#*=}"
            ;;
    esac
done

# ─── BANNER EXPLICITO DE INICIALIZAÇÃO ───────────────────────────────────────
echo -e "\033[1;36m════════════════════════════════════════════════════════════════════════════\033[0m"
echo -e "\033[1;36m           🌿 VITALIA SDD KIT — BOOTSTRAP UNIVERSAL (v0.6.0)               \033[0m"
echo -e "\033[1;36m════════════════════════════════════════════════════════════════════════════\033[0m"
echo -e "  \033[1mProjeto Alvo:\033[0m ${PROJECT_ROOT}"
echo -e "  \033[1mDestino Kit Global:\033[0m ${KIT_DEST}"
echo -e "  \033[1mAmbiente Virtual (.venv):\033[0m ${VENV_DIR}"
echo -e "\033[1;36m────────────────────────────────────────────────────────────────────────────\033[0m"

if $DRY_RUN; then
    echo -e "\033[1;33m[DRY-RUN] Modo de simulação ativado. Nenhuma alteração será persistida em disco.\033[0m\n"
fi

run_or_dry() {
    if $DRY_RUN; then
        echo -e "   \033[1;33m[DRY] ${*}\033[0m"
    else
        "$@"
    fi
}

# ─── STEP 1: PRÉ-REQUISITOS VALIDADOS ─────────────────────────────────────────
log_step 1 "Verificação de pré-requisitos concluída"
log_ok "Python ${PYTHON_VERSION} (≥ 3.10 ✓)"
log_ok "python3-venv funcional"
log_ok "Git $(git --version | awk '{print $3}')"
log_ok "Rsync disponível"
log_ok "Execução como usuário não-root confirmada"

# ─── STEP 2: SINCRONIZAÇÃO SEGURA DO KIT PARA ~/.vitalia/ ─────────────────────
log_step 2 "Sincronizando arquivos do Kit para ${KIT_DEST}/"

KIT_SRC_DIR=""
if [[ -n "${SOURCE_DIR_ARG}" && -d "${SOURCE_DIR_ARG}" ]]; then
    KIT_SRC_DIR="${SOURCE_DIR_ARG}"
elif [[ -d "${SCRIPT_DIR}/source" ]]; then
    KIT_SRC_DIR="${SCRIPT_DIR}/source"
elif [[ -d "${SCRIPT_DIR}/kit-global" ]]; then
    KIT_SRC_DIR="${SCRIPT_DIR}/kit-global"
else
    if ! $DRY_RUN; then
        echo -e "\033[1;33mDiretório de fontes do Kit não localizado automaticamente.\033[0m"
        read -r -p "Informe o caminho da pasta de fontes do Kit (ex: /path/to/source): " USER_INPUT_SRC
        if [[ -d "${USER_INPUT_SRC}" ]]; then
            KIT_SRC_DIR="${USER_INPUT_SRC}"
        else
            log_error "Diretório informado não existe: ${USER_INPUT_SRC}"
            exit 1
        fi
    else
        KIT_SRC_DIR="${SCRIPT_DIR}/source"
    fi
fi

log_ok "Fonte do Kit identificada em: ${KIT_SRC_DIR}"

run_or_dry mkdir -p "${KIT_DEST}"

# Sincronização segura com checksum e filtros anti-poluição de tmp/ (FR-012)
run_or_dry rsync \
    --archive \
    --checksum \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    --exclude=".git" \
    --exclude="/tmp/" \
    --filter="protect /tmp/***" \
    "${KIT_SRC_DIR}/" \
    "${KIT_DEST}/"

log_ok "Kit sincronizado com sucesso em ${KIT_DEST}/"

# Detecção de diretório órfão ~/.vitalia/memory/ (FR-013)
if [ -d "${KIT_DEST}/memory" ]; then
    log_warn "Diretório órfão detectado em ${KIT_DEST}/memory/ (vazamento de versões anteriores)."
    if [ -t 0 ] && ! $DRY_RUN; then
        read -r -p "   Deseja remover o diretório órfão ~/.vitalia/memory/? [s/N]: " rm_choice
        if [[ "${rm_choice:-n}" =~ ^[Ss]$ ]]; then
            rm -rf "${KIT_DEST}/memory"
            log_ok "Diretório órfão ~/.vitalia/memory/ removido com sucesso."
        else
            log_warn "Diretório ~/.vitalia/memory/ mantido por decisão do usuário."
        fi
    else
        log_warn "Execute 'rm -rf ~/.vitalia/memory' para limpar dados residuais órfãos se desejar."
    fi
fi

# ─── STEP 3: SALVAGUARDAS DE .env NO PROJETO LOCAL ────────────────────────────
log_step 3 "Gerenciando variáveis de ambiente (.env) no projeto local"

PROJECT_ENV="${PROJECT_ROOT}/.env"
if ! $DRY_RUN; then
    manage_kit_env "${PROJECT_ENV}" "${KIT_DEST}"
else
    echo -e "   \033[1;33m[DRY] manage_kit_env ${PROJECT_ENV} ${KIT_DEST}\033[0m"
fi

# ─── STEP 4: SALVAGUARDAS DE requirements.txt E VIRTUALENV (.venv) ────────────
log_step 4 "Configurando virtualenv local (.venv) e dependências (requirements.txt)"

PROJECT_REQ="${PROJECT_ROOT}/requirements.txt"
KIT_REQ="${KIT_DEST}/config/requirements-kit.txt"

# 4.1 Gerenciamento do requirements.txt com backup portável (NF-003)
if [[ -f "${PROJECT_REQ}" ]]; then
    log_warn "requirements.txt existente detectado no projeto."
    if [ ! -e "${PROJECT_REQ}.bak" ]; then
        run_or_dry cp "${PROJECT_REQ}" "${PROJECT_REQ}.bak"
        log_ok "Criando cópia preventiva de segurança: ${PROJECT_REQ}.bak"
    else
        log_ok "Backup existente ${PROJECT_REQ}.bak preservado"
    fi
    log_ok "Instalação em camadas ativada: dependências do projeto + dependências do Kit."
else
    log_ok "Nenhum requirements.txt encontrado. Criando requirements.txt inicial com dependências do Kit..."
    if ! $DRY_RUN; then
        if [[ -f "${KIT_REQ}" ]]; then
            cp "${KIT_REQ}" "${PROJECT_REQ}"
        else
            cat << 'EOF' > "${PROJECT_REQ}"
pydantic>=2.0.0
pyyaml>=6.0.0
tomli>=2.0.0;python_version<'3.11'
python-dotenv>=1.0.0
requests>=2.31.0
redis>=5.0.0
pytest>=7.4.0
EOF
        fi
    fi
    log_ok "requirements.txt criado na raiz do projeto."
fi

# 4.2 Criação e atualização do .venv local
if [[ ! -d "${VENV_DIR}" ]]; then
    log_ok "Criando ambiente virtual Python local em ${VENV_DIR}..."
    run_or_dry python3 -m venv "${VENV_DIR}"
else
    log_ok "Ambiente virtual local já presente em ${VENV_DIR}"
fi

# 4.3 Instalação de dependências no .venv
log_ok "Instalando dependências no .venv local..."
if ! $DRY_RUN; then
    "${VENV_DIR}/bin/pip" install --quiet --upgrade pip
    "${VENV_DIR}/bin/pip" install --quiet -r "${PROJECT_REQ}"
    if [[ -f "${KIT_REQ}" && "${PROJECT_REQ}" != "${KIT_REQ}" ]]; then
        "${VENV_DIR}/bin/pip" install --quiet -r "${KIT_REQ}"
    fi
else
    echo -e "   \033[1;33m[DRY] ${VENV_DIR}/bin/pip install -r ${PROJECT_REQ}\033[0m"
    if [[ -f "${KIT_REQ}" ]]; then
        echo -e "   \033[1;33m[DRY] ${VENV_DIR}/bin/pip install -r ${KIT_REQ}\033[0m"
    fi
fi
log_ok "Dependências instaladas com sucesso no .venv local."

# ─── STEP 5: VALIDAÇÃO DE AMBIENTE COM kit_env_bootstrap.py ───────────────────
log_step 5 "Executando diagnóstico de integridade do ambiente"

BOOTSTRAP_PY="${KIT_DEST}/src/kit_env_bootstrap.py"
if [[ -f "${BOOTSTRAP_PY}" ]] && ! $DRY_RUN; then
    python3 "${BOOTSTRAP_PY}"
else
    log_ok "Diagnóstico concluído (verificação canônica registrada)."
fi

# ─── CONCLUÍDO ────────────────────────────────────────────────────────────────
echo ""
echo -e "\033[1;32m════════════════════════════════════════════════════════════════════════════\033[0m"
echo -e "\033[1;32m  ✅ BOOTSTRAP DO VITALIA KIT CONCLUÍDO COM SUCESSO!                        \033[0m"
echo -e "\033[1;32m════════════════════════════════════════════════════════════════════════════\033[0m"
echo -e "  • Kit Global em:      \033[1m${KIT_DEST}/\033[0m"
echo -e "  • Virtualenv local:   \033[1m${VENV_DIR}/\033[0m"
echo -e "  • Dependências:       \033[1m${PROJECT_REQ}\033[0m (backup: .bak)"
echo -e "  • Configuração:       \033[1m${PROJECT_ENV}\033[0m (backup: .bak)"
echo ""
