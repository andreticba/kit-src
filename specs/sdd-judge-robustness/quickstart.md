<!-- quickstart.md | Vitalia SDD v0.6.0 | 12-10-2026 20:50(GMT-04:00) -->
# Quickstart & Guia de Validação: sdd-judge-robustness

Este guia contém os cenários de validação end-to-end do juiz constitucional reformulado.

---

## 1. Pré-Requisitos
1. Ollama rodando localmente na máquina:
   ```bash
   ollama list
   # Certifique-se de que phi4-mini e qwen2.5-coder:7b estão instalados
   ollama pull phi4-mini
   ```
2. Arquivo `.env` configurado na raiz com `OLLAMA_REASONING_MODEL=phi4-mini`.

---

## 2. Cenários Executáveis de Validação

### Cenário 1: Auditoria Atômica de Tarefas no modo 1-a-1 com Varredura Completa
Valida se o juiz inspeciona tarefa por tarefa sem truncar e emite o relatório tabular com o banner transparente do Ollama:

```bash
python3 source/src/hooks/sdd_judge/cli.py --mode tasks specs/sdd-judge-robustness/fixtures/valid_tasks.md
```
**Resultado Esperado:**
- Banner impresso: `--- PARECER DO JUIZ [Ollama: phi4-mini | X.XXs] ---`
- Painel consolidado com status individual de cada `T001`, `T002`, etc.
- Exit code `0` (PASS).

---

### Cenário 2: Detecção de Falha Constitucional com `suggested_fix`
Submeter um arquivo de tarefas contendo uma task sem declaração de teste (violação P05):

```bash
python3 source/src/hooks/sdd_judge/cli.py --mode tasks specs/sdd-judge-robustness/fixtures/invalid_tasks.md
```
**Resultado Esperado:**
- Terminal exibe `🚫 T002 [BLOCK] (Violação P05: Test-First Development)`
- Linha sugerida de correção exibida diretamente no console:
  `Sugestão: - [ ] T002 [P] [US1] Escrever teste unitário para BaseEvaluator em tests/test_base.py`
- Exit code `1` (BLOCK).

---

### Cenário 3: Resiliência de Timeout em Queda de Nó (Exit Code 2)
Simular queda do serviço Ollama para confirmar a distinção entre erro constitucional e erro de infraestrutura:

```bash
OLLAMA_URL=http://localhost:9999/api/generate python3 source/src/hooks/sdd_judge/cli.py --mode tasks specs/sdd-judge-robustness/fixtures/valid_tasks.md
```
**Resultado Esperado:**
- Terminal exibe: `🔌 VEREDICTO FINAL: INFRA_FAIL (exit code 2)`
- Mensagem explícita: "Este NÃO é um BLOCK constitucional".
- Exit code `2`.
