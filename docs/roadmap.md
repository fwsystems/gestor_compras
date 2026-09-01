# Roadmap

As etapas posteriores estão registradas apenas para planejamento. As Sprints 0, 1, 2 e 3 estão concluídas. A Sprint 4 — Evolução Funcional do Gestor — está em andamento.

## SPRINT 0 — Fundação

- ET-001 Bootstrap e documentação — **concluída**
- ET-002 Convenções e configuração de ambientes — **concluída**
- ET-003 Infraestrutura inicial de frontend e backend — **concluída**

## SPRINT 1 — Mock visual

- ET-004 App Shell — **concluída**
- ET-005 Tela principal do Gestor — **concluída**
- ET-006 Dados mock — **concluída**
- ET-007 Navegação entre meses — **concluída**
- ET-008 Alertas e formatação visual — **concluída**
- ET-008A Refinamento semântico da barra de consumo — **concluída**

## SPRINT 2 — API Mock — **concluída**

- ET-009 Contratos da API — **concluída**
- ET-010 Endpoint mock do Gestor — **concluída**
- ET-011 Integração frontend/backend — **concluída**
- ET-012 Tratamento de loading, erro e empty state — **concluída**

## SPRINT 3 — SQL Server / Homologação — **concluída**

- ET-013 Infraestrutura de conexão SQL Server — **concluída**
- ET-014 Repository de Naturezas — **concluída**
- ET-015 Repository de Limites — **concluída**
- ET-016 Repository de PC aberto — **concluída**
- ET-017 Repository de NF entrada — **concluída**
- ET-018 Repository de Contingências — **concluída**

### Paridade Protheus e fechamento da Sprint 3

- ET-019 Serviço consolidado do Gestor — **concluída**
- ET-020 Validação integrada da composição SQL em HML — **aguardando validação funcional**
- ET-020A Ampliação anterior do conjunto base de Naturezas — **posteriormente parcialmente revertida/corrigida pela ET-021A**
- ET-020B Ativação da fonte SQL no ambiente HML — **concluída**
- ET-020C Navegação mensal dinâmica em HML — **concluída**
- ET-021 Filtros operacionais e comparação HML x FWACOM04 — **aguardando validação manual**
- ET-021A Alinhamento do conjunto de Naturezas com FWACOM17 — **concluída**
- ET-021B Handoff técnico e consolidação documental — **concluída**
- ET-021B.1 Saneamento da suíte backend e fechamento do handoff — **concluída (198 testes aprovados)**
- ET-021C Diagnóstico da divergência de PC aberto em HML — **concluída diagnosticamente; causa ainda não comprovada; 207 testes aprovados**
- ET-021D Habilitação controlada de leitura em PRD — **implementada tecnicamente; execução real pendente de confirmação externa SELECT-only e autorização; 229 testes aprovados**
- ET-021D.1 Configuração temporária e comparação controlada PRD — **concluída; `4.000-460`, julho/2026, homologada contra o FWACOM04 atual**
- ET-021D.2 Configuração persistente e protegida de PRD — **concluída; `.env.prd` separado e ignorado**
- ET-021D.2A Seletor controlado DEV/HML/PRD — **concluída; seleção por requisição e confirmação manual PRD preservadas; decisão HML inicial substituída pela ET-021D.2C**
- ET-021D.2B Período inicial automático — **concluída tecnicamente; HML/PRD usam o mês civil local do navegador, DEV mantém fallback setembro/2025**
- ET-021D.2C Ambiente inicial PRD — **concluída tecnicamente; PRD inicial quando disponível, fallback de disponibilidade HML/DEV, sem fallback de consulta e sem go-live**
- ET-022 Ajustes de divergências — **absorvida pelo fechamento funcional da Sprint 3**

## SPRINT 4 — Evolução Funcional do Gestor — **em andamento**

- ET-023 Abertura da Sprint 4 e detalhamento financeiro por Natureza — **concluída e homologada manualmente**
- ET-023A Diagnóstico e correção do drill-down financeiro inconsistente — **concluída e homologada manualmente; causa `EV_VALOR float(53)` comprovada**
- ET-024 Acesso ao Gestor por outro computador da rede local — **concluída e homologada manualmente em outros computadores da LAN; URL atual `http://10.211.2.67:5193`**
- Propostas anteriores de ET-024 sobre drill-down de Contingência OK — **canceladas; não pertencem ao histórico oficial**
- ET-025 Evolução do detalhamento de NF Entrada / Títulos — **concluída; funcionalidade-base antecipada na ET-023, enriquecida com nome do fornecedor SA2 e emissão SE2 sem alterar a composição financeira**
- ET-026 Detalhamento de Contingências por Natureza — **concluída; detalhes independentes OK/aprovação no endpoint e drawer existentes, com invariância e regras consolidadas preservadas**
- ET-027 Refinamento da Interface de Detalhes — **concluída; drawer-base da ET-023 reutilizado e refinado para os quatro tipos, sem alteração financeira ou de backend; validação visual manual pendente**
- ET-028 Visualização Mensal / Semanal / Diária — **concluída; escopo anterior de filtros adicionais já havia sido antecipado na ET-021. Semanal/Diária usam intervalo real, Limite Original proporcional por dias úteis e movimentos por data; Mensal preservado**
- ET-029 Busca adicional — **absorvida pela busca/filtro de Natureza já implementada anteriormente na ET-021**

## SPRINT 5 — UX

- ET-030 Ordenação — **concluída tecnicamente; ordenação local crescente/decrescente em todas as colunas, sem API**
- ET-031 Exportação — **concluída tecnicamente; CSV e XLSX locais, respeitando filtro, ordenação e granularidade, sem API**
- ET-032 Responsividade — **concluída tecnicamente; controles, tabela com overflow local e drawer adaptados sem alteração funcional**
- ET-033 Estrutura do Dashboard Gerencial — **concluída tecnicamente; cards consolidados e navegação Dashboard/Gestor, sem gráficos**

## SPRINT 6 — Homologação

- ET-034 Gráficos Gerenciais — **concluída tecnicamente; gráficos em colunas, cards com ícones e resumo local derivados do consolidado do Dashboard**
- ET-035 Indicadores de Atenção — **concluída tecnicamente; quatro indicadores e detalhes locais no Dashboard**
- ET-036 Evolução Temporal — **concluída tecnicamente; linha mensal de janeiro ao mês selecionado via endpoint timeline**
- ET-037 Testes Automatizados — **concluída tecnicamente; cobertura consolidada de timeline, endpoint e validações frontend**
- ET-036 Evolução Temporal
- ET-037 Homologação dos usuários
- ET-038 Correções da homologação

## SPRINT 7 — Produção

- ET-039 Configuração PRD para operação/go-live (não antecipada pela ET-021D)
- ET-040 Segurança e credenciais
- ET-041 Logging
- ET-042 Health check
- ET-043 Procedimento de deploy
- ET-044 Plano de rollback

## SPRINT 8 — Go Live

- ET-045 Deploy produção
- ET-046 Validação pós-deploy
- ET-047 Monitoramento inicial
- ET-048 Encerramento da implantação
