"""Dependências do FastAPI: usuário autenticado e controle de acesso por perfil."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import Perfil
from app.exceptions import NaoAutenticado, Proibido
from app.models import Usuario
from app.security import ler_token

_bearer = HTTPBearer(auto_error=False, description="Cole o access_token retornado por POST /auth/login")


def usuario_atual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> Usuario:
    if cred is None:
        raise NaoAutenticado("Não autenticado. Faça login.")
    usuario = db.get(Usuario, ler_token(cred.credentials))
    if not usuario:
        raise NaoAutenticado("Usuário do token não existe mais.")
    return usuario


def exigir_perfil(*perfis: Perfil):
    """Gera uma dependência que só deixa passar os perfis informados (senão 403)."""

    def dependencia(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.perfil not in perfis:
            nomes = ", ".join(p.value for p in perfis)
            raise Proibido(f"Acesso negado: esta operação é restrita ao perfil {nomes}.")
        return usuario

    return dependencia


somente_chefe = exigir_perfil(Perfil.CHEFE)
somente_eleitor = exigir_perfil(Perfil.ELEITOR)
