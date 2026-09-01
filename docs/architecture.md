# Arquitetura

## Visão geral

```text
Frontend React
      ↓ HTTP/JSON
FastAPI + provider por ambiente
      ├── DEV → MockGestorService
      ├── HML → GestorSqlService → SQL Server / Protheus read-only
      └── PRD → GestorSqlService com `.env.prd` e opt-in read-only
```

O navegador se comunica exclusivamente com uma API REST. O ambiente do processo (`APP_ENV`) é separado do ambiente de dados do Gestor (`dev`, `hml` ou `prd`), informado por requisição. O acesso ao ERP permanece encapsulado e read-only.

## Responsabilidades

### Frontend

- Apresentar páginas, filtros, indicadores e estados de interface.
- Fazer requisições HTTP à API e tipar seus contratos.
- Não conhecer credenciais, drivers ou detalhes do SQL Server.
- Não reproduzir consultas ao Protheus no cliente.

### API

- Definir endpoints e validar dados de entrada e saída.
- Traduzir resultados dos serviços para contratos HTTP/JSON.
- Centralizar respostas de erro e preocupações próprias da camada web.

### Serviços

- Orquestrar os casos de uso e aplicar as regras consolidadas do Gestor de Compras.
- Permanecer independentes do protocolo HTTP e dos detalhes do banco.

### Repositórios

- Encapsular as consultas ao SQL Server.
- Expor dados aos serviços sem espalhar SQL pelas demais camadas.
- Garantir o princípio read-only: nenhuma operação de escrita no ERP.

### Schemas e modelos

- Schemas definem contratos validados da API.
- Modelos representam conceitos internos quando forem necessários.

### Configuração

- Ler configurações do ambiente sem armazenar segredos no código.
- Manter valores padrão seguros para desenvolvimento local.
- Centralizar variáveis backend com Pydantic Settings e variáveis Vite em `src/config/env.ts`.
- Validar ambiente, prefixo da API, URL pública e origens CORS antes do uso.

### Fluxo de configuração

```text
backend/.env → Pydantic Settings → FastAPI, CORS e logging
frontend/.env → config/env.ts → páginas e services HTTP
```

Os campos `DB_*` configuram a conexão usada em HML e, quando explicitamente habilitada, na validação PRD. O logging de inicialização contém somente nome, versão e ambiente e não expõe configuração SQL.

## Comunicação disponível

Na ET-003, a HomePage consulta `GET /api/info` por meio deste fluxo:

```text
HomePage → useAppInfo → appService → httpClient → FastAPI /api/info
```

- `httpClient` aplica a `VITE_API_BASE_URL` centralizada e converte respostas HTTP inválidas em erro tipado.
- `useAppInfo` controla carregamento, dados, erro e cancelamento da requisição ao desmontar.
- A página apresenta somente estados públicos e continua funcional quando a API está desligada.
- O CORS do backend permite apenas as origens explicitamente configuradas.

## App Shell

As rotas são renderizadas em uma estrutura reutilizável baseada em React Router:

```text
AppShell
├── Sidebar
└── Área da aplicação
    ├── Topbar
    └── MainContent
        └── Outlet da rota
```

A Sidebar centraliza a identidade e a navegação; a Topbar apresenta o contexto da página e o ambiente; o MainContent preserva largura para as futuras telas densas do Gestor. Em telas estreitas, a navegação assume uma faixa superior compacta sem criar um sistema de menu mobile.

### Páginas atuais

- `/`: página inicial e estado da API.
- `/gestor`: tela operacional com período, filtro de Natureza e grade financeira.
- `*`: página não encontrada dentro do App Shell.

A `GestorPage` compõe componentes específicos de apresentação para período, filtro, legenda e tabela. A seleção de período dispara este fluxo:

```text
GestorPage → useGestor → gestorService → httpClient
           → FastAPI /api/gestor → provider por ambiente
```

- `useGestor` controla dados, carregamento, erro, retry e cancelamento de requisições obsoletas.
- Cada snapshot do hook é identificado pela consulta atual; ao trocar período ou executar retry, dados e erros de outra consulta deixam de ser expostos imediatamente.
- `gestorService` monta `ano`, `mes` e `filial` com `URLSearchParams` e valida a quantidade retornada.
- A filial atual `0101`, o período inicial e os limites de navegação são centralizados na configuração de domínio do Gestor.
- O mock frontend foi removido e não existe fallback local: DEV usa o backend mock e HML usa SQL.
- Os cinco repositories de domínio são read-only e resolvem os nomes físicos das tabelas em um ponto central.

## Infraestrutura SQL Server preparada

Desde a ET-013, o backend possui uma camada central de conexão usada pelo fluxo HML:

```text
FastAPI → GestorSqlService → repositories → app/core/database.py
        → pyodbc / ODBC Driver → SQL Server Protheus HML
```

Essa infraestrutura constrói a configuração em um único ponto, limita timeouts e fecha cada conexão por context manager. Não existe conexão global nem pool customizado. O pooling padrão do `pyodbc` pode ser utilizado pelo driver, mantendo ciclo de aquisição e liberação explícito na aplicação.

O health técnico utiliza somente `SELECT 1`. Os repositories permanecem isolados da camada HTTP; `GET /api/gestor` chega a eles em HML ou no PRD habilitado por meio do provider e do `GestorSqlService`.

`ApplicationIntent=ReadOnly` é opcional e não substitui a garantia definitiva: a credencial da aplicação em HML deverá receber no SQL Server somente as permissões de leitura estritamente necessárias.

### Repository de Naturezas

Desde a ET-014, o primeiro fluxo interno de domínio está preparado:

```text
NaturezaRepository → SQL connection layer → SED + EXISTS SE7
```

O repository retorna o universo permitido como `NaturezaRecord`, desacoplado das colunas físicas. Ele filtra SED por filial e painel `02` parametrizados e usa `EXISTS` na SE7 ativa, sem ano/mês, para confirmar participação histórica. O `LimiteRepository` permanece responsável pelo valor periódico. Os nomes físicos são formados por prefixos internos e sufixo configurado/validado.

### Repository de Limites

Desde a ET-015, a leitura interna do Limite Original segue:

```text
LimiteRepository → SQL connection layer → SE7
```

`list_limites` consulta todas as Naturezas de filial/ano/mês em lote. A coluna mensal vem de whitelist fixa e os valores retornam como `Decimal`. `get_limite` reutiliza a mesma lógica para uma Natureza parametrizada. Registros ambíguos geram erro interno explícito.

Natureza e Limite compartilham a resolução central de nomes físicos baseada em `DB_PROTHEUS_TABLE_SUFFIX`. Nenhum endpoint ou service de composição foi criado.

### Repository de PC aberto

Desde a ET-016, os compromissos de Pedidos de Compra seguem o fluxo interno:

```text
PcAbertoRepository → SQL connection layer → SZN + SC7
```

O repository agrega `ZN_SALDO` por Natureza em uma consulta para o período, verificando na SC7 a existência de pedido ainda aberto e sem resíduo. Tabelas, filial e período usam respectivamente resolução central e parâmetros SQL. O retorno financeiro permanece `Decimal`.

O fluxo operacional permanece separado do repository:

```text
GET /api/gestor → provider → DEV mock ou HML GestorSqlService
```

### Repository de NF entrada

Desde a ET-017, os rateios por Natureza dos títulos de entrada seguem o fluxo interno:

```text
NfEntradaRepository → SQL connection layer → SE2 + SEV
```

O repository soma `EV_VALOR` por `EV_NATUREZ` para os títulos com vencimento no mês, preservando as chaves, situações e identificador do método `FWACOM04:retSldTitulos`. A consulta é única para todas as Naturezas, usa nomes de tabela centralizados e parâmetros SQL, e retorna valores `Decimal`.

Este fluxo interno é orquestrado somente pelo serviço HML:

```text
GET /api/gestor → provider HML → GestorSqlService
```

### Repository de Contingências

Desde a ET-018, as duas colunas de contingência seguem o fluxo interno:

```text
ContingenciaRepository → SQL connection layer → SZR
```

Uma consulta agrega `ZR_CONTING` por `ZR_NATUREZ`, separando Contingência OK e Contingência em aprovação por condições confirmadas de `ZR_APROV` e `ZR_REPROV`. O agregado não usa SC7 ou SA2, que pertencem somente ao detalhamento do fonte original. O retorno possui os dois valores em `Decimal`, sem consulta individual por Natureza.

O fluxo operacional acessa o repository em HML e, com opt-in, na validação PRD:

```text
GET /api/gestor → provider HML ou PRD habilitado → GestorSqlService
```

### Serviço consolidado SQL

Desde a ET-019, a composição real pode ser exercitada isoladamente pelo fluxo:

```text
GestorSqlService
├── NaturezaRepository
├── LimiteRepository
├── PcAbertoRepository
├── NfEntradaRepository
└── ContingenciaRepository
```

Cada repository é chamado uma vez, totalizando cinco consultas em lote. Os códigos mensais são a união dos resultados de Limite, PC, NF e Contingência, limitada ao universo retornado pelo `NaturezaRepository`. Movimentos fora do painel não criam linha nem 503. Natureza elegível sem movimento não aparece; ausência de um componente financeiro vira `Decimal("0")`. Códigos vazios e duplicidades continuam defensivamente rejeitados.

O service calcula `Limite Total = Limite Original + Contingência OK`, `Saldo Previsto = Limite Total - PC aberto - NF entrada` e `Saldo Real = Limite Total - NF entrada`. Contingência em aprovação permanece apenas informativa. O serviço não contém SQL, não compartilha conexão entre repositories e não estabelece snapshot transacional entre as cinco leituras independentes.

O caminho público seleciona a fonte por ambiente:

```text
GET /api/gestor → provider → DEV mock, HML SQL ou PRD SQL com opt-in
```

Não existe fallback entre as fontes. PRD retorna indisponibilidade controlada antes de construir o serviço SQL, exceto quando `GESTOR_PRD_READ_ONLY_VALIDATION=true`.

### Seleção da fonte do Gestor

```text
GET /api/gestor
        ↓
Gestor Service Provider
├── DEV → MockGestorService
├── HML → GestorSqlService → cinco repositories → SQL Server HML
└── PRD → bloqueado por padrão
          └── flag=true → GestorSqlService → cinco repositories → SQL Server PRD
```

O provider consulta `APP_ENV` e, somente em PRD, a flag explícita. A rota preserva `GestorResponse`, não possui SQL ou fórmulas e converte bloqueio, falhas de banco ou integridade em HTTP 503 sanitizado. HML e o endpoint PRD habilitado não realizam health adicional por requisição e não utilizam fallback para o mock.

A ativação técnica da API HML foi validada para os três meses disponíveis no frontend. A validação visual final da ET-020B permanece pendente quando não houver navegador controlável conectado ao ambiente de automação.

### Runner de validação HML

A ET-020 acrescenta um fluxo operacional separado do runtime normal:

```text
HML Validation Runner
        ↓
Database Health central
        ↓
GestorSqlService
        ↓
cinco repositories em lote
```

O runner exige ambiente HML e argumentos explícitos, bloqueia DEV/PRD antes de qualquer conexão e apresenta apenas um resumo estrutural sanitizado. Ele não possui endpoint, não participa da inicialização FastAPI, não constrói SQL, não recalcula fórmulas e não modifica o caminho mock do Gestor.

### Runners de validação PRD

Os runners PRD são separados do runner HML e protegidos por `APP_ENV=prd` mais `GESTOR_PRD_READ_ONLY_VALIDATION=true`. Ambos validam os pré-requisitos locais e executam primeiro o health central `SELECT 1`. `validate_gestor_prd` chama a composição existente; `diagnose_pc_aberto_prd` reutiliza apenas o núcleo SELECT-only do diagnóstico, mantendo as guardas de ambiente independentes. Essa capacidade é de comparação funcional, não de operação ou go-live.

### Estados operacionais do Gestor

- **Loading:** mantém a grade reconhecível, oculta linhas anteriores e anuncia o carregamento de forma acessível.
- **Success:** apresenta as linhas e a quantidade informada pela API.
- **Empty:** apresenta mensagem neutra e `0 naturezas`, sem erro ou retry.
- **Error:** mantém a estrutura da página, não apresenta dados antigos e oferece retry da mesma consulta.

O cancelamento com `AbortController` impede que respostas obsoletas substituam a consulta atual. Abort é tratado como comportamento esperado, não como erro funcional.

### Política de navegação mensal

```text
GestorPage → política central de período
            ├── DEV → lista fixa do mock (08/2025 a 10/2025)
            ├── HML → mês civil anterior/próximo (01/2000 a 12/2100)
            └── PRD → navegação bloqueada
                    ↓
              useGestor → GET /api/gestor
```

A troca de ano é calculada como calendário (`12/2025 → 01/2026` e o caminho inverso), sem listas mensais codificadas para HML. A consulta continua identificada por filial, ano e mês; loading, empty, error, retry e cancelamento por `AbortController` permanecem no hook existente.

### Filtros do Gestor

```text
GestorPage
    ↓
Gestor Filters
    ├── Period Filter ──→ estado mensal controlado
    └── Natureza Filter ──→ memória do frontend
    ↓
useGestor
    ↓
GET /api/gestor
```

Somente a alteração do período dispara `useGestor`. A pesquisa por Natureza filtra a resposta presente no frontend e não acrescenta endpoint, parâmetro HTTP ou acesso SQL. Loading, error, retry, cancelamento e proteção contra respostas obsoletas permanecem centralizados no hook.

## Limites atuais

DEV permite navegar somente entre os três meses disponíveis na API mock. HML e PRD permitem navegação mensal entre 2000 e 2100 e consultam seus SQL Servers read-only. Não há persistência do ambiente: ao recarregar, o backend seleciona PRD quando disponível, depois HML e por fim DEV.

## Seleção de datasource por requisição — ET-021D.2A

`GET /api/gestor` recebe `ambiente=dev|hml|prd` (default temporário e seguro: `hml`). O provider centraliza a escolha: DEV não resolve settings nem abre SQL; HML carrega `backend/.env`; PRD carrega `backend/.env.prd` e exige a flag de opt-in. Os loaders criam objetos `Settings` separados e ignoram variáveis do processo, evitando mutação global e cruzamento concorrente entre datasources.

O frontend não monta o Gestor antes de descobrir `default`, `id`, `label` e `available` em `/api/gestor/environments`. PRD é escolhida quando habilitada; HML e DEV são fallbacks de disponibilidade. Assim, não existe consulta ou identificação HML transitória antes da primeira consulta PRD. A confirmação é exigida apenas na seleção manual HML/DEV → PRD. Trocas abortam a chamada anterior e limpam os dados; período e filtro são preservados, exceto período incompatível ao entrar em DEV, que volta deterministicamente para setembro/2025.

Falha na descoberta mantém a aplicação sem datasource e apresenta retry sanitizado. Falha SQL depois de uma consulta PRD iniciada permanece erro PRD e nunca aciona HML.

Na inicialização completa da `GestorPage`, `getCurrentGestorPeriod()` lê uma única vez o ano e o mês civis locais do navegador. HML e PRD usam esse período inicial, limitado defensivamente a `01/2000`–`12/2100`. A regra não usa UTC, relógio do servidor ou persistência e não sobrescreve escolhas realizadas durante a sessão.

## Drill-down financeiro — ET-023 a ET-026

O carregamento consolidado permanece com cinco queries em lote. O drill-down nasce apenas após clique e segue `GestorPage → useGestorDetail → GET /api/gestor/details → provider do ambiente → GestorSqlService → repository`. O hook possui estado, retry, cancelamento e identidade de requisição independentes do `useGestor`.

Cada repository de PC/NF mantém um único fragmento interno de JOIN/predicados compartilhado entre agregado e detalhe. O `ContingenciaRepository` mantém duas operações de detalhe SZR, separadas pelos mesmos status usados no agregado. O service consulta o agregado da fonte selecionada, consulta os registros da mesma Natureza/tipo e exige igualdade exata em `Decimal`. O drawer não conhece campos Protheus, não recalcula regras e não altera a resposta consolidada. Não há chamada de detalhe na montagem nem consulta por linha.

Os tipos `contingencia_ok` e `contingencia_aprovacao` reutilizam integralmente rota, provider, hook, estados e drawer. Na tabela, apenas valores diferentes de zero de PC, NF e das duas contingências viram botões. Uma abertura de contingência executa duas consultas previsíveis: agregado de SZR e detalhe da Natureza/status; o carregamento inicial continua com as cinco consultas em lote.
