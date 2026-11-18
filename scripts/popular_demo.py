"""Popula o banco com dados de demonstração (rode da raiz do projeto).

    python -m scripts.popular_demo

Cria 1 eleição AGENDADA (1º turno), candidatos a Governador e Presidente
e 5 eleitores (senha 1234). Depois é só abrir a eleição pelo app como Chefe da Seção.
"""
from datetime import date, time

from app.database import Base, SessionLocal, engine
from app.enums import Cargo
from app.schemas import CandidatoIn, EleicaoIn, EleitorIn
from app.services import candidatos, eleicoes, usuarios


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        usuarios.garantir_chefe(db)
        e = eleicoes.criar(db, EleicaoIn(titulo="Eleição Demo", data=date.today(), turno=1, hora_abertura=time(8), hora_encerramento=time(17)))
        for nome, login, num, partido, cargo in [
            ("Ana Souza", "ana", 11, "PAZ", Cargo.GOVERNADOR),
            ("Bruno Lima", "bruno", 22, "VIDA", Cargo.GOVERNADOR),
            ("Carla Dias", "carla", 33, "PAZ", Cargo.PRESIDENTE),
            ("Diego Melo", "diego", 44, "FUTURO", Cargo.PRESIDENTE),
        ]:
            candidatos.criar(db, CandidatoIn(nome=nome, login=login, senha="1234", numero=num, partido=partido, cargo=cargo, eleicao_id=e.id))
        for i in range(1, 6):
            usuarios.criar_eleitor(db, EleitorIn(nome=f"Eleitor {i}", login=f"eleitor{i}", senha="1234"))
    print("Pronto. Chefe: admin/admin123 | Candidatos: ana, bruno, carla, diego | Eleitores: eleitor1..eleitor5 (senha 1234)")


if __name__ == "__main__":
    main()
