"""Liga Geo Diaria: servidor FastAPI que guarda los resultados en Postgres (o SQLite en local)."""
import json
import os
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

PLAYERS = ["Pablopa", "Nani", "Vale", "Sopi", "Marta", "JP", "Mija", "Anto", "Coco", "Seba"]
PIN = os.environ.get("LIGA_PIN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Liga Geo Diaria")


# ---------- base de datos ----------
def _pg():
    import psycopg
    return psycopg.connect(DATABASE_URL, autocommit=True)


def _sqlite():
    con = sqlite3.connect(Path(__file__).parent / "liga.db")
    con.row_factory = sqlite3.Row
    return con


USE_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
PH = "%s" if USE_PG else "?"


def db():
    return _pg() if USE_PG else _sqlite()


def init_db() -> None:
    detail_type = "JSONB" if USE_PG else "TEXT"
    with db() as con:
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS results (
                player     TEXT NOT NULL,
                day        TEXT NOT NULL,
                game       TEXT NOT NULL,
                score      DOUBLE PRECISION NOT NULL,
                detail     {detail_type},
                updated_at TEXT NOT NULL,
                PRIMARY KEY (player, day, game)
            )""")


init_db()


# ---------- modelos ----------
class Result(BaseModel):
    player: str
    day: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    game: Literal["globle", "flagle", "maptap"]
    score: float = Field(ge=0, le=100000)
    detail: Any = None

    @field_validator("player")
    @classmethod
    def known_player(cls, v: str) -> str:
        if v not in PLAYERS:
            raise ValueError("jugador desconocido")
        return v

    @field_validator("day")
    @classmethod
    def real_date(cls, v: str) -> str:
        date.fromisoformat(v)
        return v

    @field_validator("detail")
    @classmethod
    def small_detail(cls, v: Any) -> Any:
        if v is not None and len(json.dumps(v, ensure_ascii=False)) > 2000:
            raise ValueError("detalle demasiado largo")
        return v


class SaveRequest(BaseModel):
    results: list[Result] = Field(min_length=1, max_length=60)


def check_pin(x_pin: str | None) -> None:
    if not PIN:
        raise HTTPException(500, "Falta configurar LIGA_PIN en el servidor")
    if (x_pin or "").strip() != PIN:
        raise HTTPException(401, "PIN incorrecto")


# ---------- rutas ----------
@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/api/players")
def players():
    return PLAYERS


@app.get("/api/results")
def list_results():
    with db() as con:
        cur = con.execute("SELECT player, day, game, score, detail FROM results ORDER BY day")
        rows = cur.fetchall()
    out = []
    for r in rows:
        player, day, game, score, detail = (r[0], r[1], r[2], r[3], r[4])
        if not USE_PG and isinstance(detail, str):  # SQLite stores JSON as text; Postgres JSONB comes back decoded
            detail = json.loads(detail)
        out.append({"player": player, "day": day, "game": game, "score": score, "detail": detail})
    return out


@app.post("/api/pin")
def verify_pin(x_pin: str | None = Header(default=None)):
    check_pin(x_pin)
    return {"ok": True}


@app.post("/api/results")
def save_results(body: SaveRequest, x_pin: str | None = Header(default=None)):
    check_pin(x_pin)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    sql = (
        f"INSERT INTO results (player, day, game, score, detail, updated_at) "
        f"VALUES ({PH},{PH},{PH},{PH},{PH + '::jsonb' if USE_PG else PH},{PH}) "
        f"ON CONFLICT (player, day, game) DO UPDATE SET "
        f"score = EXCLUDED.score, detail = EXCLUDED.detail, updated_at = EXCLUDED.updated_at"
    )
    with db() as con:
        for r in body.results:
            detail = json.dumps(r.detail, ensure_ascii=False) if r.detail is not None else None
            con.execute(sql, (r.player, r.day, r.game, r.score, detail, now))
    return {"saved": len(body.results)}


@app.delete("/api/results/{player}/{day}/{game}")
def delete_result(player: str, day: str, game: str, x_pin: str | None = Header(default=None)):
    check_pin(x_pin)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise HTTPException(400, "fecha inválida")
    with db() as con:
        con.execute(f"DELETE FROM results WHERE player={PH} AND day={PH} AND game={PH}", (player, day, game))
    return {"ok": True}
