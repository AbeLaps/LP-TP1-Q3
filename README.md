# Traabalho Prático 2 - Linguages de Programação

Este projeto realiza uma simulação do jogo *Nota Secreta* baseado no jogo Dixit. Esse é um jogo de associação de músicas em que os jogadores são agentes implementados. Cada agente possui uma mão de cartas de músicas brasileiras e, a cada rodada, um agente assume o papel de **narrador**: escolhe uma de suas cartas, gera uma **dica com no máximo 6 palavras** baseada na letra, e os demais agentes tentam adivinhar qual música é a do narrador votando entre todas as cartas jogadas naquela rodada.

O jogo termina quando algum agente atinge a **pontuação-alvo** (padrão: 30 pontos).

## Como executar

### Setup inicial

Crie um ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```
Instale as dependências:

```bash
python3 -m pip install -r requirements.txt
```

Instale o modelo gguf:

```bash
wget https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf
```

## Rodar o jogo

#### Existem 2 configurações de comportamento dos agentes:
- Modo mock: 
```python
 python3 run_game.py --force-mock 
```
- Com modelos GGUF real:
```python
 python3 run_game.py --model <<path para o modelo .gguf instalado anteriormente>> 
```
#### Configuração de quais agentes vão jogar
- Com todos agentes estratégicos (é possível utilizar modelos GGUF reais não apenas o modo mock)
```python
 python3 run_game.py --all-strategic --force-mock
```
- Para personalização dos agentes jogadores deve ser feito o processo manual executado por ```text run_game.py ``` esse processo está descrito no README.md oficial do trabalho