"""Hash de senha (PBKDF2 da biblioteca padrão) e tokens JWT."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.exceptions import NaoAutenticado

ALGORITMO = "HS256"


def _pbkdf2(senha: str, sal: str, iteracoes: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), iteracoes).hex()


def hash_senha(senha: str) -> str:
    """Devolve `pbkdf2$<iteracoes>$<sal>$<hash_hex>` com sal aleatório."""
    sal = secrets.token_hex(16)
    it = settings.pbkdf2_iterations
    return f"pbkdf2${it}${sal}${_pbkdf2(senha, sal, it)}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    """Compara em tempo constante. Formato inválido devolve False em vez de lançar exceção."""
    try:
        esquema, it, sal, esperado = armazenado.split("$")
        if esquema != "pbkdf2":
            return False
        calculado = _pbkdf2(senha, sal, int(it))
    except (AttributeError, TypeError, ValueError):
        return False
    return hmac.compare_digest(calculado, esperado)


def criar_token(usuario_id: int, perfil: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.token_expire_minutes)
    dados = {"sub": str(usuario_id), "perfil": perfil, "exp": exp}
    return jwt.encode(dados, settings.secret_key, algorithm=ALGORITMO)


def ler_token(token: str) -> int:
    """Devolve o id do usuário ou lança NaoAutenticado se o token for inválido/expirado."""
    try:
        dados = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITMO],
            options={"require": ["exp", "sub"]},
        )
        return int(dados["sub"])
    except jwt.ExpiredSignatureError:
        raise NaoAutenticado("Sessão expirada. Faça login novamente.")
    except (jwt.PyJWTError, KeyError, ValueError):
        raise NaoAutenticado("Token inválido.")
