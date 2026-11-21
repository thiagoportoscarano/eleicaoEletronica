import jwt
import pytest
from pydantic import ValidationError

from app.config import settings
from app.exceptions import NaoAutenticado
from app.models import Voto
from app.schemas import CandidatoIn, EleicaoIn
from app.security import criar_token, hash_senha, ler_token, verificar_senha


def test_hash_nao_guarda_senha_em_texto_e_usa_sal():
    h1, h2 = hash_senha("segredo"), hash_senha("segredo")
    assert "segredo" not in h1
    assert h1 != h2  # sal diferente


def test_verificar_senha():
    h = hash_senha("segredo")
    assert verificar_senha("segredo", h)
    assert not verificar_senha("errada", h)
    assert not verificar_senha("segredo", "lixo")


def test_token_ida_e_volta():
    assert ler_token(criar_token(42, "ELEITOR")) == 42


def test_token_adulterado_ou_expirado_e_rejeitado():
    with pytest.raises(NaoAutenticado):
        ler_token("abc.def.ghi")
    expirado = jwt.encode({"sub": "1", "exp": 1}, settings.secret_key, algorithm="HS256")
    with pytest.raises(NaoAutenticado, match="expirada"):
        ler_token(expirado)
    outra_chave = jwt.encode({"sub": "1"}, "outra-chave-com-mais-de-32-bytes-ok", algorithm="HS256")
    with pytest.raises(NaoAutenticado):
        ler_token(outra_chave)


def test_token_sem_exp_ou_sem_sub_e_rejeitado():
    """ler_token exige as claims exp e sub (options={"require": ["exp", "sub"]})."""
    sem_exp = jwt.encode({"sub": "1"}, settings.secret_key, algorithm="HS256")
    with pytest.raises(NaoAutenticado):
        ler_token(sem_exp)
    sem_sub = jwt.encode({"exp": 9999999999}, settings.secret_key, algorithm="HS256")
    with pytest.raises(NaoAutenticado):
        ler_token(sem_sub)


def test_eleicao_exige_encerramento_depois_da_abertura():
    base = {"data": "2026-10-04", "turno": 1}
    EleicaoIn(**base, hora_abertura="08:00", hora_encerramento="17:00")
    with pytest.raises(ValidationError):
        EleicaoIn(**base, hora_abertura="17:00", hora_encerramento="08:00")


@pytest.mark.parametrize("turno", [0, 3])
def test_turno_so_1_ou_2(turno):
    with pytest.raises(ValidationError):
        EleicaoIn(data="2026-10-04", turno=turno, hora_abertura="08:00", hora_encerramento="17:00")


def test_cargo_invalido_e_rejeitado():
    with pytest.raises(ValidationError):
        CandidatoIn(nome="X Y", login="xyz", senha="1234", numero=1, partido="P", cargo="REI", eleicao_id=1)


def test_voto_e_anonimo_no_modelo():
    """Sigilo: a tabela de votos não pode ter coluna que identifique o eleitor nem horário."""
    colunas = {c.name for c in Voto.__table__.columns}
    assert colunas == {"id", "eleicao_id", "candidato_id", "cargo"}
