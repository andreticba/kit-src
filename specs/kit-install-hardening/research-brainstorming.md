<!-- research-brainstorming.md | Vitalia SDD v0.6.0 | 02-11-2026 08:45:00(GMT-04:00) -->
> **research-brainstorming.md | Vitalia SDD v0.6.0 | 02-11-2026 08:45:00(GMT-04:00)**

# Síntese de Concepção: Atualização Atômica e Resiliente do Vitalia Kit

**Feature:** Kit Install Hardening — Atualização Atômica e Pre-flight (Adendo v0.6.1)  
**Origem:** Validação funcional da v0.6.0 no projeto `ai-control` em 02-11-2026  
**Status:** EM ALINHAMENTO SOCRÁTICO (Pesquisa Externa Concluída)

---

## 1. Resumo Executivo e Contexto do Incidente

Durante a validação prática da atualização do Kit no projeto existente `ai-control`, o script `install-project` foi interrompido no Passo 5 logo após a primeira skill (`vitalia-adr`). A causa raiz diagnosticada foi a quebra da diretiva `set -euo pipefail` na função `get_manifest_hash` de `agent_preserver.sh`: ao consultar uma skill ainda não registrada em um manifesto pré-existente, o `grep` retornou código de saída `1`, abortando o script imediatamente.

O incidente levantou um problema arquitetural mais profundo: **como garantir que atualizações do Kit não interrompam no meio do caminho deixando o sistema em estado corrompido ("kit quebrado")?**

Foi realizada uma pesquisa aprofundada em fontes oficiais e padrões da indústria para fundamentar a arquitetura do instalador.

---

## 2. Achados da Pesquisa Externa (Grounding & Padrões da Indústria)

### 2.1 Limitações de Kernel no `rename(2)` para Diretórios
- Conforme a documentação oficial da chamada de sistema `rename(2)` (`man 2 rename`), um `rename(old, new)` é estritamente atômico, mas se `new` for um diretório existente **não-vazio**, a chamada falha com o erro `ENOTEMPTY` ou `EEXIST`.
- Consequentemente, não é possível substituir um diretório existente não-vazio por outro via `mv` direto em um único passo no Linux.
- Se o instalador fizer dois passos (`mv ~/.vitalia ~/.vitalia.bak` e depois `mv ~/.vitalia.staging ~/.vitalia`), existe uma janela de tempo onde `~/.vitalia` não existe. Se o processo for interrompido nesse exato intervalo (SIGINT/falha de energia), o ambiente fica quebrado.

### 2.2 Padrão de Releases e Symlink Swap (Capistrano / Deployer)
- A solução padrão na indústria para zero-downtime e substituição atômica sem janela de inconsistência utiliza symlinks:
  - Estrutura: `~/.vitalia-releases/<timestamp>/` para cada versão instalada.
  - Caminho ativo: `~/.vitalia` é um symlink para a release ativa.
  - Dados persistentes (`shared`): diretórios de estado de runtime (como `tmp/` contendo os stubs JSON de contexto do Guardian) residem em `~/.vitalia-shared/tmp/` e são linkados simbolicamente dentro de cada release.
  - **Troca Atômica:** A substituição é feita com link temporário e renomeação via flag `-T`:
    ```bash
    ln -s ~/.vitalia-releases/20261102083000 ~/.vitalia.tmp
    mv -T ~/.vitalia.tmp ~/.vitalia
    ```
    Isso executa um `rename(2)` sobre um symlink (não sobre um diretório físico), o que é garantidamente atômico no kernel POSIX.

### 2.3 Fragilidade de `set -e` / `pipefail` (Greg's Wiki BashFAQ/105)
- O guia canônico *BashFAQ/105 (Pleasures and perils of set -e)* demonstra que `set -e` combinado com `pipefail` causa armadilhas graves quando pipelines contêm comandos que retornam código diferente de zero de forma esperada (como `grep` quando não encontra correspondência).
- A substituição de pipelines `grep | awk | head` por um único comando `awk -v p="$key" '$2 == p { print $1; exit }' file` é o padrão recomendado: o `awk` trata a busca internamente e termina com exit code `0` com ou sem match.

### 2.4 Especificação XDG Base Directory e Preservação de Estado (`tmp/`)
- A especificação XDG distingue dados de configuração (`$XDG_CONFIG_HOME`), dados de aplicação (`$XDG_DATA_HOME`) e estado transitório persistente (`$XDG_STATE_HOME`).
- O diretório `~/.vitalia/tmp/` armazena stubs JSON de Context Lifting gerados durante sessões ativas. Uma atualização de versão nunca deve descartar ou limpar o `tmp/` de sessões em andamento.

### 2.5 Impacto Crítico no Guardrail Zero Data Leak de `vitalia_handoff.py`
- Em [vitalia_handoff.py](file:///home/andre/projetos/assistidos/kit_src/source/src/vitalia_handoff.py#L41), a variável `kit_dir` é definida como `(home / ".vitalia")` sem chamar `.resolve()`.
- Se `~/.vitalia` for um symlink para `~/.vitalia-releases/...`, `storage_dir.resolve()` resultará no caminho físico real, enquanto `kit_dir` seria o link não resolvido.
- A comparação `resolved_storage.relative_to(kit_dir)` falharia silenciosamente com `ValueError`, desativando acidentalmente o guardrail de proteção.
- **Correção obrigatória:** Garantir `(home / ".vitalia").resolve()` explicitamente em [vitalia_handoff.py](file:///home/andre/projetos/assistidos/kit_src/source/src/vitalia_handoff.py#L41) e [vitalia_handoff.py](file:///home/andre/projetos/assistidos/kit_src/source/src/vitalia_handoff.py#L103).

---

## 3. Rastro de Pesquisa e Grounding (P03)

| # | Afirmação / Fato Técnico | Verificado? | Fonte / Evidência | Data |
|---|---------------------------|-------------|-------------------|------|
| 1 | `rename(2)` falha com `ENOTEMPTY` se o destino for diretório não vazio | Sim | [man7.org rename(2)](https://man7.org/linux/man-pages/man2/rename.2.html) | 02-11-2026 |
| 2 | Troca de symlink com `mv -T` é atômica no Linux | Sim | GNU Coreutils `mv -T` / Linux kernel `rename(2)` | 02-11-2026 |
| 3 | `ln -sfn` não é atômico (executa unlink + link separados) | Sim | GNU `ln` source / Deployer docs / Stack Overflow | 02-11-2026 |
| 4 | `grep` sem match retorna exit 1 e derruba subshell sob `pipefail` | Sim | [mywiki.wooledge.org/BashFAQ/105](https://mywiki.wooledge.org/BashFAQ/105) | 02-11-2026 |
| 5 | Capistrano isola releases e compartilha estado persistente via `shared/` | Sim | [capistranorb.com structure docs](https://capistranorb.com/documentation/getting-started/structure/) | 02-11-2026 |
| 6 | Sem `.resolve()` em `kit_dir`, symlinks quebram `relative_to` no Python | Sim | Inspecionado em `source/src/vitalia_handoff.py` L41 e L103 | 02-11-2026 |

---

## 4. Decisões Arquiteturais Acordadas

1. **Auditoria Histórica Completa:** Preservar todas as versões anteriores para auditoria e possibilidade de rollback manual.
2. **Auto-Teste de Sanidade no Staging (Self-Test):** Nenhuma versão é promovida se falhar nos testes prévios (`bash -n`, carregamento sob `pipefail`, busca em manifesto vazio e integridade de templates).
3. **Resolução Determinística do Manifesto com `awk`:** Eliminação de pipelines frágeis de grep em `agent_preserver.sh`.
4. **Preservação Contínua de `tmp/`:** O diretório de stubs de contexto nunca é expurgado durante atualizações.
5. **Correção de `.resolve()` em `vitalia_handoff.py`:** Blindagem do guardrail Zero Data Leak para suportar tanto diretório físico quanto symlink.

---

## 5. Decisão Aprovada pelo Usuário

### Decisão Ratificada: Opção 1 — Padrão Capistrano (Symlink Atômico com `releases/` e `shared/`)

- **Estrutura de Diretórios no `$HOME`:**
  - `~/.vitalia` -> Symlink apontando para a release ativa (ex: `~/.vitalia-releases/20261102084500`).
  - `~/.vitalia-releases/<timestamp>/` -> Diretórios imutáveis de cada versão instalada (auditoria histórica completa).
  - `~/.vitalia-shared/tmp/` -> Diretório compartilhado de estado e stubs de contexto, symlinkado como `~/.vitalia/tmp`.
- **Fluxo do `kit-bootstrap.sh`:**
  1. Cria diretório de staging isolado: `~/.vitalia-releases/<timestamp>.staging/`.
  2. Executa `rsync` dos arquivos novos para o staging.
  3. Realiza auto-teste de sanidade completa dentro do staging (`bash -n`, carregamento sob `pipefail`, teste de manifesto e integridade de templates).
  4. Se falhar: remove o staging e aborta sem tocar no `~/.vitalia` ativo.
  5. Se passar:
     - Renomeia o staging para o caminho final da release: `mv ~/.vitalia-releases/<timestamp>.staging ~/.vitalia-releases/<timestamp>`.
     - Symlinka o estado persistente: `ln -sfn ~/.vitalia-shared/tmp ~/.vitalia-releases/<timestamp>/tmp`.
     - Executa o swap atômico de kernel via GNU `mv -T`:
       ```bash
       ln -s ~/.vitalia-releases/<timestamp> ~/.vitalia.tmp
       mv -T ~/.vitalia.tmp ~/.vitalia
       ```
  6. **Migração do Legado:** Na primeira execução sob este modelo, caso `~/.vitalia` seja um diretório real existente, o bootstrap migra o diretório para `~/.vitalia-releases/<timestamp_legado>`, move `tmp/` para `~/.vitalia-shared/tmp/` e estabelece o symlink inicial.
- **Blindagem do Guardrail em `vitalia_handoff.py`:**
  - Garantir `.resolve()` explícito em `(home / ".vitalia").resolve()` para que comparações de caminhos funcionem com precisão quando `~/.vitalia` for um symlink.

---

## 6. Próximos Passos no SDD

Concepção finalizada com consenso e grounding de padrões da indústria. O próximo passo inviolável é acionar o despachante oficial `/vitalia-route` para registrar a transição determinística e despachar para o especialista de especificação.
