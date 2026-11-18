"""Schemas Pydantic (entrada e saída da API). Aparecem na documentação Swagger."""
from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import Cargo, Perfil, Situacao


class Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Autenticação ----------
class LoginIn(BaseModel):
    login: str = Field(min_length=1, examples=["admin"])
    senha: str = Field(min_length=1, examples=["admin123"])


class UsuarioOut(Saida):
    id: int
    nome: str
    perfil: Perfil


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    perfil: Perfil
    usuario: UsuarioOut


# ---------- Eleição ----------
class EleicaoIn(BaseModel):
    titulo: str | None = Field(default=None, max_length=150, examples=["Eleição Geral 2026"])
    data: date
    turno: int = Field(ge=1, le=2, description="1º ou 2º turno")
    hora_abertura: time
    hora_encerramento: time

    @model_validator(mode="after")
    def _horarios(self):
        if self.hora_encerramento <= self.hora_abertura:
            raise ValueError("O horário de encerramento deve ser depois do horário de abertura.")
        return self


class EleicaoUpdate(BaseModel):
    titulo: str | None = Field(default=None, max_length=150)
    data: date | None = None
    turno: int | None = Field(default=None, ge=1, le=2)
    hora_abertura: time | None = None
    hora_encerramento: time | None = None


class EleicaoOut(Saida):
    id: int
    titulo: str | None
    data: date
    turno: int
    hora_abertura: time
    hora_encerramento: time
    situacao: Situacao


# ---------- Eleitor ----------
class EleitorIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    login: str = Field(min_length=3, max_length=60)
    senha: str = Field(min_length=4, max_length=100)


class EleitorUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    login: str | None = Field(default=None, min_length=3, max_length=60)
    senha: str | None = Field(default=None, min_length=4, max_length=100)


class EleitorOut(Saida):
    id: int
    nome: str
    login: str


# ---------- Candidato ----------
class CandidatoIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    login: str = Field(min_length=3, max_length=60)
    senha: str = Field(min_length=4, max_length=100)
    numero: int = Field(ge=1, le=99999, description="Número de identificação eleitoral")
    partido: str = Field(min_length=1, max_length=40)
    cargo: Cargo
    eleicao_id: int


class CandidatoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    login: str | None = Field(default=None, min_length=3, max_length=60)
    senha: str | None = Field(default=None, min_length=4, max_length=100)
    numero: int | None = Field(default=None, ge=1, le=99999)
    partido: str | None = Field(default=None, min_length=1, max_length=40)
    cargo: Cargo | None = None


class CandidatoOut(Saida):
    id: int
    usuario_id: int
    nome: str
    numero: int
    partido: str
    cargo: Cargo
    eleicao_id: int


# ---------- Votação ----------
class VotoIn(BaseModel):
    candidato_id: int
    confirmado: bool = Field(description="Precisa ser true: é a confirmação do voto (irreversível).")


class VotoOut(BaseModel):
    eleicao_id: int
    cargo: Cargo
    mensagem: str = "Voto registrado com sucesso."


class CargoCandidatosOut(BaseModel):
    cargo: Cargo
    rotulo: str
    ja_votou: bool
    candidatos: list[CandidatoOut]


class MeusVotosOut(BaseModel):
    """Só informa EM QUAIS CARGOS o eleitor já votou — nunca em quem."""

    cargos_votados: list[Cargo]
    cargos_pendentes: list[Cargo]


# ---------- Apuração / Resultado ----------
class CandidatoVotosOut(BaseModel):
    candidato_id: int
    nome: str
    numero: int
    partido: str
    votos: int


class CargoApuracaoOut(BaseModel):
    cargo: Cargo
    rotulo: str
    total_votos: int
    candidatos: list[CandidatoVotosOut]


class ApuracaoOut(BaseModel):
    eleicao_id: int
    situacao: Situacao
    cargos: list[CargoApuracaoOut]


class CargoResultadoOut(CargoApuracaoOut):
    vencedor: CandidatoVotosOut | None = Field(description="Candidato mais votado (null se não houve votos ou houve empate)")
    empate: bool = False


class ResultadoOut(BaseModel):
    eleicao_id: int
    situacao: Situacao
    cargos: list[CargoResultadoOut]
