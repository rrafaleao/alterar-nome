# API Mobile ZappShop (Android)

Esta API foi criada separada das rotas HTML do site para uso no Android Studio.
Ela usa o mesmo banco de dados e os mesmos modelos do sistema web.

## Base URL

- http://localhost:5000/api/v1

## Endpoints

### GET /health

Verifica se a API esta online.

### GET /customers/exists

Verifica se um email existe no sistema.

Query params:
- email (obrigatorio)
- store_slug (opcional)

Retorno:
- exists_global: se o email existe em qualquer loja
- exists_in_store: se o email existe na loja informada

### POST /auth/register

Cria store_customer na loja.

Body JSON:
{
  "store_slug": "minha-loja",
  "full_name": "Nome Completo",
  "email": "cliente@teste.com",
  "phone": "11999999999",
  "password": "123456",
  "confirm_password": "123456"
}

Regras:
- Se email ainda nao existe: cria cliente novo.
- Se email ja existe em outra loja e a senha confere: vincula automaticamente na loja solicitada.
- Se email ja existe e senha nao confere: retorna erro 409.

Retorna token Bearer para autenticacao no app.

### POST /auth/login

Login de cliente por email, senha e store_slug.

Body JSON:
{
  "store_slug": "minha-loja",
  "email": "cliente@teste.com",
  "password": "123456"
}

Retorna token Bearer e dados do cliente/loja.

### GET /auth/me

Rota protegida por token Bearer.

Header:
Authorization: Bearer SEU_TOKEN

Retorna dados do store_customer autenticado.

### GET /products

Lista produtos ativos das lojas com onboarding concluido.

Query params opcionais:
- page (default 1)
- per_page (default 20, max 100)
- store_slug
- category_id
- search

Exemplos:
- /api/v1/products
- /api/v1/products?store_slug=minha-loja
- /api/v1/products?search=camisa&page=1&per_page=20

## Formato de resposta

Sucesso:
{
  "success": true,
  "data": {}
}

Erro simples:
{
  "success": false,
  "error": "mensagem"
}

Erro de validacao:
{
  "success": false,
  "errors": {
    "campo": "descricao"
  }
}

## Codigos HTTP

- 200 sucesso
- 201 criado
- 400 erro de validacao
- 401 nao autenticado
- 403 conta inativa
- 404 nao encontrado
- 409 conflito
- 500 erro interno

## Fluxo recomendado para Android

1. Login com /auth/login e salvar token.
2. Enviar token em Authorization Bearer nas rotas protegidas.
3. Carregar vitrine com /products.
4. Opcionalmente checar email com /customers/exists antes de cadastro.
