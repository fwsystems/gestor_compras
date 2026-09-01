# Infraestrutura SQL Server

## Objetivo e escopo

A conectividade técnica iniciada na ET-013 usa `pyodbc`. Desde a ET-020B, ela é a fonte do Gestor em HML por meio de cinco repositories de domínio read-only; DEV continua no mock. Desde a ET-021D, PRD permanece bloqueado por padrão e pode usar a mesma composição somente mediante opt-in explícito para validação read-only.

As consultas HML acessam tabelas Protheus com sufixo físico atualmente identificado como `010` (por exemplo, `SED010`, `SE7010`, `SZN010`, `SC7010`, `SE2010`, `SEV010` e `SZR010`). A resolução é centralizada por `DB_PROTHEUS_TABLE_SUFFIX`; o `GestorSqlService` não conhece nomes físicos.

## Dependências do sistema

Além do pacote Python `pyodbc`, o sistema operacional precisa ter instalado o Microsoft ODBC Driver cujo nome é informado por `DB_DRIVER`. O nome não é fixado no código para permitir que a infraestrutura corporativa defina uma versão compatível.

## Configuração

As variáveis pertencem somente ao backend:

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_DRIVER`
- `DB_CONNECT_TIMEOUT`
- `DB_QUERY_TIMEOUT`
- `DB_ENCRYPT`
- `DB_TRUST_SERVER_CERTIFICATE`
- `DB_APPLICATION_INTENT_READ_ONLY`

Credenciais reais devem existir apenas em configuração externa ou `.env` local ignorado pelo Git. A aplicação DEV inicia normalmente com os campos de identidade e credencial vazios; a validação ocorre quando uma conexão é solicitada.

## TLS

`DB_ENCRYPT` habilita ou desabilita criptografia no driver. `DB_TRUST_SERVER_CERTIFICATE` controla a confiança direta no certificado e possui default `false`. Definir esse campo como `true` depende da política e dos certificados da infraestrutura; não deve ser usado silenciosamente como solução universal.

## Timeouts e ciclo de vida

O timeout de conexão possui default de 5 segundos e o de consulta, 30 segundos. Cada aquisição usa context manager e garante fechamento inclusive em exceções. `autocommit=True` evita manter transações abertas durante as consultas exclusivamente read-only; nenhuma operação de escrita é disponibilizada. Não existe conexão singleton nem pool manual. O `pyodbc` mantém seu pooling próprio por padrão.

## Read-only

A camada não oferece helper público genérico para executar SQL arbitrário e não implementa `INSERT`, `UPDATE`, `DELETE`, `MERGE` ou procedures. Além do `SELECT 1` do health, existem somente as consultas de domínio SELECT dos repositories descritos abaixo.

A garantia definitiva deve estar também no SQL Server: o usuário da aplicação deverá receber somente `SELECT` nas tabelas ou views estritamente necessárias. `ApplicationIntent=ReadOnly`, quando habilitado, comunica intenção de roteamento ao SQL Server/Always On, mas não é autorização e não substitui permissões SELECT-only.

## Health check

`GET /api/database/health` executa somente `SELECT 1`:

- HTTP 200 com `{"status":"ok","database":"sqlserver"}` quando a conexão funciona.
- HTTP 503 com `{"status":"unavailable","database":"sqlserver"}` quando falta configuração ou há falha.

A resposta não expõe host, base, usuário, senha, driver ou connection string. `GET /health` permanece independente do banco e indica apenas a disponibilidade da API.

## Primeiro repository de domínio

A ET-014 introduziu `NaturezaRepository`. A ET-021A alinhou seu universo ao Gestor original, conforme evidência de HML e a formação da lista em `FWACOM17`. O repository consulta em lote:

- SED: `ED_FILIAL`, `ED_CODIGO`, `ED_DESCRIC`, `ED_ZPAINEL` e exclusão lógica;
- SE7: existência ativa da mesma filial/Natureza por `EXISTS`.

SE7 participa somente da elegibilidade histórica do universo, sem filtro de ano ou mês nessa consulta. O valor do Limite Original continua sendo responsabilidade exclusiva do `LimiteRepository`, que aplica ano e coluna mensal. Assim, SE7 histórica com Limite atual ausente resulta em zero sem excluir uma Natureza que tenha movimento no período.

Os nomes físicos SED e SE7 usam `DB_PROTHEUS_TABLE_SUFFIX`. O sufixo aceita somente de 1 a 10 letras ou números, é normalizado para maiúsculas e nunca vem de entrada HTTP. Filial e painel são parâmetros; a consulta exige `D_E_L_E_T_ = ''` nas duas tabelas e não utiliza `SELECT *` ou `NOLOCK`.

Campos CHAR têm apenas espaços externos removidos. Código vazio/nulo é descartado, descrição nula se torna string vazia e o retorno interno usa `codigo`/`descricao`, sem propagar nomes físicos do Protheus.

O painel do Gestor de Compras é centralizado como `GESTOR_COMPRAS_PAINEL = "02"` e enviado como parâmetro SQL, nunca concatenado.

## Repository de Limites

A ET-015 introduz `LimiteRepository` para ler exclusivamente o Limite Original mensal da SE7. A operação principal `list_limites(filial, ano, mes)` retorna todos os valores do período em uma consulta, evitando N+1. `get_limite` reutiliza a mesma construção e acrescenta Natureza como parâmetro.

O método `FWACOM04:retSaldo` confirmou o mapa físico:

| Mês | Campo SE7 |
|---:|---|
| 1 | `E7_VALJAN1` |
| 2 | `E7_VALFEV1` |
| 3 | `E7_VALMAR1` |
| 4 | `E7_VALABR1` |
| 5 | `E7_VALMAI1` |
| 6 | `E7_VALJUN1` |
| 7 | `E7_VALJUL1` |
| 8 | `E7_VALAGO1` |
| 9 | `E7_VALSET1` |
| 10 | `E7_VALOUT1` |
| 11 | `E7_VALNOV1` |
| 12 | `E7_VALDEZ1` |

A coluna é escolhida somente por whitelist interna. Filial e ano são parâmetros SQL; o ano inteiro é convertido para texto com quatro dígitos, como `2025`. O nome SE7 físico reutiliza a resolução centralizada baseada em `DB_PROTHEUS_TABLE_SUFFIX`.

Para preservar `FWACOM04:retSaldo`, a query não filtra `E7_MOEDA`. Embora a chave oficial da SE7 possa conter moeda, mais de um registro normalizado para a mesma Natureza é tratado como ambiguidade explícita, nunca resolvido por `TOP 1`, `MAX` ou `SUM`.

Valores permanecem `Decimal`. Zero e `NULL` de um registro existente tornam-se `Decimal("0")`; ausência permanece lista vazia ou `None` na operação individual. A query aplica `D_E_L_E_T_ = ''`, ordena por `E7_NATUREZ` e não utiliza `SELECT *` ou `NOLOCK`.

## Repository de PC aberto

A ET-016 introduz `PcAbertoRepository`, baseado em `FWACOM04:retSldPedidos`. A operação em lote `list_pc_aberto(filial, ano, mes)` executa uma consulta para todas as Naturezas do período.

A regra utiliza SZN e SC7:

- SZN fornece `ZN_FILIAL`, `ZN_NUMPED`, `ZN_NATUREZ`, `ZN_SALDO` e `ZN_VENCTO`.
- SC7 confirma o pedido por `C7_FILIAL = ZN_FILIAL` e `C7_NUM = ZN_NUMPED`.
- O vencimento é filtrado por `ZN_VENCTO LIKE AAAAMM%`.
- O pedido permanece aplicável quando existe item com `C7_QUJE < C7_QUANT` e `C7_RESIDUO = ' '`, enviado como parâmetro SQL.
- `D_E_L_E_T_ = ''` é aplicado nas duas tabelas.

O valor da coluna é `SUM(ZN_SALDO)` agrupado por `ZN_NATUREZ`. A leitura não recalcula quantidade × preço. No fluxo original, `FWACOM04:incluiPrev` forma `ZN_SALDO` a partir do saldo `(C7_QUANT - C7_QUJE) × C7_PRECO` e o distribui conforme a condição de pagamento; `retSldPedidos` soma essas parcelas armazenadas no mês consultado.

Um pedido totalmente recebido não satisfaz a existência de item aberto. Pedido marcado como resíduo também não participa. A consulta não usa item no relacionamento agregado, preservando a implementação não detalhada do fonte original.

Natureza é normalizada com `strip` e valores permanecem `Decimal`. A resolução central de tabelas agora permite SC7 e SZN com o mesmo `DB_PROTHEUS_TABLE_SUFFIX`. Não há `SELECT *`, `NOLOCK`, escrita ou consulta individual por Natureza.

## Repository de NF entrada

A ET-017 introduz `NfEntradaRepository`, baseado diretamente em `FWACOM04:retSldTitulos`. A operação `list_nf_entrada(filial, ano, mes)` agrega todas as Naturezas em uma única consulta, sem N+1, e participa da composição HML por meio do `GestorSqlService`.

A consulta relaciona SE2 e SEV exatamente por filial, número, prefixo, parcela, fornecedor/cliente e loja: `EV_FILIAL = E2_FILIAL`, `EV_NUM = E2_NUM`, `EV_PREFIXO = E2_PREFIXO`, `EV_PARCELA = E2_PARCELA`, `EV_CLIFOR = E2_FORNECE` e `EV_LOJA = E2_LOJA`. O fonte agregado não relaciona tipo e não foi alterado pela ET-025.

O período é o vencimento do título, por `E2_VENCTO LIKE AAAAMM%`. O valor é `SUM(EV_VALOR)` agrupado por `EV_NATUREZ`. Participam somente rateios com `EV_SITUACA NOT IN ('E', 'X')` e `EV_IDENT = '1'`; esses valores, filial e período são parâmetros SQL. SE2 e SEV exigem `D_E_L_E_T_ = ''`.

Para preservar o fonte, não há filtros por `E2_SALDO`, `E2_BAIXA`, `E2_TIPO`, moeda, emissão, impostos ou campo adicional de cancelamento. Assim, baixa total ou parcial não é inferida pelo repository; a seleção decorre somente das condições confirmadas acima. Os significados textuais dos códigos `E` e `X` não são presumidos: operacionalmente, são as duas situações excluídas pelo método original.

SE2 e SEV usam a resolução central de nomes físicos com `DB_PROTHEUS_TABLE_SUFFIX`. A leitura é exclusivamente `SELECT`, sem `SELECT *` ou `NOLOCK`; Natureza é normalizada e o valor financeiro permanece `Decimal`.

Na operação de detalhe, a ET-025 adicionou somente enriquecimento cadastral e `E2_EMISSAO`. O schema real confirmou `SA2.A2_FILIAL`, `A2_COD`, `A2_LOJA`, `A2_NOME`, `SE2.E2_EMISSAO` e `SE2.E2_TIPO`; o tipo foi deliberadamente omitido por falta de utilidade funcional comprovada. A SA2 ativa entra por `LEFT JOIN` com `A2_FILIAL = LEFT(E2_FILIAL, 2)`, fornecedor e loja. A relação retornou cardinalidade máxima 1 nos casos controlados, e a auditoria agregada da filial cadastral não encontrou chave ativa fornecedor+loja duplicada em HML ou PRD. Cadastro ausente mantém a linha com nome vazio para fallback da interface. Não existe consulta à SA2 por título.

A ordem do detalhe é determinística por vencimento, documento, prefixo, parcela, fornecedor e loja. `EV_VALOR float(53)` continua normalizado para `Decimal('0.01')` com `ROUND_HALF_UP` tanto no agregado quanto nas linhas, preservando a invariância.

## Repository de Contingências

A ET-018 introduz `ContingenciaRepository`, baseado em `FWACOM04:retSldConting` e nas chamadas feitas por `FWACOM04:btnAvancar`. A operação `list_contingencias(filial, ano, mes)` retorna Contingência OK e Contingência em aprovação para todas as Naturezas em uma única consulta.

O agregado original usa somente SZR. SC7 e SA2 aparecem apenas quando `retSldConting` é chamado para detalhamento; elas não participam do cálculo das colunas do Gestor. Portanto, o repository agregado não possui JOIN e não antecipa dados de pedido, item ou fornecedor.

Os campos físicos necessários são `ZR_FILIAL`, `ZR_NATUREZ`, `ZR_VENCTO`, `ZR_CONTING`, `ZR_APROV`, `ZR_REPROV` e `D_E_L_E_T_`. O período usa `ZR_VENCTO LIKE AAAAMM%`. O valor de ambas as colunas é a soma de `ZR_CONTING`, nunca `ZR_VALOR`.

Contingência OK corresponde exatamente a `ZR_APROV = 'T'` e `ZR_REPROV <> 'T'`. Contingência em aprovação corresponde a `ZR_APROV = 'F'` e `ZR_REPROV = 'F'`. O código auxiliar de detalhamento identifica a primeira combinação como aprovada, a segunda como aguardando aprovação e as demais como reprovadas; combinações fora dos dois critérios não entram no agregado web.

A query usa duas somas condicionais agrupadas por `ZR_NATUREZ`, preservando zero na coluna oposta quando uma Natureza possui apenas um dos estados. Filial, período e valores de status são parâmetros SQL. A SZR exige `D_E_L_E_T_ = ''`; não existe outro campo de cancelamento na leitura agregada, e registros reprovados são excluídos pelos critérios de status.

O nome físico SZR reutiliza `DB_PROTHEUS_TABLE_SUFFIX` e a resolução central. Natureza recebe `strip`, valores permanecem `Decimal`, e a consulta é exclusivamente read-only, sem `SELECT *`, `NOLOCK`, procedure ou N+1.

Na ET-026, o schema real de HML e PRD confirmou `ZR_NUMPED`, `ZR_ITEMPED`, `ZR_VENCTO`, `ZR_USER`, `ZR_APROV`, `ZR_REPROV` e `ZR_CONTING`. As duas operações de detalhe usam somente SZR e repetem os mesmos filtros de filial, competência, Natureza, exclusão lógica e status do agregado. Não há JOIN ou enriquecimento necessário para identificar pedido/item, nem consulta por registro.

`list_contingencia_ok_details` aplica `ZR_APROV='T'` e `ZR_REPROV<>'T'`; `list_contingencia_aprovacao_details` aplica `ZR_APROV='F'` e `ZR_REPROV='F'`. Ambas ordenam por vencimento, pedido, item e identificador interno, retornando pedido, item, vencimento, usuário, status semântico comprovado e valor. `ZR_CONTING` é `float(53)` nos dois ambientes, por isso agregado e detalhe são normalizados para `Decimal('0.01')` com `ROUND_HALF_UP` antes da comparação exata.

## Composição do Gestor

A ET-019 introduz `GestorSqlService`, que não executa SQL. Uma composição completa chama uma vez cada operação em lote de `NaturezaRepository`, `LimiteRepository`, `PcAbertoRepository`, `NfEntradaRepository` e `ContingenciaRepository`, totalizando cinco consultas read-only independentes.

Os resultados são indexados em memória por Natureza, sem consulta por linha e sem mega-query. Os códigos relevantes são a interseção do universo permitido por SED/SE7/painel com a união de Limite, PC aberto, NF entrada e Contingências. Natureza elegível sem ocorrência financeira não gera linha. Ausência de componente financeiro vira zero; movimento fora do painel é ignorado, enquanto código vazio ou duplicado continua sendo sinalizado explicitamente. O resultado é ordenado por código.

Não existe transação compartilhada, Unit of Work, isolamento especial ou garantia de snapshot único entre as cinco consultas. O endpoint público usa essa composição em HML e o mock em DEV, selecionados pelo provider.

## Validação integrada em HML

A ET-020 prepara `backend/scripts/validate_gestor_hml.py` para validar a composição sem alterar o runtime da API. O runner aceita exclusivamente `APP_ENV=hml`, exige filial, ano e mês explícitos, valida a configuração e a disponibilidade do driver, executa o health central antes da composição e bloqueia DEV e PRD.

Exemplo de execução, somente após configurar externamente o ambiente HML:

```text
python -m scripts.validate_gestor_hml --filial <FILIAL_HML> --ano 2025 --mes 9
```

O modo opcional `--natureza <CODIGO>` exibe apenas um recorte controlado da resposta já carregada, sem nova consulta. A saída padrão contém somente filial mascarada, período, duração aproximada e contadores estruturais; não gera arquivos nem lista valores financeiros individuais.

O fluxo permanece composto pelas cinco consultas em lote dos repositories, sem mega-query e sem N+1. O runner não contém SQL de domínio, não recalcula fórmulas e respeita os timeouts da infraestrutura existente. O health utiliza a consulta técnica mínima já aprovada; todas as operações funcionais continuam read-only.

Na primeira execução real, a ET-020A passou a aceitar qualquer Natureza SED com movimento financeiro. A comparação manual posterior mostrou a regressão: `5.000-350` tinha NF, mas `ED_ZPAINEL` vazio e não aparecia no Gestor original. A ET-021A restabeleceu SED + painel `02` + existência histórica na SE7 como universo permitido. Natureza elegível sem Limite no período ainda recebe Limite Original zero. A comparação financeira completa permanece pendente.

A permissão SELECT-only efetiva da credencial deve continuar confirmada pela infraestrutura/DBA; `ApplicationIntent=ReadOnly` não substitui permissões do banco.

## Fonte SQL no runtime HML

Desde a ET-020B, `GET /api/gestor` utiliza o `GestorSqlService` quando `APP_ENV=hml`. DEV continua no mock sem exigir banco. PRD retorna indisponibilidade e não abre conexão por padrão; a ET-021D permite SQL somente com opt-in explícito. A seleção não depende da mera presença de `DB_HOST` ou outra credencial.

Cada requisição HML mantém as cinco consultas em lote existentes: catálogo SED, Limites, PC aberto, NF entrada e Contingências. Não há `SELECT 1` adicional, mega-query, N+1 ou fallback para dados mock. Falhas SQL e inconsistências são convertidas em HTTP 503 sem expor detalhes internos.

## Validação read-only em PRD

`GESTOR_PRD_READ_ONLY_VALIDATION=false` é o default seguro. Com `APP_ENV=prd` e a flag desabilitada, o provider retorna indisponibilidade antes de construir `GestorSqlService` ou abrir conexão. Com a flag habilitada, o endpoint usa a composição SQL existente, mantém o contrato público e não possui fallback para mock.

Os runners separados são:

```bash
python -m scripts.validate_gestor_prd --filial <FILIAL> --ano <ANO> --mes <MES> [--natureza <CODIGO>]
python -m scripts.diagnose_pc_aberto_prd --filial <FILIAL> --ano <ANO> --mes <MES> --natureza <CODIGO>
```

Ambos validam ambiente, flag, configuração completa, sufixo e driver antes do health técnico `SELECT 1`. O runner consolidado produz resumo estrutural e mascara a filial; valores individuais aparecem somente quando `--natureza` é informado. O runner diagnóstico reutiliza o núcleo SELECT-only da ET-021C, mas possui guarda PRD própria; o runner HML continua rejeitando PRD.

Na continuidade ET-021D.1, a credencial PRD foi confirmada externamente como somente consulta, o health `SELECT 1` passou e a composição read-only foi comparada com o FWACOM04. `ApplicationIntent=ReadOnly` continua sendo defesa adicional e não substitui permissões SQL restritas.

Na ET-021D.2A, cada repository recebe o `Settings` da requisição por injeção. HML e PRD podem coexistir no mesmo processo sem trocar variáveis globais, singleton ou conexão. O ciclo continua sendo context manager por consulta, com timeout e fechamento; não foi criado pool nem conexão global. SQL, JOINs, filtros e agregações dos repositories não foram alterados.

## Queries de detalhe — ET-023 a ET-026

`PcAbertoRepository.list_pc_aberto_details` seleciona explicitamente `ZN_NUMPED`, `ZN_VENCTO`, `ZN_NATUREZ` e `ZN_SALDO`, acrescentando Natureza parametrizada ao mesmo predicado compartilhado pelo agregado. O `EXISTS` em SC7 conserva filial/número, item ainda aberto, resíduo em branco e exclusão lógica; não duplica saldos por item.

`NfEntradaRepository.list_nf_entrada_details` seleciona explicitamente número, prefixo, parcela, fornecedor, loja e vencimento de SE2, Natureza e valor de SEV. O JOIN completo, `EV_SITUACA NOT IN ('E','X')`, `EV_IDENT='1'`, competência por `E2_VENCTO` e exclusões lógicas são os mesmos do agregado. Todos os valores de entrada continuam parametrizados e as queries são exclusivamente `SELECT`, sem `NOLOCK` ou escrita.

`ContingenciaRepository` possui duas operações de detalhe sobre SZR, uma para cada combinação de status consolidada. Cada abertura executa uma consulta agregada para obter o total homologado e uma única consulta de linhas para a Natureza/tipo solicitado. As categorias não se misturam e nenhuma consulta de detalhe foi adicionada ao carregamento principal.

As queries adicionais existem somente durante uma solicitação de detalhe. Não foram acrescentadas ao fluxo inicial do Gestor, portanto as cinco queries em lote e a ausência de N+1 permanecem.

### Precisão de `EV_VALOR` — ET-023A

O schema PRD confirma `SEV.EV_VALOR` como SQL Server `float(53)`. Por isso, `SUM(EV_VALOR)` pode carregar resíduos da representação binária, mesmo quando os valores têm semântica de moeda. No caso comprovado de agosto/2026, a API obteve `28056.880000000005` e uma recontagem das mesmas 9 contribuições obteve `28056.879999999997`; o `SUM(CAST(... AS DECIMAL(28,2)))` e a soma detalhada resultaram em `28056.88`. A variação do resíduo entre execuções reforça que a causa é a aritmética `float`, não diferença no conjunto de linhas.

O repository normaliza toda leitura de `EV_VALOR` — agregada ou individual — para `Decimal('0.01')` com `ROUND_HALF_UP`. Essa é uma normalização de fronteira do tipo físico para o domínio monetário; não modifica JOIN, filtros, cardinalidade, campo somado ou query agregada. A validação exata de invariância permanece ativa após a normalização.
