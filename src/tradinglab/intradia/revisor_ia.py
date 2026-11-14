"""Analista IA que revisa cada señal antes de ejecutarla.

No usa la API de pago de Anthropic. La opción 'claude_cli' llama a Claude Code instalado en tu PC
(`claude -p ...`), que funciona con tu suscripción de Claude. Claude aplica la skill
`.claude/skills/revisor-senal-intradia` (noticias, contexto de mercado, coherencia de la señal).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

from ..common.config import RAIZ
from .modelos import ResultadoCapa, Senal


class RevisorNinguno:
    def revisar(self, s: Senal, contexto: dict) -> ResultadoCapa:
        return ResultadoCapa("ia", True, "IA desactivada", {"veredicto": "sin_ia"})


class RevisorClaudeCLI:
    def __init__(self, tiempo_maximo_seg: int = 120, si_falla: str = "dejar_pasar"):
        self.timeout = tiempo_maximo_seg
        self.si_falla = si_falla
        self.exe = shutil.which("claude")

    def _prompt(self, s: Senal, contexto: dict) -> str:
        return (
            "Usa la skill revisor-senal-intradia.\n"
            f"Señal propuesta: {s.lado.upper()} {s.simbolo} a {s.entrada:.2f}. "
            f"Stop {s.stop:.2f}, objetivo {s.objetivo:.2f}. Estrategia: {s.estrategia} ({s.motivo}).\n"
            f"Contexto: {json.dumps(contexto, ensure_ascii=False, default=str)}\n"
            'Responde SOLO con un JSON en una línea: {"veredicto": "pasa" o "frena", '
            '"confianza": 0-100, "motivo": "frase corta en español"}'
        )

    def _fallo(self, motivo: str) -> ResultadoCapa:
        return ResultadoCapa("ia", self.si_falla == "dejar_pasar", f"Fallo de la IA: {motivo}",
                             {"veredicto": "error"})

    def revisar(self, s: Senal, contexto: dict) -> ResultadoCapa:
        if not self.exe:
            return self._fallo("no encuentro el comando 'claude' (instala Claude Code)")
        try:
            r = subprocess.run(
                [self.exe, "-p", self._prompt(s, contexto), "--output-format", "json",
                 "--allowedTools", "WebSearch", "WebFetch", "Read"],
                cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", timeout=self.timeout,
            )
            texto = json.loads(r.stdout).get("result", "") if r.stdout.strip().startswith("{") else r.stdout
            m = re.search(r"\{[^{}]*\"veredicto\"[^{}]*\}", texto)
            if not m:
                return self._fallo("respuesta sin JSON")
            d = json.loads(m.group(0))
            pasa = str(d.get("veredicto", "")).lower().startswith("pasa")
            return ResultadoCapa("ia", pasa, d.get("motivo", ""), d)
        except subprocess.TimeoutExpired:
            return self._fallo(f"tardó más de {self.timeout} s")
        except Exception as e:  # noqa: BLE001
            return self._fallo(str(e)[:200])


def crear(cfg_ia: dict):
    if cfg_ia.get("revisor") == "claude_cli":
        return RevisorClaudeCLI(cfg_ia.get("tiempo_maximo_seg", 120), cfg_ia.get("si_falla_la_ia", "dejar_pasar"))
    return RevisorNinguno()
