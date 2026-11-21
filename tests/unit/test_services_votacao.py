"""Testes unitários das regras de negócio, chamando os services direto (sem HTTP)."""
import pytest

from app.enums import Cargo, Perfil, Situacao
from app.exceptions import Conflito, DadoInvalido, NaoEncontrado
from app.models import Candidato, Eleicao, Usuario
from app.schemas import VotoIn
from app.services import apuracao, eleicoes, usuarios, votacao
from datetime import date, time


@pytest.fixture()
def base(db):
    e = Eleicao(data=date(2026, 10, 4), turno=1, hora_abertura=time(8), hora_encerramento=time(17), situacao=Situacao.ABERTA)
    db.add(e)
    u = usuarios.criar_usuario(db, "Ana", "ana", "1234", Perfil.CANDIDATO)
    eleitor = usuarios.criar_usuario(db, "Edu", "edu", "1234", Perfil.ELEITOR)
    db.flush()
    c = Candidato(usuario_id=u.id, eleicao_id=e.id, numero=11, partido="AAA", cargo=Cargo.GOVERNADOR)
    db.add(c)
    db.commit()
    return e, c, eleitor, u


def test_votar_com_eleicao_agendada_falha(db, base):
    e, c, eleitor, _ = base
    e.situacao = Situacao.AGENDADA
    db.commit()
    with pytest.raises(Conflito, match="não está aberta"):
        votacao.votar(db, e.id, eleitor, VotoIn(candidato_id=c.id, confirmado=True))


def test_votar_sem_confirmar_falha(db, base):
    e, c, eleitor, _ = base
    with pytest.raises(DadoInvalido):
        votacao.votar(db, e.id, eleitor, VotoIn(candidato_id=c.id, confirmado=False))


def test_votar_duas_vezes_no_mesmo_cargo_falha(db, base):
    e, c, eleitor, _ = base
    votacao.votar(db, e.id, eleitor, VotoIn(candidato_id=c.id, confirmado=True))
    with pytest.raises(Conflito, match="já votou"):
        votacao.votar(db, e.id, eleitor, VotoIn(candidato_id=c.id, confirmado=True))


def test_candidato_inexistente(db, base):
    e, _, eleitor, _ = base
    with pytest.raises(NaoEncontrado):
        votacao.votar(db, e.id, eleitor, VotoIn(candidato_id=999, confirmado=True))


def test_contagem_e_vencedor(db, base):
    e, c, eleitor, _ = base
    votacao.votar(db, e.id, eleitor, VotoIn(candidato_id=c.id, confirmado=True))
    e.situacao = Situacao.ENCERRADA
    db.commit()
    chefe = usuarios.criar_usuario(db, "Chefe", "chefe2", "1234", Perfil.CHEFE)
    res = apuracao.resultado(db, e.id, chefe)
    gov = res.cargos[0]
    assert gov.total_votos == 1 and gov.vencedor.candidato_id == c.id and not gov.empate


def test_nao_abre_eleicao_sem_candidatos(db):
    e = Eleicao(data=date(2026, 10, 4), turno=1, hora_abertura=time(8), hora_encerramento=time(17))
    db.add(e)
    db.commit()
    with pytest.raises(Conflito, match="sem candidatos"):
        eleicoes.abrir(db, e.id)


def test_login_duplicado(db):
    usuarios.criar_usuario(db, "A", "dup", "1234", Perfil.ELEITOR)
    with pytest.raises(Conflito):
        usuarios.criar_usuario(db, "B", "dup", "1234", Perfil.ELEITOR)
