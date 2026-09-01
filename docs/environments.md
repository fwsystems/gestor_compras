# Ambientes

O projeto possui exatamente três ambientes oficiais. A aplicação continua iniciando sem SQL Server; a infraestrutura de conexão preparada na ET-013 somente valida `DB_*` quando uma conexão é solicitada.

| Ambiente | `APP_ENV` / `VITE_APP_ENV` | Debug padrão | Fonte de dados nesta fase |
|---|---|---:|---|
| Desenvolvimento | `dev` | `true` | Mock backend, sem exigir SQL Server |
| Homologação | `hml` | `false` | Gestor SQL Server HML read-only; filial atual `0101` |
| Produção | `prd` | `false` | bloqueado por padrão; SQL read-only somente com opt-in explícito |

Valores alternativos, como `development` ou `production`, são inválidos e não são convertidos silenciosamente.

## Backend

O módulo `app/core/config.py` usa Pydantic Settings como fonte central. Variáveis disponíveis:

- `APP_NAME`, `APP_ENV` e `APP_VERSION` identificam a aplicação.
- `API_PREFIX` define o prefixo dos endpoints funcionais; o padrão é `/api`.
- `DEBUG` substitui explicitamente o default do ambiente quando informado com um booleano válido. Um valor não booleano é ignorado e o default seguro do ambiente é aplicado.
- `CORS_ORIGINS` contém uma ou mais origens separadas por vírgula, por exemplo `http://localhost:5193,http://localhost:4173`.
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` e `DB_DRIVER` identificam a conexão SQL Server exclusivamente no backend.
- `DB_CONNECT_TIMEOUT` e `DB_QUERY_TIMEOUT` limitam conexão e consulta.
- `DB_ENCRYPT` e `DB_TRUST_SERVER_CERTIFICATE` controlam TLS conforme a infraestrutura corporativa.
- `DB_APPLICATION_INTENT_READ_ONLY` habilita opcionalmente `ApplicationIntent=ReadOnly`.
- `GESTOR_PRD_READ_ONLY_VALIDATION` habilita explicitamente a comparação controlada em PRD; o default é `false`.

O CORS não aceita `*`. Em DEV, o default seguro permite somente `http://localhost:5193`; HML e PRD devem receber suas origens explícitas por configuração externa. Campos de identidade e credencial do banco são opcionais na inicialização e obrigatórios somente ao solicitar conectividade SQL.

## Frontend

O módulo `src/config/env.ts` é o único ponto que lê `import.meta.env`. Ele valida:

- `VITE_APP_NAME`;
- `VITE_APP_ENV`, limitado a `dev`, `hml` ou `prd`;
- `VITE_API_BASE_URL`, opcional; vazia usa o mesmo origin e o proxy Vite, enquanto um override deve ser uma URL HTTP ou HTTPS.

Os defaults locais seguros permitem executar a aplicação sem criar um `.env`. Valores específicos do ambiente podem ser definidos externamente com base no `frontend/.env.example`.

O servidor Vite DEV utiliza `host: '0.0.0.0'`, porta fixa `5193` e falha claramente quando ela já estiver ocupada, em vez de selecionar outra porta silenciosamente. O proxy `/api` aponta internamente para `http://127.0.0.1:8000`; o browser usa URLs relativas e não conhece o endereço do backend.

## Acesso LAN — ET-024

O IPv4 atual do computador servidor é `10.211.2.67`. Endereços operacionais:

- local: `http://localhost:5193` e `http://127.0.0.1:5193`;
- LAN: `http://10.211.2.67:5193`.

O endereço LAN não está fixado no código e pode mudar se a máquina não possuir reserva DHCP/IP fixo. Somente TCP `5193` precisa ser alcançável pela rede local. O FastAPI deve ser iniciado em `127.0.0.1:8000` e acessado pelo proxy; TCP `8000` não deve ser liberada na LAN.

Como frontend e `/api` compartilham o origin da porta `5193`, não é necessário ampliar CORS nem adicionar wildcard. A ET-024 não autoriza firewall automático, port forwarding, túnel, DMZ, domínio, VPN ou exposição à Internet.

Variáveis Vite são públicas no bundle do navegador. Portanto, nenhuma variável `VITE_*` pode conter credenciais, tokens ou configurações do SQL Server.

## Arquivos locais e secrets

Para personalização local, copie o `.env.example` correspondente para `.env`. HML usa `backend/.env`; PRD possui `backend/.env.prd`. O `.gitignore` bloqueia `.env` e todas as suas variações, mantendo somente arquivos chamados `.env.example` versionáveis.

Nunca versionar ou retornar em endpoints públicos:

- IPs internos;
- usuários ou senhas;
- strings de conexão reais;
- tokens ou outros secrets;
- hosts ou drivers de infraestrutura.

Credenciais existem exclusivamente no backend local/externo e o acesso ao ERP continua 100% read-only. O sufixo físico HML atualmente identificado é `010`, configurado localmente por `DB_PROTHEUS_TABLE_SUFFIX`; ele não autoriza acesso a PRD nem deve ser usado para inferir outro ambiente.

## Validação controlada em PRD

A matriz do provider é:

| Ambiente | Flag PRD | Fonte |
|---|---:|---|
| DEV | qualquer valor | `MockGestorService` |
| HML | qualquer valor | `GestorSqlService` |
| PRD | `false` | indisponibilidade controlada antes de construir o serviço SQL |
| PRD | `true` | `GestorSqlService`, sem fallback |

Os runners `validate_gestor_prd` e `diagnose_pc_aberto_prd` exigem ambiente `prd`, flag habilitada, configuração SQL completa, sufixo físico e driver instalado. Executam o health central (`SELECT 1`) antes da composição ou diagnóstico. A habilitação é apenas para comparação funcional controlada; não habilita go-live, escrita, carga, sincronização ou fallback para mock.

O loader continua lendo apenas `backend/.env` por padrão; a simples existência de `.env.prd` não altera o ambiente. Para uma execução futura, as variáveis de `.env.prd` devem ser carregadas explicitamente no processo PowerShell autorizado, e a flag deve ser alterada para `true` somente nessa sessão. Não renomear nem substituir `.env`, não criar seleção automática por `APP_ENV` e não imprimir as variáveis importadas. Ao fechar a sessão, a configuração temporária deixa de existir e HML permanece intacta.

A credencial configurada para PRD é a mesma atualmente utilizada em HML, conforme confirmação externa do responsável pelo ambiente. Essa equivalência não comprova permissão SELECT-only, que continua pendente de confirmação externa antes de qualquer conexão.

## Requisitos para validação integrada HML

O runner `python -m scripts.validate_gestor_hml` somente opera com `APP_ENV=hml` e requer configuração externa completa para:

- `DB_HOST`;
- `DB_PORT`;
- `DB_NAME`;
- `DB_USER`;
- `DB_PASSWORD`;
- `DB_DRIVER`;
- `DB_PROTHEUS_TABLE_SUFFIX`;
- opções TLS compatíveis com a infraestrutura.

O driver indicado por `DB_DRIVER` deve estar instalado no Windows. A filial HML, o ano e o mês são argumentos obrigatórios do runner e não são herdados do mock. A credencial deve possuir somente SELECT nas tabelas necessárias; essa permissão deve ser confirmada externamente pelo DBA.

DEV e PRD são bloqueados antes do health e da composição pelo runner HML. Ele não procura credenciais em fontes antigas ou arquivos externos, não imprime configuração de conexão e não substitui HML por produção.

## Fonte do Gestor por ambiente

- DEV: `GET /api/gestor` usa o mock backend e não exige configuração SQL.
- HML: o mesmo endpoint usa `GestorSqlService` e os cinco repositories read-only.
- PRD: retorna indisponibilidade controlada por padrão; com o opt-in explícito usa SQL read-only e nunca mock.

A seleção depende de `APP_ENV` e, somente em PRD, da flag explícita. Nunca depende da mera presença de credenciais. Não existe fallback entre SQL e mock. O frontend utiliza o mesmo contrato em todos os ambientes e não recebe informação sobre a fonte.

## Política de período do frontend

- DEV restringe a navegação a agosto, setembro e outubro de 2025; ao receber um período incompatível durante uma troca, usa setembro/2025.
- HML e PRD iniciam no mês civil atual do navegador e navegam mês a mês, com transição de ano, entre janeiro de 2000 e dezembro de 2100.
- PRD permite navegação quando o backend o anuncia disponível e exige confirmação antes da seleção.

Os limites e o período inicial são configuração de domínio do frontend; não dependem de credenciais nem alteram a seleção da fonte no backend.

Na seleção direta, DEV oferece somente os três períodos do mock; HML e PRD aceitam qualquer mês válido entre 2000 e 2100. O filtro textual de Natureza é idêntico nos ambientes porque opera apenas sobre a resposta já carregada.

## Ambiente do processo × ambiente de dados

`APP_ENV` identifica o processo e não seleciona mais sozinho a fonte do Gestor. Cada chamada informa `ambiente=dev|hml|prd`. HML é carregado explicitamente de `backend/.env`; PRD, de `backend/.env.prd`; DEV não carrega datasource. Os objetos não são mutados nem compartilhados entre ambientes.

Nesta instalação controlada, a flag do `.env.prd` está `true` após confirmação externa de credencial somente consulta, health PRD e comparação funcional. O default do modelo `Settings` e `backend/.env.example` permanecem `false`, portanto arquivos ausentes, inválidos, incompletos ou sem opt-in resultam em `available=false`, sem fail-open e sem fallback.

O frontend recebe apenas a capacidade sanitizada de `/api/gestor/environments`. A ordem inicial é PRD disponível, HML disponível e DEV. A aplicação aguarda essa descoberta antes de montar o Gestor; falha no endpoint não assume PRD nem inicia datasource desconhecido. A escolha não é persistida em storage, cookie ou URL.
