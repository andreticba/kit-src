<!-- adversarial_subagent_architecture.md | Vitalia SDD v0.6.0 | 16-10-2026 13:27(GMT-04:00) -->

# Fluxo Arquitetural: Sub-Agente Adversarial e Privacy Gateway (Vitalia SDD v0.6.0)

Este documento detalha o funcionamento do **Sub-Agente Promotor Constitucional (Red Team)** operando em conjunto com o **Privacy Proxy Gateway Local**, garantindo separação de privilégios e proteção estrita de PII/PHI.

---

## 1. Diagrama de Sequência: Agente Construtor vs. Sub-Agente Red Team

```mermaid
sequenceDiagram
    autonumber
    actor Dev as "Desenvolvedor"
    participant MainAgent as "Agente Construtor (IDE)"
    participant SubAgent as "Sub-Agente Promotor (Red Team)"
    participant PrivacyGate as "Privacy Gateway Local"
    participant Disk as "Disco (tasks.md)"
    participant Hook as "Hook Final (sdd_judge)"

    Dev->>MainAgent: Aciona /vitalia-spec-tasks
    MainAgent->>MainAgent: Gera proposta preliminar de tarefas a partir de spec.md
    
    rect rgb(240, 248, 255)
        note over MainAgent,SubAgent: Debate Adversarial In-Process (Separacao de Privilegios P01)
        MainAgent->>SubAgent: Spawna Sub-Agente com Prompt Hostil Red Team
        note over SubAgent: Opera em contexto isolado sem vies de autoria
        SubAgent-->>MainAgent: Emite Relatorio de Contestacao (ex: Falha P05 na T004)
        MainAgent->>MainAgent: Refatora T004 para sanar a contestacao
        MainAgent->>SubAgent: Envia nova redacao para reavaliacao
        SubAgent-->>MainAgent: Veredito: APROVADO (Consenso Atingido)
    end

    rect rgb(255, 250, 240)
        note over MainAgent,PrivacyGate: Camada de Protecao P07/P09 (Zero-Leak PHI/PII)
        MainAgent->>PrivacyGate: Inspeciona tasks.md gerado contra padroes de PII/PHI
        alt Detectado PHI/PII Clinico Nao-Anonimizavel
            PrivacyGate-->>MainAgent: Bloqueia transito externo (100% Ollama Offline)
        else Dados Tecnicos Seguros ou Pseudonimizaveis
            PrivacyGate-->>MainAgent: Libera com sanitizacao de tokens
        end
    end

    MainAgent->>Disk: Grava tasks.md definitivo com backup preventivo
    MainAgent->>Hook: Executa sdd_judge.py --mode tasks no [hooks].after
    Hook-->>Dev: Exit Code 0 (Certificacao Constitucional)
```

---

## 2. Princípios Constitucionais Atendidos

1. **P01 (SDD Pipeline Inviolability & Separation of Concerns):** O agente que constrói o código não é o único validador de si mesmo. O Sub-Agente atua como auditor externo independente.
2. **P07 (Data Sovereignty) & P09 (Clinical Safety Gate):** O Privacy Gateway analisa o payload antes de qualquer trânsito na rede. Dados sensíveis de saúde nunca saem do ambiente local.
3. **P11 (Hardware Agnosticism):** Modelos e parâmetros são resolvidos dinamicamente via `.env`, preservando o funcionamento em qualquer hardware ou provedor.
4. **P12 (Agent Security & Constrained Output):** Todos os vereditos entre o Sub-Agente e o Agente Principal utilizam schemas JSON formais, anulando alucinações de recusa ou comandos malformados.
