from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas import LoginIn, TokenOut, UsuarioOut
from app.security import criar_token
from app.services import usuarios

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenOut, summary="Login de qualquer perfil")
def login(dados: LoginIn, db: Session = Depends(get_db)):
    """Autentica Chefe da Seção, Eleitor ou Candidato. Retorna o JWT e o perfil, que define o que o usuário pode fazer."""
    u = usuarios.autenticar(db, dados.login, dados.senha)
    return TokenOut(access_token=criar_token(u.id, u.perfil.value), perfil=u.perfil, usuario=UsuarioOut.model_validate(u))


@router.get("/me", response_model=UsuarioOut, summary="Dados do usuário autenticado")
def me(usuario: Usuario = Depends(usuario_atual)):
    return usuario
