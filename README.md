# Discord Match History Bot

Bot de Discord em Python para consultar perfil de jogador, ranked e historico recente de partidas de **League of Legends** usando a **Riot API**.

## Recursos

- Comando `/player` para buscar perfil e elos ranqueados
- Comando `/recent` para listar ultimas partidas
- Integração com Riot ID (`gameName#tagLine`)
- Estrutura pronta para subir no GitHub
- Variaveis sensiveis protegidas via `.env`

## Estrutura

```bash
.
├── bot.py
├── riot_api.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Requisitos

- Python 3.11+
- Uma aplicacao/bot criada no Discord Developer Portal
- Uma chave da Riot Developer API

## Instalacao

```bash
git clone https://github.com/SEU_USUARIO/discord-match-history-bot.git
cd discord-match-history-bot
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Configuracao

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Preencha:

```env
DISCORD_TOKEN=seu_token_do_discord
RIOT_API_KEY=sua_chave_da_riot
DEFAULT_PLATFORM=BR1
```

## Como rodar

```bash
python bot.py
```

## Comandos do bot

### `/ping`
Verifica se o bot esta online.

### `/player`
Busca o perfil e as filas ranqueadas de um jogador.

Exemplo de uso:
- `game_name`: Faker
- `tag_line`: KR1
- `platform`: KR

### `/recent`
Busca as ultimas partidas de um jogador.

Exemplo de uso:
- `game_name`: apexshop
- `tag_line`: BR1
- `platform`: BR1
- `count`: 5

## Como publicar no GitHub

1. Crie um repositorio vazio no GitHub.
2. Dentro da pasta do projeto, rode:

```bash
git init
git add .
git commit -m "feat: initial discord match history bot"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/discord-match-history-bot.git
git push -u origin main
```

## Observacoes importantes

- Nao suba seu arquivo `.env` para o GitHub.
- Chaves de desenvolvimento da Riot expiram; se parar de funcionar, gere uma nova.
- Para aprovacao de produto, descreva o bot como uma ferramenta de consulta de historico, perfil e estatisticas basicas, sem oferecer vantagem competitiva indevida.

## Aviso legal

Discord Match History Bot is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
