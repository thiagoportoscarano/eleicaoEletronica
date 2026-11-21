"""CRUD de candidatos. Cada candidato é um usuário (perfil CANDIDATO) associado a cargo + eleição."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.enums import Cargo, Perfil, Situacao
from app.exceptions import Conflito, NaoEncontrado
from app.models import Candidato, Usuario
from app.schemas import CandidatoIn, CandidatoUpdate
from app.security import hash_senha
from app.services import eleicoes as eleicao_svc
from app.services.usuarios import criar_usuario


def obter(db: Session, candidato_id: int) -> Candidato:
    c = db.get(Candidato, candidato_id)
    if not c:
        raise NaoEncontrado("Candidato não encontrado.")
    return c


def _exigir_eleicao_agendada(db: Session, eleicao_id: int) -> None:
    e = eleicao_svc.obter(db, eleicao_id)
    if e.situacao != Situacao.AGENDADA:
        raise Conflito("Candidatos só podem ser cadastrados, alterados ou excluídos enquanto a eleição está AGENDADA.")


def criar(db: Session, dados: CandidatoIn) -> Candidato:
    _exigir_eleicao_agendada(db, dados.eleicao_id)
    try:
        usuario = criar_usuario(db, dados.nome, dados.login, dados.senha, Perfil.CANDIDATO)
        c = Candidato(usuario_id=usuario.id, eleicao_id=dados.eleicao_id, numero=dados.numero, partido=dados.partido, cargo=dados.cargo)
        db.add(c)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflito(f"Já existe um candidato com o número {dados.numero} para este cargo nesta eleição.")
    except Conflito:
        db.rollback()
        raise
    return c


def listar(db: Session, eleicao_id: int | None = None, cargo: Cargo | None = None) -> list[Candidato]:
    q = select(Candidato).order_by(Candidato.cargo, Candidato.numero)
    if eleicao_id is not None:
        q = q.where(Candidato.eleicao_id == eleicao_id)
    if cargo is not None:
        q = q.where(Candidato.cargo == cargo)
    return list(db.scalars(q))


def atualizar(db: Session, candidato_id: int, dados: CandidatoUpdate) -> Candidato:
    c = obter(db, candidato_id)
    _exigir_eleicao_agendada(db, c.eleicao_id)
    u = c.usuario
    if dados.login and dados.login != u.login:
        if db.scalar(select(Usuario).where(Usuario.login == dados.login)):
            raise Conflito(f"O login '{dados.login}' já está em uso.")
        u.login = dados.login
    if dados.nome:
        u.nome = dados.nome
    if dados.senha:
        u.senha_hash = hash_senha(dados.senha)
    if dados.numero is not None:
        c.numero = dados.numero
    if dados.partido:
        c.partido = dados.partido
    if dados.cargo:
        c.cargo = dados.cargo
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflito("Já existe um candidato com esse número para este cargo nesta eleição.")
    return c


def excluir(db: Session, candidato_id: int) -> None:
    c = obter(db, candidato_id)
    _exigir_eleicao_agendada(db, c.eleicao_id)
    usuario = c.usuario
    db.delete(c)
    db.flush()
    if not db.scalar(select(Candidato.id).where(Candidato.usuario_id == usuario.id).limit(1)):
        db.delete(usuario)
    db.commit()
