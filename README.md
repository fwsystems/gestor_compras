# Gestor de Compras Web

Aplicação web que reproduz o Gestor de Compras do TOTVS Protheus, com backend FastAPI e frontend React. O objetivo atual é alcançar paridade funcional com as rotinas originais antes de qualquer preparação de produção.

## Estado atual / Continuidade do projeto

**Sprint 3 concluída; Sprint 4 em andamento com ET-023 a ET-028 concluídas. A ET-024 foi homologada manualmente em outros computadores da LAN.** O Gestor inicia em PRD, quando disponível e habilitada, no mês civil atual do navegador. Se PRD estiver indisponível, a inicialização usa HML e depois DEV conforme a capacidade sanitizada do backend. HML usa `backend/.env`, PRD usa `backend/.env.prd` somente com opt-in read-only e DEV usa mock sem SQL. Consulte [docs/handoff.md](docs/handoff.md) antes de alterar regras funcionais.

```text
React + TypeScript + Vite
          ↓ HTTP/JSON
FastAPI
          ↓ seleção explícita de ambiente de dados por requisição
DEV: MockGestorService | HML: GestorSqlService/.env | PRD: GestorSqlService/.env.prd com opt-in
                              ↓
                  5 repositories read-only
                              ↓
                    SQL Server / Protheus do ambiente selecionado
```

- **DEV:** não acessa SQL. Usa fixtures de agosto/2025 (18 Naturezas), setembro/2025 (20) e outubro/2025 (22).
- **HML:** usa `GestorSqlService`, cinco consultas independentes e em lote, dados reais do Protheus e filial atual `0101`. O sufixo físico identificado é `010`.
- **PRD:** datasource inicial nesta instalação controlada, sem confirmação durante o carregamento. Seleções manuais HML/DEV → PRD continuam exigindo confirmação. O opt-in local `GESTOR_PRD_READ_ONLY_VALIDATION=true` permanece estritamente read-only e não representa go-live; o default da flag no código e no `.env.example` continua `false`.

O universo exibível segue o comportamento do `FWACOM17`: Natureza SED ativa, `ED_ZPAINEL = '02'` e relacionamento SE7 ativo em qualquer período. Movimentos financeiros fora desse universo não criam linhas. A ET-021A corrigiu a ampliação indevida introduzida na ET-020A: setembro/2025 passou de 129 para 52 Naturezas em HML, e `5.000-350 — PUBLICIDADES, PUBLICACOES ETC`, cujo `ED_ZPAINEL` está vazio, deixou corretamente de aparecer. A quantidade 52 é resultado dos dados de HML, nunca uma constante de negócio.

As colunas-base são `(a) PC aberto`, `(b) NF entrada`, `(c) Contingência OK`, `(d) Contingência em aprovação` e `(e) Lim Original`. As fórmulas atuais são:

```text
Lim Total      = (e) + (c)
Saldo previsto = (e) + (c) - (a) - (b)
Saldo real     = (e) + (c) - (b)
```

A coluna `(d)` é somente informativa e não participa dessas fórmulas.

Na ET-023, valores não nulos de `(a) PC aberto` e `(b) NF entrada` passaram a abrir um drawer acessível com registros carregados sob demanda por `GET /api/gestor/details`. Valores zero continuam apenas textuais. O detalhe usa os mesmos predicados SQL da consolidação, confere quantidade e soma antes de responder e trata diferença ou ausência incompatível como inconsistência. Trocas de ambiente, período ou filtro fecham e cancelam o detalhe; não há N+1 no carregamento principal.

A validação controlada PRD de `4.000-460`, julho/2026, confirmou NF consolidada, total detalhado e soma de 2 registros em R$ 8.773,50. A ET-023 foi posteriormente homologada manualmente.

A ET-023A corrigiu uma inconsistência de precisão observada em `1.000-030`, agosto/2026. O campo `EV_VALOR` é `float(53)` no SQL Server: o `SUM` agregado retornava `28056.880000000005`, enquanto as mesmas 9 linhas somavam `28056.88` no detalhe. O `NfEntradaRepository` agora normaliza ambos para centavos no ingresso no domínio `Decimal`, sem alterar SQL, filtros, registros ou validação de invariância. As regressões PRD de `1.000-050` e `4.000-460` permaneceram aprovadas, e a ET-023A foi homologada manualmente.

A ET-025 evoluiu o detalhe de NF antecipado na ET-023. O mesmo endpoint e drawer agora incluem nome do fornecedor e emissão. O nome vem da SA2 ativa por filial cadastral `LEFT(E2_FILIAL, 2)`, código e loja, em `LEFT JOIN`; ausência de cadastro preserva o título e aparece como `—`. A query agregada, o universo financeiro e a normalização monetária não mudaram. A cardinalidade 1:1 foi comprovada em HML e nos três casos PRD homologados.

A ET-026 estendeu o mesmo endpoint e drawer para `(c) Contingência OK` e `(d) Contingência em aprovação`. Valores não zero abrem detalhes independentes; zero permanece texto. Os registros vêm exclusivamente da SZR ativa e exibem pedido, item, vencimento, usuário, status e `ZR_CONTING`. O primeiro tipo usa `ZR_APROV='T'` e `ZR_REPROV<>'T'`; o segundo usa `ZR_APROV='F'` e `ZR_REPROV='F'`. Como `ZR_CONTING` é `float(53)`, agregado e linhas são normalizados para centavos antes da invariância. As fórmulas consolidadas não mudaram e `(d)` continua informativa.

A ET-027 refinou a interface-base antecipada pela ET-023, reutilizando o mesmo drawer para os quatro tipos. O cabeçalho agora separa tipo amigável, Natureza, período e ambiente; o resumo destaca registros e total; e a tabela recebeu hierarquia visual, larguras coerentes, cabeçalho sticky e overflow interno controlado. Datas, moeda, campos, acessibilidade, loading, erro, retry, foco, cancelamento e proteção contra resposta obsoleta foram preservados. Backend, endpoints, contratos, repositories, SQL e regras financeiras não foram alterados. A validação visual manual permanece pendente porque não havia navegador conectado à automação.

### Ponto atual da homologação

- Setembro/2025, `4.000-350 — OLEO DE BARRAMENTO`: valores relevantes coincidem entre Protheus e Web.
- Setembro/2025, `4.000-400 — OLEO SOLUVEL`: amostra Web registrada para continuidade.
- Julho/2026, `4.000-460 — TAMBOREAMENTO`: a Contingência em aprovação coincide em **R$ 489,58**. O diagnóstico atual reproduziu PC aberto Web de R$ 6.630,00; SZN ativa bruta e total elegível também são R$ 6.630,00, sem exclusão pelo `EXISTS`. A origem dos R$ 2.143,50 adicionais vistos anteriormente no Protheus ainda não foi comprovada.

> **PRÓXIMO PONTO DE INVESTIGAÇÃO:** divergência do PC aberto da Natureza `4.000-460 — TAMBOREAMENTO` em julho/2026. Protheus = R$ 8.773,50; Web = R$ 6.630,00; diferença = R$ 2.143,50. A coluna (d) Contingência em aprovação coincide em R$ 489,58.

O diagnóstico detalhado está em [docs/pc-aberto-diagnostic.md](docs/pc-aberto-diagnostic.md). Não implementar correção sem uma nova comparação simultânea Protheus/Web e, se a divergência persistir, sem o trecho literal do `FWACOM04`.

O projeto ainda não possui repositório Git próprio por decisão atual. O versionamento será criado em etapa futura, antes da preparação para produção; isso não constitui defeito ou pendência do handoff.

## Funcionalidades atuais

A tela do Gestor oferece navegação anterior/próxima e seleção direta de mês/ano, filtro local de Natureza por código ou descrição, tabela de nove colunas, barra de consumo, criticidade e estados de loading, erro, retry e vazio. O filtro é parcial, case-insensitive, preservado entre períodos e nunca dispara API ou SQL.

DEV limita a navegação aos três fixtures. HML e PRD iniciam no mês civil atual do navegador e navegam dinamicamente entre `01/2000` e `12/2100`; as transições de dezembro para janeiro e de janeiro para dezembro estão validadas. Ao entrar em DEV com um período incompatível, o fallback permanece setembro/2025.

Na ET-028, a visualização **Mensal / Semanal / Diária** passou a consultar dados reais por intervalo. Semanal considera segunda a domingo e, quando atravessa o mês, usa somente a interseção com o mês selecionado. Limite Original é proporcional aos dias úteis de segunda a sexta (sem feriados); PC, NF e contingências usam registros reais por `ZN_VENCTO`, `E2_VENCTO` e `ZR_VENCTO`. Mensal permanece inalterado.

A ET-029 foi absorvida pelo filtro de Natureza já existente desde a ET-021. A ET-030 adicionou ordenação local crescente/decrescente em todas as colunas da tabela, preservada com o filtro e nos modos Mensal/Semanal/Diário, sem nova chamada de API.

A ET-031 permite exportar localmente a tabela consolidada visível em CSV (UTF-8/BOM, `;` e decimais pt-BR) ou Excel. A exportação respeita filtro, ordenação, ambiente, período e granularidade, sem nova consulta à API.

A ET-032 adaptou os controles para telas intermediárias e pequenas, preservando a tabela com overflow horizontal local e o drawer em largura integral no celular. Filtro, ordenação, exportação e os modos Mensal/Semanal/Diário permanecem disponíveis.

A ET-033 adicionou o Dashboard gerencial com cards derivados do consolidado já carregado, mantendo CSV/XLSX para análise tabular. Não há gráficos nesta etapa.

A ET-034 adicionou gráficos locais de orçamento versus compromissos, Top 10 de consumo e menores saldos previstos, sempre a partir das mesmas linhas consolidadas do Dashboard.

O ajuste visual da ET-034 adicionou ícones SVG locais aos cards, três gráficos de colunas e uma faixa gerencial derivada dos mesmos consolidados, sem alterações financeiras ou de backend.

A ET-035 evoluiu a faixa para Atenção Gerencial: quatro indicadores clicáveis e detalhes locais, sem novas consultas, API, backend ou regras financeiras.

A ET-036 adicionou a Evolução Temporal mensal no Dashboard, alimentada por `/api/gestor/timeline` com Limite Total, NF Entrada e Saldo Previsto de janeiro até o mês selecionado.

A ET-037 consolidou os testes automatizados do Gestor e Dashboard, cobrindo o contrato, cancelamento e séries da timeline, além dos erros e validações do endpoint.

## Execução

### Backend

Requer Python 3.11 ou superior.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

A API fica em `http://localhost:8000`; os principais recursos são `GET /health`, `GET /api/info`, `GET /api/database/health`, `GET /api/gestor/environments` e `GET /api/gestor?ano=2025&mes=9&filial=0101&ambiente=hml`. O endpoint de ambientes anuncia PRD como default somente quando disponível, com fallback HML/DEV. A omissão temporária de `ambiente` na consulta financeira continua usando HML por compatibilidade; o frontend sempre envia o ambiente descoberto explicitamente.

### Frontend

Requer Node.js 20 ou superior.

```bash
cd frontend
npm install
npm run dev
```

O frontend DEV usa a porta fixa `5193`, escuta em todas as interfaces por configuração e usa chamadas relativas `/api`. O proxy Vite encaminha essas chamadas internamente para `http://127.0.0.1:8000`, mantendo o FastAPI fora da LAN.

### Acesso pela rede local — ET-024

- acesso local: `http://localhost:5193` ou `http://127.0.0.1:5193`;
- acesso LAN atual: `http://10.211.2.67:5193`;
- frontend configurado com `host: '0.0.0.0'`, porta `5193` e proxy `/api`;
- backend restrito a `127.0.0.1:8000`; a porta `8000` não precisa ser liberada na LAN.

`10.211.2.67` é o IPv4 LAN atual e pode mudar sem reserva DHCP/IP fixo; o código não depende desse endereço. Somente TCP `5193` deve ser acessível no perfil de rede apropriado. Nenhuma regra de firewall, roteador ou exposição à Internet foi criada automaticamente.

O acesso em `http://10.211.2.67:5193` foi confirmado manualmente pelo usuário em outros computadores da mesma LAN; a ET-024 está concluída e homologada.

## Validações

```bash
cd backend
pytest

cd ../frontend
node scripts/validate-period.mjs
npm run validate:detail
npm run validate:contingency-detail
npm run validate:detail-interface
npm run lint
npm run build
```

Para validar HML, configure somente o `backend/.env` local e ignorado pelo Git, confirme uma credencial SELECT-only e execute:

```bash
cd backend
python -m scripts.validate_gestor_hml --filial 0101 --ano <ANO> --mes <MES>
```

O runner bloqueia DEV e PRD. Não registre host, usuário, senha ou connection string em documentação, logs ou commits.

Para PRD, use runners separados somente depois de configurar externamente `APP_ENV=prd`, habilitar `GESTOR_PRD_READ_ONLY_VALIDATION=true` e obter confirmação do DBA de que a credencial possui apenas `SELECT`:

```bash
python -m scripts.validate_gestor_prd --filial <FILIAL> --ano <ANO> --mes <MES> [--natureza <CODIGO>]
python -m scripts.diagnose_pc_aberto_prd --filial <FILIAL> --ano <ANO> --mes <MES> --natureza <CODIGO>
```

O `.env` local continua sendo HML. A ET-021D.2 criou `.env.prd` como configuração persistente separada e a ET-021D.2A habilitou sua flag local após a confirmação externa de acesso somente consulta e a validação funcional PRD. Cada arquivo é carregado explicitamente em um objeto `Settings` isolado; o frontend nunca recebe configuração física ou credenciais.

## Leitura obrigatória antes da próxima ET

1. [docs/handoff.md](docs/handoff.md) — contexto autocontido e próximo passo.
2. [docs/roadmap.md](docs/roadmap.md) — histórico e status das ETs.
3. [docs/business-rules.md](docs/business-rules.md) — regras financeiras confirmadas.
4. [docs/database.md](docs/database.md) — tabelas, repositories e limites SQL.
5. [docs/hml-validation.md](docs/hml-validation.md) — evidências de homologação.
6. [docs/pc-aberto-diagnostic.md](docs/pc-aberto-diagnostic.md) — diagnóstico da divergência ainda não comprovada.
7. [docs/architecture.md](docs/architecture.md), [docs/environments.md](docs/environments.md), [docs/api-contracts.md](docs/api-contracts.md) e [docs/conventions.md](docs/conventions.md) — arquitetura, operação e contratos.

Credenciais reais pertencem somente aos arquivos `.env` locais, que permanecem ignorados. Os `.env.example` contêm apenas placeholders seguros.
