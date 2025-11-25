# 1. Visão Geral do Projeto

O projeto consiste no desenvolvimento de uma plataforma completa de criação e gestão de lojas virtuais, inspirada em soluções como **Nuvemshop**, **Shopify** e **Loja Integrada**.

O sistema permite que lojistas criem suas próprias lojas, personalizem seus catálogos e gerenciem vendas, enquanto clientes podem navegar nas lojas e realizar compras.

A plataforma será composta por:

- **Back-end (API REST)** desenvolvido em *Python + Django + Django REST Framework*
- **Aplicação Web** para administração e loja pública
- **Aplicativo Mobile universal**, onde o cliente visualiza qualquer loja da plataforma e pode comprar
- **Banco de dados PostgreSQL**
- **Gerenciamento via GitHub Projects + Codespaces**, conforme exigência do professor

---

# 2. Objetivo Geral

Criar uma solução robusta e escalável que permita:

- lojistas criarem e gerenciarem suas lojas virtuais;
- consumidores comprarem produtos nessas lojas via Web ou aplicativo mobile;
- um painel administrativo completo para o lojista gerenciar produtos, pedidos e configurações da loja.

---

# 3. Objetivos Específicos

- Desenvolver um **back-end modularizado** (usuários, lojas, produtos, pedidos).
- Criar **endpoints RESTful** com autenticação **JWT**.
- Gerenciar **múltiplos lojistas e suas lojas** dentro da mesma plataforma.
- Criar interface Web para:
  - administração da loja;
  - gestão de catálogo;
  - gestão de pedidos;
  - personalização visual da loja;
  - loja pública acessível por URL.
- Desenvolver um **aplicativo mobile universal** capaz de:
  - listar lojas;
  - visualizar produtos;
  - gerenciar carrinho;
  - realizar pedidos;
  - acompanhar status do pedido.

---

# 4. Descrição da Plataforma

## 4.1. Módulo do Lojista (Web – Painel Administrativo)

O lojista poderá:

- Criar conta e criar sua loja na plataforma
- Definir nome, descrição e logo da loja
- Personalizar cores e tema básico
- Criar e gerenciar categorias
- Cadastrar produtos com:
  - título
  - descrição
  - preço
  - estoque
  - fotos
  - categoria
- Alterar estoque e preço rapidamente
- Acompanhar pedidos:
  - pendentes
  - pagos
  - enviados
  - entregues
- Alterar status do pedido
- Acessar relatório simples:
  - total vendido
  - número de pedidos
  - produtos com menor estoque

---

A loja contará com:

- Home da loja
- Listagem de categorias
- Lista de produtos
- Página do produto
- Carrinho de compras
- Checkout (pagamento simulado)
- Confirmação de pedido

Simula o funcionamento de um e-commerce real.

---

## 4.2. Aplicativo Mobile Universal

O aplicativo é destinado ao **consumidor final**, não ao lojista.

Funciona como um **“super app”** que acessa as lojas cadastradas na plataforma.

### Funcionalidades

#### 🔎 Explorar lojas
- listar todas as lojas cadastradas
- pesquisar lojas por nome
- acessar a loja escolhida

#### 🛒 Comprar
- ver produtos da loja selecionada
- ver detalhes do produto
- adicionar itens ao carrinho
- gerenciar o carrinho
- finalizar pedido
- pagamento simulado

#### 📦 Acompanhamento
- ver meus pedidos
- ver status do pedido (pendente, pago, enviado, entregue)

