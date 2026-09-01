# Contratos da API do Gestor

## Objetivo e estágio atual

Este documento define o contrato estável da API do Gestor de Compras. O frontend consome `GET /api/gestor` sem conhecer a fonte. DEV usa dados mock, HML usa `GestorSqlService` read-only e PRD é bloqueado por padrão; com o opt-in da ET-021D, PRD usa o mesmo serviço e preserva exatamente este contrato.

O contrato representa o domínio do Gestor e não expõe nomes físicos de campos ou tabelas do ERP.

## Requisição

```http
GET /api/gestor?ano=2025&mes=9&filial=0101
```

Parâmetros obrigatórios:

| Parâmetro | Tipo | Regra |
|---|---|---|
| `ano` | inteiro | De 2000 a 2100 |
| `mes` | inteiro | De 1 a 12 |
| `filial` | string | Identificador não vazio; sem validação contra o Protheus nesta sprint |

O período não é transportado como texto formatado. Expressões como “Setembro / 2025” são responsabilidade exclusiva da apresentação frontend.

## Contrato do período

`GestorPeriod`:

```json
{
  "ano": 2025,
  "mes": 9
}
```

## Contrato da linha

`GestorRow` possui os seguintes campos obrigatórios:

| Campo JSON | Tipo | Descrição |
|---|---|---|
| `naturezaCodigo` | string | Código funcional da natureza |
| `naturezaDescricao` | string | Descrição da natureza |
| `pcAberto` | número | Pedidos de compra abertos |
| `nfEntrada` | número | Notas/títulos de entrada |
| `contingenciaOk` | número | Contingências aprovadas |
| `contingenciaEmAprovacao` | número | Contingências aguardando aprovação |
| `limiteOriginal` | número | Orçamento mensal original |
| `limiteTotal` | número | Limite original acrescido da contingência aprovada |
| `saldoPrevisto` | número | Saldo após PCs abertos e NF entrada |
| `saldoReal` | número | Saldo após NF entrada |

Zeros e valores negativos são válidos. Em especial, `limiteTotal`, `saldoPrevisto` e `saldoReal` não possuem restrição de positividade.

## Campos derivados

Os campos derivados são retornados explicitamente para que o backend se torne futuramente a fonte oficial das regras:

```text
limiteTotal = limiteOriginal + contingenciaOk
saldoPrevisto = limiteTotal - pcAberto - nfEntrada
saldoReal = limiteTotal - nfEntrada
```

`contingenciaEmAprovacao` não participa desses cálculos.

## Resposta consolidada

`GestorResponse`:

| Campo | Tipo | Regra |
|---|---|---|
| `periodo` | `GestorPeriod` | Período consultado |
| `filial` | string | Identificador da filial |
| `linhas` | `GestorRow[]` | Linhas financeiras |
| `quantidade` | inteiro | Deve corresponder exatamente a `linhas.length` |

Exemplo conceitual:

```json
{
  "periodo": {
    "ano": 2025,
    "mes": 9
  },
  "filial": "0101",
  "linhas": [
    {
      "naturezaCodigo": "4.000-010",
      "naturezaDescricao": "MATÉRIA-PRIMA",
      "pcAberto": 40000.00,
      "nfEntrada": 30000.00,
      "contingenciaOk": 10000.00,
      "contingenciaEmAprovacao": 0.00,
      "limiteOriginal": 160000.00,
      "limiteTotal": 170000.00,
      "saldoPrevisto": 100000.00,
      "saldoReal": 140000.00
    }
  ],
  "quantidade": 1
}
```

## Valores financeiros e JSON

O backend representa valores financeiros com `Decimal`. Na serialização JSON, eles são convertidos explicitamente para números JSON, pois JSON não possui um tipo decimal nativo. O frontend os recebe como `number` e aplica formatação BRL/pt-BR somente na interface.

Valores nunca são transportados como strings formatadas, como `"R$ 40.000,00"`.

## Consulta sem dados

Uma consulta válida sem naturezas retorna HTTP 200:

```json
{
  "periodo": {
    "ano": 2025,
    "mes": 9
  },
  "filial": "0101",
  "linhas": [],
  "quantidade": 0
}
```

A ausência de linhas não é um erro e não produz HTTP 404.

## Erros

- HTTP 422: parâmetros ou dados incompatíveis com as validações do FastAPI/Pydantic.
- HTTP 503: fonte indisponível, inconsistência HML ou Gestor bloqueado no ambiente.
- HTTP 500: falha interna inesperada fora dos casos sanitizados.
- HTTP 404 não será usado apenas para representar uma consulta válida sem dados.

O formato básico de erro permanece o padrão do FastAPI:

```json
{
  "detail": "Mensagem do erro"
}
```

## Comportamento por ambiente

A origem é transparente ao JSON:

- DEV: mock determinístico descrito abaixo;
- HML: cinco consultas em lote e composição SQL real;
- PRD: HTTP 503 nesta fase.

Não existe fallback SQL/mock.

### Mock DEV

- Fonte atual: módulo mock local do backend, sem dependência do frontend.
- Filial com dados: `0101`.
- Agosto/2025: 18 linhas.
- Setembro/2025: 20 linhas.
- Outubro/2025: 22 linhas.
- Outro período válido ou outra filial: HTTP 200, `linhas: []` e `quantidade: 0`.
- Parâmetros fora das restrições: HTTP 422 no formato padrão do FastAPI.

Exemplo real com dados:

```http
GET /api/gestor?ano=2025&mes=9&filial=0101
```

Exemplo real sem dados por período:

```http
GET /api/gestor?ano=2025&mes=11&filial=0101
```

Exemplo real sem dados por filial:

```http
GET /api/gestor?ano=2025&mes=9&filial=9999
```

Exemplo de validação inválida:

```http
GET /api/gestor?ano=2025&mes=13&filial=0101
```

A especificação e a interface Swagger estão disponíveis em `/openapi.json` e `/docs`. HML preserva o mesmo contrato público com acesso SQL read-only.

## Desacoplamento do Protheus

O contrato não contém nomes como `C7_*`, `E2_*`, `EV_*`, `ZN_*`, `ZR_*` ou `E7_*`. A tradução entre tabelas do ERP e o domínio público fica encapsulada no backend, sempre em modo read-only.

## Ambiente de dados — ET-021D.2A

```http
GET /api/gestor?ano=2026&mes=7&filial=0101&ambiente=prd
```

`ambiente` aceita exclusivamente `dev`, `hml` ou `prd`; qualquer outro valor retorna HTTP 422. O frontend novo sempre o envia. Para compatibilidade temporária, a ausência usa HML, nunca PRD. Fonte indisponível retorna HTTP 503 sanitizado e não faz fallback.

```http
GET /api/gestor/environments
```

Retorna uma lista com `id`, `label` e `available`. `default` é `prd` quando PRD está disponível, senão `hml` quando HML está disponível e, por fim, `dev`. O default sempre referencia uma opção disponível. Não expõe host, banco, usuário, senha, driver, connection string, sufixo, tabelas ou motivo técnico. O `GestorResponse` financeiro permanece inalterado.

## Detalhamento financeiro — ET-023 a ET-026

```http
GET /api/gestor/details?ambiente=prd&filial=0101&ano=2026&mes=7&natureza=4.000-460&tipo=nf_entrada
```

Todos os parâmetros são obrigatórios. `tipo` aceita `pc_aberto`, `nf_entrada`, `contingencia_ok` ou `contingencia_aprovacao`; valor inválido ou parâmetro ausente retorna HTTP 422. A resposta contém `ambiente`, `filial`, `periodo`, `naturezaCodigo`, `naturezaDescricao`, `tipo`, `quantidade`, `total` e `registros`. `quantidade` deve coincidir com o tamanho da lista e `total` com a soma dos valores.

Registros de PC contêm `pedido`, `vencimento` e `valor`; seu contrato permanece inalterado. Registros de NF contêm `documento`, `prefixo`, `parcela`, `fornecedor`, `fornecedorNome`, `loja`, `emissao`, `vencimento` e `valor`. `fornecedor` preserva o código; `fornecedorNome` pode ser vazio quando não há cadastro ativo correspondente, e a interface apresenta `—`. Datas Protheus são transportadas como `AAAAMMDD` e formatadas apenas na interface. O contrato não expõe nomes físicos de tabelas/campos, credenciais ou mensagens SQL. Fonte indisponível ou inconsistência retorna HTTP 503 sanitizado e nunca aciona fallback entre ambientes.

Registros dos dois tipos de contingência contêm `pedido`, `item`, `vencimento`, `usuario`, `status` e `valor`. Para `contingencia_ok`, `status` é `OK`; para `contingencia_aprovacao`, é `Em aprovação`. As categorias são mutuamente independentes e o total corresponde à respectiva coluna consolidada. Nenhum código de infraestrutura ou campo interno de banco é exposto.
