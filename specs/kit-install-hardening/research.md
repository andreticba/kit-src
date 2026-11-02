<!-- research.md | Vitalia SDD v0.6.0 | 31-10-2026 12:32(GMT-04:00) -->
> **research.md | Vitalia SDD v0.6.0 | 31-10-2026 12:32(GMT-04:00)**

# Technical Research: Kit Install Hardening

## Decisão 1: Resolvedor de raiz de projeto

- **Escolhido**: Função dedicada `resolve_project_root()` em `vitalia_handoff.py`, autocontida (stdlib-only)
- **Verificado em**: Teste local executado com `.venv/bin/python` em 31-10-2026 — `find_project_root()` retorna `$HOME` a partir de `~/projetos`
- **Justificativa**: A função existente `find_project_root()` em `kit_env_bootstrap.py` sobe buscando `.vitalia/` ou `.git/` como marcador. A pasta `~/.vitalia/` (kit global) conta como marcador, fazendo a resolução retornar `$HOME`. Além disso, `.vitalia/memory/data_storage/.git` (aninhado) faz a mesma função retornar `data_storage` como raiz. A função existente não pode ser alterada pois `gemini.py` e `scan_environment.py` dependem dela.
- **Alternativas**:
  - Refatorar `find_project_root()`: rejeitado porque quebraria `gemini.py` L47 e `scan_environment.py` que usam a mesma lógica.
  - Variável de ambiente `PROJECT_ROOT`: rejeitado porque o LLM pode injetá-la incorretamente no `.env` (como ocorreu com `VITALIA_KIT_DIR` no projeto ai-control).

## Decisão 2: Formato de marcadores para `AGENTS.md`

- **Escolhido**: Comentários HTML `<!-- VITALIA:KIT:START -->` / `<!-- VITALIA:KIT:END -->`
- **Verificado em**: Teste em IDE Antigravity — comentários HTML são invisíveis no Markdown renderizado e não interferem com processamento da IDE. Verificado em 31-10-2026.
- **Justificativa**: A IDE lê `AGENTS.md` como Markdown; marcadores HTML são silenciosos no rendering. `sed` pode substituir o bloco entre marcadores com padrões POSIX simples (`/VITALIA:KIT:START/,/VITALIA:KIT:END/`).
- **Alternativas**:
  - Arquivo separado `.agents/VITALIA.md`: rejeitado porque IDEs como Antigravity e Gemini CLI só processam `AGENTS.md` como entry point.
  - Marcadores YAML front-matter: rejeitado porque `AGENTS.md` já pode ter front-matter de outras ferramentas.

## Decisão 3: Manifesto SHA-256 para skills

- **Escolhido**: Arquivo `.agents/skills/.vitalia-manifest` com formato `sha256  vitalia-skillname/SKILL.md` por linha
- **Verificado em**: `sha256sum` verificado como disponível em coreutils GNU (todas as distribuições Linux). Em macOS, `shasum -a 256` como fallback. Verificado em 31-10-2026.
- **Justificativa**: O template `SKILL.md.template` contém `{{VERSION}}` (verificado na L6 do template). A cada versão do kit, o hash do SKILL.md gerado muda mesmo que o usuário não tenha editado. O manifesto armazena o hash da última versão instalada, permitindo distinguir: (hash local = manifesto → atualização automática) vs (hash local ≠ manifesto → edição do usuário → backup).
- **Alternativas**:
  - Diff textual entre template renderizado e arquivo local: rejeitado porque o diff é computacionalmente mais caro e produz falsos positivos com mudanças de whitespace.
  - Timestamp de modificação (`stat -c %Y`): rejeitado porque `git clone` reseta timestamps.

## Decisão 4: Regex POSIX para detecção de variáveis no `.env`

- **Escolhido**: `^[[:space:]]*(export[[:space:]]+)?VAR[[:space:]]*=` com `grep -q`
- **Verificado em**: Testado com GNU grep 3.11 e BSD grep (macOS) em 31-10-2026. POSIX character classes `[[:space:]]` são portáveis.
- **Justificativa**: Cobre os formatos: `VAR=value`, `export VAR=value`, `  VAR = value`, `export  VAR="value"`, `VAR='value'`. Não executa o arquivo (evita side-effects).
- **Alternativas**:
  - `source .env && test -v VAR`: rejeitado porque executa o `.env` inteiro, risco de side-effects se houver comandos ou `$(...)` no arquivo.
  - Parse Python com `dotenv`: rejeitado porque introduz dependência Python no script shell.

## Decisão 5: `cp -n` vs. teste explícito para backup

- **Escolhido**: `[ -e "$bak" ] || cp "$src" "$bak"` (teste explícito)
- **Verificado em**: Teste local em coreutils 9.7 — `cp -n` emite `cp: not replacing '...'` para stderr com exit 0, mas será removido em versão futura. Verificado em 31-10-2026.
- **Justificativa**: `cp -n` está marcado como obsoleto no coreutils 9.7 (GNU). O teste explícito é equivalente, portável e não produz warnings.
- **Alternativas**:
  - `cp --no-clobber`: rejeitado — sinônimo de `cp -n`, mesma obsolescência.
  - `cp --update=none`: disponível apenas em coreutils >= 9.3, não portável para macOS/Debian oldstable.

## Decisão 6: Padrão de `REDIS_URL`

- **Escolhido**: `redis://localhost:6379/0` (com `/0` para database index)
- **Verificado em**: [Redis URI specification](https://www.iana.org/assignments/uri-schemes/prov/redis) — o formato inclui database index como path. Verificado em 31-10-2026.
- **Justificativa**: O kit atualmente usa três variantes inconsistentes: `redis://localhost:6379` (install-project L69), `redis://127.0.0.1:6379/0` (kit-bootstrap L165), e `redis://localhost:6379/0` (em Python). Unificar para `redis://localhost:6379/0` — com `localhost` (mais legível) e `/0` (database explícito, evita ambiguidade).
- **Alternativas**:
  - `redis://127.0.0.1:6379/0`: rejeitado como padrão porque `localhost` é mais legível; `127.0.0.1` pode ser necessário em ambientes onde localhost resolve para IPv6.

## Decisão 7: Arquitetura de Releases com Swap Atômico via Symlink (`mv -T`)

- **Escolhido**: Estrutura `~/.vitalia-releases/<timestamp>/` com swap atômico via `ln -s ... ~/.vitalia.tmp && mv -T ~/.vitalia.tmp ~/.vitalia` no mesmo filesystem (`$HOME`).
- **Verificado em**: [Linux rename(2) man page](https://man7.org/linux/man-pages/man2/rename.2.html), [Capistrano Deployment Flow](https://capistranorb.com/documentation/getting-started/flow/), [BashFAQ/105](https://mywiki.wooledge.org/BashFAQ/105) em 02-11-2026.
- **Justificativa**: A syscall `rename(2)` do kernel Linux retorna `ENOTEMPTY` se o alvo for um diretório não-vazio. A promoção direta de um diretório com `mv` não é atômica e falha no Linux. A substituição atômica de um symlink via `rename(2)` (invocada por `mv -T` do GNU coreutils) é atômica, imediata no inode e elimina qualquer janela de indisponibilidade.
- **Alternativas**:
  - `rsync --delete` in-place: rejeitado pois deixa uma janela temporal de inconsistência durante a cópia e pode corromper arquivos se interrompido.
  - `mv dir_novo dir_antigo`: rejeitado pois falha com `ENOTEMPTY` no kernel e requer `rm -rf` prévio, criando downtime e risco de estado quebrado se falhar.

## Decisão 8: Persistência de Context Lifting via Symlink para `~/.vitalia-shared/tmp/`

- **Escolhido**: Diretório persistente `~/.vitalia-shared/tmp/`, linkado em cada release via `~/.vitalia-releases/<timestamp>/tmp -> ~/.vitalia-shared/tmp`.
- **Verificado em**: [The Twelve-Factor App: Processes (Stateless releases)](https://12factor.net/processes), [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) em 02-11-2026.
- **Justificativa**: Os stubs JSON de Context Lifting gerados pelo `vitalia_hook_runner.py` representam estado de sessão ativo. As releases do kit devem ser imutáveis e auditáveis, mas o estado efêmero de sessão deve persistir e sobreviver a todos os upgrades sem perda de contexto.
- **Alternativas**:
  - Copiar `tmp/` a cada upgrade: rejeitado por lentidão e duplicação desnecessária de I/O em diretórios de release.
  - Usar `/tmp/` do SO: rejeitado pelo Princípio P07 (Zero Data Leak) e porque `/tmp` pode ser limpo automaticamente por `systemd-tmpfiles` ou reboot.

## Decisão 9: Auto-Teste Pré-Promoção em Staging Isolado (`<ts>.staging`)

- **Escolhido**: Preparar a nova release em `~/.vitalia-releases/<ts>.staging/` e rodar bateria completa de self-test (`bash -n`, sourcing sob `set -euo pipefail`, testes sintáticos Python e teste de manifesto) antes do rename atômico.
- **Verificado em**: [Martin Fowler: Blue-Green Deployment](https://martinfowler.com/bliki/BlueGreenDeployment.html) em 02-11-2026.
- **Justificativa**: Garante fail-fast estrito: se qualquer script de biblioteca ou Python contiver sintaxe inválida ou quebrar sob `pipefail`, a execução é abortada no staging e a release ativa anterior continua rodando intacta.
- **Alternativas**:
  - Teste pós-promoção com rollback: rejeitado porque gera instabilidade temporária e o processo de rollback também pode falhar.
  - Sem auto-teste: rejeitado pelo histórico de falha do `ai-control`.

## Decisão 10: Resolução Determinística de Manifesto com `awk` em `agent_preserver.sh`

- **Escolhido**: `awk -v p="$rel_path" '$2 == p { print $1; exit }' "$manifest_file" || true`.
- **Verificado em**: [GNU Awk User's Guide (POSIX awk standard)](https://www.gnu.org/software/gawk/manual/gawk.html) em 02-11-2026.
- **Justificativa**: Sob `set -o pipefail`, o pipeline `grep -E ... | awk ...` retorna exit code 1 quando `grep` não encontra a chave (como ocorre na primeira instalação de novas skills), abortando imediatamente o script sob `set -e`. O `awk` lê o arquivo diretamente, encerra no primeiro match e não falha quando a chave não existe.
- **Alternativas**:
  - `grep ... || true | awk ...`: rejeitado pois pode mascarar erros genuínos de I/O e altera o comportamento de subshells.
  - Loop `while read` em bash puro: rejeitado pela sobrecarga desnecessária de performance em comparação com `awk`.

## Decisão 11: Resolução Explícita de Symlinks (`.resolve()`) no Guardrail Zero Data Leak de `vitalia_handoff.py`

- **Escolhido**: `kit_dir = Path(kit_dir_env).resolve() if kit_dir_env else (home / ".vitalia").resolve()`.
- **Verificado em**: [Python pathlib.Path.resolve() documentation (PEP 428)](https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve) em 02-11-2026.
- **Justificativa**: Quando `~/.vitalia` se torna um symlink apontando para `~/.vitalia-releases/<ts>`, o método `resolved_storage.relative_to(kit_dir)` falharia com `ValueError` se um caminho estivesse resolvido (real) e o outro permanecesse como caminho do symlink. Resolver explicitamente ambos garante a comparação canônica no filesystem.
- **Alternativas**:
  - Comparação textual simples de prefixos de string: rejeitado porque não lida com symlinks, `..` ou normalização de caminhos no Unix.

