from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import somente_eleitor
from app.models import Usuario
from app.schemas import CargoCandidatosOut, MeusVotosOut, VotoIn, VotoOut
from app.services import votacao as svc

router = APIRouter(prefix="/eleicoes/{eleicao_id}", tags=["Votação (Eleitor)"])


@router.get("/cargos", response_model=list[CargoCandidatosOut], summary="Candidatos disponíveis por cargo")
def cargos(eleicao_id: int, eleitor: Usuario = Depends(somente_eleitor), db: Session = Depends(get_db)):
    """Lista, para cada cargo, os candidatos e se o eleitor logado já votou naquele cargo."""
    return svc.candidatos_por_cargo(db, eleicao_id, eleitor)


@router.get("/meus-votos", response_model=MeusVotosOut, summary="Em quais cargos já votei")
def meus_votos(eleicao_id: int, eleitor: Usuario = Depends(somente_eleitor), db: Session = Depends(get_db)):
    """Só informa os cargos já votados — o sistema não guarda nem revela em quem o eleitor votou."""
    return svc.meus_votos(db, eleicao_id, eleitor)


@router.post("/votos", response_model=VotoOut, status_code=201, summary="Registrar e confirmar voto")
def votar(eleicao_id: int, dados: VotoIn, eleitor: Usuario = Depends(somente_eleitor), db: Session = Depends(get_db)):
    """Regras: eleição ABERTA; apenas eleitor; um voto por cargo; `confirmado` deve ser true; voto confirmado não pode ser alterado."""
    return svc.votar(db, eleicao_id, eleitor, dados)
