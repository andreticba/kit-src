#!/usr/bin/env python3
# utils.py | Vitalia Kit — Domínio CORE
# Atualizado em: 28-08-2026 08:59:34(GMT-04:00)
"""
Módulo de Utilitários Compartilhados — Vitalia Kit (Domínio CORE)

Responsabilidades:
1. Geração e formatação de timestamps padronizados no fuso horário imutável America/Cuiaba (GMT-04:00).
2. Formatação de cabeçalhos de rastreabilidade para arquivos de código e visões Markdown.
3. Geração determinística de identificadores SHA256 únicos para registros de decisões e aprendizados.
4. Helpers robustos de I/O para leitura e append atômico em arquivos transacionais JSON Lines (.jsonl).

Didática para Desenvolvedores Iniciantes:
- Por que usamos (GMT-04:00)? Para garantir que desenvolvedores em diferentes fusos sincronizem
  contexto e ordenem eventos cronologicamente sem ambiguidades.
- Por que usamos JSON Lines (.jsonl)? Porque arquivos JSONL permitem operações de append atômicas
  (adicionar uma linha ao final) sem precisar reescrever ou carregar o arquivo inteiro na memória.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Fuso horário padrão imutável do ecossistema Vitalia (UTC-4 / America/Cuiaba)
VITALIA_TIMEZONE = timezone(timedelta(hours=-4))


def get_current_datetime() -> datetime:
    """
    Retorna o objeto datetime atual no fuso horário America/Cuiaba (GMT-04:00).
    """
    return datetime.now(VITALIA_TIMEZONE)


def get_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Gera string de timestamp no formato canônico da Vitalia: DD-MM-YYYY HH:MM:SS(GMT-04:00).
    Exemplo de retorno: '28-08-2026 08:59:34(GMT-04:00)'
    """
    if dt is None:
        dt = get_current_datetime()
    return dt.strftime("%d-%m-%Y %H:%M:%S(GMT-04:00)")


def format_visible_header(dt: Optional[datetime] = None) -> str:
    """
    Retorna a linha visível obrigatória para o corpo de documentos Markdown.
    Exemplo: '**Data/Hora de Geração:** 28-08-2026 08:59:34(GMT-04:00) | **Fuso Horário:** America/Cuiaba (GMT-04:00)'
    """
    ts = get_timestamp(dt)
    return f"**Data/Hora de Geração:** `{ts}` | **Fuso Horário:** America/Cuiaba `(GMT-04:00)`"


def generate_id(content: str, length: int = 8) -> str:
    """
    Gera um hash hexadecimal SHA256 determinístico a partir de uma string de conteúdo.
    Útil para criar identificadores únicos imutáveis de decisões e aprendizados.
    
    Parâmetros:
      content (str): Texto base para o hash (ex: timestamp + máquina + descrição).
      length (int): Quantidade de caracteres do hash retornado (padrão: 8 caracteres).
    """
    hash_obj = hashlib.sha256(content.encode('utf-8'))
    return hash_obj.hexdigest()[:length]


def read_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """
    Lê um arquivo JSON Lines (.jsonl) de forma resiliente e retorna uma lista de dicionários.
    Linhas vazias ou inválidas são ignoradas graciosamente sem interromper a leitura das demais.
    
    Parâmetros:
      file_path (Path): Caminho do arquivo .jsonl a ser lido.
    """
    records = []
    if not file_path.exists() or not file_path.is_file():
        return records

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_idx, line in enumerate(f, start=1):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    records.append(data)
                except json.JSONDecodeError as err:
                    # Log amigável sem travar o processo
                    print(f"⚠️ [core.utils] Aviso: Linha {line_idx} inválida em {file_path.name}: {err}", file=sys.stderr)
    except Exception as e:
        print(f"❌ [core.utils] Erro ao ler {file_path}: {e}", file=sys.stderr)

    return records


def append_jsonl(file_path: Path, record: Dict[str, Any]) -> bool:
    """
    Adiciona um registro (dicionário Python) como uma nova linha ao final de um arquivo .jsonl.
    Cria os diretórios pais automaticamente se não existirem.
    
    Parâmetros:
      file_path (Path): Caminho de destino do arquivo .jsonl.
      record (dict): Dicionário com os dados do registro.
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
        return True
    except Exception as e:
        print(f"❌ [core.utils] Falha ao gravar append em {file_path}: {e}", file=sys.stderr)
        return False
