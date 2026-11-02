#!/usr/bin/env bash
# tests/smoke_install_project.sh | Vitalia SDD v0.6.0
# Valida source/bin/install-project contra cenários SC-004 a SC-009, SC-012, SC-013.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_PROJECT_BIN="${REPO_ROOT}/source/bin/install-project"

TEST_SANDBOX="$(mktemp -d)"
trap 'rm -rf "${TEST_SANDBOX}"' EXIT

echo "=== INICIANDO TESTES DO INSTALL-PROJECT NO SANDBOX ==="
echo "Sandbox: ${TEST_SANDBOX}"

# Simula uma instalação do kit em ~/.vitalia ou kit mock
MOCK_KIT="${TEST_SANDBOX}/mock_kit"
mkdir -p "${MOCK_KIT}"/{bin/lib,extensions,templates,integrations/antigravity}
echo "0.6.0" > "${MOCK_KIT}/VERSION"
cat << 'EOF' > "${MOCK_KIT}/AGENTS.md"
# Global Vitalia Rules v{{VERSION}}
Kit dir: {{VITALIA_KIT_DIR}}
EOF

cat << 'EOF' > "${MOCK_KIT}/integrations/antigravity/SKILL.md.template"
---
name: {{NAME}}
description: {{DESCRIPTION}}
version: {{VERSION}}
---
# Skill {{NAME}}
EOF

cat << 'EOF' > "${MOCK_KIT}/extensions/test-skill.toml"
description = "Test skill description"
EOF

# Copia as libs e o bin para o mock kit
cp -r "${REPO_ROOT}/source/bin/lib/"* "${MOCK_KIT}/bin/lib/"
cp "${INSTALL_PROJECT_BIN}" "${MOCK_KIT}/bin/install-project"
chmod +x "${MOCK_KIT}/bin/install-project"

# -------------------------------------------------------------
# Teste 1: Fail-fast quando libs estão ausentes (SC-013)
# -------------------------------------------------------------
echo -n "Test 1: SC-013 Fail-fast de libs ausentes... "
BROKEN_KIT="${TEST_SANDBOX}/broken_kit"
mkdir -p "${BROKEN_KIT}/bin"
cp "${INSTALL_PROJECT_BIN}" "${BROKEN_KIT}/bin/install-project"
OUT=$( ("${BROKEN_KIT}/bin/install-project" 2>&1) || true )
if echo "${OUT}" | grep -q "Kit desatualizado"; then
    echo "PASS"
else
    echo "FAIL: Expected 'Kit desatualizado', got: ${OUT}"
    exit 1
fi

# -------------------------------------------------------------
# Teste 2: Criação de novo projeto sem .env e sem AGENTS.md (SC-005, SC-012)
# -------------------------------------------------------------
echo -n "Test 2: Instalação limpa em projeto virgem... "
PROJ1="${TEST_SANDBOX}/proj1"
mkdir -p "${PROJ1}"
(
    cd "${PROJ1}"
    VITALIA_KIT_DIR="${MOCK_KIT}" "${MOCK_KIT}/bin/install-project" </dev/null >/dev/null 2>&1
)

# Verifica .env criado
if [ ! -f "${PROJ1}/.env" ]; then
    echo "FAIL: .env não foi criado"
    exit 1
fi
if ! grep -q "REDIS_URL=redis://localhost:6379/0" "${PROJ1}/.env"; then
    echo "FAIL: REDIS_URL incorreto no .env"
    exit 1
fi
if ! grep -q "VITALIA_ENVIRONMENT=development" "${PROJ1}/.env"; then
    echo "FAIL: VITALIA_ENVIRONMENT ausente no .env"
    exit 1
fi
if ! grep -q "VITALIA_KIT_DIR=" "${PROJ1}/.env"; then
    echo "FAIL: VITALIA_KIT_DIR ausente no .env"
    exit 1
fi

# Verifica AGENTS.md criado com marcadores
if [ ! -f "${PROJ1}/.agents/AGENTS.md" ]; then
    echo "FAIL: .agents/AGENTS.md não foi criado"
    exit 1
fi
if ! grep -q "<!-- VITALIA:KIT:START -->" "${PROJ1}/.agents/AGENTS.md"; then
    echo "FAIL: Marcador START ausente em AGENTS.md"
    exit 1
fi
if ! grep -q "<!-- VITALIA:KIT:END -->" "${PROJ1}/.agents/AGENTS.md"; then
    echo "FAIL: Marcador END ausente em AGENTS.md"
    exit 1
fi

# Verifica skill criada
if [ ! -f "${PROJ1}/.agents/skills/vitalia-test-skill/SKILL.md" ]; then
    echo "FAIL: SKILL.md de vitalia-test-skill não gerada"
    exit 1
fi
if [ ! -f "${PROJ1}/.agents/skills/.vitalia-manifest" ]; then
    echo "FAIL: .vitalia-manifest não gerado"
    exit 1
fi
echo "PASS"

# -------------------------------------------------------------
# Teste 3: Preservação de .env customizado (SC-004, SC-006)
# -------------------------------------------------------------
echo -n "Test 3: Preservação de .env existente com customizações... "
PROJ2="${TEST_SANDBOX}/proj2"
mkdir -p "${PROJ2}"
cat << 'EOF' > "${PROJ2}/.env"
# Meu env customizado
REDIS_URL=redis://custom-host:6380/2
GOOGLE_API_KEY=AIzaSySecretCustom
CUSTOM_VAR=hello_world
EOF

(
    cd "${PROJ2}"
    VITALIA_KIT_DIR="${MOCK_KIT}" "${MOCK_KIT}/bin/install-project" </dev/null >/dev/null 2>&1
)

# Verifica se REDIS_URL customizado foi preservado e não duplicado
REDIS_COUNT=$(grep -c "REDIS_URL" "${PROJ2}/.env")
if [ "${REDIS_COUNT}" -ne 1 ]; then
    echo "FAIL: REDIS_URL duplicado no .env (${REDIS_COUNT} ocorrências)"
    exit 1
fi
if ! grep -q "REDIS_URL=redis://custom-host:6380/2" "${PROJ2}/.env"; then
    echo "FAIL: REDIS_URL customizado foi sobrescrito"
    exit 1
fi

# Verifica se GOOGLE_API_KEY evitou GEMINI_API_KEY (SC-006)
if grep -q "GEMINI_API_KEY" "${PROJ2}/.env"; then
    echo "FAIL: GEMINI_API_KEY adicionada indevidamente quando GOOGLE_API_KEY já existe"
    exit 1
fi
echo "PASS"

# -------------------------------------------------------------
# Teste 4: Preservação de AGENTS.md de terceiros (SC-007)
# -------------------------------------------------------------
echo -n "Test 4: Preservação de AGENTS.md de terceiros... "
PROJ3="${TEST_SANDBOX}/proj3"
mkdir -p "${PROJ3}/.agents"
cat << 'EOF' > "${PROJ3}/.agents/AGENTS.md"
# Regras Customizadas do Usuário
- Sempre usar tabs
- Não tocar em backend
EOF

(
    cd "${PROJ3}"
    VITALIA_KIT_DIR="${MOCK_KIT}" "${MOCK_KIT}/bin/install-project" </dev/null >/dev/null 2>&1
)

# Verifica se backup foi gerado
BAK_COUNT=$(ls "${PROJ3}/.agents"/AGENTS.md.bak.* 2>/dev/null | wc -l)
if [ "${BAK_COUNT}" -lt 1 ]; then
    echo "FAIL: Backup de AGENTS.md de terceiros não foi gerado"
    exit 1
fi

# Verifica se conteúdo original foi preservado após o END_MARKER
if ! grep -q "Sempre usar tabs" "${PROJ3}/.agents/AGENTS.md"; then
    echo "FAIL: Regras customizadas do usuário foram destruídas"
    exit 1
fi
if ! grep -q "<!-- VITALIA:KIT:START -->" "${PROJ3}/.agents/AGENTS.md"; then
    echo "FAIL: Marcadores não inseridos no topo"
    exit 1
fi
echo "PASS"

# -------------------------------------------------------------
# Teste 5: Reinstalação com marcadores preserva miolo e regras do usuário sem novo backup (SC-008)
# -------------------------------------------------------------
echo -n "Test 5: Reinstalação com marcadores existentes... "
# Conta backups antes
BAK_BEFORE=$(ls "${PROJ3}/.agents"/AGENTS.md.bak.* 2>/dev/null | wc -l)
(
    cd "${PROJ3}"
    VITALIA_KIT_DIR="${MOCK_KIT}" "${MOCK_KIT}/bin/install-project" </dev/null >/dev/null 2>&1
)
BAK_AFTER=$(ls "${PROJ3}/.agents"/AGENTS.md.bak.* 2>/dev/null | wc -l)
if [ "${BAK_BEFORE}" -ne "${BAK_AFTER}" ]; then
    echo "FAIL: Backup redundante criado na reinstalação de AGENTS.md com marcadores"
    exit 1
fi
if ! grep -q "Sempre usar tabs" "${PROJ3}/.agents/AGENTS.md"; then
    echo "FAIL: Regras customizadas perdidas após segunda reinstalação"
    exit 1
fi
echo "PASS"

# -------------------------------------------------------------
# Teste 6: Detecção e backup de edição de usuário em SKILL.md (SC-009)
# -------------------------------------------------------------
echo -n "Test 6: Detecção de edição de usuário em SKILL.md com backup... "
# Edita a skill em proj1
echo "Edição manual do usuário" >> "${PROJ1}/.agents/skills/vitalia-test-skill/SKILL.md"

(
    cd "${PROJ1}"
    VITALIA_KIT_DIR="${MOCK_KIT}" "${MOCK_KIT}/bin/install-project" </dev/null >/dev/null 2>&1
)

SKILL_BAK_COUNT=$(ls "${PROJ1}/.agents/skills/vitalia-test-skill"/SKILL.md.bak.* 2>/dev/null | wc -l)
if [ "${SKILL_BAK_COUNT}" -lt 1 ]; then
    echo "FAIL: Backup de SKILL.md modificada não foi gerado"
    exit 1
fi
echo "PASS"

echo "=== TODOS OS TESTES DO INSTALL-PROJECT PASSARAM COM SUCESSO! ==="
exit 0
