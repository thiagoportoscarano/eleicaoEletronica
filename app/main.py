from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import Base, SessionLocal, engine
from app.exceptions import ErroNegocio
from app.routers import apuracao, auth, candidatos, eleicoes, eleitores, votacao
from app.services.usuarios import garantir_chefe


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        garantir_chefe(db)
    yield


DESCRICAO = """
API do **Sistema de Simulação de Eleição Eletrônica**.

**Como usar:** faça `POST /auth/login`, copie o `access_token` e clique em **Authorize** (cadeado).

Perfis: **CHEFE** (administra a eleição, eleitores e candidatos), **ELEITOR** (vota e acompanha),
**CANDIDATO** (acompanha apenas o próprio cargo).

Sigilo do voto: o sistema controla *quem já votou* em cada cargo, mas nunca *em quem* votou.
"""

app = FastAPI(title="Eleição Eletrônica API", description=DESCRICAO, version="1.0.0", lifespan=lifespan)

# O app Ionic (navegador/WebView) chama esta API de outra origem.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ErroNegocio)
async def tratar_erro_negocio(_: Request, exc: ErroNegocio):
    cabecalhos = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=cabecalhos)


for r in (auth, eleicoes, eleitores, candidatos, votacao, apuracao):
    app.include_router(r.router)


@app.get("/saude", tags=["Infra"], summary="Verifica se a API está no ar")
def saude():
    return {"status": "ok"}
