from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import somente_chefe, usuario_atual
from app.enums import Situacao
from app.schemas import EleicaoIn, EleicaoOut, EleicaoUpdate
from app.services import eleicoes as svc

router = APIRouter(prefix="/eleicoes", tags=["Eleições"])


@router.post("", response_model=EleicaoOut, status_code=201, dependencies=[Depends(somente_chefe)], summary="Cadastrar eleição (Chefe)")
def criar(dados: EleicaoIn, db: Session = Depends(get_db)):
    """Define data, turno e horários de abertura/encerramento. A eleição nasce AGENDADA."""
    return svc.criar(db, dados)


@router.get("", response_model=list[EleicaoOut], dependencies=[Depends(usuario_atual)], summary="Listar eleições")
def listar(situacao: Situacao | None = Query(default=None), db: Session = Depends(get_db)):
    return svc.listar(db, situacao)


@router.get("/atual", response_model=EleicaoOut, dependencies=[Depends(usuario_atual)], summary="Eleição em destaque")
def atual(db: Session = Depends(get_db)):
    """A eleição ABERTA; se não houver, a próxima AGENDADA; se não houver, a última ENCERRADA."""
    return svc.atual(db)


@router.get("/{eleicao_id}", response_model=EleicaoOut, dependencies=[Depends(usuario_atual)], summary="Consultar situação da eleição")
def obter(eleicao_id: int, db: Session = Depends(get_db)):
    return svc.obter(db, eleicao_id)


@router.put("/{eleicao_id}", response_model=EleicaoOut, dependencies=[Depends(somente_chefe)], summary="Alterar eleição agendada (Chefe)")
def atualizar(eleicao_id: int, dados: EleicaoUpdate, db: Session = Depends(get_db)):
    return svc.atualizar(db, eleicao_id, dados)


@router.post("/{eleicao_id}/abrir", response_model=EleicaoOut, dependencies=[Depends(somente_chefe)], summary="Abrir votação (Chefe)")
def abrir(eleicao_id: int, db: Session = Depends(get_db)):
    """AGENDADA → ABERTA. Exige ao menos um candidato cadastrado."""
    return svc.abrir(db, eleicao_id)


@router.post("/{eleicao_id}/encerrar", response_model=EleicaoOut, dependencies=[Depends(somente_chefe)], summary="Encerrar votação (Chefe)")
def encerrar(eleicao_id: int, db: Session = Depends(get_db)):
    """ABERTA → ENCERRADA. Depois disso nenhum voto novo é aceito."""
    return svc.encerrar(db, eleicao_id)
