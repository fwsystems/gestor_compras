# Diagnóstico do PC aberto — ET-021C

## Caso investigado

- Filial: `0101`.
- Período: julho/2026.
- Natureza: `4.000-460 — TAMBOREAMENTO`.
- Protheus/FWACOM04 observado anteriormente: R$ 8.773,50.
- Web observado e reproduzido: R$ 6.630,00.
- Diferença histórica: R$ 2.143,50.
- Execução diagnóstica final: 26/08/2026 às 11:15:56 UTC.

A investigação foi exclusivamente read-only em HML. Não houve acesso a PRD nem alteração de query funcional, repository, service, fórmula, frontend ou mock.

## Regra Web confirmada no código

O `PcAbertoRepository` soma `ZN_SALDO` por `ZN_NATUREZ` na SZN ativa para filial e `ZN_VENCTO LIKE '202607%'`. Uma parcela participa quando existe na SC7 ativa um item do mesmo `C7_FILIAL = ZN_FILIAL` e `C7_NUM = ZN_NUMPED` que satisfaça `C7_QUJE < C7_QUANT` e `C7_RESIDUO = ' '`. O relacionamento não usa item ou Natureza da SC7. A leitura não recalcula quantidade × preço.

## Resultado atual em HML

| Medida | Valor |
|---|---:|
| A. Total bruto SZN ativo, antes do `EXISTS` | R$ 6.630,00 |
| B. Total elegível pela regra Web | R$ 6.630,00 |
| C. Valor Protheus observado anteriormente | R$ 8.773,50 |
| A − B | R$ 0,00 |
| C − B | R$ 2.143,50 |

O runner reproduziu o `PcAbertoRepository` exatamente. Não existe hoje saldo SZN ativo da Natureza/período excluído pelo `EXISTS` atual.

## Decomposição dos R$ 6.630,00

O total Web possui uma única contribuição ativa:

| Pedido | Item SZN | Vencimento | ZN_SALDO | Registros | Elegibilidade |
|---|---|---|---:|---:|---|
| `019976` | `0001` | 05/07/2026 | R$ 6.630,00 | 1 | elegível |

O pedido possui um item SC7 ativo e elegível:

| Pedido | Item | C7_ZZNATUR | C7_QUANT | C7_QUJE | C7_PRECO | C7_TOTAL | Situação |
|---|---|---|---:|---:|---:|---:|---|
| `019976` | `0001` | `4.000-460` | 2.600 | 0 | R$ 33,15 | R$ 86.190,00 | aberto, sem resíduo, elegível |

O valor `(C7_QUANT − C7_QUJE) × C7_PRECO` é R$ 86.190,00. Ele não corresponde ao valor mensal nem à diferença histórica; isso confirma que a leitura deve continuar usando as parcelas persistidas na SZN, sem substituir o agregado por quantidade × preço.

## Registros que não entram no total atual

Não há registro SZN ativo excluído por pedido ausente, item encerrado, resíduo, Natureza divergente ou exclusão lógica na SC7. Existem, porém, registros SZN logicamente excluídos no mesmo recorte, totalizando R$ 67.707,92:

| Pedido | Total SZN logicamente excluído em julho/2026 |
|---|---:|
| `014573` | R$ 1.468,74 |
| `018829` | R$ 39.166,68 |
| `019976` | R$ 27.072,50 |
| **Total** | **R$ 67.707,92** |

Nenhuma parcela individual, grupo por pedido/data ou combinação diretamente identificada pelo runner totaliza R$ 2.143,50. Os registros excluídos não podem ser reincorporados: exclusão lógica é uma decisão funcional protegida e o total histórico excluído é muito superior à diferença.

## Estado da SZN ao longo de 2026

Para a mesma Natureza, o estado ativo atual repete R$ 6.630,00 mensalmente de junho a dezembro/2026. Há volumes logicamente excluídos em todos os meses consultados, inclusive R$ 67.707,92 em julho. Isso comprova que a distribuição persistida passou por revisões, mas não fornece timestamp funcional nem vínculo capaz de demonstrar que uma revisão específica produziu os R$ 8.773,50 observados anteriormente.

## Comparação com FWACOM04

Os fontes `FWACOM04.prw`, `FWACOM09.prw` e `FWACOM17.prw` não estão disponíveis no workspace. Portanto, esta matriz compara o Web somente com as regras do `FWACOM04` já documentadas; não é uma nova leitura literal do ADVPL.

| Regra | FWACOM04 documentado | Web atual | Resultado | Impacto observado |
|---|---|---|---|---|
| Origem | SZN + SC7 | SZN + SC7 | igual | nenhum |
| Relacionamento | filial + pedido | filial + pedido via `EXISTS` | igual | nenhum |
| Período | `ZN_VENCTO` no mês | `LIKE '202607%'` | igual | nenhum |
| Pedido aberto | `C7_QUJE < C7_QUANT` | condição equivalente | igual | pedido atual elegível |
| Resíduo | espaço | espaço parametrizado | igual | pedido atual elegível |
| Valor | soma de `ZN_SALDO` | soma de `ZN_SALDO` | igual | R$ 6.630,00 atual |
| Exclusão lógica | aplicada | aplicada em SZN e SC7 | igual | histórico excluído não participa |
| Item/Natureza SC7 no vínculo | não documentado no agregado | não utilizado | sem diferença conhecida | `C7_ZZNATUR` atual coincide |

### retSldPedidos

Pelas regras já documentadas, `retSldPedidos` soma o saldo persistido da SZN após validar pedido aberto na SC7. O comportamento Web atual reproduz essa descrição e, no estado HML consultado, retorna R$ 6.630,00. Sem o fonte ADVPL e sem uma nova leitura da tela original no mesmo instante, não é possível demonstrar por que o Protheus mostrou R$ 8.773,50 anteriormente.

### incluiPrev

A documentação registra que `incluiPrev` parte de `(C7_QUANT − C7_QUJE) × C7_PRECO` e distribui o valor pela condição de pagamento na SZN. O item atual totaliza R$ 86.190,00 e a parcela ativa de julho é R$ 6.630,00. Os registros logicamente excluídos comprovam revisões da distribuição, mas não há evidência suficiente para atribuir os R$ 2.143,50 a uma revisão específica.

## Hipóteses avaliadas

- **Saldo ativo excluído pelo `EXISTS`: descartada no estado atual.** A − B = R$ 0,00.
- **Pedido atual ausente, encerrado ou com resíduo: descartada.** O pedido `019976` possui item ativo, aberto e elegível.
- **Natureza divergente no item: descartada para a contribuição atual.** `C7_ZZNATUR = '4.000-460'`.
- **Diferença igual ao saldo aberto bruto do item SC7: descartada.** O valor calculável é R$ 86.190,00.
- **Parcela SZN atual ou excluída de R$ 2.143,50: não encontrada.**
- **Mudança temporal/redistribuição da SZN entre a observação manual e o diagnóstico: plausível, mas não comprovada.** Faltam timestamp funcional e reprodução simultânea no Protheus.
- **Regra adicional no ADVPL não documentada: não avaliável.** O fonte não está disponível.

## Caso de controle

Para `4.000-350 — OLEO DE BARRAMENTO`, setembro/2025, o runner retornou:

- `PcAbertoRepository`: R$ 0,00;
- SZN ativa bruta: R$ 0,00;
- total elegível: R$ 0,00;
- SZN logicamente excluída no período: R$ 100.800,00.

O resultado atual coincide com o PC aberto R$ 0,00 já homologado e mostra que a presença de histórico logicamente excluído não implica divergência.

## Conclusão

**Causa: AINDA NÃO COMPROVADA.**

O diagnóstico explicou integralmente o Web atual, mas explicou **R$ 0,00** dos R$ 2.143,50 históricos por filtros do repository. Os R$ 2.143,50 permanecem sem decomposição nos dados ativos atuais.

A próxima evidência necessária é uma nova leitura do `FWACOM04` e do Web no mesmo instante, no mesmo contexto, seguida da captura read-only imediata da SZN/SC7. Também é necessário disponibilizar o trecho literal de `FWACOM04:retSldPedidos` e `incluiPrev` caso o Protheus continue mostrando R$ 8.773,50. Somente após essa evidência poderá ser proposta uma ET de correção.

## Runner

```text
python -m scripts.diagnose_pc_aberto_hml --filial 0101 --ano 2026 --mes 7 --natureza 4.000-460
```

O runner é HML-only, usa resolução central de tabelas, parâmetros SQL e apenas `SELECT`. Sua saída é controlada e não contém configuração de conexão ou credenciais.

A ET-021D preservou essa guarda HML e adicionou um runner separado para repetir a mesma leitura em PRD:

```bash
python -m scripts.diagnose_pc_aberto_prd --filial <FILIAL> --ano <ANO> --mes <MES> --natureza <CODIGO>
```

O runner PRD exige `APP_ENV=prd`, `GESTOR_PRD_READ_ONLY_VALIDATION=true`, configuração completa, sufixo e driver, e executa primeiro o health `SELECT 1`. Ele não foi executado na ET-021D porque o `.env` local permanece em HML e não houve confirmação externa de credencial PRD somente leitura.

## Validação técnica

- backend ao final da ET-021C: 207/207 testes aprovados; estado atual após ET-021D: 229/229;
- 9 testes específicos do runner aprovados;
- validação frontend: 21/21 verificações aprovadas;
- lint frontend: aprovado;
- build frontend: aprovado;
- dependências adicionadas: nenhuma.
