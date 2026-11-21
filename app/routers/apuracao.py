from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas import ApuracaoOut, ResultadoOut
from app.services import apuracao as svc

router = APIRouter(prefix="/eleicoes/{eleicao_id}", tags=["Apuração e Resultado"])


@router.get("/apuracao", response_model=ApuracaoOut, summary="Acompanhar a votação (parcial)")
def apuracao(eleicao_id: int, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    """Votos por candidato, atualizados a cada voto. Eleitor e Chefe veem todos os cargos; Candidato só o seu. Indisponível enquanto AGENDADA."""
    return svc.apuracao(db, eleicao_id, usuario)


@router.get("/resultado", response_model=ResultadoOut, summary="Resultado final")
def resultado(eleicao_id: int, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    """Disponível só após o encerramento. Traz votos por candidato e o mais votado de cada cargo (Candidato vê apenas o seu cargo)."""
    return svc.resultado(db, eleicao_id, usuario)
