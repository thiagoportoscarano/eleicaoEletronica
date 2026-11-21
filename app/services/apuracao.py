"""Acompanhamento da votação e resultado final."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import CARGO_ROTULO, ORDEM_CARGOS, Cargo, Perfil, Situacao
from app.exceptions import Conflito, Proibido
from app.models import Candidato, Usuario, Voto
from app.schemas import ApuracaoOut, CandidatoVotosOut, CargoApuracaoOut, CargoResultadoOut, ResultadoOut
from app.services import eleicoes as eleicao_svc


def cargo_do_candidato(db: Session, usuario: Usuario, eleicao_id: int) -> Cargo:
    c = db.scalar(select(Candidato).where(Candidato.eleicao_id == eleicao_id, Candidato.usuario_id == usuario.id))
    if not c:
        raise Proibido("Você não é candidato nesta eleição.")
    return c.cargo


def _cargo_permitido(db: Session, usuario: Usuario, eleicao_id: int) -> Cargo | None:
    """Candidato só enxerga o próprio cargo; os demais perfis veem todos (None = sem restrição)."""
    if usuario.perfil == Perfil.CANDIDATO:
        return cargo_do_candidato(db, usuario, eleicao_id)
    return None


def _contar(db: Session, eleicao_id: int, restringir: Cargo | None) -> list[CargoApuracaoOut]:
    contagem = dict(db.execute(select(Voto.candidato_id, func.count(Voto.id)).where(Voto.eleicao_id == eleicao_id).group_by(Voto.candidato_id)).all())
    candidatos = list(db.scalars(select(Candidato).where(Candidato.eleicao_id == eleicao_id)))
    cargos = []
    for cargo in ORDEM_CARGOS:
        if restringir and cargo != restringir:
            continue
        linhas = [
            CandidatoVotosOut(candidato_id=c.id, nome=c.nome, numero=c.numero, partido=c.partido, votos=contagem.get(c.id, 0))
            for c in candidatos
            if c.cargo == cargo
        ]
        if not linhas:
            continue
        linhas.sort(key=lambda x: (-x.votos, x.numero))
        cargos.append(CargoApuracaoOut(cargo=cargo, rotulo=CARGO_ROTULO[cargo], total_votos=sum(l.votos for l in linhas), candidatos=linhas))
    return cargos


def apuracao(db: Session, eleicao_id: int, usuario: Usuario) -> ApuracaoOut:
    eleicao = eleicao_svc.obter(db, eleicao_id)
    restricao = _cargo_permitido(db, usuario, eleicao_id)
    if eleicao.situacao == Situacao.AGENDADA:
        raise Conflito("A eleição ainda não foi aberta: não há votação para acompanhar.")
    return ApuracaoOut(eleicao_id=eleicao.id, situacao=eleicao.situacao, cargos=_contar(db, eleicao_id, restricao))


def resultado(db: Session, eleicao_id: int, usuario: Usuario) -> ResultadoOut:
    eleicao = eleicao_svc.obter(db, eleicao_id)
    restricao = _cargo_permitido(db, usuario, eleicao_id)
    if eleicao.situacao != Situacao.ENCERRADA:
        raise Conflito("O resultado final só fica disponível depois que a eleição for encerrada.")
    cargos = []
    for c in _contar(db, eleicao_id, restricao):
        topo = c.candidatos[0].votos if c.candidatos else 0
        lideres = [x for x in c.candidatos if x.votos == topo]
        empate = topo > 0 and len(lideres) > 1
        vencedor = lideres[0] if topo > 0 and not empate else None
        cargos.append(CargoResultadoOut(**c.model_dump(), vencedor=vencedor, empate=empate))
    return ResultadoOut(eleicao_id=eleicao.id, situacao=eleicao.situacao, cargos=cargos)
