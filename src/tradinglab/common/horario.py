"""Horario de la sesión. Se trabaja en hora de Nueva York para evitar líos con los cambios de hora."""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")


def _hora(txt: str) -> time:
    h, m = txt.split(":")
    return time(int(h), int(m))


class Horario:
    def __init__(self, cfg: dict):
        self.zona = ZoneInfo(cfg.get("zona", "America/New_York"))
        self.inicio = _hora(cfg["inicio"])
        self.fin_entradas = _hora(cfg["fin_entradas"])
        self.cierre = _hora(cfg["cierre_forzado"])

    def local(self, ts: datetime) -> time:
        return ts.astimezone(self.zona).time()

    def ahora(self) -> datetime:
        return datetime.now(self.zona)

    def en_ventana_entradas(self, ts: datetime) -> bool:
        return self.inicio <= self.local(ts) < self.fin_entradas

    def hay_que_cerrar(self, ts: datetime) -> bool:
        return self.local(ts) >= self.cierre

    def en_madrid(self, t: time) -> str:
        hoy = datetime.now(self.zona).replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return hoy.astimezone(MADRID).strftime("%H:%M")
