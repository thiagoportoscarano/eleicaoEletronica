"""Gerenciamento da eleição: cadastro, abertura e encerramento."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import Situacao
from app.exceptions import Conflito, DadoInvalido, NaoEncontrado
from app.models import Candidato, Eleicao
from app.schemas import EleicaoIn, EleicaoUpdate


def obter(db: Session, eleicao_id: int) -> Eleicao:
    e = db.get(Eleicao, eleicao_id)
    if not e:
        raise NaoEncontrado("Eleição não encontrada.")
    return e


def criar(db: Session, dados: EleicaoIn) -> Eleicao:
    e = Eleicao(**dados.model_dump(), situacao=Situacao.AGENDADA)
    db.add(e)
    db.commit()
    return e


def listar(db: Session, situacao: Situacao | None = None) -> list[Eleicao]:
    q = select(Eleicao).order_by(Eleicao.data.desc(), Eleicao.turno.desc(), Eleicao.id.desc())
    if situacao:
        q = q.where(Eleicao.situacao == situacao)
    return list(db.scalars(q))


def atual(db: Session) -> Eleicao:
    """Eleição em destaque: a ABERTA; senão a próxima AGENDADA; senão a última ENCERRADA."""
    for sit, ordem in (
        (Situacao.ABERTA, Eleicao.id.desc()),
        (Situacao.AGENDADA, Eleicao.data.asc()),
        (Situacao.ENCERRADA, Eleicao.data.desc()),
    ):
        e = db.scalar(select(Eleicao).where(Eleicao.situacao == sit).order_by(ordem, Eleicao.id.desc()).limit(1))
        if e:
            return e
    raise NaoEncontrado("Nenhuma eleição cadastrada.")


def atualizar(db: Session, eleicao_id: int, dados: EleicaoUpdate) -> Eleicao:
    e = obter(db, eleicao_id)
    if e.situacao != Situacao.AGENDADA:
        raise Conflito("Só é possível alterar uma eleição que ainda está AGENDADA.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(e, campo, valor)
    if e.hora_encerramento <= e.hora_abertura:
        db.rollback()
        raise DadoInvalido("O horário de encerramento deve ser depois do horário de abertura.")
    db.commit()
    return e


def abrir(db: Session, eleicao_id: int) -> Eleicao:
    e = obter(db, eleicao_id)
    if e.situacao != Situacao.AGENDADA:
        raise Conflito(f"Só é possível abrir uma eleição AGENDADA (situação atual: {e.situacao.value}).")
    if not db.scalar(select(func.count(Candidato.id)).where(Candidato.eleicao_id == e.id)):
        raise Conflito("Não é possível abrir a eleição sem candidatos cadastrados.")
    e.situacao = Situacao.ABERTA
    db.commit()
    return e


def encerrar(db: Session, eleicao_id: int) -> Eleicao:
    e = obter(db, eleicao_id)
    if e.situacao != Situacao.ABERTA:
        raise Conflito(f"Só é possível encerrar uma eleição ABERTA (situação atual: {e.situacao.value}).")
    e.situacao = Situacao.ENCERRADA
    db.commit()
    return e
