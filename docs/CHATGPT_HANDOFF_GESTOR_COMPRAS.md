# CHATGPT HANDOFF --- GESTOR DE COMPRAS

**Data do checkpoint:** 31/08/2026\
**Projeto:** Gestor de Compras Web --- substituição/evolução da rotina
Protheus/Fastwork `FWACOM04`\
**Workspace local:** `C:\Projetos\Gestão Compras`

> Documento de handoff para continuar o projeto em outra conta/conversa
> do ChatGPT. Leia também os arquivos atuais `README.md`,
> `docs/handoff.md` e `docs/roadmap.md`. Antes de alterar algo, valide o
> estado real do workspace e preserve tudo que já foi homologado.

## 1. Modo de trabalho

-   Trabalhar em português.
-   Desenvolvimento por ETs numeradas e sequenciais.
-   Antes de uma nova ET, verificar o que já foi implementado/aprovado
    para evitar regressões.
-   Prompts para Codex devem ser entregues em **um único bloco completo,
    pronto para copiar/colar**.
-   Não fragmentar prompts, scripts ou queries.
-   Não iniciar a próxima ET automaticamente.
-   Se faltar IP, porta, banco, servidor, caminho ou outro dado
    ambiental, perguntar ao usuário; não usar placeholders.
-   Não usar Git ainda. `git init`, commit e push somente quando
    autorizado.
-   Manter README, handoff e roadmap atualizados.
-   A partir da ET-028, usar ETs **pequenas e cirúrgicas** para
    economizar créditos do Codex.
-   Não mandar o Codex reler o projeto inteiro ou repetir
    consultas/testes de áreas não alteradas.
-   Definir regras funcionais no ChatGPT antes de enviar implementação
    ao Codex.

## 2. Arquitetura e rede

Frontend: - React + TypeScript + Vite. - Porta LAN `5193`. - URL
homologada: `http://10.211.2.67:5193` - Proxy relativo `/api`.

Backend: - Python + FastAPI. - Listener `127.0.0.1:8000`. - Backend não
deve ser exposto diretamente na LAN.

Máquina: - IPv4 `10.211.2.67`. - Acesso por outros computadores da LAN
já homologado. - Não criar automaticamente regra de firewall, túnel ou
exposição à Internet.

## 3. Ambientes e SQL Server

HML: - Servidor: `SRVFASTSQL` - Banco: `PROTHEUS_2510_HML` -
Configuração: `backend/.env`

PRD: - Servidor: `SRVFASTSQL` - Banco: `PROTHEUS_PRODUCAO` -
Configuração: `backend/.env.prd` - PRD somente leitura. - Feature flag:
`GESTOR_PRD_READ_ONLY_VALIDATION`

Driver: - `ODBC Driver 17 for SQL Server`

Filial: - `0101`

Tabelas relevantes: - `SC7010` - `SE2010` - `SE7010` - `SED010` -
`SEV010` - `SZN010` - `SZR010` - SA2 como cadastro de fornecedor.

Nunca registrar usuário/senha de banco na documentação. Credenciais
ficam apenas nos `.env` locais.

## 4. Seleção de ambiente

Separação entre: - `APP_ENV` do processo; - `GestorDataEnvironment`:
`dev`, `hml`, `prd`.

Frontend possui seletor DEV/HML/PRD.

Regras: - DEV usa `MockGestorService`. - HML usa `.env`. - PRD usa
`.env.prd`. - Sem fallback silencioso entre ambientes. - PRD
read-only. - `GET /api/gestor/environments` -
`GET /api/gestor?ambiente=...`

Período inicial usa mês/ano civil local atual (`new Date()`,
`getFullYear()`, `getMonth()+1`), não UTC.

## 5. Regras originais --- FWACOM04

A aplicação busca paridade com `FWACOM04.prw`.

Limite Original --- `retSaldo`: - SE7; - filial, ano e Natureza; -
campos mensais `E7_VALJAN1` até `E7_VALDEZ1`.

PC aberto --- `retSldPedidos`: - SZN; - existência correspondente em SC7
aberto e não-resíduo.

NF Entrada --- `retSldTitulos`: - SE2 + SEV; - período por
`E2_VENCTO`; - Natureza `EV_NATUREZ`; - `EV_SITUACA NOT IN ('E','X')`; -
`EV_IDENT='1'`.

Contingências --- `retSldConting`: - SZR.

Contingência OK: - `ZR_APROV='T'` - não rejeitada.

Contingência em aprovação: - `ZR_APROV='F'` - `ZR_REPROV='F'`.

## 6. Fórmulas homologadas

-   `(a)` PC aberto
-   `(b)` NF entrada
-   `(c)` Contingência OK
-   `(d)` Contingência em aprovação
-   `(e)` Lim Original

`Lim Total = Lim Original + Contingência OK`

`Saldo previsto = Lim Total - PC aberto - NF entrada`

`Saldo real = Lim Total - NF entrada`

**Contingência em aprovação é informativa e NÃO entra nas fórmulas.**

Não alterar sem decisão funcional explícita.

## 7. Universo de Naturezas

Regra corrigida para reproduzir Fastwork: - SED ativa; - existência
histórica em SE7; - painel Compras `ED_ZPAINEL='02'`.

O `FWACOM17.prw` usa SED + SE7 sem exigir registro SE7 especificamente
no ano selecionado.

Busca/filtro de Natureza já foi antecipada.

## 8. Detalhamento financeiro

Endpoint: `GET /api/gestor/details`

Tipos: - `pc_aberto` - `nf_entrada` - `contingencia_ok` -
`contingencia_aprovacao`

Zero no consolidado permanece não clicável.

Drawer preserva: - loading; - erro/retry; - fechamento/Escape; - foco e
restauração; - AbortController; - proteção contra resposta obsoleta; -
quantidade; - total; - tabela específica.

NF Entrada inclui: - documento, prefixo, parcela, fornecedor, nome do
fornecedor, loja, emissão, vencimento, valor. - Financeiro SE2 + SEV. -
Fornecedor SA2 ativa. - Join: `A2_FILIAL = LEFT(E2_FILIAL, 2)`,
`A2_COD = E2_FORNECE`, `A2_LOJA = E2_LOJA`. - Valores normalizados com
`Decimal('0.01')` + `ROUND_HALF_UP`.

Contingências: - SZR. - Campos: pedido, item, vencimento, usuário,
status, valor. - `ZR_CONTING` float(53), com normalização
Decimal/ROUND_HALF_UP.

Casos PRD já homologados e que não precisam ser repetidos sem
necessidade: - NF `1.000-030`, Ago/2026: 9 registros, R\$ 28.056,88. -
NF `1.000-050`: 2 registros, R\$ 14.800,00. - NF `4.000-460`, Jul/2026:
2 registros, R\$ 8.773,50. - Contingência em aprovação `4.000-460`,
Jul/2026: 1 registro, R\$ 489,58.

## 9. Estado das ETs

Sprint 3: concluída.

Sprint 4: - ET-023 --- detalhe financeiro por Natureza:
CONCLUÍDA/HOMOLOGADA. - ET-023A --- correção de precisão float:
CONCLUÍDA/HOMOLOGADA. - ET-024 --- acesso LAN: CONCLUÍDA/HOMOLOGADA. -
ET-025 --- evolução do detalhe de NF: CONCLUÍDA/HOMOLOGADA. - ET-026 ---
detalhes das contingências: CONCLUÍDA/HOMOLOGADA. - ET-027 ---
refinamento da interface de detalhes: **CONCLUÍDA E HOMOLOGADA
MANUALMENTE**.

ET-027: - backend não alterado; - endpoints/contratos/repositories não
alterados; - drawer reutilizado; - cabeçalho amigável; - Natureza,
mês/ano e ambiente visíveis; - resumo registros/total; - tabela
refinada; - sticky header; - overflow controlado; - DD/MM/AAAA e moeda
brasileira; - loading/erro/retry e Escape/foco preservados; - zero não
clicável; - regras financeiras/invariância preservadas; - acesso LAN
preservado; - nenhuma dependência nova; - validação visual manual
aprovada pelo usuário.

Último estado conhecido: - backend: 273/273 testes aprovados (não
reexecutado na ET-027, pois não mudou); - frontend: 53 validações de
período + 19 NF + 22 contingências + 26 ET-027 aprovadas; - lint
aprovado; - build aprovado.

## 10. Ponto exato de retomada

**NÃO iniciar automaticamente a ET-028.**

Nova necessidade funcional a desenhar primeiro:

### Visualização Mensal / Semanal / Diário

O modo mensal atual deve ser preservado.

Quando selecionar semana ou dia, o limite não deve ser comparado
diretamente ao limite mensal inteiro. O limite deverá ser proporcional
ao período selecionado, **respeitando dias úteis**, e a barra de consumo
deverá utilizar esse limite proporcional.

Exemplo apenas conceitual, ainda não aprovado como regra final:

-   limite mensal = R\$ 22.000;
-   mês = 22 dias úteis;
-   limite diário = R\$ 1.000;
-   semana com 5 dias úteis = limite proporcional de R\$ 5.000.

A barra compararia o consumo da semana/dia com o respectivo limite
proporcional.

### Regra ainda NÃO fechada

Antes de criar prompt para Codex, decidir com o usuário:

1.  Dia útil significa apenas segunda a sexta ou também excluir
    feriados?
2.  Se houver feriados: nacional, estadual, municipal e/ou calendário da
    empresa?
3.  Qual campo/data determina a inclusão diária/semanal de PC aberto?
4.  Qual campo/data determina a inclusão diária/semanal de NF Entrada?
5.  Qual campo/data determina a inclusão diária/semanal das
    contingências?
6.  Como tratar semana que atravessa dois meses?
7.  Como proporcionalizar Lim Original, Contingência OK e Lim Total?
8.  Como ficam Saldo previsto e Saldo real no semanal/diário?
9.  Como calcular percentual/cores da barra?
10. Como será a navegação Mensal \| Semanal \| Diário?
11. Como tratar períodos sem dias úteis?
12. Quais alterações de query/endpoints são realmente necessárias?

**Não deixar o Codex decidir essas regras de negócio.**

O mensal atual é referência homologada e não pode sofrer regressão
silenciosa.

## 11. Roadmap após a retomada

-   ET-028 --- originalmente filtros adicionais; reavaliar/redefinir
    para a necessidade de granularidade temporal.
-   ET-029 --- busca adicional; parte da busca de Natureza já foi
    antecipada.
-   ET-030 --- ordenação.
-   ET-031 --- exportação.
-   ET-032 --- responsividade.
-   ET-033 --- refinamento visual geral.
-   ET-034 --- testes automatizados.
-   ET-035 --- integração.
-   ET-036 --- desempenho.
-   ET-037 --- homologação de usuários.
-   ET-038 --- correções.
-   ET-039 a ET-044 --- preparação para produção.
-   ET-045 a ET-048 --- deploy, validação, monitoramento e encerramento.

Se uma ET já tiver sido absorvida, documentar isso em vez de criar
funcionalidade artificial apenas para cumprir a numeração.

## 12. Primeira mensagem sugerida na nova conta

Após anexar: - `CHATGPT_HANDOFF_GESTOR_COMPRAS.md` - `README.md` -
`handoff.md` - `roadmap.md`

enviar:

> Este é o projeto Gestor de Compras que eu estava desenvolvendo em
> outra conta. Leia integralmente os quatro arquivos anexados e assuma o
> projeto a partir do estado documentado. Não implemente nada e não gere
> prompt para Codex ainda. Primeiro apresente o estado atual do projeto,
> ETs concluídas, regras financeiras que não podem sofrer regressão,
> pendências reais e o ponto exato de retomada. Depois vamos definir
> juntos a regra funcional da ET-028 para visualização
> Mensal/Semanal/Diária e proporcionalização por dias úteis.

## 13. Regra principal para o próximo agente

**Preservar tudo que já está homologado.**

-   Não reinterpretar regra financeira sem fonte ou decisão explícita.
-   Não executar ET só porque aparece no roadmap.
-   Verificar se o escopo já foi antecipado.
-   Não deixar Codex decidir regra de negócio indefinida.
-   Manter próximas ETs curtas para reduzir consumo de créditos.
