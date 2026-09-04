# Um linter para jornadas de CRM

*Case técnico. Python, sem dependência além de PyYAML, 21 testes, CI que roda o linter contra as próprias jornadas de exemplo. Código aberto em [github.com/daniloespeleta/lifecycle-lint](https://github.com/daniloespeleta/lifecycle-lint). O método de leitura de jornada por trás das regras é o LEEA. A base técnica vem de Claude Code in Action e AI Fluency (Anthropic) e Agents and Workflows (OpenAI Academy).*

---

Uma jornada de CRM com defeito de construção continua executando. A falha não interrompe o fluxo nem gera alerta: as mensagens saem, o relatório fecha com número positivo, e o efeito aparece semanas depois na taxa de descadastro, que é uma métrica sem reversão.

Engenharia de software resolveu essa classe de problema com linters: programas que leem o código e apontam o erro que o compilador aceita mas que causa dano em produção. Operação de CRM não tem ferramenta equivalente, então construí uma.

## O defeito que revisão de fluxo não encontra

Montei três jornadas de uma edtech fictícia, do tipo que qualquer operação de lifecycle tem rodando: onboarding de novo aluno, reengajamento de inativos, recuperação de checkout abandonado. Cada uma passa em revisão isolada, nenhuma tem erro grosseiro.

Em conjunto, elas cobram nove toques por semana do mesmo contato.

O reengajamento roda sobre "inativos há mais de 60 dias". O checkout roda sobre "inativos há mais de 60 dias que abandonaram carrinho". Times diferentes, objetivos diferentes, calendários diferentes, e o mesmo grupo de pessoas na base. A carga somada não aparece em nenhum dos dois arquivos, porque ela só existe na interseção.

É o defeito mais caro de uma operação de CRM e o que nenhuma revisão de fluxo individual detecta.

## As decisões de cálculo

O linter tem doze regras. Dez avaliam uma jornada isolada, duas avaliam o conjunto de jornadas ativas. As duas de conjunto são a razão da ferramenta existir.

Para comparar audiências, a escolha padrão seria índice de Jaccard, que divide a interseção pela união. Ele subestima o caso relevante aqui. "Inativos há 60 dias" e "inativos há 60 dias que abandonaram checkout" alcançam o mesmo grupo de pessoas, e Jaccard retorna 0.5 porque o segundo conjunto tem um filtro a mais. Trocando por coeficiente de sobreposição, que divide pela cardinalidade do menor conjunto, o resultado é 1.0, que descreve corretamente a relação: o segundo grupo está contido no primeiro.

Uma linha de código, e é ela que determina se a regra encontra ou não o caso que motivou a ferramenta.

A segunda decisão foi a unidade de pressão. Contagem simples de mensagens não serve, porque push, SMS e e-mail têm custo de atenção diferente. Cada canal recebeu um peso, e a pressão da jornada é a carga ponderada dentro de uma janela de sete dias, com piso de sete dias no denominador. Sem o piso, um fluxo de carrinho abandonado com três toques em 24 horas seria lido como 21 toques por semana, número que não ocorre porque a jornada termina.

Falso positivo é o motivo mais comum de abandono de linter, e ajustar essa fórmula foi o que mais consumiu tempo no projeto.

## Onde o modelo entra

A flag `--explain` envia os achados ao Claude e imprime um resumo em prosa, para levar à reunião de revisão. Ela é opcional, e a arquitetura em volta dela é a decisão que importa.

O diagnóstico é integralmente determinístico. Nenhuma das doze regras chama modelo. Sem chave de API, o linter roda igual e a flag apenas avisa que a explicação está indisponível.

Um LLM no caminho crítico de uma auditoria substitui um resultado reproduzível por um resultado que varia entre execuções. Auditoria com essa propriedade não serve como critério de publicação. O critério que apliquei: onde existe regra determinável, escrevo regra. O modelo entra na síntese e na tradução do achado para a linguagem de quem decide.

Parte relevante do que se apresenta hoje como IA aplicada a marketing inverte essa ordem, colocando modelo onde caberia uma condicional, e herdando a variância junto.

## O que a ferramenta demonstra

Que a diferença entre uma régua bem construída e uma malfeita está em conhecimento tácito de operação. Critério de saída, lista de supressão, teto de frequência e grupo de controle são quatro campos que as interfaces de automação não solicitam, e que por isso ficam em branco. O linter os exige.

Conhecimento tácito não escala em revisão manual. Escala quando vira regra executável, com identificador, severidade, correção sugerida e exit code que barra o merge.
