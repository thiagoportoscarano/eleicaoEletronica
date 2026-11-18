import enum


class Perfil(str, enum.Enum):
    CHEFE = "CHEFE"
    ELEITOR = "ELEITOR"
    CANDIDATO = "CANDIDATO"


class Situacao(str, enum.Enum):
    AGENDADA = "AGENDADA"
    ABERTA = "ABERTA"
    ENCERRADA = "ENCERRADA"


class Cargo(str, enum.Enum):
    DEPUTADO_ESTADUAL = "DEPUTADO_ESTADUAL"
    DEPUTADO_FEDERAL = "DEPUTADO_FEDERAL"
    SENADOR = "SENADOR"
    GOVERNADOR = "GOVERNADOR"
    PRESIDENTE = "PRESIDENTE"


CARGO_ROTULO = {
    Cargo.DEPUTADO_ESTADUAL: "Deputado Estadual",
    Cargo.DEPUTADO_FEDERAL: "Deputado Federal",
    Cargo.SENADOR: "Senador",
    Cargo.GOVERNADOR: "Governador",
    Cargo.PRESIDENTE: "Presidente da República",
}

# Ordem de exibição dos cargos
ORDEM_CARGOS = list(Cargo)
