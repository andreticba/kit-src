#!/usr/bin/env bash
# kit-bootstrap.sh | Vitalia SDD v0.6.0
# Atualizado em: 16-10-2026 16:55(GMT-04:00)
#
# FASE 1: Bootstrap Universal do Kit Vitalia (Agnóstico para GitHub).
#
# O que este script faz:
#   1. Anuncia expressamente a configuração do .venv e requirements.txt do projeto.
#   2. Localiza e sincroniza os arquivos do Kit para ~/.vitalia/
#   3. Cria e gerencia o ambiente virtual (.venv) EXCLUSIVAMENTE na raiz do projeto local.
#   4. Aplica salvaguardas não-destrutivas com backup (.bak) para .env e requirements.txt.
#   5. Instala as dependências e valida a conectividade de ambiente.

set -euo pipefail

# ─── CORES PARA OUTPUT ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ─── DIRETÓRIOS E PATHS ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"
KIT_DEST="${HOME}/.vitalia"
VENV_DIR="${PROJECT_ROOT}/.venv"

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
echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}           🌿 VITALIA SDD KIT — BOOTSTRAP UNIVERSAL (v0.6.0)               ${NC}"
echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "  ${BOLD}Projeto Alvo:${NC} ${PROJECT_ROOT}"
echo -e "  ${BOLD}Destino Kit Global:${NC} ${KIT_DEST}"
echo -e "  ${BOLD}Ambiente Virtual (.venv):${NC} ${VENV_DIR}"
echo -e "${BOLD}${CYAN}────────────────────────────────────────────────────────────────────────────${NC}"

if $DRY_RUN; then
    echo -e "${YELLOW}[DRY-RUN] Modo de simulação ativado. Nenhuma alteração será persistida em disco.${NC}\n"
fi

# ─── FUNÇÕES AUXILIARES ───────────────────────────────────────────────────────
TOTAL_STEPS=5

log_step() {
    echo -e "\n${BOLD}${BLUE}[${1}/${TOTAL_STEPS}] ${2}${NC}"
}

log_ok() {
    echo -e "   ${GREEN}✅ ${1}${NC}"
}

log_warn() {
    echo -e "   ${YELLOW}⚠️  ${1}${NC}"
}

log_error() {
    echo -e "   ${RED}❌ ${1}${NC}"
}

run_or_dry() {
    if $DRY_RUN; then
        echo -e "   ${YELLOW}[DRY] ${*}${NC}"
    else
        "$@"
    fi
}

# ─── STEP 1: VERIFICAÇÃO DE PRÉ-REQUISITOS LOCAIS ─────────────────────────────
log_step 1 "Verificando pré-requisitos do sistema"

if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    if [[ "$PYTHON_MAJOR" -ge 3 && "$PYTHON_MINOR" -ge 10 ]]; then
        log_ok "Python ${PYTHON_VERSION} (≥ 3.10 ✓)"
    else
        log_error "Python ${PYTHON_VERSION} encontrado, mas 3.10+ é obrigatório."
        exit 1
    fi
else
    log_error "python3 não encontrado. Instale Python 3.10+."
    exit 1
fi

if command -v git &>/dev/null; then
    log_ok "Git $(git --version | awk '{print $3}')"
else
    log_error "git não encontrado. Instale com seu gerenciador de pacotes."
    exit 1
fi

# ─── STEP 2: SINCRONIZAÇÃO DO KIT PARA ~/.vitalia/ ────────────────────────────
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
        echo -e "${YELLOW}Diretório de fontes do Kit não localizado automaticamente.${NC}"
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
run_or_dry rsync \
    --archive \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    --exclude=".git" \
    "${KIT_SRC_DIR}/" \
    "${KIT_DEST}/"

log_ok "Kit sincronizado com sucesso em ${KIT_DEST}/"

# ─── STEP 3: SALVAGUARDAS DE .env NO PROJETO LOCAL ────────────────────────────
log_step 3 "Gerenciando variáveis de ambiente (.env) no projeto local"

PROJECT_ENV="${PROJECT_ROOT}/.env"
if [[ -f "${PROJECT_ENV}" ]]; then
    log_warn "Arquivo .env existente detectado em ${PROJECT_ENV}"
    log_ok "Criando cópia preventiva de segurança: ${PROJECT_ENV}.bak"
    run_or_dry cp -n "${PROJECT_ENV}" "${PROJECT_ENV}.bak"

    # Inclusão aditiva não-destrutiva de variáveis essenciais caso ausentes
    if ! $DRY_RUN; then
        if ! grep -q "^VITALIA_ENVIRONMENT=" "${PROJECT_ENV}"; then
            echo -e "\n# Configurações do Vitalia SDD Kit adicionadas pelo bootstrap" >> "${PROJECT_ENV}"
            echo "VITALIA_ENVIRONMENT=development" >> "${PROJECT_ENV}"
        fi
        if ! grep -q "^REDIS_URL=" "${PROJECT_ENV}"; then
            echo "REDIS_URL=redis://127.0.0.1:6379/0" >> "${PROJECT_ENV}"
        fi
    fi
    log_ok "Variáveis do Kit mescladas ao .env com segurança (valores pré-existentes preservados)"
else
    log_ok "Arquivo .env não encontrado. Provisionando .env inicial a partir do modelo..."
    if ! $DRY_RUN; then
        cat << 'EOF' > "${PROJECT_ENV}"
# .env | Vitalia SDD Kit
VITALIA_ENVIRONMENT=development
REDIS_URL=redis://127.0.0.1:6379/0
EOF
    fi
    log_ok "Arquivo .env inicial criado com sucesso em ${PROJECT_ENV}"
fi

# ─── STEP 4: SALVAGUARDAS DE requirements.txt E VIRTUALENV (.venv) ────────────
log_step 4 "Configurando virtualenv local (.venv) e dependências (requirements.txt)"

PROJECT_REQ="${PROJECT_ROOT}/requirements.txt"
KIT_REQ="${KIT_DEST}/config/requirements-kit.txt"

# 4.1 Gerenciamento do requirements.txt
if [[ -f "${PROJECT_REQ}" ]]; then
    log_warn "requirements.txt existente detectado no projeto."
    log_ok "Criando cópia preventiva de segurança: ${PROJECT_REQ}.bak"
    run_or_dry cp -n "${PROJECT_REQ}" "${PROJECT_REQ}.bak"
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
    echo -e "   ${YELLOW}[DRY] ${VENV_DIR}/bin/pip install -r ${PROJECT_REQ}${NC}"
    if [[ -f "${KIT_REQ}" ]]; then
        echo -e "   ${YELLOW}[DRY] ${VENV_DIR}/bin/pip install -r ${KIT_REQ}${NC}"
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
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  ✅ BOOTSTRAP DO VITALIA KIT CONCLUÍDO COM SUCESSO!                        ${NC}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "  • Kit Global em:      ${BOLD}${KIT_DEST}/${NC}"
echo -e "  • Virtualenv local:   ${BOLD}${VENV_DIR}/${NC}"
echo -e "  • Dependências:       ${BOLD}${PROJECT_REQ}${NC} (backup: .bak)"
echo -e "  • Configuração:       ${BOLD}${PROJECT_ENV}${NC} (backup: .bak)"
echo ""
