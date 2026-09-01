# Convenções do projeto

Estas regras devem manter o código previsível sem adicionar burocracia desnecessária.

## Nomes e arquivos

- Componentes e páginas React: arquivo e símbolo em `PascalCase`, por exemplo `HomePage.tsx`.
- Hooks React: `camelCase` com prefixo `use`, por exemplo `useGestor.ts`.
- Services, configurações e utilitários TypeScript: arquivos em `camelCase`.
- Módulos, arquivos, funções e variáveis Python: `snake_case`.
- Classes, schemas e enums Python: `PascalCase`.
- Constantes: `UPPER_SNAKE_CASE` quando forem realmente imutáveis e globais.

## Imports

- Agrupar primeiro bibliotecas externas e depois módulos internos, separados por uma linha vazia.
- Evitar importações circulares e caminhos que atravessem camadas sem necessidade.
- Não usar importações globais (`*`).

## TypeScript e React

- Manter o modo `strict` habilitado e evitar `any`.
- Tipar os contratos HTTP explicitamente quando endpoints funcionais forem criados.
- Ler variáveis Vite somente em `src/config/env.ts`.
- Componentes e páginas cuidam da interface; regras de negócio não ficam no JSX.
- Frontend Services centralizam a comunicação HTTP e o tratamento comum de falhas.

## Python e FastAPI

- Usar type hints em funções públicas e contratos.
- API/Endpoint cuida de HTTP, validação de entrada, status codes e resposta.
- Service cuida de regras de negócio e orquestração.
- Repository cuida exclusivamente do acesso a dados e SQL.
- Schema Pydantic define contratos de entrada e saída da API.
- Não colocar SQL em endpoints nem acoplar services ao FastAPI.

## API

- Endpoints funcionais usam o prefixo configurável `/api`.
- Recursos usam substantivos, URLs em minúsculas e respostas JSON.
- O health check operacional permanece em `GET /health`.
- Erros seguem inicialmente o formato nativo e simples do FastAPI:

```json
{
  "detail": "Mensagem do erro"
}
```

Exemplos reservados para etapas futuras, não implementados nesta etapa:

- `GET /api/gestor`
- `GET /api/gestor/{natureza}/pedidos`
- `GET /api/gestor/{natureza}/titulos`
- `GET /api/gestor/{natureza}/contingencias`

## Configuração e ambientes

- Variáveis de ambiente usam `UPPER_SNAKE_CASE`.
- Variáveis públicas do Vite usam obrigatoriamente o prefixo `VITE_`.
- Somente `dev`, `hml` e `prd` são ambientes válidos.
- A configuração deve ser lida por módulos centrais, nunca espalhada pelo código.
- `.env` e suas variações locais não são versionados; somente `.env.example`.

## Segurança e ERP

- Senhas, tokens, IPs internos e strings de conexão nunca são registrados no código, logs ou respostas públicas.
- O frontend nunca recebe credenciais do banco.
- Futuras credenciais `DB_*` existirão somente no backend.
- Todo acesso futuro ao ERP será read-only. É proibido executar `INSERT`, `UPDATE` ou `DELETE` em suas tabelas.

## Commits

Recomenda-se uma mensagem curta no imperativo, com escopo opcional:

```text
feat(config): valida ambientes da aplicação
docs: registra convenções de camadas
test(api): cobre endpoint de informações
```

Cada commit deve representar uma mudança coesa e não deve incluir arquivos gerados, ambientes locais ou segredos.

