# Regras de negócio conhecidas

Este documento registra as regras funcionais já confirmadas e atualmente reproduzidas. Os fontes ADVPL `FWACOM04.prw` e `FWACOM17` são referências de comportamento; não devem ser convertidos literalmente para JavaScript, TypeScript ou Python.

## Chave de apuração

O Gestor calcula os valores para cada combinação de:

`FILIAL + NATUREZA + ANO + MÊS`

## Componentes

### (a) PC aberto

- Origem principal: `SZN` + `SC7`.
- Representa `SUM(ZN_SALDO)` por Natureza para parcelas com `ZN_VENCTO` no período `AAAAMM`.
- SZN é relacionada à SC7 por filial e número do pedido.
- O pedido participa quando existe item SC7 ainda não totalmente atendido (`C7_QUJE < C7_QUANT`) e sem resíduo (`C7_RESIDUO` vazio).
- Pedidos totalmente recebidos, marcados como resíduo ou logicamente excluídos não participam.
- No fluxo que alimenta SZN, o saldo inicial é `(C7_QUANT - C7_QUJE) × C7_PRECO`, distribuído pela condição de pagamento; a leitura do Gestor soma o `ZN_SALDO` já armazenado, sem recalculá-lo.
- A consulta agregada do fonte não relaciona `ZN_ITEPED`; ela verifica a existência de item aberto no pedido e soma as parcelas SZN aplicáveis por Natureza.

### (b) NF entrada

- Origem principal: `SE2` + `SEV`.
- Regra confirmada em `FWACOM04:retSldTitulos`: representa `SUM(EV_VALOR)` agrupado por `EV_NATUREZ`.
- O período é determinado por `E2_VENCTO LIKE AAAAMM%`, e não pela emissão.
- SE2 e SEV são relacionadas por filial, número, prefixo, parcela, fornecedor/cliente e loja.
- O rateio participa quando `EV_SITUACA NOT IN ('E', 'X')` e `EV_IDENT = '1'`.
- Registros logicamente excluídos em SE2 ou SEV não participam.
- O método agregado não relaciona nem filtra tipo de título e não consulta saldo, baixa, moeda, impostos ou um campo adicional de cancelamento.
- Consequentemente, título baixado ou parcialmente baixado não recebe tratamento específico: o `EV_VALOR` armazenado é somado quando as condições confirmadas são satisfeitas.
- Os rótulos funcionais dos códigos de situação `E` e `X` não foram inferidos; está confirmado apenas que o fonte os exclui.
- Apesar do nome do componente, a rotina utiliza títulos financeiros e o rateio por natureza.

### (c) Contingência OK

- Origem: `SZR`.
- Regra confirmada em `FWACOM04:retSldConting` e na chamada de `btnAvancar` com `lAprovado = .T.`.
- Representa `SUM(ZR_CONTING)` por `ZR_NATUREZ` para `ZR_APROV = 'T'` e `ZR_REPROV <> 'T'`.
- O período é `ZR_VENCTO LIKE AAAAMM%` e a filial vem de `ZR_FILIAL`.
- Registros SZR logicamente excluídos não participam.
- O cálculo agregado não relaciona SC7 ou SA2 e não utiliza `ZR_VALOR`, pedido, item, fornecedor, produto, centro de custo, moeda ou rateio externo.

### (d) Contingência em aprovação

- Origem: `SZR`.
- Regra confirmada em `FWACOM04:retSldConting` e na chamada de `btnAvancar` com `lEmAprovacao = .T.`.
- Representa `SUM(ZR_CONTING)` por `ZR_NATUREZ` para `ZR_APROV = 'F'` e `ZR_REPROV = 'F'`.
- O período é `ZR_VENCTO LIKE AAAAMM%` e a filial vem de `ZR_FILIAL`.
- Registros SZR logicamente excluídos e combinações de status fora do critério não participam.
- Não participa dos cálculos de saldo.

No detalhamento do próprio `FWACOM04`, `ZR_APROV = 'T'` é apresentado como aprovado, `ZR_APROV = 'F'` com `ZR_REPROV = 'F'` como aguardando aprovação e as demais combinações como reprovadas. SC7 e SA2 são usadas somente nesse detalhamento para pedido/item e fornecedor; não fazem parte das somas do painel.

### (e) Limite Original

- Origem: `SE7`.
- Representa o orçamento mensal da natureza.
- É identificado por filial, Natureza, ano de quatro dígitos e mês.
- O campo mensal é escolhido entre `E7_VALJAN1`, `E7_VALFEV1`, `E7_VALMAR1`, `E7_VALABR1`, `E7_VALMAI1`, `E7_VALJUN1`, `E7_VALJUL1`, `E7_VALAGO1`, `E7_VALSET1`, `E7_VALOUT1`, `E7_VALNOV1` e `E7_VALDEZ1`.
- Conforme `FWACOM04:retSaldo`, a leitura não filtra `E7_MOEDA`. Se isso produzir mais de um registro para a mesma Natureza/período, a aplicação web sinaliza ambiguidade em vez de escolher ou agregar valores silenciosamente.
- Zero ou `NULL` em registro existente representa `Decimal("0")`; ausência de registro permanece distinta de zero.

O `LimiteRepository` retorna somente o Limite Original. O `GestorSqlService` combina esse valor com a Contingência OK para calcular Lim Total e saldos; repositories não calculam fórmulas entre componentes.

### Dados complementares

- Naturezas: `SED`.
- Fornecedor nos detalhes: `SA2`.

### Naturezas exibíveis no Gestor

O universo permitido do Gestor de Compras é definido pelo `NaturezaRepository`: cadastro SED ativo da filial, `ED_ZPAINEL = '02'` e existência de ao menos um registro SE7 ativo para a mesma filial/Natureza. A existência na SE7 é histórica e não recebe filtro de ano ou mês nessa etapa. A referência funcional é a formação da lista do Gestor original em `FWACOM17`.

Dentro desse universo, uma Natureza gera linha quando possui Limite, PC aberto, NF entrada ou Contingência no período. Ausência de Limite no ano/mês não a exclui: o Limite Original é zero e os demais valores e saldos são calculados normalmente. Movimentos de Naturezas fora do painel não criam linhas e não são, isoladamente, inconsistências.

Registros logicamente excluídos em SED não pertencem ao catálogo. Código e descrição são normalizados apenas para remover preenchimento externo típico de campos CHAR.

O valor `ED_ZPAINEL = '02'` foi confirmado em HML contra as Naturezas exibidas pelo Gestor original e é centralizado semanticamente como painel do Gestor de Compras.

### Regressão ET-020A e correção ET-021A

Na ET-020A, o conjunto base foi ampliado para a união das Naturezas encontradas nos movimentos financeiros. Isso fez `5.000-350 — PUBLICIDADES, PUBLICACOES ETC` aparecer em setembro/2025 por causa de uma NF entrada de R$ 220,00, embora seu `ED_ZPAINEL` esteja vazio. Naturezas válidas observadas, como `4.000-350`, `4.000-400`, `5.000-150` e `5.000-400`, possuem painel `02`.

A ET-021A restaurou o universo funcional descrito acima. Em HML, setembro/2025 passou de 129 para 52 Naturezas e `5.000-350` deixou de aparecer. O número 52 é consequência dos dados e da elegibilidade, não deve ser codificado. A SE7 usada para confirmar participação histórica no universo não se confunde com a consulta mensal do `LimiteRepository`.

## Fórmulas confirmadas

```text
LIMITE TOTAL = (e) Limite Original + (c) Contingência OK

SALDO PREVISTO = (e) Limite Original
                + (c) Contingência OK
                - (a) PC aberto
                - (b) NF entrada

SALDO REAL = (e) Limite Original
             + (c) Contingência OK
             - (b) NF entrada
```

A contingência em aprovação `(d)` não entra nos cálculos dos saldos.

Desde a ET-019, essas fórmulas também são aplicadas pelo `GestorSqlService`. A ET-021A corrigiu a regressão da ET-020A: a união financeira é intersectada com o universo permitido do `NaturezaRepository`. Ausência de componente financeiro é zero; códigos vazios e duplicidades continuam sendo inconsistências.

## Alerta visual

Uma linha é considerada crítica quando pelo menos uma destas condições for verdadeira:

```text
SALDO PREVISTO < 0
ou
LIMITE TOTAL < 0
```

Esta regra é independente das faixas da barra de consumo. Em particular, `SALDO PREVISTO = 0` representa 100% de comprometimento, mas não torna a linha crítica por si só.

## Barra de consumo

A barra representa o comprometimento utilizado no Saldo Previsto:

```text
CONSUMO = (a) PC aberto + (b) NF entrada

PERCENTUAL DE CONSUMO = CONSUMO / LIMITE TOTAL × 100
```

A Contingência OK já compõe o Limite Total e não é somada novamente ao consumo. A Contingência em aprovação não entra no Limite Total, no Saldo Previsto nem no consumo.

Faixas de apresentação:

- 0% a 69%: verde, faixa confortável;
- 70% a 89%: amarelo, atenção;
- 90% a 99%: laranja, próximo do limite;
- exatamente 100%: âmbar/laranja forte, limite totalmente comprometido;
- acima de 100%: vermelho, limite excedido.

O percentual textual pode ultrapassar 100%, mas a largura visual da barra é limitada ao trilho. A classificação utiliza o percentual real antes do arredondamento de apresentação. Se o Limite Total for zero e o consumo também for zero, a apresentação é `0% utilizado`. Se a base for zero e houver consumo, a apresentação determinística é `100%+ utilizado`, como limite excedido, sem produzir `Infinity` ou `NaN`.

Exatamente 100% utilizado, por si só, não torna uma linha crítica: representa o limite totalmente comprometido e Saldo Previsto igual a zero. A criticidade da linha continua dependendo exclusivamente de `SALDO PREVISTO < 0` ou `LIMITE TOTAL < 0`.

## Funcionalidades previstas

- Dashboard mensal com Natureza, PC aberto, NF entrada, Contingência OK, Contingência em aprovação, Limite Original, Limite Total, Saldo Previsto e Saldo Real.
- Navegação entre mês anterior e próximo mês.
- Drill-down de pedidos de compra, notas/títulos e contingências.
- Filtros por filial, período, natureza e situação.
- Exportação e indicadores futuros.

## Navegação mensal por ambiente

Em HML e PRD, o período inicial do Gestor é o mês civil atual obtido pela data local do navegador no carregamento da página. O valor não é persistido nem recalculado durante navegação, retry ou troca de ambiente. O rótulo visual segue o formato `Mês / Ano`.

O ambiente de dados inicial é PRD quando o backend confirma sua disponibilidade. Se PRD estiver indisponível antes da primeira consulta, usa-se HML e depois DEV. Essa escolha de disponibilidade não é fallback financeiro: erro durante consulta PRD permanece erro PRD.

- Em DEV, a navegação permanece limitada ao mock de agosto, setembro e outubro de 2025. O botão anterior é desabilitado em agosto e o próximo em outubro.
- Em HML, os controles avançam ou retrocedem um mês por vez, inclusive entre dezembro e janeiro, no intervalo global de janeiro de 2000 a dezembro de 2100.
- Em PRD, ambos os controles permanecem bloqueados.

Um período HML sem ocorrências é um resultado válido: a tela apresenta o estado vazio e `0 naturezas`, sem convertê-lo em erro.

## Filtros operacionais

O filtro de período possui granularidade exclusivamente mensal. A seleção direta de mês/ano compartilha o mesmo estado controlado da `GestorPage` com os botões anterior e próximo; não existem datas diárias nem intervalos.

O filtro de Natureza pesquisa parcialmente código ou descrição, sem diferenciar maiúsculas e minúsculas e ignorando espaços externos da entrada. Ele atua somente sobre as linhas já carregadas em memória, preserva a ordem recebida, não executa nova consulta e não altera valores, fórmulas ou `quantidade` da resposta da API. Ao trocar o período, o texto pesquisado é preservado.

Período sem dados e pesquisa sem resultados possuem mensagens e contadores distintos.

## Ambiente de dados

A seleção DEV/HML/PRD não altera nenhuma regra financeira. DEV conserva as fixtures de 18/20/22 Naturezas; HML e PRD executam os mesmos cinco repositories e a mesma composição, variando exclusivamente o objeto de configuração da conexão. Período e filtro de Natureza são preservados entre HML e PRD. Ao entrar em DEV com período fora de agosto, setembro ou outubro de 2025, aplica-se setembro/2025 sem consultar SQL.

## Detalhamento por Natureza — ET-023 e ET-025

Somente `(a) PC aberto` e `(b) NF entrada` admitem drill-down nesta etapa, e somente quando o valor consolidado é diferente de zero. Para PC, cada registro corresponde aos campos confirmados de SZN: pedido, vencimento e contribuição `ZN_SALDO`; a elegibilidade continua exigindo pedido com item aberto/não residual em SC7. Para NF, cada registro usa as chaves confirmadas de SE2/SEV: documento, prefixo, parcela, fornecedor, loja, emissão, vencimento e `EV_VALOR`, além do nome cadastral da SA2.

O enriquecimento cadastral da ET-025 usa SA2 ativa pela chave comprovada `A2_FILIAL = LEFT(E2_FILIAL, 2)`, `A2_COD = E2_FORNECE` e `A2_LOJA = E2_LOJA`. É um `LEFT JOIN`: cadastro ausente ou logicamente excluído não elimina o título, não altera o valor e resulta no fallback visual `—` para o nome. O código e a loja permanecem expostos. Natureza não é repetida na grade porque já contextualiza o drawer; `E2_TIPO`, embora existente no schema, não foi incluído sem evidência de utilidade funcional.

Na ET-026, `(c)` e `(d)` passaram a admitir drill-down independente no mesmo endpoint/drawer. Contingência OK contém exclusivamente SZR ativa com `ZR_APROV='T'` e `ZR_REPROV<>'T'`; Contingência em aprovação contém exclusivamente `ZR_APROV='F'` e `ZR_REPROV='F'`. Filial, competência por `ZR_VENCTO`, Natureza e `ZR_CONTING` são idênticos ao agregado. Soma das linhas, total do detalhe e coluna consolidada devem coincidir exatamente após normalização monetária.

O detalhe não muda as fórmulas: somente `(c)` aumenta Lim Total; `(d)` continua informativa e fora de Lim Total, Saldo previsto e Saldo real. Valores zero nas quatro colunas detalháveis não são interativos e não disparam consulta.

A soma dos registros deve ser idêntica ao valor consolidado da mesma filial, competência, Natureza, tipo e ambiente. Total divergente, Natureza divergente ou lista vazia diante de consolidado não zero é inconsistência, nunca empty state normal. Os valores detalhados não participam de novas fórmulas e não mudam universo de Naturezas, Limite Total, Saldo Previsto ou Saldo Real.
