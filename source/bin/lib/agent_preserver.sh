#!/usr/bin/env bash
# agent_preserver.sh | Vitalia SDD v0.6.0 | 31-10-2026
# Preservação não-destrutiva de AGENTS.md e SKILL.md via marcadores e manifesto SHA-256.
# Referência: FR-008, FR-009, P06, NF-001, NF-002, NF-003.

[ -n "${_VITALIA_AGENT_PRESERVER_LOADED:-}" ] && return 0
_VITALIA_AGENT_PRESERVER_LOADED=1

# Carrega logger se disponível
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

START_MARKER="<!-- VITALIA:KIT:START -->"
END_MARKER="<!-- VITALIA:KIT:END -->"

update_agents_md() {
    local target_file="${1:-}"
    local kit_content="${2:-}"

    if [ -z "${target_file}" ] || [ -z "${kit_content}" ]; then
        log_error "update_agents_md requer caminho do arquivo e conteúdo do Kit"
        return 1
    fi

    local target_dir
    target_dir="$(dirname "${target_file}")"
    mkdir -p "${target_dir}"

    local ts
    ts="$(date +%Y%m%d%H%M%S)"

    # Ramo 1: Arquivo ausente → cria apenas o bloco do kit
    if [ ! -f "${target_file}" ]; then
        cat << EOF > "${target_file}"
${START_MARKER}
${kit_content}
${END_MARKER}
EOF
        log_ok "[CRIADO] AGENTS.md inicializado com marcadores do Kit"
        return 0
    fi

    # Ramo 2: Com marcadores existentes → substitui apenas o miolo
    if grep -qF "${START_MARKER}" "${target_file}" && grep -qF "${END_MARKER}" "${target_file}"; then
        local tmp_file
        tmp_file="$(mktemp)"

        # Extrai conteúdo anterior ao START_MARKER
        sed -n "1,/${START_MARKER}/p" "${target_file}" | grep -vF "${START_MARKER}" > "${tmp_file}" || true

        # Insere o novo bloco delimitado
        echo "${START_MARKER}" >> "${tmp_file}"
        printf "%s\n" "${kit_content}" >> "${tmp_file}"
        echo "${END_MARKER}" >> "${tmp_file}"

        # Extrai conteúdo posterior ao END_MARKER
        sed -n "/${END_MARKER}/,\$p" "${target_file}" | grep -vF "${END_MARKER}" >> "${tmp_file}" || true

        mv "${tmp_file}" "${target_file}"
        log_ok "[ATUALIZADO] AGENTS.md: bloco do Kit atualizado entre marcadores; regras customizadas preservadas"
        return 0
    fi

    # Ramo 3: Legado do kit (sem marcadores, contém '# AGENTS.md — Kit Global')
    if grep -q "AGENTS.md — Kit Global" "${target_file}"; then
        local bak_file="${target_file}.bak.${ts}"
        cp "${target_file}" "${bak_file}"
        cat << EOF > "${target_file}"
${START_MARKER}
${kit_content}
${END_MARKER}
EOF
        log_ok "[MIGRADO] AGENTS.md legado migrado para marcadores (backup em $(basename "${bak_file}"))"
        return 0
    fi

    # Ramo 4: Conteúdo de terceiros / customizado sem marcadores
    local bak_file="${target_file}.bak.${ts}"
    cp "${target_file}" "${bak_file}"
    local tmp_file
    tmp_file="$(mktemp)"

    cat << EOF > "${tmp_file}"
${START_MARKER}
${kit_content}
${END_MARKER}

EOF
    cat "${target_file}" >> "${tmp_file}"
    mv "${tmp_file}" "${target_file}"
    log_ok "[PRESERVADO] Conteúdo customizado preservado abaixo do bloco do Kit (backup em $(basename "${bak_file}"))"
    return 0
}

compute_skill_hash() {
    local file="${1:-}"
    if [ ! -f "${file}" ]; then
        echo ""
        return 1
    fi
    sha256sum "${file}" | awk '{print $1}'
}

get_manifest_hash() {
    local rel_path="${1:-}"
    local manifest_file="${2:-}"
    [ -f "${manifest_file}" ] || return 0
    grep -E "[[:space:]]+${rel_path}\$" "${manifest_file}" 2>/dev/null | awk '{print $1}' | head -n 1
}

set_manifest_hash() {
    local rel_path="${1:-}"
    local new_hash="${2:-}"
    local manifest_file="${3:-}"

    touch "${manifest_file}"
    local tmp_m
    tmp_m="$(mktemp)"

    # Remove entrada anterior se existir
    grep -v -E "[[:space:]]+${rel_path}\$" "${manifest_file}" > "${tmp_m}" 2>/dev/null || true
    # Adiciona nova entrada
    printf "%s  %s\n" "${new_hash}" "${rel_path}" >> "${tmp_m}"
    mv "${tmp_m}" "${manifest_file}"
}

update_skill() {
    local skill_name="${1:-}"
    local skill_content="${2:-}"
    local skills_dir="${3:-}"

    local skill_folder="${skills_dir}/${skill_name}"
    local target_file="${skill_folder}/SKILL.md"
    local rel_path="${skill_name}/SKILL.md"
    local manifest_file="${skills_dir}/.vitalia-manifest"

    mkdir -p "${skill_folder}"
    local ts
    ts="$(date +%Y%m%d%H%M%S)"

    # Caso 1: SKILL.md inexistente → criação direta
    if [ ! -f "${target_file}" ]; then
        printf "%s\n" "${skill_content}" > "${target_file}"
        local new_hash
        new_hash="$(compute_skill_hash "${target_file}")"
        set_manifest_hash "${rel_path}" "${new_hash}" "${manifest_file}"
        log_ok "[CRIADA] ${rel_path}"
        return 0
    fi

    local current_hash
    current_hash="$(compute_skill_hash "${target_file}")"
    local manifest_hash
    manifest_hash="$(get_manifest_hash "${rel_path}" "${manifest_file}")"

    # Caso 2: Manifesto presente
    if [ -n "${manifest_hash}" ]; then
        if [ "${current_hash}" = "${manifest_hash}" ]; then
            # Hash bate com manifesto → atualização silenciosa
            printf "%s\n" "${skill_content}" > "${target_file}"
            local new_hash
            new_hash="$(compute_skill_hash "${target_file}")"
            set_manifest_hash "${rel_path}" "${new_hash}" "${manifest_file}"
            log_ok "[ATUALIZADA] ${rel_path} (silenciosa)"
            return 0
        else
            # Hash não bate → edição do usuário detectada: backup antes de atualizar
            local bak_file="${target_file}.bak.${ts}"
            cp "${target_file}" "${bak_file}"
            log_warn "[BACKUP] Edição do usuário detectada em ${rel_path} -> backup em $(basename "${bak_file}")"
            printf "%s\n" "${skill_content}" > "${target_file}"
            local new_hash
            new_hash="$(compute_skill_hash "${target_file}")"
            set_manifest_hash "${rel_path}" "${new_hash}" "${manifest_file}"
            log_ok "[ATUALIZADA] ${rel_path} atualizada após backup de segurança"
            return 0
        fi
    fi

    # Caso 3: Sem manifesto (instalação anterior)
    local tmp_new
    tmp_new="$(mktemp)"
    printf "%s\n" "${skill_content}" > "${tmp_new}"

    if cmp -s "${target_file}" "${tmp_new}"; then
        # Conteúdo idêntico ao template: apenas registra manifesto sem backup
        rm -f "${tmp_new}"
        set_manifest_hash "${rel_path}" "${current_hash}" "${manifest_file}"
        log_ok "[MANIFESTO] ${rel_path} registrada no manifesto"
        return 0
    else
        # Conteúdo diferente: backup preventivo único e atualização
        rm -f "${tmp_new}"
        local bak_file="${target_file}.bak.${ts}"
        cp "${target_file}" "${bak_file}"
        log_warn "[BACKUP] Skill legada com alterações em ${rel_path} -> backup em $(basename "${bak_file}")"
        printf "%s\n" "${skill_content}" > "${target_file}"
        local new_hash
        new_hash="$(compute_skill_hash "${target_file}")"
        set_manifest_hash "${rel_path}" "${new_hash}" "${manifest_file}"
        log_ok "[ATUALIZADA] ${rel_path} migrada para manifesto após backup"
        return 0
    fi
}

update_all_skills() {
    local extensions_dir="${1:-}"
    local skills_dir="${2:-}"
    local template_file="${3:-}"
    local version="${4:-0.6.0}"
    local kit_dir="${5:-~/.vitalia}"

    if [ ! -d "${extensions_dir}" ] || [ ! -f "${template_file}" ]; then
        log_error "update_all_skills: diretório de extensões ou template ausente"
        return 1
    fi

    mkdir -p "${skills_dir}"

    for toml_file in "${extensions_dir}"/*.toml; do
        [ -f "${toml_file}" ] || continue
        local ext_name
        ext_name="$(basename "${toml_file}" .toml)"

        # Extrai descrição do TOML com fallback defensivo
        local desc
        desc="$(grep -E '^[[:space:]]*description[[:space:]]*=' "${toml_file}" | head -n 1 | sed -E 's/^[[:space:]]*description[[:space:]]*=[[:space:]]*["'"'"']?//; s/["'"'"'][[:space:]]*$//')"
        [ -z "${desc}" ] && desc="Comando ${ext_name} do Vitalia Kit."

        # Renderiza template
        local rendered
        rendered="$(sed \
            -e "s|{{NAME}}|${ext_name}|g" \
            -e "s|{{DESCRIPTION}}|${desc}|g" \
            -e "s|{{VERSION}}|${version}|g" \
            -e "s|{{VITALIA_KIT_DIR}}|${kit_dir}|g" \
            "${template_file}")"

        update_skill "vitalia-${ext_name}" "${rendered}" "${skills_dir}"
    done

    return 0
}
