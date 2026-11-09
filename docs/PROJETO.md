# OneCheck — documento do projeto

O OneCheck registra vistorias de imóveis alugados. O locatário acompanha o próprio contrato e o laudo. O vistoriador preenche somente as vistorias atribuídas a ele. O gestor organiza imóveis, contratos, agenda e ocorrências. O administrador é o único que gerencia contas e consulta a auditoria.

O sistema tem duas partes:

- Aplicativo Flutter, neste repositório.
- API REST em Python (FastAPI), publicada em `https://isg022-one-check-api-python.onrender.com`.

O aplicativo não decide sozinho se uma operação é permitida. Ele esconde rotas e botões. A API responde `403` quando o papel ou o vínculo não autoriza a consulta.

## Endereço da API

O arquivo `assets/env/app_config.json` usa:

```json
"apiBaseUrl": "https://isg022-one-check-api-python.onrender.com",
"apiPrefix": "/api/v1"
```

O cliente HTTP junta os dois e chama, por exemplo, `https://isg022-one-check-api-python.onrender.com/api/v1/auth/login`. A URL base não leva barra no final nem o prefixo `/api/v1`.

O Swagger da API publicada fica em `https://isg022-one-check-api-python.onrender.com/docs`.

Uma API rodando na própria máquina pode usar `http://127.0.0.1:8765`. O emulador web do FlutLab não alcança esse endereço.

## Perfis

Existem quatro papéis. Não há um quinto tipo de usuário.

| Papel | Função |
| --- | --- |
| `admin` | Contas, papéis, MFA de outras pessoas, imóveis, contratos, vistorias, indicadores e auditoria |
| `gestor` | Imóveis, contratos, agendamentos, vistorias, ocorrências e indicadores. Sem contas e sem logs |
| `vistoriador` | A própria agenda, os checklists atribuídos, fotos e observações, e o próprio perfil |
| `locatario` | Os próprios contratos, imóveis ligados a eles, vistorias, ocorrências permitidas e o próprio perfil |

Desativar uma conta grava `ativo = false`. O histórico dessa pessoa permanece no banco.

## Autenticação

1. `POST /auth/login` recebe e-mail e senha.
2. Se a conta ainda não tem MFA configurado, a API devolve um token temporário de preparação e o aplicativo abre `/mfa-setup`.
3. Se o MFA já está ativo, a API devolve um token temporário de verificação e o aplicativo abre `/mfa`.
4. O código de seis dígitos vai para `POST /auth/mfa/activate-login` ou `POST /auth/mfa/verify`.
5. Só então a API emite o access token e o refresh token.

O botão Voltar das duas telas abandona só esse desafio e retorna ao login, mantendo o e-mail digitado. O segredo TOTP aparece na tela de ativação para o aplicativo autenticador. Ele não entra em mensagem de erro.

Access e refresh ficam no `flutter_secure_storage`. A senha não é gravada. O código de seis dígitos é validado pela API, não pelo celular.

`GET /usuarios/me`, `PATCH /usuarios/me` e `PUT /usuarios/me/senha` continuam disponíveis para a própria conta. O mesmo vale para o setup, a ativação e a desativação do MFA próprio.

## Aplicativo Flutter

Organização por funcionalidade. A tela observa um provider do Riverpod. O provider chama um repositório. O repositório usa o `DioClient`.

| Pasta | Responsabilidade |
| --- | --- |
| `lib/app` | Tema, rotas e providers globais |
| `lib/core` | Configuração, HTTP, tokens, Hive, compressão de imagem e widgets |
| `lib/features/auth` | Login, ativação do MFA e código do autenticador |
| `lib/features/home` | Painel, menu e navegação por papel |
| `lib/features/imoveis` | Imóveis, endereço e cômodos |
| `lib/features/contratos` | Contratos, agendamentos e abertura de checklist |
| `lib/features/agenda` | Agenda agregada, busca e filtros |
| `lib/features/checklist` | Preenchimento, fotos, revisão e envio |
| `lib/features/vistoria` | Vistorias e aceite do locatário |
| `lib/features/ocorrencias` | Problemas e linha do tempo |
| `lib/features/usuarios` | Cadastro administrativo |
| `lib/features/auditoria` | Logs da API |
| `lib/features/logs` | Histórico local do aparelho |
| `lib/features/perfil` | Nome, senha, fila offline e saída |

O `GoRouter` manda cada papel para a página inicial dele:

- administrador e gestor: `/admin`
- vistoriador: `/agenda`
- locatário: `/locatario`

`/usuarios`, `/auditoria` e `/historico` só abrem para o administrador. Um endereço digitado por outro papel volta para a página inicial desse papel.

A identidade visual usa o fundo azul-marinho, o botão azul e a palavra OneCheck com “Check” em verde.

### Agenda

Não existe `GET /agendamentos` global. A agenda junta contratos, checklists, agendamentos e imóveis. Dá para buscar por nome ou endereço e filtrar por status, tipo e, para administrador e gestor, pelo responsável.

Os tipos exibidos são entrada (`inicial`), saída (`encerramento`) e manutenção (`manutencao`). A criação pela API aceita entrada e saída. Manutenção é um tipo já gravado para demonstração e aparece na lista.

O nome do vistoriador na agenda não vem de uma listagem completa de contas. O aplicativo chama `GET /usuarios/resumo?role=vistoriador`, que devolve só identificador, nome e papel.

## API

FastAPI, SQLAlchemy e PostgreSQL em produção. Os testes usam SQLite. O prefixo das rotas é `/api/v1`.

A resposta de negócio usa o envelope `sucesso`, `dados`, `erro` e, quando há lista, `paginacao`. Falta de token responde `401`. Papel ou vínculo insuficiente responde `403`.

As regras de vínculo ficam em `app/access.py`. `require_roles` protege as rotas administrativas. O papel `admin` continua autorizado nas rotas operacionais de gestor.

### Contas

| Rota | Quem pode |
| --- | --- |
| `GET /usuarios` | administrador |
| `POST /usuarios` | administrador |
| `GET /usuarios/{id}` | administrador |
| `PUT /usuarios/{id}` | administrador |
| `DELETE /usuarios/{id}` | administrador, sem desativar a própria conta |
| MFA de outro usuário | administrador |
| `GET /usuarios/resumo` | administrador e gestor, só vistoriador e locatário, sem e-mail, CPF ou MFA |
| rotas `/usuarios/me` | o próprio usuário autenticado |

### Auditoria

`GET /logs` é exclusivo do administrador. A consulta devolve ação, entidade, identificador, detalhes, payload sanitizado, IP e data. Senha e segredo MFA não são gravados no payload.

A gravação do log continua em criações, alterações e exclusões, qualquer que seja o papel de quem fez a operação. Nada é apagado para esconder o histórico.

`GET /dashboard` fica com administrador e gestor. Locatário e vistoriador recebem `403`, porque os números são do conjunto da operação, não de um contrato isolado.

### Vínculo dos dados

- O locatário só abre contrato, imóvel, vistoria, PDF e ocorrência ligados ao próprio contrato.
- O vistoriador só abre imóvel, contrato, agenda e checklist em que ele é o responsável.
- Criar checklist é ação de administrador ou gestor, e o responsável informado precisa ter o papel vistoriador.
- O PDF do laudo mostra o nome das partes, sem e-mail.
- O gestor continua criando imóvel, contrato e agendamento, acompanhando ocorrências e vendo os indicadores.

## Dados

As tabelas principais são:

- `usuarios` e `auth_refresh_tokens`
- `imoveis`, `enderecos` e `imoveis_comodos`
- `contratos` e `agendamentos_vistoria`
- `checklists`, `checklist_itens`, `checklist_item_fotos` e `aceites_checklist`
- `itens_vistoria`, o catálogo de pintura, piso, portas, janelas e instalações
- `problemas` e `atualizacoes_problema`
- `logs_operacao`

Quartos e banheiros são cômodos, não colunas do imóvel. O estado de pintura, piso, portas, janelas e instalações fica nos itens do checklist. Fotos são arquivos enviados de verdade. O aplicativo não inventa imagem.

O Hive, no aparelho, guarda rascunho de checklist, fila de fotos ainda não confirmadas e a URL da API escolhida na tela. Não guarda senha.

## Fluxos

### Primeira ativação do MFA

Login, tela com QR Code, código de seis dígitos, sessão criada. Voltar retorna ao login sem prender a pessoa na configuração.

### Acesso seguinte

Login, tela do código, sessão criada. Código inválido ou expirado mostra o erro da API e não entra. Voltar retorna ao login sem reiniciar o e-mail.

### Vistoria

O gestor cria o contrato com um locatário e abre o checklist escolhendo o vistoriador. O vistoriador vê o item na agenda, preenche cômodos, registra foto e observação e envia. O locatário aceita ou rejeita com motivo. Depois de enviada, aceita ou rejeitada, a edição fecha no aplicativo e na API.

### Ocorrência

O locatário registra um problema no próprio contrato. Administrador e gestor acompanham, mudam o status e acrescentam a linha do tempo.

## Como executar o aplicativo

```bash
flutter pub get
flutter analyze
flutter test
flutter run -d chrome
```

Android:

```bash
flutter run -d android
```

## Como executar a API localmente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-test.txt
uvicorn app.main:app --host 0.0.0.0 --port 8765
pytest
```

Para apontar o aplicativo a essa API local, troque `apiBaseUrl` para `http://127.0.0.1:8765`. A URL publicada do projeto continua sendo a do Render.

## Testes que protegem a hierarquia

No Flutter, `test/unit/route_access_test.dart` garante que só o administrador abre usuários, auditoria e histórico, e que o gestor continua entrando em imóveis, contratos e agenda.

Na API, `tests/integration/test_autorizacao.py` cobre a lista de contas, o perfil de terceiros, a criação e a desativação, os logs, o resumo operacional, a vistoria do próprio vistoriador, o contrato do próprio locatário e a troca de identificador na URL.

## O que este repositório não contém

As vistorias de demonstração já inseridas no banco da API publicada não estão em arquivos deste repositório. Usuários reais e vistorias anteriores não foram substituídos. Senha de banco, `SEED_SECRET` e segredo MFA de uma conta ativa não ficam no código do aplicativo.
