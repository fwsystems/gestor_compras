# Homologação HML x Protheus

## Escopo e situação

A ET-021 compara manualmente o Gestor Web em HML com as referências funcionais `FWACOM04` e `FWACOM17`. A homologação ainda não foi encerrada. Consultas HML são read-only e usam a filial atual `0101`. A capacidade PRD da ET-021D é separada, opt-in e não altera as evidências HML deste documento.

Diferenças apenas de formatação decimal não constituem divergência. Nenhum valor ausente do Protheus deve ser inferido e nenhuma divergência deve provocar alteração automática de código.

## Universo de Naturezas — ET-021A

A ET-020A ampliou o conjunto base para a união das Naturezas encontradas nos movimentos financeiros. Isso permitiu que `5.000-350 — PUBLICIDADES, PUBLICACOES ETC` aparecesse em setembro/2025 por causa de uma NF entrada de R$ 220,00, embora estivesse fora do painel do Gestor.

A consulta manual na SED confirmou:

- `5.000-350`: `ED_ZPAINEL` vazio;
- `4.000-350`, `4.000-400`, `5.000-150` e `5.000-400`: `ED_ZPAINEL = '02'`.

A ET-021A corrigiu a regressão aplicando SED ativa + painel `02` + existência histórica ativa na SE7, sem restringir essa existência ao período consultado. O resultado de setembro/2025 caiu de 129 para 52 Naturezas, e `5.000-350` deixou corretamente de aparecer. A quantidade 52 é consequência dos dados HML e não deve ser codificada.

## Casos comparados

### Setembro/2025 — 4.000-350 — OLEO DE BARRAMENTO

| Campo | Protheus | Web | Status |
|---|---:|---:|---|
| PC aberto | R$ 0,00 | R$ 0,00 | OK |
| NF entrada | R$ 13.440,00 | R$ 13.440,00 | OK |
| Contingência OK | R$ 0,00 | R$ 0,00 | OK |
| Contingência em aprovação | R$ 0,00 | R$ 0,00 | OK |
| Lim Original | R$ 13.500,00 | R$ 13.500,00 | OK |
| Lim Total | — | R$ 13.500,00 | coerente com a fórmula |
| Saldo previsto | R$ 60,00 | R$ 60,00 | OK |
| Saldo real | R$ 60,00 | R$ 60,00 | OK |

Esta amostra apresentou correspondência visual dos valores relevantes.

### Setembro/2025 — 4.000-400 — OLEO SOLUVEL

Valores observados no Web e preservados como amostra para continuidade:

| Campo | Web |
|---|---:|
| NF entrada | R$ 127.954,00 |
| Lim Original | R$ 105.000,00 |
| Saldo previsto | -R$ 22.954,00 |
| Saldo real | -R$ 22.954,00 |

Não há nesta documentação uma comparação completa de todas as colunas dessa Natureza com o Protheus.

### Julho/2026 — 4.000-460 — TAMBOREAMENTO

| Campo | Protheus/FWACOM04 | Web | Status |
|---|---:|---:|---|
| PC aberto | R$ 8.773,50 | R$ 6.630,00 | **DIVERGENTE** |
| NF entrada | R$ 0,00 | R$ 0,00 | OK |
| Contingência OK | R$ 0,00 | R$ 0,00 | OK |
| Contingência em aprovação | R$ 489,58 | R$ 489,58 | **OK** |
| Lim Original | R$ 6.000,00 | R$ 6.000,00 | OK |
| Lim Total | — | R$ 6.000,00 | coerente com a fórmula |
| Saldo previsto | -R$ 2.773,50 | -R$ 630,00 | **DIVERGENTE por causa do PC aberto** |
| Saldo real | R$ 6.000,00 | R$ 6.000,00 | OK |

A coluna `(d) Contingência em aprovação` possui evidência positiva de correção nessa amostra. Ela permanece informativa e não participa das fórmulas. A diferença do Saldo previsto é exatamente a diferença do PC aberto:

```text
R$ 8.773,50 - R$ 6.630,00 = R$ 2.143,50
```

## Divergência investigada, ainda não comprovada

> **PRÓXIMO PONTO DE INVESTIGAÇÃO:** divergência do PC aberto da Natureza `4.000-460 — TAMBOREAMENTO` em julho/2026. Protheus = R$ 8.773,50; Web = R$ 6.630,00; diferença = R$ 2.143,50. A coluna (d) Contingência em aprovação coincide em R$ 489,58.

A ET-021C reproduziu em HML R$ 6.630,00 no `PcAbertoRepository`, no total SZN ativo bruto e no total elegível. Portanto, nenhum saldo SZN ativo é atualmente excluído pelo `EXISTS` da SC7. Os dados atuais não contêm contribuição de R$ 2.143,50 capaz de fechar o valor histórico do Protheus, e a causa permanece **ainda não comprovada**.

O diagnóstico completo está em [pc-aberto-diagnostic.md](pc-aberto-diagnostic.md). A próxima evidência necessária é repetir Protheus e Web no mesmo instante e disponibilizar os trechos literais de `FWACOM04:retSldPedidos` e `incluiPrev` caso a divergência persista. Não alterar `PcAbertoRepository` por hipótese.

## Amostras Web anteriores ainda não comparadas

Permanecem apenas como registros auxiliares de setembro/2025, sem confirmação manual completa no Protheus: `2.000-190 — INSS / SESI-SENAI / 13°`, `1.000-030 — EQUIPAMENTOS P/ MAQUINAS`, `1.000-010 — MAQUINAS P/ PRODUCAO` e `4.000-520 — TRATAMENTOS SUPERFICIAIS`. O caso `5.000-350` não é uma amostra financeira válida, pois foi excluído do universo pela ET-021A.

## Roteiro para continuidade

1. Abrir o mesmo período e a mesma filial no Web e no Protheus.
2. Confirmar que a Natureza pertence ao universo SED/SE7/painel `02`.
3. Comparar cada componente separadamente, com precisão de centavos.
4. Em divergência, localizar a regra funcional correspondente antes de editar: PC aberto → `FWACOM04:retSldPedidos`/`incluiPrev`; NF entrada → `retSldTitulos`; contingências → `retSldConting`; Lim Original → `retSaldo`.
5. Usar HML para este roteiro e preservar consultas read-only; nunca registrar documentos detalhados, fornecedores ou credenciais. Uma comparação PRD deve usar os runners próprios da ET-021D e somente após as confirmações externas descritas em `environments.md`.

## Fechamento da divergência por comparação de bases — ET-021D.1/2A

A comparação posterior, simultânea e controlada em PRD substitui a hipótese histórica acima como estado atual do caso `4.000-460 — TAMBOREAMENTO`, julho/2026. Web PRD e FWACOM04 PRD retornaram os mesmos valores: PC aberto R$ 0,00; NF entrada R$ 8.773,50; Contingência OK R$ 0,00; Contingência em aprovação R$ 489,58; Lim Original e Lim Total R$ 6.000,00; Saldo previsto e Saldo real -R$ 2.773,50.

O caso PRD está homologado. Os valores anteriormente registrados no Web eram da base HML; portanto, a divergência HML × PRD não comprova defeito no `PcAbertoRepository`. A regra, as queries, as cinco consultas em lote e as fórmulas foram preservadas. Comparações futuras devem sempre registrar explicitamente o ambiente de dados.
