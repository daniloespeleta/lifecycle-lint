# Um linter para jornadas de CRM

*Case técnico. Python, sem dependência além de PyYAML, 21 testes, CI que roda o linter contra as próprias jornadas de exemplo. Código aberto em [github.com/daniloespeleta/lifecycle-lint](https://github.com/daniloespeleta/lifecycle-lint). O método de leitura de jornada por trás das regras é o LEEA. A base técnica vem de Claude Code in Action e AI Fluency (Anthropic) e Agents and Workflows (OpenAI Academy), que aparecem aqui do jeito que certificação deve aparecer: como nota de topo, antes de sair do caminho.*

---

Jornada de CRM quebrada raramente quebra. Ela roda.

Esse é o problema inteiro em uma frase. Quando um fluxo de automação tem defeito, ele não cai, não estoura erro, não acende alerta. Ele continua enviando. As mensagens saem, o relatório fecha em verde, e o defeito aparece meses depois na taxa de descadastro. Que é a métrica que não volta.

Software resolveu isso há trinta anos com linter: um programa que lê o código e aponta o erro que o compilador aceita mas o humano vai pagar. CRM nunca teve equivalente. Construí um.

## O defeito que ninguém encontra numa revisão de fluxo

Montei três jornadas de uma edtech fictícia, do tipo que qualquer operação de lifecycle tem rodando agora. Onboarding de novo aluno. Reengajamento de inativos. Recuperação de checkout abandonado. Cada uma passaria numa revisão isolada, nenhuma tem erro grosseiro.

Juntas, elas cobram nove toques por semana da mesma pessoa.

Porque o reengajamento roda sobre "inativos há mais de 60 dias", e o checkout roda sobre "inativos há mais de 60 dias que abandonaram carrinho". Times diferentes, objetivos diferentes, calendários diferentes. Mesma gente. Ninguém decidiu bombardear esse contato. A soma decidiu.

É o defeito mais caro de uma operação de CRM e o único que nenhuma revisão de fluxo único encontra, porque ele não existe dentro de nenhum dos fluxos. Existe entre eles.

## A decisão de projeto

O linter tem doze regras. Dez olham uma jornada, duas olham o portfólio inteiro. As duas do portfólio são a razão de a ferramenta existir.

Para comparar audiências, a escolha ingênua seria índice de Jaccard, que mede interseção sobre união. Ele erra exatamente o caso que importa. "Inativos há 60 dias" e "inativos há 60 dias que abandonaram checkout" descrevem gente que se encontra, e Jaccard leria 0.5 só porque um dos lados tem um filtro a mais. Trocando por coeficiente de sobreposição, que divide pelo menor dos dois conjuntos, o resultado é 1.0. Que é a resposta certa: todo mundo do segundo grupo está no primeiro.

Uma linha de código. A diferença entre a ferramenta funcionar e a ferramenta não servir para nada.

A segunda decisão foi a unidade de pressão. Não dá para contar mensagens, porque um push não custa o mesmo que um e-mail e um WhatsApp custa o dobro. Então cada canal tem peso, e a pressão da jornada é a carga ponderada dentro de uma janela de sete dias. Com piso no denominador, senão um fluxo de carrinho abandonado com três toques em 24 horas seria lido como vinte e um toques por semana. O que é falso, porque a jornada acaba.

Falso positivo é o que mata linter. O time desliga na segunda semana e nunca mais liga.

## O que o LLM faz aqui, e o que não faz

Tem uma flag `--explain` que pede ao Claude um resumo em prosa dos achados, para levar à reunião de revisão. Ela é opcional, e é aí que está a decisão.

O diagnóstico inteiro é determinístico. Nenhuma regra chama modelo. Sem chave de API, o linter continua correto, só fica menos falante.

Colocar um modelo no caminho crítico de uma auditoria troca resultado reproduzível por resultado plausível. E auditoria plausível não decide se um fluxo entra no ar. A régua que uso é simples: onde existe regra, escrevo regra. O modelo entra na leitura, na síntese, na tradução do achado para a linguagem de quem vai decidir. Não entra no achado.

Boa parte do que hoje se chama de IA aplicada a marketing é o contrário disso. Modelo no lugar onde caberia um `if`, com a incerteza embutida de brinde.

## O que a ferramenta prova

Que régua boa e régua ruim se separam por conhecimento tácito. Critério de saída, supressão, teto de frequência, grupo de controle: quatro campos que a interface da ferramenta de automação não pergunta, e que por isso ninguém preenche. O linter pergunta.

Conhecimento tácito não escala em revisão manual. Escala quando vira regra executável, com nome, severidade, correção sugerida e um exit code que barra o merge.

Nem toda régua deveria existir. Nem toda régua que existe foi lida por alguém.

Operação de CRM madura não é a que erra menos. É a que descobre o erro antes do envio.
