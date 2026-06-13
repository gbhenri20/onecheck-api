"""
Fase 2.1 — Testes de integração das rotas de autenticação

Rotas cobertas:
  POST /auth/login
  POST /auth/mfa/verify
  POST /auth/refresh
  POST /auth/logout
"""
import pytest

from app.auth import create_refresh_token, create_temp_token
from app.models import Usuario
from tests.conftest import MFA_TEST_SECRET, TEST_SENHA, _SENHA_HASH, auth, totp_now


# ── POST /auth/login ──────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_sem_mfa_retorna_tokens(self, client, user_locatario):
        r = client.post("/api/v1/auth/login", json={
            "email": user_locatario.email,
            "senha": TEST_SENHA,
        })
        data = r.json()
        assert data["sucesso"] is True
        assert "access_token" in data["dados"]
        assert "refresh_token" in data["dados"]
        assert data["dados"]["usuario"]["email"] == user_locatario.email

    def test_login_com_mfa_retorna_temp_token(self, client, user_admin):
        r = client.post("/api/v1/auth/login", json={
            "email": user_admin.email,
            "senha": TEST_SENHA,
        })
        data = r.json()
        assert data["sucesso"] is True
        assert data["dados"]["mfa_required"] is True
        assert "temp_token" in data["dados"]

    def test_login_email_invalido(self, client):
        r = client.post("/api/v1/auth/login", json={
            "email": "naoexiste@test.com",
            "senha": TEST_SENHA,
        })
        data = r.json()
        assert data["sucesso"] is False
        assert "inválidas" in data["erro"].lower()

    def test_login_senha_incorreta(self, client, user_locatario):
        r = client.post("/api/v1/auth/login", json={
            "email": user_locatario.email,
            "senha": "senhaerrada",
        })
        data = r.json()
        assert data["sucesso"] is False

    def test_login_usuario_inativo(self, client, db):
        u = Usuario(
            nome="Inativo",
            email="inativo@test.com",
            senha_hash=_SENHA_HASH,
            role="locatario",
            mfa_enabled=False,
            ativo=False,
        )
        db.add(u)
        db.flush()

        r = client.post("/api/v1/auth/login", json={
            "email": "inativo@test.com",
            "senha": TEST_SENHA,
        })
        data = r.json()
        assert data["sucesso"] is False

    def test_login_resposta_http_200_mesmo_em_falha(self, client):
        # A API usa padrão de envelope JSON — sempre retorna 200
        r = client.post("/api/v1/auth/login", json={
            "email": "x@x.com",
            "senha": "errado",
        })
        assert r.status_code == 200

    def test_login_role_gestor_com_mfa(self, client, user_gestor):
        r = client.post("/api/v1/auth/login", json={
            "email": user_gestor.email,
            "senha": TEST_SENHA,
        })
        data = r.json()
        assert data["sucesso"] is True
        assert data["dados"]["mfa_required"] is True

    def test_login_visualizador_sem_mfa(self, client, user_visualizador):
        r = client.post("/api/v1/auth/login", json={
            "email": user_visualizador.email,
            "senha": TEST_SENHA,
        })
        data = r.json()
        assert data["sucesso"] is True
        assert "access_token" in data["dados"]


# ── POST /auth/mfa/verify ─────────────────────────────────────────────────────────

class TestMfaVerify:
    def test_mfa_verify_valido_retorna_tokens(self, client, user_admin):
        temp_token = create_temp_token(user_admin.id)
        r = client.post("/api/v1/auth/mfa/verify", json={
            "temp_token": temp_token,
            "codigo": totp_now(),
        })
        data = r.json()
        assert data["sucesso"] is True
        assert "access_token" in data["dados"]
        assert "refresh_token" in data["dados"]

    def test_mfa_verify_token_invalido(self, client):
        r = client.post("/api/v1/auth/mfa/verify", json={
            "temp_token": "token.invalido.qualquer",
            "codigo": "123456",
        })
        data = r.json()
        assert data["sucesso"] is False
        assert "inválido" in data["erro"].lower()

    def test_mfa_verify_token_tipo_errado(self, client, user_admin):
        # Envia um access token no lugar do temp_token MFA
        access_token = create_temp_token.__module__  # não é um access token
        from app.auth import create_access_token
        wrong_token = create_access_token(user_admin.id, user_admin.role)
        r = client.post("/api/v1/auth/mfa/verify", json={
            "temp_token": wrong_token,
            "codigo": totp_now(),
        })
        data = r.json()
        assert data["sucesso"] is False

    def test_mfa_verify_codigo_incorreto(self, client, user_admin):
        temp_token = create_temp_token(user_admin.id)
        r = client.post("/api/v1/auth/mfa/verify", json={
            "temp_token": temp_token,
            "codigo": "000000",
        })
        data = r.json()
        # 000000 pode acidentalmente ser o código válido; nesse caso o teste é skip
        if totp_now() == "000000":
            pytest.skip("000000 é o código TOTP atual — skip para evitar falso negativo")
        assert data["sucesso"] is False

    def test_mfa_verify_usuario_inexistente_no_token(self, client):
        temp_token = create_temp_token("id-que-nao-existe")
        r = client.post("/api/v1/auth/mfa/verify", json={
            "temp_token": temp_token,
            "codigo": totp_now(),
        })
        data = r.json()
        assert data["sucesso"] is False
        assert "encontrado" in data["erro"].lower()

    def test_mfa_verify_retorna_dados_do_usuario(self, client, user_admin):
        temp_token = create_temp_token(user_admin.id)
        r = client.post("/api/v1/auth/mfa/verify", json={
            "temp_token": temp_token,
            "codigo": totp_now(),
        })
        data = r.json()
        assert data["sucesso"] is True
        assert data["dados"]["usuario"]["id"] == user_admin.id
        assert data["dados"]["usuario"]["role"] == "admin"


# ── POST /auth/refresh ────────────────────────────────────────────────────────────

class TestRefresh:
    def test_refresh_valido_retorna_novos_tokens(self, client, db, user_locatario):
        raw_token = create_refresh_token(db, user_locatario.id)
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})
        data = r.json()
        assert data["sucesso"] is True
        assert "access_token" in data["dados"]
        assert "refresh_token" in data["dados"]

    def test_refresh_novo_token_diferente_do_antigo(self, client, db, user_locatario):
        raw_token = create_refresh_token(db, user_locatario.id)
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})
        data = r.json()
        assert data["dados"]["refresh_token"] != raw_token

    def test_refresh_token_invalido(self, client):
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": "token-invalido"})
        data = r.json()
        assert data["sucesso"] is False
        assert "inválido" in data["erro"].lower()

    def test_refresh_token_revogado_apos_uso(self, client, db, user_locatario):
        raw_token = create_refresh_token(db, user_locatario.id)
        # Primeiro uso
        client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})
        # Segundo uso com o mesmo token (deve falhar pois foi revogado)
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})
        data = r.json()
        assert data["sucesso"] is False


# ── POST /auth/logout ─────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_com_refresh_token(self, client, db, user_locatario, token_locatario):
        raw_token = create_refresh_token(db, user_locatario.id)
        r = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": raw_token},
            headers=auth(token_locatario),
        )
        data = r.json()
        assert data["sucesso"] is True

    def test_logout_sem_refresh_token(self, client, token_locatario):
        r = client.post("/api/v1/auth/logout", headers=auth(token_locatario))
        data = r.json()
        assert data["sucesso"] is True

    def test_logout_sem_autenticacao_retorna_401(self, client):
        r = client.post("/api/v1/auth/logout")
        assert r.status_code == 401

    def test_logout_revoga_refresh_token(self, client, db, user_locatario, token_locatario):
        raw_token = create_refresh_token(db, user_locatario.id)
        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": raw_token},
            headers=auth(token_locatario),
        )
        # Após logout, o refresh token não deve mais funcionar
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})
        data = r.json()
        assert data["sucesso"] is False

    def test_logout_token_invalido_retorna_401(self, client):
        r = client.post(
            "/api/v1/auth/logout",
            headers=auth("token.invalido.aqui"),
        )
        assert r.status_code == 401
