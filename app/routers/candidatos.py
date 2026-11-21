from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import somente_chefe, usuario_atual
from app.enums import Cargo
from app.schemas import CandidatoIn, CandidatoOut, CandidatoUpdate
from app.services import candidatos as svc

router = APIRouter(prefix="/candidatos", tags=["Candidatos"])


@router.post("", response_model=CandidatoOut, status_code=201, dependencies=[Depends(somente_chefe)], summary="Cadastrar candidato (Chefe)")
def criar(dados: CandidatoIn, db: Session = Depends(get_db)):
    """Cria o usuário (perfil CANDIDATO) e o associa a um cargo e a uma eleição AGENDADA."""
    return svc.criar(db, dados)


@router.get("", response_model=list[CandidatoOut], dependencies=[Depends(usuario_atual)], summary="Consultar candidatos")
def listar(eleicao_id: int | None = Query(default=None), cargo: Cargo | None = Query(default=None), db: Session = Depends(get_db)):
    return svc.listar(db, eleicao_id, cargo)


@router.get("/{candidato_id}", response_model=CandidatoOut, dependencies=[Depends(usuario_atual)], summary="Consultar um candidato")
def obter(candidato_id: int, db: Session = Depends(get_db)):
    return svc.obter(db, candidato_id)


@router.put("/{candidato_id}", response_model=CandidatoOut, dependencies=[Depends(somente_chefe)], summary="Alterar candidato (Chefe)")
def atualizar(candidato_id: int, dados: CandidatoUpdate, db: Session = Depends(get_db)):
    return svc.atualizar(db, candidato_id, dados)


@router.delete("/{candidato_id}", status_code=204, dependencies=[Depends(somente_chefe)], summary="Excluir candidato (Chefe)")
def excluir(candidato_id: int, db: Session = Depends(get_db)):
    svc.excluir(db, candidato_id)
    return Response(status_code=204)
