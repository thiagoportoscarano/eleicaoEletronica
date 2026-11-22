"""Exceções de negócio. Os services lançam; o handler em main.py converte em resposta HTTP."""


class ErroNegocio(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NaoAutenticado(ErroNegocio):
    status_code = 401


class Proibido(ErroNegocio):
    status_code = 403


class NaoEncontrado(ErroNegocio):
    status_code = 404


class Conflito(ErroNegocio):
    status_code = 409


class DadoInvalido(ErroNegocio):
    status_code = 422
