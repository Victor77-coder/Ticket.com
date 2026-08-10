<!--
SYNC IMPACT REPORT
==================
Versão: TEMPLATE (não versionado) → 1.0.0
Tipo de bump: MAJOR inicial — primeira ratificação com princípios concretos substituindo
todos os placeholders do template.

Princípios definidos (todos novos):
  - [PRINCIPLE_1_NAME] → I. Fluxo Completo Antes de Profundidade
  - [PRINCIPLE_2_NAME] → II. Integridade da Reserva (NÃO NEGOCIÁVEL)
  - [PRINCIPLE_3_NAME] → III. Ingresso Inforjável e Validação Única (NÃO NEGOCIÁVEL)
  - [PRINCIPLE_4_NAME] → IV. Papéis Explícitos e Autorização no Servidor
  - [PRINCIPLE_5_NAME] → V. Interface Autoral (Anti AI-Slop)
  - (novo) VI. Rastro de Decisão Versionado
  - (novo) VII. Isolamento da API Externa

Seções renomeadas:
  - [SECTION_2_NAME] → Stack e Restrições Obrigatórias
  - [SECTION_3_NAME] → Fluxo de Desenvolvimento e Portões de Qualidade

Seções removidas: nenhuma.

Templates verificados:
  ✅ .specify/templates/plan-template.md — "Constitution Check" é placeholder genérico
     preenchido em tempo de execução pelo /speckit-plan; nenhuma edição necessária.
  ✅ .specify/templates/spec-template.md — estrutura compatível; princípios V e VI serão
     exercidos via seções de Requirements/Assumptions.
  ✅ .specify/templates/tasks-template.md — fases genéricas comportam as categorias de
     tarefa exigidas (auth, concorrência, seed, README); nenhuma edição necessária.
  ✅ .specify/templates/checklist-template.md — genérico, sem referências desatualizadas.
  ⚠ README.md — ainda não existe. Exigido pelo Princípio VI e pelos Requisitos Não
     Funcionais do desafio. Criar antes da entrega.

Desvio registrado: o usuário havia indicado Nuxt.js; o PDF do desafio exige React.
Decisão confirmada com o usuário em 2026-08-10 → adotado Next.js (React).

TODOs adiados:
  - TODO(DATA_LIMITE_ENTREGA): o prazo é de 7 dias corridos a partir do recebimento do
    desafio; a data de recebimento não foi informada. Fixar a data-limite absoluta.
-->

# Plataforma de Ingressos de Cinema — Constitution

Este documento governa o desenvolvimento da plataforma de venda de ingressos de cinema
entregue como resposta ao Desafio Elite Dev 2026 (Verzel). Ele traduz os requisitos
obrigatórios do desafio em regras verificáveis. Onde houver conflito entre este documento
e uma preferência pessoal, este documento prevalece; onde houver conflito entre este
documento e o PDF do desafio, o PDF prevalece e esta constitution DEVE ser emendada.

## Core Principles

### I. Fluxo Completo Antes de Profundidade

O caminho ponta a ponta — catálogo → sessão → seleção de assento → pagamento simulado →
ingresso com QR → validação na portaria — DEVE estar funcionando de forma completa antes
que qualquer refinamento, otimização ou item opcional seja iniciado. Nenhuma tela pode ser
entregue pela metade: se um passo do fluxo existe na navegação, ele DEVE ter estado de
sucesso, estado de erro e estado vazio implementados.

Itens explicitamente fora de escopo, que NÃO DEVEM ser construídos: nota fiscal, revenda
entre usuários, aplicativo nativo, recuperação de senha e envio de ingresso por e-mail.

**Racional**: o desafio afirma preferir "o fluxo inteiro simples e completo a um pedaço
sofisticado com telas pela metade". Escopo pequeno é intencional; ampliá-lo antes de fechar
o fluxo trabalha contra o critério de avaliação.

### II. Integridade da Reserva (NÃO NEGOCIÁVEL)

O mesmo assento de uma mesma sessão NUNCA pode ser vendido duas vezes. Esta garantia DEVE
ser aplicada no banco de dados, não apenas na aplicação:

- Constraint `UNIQUE` sobre (sessão, assento) para assentos ocupados — a corrida perdedora
  falha no PostgreSQL, não em uma checagem prévia em Python.
- Toda transição de estado de assento (livre → reservado → vendido → liberado) DEVE ocorrer
  dentro de uma transação de banco, com bloqueio explícito (`SELECT FOR UPDATE`) quando
  houver leitura-antes-de-escrita.
- Reserva não paga DEVE ter expiração definida, devolvendo o assento ao estoque.
- Pagamento recusado DEVE liberar o assento; pagamento aprovado DEVE emitir o ingresso.
  Não existe estado intermediário durável em que o assento esteja preso sem dono.

Toda feature que toque assentos, reservas ou pagamento DEVE ser acompanhada de um teste de
concorrência que dispare duas compras simultâneas do mesmo assento e prove que exatamente
uma vence.

**Racional**: é o requisito de backend mais fácil de alegar e mais difícil de provar. A
prova é o teste concorrente; sem ele, a garantia é apenas uma intenção.

### III. Ingresso Inforjável e Validação Única (NÃO NEGOCIÁVEL)

O código em QR NÃO PODE ser um identificador adivinhável (id sequencial, UUID cru, ou dado
do pedido concatenado). O conteúdo do QR DEVE ser assinado criptograficamente pelo servidor
com um segredo que nunca sai do backend, e a portaria DEVE verificar essa assinatura antes
de qualquer consulta ao banco.

A validação na portaria DEVE ser atômica e idempotente: a primeira leitura marca o ingresso
como utilizado; leituras subsequentes retornam "já utilizado" sem alterar estado. O
resultado exibido DEVE distinguir, sem ambiguidade, quatro desfechos: **válido**,
**inválido**, **já utilizado** e **sessão errada**.

O link de compartilhamento de ingresso DEVE conceder apenas visualização do ingresso — ele
nunca expõe a conta do comprador, o histórico de compras ou qualquer dado de pagamento.

**Racional**: um QR forjável ou uma validação que aceita o mesmo ingresso duas vezes derruba
o propósito inteiro da tela de portaria.

### IV. Papéis Explícitos e Autorização no Servidor

O sistema DEVE ter exatamente três papéis, com fronteiras rígidas:

- **Organizador** — cria e gerencia filmes, sessões, salas, capacidade e preços.
- **Cliente** — navega, reserva, paga e recebe ingressos.
- **Portaria** — valida ingressos na entrada. Não compra e não gerencia nada.

Toda decisão de autorização DEVE ser tomada no backend. Esconder um botão no front-end nunca
conta como controle de acesso: cada endpoint DEVE negar por padrão e exigir o papel correto,
e a suíte de testes DEVE cobrir pelo menos uma tentativa de acesso cruzado negada por papel
(ex.: cliente chamando endpoint de organizador → 403).

O seed do banco DEVE seguir a composição exigida pelo desafio: **1 organizador, 2 clientes,
1 usuário de portaria** e ao menos uma sessão publicada com ingressos disponíveis. As
credenciais desses quatro usuários DEVEM estar documentadas no README.

**Racional**: o avaliador vai percorrer o fluxo com essas contas sem montar nada do zero. O
seed não é conveniência de desenvolvimento — é parte da entrega.

### V. Interface Autoral (Anti AI-Slop)

A interface NÃO PODE ser a saída padrão não editada de uma ferramenta de geração. Cada tela
entregue DEVE carregar decisão explícita de layout, hierarquia e linguagem visual, e as
decisões de produto não óbvias DEVEM estar registradas conforme o Princípio VI.

Regras verificáveis:

- Sem texto de placeholder, lorem ipsum, ícone genérico sem propósito ou seção "coming soon"
  na entrega final.
- Paleta, tipografia e espaçamento DEVEM vir de tokens definidos uma vez e reutilizados —
  não de valores ad-hoc espalhados por componente.
- Todo estado de erro DEVE ter mensagem escrita para o usuário final em português, dizendo o
  que aconteceu e qual a próxima ação. "Something went wrong" é violação.
- O mapa de assentos DEVE comunicar visualmente, sem depender só de cor, a diferença entre
  disponível, selecionado, ocupado e indisponível.

**Racional**: o desafio afirma explicitamente que qualquer enunciado colado numa ferramenta
devolve um sistema inteiro, e que o que se avalia é o critério de quem conduziu. "O problema
não é a IA ter feito, é ninguém ter escolhido nada."

### VI. Rastro de Decisão Versionado

O processo faz parte do que está sendo avaliado e DEVE ser versionado junto com o código:

- **README** obrigatório, com passo a passo para configurar e executar a aplicação
  (incluindo configuração do PostgreSQL), credenciais de seed, variáveis de ambiente
  necessárias e uma seção honesta sobre o que não está funcionando como esperado. Omissão
  impacta negativamente a avaliação; escrever "não implementei X e aqui está o porquê" não.
- **Uso de IA** DEVE ser declarado: quais ferramentas, em que partes do projeto, e o que foi
  feito sem IA.
- **Artefatos de spec** (`.specify/`, specs, checklists, planos) DEVEM ser commitados no
  repositório, não descartados.
- **Commits** DEVEM ser incrementais ao longo do período, com mensagens descritivas. Um
  único commit gigante no último dia apaga a evidência de processo.
- Toda decisão que pareça estranha numa leitura rápida DEVE ter sua justificativa escrita no
  README ou em documento dedicado.

**Racional**: o desafio pede explicitamente que o processo seja contado, e afirma que
explicar o processo defende escolhas que, sem contexto, seriam mal interpretadas.

### VII. Isolamento da API Externa

O catálogo de filmes vem do TMDb, que é uma dependência de terceiro e DEVE ser tratada como
tal:

- A chave da API do TMDb NUNCA pode ser exposta ao front-end. Todas as chamadas passam pelo
  backend Django.
- Os dados de filme necessários para vender um ingresso (título, pôster, duração, sinopse)
  DEVEM ser persistidos localmente no momento em que o organizador cria a sessão. Uma queda
  do TMDb pode degradar a busca no catálogo, mas NUNCA pode impedir a compra, a exibição do
  ingresso ou a validação na portaria.
- Chamadas ao TMDb DEVEM ter timeout explícito e tratamento de erro que retorne mensagem
  útil ao organizador.

**Racional**: o fluxo crítico do sistema é vender e validar ingressos. Ele não pode ficar
refém da disponibilidade de um serviço externo durante a avaliação.

## Stack e Restrições Obrigatórias

Estas escolhas são fixas e não podem ser alteradas sem emenda formal a esta constitution:

| Camada | Tecnologia | Origem da restrição |
|---|---|---|
| Back-End | Django (Python) + Django REST Framework | Obrigatório pelo desafio (Python/Django é opção explícita) |
| Front-End | Next.js (React) | Obrigatório pelo desafio: "Front-End: React" |
| Banco de Dados | PostgreSQL | Escolha do projeto; qualquer distribuição é permitida |
| API Externa | TMDb (The Movie Database) | Obrigatório escolher Ticketmaster e/ou TMDb |
| Domínio | Cinema — filmes, sessões e mapa de assentos | Escopo definido para o projeto |

**Desvio registrado e resolvido**: a intenção inicial do projeto era usar Nuxt.js (Vue).
O PDF do desafio lista React como tecnologia obrigatória de front-end. A decisão foi trocar
para Next.js, que oferece o modelo mental equivalente (SSR, roteamento por arquivos) dentro
do ecossistema exigido. Nenhum código Vue DEVE entrar no repositório.

**Fluxo de reserva**: o desafio permite implementar mapa de assentos, quantidade de
ingressos, ou ambos. Este projeto implementa **mapa de assentos**, coerente com o domínio
de cinema. Venda por quantidade é opcional e só entra após o fluxo completo estar fechado.

**Pagamento**: DEVE ser simulado, sem transação financeira real, e DEVE contemplar tanto
confirmação quanto recusa como caminhos exercitáveis pelo avaliador. O caminho de recusa
não é opcional.

**Leitura do QR na portaria**: a leitura pela câmera é o caminho principal; a digitação
manual do código DEVE existir como alternativa sempre disponível, inclusive quando a câmera
for negada ou indisponível.

**Segredos**: nenhuma chave de API, `SECRET_KEY` do Django ou segredo de assinatura de
ingresso pode ser commitado. O repositório DEVE conter um `.env.example` completo.

## Fluxo de Desenvolvimento e Portões de Qualidade

**Ordem de construção obrigatória** — cada etapa só começa quando a anterior está utilizável
ponta a ponta:

1. Modelos, autenticação com os três papéis e seed dos quatro usuários.
2. Organizador cria filme/sessão a partir do TMDb, com preço e capacidade.
3. Cliente navega, seleciona assento e conclui pagamento simulado (aprovado e recusado).
4. Ingresso com QR assinado, área "Meus ingressos" e link de compartilhamento.
5. Tela de portaria com câmera, digitação manual e os quatro desfechos de validação.
6. Só então: busca e filtros, painel do organizador, cancelamento com devolução ao estoque,
   assentos em tempo real, Docker Compose, deploy.

**Portões de qualidade** — nenhuma feature é considerada concluída sem:

- Backend nega o acesso pelo papel errado (não apenas o front-end esconde a opção).
- Estados de erro e vazio implementados e escritos para humanos.
- README atualizado se a feature muda setup, variáveis de ambiente ou credenciais.
- Commit com mensagem descritiva.

**Testes**: testes completos não são obrigatórios pelo desafio, mas são explicitamente
avaliados como diferencial. São obrigatórios nesta constitution apenas onde os princípios
NÃO NEGOCIÁVEIS exigem prova: concorrência de assento (Princípio II), dupla validação de
ingresso e assinatura do QR (Princípio III), e negação de acesso por papel (Princípio IV).

**Prazo**: 7 dias corridos a partir do recebimento do desafio.
TODO(DATA_LIMITE_ENTREGA): fixar a data-limite absoluta — a data de recebimento do desafio
não foi registrada.

**Entrega**: repositório público no GitHub com histórico de commits ao longo do período,
enviado via formulário elitedev.verzel.com.br. Deploy (Vercel ou similar) não é obrigatório,
mas vale 1 ponto adicional na nota final e DEVE ser tentado se o fluxo completo fechar antes
do prazo.

## Governance

Esta constitution prevalece sobre preferências individuais, hábitos de projeto anterior e
sugestões de ferramentas de IA. Ferramentas de IA são bem-vindas e recomendadas pelo próprio
desafio, mas produzir código não autoriza ignorar estes princípios: o output DEVE ser
revisado contra esta constitution antes do commit.

**Emendas**: qualquer alteração de princípio, stack ou escopo DEVE ser feita editando este
arquivo, com incremento de versão e atualização do Sync Impact Report no topo. Mudança de
stack ou remoção de um princípio NÃO NEGOCIÁVEL exige registro explícito da justificativa no
README, porque contraria um requisito obrigatório do desafio.

**Versionamento** (semver):

- **MAJOR** — remoção ou redefinição incompatível de um princípio ou da stack obrigatória.
- **MINOR** — novo princípio ou seção, ou expansão material de orientação existente.
- **PATCH** — esclarecimento, correção de redação, refinamento não semântico.

**Conformidade**: antes de cada `/speckit-plan`, o "Constitution Check" DEVE ser preenchido
com os portões derivados destes princípios. Violações não são proibidas em absoluto, mas
DEVEM ser registradas na tabela de Complexity Tracking do plano com a alternativa mais
simples que foi rejeitada e o motivo. Violação não registrada é bug de processo.

**Revisão final**: antes da entrega, os sete princípios DEVEM ser percorridos um a um contra
a aplicação rodando, e qualquer desvio remanescente DEVE aparecer na seção de limitações
conhecidas do README.

**Version**: 1.0.0 | **Ratified**: 2026-08-10 | **Last Amended**: 2026-08-10
