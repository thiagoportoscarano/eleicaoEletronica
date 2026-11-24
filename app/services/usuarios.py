"""Usuários: autenticação e CRUD de eleitores."""
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import Perfil
from app.exceptions import Conflito, NaoAutenticado, NaoEncontrado
from app.models import Comparecimento, Usuario
from app.schemas import EleitorIn, EleitorUpdate
from app.security import hash_senha, verificar_senha


def criar_usuario(db: Session, nome: str, login: str, senha: str, perfil: Perfil) -> Usuario:
    if db.scalar(select(Usuario).where(Usuario.login == login)):
        raise Conflito(f"O login '{login}' já está em uso.")
    u = Usuario(nome=nome, login=login, senha_hash=hash_senha(senha), perfil=perfil)
    db.add(u)
    db.flush()
    return u


def garantir_chefe(db: Session) -> None:
    """Cria o Chefe da Seção inicial se ainda não existir nenhum."""
    if not db.scalar(select(Usuario).where(Usuario.perfil == Perfil.CHEFE)):
        criar_usuario(db, settings.chefe_nome, settings.chefe_login, settings.chefe_senha, Perfil.CHEFE)
        db.commit()


_hash_ficticio: str | None = None


def _verificar_senha_ficticia(senha: str) -> None:
    """Roda o PBKDF2 mesmo quando o login não existe, para o tempo de resposta não revelar
    quais logins estão cadastrados."""
    global _hash_ficticio
    if _hash_ficticio is None:
        _hash_ficticio = hash_senha(secrets.token_hex(16))
    verificar_senha(senha, _hash_ficticio)


def autenticar(db: Session, login: str, senha: str) -> Usuario:
    u = db.scalar(select(Usuario).where(Usuario.login == login))
    if not u:
        _verificar_senha_ficticia(senha)
        raise NaoAutenticado("Login ou senha inválidos.")
    if not verificar_senha(senha, u.senha_hash):
        raise NaoAutenticado("Login ou senha inválidos.")
    return u


# ---------- Eleitores ----------
def _eleitor_ou_404(db: Session, eleitor_id: int) -> Usuario:
    u = db.get(Usuario, eleitor_id)
    if not u or u.perfil != Perfil.ELEITOR:
        raise NaoEncontrado("Eleitor não encontrado.")
    return u


def criar_eleitor(db: Session, dados: EleitorIn) -> Usuario:
    u = criar_usuario(db, dados.nome, dados.login, dados.senha, Perfil.ELEITOR)
    db.commit()
    return u


def listar_eleitores(db: Session, busca: str | None = None) -> list[Usuario]:
    q = select(Usuario).where(Usuario.perfil == Perfil.ELEITOR).order_by(Usuario.nome)
    if busca:
        q = q.where(Usuario.nome.ilike(f"%{busca}%"))
    return list(db.scalars(q))


def obter_eleitor(db: Session, eleitor_id: int) -> Usuario:
    return _eleitor_ou_404(db, eleitor_id)


def atualizar_eleitor(db: Session, eleitor_id: int, dados: EleitorUpdate) -> Usuario:
    u = _eleitor_ou_404(db, eleitor_id)
    if dados.login and dados.login != u.login:
        if db.scalar(select(Usuario).where(Usuario.login == dados.login)):
            raise Conflito(f"O login '{dados.login}' já está em uso.")
        u.login = dados.login
    if dados.nome:
        u.nome = dados.nome
    if dados.senha:
        u.senha_hash = hash_senha(dados.senha)
    db.commit()
    return u


def excluir_eleitor(db: Session, eleitor_id: int) -> None:
    """Eleitor que já votou não pode ser excluído: apagar o comparecimento deixaria a eleição com
    mais votos do que eleitores que votaram (o voto anônimo não pode ser localizado para sair junto)."""
    u = _eleitor_ou_404(db, eleitor_id)
    if db.scalar(select(Comparecimento.id).where(Comparecimento.eleitor_id == u.id).limit(1)):
        raise Conflito("Este eleitor já votou e não pode ser excluído: a contagem de votos ficaria inconsistente.")
    db.delete(u)
    db.commit()
