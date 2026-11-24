"""Gera docs/openapi.json a partir do código (a mesma especificação que o Swagger UI mostra em /docs).

Uso: python -m scripts.exportar_openapi
Rode de novo sempre que mudar uma rota ou um schema, e faça commit do docs/openapi.json.
"""
import json
from pathlib import Path

from app.main import app

DESTINO = Path(__file__).resolve().parent.parent / "docs" / "openapi.json"


def main() -> None:
    spec = app.openapi()
    # A página estática (docs/index.html) não tem servidor próprio: o "Try it out" aponta para a API local.
    spec["servers"] = [{"url": "http://localhost:8000", "description": "API rodando localmente (uvicorn)"}]
    DESTINO.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Especificação salva em {DESTINO} ({len(spec['paths'])} rotas)")


if __name__ == "__main__":
    main()
