import os

# Precisa vir ANTES de importar o app: banco em memória e hash rápido.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["PBKDF2_ITERATIONS"] = "1000"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.services.usuarios import garantir_chefe


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as sessao:
        garantir_chefe(sessao)
        yield sessao


@pytest.fixture()
def client(db):
    return TestClient(app)


def auth(client, login, senha):
    r = client.post("/auth/login", json={"login": login, "senha": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def chefe(client):
    return auth(client, "admin", "admin123")


@pytest.fixture()
def cenario(client, chefe):
    """Eleição AGENDADA com 2 candidatos a Governador, 1 a Presidente e 2 eleitores."""
    eleicao = client.post("/eleicoes", headers=chefe, json={"titulo": "Teste", "data": "2026-10-04", "turno": 1, "hora_abertura": "08:00", "hora_encerramento": "17:00"}).json()
    cands = {}
    for chave, nome, login, num, partido, cargo in [
        ("g1", "Ana Gov", "ana", 11, "AAA", "GOVERNADOR"),
        ("g2", "Bia Gov", "bia", 22, "BBB", "GOVERNADOR"),
        ("p1", "Caio Pres", "caio", 33, "CCC", "PRESIDENTE"),
    ]:
        r = client.post("/candidatos", headers=chefe, json={"nome": nome, "login": login, "senha": "1234", "numero": num, "partido": partido, "cargo": cargo, "eleicao_id": eleicao["id"]})
        assert r.status_code == 201, r.text
        cands[chave] = r.json()
    for login in ("eleitor1", "eleitor2"):
        assert client.post("/eleitores", headers=chefe, json={"nome": login.title(), "login": login, "senha": "1234"}).status_code == 201
    return {"eleicao": eleicao, "cands": cands}


def abrir(client, chefe, eleicao_id):
    assert client.post(f"/eleicoes/{eleicao_id}/abrir", headers=chefe).status_code == 200


def votar(client, headers, eleicao_id, candidato_id, confirmado=True):
    return client.post(f"/eleicoes/{eleicao_id}/votos", headers=headers, json={"candidato_id": candidato_id, "confirmado": confirmado})
