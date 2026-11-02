#!/usr/bin/env bash
# smoke_shell_libs.sh | Vitalia SDD v0.6.0 | 31-10-2026
# Smoke test abrangente e isolado para as 5 bibliotecas shell de source/bin/lib/.
# Referência: T013-B, NF-001, NF-002, NF-003, P05, P06.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LIB_DIR="${REPO_ROOT}/source/bin/lib"

echo "🧪 Iniciando Smoke-Test de Bibliotecas Shell (T013-B)..."

TMP_WORKSPACE="$(mktemp -d)"
trap 'rm -rf "${TMP_WORKSPACE}"' EXIT

# ── 1. TESTE logger.sh ────────────────────────────────────────────────────────
echo -e "\n--- Teste 1: logger.sh ---"
(
    set -euo pipefail
    source "${LIB_DIR}/logger.sh"
    log_step 1 "Verificando saída de logs"
    log_ok "Teste OK"
    log_warn "Teste Aviso"
    log_error "Teste Erro (redirecionado para stderr)"
)

# ── 2. TESTE env_manager.sh COM CASOS DE BORDA ────────────────────────────────
echo -e "\n--- Teste 2: env_manager.sh (Casos de Borda) ---"
(
    set -euo pipefail
    source "${LIB_DIR}/env_manager.sh"
    ENV_FILE="${TMP_WORKSPACE}/.env"

    # Caso 2.1: .env vazio
    touch "${ENV_FILE}"
    ensure_env_file "${ENV_FILE}"
    [ -f "${ENV_FILE}.bak" ] || { echo "Falha: backup não criado para .env existente"; exit 1; }

    # Caso 2.2: Variável com espaços e caracteres especiais
    ensure_env_var "COMPLEX_VAR" "valor com espacos e = caracteres / especiais" "${ENV_FILE}" "Comentário complexo"
    read_val="$(get_env_var "COMPLEX_VAR" "${ENV_FILE}")"
    [ "${read_val}" = "valor com espacos e = caracteres / especiais" ] || { echo "Falha ao ler COMPLEX_VAR: ${read_val}"; exit 1; }

    # Caso 2.3: Idempotência e não-duplicação (S5)
    ensure_env_var "COMPLEX_VAR" "valor_padrao" "${ENV_FILE}"
    count="$(grep -c 'COMPLEX_VAR' "${ENV_FILE}")"
    [ "${count}" -eq 1 ] || { echo "Falha: COMPLEX_VAR duplicada no .env (${count} ocorrências)"; exit 1; }

    # Caso 2.4: manage_kit_env com REDIS_URL customizado e sanitização
    manage_kit_env "${ENV_FILE}" "/home/andre/.vitalia"
    has_env_var "REDIS_URL" "${ENV_FILE}" || { echo "Falha: REDIS_URL ausente"; exit 1; }
    has_env_var "VITALIA_ENVIRONMENT" "${ENV_FILE}" || { echo "Falha: VITALIA_ENVIRONMENT ausente"; exit 1; }

    # Caso 2.5: Mascaramento de credenciais
    masked="$(mask_credential "redis://usuario:senha_ultra_secreta@10.0.0.1:6379/0")"
    if echo "${masked}" | grep -q "senha_ultra_secreta"; then
        echo "Falha: senha vazou no mask_credential!"; exit 1
    fi
    echo "   ✅ env_manager.sh: todos os casos de borda aprovados"
)

# ── 3. TESTE agent_preserver.sh ───────────────────────────────────────────────
echo -e "\n--- Teste 3: agent_preserver.sh (4 Ramos e Manifesto) ---"
(
    set -euo pipefail
    source "${LIB_DIR}/agent_preserver.sh"

    # Ramo 1: Criação inicial
    AGENTS="${TMP_WORKSPACE}/AGENTS.md"
    update_agents_md "${AGENTS}" "Conteúdo Kit v1"
    grep -q "VITALIA:KIT:START" "${AGENTS}" || { echo "Falha Ramo 1: marcadores ausentes"; exit 1; }

    # Ramo 2: Atualização com preservação de customizações do usuário
    printf "Regra personalizada no topo\n" > "${TMP_WORKSPACE}/custom.tmp"
    cat "${AGENTS}" >> "${TMP_WORKSPACE}/custom.tmp"
    printf "Regra personalizada no rodape\n" >> "${TMP_WORKSPACE}/custom.tmp"
    mv "${TMP_WORKSPACE}/custom.tmp" "${AGENTS}"

    update_agents_md "${AGENTS}" "Conteúdo Kit v2 Atualizado"
    grep -q "Regra personalizada no topo" "${AGENTS}" || { echo "Falha Ramo 2: topo perdido"; exit 1; }
    grep -q "Regra personalizada no rodape" "${AGENTS}" || { echo "Falha Ramo 2: rodapé perdido"; exit 1; }
    grep -q "Conteúdo Kit v2 Atualizado" "${AGENTS}" || { echo "Falha Ramo 2: miolo não atualizado"; exit 1; }

    # Ramo 3: Legado do kit
    LEGACY="${TMP_WORKSPACE}/legacy.md"
    echo "# AGENTS.md — Kit Global (versão antiga)" > "${LEGACY}"
    update_agents_md "${LEGACY}" "Conteúdo Kit v2"
    grep -q "VITALIA:KIT:START" "${LEGACY}" || { echo "Falha Ramo 3"; exit 1; }
    ls "${LEGACY}.bak."* >/dev/null || { echo "Falha Ramo 3: backup ausente"; exit 1; }

    # Ramo 4: Terceiros
    THIRD="${TMP_WORKSPACE}/third.md"
    echo "# Regras Corporativas" > "${THIRD}"
    update_agents_md "${THIRD}" "Conteúdo Kit v2"
    grep -q "Regras Corporativas" "${THIRD}" || { echo "Falha Ramo 4"; exit 1; }
    ls "${THIRD}.bak."* >/dev/null || { echo "Falha Ramo 4: backup ausente"; exit 1; }

    # Skills e Manifesto SHA-256
    SKILLS="${TMP_WORKSPACE}/skills"
    update_skill "vitalia-demo" "Code 1.0" "${SKILLS}"
    [ -f "${SKILLS}/.vitalia-manifest" ] || { echo "Falha: manifesto não criado"; exit 1; }

    # Atualização silenciosa
    update_skill "vitalia-demo" "Code 2.0" "${SKILLS}"
    grep -q "Code 2.0" "${SKILLS}/vitalia-demo/SKILL.md" || { echo "Falha: skill não atualizada"; exit 1; }

    # Edição do usuário -> backup
    echo "Edição do desenvolvedor" > "${SKILLS}/vitalia-demo/SKILL.md"
    update_skill "vitalia-demo" "Code 3.0" "${SKILLS}"
    ls "${SKILLS}/vitalia-demo/SKILL.md.bak."* >/dev/null || { echo "Falha: backup de skill editada não gerado"; exit 1; }

    echo "   ✅ agent_preserver.sh: todos os 4 ramos e manifesto aprovados"
)

# ── 4. TESTE redis_detector.sh ────────────────────────────────────────────────
echo -e "\n--- Teste 4: redis_detector.sh ---"
(
    set -euo pipefail
    source "${LIB_DIR}/redis_detector.sh"
    ENV_TEST="${TMP_WORKSPACE}/redis.env"

    echo "REDIS_URL=redis://app:senha_privada@127.0.0.1:6379/5" > "${ENV_TEST}"
    detect_redis "${ENV_TEST}" > "${TMP_WORKSPACE}/redis_out.log" 2>&1 || true
    if grep -q "senha_privada" "${TMP_WORKSPACE}/redis_out.log"; then
        echo "Falha: senha privada vazou no redis_detector!"; exit 1
    fi
    [ "${REDIS_URL}" = "redis://app:senha_privada@127.0.0.1:6379/5" ] || { echo "Falha ao ler REDIS_URL"; exit 1; }
    echo "   ✅ redis_detector.sh: probe e sanitização aprovados"
)

# ── 5. TESTE git_storage_manager.sh ───────────────────────────────────────────
echo -e "\n--- Teste 5: git_storage_manager.sh ---"
(
    set -euo pipefail
    source "${LIB_DIR}/git_storage_manager.sh"
    MEM_DIR="${TMP_WORKSPACE}/memory"

    setup_session_repo "${MEM_DIR}" ""
    [ -d "${MEM_DIR}/session/.git" ] || { echo "Falha: session git repo não inicializado"; exit 1; }

    setup_data_repo "${MEM_DIR}" ""
    [ -d "${MEM_DIR}/data_storage/.git" ] || { echo "Falha: data_storage git repo não inicializado"; exit 1; }
    [ -d "${MEM_DIR}/data_storage/handoffs" ] || { echo "Falha: subpasta handoffs ausente"; exit 1; }
    [ -d "${MEM_DIR}/data_storage/reviews" ] || { echo "Falha: subpasta reviews ausente"; exit 1; }

    echo "   ✅ git_storage_manager.sh: repositórios de memória inicializados com sucesso"
)

echo -e "\n🎉 TODOS OS SMOKE-TESTS DAS LIBS SHELL PASSARAM COM SUCESSO! (T013-B CONCLUÍDO)"
