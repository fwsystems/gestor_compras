# Handoff técnico — Gestor de Compras Web

Este documento é o contexto operacional autocontido para continuar o projeto em outra sessão. Sprint 3 está concluída; Sprint 4 está em andamento; ET-023 a ET-027 estão concluídas. A ET-024 foi homologada manualmente em outros computadores da LAN. Não substitui a validação das regras no Protheus.

## 1. Objetivo do projeto

Reconstruir na Web o Gestor de Compras existente no TOTVS Protheus, preservando as regras funcionais confirmadas e alcançando paridade em HML antes de qualquer habilitação de PRD.

## 2. Arquitetura atual

## Ajuste visual posterior — colunas do detalhe de NF entrada

O drawer de NF entrada passou a renderizar somente Documento, Parcela, Nome do fornecedor, Emissão, Vencimento e Valor, nessa ordem. Prefixo, fornecedor e loja continuam no retorno da API e nos tipos internos, mas deixaram de ser apresentados nessa tabela. As larguras foram redistribuídas para manter o nome do fornecedor amplo, datas legíveis, valor alinhado à direita e responsividade, sem alterar quantidade, total, filtros, período ou os demais detalhamentos.

Nenhuma alteração foi feita em backend, contrato, SQL, repositories, regras financeiras ou cálculos.

## Ajuste posterior — fornecedor no detalhe de PC aberto

O detalhe de PC aberto passou a retornar e exibir Fornecedor entre Pedido e Vencimento. O código e o nome são obtidos da SC7 elegível do pedido, com enriquecimento opcional do nome pela SA2 ativa; o frontend prioriza o nome e usa o código como fallback. O agregado de PC aberto, quantidade, total, período, ambiente e os demais drawers permanecem inalterados.

- Frontend: React, TypeScript e Vite.
- Backend: Python, FastAPI, Pydantic Settings e `pyodbc`.
- Banco: SQL Server do Protheus, acessado somente pelo backend e somente em modo read-only.
- API: `GET /api/gestor` mantém o mesmo contrato, independentemente da fonte.
- Detalhes: `GET /api/gestor/details` atende `pc_aberto`, `nf_entrada`, `contingencia_ok` e `contingencia_aprovacao`, sob demanda e no ambiente explicitamente informado.
- Composição HML: `GestorSqlService` chama cinco repositories uma vez cada. São cinco consultas independentes e em lote, sem N+1, sem mega-query e sem snapshot transacional compartilhado.
- Resolução física: nomes de tabela são centralizados em `app/core/protheus_tables.py`; o service não conhece tabelas ou campos Protheus.

Fluxo:

```text
Frontend → FastAPI → Gestor Service Provider
                    ├── DEV → MockGestorService
                    ├── HML → GestorSqlService → 5 repositories → SQL Server HML
                    └── PRD → bloqueado por padrão / SQL com opt-in read-only
```

## 3. Ambientes

| Ambiente | Fonte | Período no frontend | Situação |
|---|---|---|---|
| DEV | Mock backend, sem SQL | 08/2025, 09/2025 e 10/2025 | ativo |
| HML | `GestorSqlService` read-only | 01/2000 a 12/2100 | homologação funcional |
| PRD | nenhuma por padrão; `GestorSqlService` com opt-in | validação controlada | não é go-live |

Fixtures DEV: 18 Naturezas em agosto/2025, 20 em setembro/2025 e 22 em outubro/2025. A filial usada atualmente em HML é `0101`. O sufixo físico HML identificado é `010`, produzindo nomes como `SA2010`, `SED010`, `SE7010`, `SZN010`, `SC7010`, `SE2010`, `SEV010` e `SZR010`.

PRD permanece bloqueado por padrão. A ET-021D adicionou `GESTOR_PRD_READ_ONLY_VALIDATION=false`; somente `APP_ENV=prd` com a flag `true` habilita leitura controlada, sem fallback. Isso não autoriza go-live, escrita ou execução sem credencial SELECT-only confirmada externamente.

## 4. Fonte funcional Protheus

- `FWACOM17`: referência confirmada para formar o universo de Naturezas do Gestor.
- `FWACOM04:retSaldo`: Limite Original.
- `FWACOM04:retSldPedidos` e `incluiPrev`: PC aberto.
- `FWACOM04:retSldTitulos`: NF entrada.
- `FWACOM04:retSldConting` e chamadas de `btnAvancar`: contingências.

Não inventar significados ou filtros ausentes. Antes de alterar regra financeira, localizar a regra equivalente no ADVPL ou comprová-la pelos dados HML.

## 5. Universo de Naturezas

Critérios implementados pelo `NaturezaRepository`:

1. cadastro SED ativo da filial;
2. `ED_ZPAINEL = '02'`, centralizado como `GESTOR_COMPRAS_PAINEL = "02"`;
3. existência de relacionamento SE7 ativo para a mesma filial/Natureza;
4. a existência na SE7 é histórica, sem filtro pelo ano/mês consultado;
5. descrição proveniente da SED;
6. registros logicamente excluídos ignorados.

A SE7 usada nessa elegibilidade é distinta da leitura mensal do Limite Original. Dentro do universo, uma linha é gerada quando existe Limite, PC, NF ou Contingência no período. Movimentos fora do universo não criam linhas.

Na ET-020A, a união indiscriminada dos movimentos ampliou incorretamente o conjunto. Em setembro/2025, `5.000-350 — PUBLICIDADES, PUBLICACOES ETC` apareceu por uma NF de R$ 220,00 apesar de possuir `ED_ZPAINEL` vazio. A ET-021A restaurou o universo do `FWACOM17`: o retorno HML caiu de 129 para 52 Naturezas e `5.000-350` foi excluída. Não codificar 52; é um resultado dos dados.

## 6. Repositories e responsabilidades

| Componente | Repository | Origem | Regra principal |
|---|---|---|---|
| Catálogo | `NaturezaRepository` | SED + existência SE7 | universo painel `02`, histórico e ativo |
| (e) Lim Original | `LimiteRepository` | SE7 | coluna mensal do ano/período |
| (a) PC aberto | `PcAbertoRepository` | SZN + SC7 | soma `ZN_SALDO`; existe item com `C7_QUJE < C7_QUANT` e `C7_RESIDUO = ' '` |
| (b) NF entrada | `NfEntradaRepository` | SE2 + SEV | soma `EV_VALOR`; vencimento E2; situação diferente de `E`/`X`; `EV_IDENT = '1'` |
| (c)/(d) Contingências | `ContingenciaRepository` | SZR | soma `ZR_CONTING` por status |

Todos aplicam exclusão lógica. PC aberto não recalcula quantidade × preço. NF entrada não adiciona filtros por `E2_BAIXA`, `E2_SALDO` ou `E2_TIPO`. A consulta agregada de contingências não faz JOIN adicional.

Campos mensais SE7:

| Mês | Campo | Mês | Campo |
|---|---|---|---|
| Jan | `E7_VALJAN1` | Jul | `E7_VALJUL1` |
| Fev | `E7_VALFEV1` | Ago | `E7_VALAGO1` |
| Mar | `E7_VALMAR1` | Set | `E7_VALSET1` |
| Abr | `E7_VALABR1` | Out | `E7_VALOUT1` |
| Mai | `E7_VALMAI1` | Nov | `E7_VALNOV1` |
| Jun | `E7_VALJUN1` | Dez | `E7_VALDEZ1` |

## 7. Fórmulas

Colunas-base:

- `(a)` PC aberto;
- `(b)` NF entrada;
- `(c)` Contingência OK: `ZR_APROV = 'T'` e `ZR_REPROV <> 'T'`;
- `(d)` Contingência em aprovação: `ZR_APROV = 'F'` e `ZR_REPROV = 'F'`;
- `(e)` Lim Original.

```text
Gasto previsto = (a) + (b)
Saldo previsto = (e) - (a) - (b)
Saldo real     = (e) - (b)
```

`(c)` permanece visível e detalhável, mas é informativa e não participa de Saldo previsto, Saldo real ou percentual consumido. `(d)` também é informativa.

### Ajuste funcional atual — Limite Original como base financeira

`Lim Total` foi removido da tabela principal e das exportações. O Dashboard, os gráficos, a Atenção Gerencial e a Evolução Temporal usam diretamente `(e) Lim Original`. O percentual consumido é `NF Entrada / Lim Original * 100`, com estado `Sem limite` quando o limite é zero e há NF.

`Gasto Previsto` é uma coluna derivada da tabela principal e das exportações: `PC aberto + NF entrada`. Não inclui contingências nem Lim Original.

`(c) Contingência OK` continua visível e detalhável, mas não compõe mais nenhum cálculo financeiro de referência.

## 8. Estado da homologação

- ET-013 a ET-019: infraestrutura SQL, cinco repositories e serviço consolidado concluídos.
- ET-020: validação integrada SQL em HML ainda aguarda fechamento funcional.
- ET-020A: ampliação do conjunto base posteriormente parcialmente revertida/corrigida pela ET-021A.
- ET-020B: ativação SQL em HML concluída.
- ET-020C: navegação mensal dinâmica concluída.
- ET-021: filtros operacionais implementados; comparação HML x `FWACOM04` ainda em homologação manual.
- ET-021A: universo alinhado ao `FWACOM17`, tecnicamente concluído.
- ET-021B: consolidação documental deste handoff, concluída.
- ET-021B.1: saneamento da suíte backend, concluída sem alteração de código de produção.
- ET-021C: diagnóstico read-only do PC aberto, concluído com causa ainda não comprovada.
- ET-021D: habilitação técnica controlada de leitura em PRD, concluída; execução real não realizada por ausência de configuração PRD ativa e de confirmação externa da permissão SELECT-only.
- ET-021D.1: comparação real PRD aguardando execução; ainda faltam confirmação SELECT-only, health, conferência simultânea no FWACOM04 e runner controlado.
- ET-021D.2: configuração persistente e separada criada em `backend/.env.prd`, com flag `false`, sem conexão PRD.

O frontend possui seleção direta de mês/ano, navegação anterior/próxima, filtro local parcial e case-insensitive por código/descrição, tabela de nove colunas, barra de consumo, criticidade, loading, erro, retry e estado vazio. O filtro é preservado ao navegar e não faz API/SQL. As transições `12/2025 → 01/2026` e `01/2026 → 12/2025` foram validadas.

A ET-028 implementou a visualização Mensal/Semanal/Diária. Mensal preserva os resultados homologados. Semanal usa semanas de segunda a domingo e consulta somente a interseção com o mês atual; Diário consulta a data selecionada. Limite Original é proporcional por dias úteis de segunda a sexta do mês, sem feriados. PC aberto, NF Entrada, Contingência OK e Contingência em aprovação são valores reais por `ZN_VENCTO`, `E2_VENCTO` e `ZR_VENCTO`; Lim Total e saldos são recalculados sobre esses valores. O endpoint existente recebeu somente `inicio`/`fim` opcionais e PRD permanece read-only.

Correção técnica posterior: Semanal/Diário passaram a memorizar o intervalo e os hooks usam `inicio`/`fim` primitivos nas dependências. Isso evita recriar a identidade da consulta durante o próprio loading e abortar continuamente uma requisição válida; não altera regras financeiras ou o modo Mensal.

ET-029 — Busca adicional: **absorvida** pelo filtro local de Natureza da ET-021. ET-030 adicionou ordenação local crescente/decrescente para Natureza e as oito colunas financeiras, aplicada após o filtro e preservada em Mensal/Semanal/Diário. Não houve alteração de backend, API, SQL ou regras financeiras.

ET-031 adicionou exportação local da tabela consolidada em CSV e XLSX. Usa exatamente as linhas filtradas e ordenadas exibidas, preserva Mensal/Semanal/Diário e não chama a API. O XLSX usa a dependência frontend `xlsx`, com células financeiras numéricas; CSV usa BOM UTF-8, `;` e decimais pt-BR.

ET-032 refinou somente CSS responsivo: controles se reorganizam em telas intermediárias/pequenas, tabela continua com overflow horizontal restrito ao seu contêiner e o drawer ocupa a largura disponível no celular. Não houve mudança funcional, financeira ou de backend/API/SQL.

ET-033 criou a rota Dashboard e oito cards gerenciais derivados das mesmas linhas consolidadas do Gestor. O percentual consumido é `NF Entrada / Limite Total`, nulo quando o limite é zero. CSV/XLSX continuam sendo a análise tabular; gráficos permanecem fora do escopo.

ET-034 adicionou Recharts com três gráficos locais: Limite Total x PC aberto x NF Entrada, Top 10 por consumo (`NF Entrada / Limite Total`) e Top 10 menores Saldos Previstos. Limite zero/NF positiva recebe 100% visual para permanecer no ranking sem Infinity; limite zero/NF zero é omitido. Não há API, SQL ou cálculo financeiro novo.

Correção ET-034: os `ResponsiveContainer` passaram a ficar em viewports próprios com largura e altura CSS explícitas (260 px no gráfico amplo; 340 px nos Top 10), eliminando a dependência de dimensão implícita do container pai que deixava os gráficos sem área de desenho visível. DashboardCharts já estava montado no DashboardPage; regras, API, SQL e backend não foram alterados.

Ajuste visual ET-034: cards receberam ícones SVG locais e os três gráficos passaram a usar colunas verticais em uma grade de três colunas no desktop. A faixa inferior apenas resume percentual consumido, Naturezas acima de 100%, saldo previsto e contingência em aprovação, a partir das linhas já carregadas. Não houve alteração financeira, de backend, API ou SQL.

ET-035 evoluiu a faixa para Atenção Gerencial. Consumo crítico separa percentual acima de 100% de `Sem limite` quando Limite Total é zero com NF positiva; os demais indicadores detalham saldo previsto negativo, PC aberto e contingência em aprovação. Os quatro detalhes são filtrados, ordenados e exibidos localmente no drawer, sem chamadas adicionais de API. Backend, SQL e fórmulas permanecem inalterados.

ET-036 adicionou `GET /api/gestor/timeline`. O endpoint chama a composição mensal já homologada uma vez para cada mês de janeiro ao mês final e devolve os totais de Limite Total, NF Entrada e Saldo Previsto. O Dashboard usa essa série apenas para o gráfico de linhas mensal; semanal e diário usam o mês de seu contexto como limite. A chamada é abortável, isolada de loading/erro do Dashboard e não altera PRD read-only ou fórmulas.

ET-037 consolidou a cobertura automatizada sem criar funcionalidades. Foram adicionados testes de parâmetros inválidos e falha sanitizada da timeline, incluindo a seleção explícita de PRD; no frontend, a validação cobre endpoint, `AbortController` e as três séries do gráfico temporal. As suítes de detalhe, contingência, período, lint e build continuam parte da validação final.

## 9. Casos já comparados

### 4.000-350 — OLEO DE BARRAMENTO — setembro/2025

Correspondência observada: PC R$ 0,00; NF R$ 13.440,00; Contingência OK R$ 0,00; Contingência em aprovação R$ 0,00; Lim Original R$ 13.500,00; Saldo previsto e real R$ 60,00.

### 4.000-400 — OLEO SOLUVEL — setembro/2025

Amostra Web preservada: NF R$ 127.954,00; Lim Original R$ 105.000,00; Saldo previsto e real -R$ 22.954,00. Não há comparação completa de todas as colunas registrada.

### 4.000-460 — TAMBOREAMENTO — julho/2026

NF R$ 0,00, Contingência OK R$ 0,00, Contingência em aprovação R$ 489,58, Lim Original R$ 6.000,00 e Saldo real R$ 6.000,00 coincidem. A coluna `(d)` possui evidência positiva de correção nessa amostra.

## 10. Divergências abertas

Em `4.000-460 — TAMBOREAMENTO`, julho/2026:

- PC aberto Protheus: R$ 8.773,50;
- PC aberto Web: R$ 6.630,00;
- diferença: R$ 2.143,50;
- Saldo previsto Protheus: -R$ 2.773,50;
- Saldo previsto Web: -R$ 630,00.

O Saldo previsto diverge exatamente por causa do PC aberto. A ET-021C reproduziu R$ 6.630,00 no repository, no total SZN ativo bruto e no total elegível. Não existe saldo ativo excluído pelo `EXISTS`; a causa dos R$ 2.143,50 adicionais observados anteriormente no Protheus ainda não foi comprovada. Consulte `docs/pc-aberto-diagnostic.md`.

## 11. Decisões que não devem ser revertidas

- Preservar o universo SED ativo + painel `02` + existência histórica ativa na SE7.
- Não permitir que movimentos fora do universo criem linhas.
- Manter cinco consultas independentes em lote; não criar N+1 ou mega-query.
- Manter nomes físicos centralizados e fora do `GestorSqlService`.
- Manter `(d)` apenas informativa nas fórmulas atuais.
- Somar `ZN_SALDO` no PC aberto, sem recalcular quantidade × preço.
- Preservar os critérios confirmados de NF e contingências, sem filtros/joins extras.
- Manter DEV mock, HML read-only e PRD bloqueado por padrão; a exceção PRD exige opt-in explícito e permanece estritamente read-only.
- Não corrigir divergência financeira por suposição.

## 12. Próximo passo recomendado

> **PRÓXIMO PONTO DE INVESTIGAÇÃO:** divergência do PC aberto da Natureza `4.000-460 — TAMBOREAMENTO` em julho/2026. Protheus = R$ 8.773,50; Web = R$ 6.630,00; diferença = R$ 2.143,50. A coluna (d) Contingência em aprovação coincide em R$ 489,58.

A próxima ação deve repetir Protheus e Web no mesmo instante e disponibilizar o trecho literal de `FWACOM04:retSldPedidos`/`incluiPrev` se a divergência persistir. Não criar ET de correção antes de explicar a origem exata dos R$ 2.143,50.

## 13. Comandos úteis

```bash
# Backend DEV
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload

# Testes backend
pytest

# Validação HML (somente com backend/.env local e APP_ENV=hml)
python -m scripts.validate_gestor_hml --filial 0101 --ano <ANO> --mes <MES>

# Validação PRD (somente após opt-in e confirmação externa SELECT-only)
python -m scripts.validate_gestor_prd --filial <FILIAL> --ano <ANO> --mes <MES> [--natureza <CODIGO>]
python -m scripts.diagnose_pc_aberto_prd --filial <FILIAL> --ano <ANO> --mes <MES> --natureza <CODIGO>

# Frontend
cd ../frontend
npm run dev
node scripts/validate-period.mjs
npm run lint
npm run build
```

## 14. Checklist antes de qualquer nova ET

1. Ler `README.md`.
2. Ler `docs/handoff.md`.
3. Ler `docs/roadmap.md`.
4. Ler `docs/business-rules.md`.
5. Ler `docs/database.md`.
6. Verificar as ETs já implementadas e o estado atual do código.
7. Não reverter decisões anteriores sem evidência funcional.
8. Não inventar regra Protheus.
9. Comparar com `FWACOM04`/`FWACOM17` quando houver divergência.
10. Usar HML para homologação normal; PRD somente no modo controlado da ET-021D.
11. Manter a flag PRD desabilitada por padrão e nunca executar sem confirmação externa de credencial SELECT-only.
12. Preservar consultas read-only.
13. Não armazenar secrets no Git, documentação ou logs.
14. Antes de corrigir divergência financeira, localizar a regra equivalente no ADVPL ou comprová-la pelos dados HML.

Os arquivos `backend/.env` (HML) e `backend/.env.prd` (PRD) são locais e ignorados. O loader lê somente `.env` por padrão; `.env.prd` deve ser carregado explicitamente em processo controlado. Não documentar seus valores ou connection strings completas. Os `.env.example` devem permanecer apenas com placeholders seguros.

## 15. Validação das ET-021B e ET-021B.1

Validação final executada em 26/08/2026:

- teste backend anteriormente falho, executado isoladamente: **aprovado**;
- backend completo: **198 aprovados**;
- validação frontend de período/filtro: **21 verificações aprovadas**;
- lint frontend: **aprovado**;
- build frontend: **aprovado**.

A causa da falha era uma expectativa desatualizada em `test_hml_queries_are_select_only_parameterized_and_close_cursor`. O double retorna zero colunas opcionais; portanto, o comportamento comprovado desse cenário é executar 8 operações: 4 inspeções de schema, 3 consultas detalhadas e 1 resumo obrigatório por `E2_VENCTO`. As duas operações que completariam 10 — resumos por `E2_VENCREA` e `E2_EMISSAO` — são condicionais à existência dessas colunas.

Código de produção preservado; teste atualizado para refletir o comportamento atual comprovado. ET-021B e ET-021B.1 estão **concluídas**. Isso não autoriza iniciar a investigação financeira do PC aberto.

O projeto ainda não possui repositório Git próprio por decisão atual. O versionamento será criado em etapa futura, antes da preparação para produção. A ausência de Git próprio não é defeito, pendência nem critério de conclusão deste handoff.

## 16. Validação da ET-021C

Executada em 26/08/2026:

- backend completo: **207 aprovados**;
- validação frontend de período/filtro: **21 verificações aprovadas**;
- lint frontend: **aprovado**;
- build frontend: **aprovado**.

Foram adicionados 9 testes exclusivamente para o runner diagnóstico HML-only. Nenhum código funcional foi alterado. A causa da diferença histórica de R$ 2.143,50 permanece não comprovada; os detalhes e a próxima evidência necessária estão em `docs/pc-aberto-diagnostic.md`.

## 17. Validação da ET-021D

A ET-021D adicionou a flag segura, a matriz explícita do provider e dois runners PRD separados. O endpoint continua retornando HTTP 503 sanitizado quando PRD está bloqueado e preserva `GestorResponse` quando o modo é habilitado. Não houve alteração de repository, query funcional, fórmula, schema ou frontend.

A suíte backend está em 229/229. O `.env` local foi inspecionado sem revelar valores: permanece em HML, a flag PRD está ausente e `DB_APPLICATION_INTENT_READ_ONLY=false`. Assim, nenhuma conexão ou consulta real em PRD foi tentada. O próximo passo operacional exige configuração externa PRD, flag explícita, confirmação do DBA de permissão somente `SELECT` e abertura do Protheus pelo usuário para comparação simultânea.

## 18. Validação da ET-021D.2

`backend/.env` permaneceu intacto e `backend/.env.prd` foi criado a partir dele. Somente `APP_ENV=prd`, `DB_NAME=PROTHEUS_PRODUCAO` e `GESTOR_PRD_READ_ONLY_VALIDATION=false` diferem conforme definido. Host, porta, credencial, driver, sufixo, timeouts, TLS e `ApplicationIntent` foram preservados sem exposição de valores sensíveis.

O arquivo PRD é coberto pela regra `.env.*` do `.gitignore` e não é carregado automaticamente. Nenhum health, `SELECT 1`, repository, service ou endpoint foi executado em PRD. A credencial é a mesma de HML conforme confirmação externa, mas sua permissão SELECT-only ainda precisa ser confirmada antes da ET-021D.1.

## 19. Validação da ET-021D.1 e ET-021D.2A

A continuidade da ET-021D.1 confirmou externamente a credencial PRD como somente consulta, aprovou o health `SELECT 1` e homologou `4.000-460 — TAMBOREAMENTO`, filial `0101`, julho/2026, entre Web PRD e FWACOM04 PRD: PC R$ 0,00; NF R$ 8.773,50; Contingência OK R$ 0,00; Contingência em aprovação R$ 489,58; Lim Original/Total R$ 6.000,00; saldos previsto/real -R$ 2.773,50. A divergência anterior era comparação HML × PRD, não defeito comprovado do repository.

A ET-021D.2A separou ambiente do processo de ambiente de dados e originalmente adotou HML inicial. Essa decisão inicial foi substituída pela ET-021D.2C; seleção explícita, confirmação manual para entrada em PRD, configurações isoladas e ausência de fallback permanecem protegidas.

Na troca, `useGestor` inclui ambiente, filial, ano, mês e retry na identidade, aborta a chamada anterior e limpa os dados. Período e filtro são preservados entre HML e PRD; entrada em DEV preserva agosto/setembro/outubro de 2025 ou retorna a setembro/2025. Topbar e seletor exibem explicitamente o ambiente dos dados.

Validação técnica de 26/08/2026: backend **238 aprovados**; frontend **32 verificações aprovadas**; lint e build aprovados. Nenhuma dependência foi adicionada, nenhum Git foi criado e não houve alteração de SQL funcional, repositories, universo de Naturezas ou fórmulas. PRD permanece read-only e esta entrega não é go-live.

Pendência: validação visual/manual do usuário. A próxima ET não deve iniciar automaticamente.

## 20. Validação da ET-021D.2B

Na ET-021D.2B, HML ainda era o ambiente inicial e o período deixou de ser setembro/2025 fixo. A ET-021D.2C substituiu somente a escolha do ambiente; `getCurrentGestorPeriod()` continua usando `Date#getFullYear()` e `Date#getMonth()` da data civil local. Em 27/08/2026, o resultado é agosto/2026. Não há UTC, relógio do backend, biblioteca de datas ou persistência.

Trocas HML ↔ PRD continuam preservando o período escolhido. Ao entrar em DEV, agosto/setembro/outubro de 2025 são preservados; qualquer outro período usa setembro/2025. Não existe memória separada por ambiente. Refresh agora redescobre o datasource e inicia PRD disponível com o mês civil corrente.

Validação técnica da ET-021D.2B: backend **238 aprovados**; frontend **50 verificações aprovadas**; lint e build aprovados. A afirmação histórica de que PRD nunca era inicial foi substituída explicitamente pela ET-021D.2C; PRD permanece read-only e fail-closed por configuração.

Pendência: validação visual/manual do usuário. A próxima ET não deve iniciar automaticamente.

## 21. Validação da ET-021D.2C

O endpoint `/api/gestor/environments` escolhe o primeiro datasource disponível na ordem PRD, HML e DEV. Nesta instalação controlada, retorna PRD. O frontend inicia sem ambiente definido, aguarda a resposta sanitizada e somente então monta AppShell, Topbar e Gestor; não há flash nem consulta HML antes de PRD. Falha na descoberta mantém estado neutro com retry. Falha posterior na consulta PRD não aciona fallback.

PRD inicial não exibe confirmação. A confirmação permanece obrigatória para seleção manual HML/DEV → PRD. Período atual, navegação, filtro, DEV, AbortController, retry, badge, barras e criticidade foram preservados. O backend financeiro, provider, settings, database, repositories, SQL, `GestorSqlService` e fórmulas não foram alterados.

Validação técnica: backend **240 aprovados**; frontend **53 verificações aprovadas**; lint e build aprovados. Nenhuma dependência foi adicionada. PRD continua exclusivamente read-only, a flag permanece `false` por padrão no código/exemplo e esta ET não representa go-live.

Pendência: validação visual/manual do usuário. A próxima ET não deve iniciar automaticamente.

## 22. ET-023 — abertura da Sprint 4 e detalhe financeiro

A Sprint 3 está formalmente concluída. A Sprint 4 — Evolução Funcional do Gestor — iniciou com o drill-down de PC aberto e NF entrada por Natureza. Valores consolidados diferentes de zero são botões semânticos; zero não é interativo. O drawer informa Natureza, período, ambiente e tipo, possui fechamento por botão, fundo e `Escape`, restaura foco e mantém rolagem interna.

`GET /api/gestor/details` exige `ambiente`, `filial`, `ano`, `mes`, `natureza` e `tipo=pc_aberto|nf_entrada`. O PC expõe pedido, vencimento e valor; a NF expõe documento, prefixo, parcela, fornecedor, loja, vencimento e valor. Nenhum nome de fornecedor ou campo não confirmado foi inferido. O backend soma os registros e compara com o agregado da mesma consulta funcional; vazio incompatível, Natureza divergente ou total diferente produz HTTP 503 sanitizado, sem fallback.

O detalhe é carregado somente após interação. Possui loading, erro, retry, `AbortController` e chave contra resposta obsoleta próprios. Trocas de ambiente, período ou filtro fecham o drawer. DEV gera detalhes determinísticos coerentes sem alterar os totais consolidados. HML e PRD continuam isolados por `Settings`; PRD permanece SELECT-only, sem escrita e sem go-live.

Validação técnica: backend **259 aprovados**; frontend **53 verificações aprovadas**; lint e build aprovados; nenhuma dependência adicionada. Em PRD read-only, filial `0101`, julho/2026, Natureza `4.000-460`, o consolidado de NF, o `total` do detalhe e a soma dos 2 registros retornaram exatamente **R$ 8.773,50**. A validação visual/manual continua pendente porque nenhum navegador estava conectado à automação; a ET-024 não deve iniciar automaticamente.

## 23. ET-023A — precisão monetária do drill-down de NF

Na validação manual da ET-023, `1.000-030 — EQUIPAMENTOS P/ MAQUINAS`, agosto/2026 em PRD, apresentava erro de invariância. O diagnóstico SELECT-only comprovou 1 grupo agregado e 9 registros detalhados da mesma Natureza. A execução da API produziu agregado bruto `28056.880000000005`; uma recontagem literal das mesmas 9 linhas produziu `28056.879999999997`; em ambos os casos o valor decimal em centavos e a soma detalhada eram `28056.88`. Essa variação confirma a não associatividade do `float`; não havia filtro, chave, período, cardinalidade, duplicidade ou registro perdido.

O metadado PRD confirmou `SEV.EV_VALOR` como `float(53)`. A causa foi classificada como **H — validação posterior à query afetada pela representação binária do campo financeiro**. A correção ficou em `NfEntradaRepository._to_decimal`: valores agregados e individuais são convertidos para `Decimal` e normalizados para centavos com `ROUND_HALF_UP` antes da invariância. Queries, regras financeiras, agregado funcional, frontend e PC aberto foram preservados.

Após a correção, em PRD read-only: `1.000-030` retornou 9 registros, consolidado/detalhe/soma em R$ 28.056,88; `1.000-050` preservou 2 registros de R$ 2.800,00 e R$ 12.000,00, total R$ 14.800,00; `4.000-460`, julho/2026, preservou 2 registros e R$ 8.773,50. ET-023 e ET-023A foram posteriormente homologadas manualmente e estão concluídas.

Validação técnica final da ET-023A: backend **260 aprovados**; lint e build aprovados; frontend preservado, sem dependências novas. A ET-023A foi posteriormente homologada manualmente.

## 24. ET-024 — acesso pela rede local

O frontend Vite está configurado com `host: '0.0.0.0'`, `port: 5193`, `strictPort: true` e proxy `/api` para `http://127.0.0.1:8000`. A base padrão do HTTP client é vazia, portanto o navegador usa URLs relativas e nunca interpreta `localhost:8000` como o computador cliente. Uma URL absoluta continua possível apenas por configuração frontend explícita.

O FastAPI não foi alterado e permanece em `127.0.0.1:8000`. CORS não foi ampliado: através do proxy, navegador e frontend usam o mesmo origin. Nenhuma regra de firewall foi criada, a porta `8000` não foi exposta e não houve mudança em ambientes, período, filtro, drill-down, repositories, queries ou fórmulas.

Validação no servidor: `http://localhost:5193`, `http://127.0.0.1:5193` e `http://10.211.2.67:5193` retornaram HTTP 200. Pelo IP LAN, `/api/gestor/environments` retornou os três ambientes com PRD default; o Gestor DEV retornou 20 Naturezas e o detalhe DEV respondeu corretamente. A escuta confirmou Vite em `10.211.2.67:5193` e loopback, e FastAPI somente em `127.0.0.1:8000`.

Por restrição de segurança da automação, o processo foi iniciado com listeners explícitos em `10.211.2.67` e `127.0.0.1`, comportamento equivalente e mais restrito que o bind amplo configurado. Em operação normal, `npm run dev` usa `0.0.0.0` conforme `vite.config.ts`. O IPv4 atual pode mudar sem reserva DHCP/IP fixo.

Status: **CONCLUÍDA E HOMOLOGADA MANUALMENTE EM LAN**. O usuário confirmou o acesso por outros computadores em `http://10.211.2.67:5193`.

## 25. ET-025 — evolução do detalhamento de NF Entrada / Títulos

A funcionalidade-base prevista originalmente para a ET-025 foi antecipada na ET-023. Esta etapa evoluiu o endpoint e o drawer existentes, sem criar rota, repository ou componente paralelo. O contrato de NF adiciona `fornecedorNome` e `emissao`; código, loja e todos os campos anteriores permanecem. Nome ausente usa fallback visual `—`. O contrato de PC aberto não mudou.

O schema real de HML e PRD confirmou SA2 com `A2_FILIAL`, `A2_COD`, `A2_LOJA`, `A2_NOME` e exclusão lógica, além de `E2_EMISSAO` e `E2_TIPO` na SE2. O nome é recuperado na mesma query de detalhe por `LEFT JOIN` da SA2 ativa em `A2_FILIAL = LEFT(E2_FILIAL, 2)`, código e loja. `E2_TIPO` foi omitido porque sua existência física não comprovou utilidade funcional. Não há N+1.

A query agregada, os joins SE2/SEV, filtros, universo financeiro e fórmulas não foram alterados. A normalização de `EV_VALOR float(53)` para `Decimal('0.01')` com `ROUND_HALF_UP` permanece. O detalhe passou a ordenar por vencimento, documento, prefixo, parcela, fornecedor e loja.

Validação SELECT-only: HML `4.000-350`, setembro/2025, preservou 1 título e R$ 13.440,00, com nome e emissão. Em PRD, `1.000-030` preservou 9 títulos e R$ 28.056,88; `1.000-050`, 2 títulos de R$ 2.800,00 e R$ 12.000,00, total R$ 14.800,00; `4.000-460`, julho/2026, 2 títulos e R$ 8.773,50. Todos tiveram correspondência cadastral máxima 1 por título, sem perdas ou duplicação. A auditoria agregada da filial cadastral também retornou zero chaves ativas fornecedor+loja duplicadas em HML e PRD.

Validação técnica final: backend **261 aprovados**; frontend **53 verificações existentes + 19 específicas da ET-025**; lint e build aprovados; nenhuma dependência adicionada. Acesso LAN preservado em `http://10.211.2.67:5193`. A ET-026 foi iniciada somente após a solicitação explícita subsequente.

## 26. ET-026 — detalhamento de Contingências por Natureza

O endpoint e o drawer existentes foram ampliados com `contingencia_ok` e `contingencia_aprovacao`. Na tabela principal, os valores não zero de `(c)` e `(d)` seguem o mesmo padrão de botão de PC/NF; zero permanece texto e não consulta a API. O drawer mostra pedido, item, vencimento, usuário, status e valor, preservando contexto, quantidade, total, loading, erro, retry, cancelamento, foco e `Escape`.

A origem funcional permanece exclusivamente SZR. Ambas as categorias usam filial, `ZR_VENCTO LIKE AAAAMM%`, Natureza, `D_E_L_E_T_=''` e `ZR_CONTING`. OK aplica `ZR_APROV='T'` e `ZR_REPROV<>'T'`; em aprovação aplica `ZR_APROV='F'` e `ZR_REPROV='F'`. O schema de HML e PRD confirmou `ZR_CONTING float(53)`, agora normalizado no agregado e no detalhe para `Decimal('0.01')` com `ROUND_HALF_UP`. As fórmulas não mudaram e `(d)` continua informativa.

Validações SELECT-only: HML OK `1.000-030`, setembro/2025, 4 registros e R$ 13.186,84; HML aprovação `4.000-460`, agosto/2026, 1 registro e R$ 489,58. Em PRD, o caso OK do mês atual foi `1.000-050 — RETROFITTING`, agosto/2026, 1 registro e R$ 13.733,94; o caso obrigatório `4.000-460 — TAMBOREAMENTO`, julho/2026, preservou 1 registro e R$ 489,58. Em todos, agregado e soma detalhada coincidiram exatamente.

As regressões PRD de NF permaneceram: `1.000-030` com 9/R$ 28.056,88, `1.000-050` com 2/R$ 14.800,00 e `4.000-460` com 2/R$ 8.773,50, todos com nome do fornecedor e emissão. PC aberto, cinco consultas do carregamento principal, ambientes, período, filtro e LAN foram preservados.

Validação técnica final: backend **273 aprovados**; frontend **53 verificações existentes + 19 da ET-025 + 22 da ET-026**; lint e build aprovados; nenhuma dependência adicionada. Sprint 4 permanece em andamento; a ET-027 foi iniciada somente após a solicitação explícita subsequente.

## 27. ET-027 — refinamento da Interface de Detalhes

A interface-base prevista para esta etapa havia sido antecipada pela ET-023. A ET-027 reutilizou integralmente o drawer existente e refinou a experiência dos quatro tipos: PC aberto, NF entrada, Contingência OK e Contingência em aprovação. O cabeçalho passou a apresentar em níveis distintos o título `DETALHAMENTO FINANCEIRO`, o tipo amigável, o código e a descrição da Natureza, o mês/ano e o ambiente DEV/HML/PRD, sem expor nomes técnicos.

O resumo agora destaca quantidade de registros e total financeiro em áreas próprias. As tabelas preservam exatamente os campos existentes, datas em `DD/MM/AAAA` e valores em moeda brasileira, com colunas monetárias à direita, larguras coerentes, cabeçalho visualmente distinto e sticky, linhas mais legíveis e overflow vertical/horizontal restrito ao drawer e à viewport.

Loading, erro, retry, botão fechar, `Escape`, foco inicial e restauração de foco, `AbortController`, chave contra resposta obsoleta e o comportamento de zero não clicável foram preservados. Não houve alteração de backend, endpoint, contrato, repository, `GestorSqlService`, SQL, invariância, normalização Decimal, fórmulas, ambientes, período, filtro ou mocks financeiros. Nenhuma dependência foi adicionada.

Validação técnica final: frontend **53 verificações de período + 19 de NF + 22 de contingências + 26 específicas da ET-027**; lint e build aprovados. O smoke DEV pelo proxy validou os quatro tipos com quantidade, total e soma compatíveis com o consolidado, sem consulta real HML/PRD. A suíte backend não foi reexecutada porque o backend não mudou e permanece no último estado aprovado de **273/273**. O acesso LAN foi preservado em `http://10.211.2.67:5193`.

**PENDENTE DE VALIDAÇÃO VISUAL MANUAL:** nenhum navegador estava conectado à automação para inspecionar cabeçalho, resumo, sticky header e overflow dos quatro tipos. A ET-028 foi concluída depois como estrutura de granularidade; não iniciar ET-029 automaticamente.
