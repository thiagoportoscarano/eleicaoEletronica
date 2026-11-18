"""Configurações lidas de variáveis de ambiente (com padrões para desenvolvimento)."""
import os


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./eleicao.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-troque-em-producao-0123456789")
    token_expire_minutes: int = int(os.getenv("TOKEN_EXPIRE_MINUTES", "240"))
    pbkdf2_iterations: int = int(os.getenv("PBKDF2_ITERATIONS", "200000"))

    # Chefe da Seção criado automaticamente na primeira execução
    chefe_nome: str = os.getenv("CHEFE_NOME", "Chefe da Seção")
    chefe_login: str = os.getenv("CHEFE_LOGIN", "admin")
    chefe_senha: str = os.getenv("CHEFE_SENHA", "admin123")


settings = Settings()
