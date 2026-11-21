# Eleição Eletrônica — Back-End (FastAPI)

API do Sistema de Simulação de Eleição Eletrônica. Python 3.11+, FastAPI, SQLAlchemy 2, SQLite, JWT.

## Executar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m scripts.popular_demo      # dados de demonstração, caso deseje
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger UI: http://localhost:8000/docs  (ReDoc em `/redoc`)
- Chefe da Seção criado automaticamente: **admin / admin123** (mude com `CHEFE_LOGIN`, `CHEFE_SENHA`).
- Para o app no celular, rode com `--host 0.0.0.0` e use o IP do computador (ex.: `http://192.168.0.10:8000`); libere a porta 8000 no firewall.
- Em Swagger: faça `POST /auth/login`, copie `access_token`, clique em **Authorize**.

Variáveis de ambiente: `DATABASE_URL` (padrão `sqlite:///./eleicao.db`), `SECRET_KEY`, `TOKEN_EXPIRE_MINUTES`.

## Testes

```bash
pytest           # 48 testes: unitários (tests/unit) e de integração (tests/integration)
```

> `app/security.py` e `app/exceptions.py` estão em implementação (veja [docs/TAREFA_security_exceptions.md](docs/TAREFA_security_exceptions.md)). Enquanto estiverem vazios, a API não sobe e o pytest falha no import.

## Estrutura modular

```
app/
├── main.py        app, CORS, tratamento de erros, routers
├── config.py      configuração por variáveis de ambiente
├── database.py    engine/sessão SQLAlchemy
├── models.py      tabelas: usuarios, eleicoes, candidatos, comparecimentos, votos
├── schemas.py     contratos de entrada/saída (Pydantic → Swagger)
├── security.py    hash PBKDF2 e JWT
├── deps.py        usuário autenticado + controle por perfil (403)
├── exceptions.py  erros de negócio (401/403/404/409/422)
├── routers/       camada HTTP (auth, eleicoes, eleitores, candidatos, votacao, apuracao)
└── services/      regras de negócio (sem HTTP): usuarios, eleicoes, candidatos, votacao, apuracao
tests/ unit/ + integration/      scripts/popular_demo.py
```

## Endpoints por perfil

| Perfil | Pode |
|---|---|
| público | `POST /auth/login` |
| qualquer logado | `GET /auth/me`, `GET /eleicoes`, `/eleicoes/atual`, `/eleicoes/{id}`, `GET /candidatos` |
| **CHEFE** | `POST/PUT /eleicoes`, `POST /eleicoes/{id}/abrir`, `/encerrar`; CRUD `/eleitores`; `POST/PUT/DELETE /candidatos`; apuração/resultado de todos os cargos |
| **ELEITOR** | `GET /eleicoes/{id}/cargos`, `GET /eleicoes/{id}/meus-votos`, `POST /eleicoes/{id}/votos`; apuração/resultado de todos os cargos |
| **CANDIDATO** | `GET /eleicoes/{id}/apuracao` e `/resultado` **só do próprio cargo** |

Apuração: `GET /eleicoes/{id}/apuracao` (parcial, em tempo real; 409 se AGENDADA). Resultado final: `GET /eleicoes/{id}/resultado` (409 até encerrar; traz o mais votado de cada cargo, `empate: true` quando há empate no topo).

## Regras de negócio implementadas

- Eleição: `AGENDADA → ABERTA → ENCERRADA`, só o Chefe muda; turno 1 ou 2; encerramento depois da abertura; não abre sem candidatos.
- Voto só com eleição **ABERTA**, só **ELEITOR**, **um por cargo** (restrição UNIQUE no banco), exige `confirmado: true` e não pode ser alterado (não existe rota de edição/exclusão de voto).
- Candidatos só são criados/alterados/excluídos enquanto a eleição está AGENDADA; número único por cargo+eleição.
- Chefe cadastra eleitores e candidatos (candidato = usuário com cargo, partido, número e eleição).

## Sigilo do voto

`comparecimentos` guarda *que* o eleitor votou no cargo X (barra duplicidade); `votos` guarda eleição + candidato + cargo, com **UUID aleatório e sem eleitor nem horário**. Nenhuma tabela liga eleitor a candidato e nenhum endpoint revela em quem alguém votou (`meus-votos` só lista cargos).

A tabela `votos` é criada como **`WITHOUT ROWID`** no SQLite. Numa tabela comum, o `rowid` crescente guarda a ordem de inserção, e cruzar essa ordem com a de `comparecimentos` revelaria em quem cada eleitor votou. Sem rowid, os votos ficam ordenados só pelo UUID aleatório. Um banco `eleicao.db` criado antes dessa mudança precisa ser apagado e recriado, porque o `create_all` não altera tabelas que já existem.

Testes que garantem o sigilo e o controle de acesso (48 no total): colunas de `votos` e `comparecimentos`, `votos` como WITHOUT ROWID (consulta ao `sqlite_master`), token adulterado/expirado → 401, ELEITOR e CANDIDATO fora das rotas do Chefe e da votação → 403, CANDIDATO só vê o próprio cargo na apuração e no resultado.

## Erros

Formato `{"detail": "mensagem"}`: 401 credencial/token inválido, 403 perfil sem permissão, 404 não encontrado, 409 conflito (eleição não aberta, voto duplicado, login/número repetido), 422 dados inválidos.

