<!-- spec.md | Vitalia SDD v0.6.0 | 02-11-2026 09:00:00(GMT-04:00) -->
# Especificação de Funcionalidade: Kit Install Hardening & Atomic Upgrades

**Data:** 02-11-2026  
**Autor/Agente:** Antigravity (via /vitalia-spec-specify)  
**Origem:** [research-brainstorming.md](file:///home/andre/projetos/assistidos/kit_src/specs/kit-install-hardening/research-brainstorming.md) (Revisão 3, 02-11-2026)  

---

## 1. Contexto e Objetivo (O Quê e Por Quê)

O Vitalia Kit possui dois scripts de instalação e manutenção — `kit-bootstrap.sh` (global) e `install-project` (por projeto) — que passaram por hardening inicial para resolver problemas de vazamento de dados, duplicação de variáveis e destruição de `AGENTS.md`. Durante o teste funcional no projeto legado `ai-control`, foi identificada a quebra da diretiva `set -euo pipefail` no manifesto de skills e a vulnerabilidade inerente a scripts que atualizam arquivos de produção no disco sem staging ou atomicidade garantida.

O objetivo desta especificação é endurecer o processo de atualização com o **Padrão Capistrano (Symlink Atômico com `releases/` e `shared/`)**, auto-testes de sanidade pré-ativação (pre-activation self-test), resolução determinística de manifesto via `awk` e blindagem do guardrail Zero Data Leak para caminhos resolvidos com symlinks.

---

## 2. Requisitos Funcionais

### FR-001: Resolvedor de Raiz de Projeto Dedicado [MUST]
O sistema MUST fornecer uma função `resolve_project_root()` em `vitalia_handoff.py`, autocontida (apenas stdlib), que:
- Parta de `--project-root` (se informado pelo CLI) ou de `Path.cwd()`.
- Se o caminho estiver dentro de uma árvore `.vitalia`, suba para fora dela antes de buscar.
- Suba procurando um `.vitalia/` **de projeto**: que contenha `feature.json`, `config.yml` ou `memory/`.
- Ignore `Path.home()` e o diretório do kit (`VITALIA_KIT_DIR` ou `~/.vitalia`).
- Pare ao alcançar `$HOME` ou a raiz do filesystem sem projeto válido → emita erro com instrução para executar `install-project`.

### FR-002: Validação Estrita de `data_storage` [MUST]
O sistema MUST validar a existência de `.vitalia/memory/data_storage` no projeto encontrado antes de qualquer operação de leitura ou escrita de handoffs:
- Projeto sem `data_storage` → erro: `Execute novamente o install-project para inicializar data_storage e a conexão com o GitHub.`
- Com `data_storage` presente → usa `<raiz>/.vitalia/memory/data_storage/handoffs/` (a subpasta `handoffs/` pode ser criada automaticamente).

### FR-003: Guardrail Zero Data Leak [MUST]
O sistema MUST emitir erro fatal se o caminho final de armazenamento estiver sob `~/.vitalia/` ou se a raiz resolvida for `$HOME`. Esta verificação é a última barreira antes de qualquer escrita no filesystem.

### FR-004: Argumento `--project-root` no CLI [MUST]
O CLI de `vitalia_handoff.py` MUST aceitar `--project-root` nos subcomandos `create`, `latest`, `consume` e `validate`, permitindo execução determinística independente do `cwd`.

### FR-005: Alinhamento de Leitores de Handoff [MUST]
O sistema MUST expor uma função `resolve_storage_dir()` que será consumida por `vitalia_hook_runner.py` (L216) e `guardian_context.py` (L329) para resolução de storage. Leitores que não encontrarem projeto válido MUST retornar "sem handoff" (sem erro fatal), mantendo a execução do workflow.

### FR-006: Biblioteca Shell `logger.sh` [MUST]
O sistema MUST fornecer `source/bin/lib/logger.sh` com funções `log_ok`, `log_warn`, `log_error` e `log_step`, com formatação em cores e prefixo de etapa, compatível com bash 3.2 e `set -euo pipefail`.

### FR-007: Biblioteca Shell `env_manager.sh` [MUST]
O sistema MUST fornecer `source/bin/lib/env_manager.sh` que implemente a matriz de estados S1–S7:
- **S1:** `.env` ausente → cria a partir do template com log `[CRIADO]`.
- **S2:** `.env` presente sem backup → cria `.env.bak` com log `[BACKUP]`.
- **S3:** `.env.bak` já existe → preserva o backup histórico com log `[BACKUP] preservado`.
- **S4:** Variável com valor padrão → mantém com log `[PRESERVADA]`.
- **S5:** Variável customizada (detecta via regex `^[[:space:]]*(export[[:space:]]+)?VAR[[:space:]]*=`) → mantém e não duplica com log `[PRESERVADA] valor customizado`.
- **S6:** Variável ausente → acrescenta ao final com comentário com log `[ADICIONADA]`.
- **S7:** Sem permissão de escrita → alerta e segue com log `[ALERTA] configure manualmente`.

Variáveis gerenciadas: `VITALIA_KIT_DIR`, `VITALIA_ENVIRONMENT`, `REDIS_URL`, `GEMINI_API_KEY` (pulada se `GOOGLE_API_KEY` existir; nunca preenchida com valor, apenas placeholder vazio).

### FR-008: Biblioteca Shell `agent_preserver.sh` [MUST]
O sistema MUST fornecer `source/bin/lib/agent_preserver.sh` que gerencie `AGENTS.md` com marcadores delimitados (`<!-- VITALIA:KIT:START -->` / `<!-- VITALIA:KIT:END -->`):
- **Arquivo ausente:** cria apenas o bloco do kit.
- **Com marcadores:** substitui apenas o miolo entre marcadores; resto fica intacto.
- **Legado do kit (sem marcadores, contém `# AGENTS.md — Kit Global`):** backup com timestamp, substituição integral por bloco com marcadores.
- **Conteúdo de terceiros sem marcadores:** backup com timestamp, bloco do kit inserido no topo, conteúdo original preservado abaixo.

### FR-009: Manifesto SHA-256 de Skills [MUST]
O sistema MUST manter `.agents/skills/.vitalia-manifest` com hashes SHA-256 de cada `SKILL.md` instalado no namespace `vitalia-*`:
- Hash local = manifesto → atualização silenciosa (inclusive troca de versão).
- Hash local ≠ manifesto → edição do usuário detectada: backup `SKILL.md.bak.<timestamp>` antes de atualizar.
- Sem manifesto (instalação anterior) → compara com template atual; se diferente, faz backup uma única vez e cria o manifesto.

### FR-010: Biblioteca Shell `redis_detector.sh` [SHOULD]
O sistema SHOULD fornecer `source/bin/lib/redis_detector.sh` que faça probe de Redis com fallback para modo arquivo, lendo `REDIS_URL` do `.env` existente antes de fazer o probe.

### FR-011: Biblioteca Shell `git_storage_manager.sh` [MUST]
O sistema MUST fornecer `source/bin/lib/git_storage_manager.sh` que gerencie `git init` e remote de `data_storage` e `session`.

### FR-012: Rsync Seguro no `kit-bootstrap.sh` [MUST]
O `kit-bootstrap.sh` MUST usar rsync com:
- `--checksum` para atualização baseada em conteúdo.
- `--exclude='/tmp/'` (ancorado) para não copiar arquivos de desenvolvimento.
- `--filter='protect /tmp/***'` como salvaguarda contra futuras adições de `--delete`.

### FR-013: Expurgo Automático de `~/.vitalia/memory/` Órfão [MUST]
O `kit-bootstrap.sh` MUST purgar silenciosa e automaticamente qualquer diretório órfão `memory/` legado remanescente no Kit Global durante a migração para a nova estrutura de releases, garantindo ausência de resíduos sem efetuar qualquer migração ou cópia automática para projetos.

### FR-014: Pré-requisitos Fail-Fast [MUST]
O `kit-bootstrap.sh` MUST verificar na inicialização:
- `python3 >= 3.10` disponível.
- `python3 -m venv` funcional (no Debian/Ubuntu exige `python3-venv`).
- `git` e `rsync` disponíveis.
- Alerta bloqueante se executado como root/`sudo`.
- Comando de instalação por SO via `/etc/os-release`.

### FR-015: Refatoração do `kit-bootstrap.sh` para Consumir Libs [MUST]
O `kit-bootstrap.sh` MUST ser refatorado para delegar suas responsabilidades às bibliotecas shell de `source/bin/lib/`, eliminando lógica inline de logging, gestão de `.env` e verificação de pré-requisitos.

### FR-016: Refatoração do `install-project` para Consumir Libs [MUST]
O `install-project` MUST ser refatorado para delegar suas responsabilidades às bibliotecas shell de `source/bin/lib/`, localizando-as via `BASH_SOURCE` e falhando antecipadamente com mensagem `Kit desatualizado. Execute o kit-bootstrap.sh.` se ausentes.

### FR-017: REDIS_URL Padrão Unificado [MUST]
O sistema MUST usar `redis://localhost:6379/0` como valor padrão de `REDIS_URL` em todos os pontos (template de `.env`, `redis_detector.sh`, e fallback em Python).

### FR-018: Promoção Atômica por Symlink no `kit-bootstrap.sh` [MUST]
O `kit-bootstrap.sh` MUST estruturar as versões instaladas no padrão de releases com symlink atômico:
- Diretório de versões: `~/.vitalia-releases/<timestamp>/` imutável para cada versão instalada (auditoria histórica completa).
- Caminho ativo: `~/.vitalia` MUST operar estritamente como um symlink simbólico apontando para a release ativa mais recente (`~/.vitalia-releases/<timestamp>`).
- Swap atômico: a troca de versão MUST ser realizada via link temporário no mesmo sistema de arquivos e renomeação via GNU `mv -T` (`ln -s ~/.vitalia-releases/<ts> ~/.vitalia.tmp && mv -T ~/.vitalia.tmp ~/.vitalia`), garantindo atomicidade estrita no kernel sem janela de indisponibilidade.
- Migração de legado: em instalações legadas onde `~/.vitalia` ainda é um diretório físico real (`[ -d ~/.vitalia ] && [ ! -L ~/.vitalia ]`), o bootstrap MUST renomeá-lo para `~/.vitalia-releases/<ts_legado>` convertendo-o na primeira release física, e imediatamente criar o symlink `~/.vitalia` apontando para a release ativa. Em nenhuma hipótese `~/.vitalia` permanecerá como diretório físico após a execução do bootstrap.

### FR-019: Diretório de Estado Compartilhado `shared/tmp` [MUST]
O sistema MUST manter os stubs de Context Lifting do Guardian em `~/.vitalia-shared/tmp/`, sobrevivendo a todas as trocas de versão:
- Cada release instalada MUST possuir um symlink `~/.vitalia-releases/<ts>/tmp -> ~/.vitalia-shared/tmp`.
- Nenhuma atualização de versão pode limpar ou sobrescrever stubs de sessões em andamento.

### FR-020: Auto-Teste de Sanidade no Staging (Self-Test) [MUST]
O `kit-bootstrap.sh` MUST preparar a nova release em `~/.vitalia-releases/<ts>.staging/` e executar uma bateria de auto-teste antes de promover a release ativa:
- Validação de sintaxe com `bash -n` em todos os scripts executáveis e bibliotecas.
- Carregamento isolado em subshell de todas as bibliotecas sob `set -euo pipefail`.
- Teste de busca no manifesto com chave ausente.
- Verificação de existência dos templates e extensões essenciais.
- Se qualquer verificação falhar: o staging MUST ser purgado e o symlink `~/.vitalia` ativo MUST permanecer 100% inalterado.

### FR-021: Resolução Determinística do Manifesto com `awk` [MUST]
A biblioteca `agent_preserver.sh` MUST consultar o manifesto `.vitalia-manifest` utilizando exclusivamente comandos que retornem código de saída `0` quando a chave consultada não existir:
- `get_manifest_hash` MUST usar `awk -v p="${rel_path}" '$2 == p { print $1; exit }' "${manifest_file}" 2>/dev/null || true`.
- É expressamente proibido o uso de pipelines `grep | awk` sujeitos à quebra por `pipefail` na ausência de correspondência.

### FR-022: Blindagem de Resolução de Symlinks no Guardrail Python [MUST]
O módulo `vitalia_handoff.py` MUST garantir que `kit_dir` seja explicitamente resolvido com `.resolve()`:
- `kit_dir = Path(kit_dir_env).resolve() if kit_dir_env else (home / ".vitalia").resolve()`.
- Garante que a comparação `resolved_storage.relative_to(kit_dir)` continue bloqueando violações Zero Data Leak mesmo quando `~/.vitalia` for um symlink apontando para `~/.vitalia-releases/<ts>`.

### FR-023: Pré-voo e Sugestão de Defaults no `install-project` [SHOULD]
O script `install-project` SHOULD identificar previamente o modo de execução (`NOVA_INSTALACAO` vs `UPGRADE`), exibindo a transição de versão no banner e sugerindo como padrão interativo as URLs de repositórios Git de memória já cadastradas em `.vitalia/config.yml`.

---

## 3. Requisitos Não-Funcionais (Restrições)

- **NF-001 (Compatibilidade Bash 3.2+):** O código de todas as bibliotecas shell MUST manter total compatibilidade com bash 3.2+, sendo vedado o uso de arrays associativos. [MUST]
- **NF-002 (Execução Sob Modo Estrito Shell):** Todas as bibliotecas shell MUST operar perfeitamente sob modo estrito (`set -euo pipefail`), sem falhar na ausência de dados opcionais. [MUST]
- **NF-003 (Portabilidade de Backups Shell):** As rotinas de backup MUST utilizar a verificação portável `[ -e "$bak" ] || cp "$src" "$bak"`, sendo vedado o uso de `cp -n` obsoleto no GNU coreutils 9.7+. [MUST]
- **NF-004 (Dependências de resolve_project_root):** A função `resolve_project_root()` MUST utilizar exclusivamente a biblioteca padrão (stdlib) do Python, sem qualquer dependência externa. [MUST]
- **NF-005 (Isolamento de Memória e Expurgo de Legado):** O kit MUST purgar silenciosa e automaticamente qualquer diretório órfão `~/.vitalia/memory/` remanescente no kit global e MUST NEVER copiar handoffs residuais para projetos locais. [MUST]
- **NF-006 (Caráter Informativo de VITALIA_KIT_DIR):** A variável de ambiente `VITALIA_KIT_DIR` MUST ser tratada estritamente como informativa para exibição e diagnósticos, com os módulos Python padronizados em `~/.vitalia`. [MUST]
- **NF-007 (Imutabilidade de find_project_root):** A função `find_project_root()` em `kit_env_bootstrap.py` MUST permanecer inalterada para garantir a compatibilidade com `gemini.py` e `scan_environment`. [MUST]
- **NF-008 (Colocalização em Mesmo Filesystem):** O diretório de staging e a release ativa MUST residir obrigatoriamente no mesmo filesystem (`$HOME`) para garantir a atomicidade estrita da syscall `rename(2)`. [MUST]

---

## 4. Histórias de Usuário (User Stories)

### US-001: Isolamento de memória
**Como um** desenvolvedor que trabalha com múltiplos projetos Vitalia, **eu quero** que cada projeto armazene seus handoffs exclusivamente em sua própria pasta `.vitalia/memory/data_storage/handoffs/`, **para que** dados de um projeto nunca vazem para o diretório global do kit ou para outro projeto.

### US-002: Instalação não-destrutiva
**Como um** desenvolvedor que reinstala ou atualiza o kit, **eu quero** que minhas variáveis customizadas no `.env`, minhas regras no `AGENTS.md` e minhas edições em skills SKILL.md sejam preservadas, **para que** eu não perca configurações ao atualizar o kit.

### US-003: Diagnóstico claro
**Como um** desenvolvedor que executa o kit em um diretório sem projeto Vitalia inicializado, **eu quero** receber uma mensagem de erro clara indicando qual comando executar (install-project), **para que** eu saiba exatamente como corrigir a situação.

### US-004: Atualização segura do kit global
**Como um** desenvolvedor que atualiza o kit global via `kit-bootstrap.sh`, **eu quero** que os arquivos de Context Lifting em `~/.vitalia/tmp/` sejam preservados e que arquivos de desenvolvimento não sejam copiados, **para que** stubs de sessão ativa não sejam perdidos nem poluídos.

### US-005: Atualização atômica à prova de falhas
**Como um** desenvolvedor atualizando o Kit Global, **eu quero** que a atualização execute auto-testes no staging e realize um swap atômico sem janela de indisponibilidade, **para que** falhas durante o processo nunca deixem o kit em estado quebrado ou inutilizável.

---

## 5. Critérios de Aceite (Acceptance Criteria)

### SC-001: Isolamento de memória resolve corretamente
**Dado que** o desenvolvedor está em `/home/user/projetos/meu-app` (que contém `.vitalia/memory/data_storage/`),
**Quando** `vitalia_handoff.py create` é executado sem `--project-root`,
**Então** o handoff é gravado em `/home/user/projetos/meu-app/.vitalia/memory/data_storage/handoffs/` e nunca em `~/.vitalia/memory/`.

### SC-002: Guardrail bloqueia escrita no kit global
**Dado que** o `cwd` é `~/.vitalia/src/` ou qualquer subdiretório de `~/.vitalia/`,
**Quando** `vitalia_handoff.py create` é executado,
**Então** o sistema emite erro fatal com código de saída não-zero e a mensagem contém "install-project".

### SC-003: Projeto sem data_storage recebe instrução clara
**Dado que** o projeto tem `.vitalia/` mas não possui `memory/data_storage/`,
**Quando** `vitalia_handoff.py create` é executado apontando para esse projeto,
**Então** o sistema emite erro com a instrução para reexecutar `install-project`.

### SC-004: `.env` existente não é duplicado
**Dado que** o `.env` do projeto contém `REDIS_URL=redis://custom-host:6380/2`,
**Quando** `install-project` é executado novamente,
**Então** a variável `REDIS_URL` permanece com o valor `redis://custom-host:6380/2` e não há segunda ocorrência.

### SC-005: `.env` ausente é criado
**Dado que** o projeto não possui `.env`,
**Quando** `install-project` é executado,
**Então** um `.env` é criado contendo `VITALIA_KIT_DIR`, `VITALIA_ENVIRONMENT`, `REDIS_URL` e `GEMINI_API_KEY` (com placeholder vazio).

### SC-006: `GEMINI_API_KEY` não duplica se `GOOGLE_API_KEY` já existe
**Dado que** o `.env` do projeto contém `GOOGLE_API_KEY=AIza...`,
**Quando** `install-project` é executado,
**Então** `GEMINI_API_KEY` não é adicionada ao `.env`.

### SC-007: `AGENTS.md` com conteúdo de terceiros é preservado
**Dado que** o projeto possui um `AGENTS.md` com regras customizadas e sem marcadores Vitalia,
**Quando** `install-project` é executado,
**Então** um backup com timestamp é criado, o bloco do kit (com marcadores) é inserido no topo, e o conteúdo original é preservado abaixo.

### SC-008: `AGENTS.md` com marcadores é atualizado no miolo
**Dado que** o projeto possui um `AGENTS.md` com marcadores `<!-- VITALIA:KIT:START -->` e conteúdo do usuário abaixo do `<!-- VITALIA:KIT:END -->`,
**Quando** `install-project` é executado com nova versão do kit,
**Então** apenas o conteúdo entre os marcadores é atualizado; o conteúdo do usuário permanece inalterado sem backup.

### SC-009: Skill editada pelo usuário recebe backup
**Dado que** o hash SHA-256 do `SKILL.md` local de `vitalia-brainstorming` difere do registrado no manifesto,
**Quando** `install-project` atualiza a skill,
**Então** o `SKILL.md` original é salvo como `SKILL.md.bak.<timestamp>` e o manifesto é atualizado com o novo hash.

### SC-010: Rsync protege `~/.vitalia/tmp/`
**Dado que** `~/.vitalia/tmp/` contém stubs JSON de sessão ativa,
**Quando** `kit-bootstrap.sh` é executado,
**Então** nenhum arquivo em `~/.vitalia/tmp/` é removido ou sobrescrito por arquivos de `source/tmp/`.

### SC-011: `--project-root` funciona deterministicamente
**Dado que** o desenvolvedor informa `--project-root /caminho/para/projeto`,
**Quando** qualquer subcomando de `vitalia_handoff.py` é executado,
**Então** a resolução de raiz usa exclusivamente o caminho informado sem buscar a partir do `cwd`.

### SC-012: Libs shell são encontradas pelo install-project
**Dado que** o kit global está instalado corretamente em `~/.vitalia/`,
**Quando** `install-project` é executado,
**Então** as libs são localizadas via `BASH_SOURCE` relativo e carregadas com `source`.

### SC-013: Libs shell ausentes causam falha antecipada
**Dado que** o kit global está em versão antiga sem `bin/lib/`,
**Quando** `install-project` é executado,
**Então** o script aborta com a mensagem `Kit desatualizado. Execute o kit-bootstrap.sh.` e código de saída 1.

### SC-014: Promoção atômica por symlink com histórico de releases
**Dado que** o `kit-bootstrap.sh` é executado para atualizar a máquina,
**Quando** a nova release é promovida com sucesso,
**Então** `~/.vitalia` aponta para `~/.vitalia-releases/<timestamp>` via symlink atômico e as versões anteriores permanecem intactas em `~/.vitalia-releases/`.

### SC-015: Preservação contínua de stubs em `shared/tmp`
**Dado que** existem stubs de contexto em `~/.vitalia-shared/tmp/`,
**Quando** uma nova release é instalada via `kit-bootstrap.sh`,
**Então** o novo symlink `~/.vitalia/tmp` continua apontando para `~/.vitalia-shared/tmp/` com todos os stubs preservados.

### SC-016: Fail-safe no staging impede corrupção do kit ativo
**Dado que** a nova release no staging contém erro de sintaxe ou biblioteca inválida,
**Quando** o auto-teste falha durante o `kit-bootstrap.sh`,
**Então** o diretório de staging é expurgado e o symlink `~/.vitalia` ativo permanece 100% inalterado na versão funcional anterior.

### SC-017: Resolução do manifesto não falha com pipefail
**Dado que** o `.vitalia-manifest` contém entradas de outras skills,
**Quando** o `install-project` consulta uma skill inexistente ou nova no manifesto,
**Então** `get_manifest_hash` retorna vazio com código de saída 0 e o processo continua normalmente sob `set -euo pipefail`.

### SC-018: Guardrail Zero Data Leak ativo com symlink de release
**Dado que** `~/.vitalia` é um symlink para `~/.vitalia-releases/<ts>`,
**Quando** `vitalia_handoff.py` valida o diretório de storage,
**Então** o método `relative_to(kit_dir)` detecta com precisão a tentativa de escrita sob o kit global resolvido e bloqueia com erro fatal.

---

## 6. Fora do Escopo (Out of Scope)

- [ ] Migração automática de handoffs de `~/.vitalia/memory/` para projetos existentes.
- [ ] Refatoração de `find_project_root()` em `kit_env_bootstrap.py` (usada por outros módulos).
- [ ] Interface gráfica ou TUI para o processo de instalação.
- [ ] Suporte a sistemas operacionais não-Linux (macOS, Windows).
- [ ] Utilitário CLI automático de rollback de versões (rollback é feito por repontar o symlink).

---

## 7. Suposições Verificadas (Grounding P03)

- "rename(2) ENOTEMPTY": verificado em [man7.org rename(2)](https://man7.org/linux/man-pages/man2/rename.2.html) em 02-11-2026 — kernel POSIX rejeita substituição atômica direta de diretórios não-vazios.
- "mv -T atomic symlink swap": verificado em GNU Coreutils e Stack Overflow em 02-11-2026 — substituição de symlinks temporários via `mv -T` executa rename(2) atômico de link.
- "BashFAQ/105 set -e pipefail": verificado em [mywiki.wooledge.org/BashFAQ/105](https://mywiki.wooledge.org/BashFAQ/105) em 02-11-2026 — grep em pipeline sob pipefail aborta scripts de forma imprevista.
- "Capistrano shared directory": verificado em [capistranorb.com](https://capistranorb.com/documentation/getting-started/structure/) em 02-11-2026 — isolamento de releases e dados persistentes em shared/.
- "XDG Base Directory Spec": verificado em [specifications.freedesktop.org](https://specifications.freedesktop.org/basedir-spec/latest/) em 02-11-2026 — persistência de arquivos de estado em runtime.
- "PEP 668": verificado em [PEP 668](https://peps.python.org/pep-0668/) em 31-10-2026 — venv obrigatório em distros modernas.
- "python3-venv no Debian/Ubuntu": verificado nos repositórios oficiais Ubuntu/Debian em 31-10-2026.
- "rsync --filter='protect'": verificado em `man 1 rsync` em 31-10-2026.
- "cp -n obsoleto no coreutils 9.7": verificado por teste local em 31-10-2026.

---

## 8. Assumptions (Padrões Adotados sem Necessidade de Clarificação)

- O diretório `$HOME` é o local de residência de `~/.vitalia-releases/`, `~/.vitalia-shared/` e do symlink `~/.vitalia`, garantindo mesmo filesystem e compatibilidade com `rename(2)`.
- O padrão de retenção é manter todas as releases em disco para auditoria histórica completa.
- O utilitário GNU `mv -T` está disponível no ambiente Linux padrão.
