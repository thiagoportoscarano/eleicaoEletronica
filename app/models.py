"""Modelagem do banco.

SIGILO DO VOTO: a tabela `votos` NÃO tem eleitor (nem horário) e usa UUID aleatório como chave.
O controle de "quem já votou" fica em `comparecimentos`, que só diz que o eleitor votou
naquele cargo, sem apontar o candidato. Não existe ligação entre as duas tabelas.
"""
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import Cargo, Perfil, Situacao


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    login: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(300))
    perfil: Mapped[Perfil] = mapped_column(Enum(Perfil, native_enum=False, length=20))


class Eleicao(Base):
    __tablename__ = "eleicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str | None] = mapped_column(String(150), nullable=True)
    data: Mapped[date] = mapped_column(Date)
    turno: Mapped[int] = mapped_column(Integer)
    hora_abertura: Mapped[time] = mapped_column(Time)
    hora_encerramento: Mapped[time] = mapped_column(Time)
    situacao: Mapped[Situacao] = mapped_column(Enum(Situacao, native_enum=False, length=20), default=Situacao.AGENDADA)


class Candidato(Base):
    """Candidatura de um usuário (perfil CANDIDATO) a um cargo em uma eleição."""

    __tablename__ = "candidatos"
    __table_args__ = (
        UniqueConstraint("eleicao_id", "cargo", "numero", name="uq_candidato_numero_no_cargo"),
        UniqueConstraint("eleicao_id", "usuario_id", name="uq_candidato_usuario_na_eleicao"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    eleicao_id: Mapped[int] = mapped_column(ForeignKey("eleicoes.id"))
    numero: Mapped[int] = mapped_column(Integer)
    partido: Mapped[str] = mapped_column(String(40))
    cargo: Mapped[Cargo] = mapped_column(Enum(Cargo, native_enum=False, length=30))

    usuario: Mapped[Usuario] = relationship(lazy="joined")

    @property
    def nome(self) -> str:
        return self.usuario.nome


class Comparecimento(Base):
    """Registra que o eleitor já votou em um cargo (impede voto duplicado). Não guarda em quem votou."""

    __tablename__ = "comparecimentos"
    __table_args__ = (UniqueConstraint("eleicao_id", "eleitor_id", "cargo", name="uq_um_voto_por_cargo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    eleicao_id: Mapped[int] = mapped_column(ForeignKey("eleicoes.id"))
    eleitor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    cargo: Mapped[Cargo] = mapped_column(Enum(Cargo, native_enum=False, length=30))
    registrado_em: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class Voto(Base):
    """Voto anônimo: apenas eleição, candidato e cargo."""

    __tablename__ = "votos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    eleicao_id: Mapped[int] = mapped_column(ForeignKey("eleicoes.id"), index=True)
    candidato_id: Mapped[int] = mapped_column(ForeignKey("candidatos.id"), index=True)
    cargo: Mapped[Cargo] = mapped_column(Enum(Cargo, native_enum=False, length=30))
