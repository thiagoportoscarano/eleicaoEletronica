"""Testes de integração: chamam a API real (HTTP + banco)."""
import jwt
from sqlalchemy import inspect, text

from app.config import settings
from app.database import engine
from tests.conftest import abrir, auth, votar


# ---------- Autenticação e perfis ----------
def test_login_ok_e_perfil(client):
    r = client.post("/auth/login", json={"login": "admin", "senha": "admin123"})
    assert r.status_code == 200 and r.json()["perfil"] == "CHEFE" and r.json()["access_token"]


def test_login_invalido_401(client):
    assert client.post("/auth/login", json={"login": "admin", "senha": "x"}).status_code == 401
    assert client.post("/auth/login", json={"login": "naoexiste", "senha": "x"}).status_code == 401


def test_rota_protegida_sem_token_401(client):
    assert client.get("/eleicoes").status_code == 401
    assert client.get("/eleicoes", headers={"Authorization": "Bearer lixo"}).status_code == 401


def test_token_adulterado_401(client, chefe):
    cabecalho, payload, assinatura = chefe["Authorization"].removeprefix("Bearer ").split(".")
    adulterado = f"{cabecalho}.{payload}.{assinatura[:-4]}AAAA"
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {adulterado}"})
    assert r.status_code == 401 and r.headers["WWW-Authenticate"] == "Bearer"


def test_token_expirado_401(client):
    expirado = jwt.encode({"sub": "1", "perfil": "CHEFE", "exp": 1}, settings.secret_key, algorithm="HS256")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {expirado}"})
    assert r.status_code == 401 and "expirada" in r.json()["detail"]


def test_eleitor_nao_acessa_area_do_chefe(client, chefe, cenario):
    eleitor = auth(client, "eleitor1", "1234")
    assert client.get("/eleitores", headers=eleitor).status_code == 403
    assert client.post("/eleicoes", headers=eleitor, json={}).status_code == 403
    assert client.post(f"/eleicoes/{cenario['eleicao']['id']}/abrir", headers=eleitor).status_code == 403


def test_chefe_nao_vota(client, chefe, cenario):
    e = cenario["eleicao"]["id"]
    abrir(client, chefe, e)
    assert votar(client, chefe, e, cenario["cands"]["g1"]["id"]).status_code == 403


def test_candidato_nao_vota(client, chefe, cenario):
    e = cenario["eleicao"]["id"]
    abrir(client, chefe, e)
    assert votar(client, auth(client, "ana", "1234"), e, cenario["cands"]["g1"]["id"]).status_code == 403


# ---------- Gerenciamento ----------
def test_crud_eleitor(client, chefe):
    r = client.post("/eleitores", headers=chefe, json={"nome": "Maria", "login": "maria", "senha": "abcd"})
    assert r.status_code == 201 and "senha" not in r.json()
    eid = r.json()["id"]
    assert client.post("/eleitores", headers=chefe, json={"nome": "Outra", "login": "maria", "senha": "abcd"}).status_code == 409
    assert client.put(f"/eleitores/{eid}", headers=chefe, json={"nome": "Maria S."}).json()["nome"] == "Maria S."
    assert client.get("/eleitores?busca=maria", headers=chefe).json()[0]["id"] == eid
    assert client.delete(f"/eleitores/{eid}", headers=chefe).status_code == 204
    assert client.get(f"/eleitores/{eid}", headers=chefe).status_code == 404


def test_eleitor_que_ja_votou_nao_pode_ser_excluido(client, chefe, cenario):
    e = cenario["eleicao"]["id"]
    abrir(client, chefe, e)
    assert votar(client, auth(client, "eleitor1", "1234"), e, cenario["cands"]["g1"]["id"]).status_code == 201
    ids = {x["login"]: x["id"] for x in client.get("/eleitores", headers=chefe).json()}
    r = client.delete(f"/eleitores/{ids['eleitor1']}", headers=chefe)
    assert r.status_code == 409 and "já votou" in r.json()["detail"]
    assert client.delete(f"/eleitores/{ids['eleitor2']}", headers=chefe).status_code == 204  # quem não votou pode sair
    gov = next(x for x in client.get(f"/eleicoes/{e}/apuracao", headers=chefe).json()["cargos"] if x["cargo"] == "GOVERNADOR")
    assert gov["total_votos"] == 1  # o voto já computado continua na contagem


def test_eleitor_atualiza_senha_e_loga_com_a_nova(client, chefe):
    eid = client.post("/eleitores", headers=chefe, json={"nome": "Zé", "login": "zeca", "senha": "antiga"}).json()["id"]
    client.put(f"/eleitores/{eid}", headers=chefe, json={"senha": "novinha"})
    assert client.post("/auth/login", json={"login": "zeca", "senha": "antiga"}).status_code == 401
    assert client.post("/auth/login", json={"login": "zeca", "senha": "novinha"}).status_code == 200


def test_cadastro_de_eleicao_valida_horarios(client, chefe):
    ruim = {"data": "2026-10-04", "turno": 1, "hora_abertura": "17:00", "hora_encerramento": "08:00"}
    assert client.post("/eleicoes", headers=chefe, json=ruim).status_code == 422
    ok = client.post("/eleicoes", headers=chefe, json={**ruim, "hora_abertura": "08:00", "hora_encerramento": "17:00"})
    assert ok.status_code == 201 and ok.json()["situacao"] == "AGENDADA"


def test_candidato_numero_duplicado_no_mesmo_cargo(client, chefe, cenario):
    dup = {"nome": "Dud Gov", "login": "dud", "senha": "1234", "numero": 11, "partido": "X", "cargo": "GOVERNADOR", "eleicao_id": cenario["eleicao"]["id"]}
    assert client.post("/candidatos", headers=chefe, json=dup).status_code == 409
    # o login "dud" não pode ter ficado órfão
    assert client.post("/candidatos", headers=chefe, json={**dup, "numero": 99}).status_code == 201


def test_nao_altera_candidato_com_eleicao_aberta(client, chefe, cenario):
    abrir(client, chefe, cenario["eleicao"]["id"])
    cid = cenario["cands"]["g1"]["id"]
    assert client.put(f"/candidatos/{cid}", headers=chefe, json={"partido": "ZZZ"}).status_code == 409
    assert client.delete(f"/candidatos/{cid}", headers=chefe).status_code == 409


def test_abrir_e_encerrar_so_na_ordem_certa(client, chefe, cenario):
    e = cenario["eleicao"]["id"]
    assert client.post(f"/eleicoes/{e}/encerrar", headers=chefe).status_code == 409  # ainda AGENDADA
    abrir(client, chefe, e)
    assert client.post(f"/eleicoes/{e}/abrir", headers=chefe).status_code == 409  # já ABERTA
    assert client.get(f"/eleicoes/{e}", headers=chefe).json()["situacao"] == "ABERTA"
    assert client.post(f"/eleicoes/{e}/encerrar", headers=chefe).json()["situacao"] == "ENCERRADA"


def test_eleicao_atual(client, chefe, cenario):
    e = cenario["eleicao"]["id"]
    assert client.get("/eleicoes/atual", headers=chefe).json()["situacao"] == "AGENDADA"
    abrir(client, chefe, e)
    assert client.get("/eleicoes/atual", headers=chefe).json()["id"] == e


def test_eleicao_inexistente_404(client, chefe):
    assert client.get("/eleicoes/999", headers=chefe).status_code == 404


# ---------- Votação ----------
def test_eleitor_ve_candidatos_por_cargo(client, chefe, cenario):
    eleitor = auth(client, "eleitor1", "1234")
    cargos = client.get(f"/eleicoes/{cenario['eleicao']['id']}/cargos", headers=eleitor).json()
    assert [c["cargo"] for c in cargos] == ["GOVERNADOR", "PRESIDENTE"]
    assert len(cargos[0]["candidatos"]) == 2 and cargos[0]["ja_votou"] is False


def test_nao_vota_com_eleicao_agendada_nem_encerrada(client, chefe, cenario):
    e, g1 = cenario["eleicao"]["id"], cenario["cands"]["g1"]["id"]
    eleitor = auth(client, "eleitor1", "1234")
    r = votar(client, eleitor, e, g1)
    assert r.status_code == 409 and "não está aberta" in r.json()["detail"]
    abrir(client, chefe, e)
    client.post(f"/eleicoes/{e}/encerrar", headers=chefe)
    assert votar(client, eleitor, e, g1).status_code == 409


def test_voto_precisa_ser_confirmado(client, chefe, cenario):
    e = cenario["eleicao"]["id"]
    abrir(client, chefe, e)
    eleitor = auth(client, "eleitor1", "1234")
    assert votar(client, eleitor, e, cenario["cands"]["g1"]["id"], confirmado=False).status_code == 422
    assert client.get(f"/eleicoes/{e}/meus-votos", headers=eleitor).json()["cargos_votados"] == []


def test_um_voto_por_cargo_mas_pode_votar_em_outro_cargo(client, chefe, cenario):
    e, c = cenario["eleicao"]["id"], cenario["cands"]
    abrir(client, chefe, e)
    eleitor = auth(client, "eleitor1", "1234")
    assert votar(client, eleitor, e, c["g1"]["id"]).status_code == 201
    r = votar(client, eleitor, e, c["g2"]["id"])  # outro candidato, MESMO cargo
    assert r.status_code == 409 and "já votou" in r.json()["detail"]
    assert votar(client, eleitor, e, c["p1"]["id"]).status_code == 201  # cargo diferente: ok
    mv = client.get(f"/eleicoes/{e}/meus-votos", headers=eleitor).json()
    assert mv["cargos_votados"] == ["GOVERNADOR", "PRESIDENTE"] and mv["cargos_pendentes"] == []


def test_candidato_de_outra_eleicao_e_rejeitado(client, chefe, cenario):
    e1 = cenario["eleicao"]["id"]
    e2 = client.post("/eleicoes", headers=chefe, json={"data": "2026-10-25", "turno": 2, "hora_abertura": "08:00", "hora_encerramento": "17:00"}).json()["id"]
    abrir(client, chefe, e1)
    eleitor = auth(client, "eleitor1", "1234")
    cand_e2 = client.post("/candidatos", headers=chefe, json={"nome": "Dani Gov", "login": "dani", "senha": "1234", "numero": 55, "partido": "D", "cargo": "GOVERNADOR", "eleicao_id": e2}).json()
    assert votar(client, eleitor, e1, cand_e2["id"]).status_code == 404


# ---------- Sigilo ----------
def test_sigilo_nenhuma_tabela_liga_eleitor_ao_candidato(client, chefe, cenario):
    e, g1 = cenario["eleicao"]["id"], cenario["cands"]["g1"]["id"]
    abrir(client, chefe, e)
    assert votar(client, auth(client, "eleitor1", "1234"), e, g1).status_code == 201
    insp = inspect(engine)
    cols_voto = {c["name"] for c in insp.get_columns("votos")}
    cols_comp = {c["name"] for c in insp.get_columns("comparecimentos")}
    assert not {"eleitor_id", "usuario_id"} & cols_voto
    assert "candidato_id" not in cols_comp


def test_sigilo_tabela_votos_sem_rowid(client):
    """Sem rowid, o SQLite não guarda a ordem de inserção dos votos."""
    with engine.connect() as conn:
        ddl = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='votos'")).scalar_one()
    assert "WITHOUT ROWID" in ddl.upper()


# ---------- Apuração e resultado ----------
def test_apuracao_indisponivel_antes_de_abrir(client, chefe, cenario):
    assert client.get(f"/eleicoes/{cenario['eleicao']['id']}/apuracao", headers=chefe).status_code == 409


def test_apuracao_em_tempo_real_para_eleitor(client, chefe, cenario):
    e, c = cenario["eleicao"]["id"], cenario["cands"]
    abrir(client, chefe, e)
    e1, e2 = auth(client, "eleitor1", "1234"), auth(client, "eleitor2", "1234")
    votar(client, e1, e, c["g1"]["id"])
    votar(client, e2, e, c["g1"]["id"])
    votar(client, e1, e, c["p1"]["id"])
    ap = client.get(f"/eleicoes/{e}/apuracao", headers=e1).json()
    gov = next(x for x in ap["cargos"] if x["cargo"] == "GOVERNADOR")
    assert gov["total_votos"] == 2
    assert [(x["nome"], x["votos"]) for x in gov["candidatos"]] == [("Ana Gov", 2), ("Bia Gov", 0)]
    assert len(ap["cargos"]) == 2  # eleitor vê todos os cargos


def test_candidato_so_ve_o_proprio_cargo(client, chefe, cenario):
    e, c = cenario["eleicao"]["id"], cenario["cands"]
    abrir(client, chefe, e)
    votar(client, auth(client, "eleitor1", "1234"), e, c["p1"]["id"])
    ana = auth(client, "ana", "1234")  # Governador
    ap = client.get(f"/eleicoes/{e}/apuracao", headers=ana).json()
    assert [x["cargo"] for x in ap["cargos"]] == ["GOVERNADOR"]
    caio = auth(client, "caio", "1234")  # Presidente
    assert [x["cargo"] for x in client.get(f"/eleicoes/{e}/apuracao", headers=caio).json()["cargos"]] == ["PRESIDENTE"]


def test_candidato_so_ve_o_proprio_cargo_no_resultado(client, chefe, cenario):
    e, c = cenario["eleicao"]["id"], cenario["cands"]
    abrir(client, chefe, e)
    votar(client, auth(client, "eleitor1", "1234"), e, c["p1"]["id"])
    client.post(f"/eleicoes/{e}/encerrar", headers=chefe)
    res = client.get(f"/eleicoes/{e}/resultado", headers=auth(client, "ana", "1234"))  # Governador
    assert res.status_code == 200
    assert [x["cargo"] for x in res.json()["cargos"]] == ["GOVERNADOR"]


def test_candidato_de_fora_da_eleicao_nao_acompanha(client, chefe, cenario):
    e = cenario["eleicao"]["id"]
    e2 = client.post("/eleicoes", headers=chefe, json={"data": "2026-10-25", "turno": 2, "hora_abertura": "08:00", "hora_encerramento": "17:00"}).json()["id"]
    client.post("/candidatos", headers=chefe, json={"nome": "Eva Sen", "login": "eva", "senha": "1234", "numero": 77, "partido": "E", "cargo": "SENADOR", "eleicao_id": e2})
    abrir(client, chefe, e)
    assert client.get(f"/eleicoes/{e}/apuracao", headers=auth(client, "eva", "1234")).status_code == 403


def test_resultado_so_depois_de_encerrar_com_vencedor(client, chefe, cenario):
    e, c = cenario["eleicao"]["id"], cenario["cands"]
    abrir(client, chefe, e)
    e1, e2 = auth(client, "eleitor1", "1234"), auth(client, "eleitor2", "1234")
    votar(client, e1, e, c["g2"]["id"])
    votar(client, e2, e, c["g2"]["id"])
    assert client.get(f"/eleicoes/{e}/resultado", headers=e1).status_code == 409  # ainda ABERTA
    client.post(f"/eleicoes/{e}/encerrar", headers=chefe)
    res = client.get(f"/eleicoes/{e}/resultado", headers=e1).json()
    gov = next(x for x in res["cargos"] if x["cargo"] == "GOVERNADOR")
    assert gov["vencedor"]["nome"] == "Bia Gov" and gov["vencedor"]["votos"] == 2 and gov["empate"] is False
    pres = next(x for x in res["cargos"] if x["cargo"] == "PRESIDENTE")
    assert pres["vencedor"] is None  # ninguém votou


def test_empate_nao_declara_vencedor(client, chefe, cenario):
    e, c = cenario["eleicao"]["id"], cenario["cands"]
    abrir(client, chefe, e)
    votar(client, auth(client, "eleitor1", "1234"), e, c["g1"]["id"])
    votar(client, auth(client, "eleitor2", "1234"), e, c["g2"]["id"])
    client.post(f"/eleicoes/{e}/encerrar", headers=chefe)
    gov = next(x for x in client.get(f"/eleicoes/{e}/resultado", headers=chefe).json()["cargos"] if x["cargo"] == "GOVERNADOR")
    assert gov["empate"] is True and gov["vencedor"] is None
