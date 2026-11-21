from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import somente_chefe
from app.schemas import EleitorIn, EleitorOut, EleitorUpdate
from app.services import usuarios as svc

router = APIRouter(prefix="/eleitores", tags=["Eleitores (Chefe)"], dependencies=[Depends(somente_chefe)])


@router.post("", response_model=EleitorOut, status_code=201, summary="Cadastrar eleitor")
def criar(dados: EleitorIn, db: Session = Depends(get_db)):
    return svc.criar_eleitor(db, dados)


@router.get("", response_model=list[EleitorOut], summary="Consultar eleitores")
def listar(busca: str | None = Query(default=None, description="Filtra por nome"), db: Session = Depends(get_db)):
    return svc.listar_eleitores(db, busca)


@router.get("/{eleitor_id}", response_model=EleitorOut, summary="Consultar um eleitor")
def obter(eleitor_id: int, db: Session = Depends(get_db)):
    return svc.obter_eleitor(db, eleitor_id)


@router.put("/{eleitor_id}", response_model=EleitorOut, summary="Alterar dados do eleitor")
def atualizar(eleitor_id: int, dados: EleitorUpdate, db: Session = Depends(get_db)):
    return svc.atualizar_eleitor(db, eleitor_id, dados)


@router.delete("/{eleitor_id}", status_code=204, summary="Excluir eleitor")
def excluir(eleitor_id: int, db: Session = Depends(get_db)):
    svc.excluir_eleitor(db, eleitor_id)
    return Response(status_code=204)
