# loader.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
import os
from pathlib import Path
from string import Template

try:
    import yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False


def load_prompt_template(mode: str, **kwargs) -> str:
    """Carrega o template de prompt YAML referente ao modo e interpola variáveis via string.Template."""
    prompts_dir = Path(__file__).resolve().parent
    prompt_file = prompts_dir / f"{mode}.yaml"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Template de prompt não encontrado: {prompt_file}")

    content = prompt_file.read_text(encoding="utf-8")
    template_str = ""

    if _YAML_OK:
        data = yaml.safe_load(content)
        if isinstance(data, dict) and "template" in data:
            template_str = data["template"]
        else:
            template_str = content
    else:
        # Fallback simples se PyYAML não estiver presente
        if "template: |" in content:
            template_str = content.split("template: |", 1)[1]
        else:
            template_str = content

    tmpl = Template(template_str)
    return tmpl.safe_substitute(**kwargs)
