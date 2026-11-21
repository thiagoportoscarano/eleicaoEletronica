# Tarefa: implementar `app/exceptions.py` e `app/security.py`

Os dois arquivos estão vazios de propósito. O resto do projeto já usa os nomes abaixo, então
**mantenha exatamente estes nomes e assinaturas**. Enquanto os dois não forem implementados,
a API não sobe e o `pytest` para no import do `conftest.py`.

Para conferir quando terminar: `pytest` deve mostrar **48 passed**.

---

## 1. `app/exceptions.py`

Erros de negócio. Os services lançam essas exceções e o handler em `app/main.py` transforma
cada uma em resposta HTTP `{"detail": ...}`, usando `exc.status_code` e `exc.detail`.

| Classe | Herda de | `status_code` | Usada para |
|---|---|---|---|
| `ErroNegocio` | `Exception` | 400 | base de todas |
| `NaoAutenticado` | `ErroNegocio` | 401 | login/token inválido ou expirado |
| `Proibido` | `ErroNegocio` | 403 | perfil sem permissão |
| `NaoEncontrado` | `ErroNegocio` | 404 | recurso inexistente |
| `Conflito` | `ErroNegocio` | 409 | eleição não aberta, voto duplicado, login/número repetido |
| `DadoInvalido` | `ErroNegocio` | 422 | dado que passou no schema mas viola regra |

Requisitos:
- `status_code` é **atributo de classe**.
- O construtor recebe uma mensagem: `ErroNegocio("texto")`. Guarde-a em `self.detail` e
  passe também para `super().__init__` (os testes usam `pytest.raises(..., match="...")`,
  que lê `str(exc)`).

Quem importa: `main.py`, `deps.py`, todos os arquivos de `app/services/` e os testes.

---

## 2. `app/security.py`

Hash de senha e tokens JWT. Use só a biblioteca padrão (`hashlib`, `hmac`, `secrets`) e o `PyJWT`
(`import jwt`), que já está no `requirements.txt`. Configurações em `app.config.settings`.

### `hash_senha(senha: str) -> str`
- PBKDF2-HMAC-SHA256 com **sal aleatório** (`secrets.token_hex(16)`) e
  `settings.pbkdf2_iterations` iterações.
- Formato armazenado: `pbkdf2$<iteracoes>$<sal>$<hash_hex>`.
- O mesmo texto deve gerar hashes diferentes, e a senha não pode aparecer no resultado.

### `verificar_senha(senha: str, armazenado: str) -> bool`
- Lê as iterações e o sal do valor armazenado, recalcula o hash e compara com
  **`hmac.compare_digest`** (comparação em tempo constante).
- Se `armazenado` estiver em formato inválido, devolve `False` (não pode lançar exceção).

### `criar_token(usuario_id: int, perfil: str) -> str`
- JWT **HS256**, assinado com `settings.secret_key`.
- Claims: `sub` = `str(usuario_id)`, `perfil`, `exp` = agora (UTC) + `settings.token_expire_minutes`.

### `ler_token(token: str) -> int`
- Devolve `int(sub)`.
- Chame o `jwt.decode` com `algorithms=["HS256"]` (fixo, não aceite o algoritmo que vem no token) e
  **`options={"require": ["exp", "sub"]}`**, para que tokens sem expiração ou sem usuário sejam recusados.
- Token expirado (`jwt.ExpiredSignatureError`): lançar `NaoAutenticado` com mensagem contendo
  **"expirada"** (ex.: `"Sessão expirada. Faça login novamente."`). Os testes conferem essa palavra.
- Qualquer outro problema (`jwt.PyJWTError`, `KeyError`, `ValueError`): `NaoAutenticado("Token inválido.")`.

Quem importa: `deps.py` (`ler_token`), `routers/auth.py` (`criar_token`),
`services/usuarios.py` (`hash_senha`, `verificar_senha`), `services/candidatos.py` (`hash_senha`).

---

## 3. Melhoria sugerida (opcional, em `services/usuarios.py`)

`autenticar()` já devolve a mesma mensagem para login inexistente e para senha errada. Mas, quando o
login não existe, o PBKDF2 nem é executado, então a resposta volta bem mais rápido. Medindo esse
tempo, dá para descobrir quais logins existem. Para corrigir, quando o usuário não existir, chame
`verificar_senha` contra um hash fictício (gerado uma vez com `hash_senha`) antes de lançar o erro.

## Testes que cobrem esta tarefa

- `tests/unit/test_seguranca_e_schemas.py`: hash, verificação, ida e volta do token, token
  adulterado/expirado, token sem `exp`/`sub`.
- `tests/integration/test_api.py`: login inválido → 401, token adulterado/expirado → 401 pela API,
  perfis → 403.
