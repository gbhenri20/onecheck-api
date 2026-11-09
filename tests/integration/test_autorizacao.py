"""Hierarquia de contas: admin administra, gestor opera, os demais ficam no próprio vínculo."""

from app.auth import create_access_token
from app.models import Usuario
from tests.conftest import _SENHA_HASH, auth

USUARIOS = "/api/v1/usuarios"


def _outro_vistoriador(db):
    usuario = Usuario(
        nome="Outro Vistoriador",
        email="outro.vistoriador@test.com",
        senha_hash=_SENHA_HASH,
        role="vistoriador",
        ativo=True,
    )
    db.add(usuario)
    db.flush()
    return usuario


class TestContasExclusivasDoAdmin:
    def test_admin_lista_usuarios(self, client, user_admin, token_admin):
        r = client.get(USUARIOS, headers=auth(token_admin))
        assert r.status_code == 200
        assert r.json()["sucesso"] is True
        assert any(item["id"] == user_admin.id for item in r.json()["dados"])

    def test_gestor_vistoriador_e_locatario_recebem_403_na_lista(
        self, client, token_gestor, token_vistoriador, token_locatario
    ):
        for token in (token_gestor, token_vistoriador, token_locatario):
            r = client.get(USUARIOS, headers=auth(token))
            assert r.status_code == 403

    def test_somente_admin_consulta_perfil_de_terceiro(
        self, client, user_locatario, token_admin, token_gestor, token_vistoriador
    ):
        admin = client.get(f"{USUARIOS}/{user_locatario.id}", headers=auth(token_admin))
        assert admin.status_code == 200
        assert admin.json()["dados"]["email"] == user_locatario.email

        for token in (token_gestor, token_vistoriador):
            r = client.get(f"{USUARIOS}/{user_locatario.id}", headers=auth(token))
            assert r.status_code == 403

    def test_somente_admin_cria_edita_e_desativa(
        self, client, db, token_admin, token_gestor
    ):
        criado = client.post(
            USUARIOS,
            json={
                "nome": "Conta Nova",
                "email": "conta.nova@test.com",
                "senha": "senha123",
                "role": "locatario",
            },
            headers=auth(token_admin),
        )
        assert criado.status_code == 200
        usuario_id = criado.json()["dados"]["id"]

        negado = client.post(
            USUARIOS,
            json={
                "nome": "Gestor Nao Cria",
                "email": "gestor.nao.cria@test.com",
                "senha": "senha123",
                "role": "locatario",
            },
            headers=auth(token_gestor),
        )
        assert negado.status_code == 403

        edicao = client.put(
            f"{USUARIOS}/{usuario_id}",
            json={"nome": "Conta Alterada"},
            headers=auth(token_gestor),
        )
        assert edicao.status_code == 403

        desativar = client.delete(f"{USUARIOS}/{usuario_id}", headers=auth(token_gestor))
        assert desativar.status_code == 403

        ok_admin = client.delete(f"{USUARIOS}/{usuario_id}", headers=auth(token_admin))
        assert ok_admin.json()["sucesso"] is True
        db.expire_all()
        assert db.get(Usuario, usuario_id).ativo is False

    def test_mfa_proprio_continua_e_mfa_de_terceiro_fica_com_o_admin(
        self, client, user_locatario, token_locatario, token_gestor, token_admin
    ):
        proprio = client.post(f"{USUARIOS}/me/mfa/setup", headers=auth(token_locatario))
        assert proprio.status_code == 200
        assert proprio.json()["sucesso"] is True
        assert proprio.json()["dados"].get("secret")

        terceiro = client.post(
            f"{USUARIOS}/{user_locatario.id}/mfa/setup",
            headers=auth(token_gestor),
        )
        assert terceiro.status_code == 403

        admin = client.post(
            f"{USUARIOS}/{user_locatario.id}/mfa/setup",
            headers=auth(token_admin),
        )
        assert admin.status_code == 200
        assert admin.json()["sucesso"] is True


class TestResumoOperacional:
    def test_gestor_recebe_somente_nome_de_vistoriador(
        self, client, user_vistoriador, user_admin, token_gestor
    ):
        r = client.get(
            f"{USUARIOS}/resumo?role=vistoriador",
            headers=auth(token_gestor),
        )
        assert r.status_code == 200
        dados = r.json()["dados"]
        assert any(item["id"] == user_vistoriador.id for item in dados)
        assert all(item["role"] == "vistoriador" for item in dados)
        assert all("email" not in item and "cpf" not in item and "mfa_enabled" not in item for item in dados)
        assert all(item["id"] != user_admin.id for item in dados)

    def test_vistoriador_nao_lista_o_resumo(self, client, token_vistoriador):
        r = client.get(f"{USUARIOS}/resumo?role=locatario", headers=auth(token_vistoriador))
        assert r.status_code == 403

    def test_resumo_nao_lista_administradores(self, client, token_admin):
        r = client.get(f"{USUARIOS}/resumo?role=admin", headers=auth(token_admin))
        assert r.json()["sucesso"] is False


class TestEscopoPorVinculo:
    def test_gestor_continua_na_operacao(self, client, token_gestor):
        imoveis = client.get("/api/v1/imoveis", headers=auth(token_gestor))
        painel = client.get("/api/v1/dashboard", headers=auth(token_gestor))
        logs = client.get("/api/v1/logs", headers=auth(token_gestor))
        assert imoveis.status_code == 200
        assert painel.status_code == 200
        assert logs.status_code == 403

    def test_vistoriador_ve_somente_a_propria_vistoria(
        self, client, db, checklist, token_vistoriador
    ):
        propria = client.get(
            f"/api/v1/checklists/{checklist.id}",
            headers=auth(token_vistoriador),
        )
        assert propria.status_code == 200

        outro = _outro_vistoriador(db)
        alheia = client.get(
            f"/api/v1/checklists/{checklist.id}",
            headers=auth(create_access_token(outro.id, outro.role)),
        )
        assert alheia.status_code == 403

    def test_locatario_ve_somente_o_proprio_contrato(
        self, client, db, contrato, imovel, token_locatario
    ):
        proprio = client.get(f"/api/v1/contratos/{contrato.id}", headers=auth(token_locatario))
        assert proprio.status_code == 200

        outro = Usuario(
            nome="Outro Locatario",
            email="outro.locatario@test.com",
            senha_hash=_SENHA_HASH,
            role="locatario",
            ativo=True,
        )
        db.add(outro)
        db.flush()
        from app.models import Contrato
        from datetime import date

        alheio = Contrato(
            imovel_id=imovel.id,
            locatario_id=outro.id,
            data_inicio=date(2025, 2, 1),
            data_fim=date(2025, 12, 31),
            status="encerrado",
        )
        db.add(alheio)
        db.flush()
        r = client.get(f"/api/v1/contratos/{alheio.id}", headers=auth(token_locatario))
        assert r.status_code == 403

    def test_trocar_id_do_imovel_nao_abre_dados_de_terceiro(
        self, client, imovel, token_vistoriador, token_locatario
    ):
        for token in (token_vistoriador, token_locatario):
            r = client.get(f"/api/v1/imoveis/{imovel.id}", headers=auth(token))
            assert r.status_code == 403
