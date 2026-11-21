"""Regras de votação."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.enums import CARGO_ROTULO, ORDEM_CARGOS, Cargo, Situacao
from app.exceptions import Conflito, DadoInvalido, NaoEncontrado
from app.models import Candidato, Comparecimento, Eleicao, Usuario, Voto
from app.schemas import CargoCandidatosOut, MeusVotosOut, VotoIn, VotoOut
from app.services import eleicoes as eleicao_svc


def _cargos_votados(db: Session, eleicao_id: int, eleitor_id: int) -> set[Cargo]:
    return set(db.scalars(select(Comparecimento.cargo).where(Comparecimento.eleicao_id == eleicao_id, Comparecimento.eleitor_id == eleitor_id)))


def candidatos_por_cargo(db: Session, eleicao_id: int, eleitor: Usuario) -> list[CargoCandidatosOut]:
    eleicao_svc.obter(db, eleicao_id)
    votados = _cargos_votados(db, eleicao_id, eleitor.id)
    candidatos = list(db.scalars(select(Candidato).where(Candidato.eleicao_id == eleicao_id).order_by(Candidato.numero)))
    saida = []
    for cargo in ORDEM_CARGOS:
        do_cargo = [c for c in candidatos if c.cargo == cargo]
        if do_cargo:
            saida.append(CargoCandidatosOut(cargo=cargo, rotulo=CARGO_ROTULO[cargo], ja_votou=cargo in votados, candidatos=do_cargo))
    return saida


def meus_votos(db: Session, eleicao_id: int, eleitor: Usuario) -> MeusVotosOut:
    eleicao_svc.obter(db, eleicao_id)
    votados = _cargos_votados(db, eleicao_id, eleitor.id)
    cargos = {c for c in db.scalars(select(Candidato.cargo).where(Candidato.eleicao_id == eleicao_id))}
    return MeusVotosOut(
        cargos_votados=[c for c in ORDEM_CARGOS if c in votados],
        cargos_pendentes=[c for c in ORDEM_CARGOS if c in cargos and c not in votados],
    )


def votar(db: Session, eleicao_id: int, eleitor: Usuario, dados: VotoIn) -> VotoOut:
    eleicao: Eleicao = eleicao_svc.obter(db, eleicao_id)

    if eleicao.situacao != Situacao.ABERTA:
        raise Conflito(f"A eleição não está aberta (situação: {eleicao.situacao.value}). Não é possível votar.")
    if not dados.confirmado:
        raise DadoInvalido("O voto precisa ser confirmado (confirmado=true). Depois de confirmado ele não pode ser alterado.")

    candidato = db.get(Candidato, dados.candidato_id)
    if not candidato or candidato.eleicao_id != eleicao_id:
        raise NaoEncontrado("Candidato não encontrado nesta eleição.")

    # Controle de voto duplicado (sem registrar em quem votou) + voto anônimo, na MESMA transação.
    try:
        db.add(Comparecimento(eleicao_id=eleicao_id, eleitor_id=eleitor.id, cargo=candidato.cargo))
        db.flush()
        db.add(Voto(eleicao_id=eleicao_id, candidato_id=candidato.id, cargo=candidato.cargo))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflito(f"Você já votou para o cargo de {CARGO_ROTULO[candidato.cargo]} nesta eleição. Não é possível votar novamente.")

    return VotoOut(eleicao_id=eleicao_id, cargo=candidato.cargo)
