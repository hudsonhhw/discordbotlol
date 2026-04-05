from __future__ import annotations

import asyncio
import os
from typing import Iterable

import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

from riot_api import RiotAPI, RiotAPIError, find_participant, queue_name

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
DEFAULT_PLATFORM = os.getenv("DEFAULT_PLATFORM", "BR1").upper()

PLATFORM_CHOICES = [
    app_commands.Choice(name=platform, value=platform)
    for platform in [
        "BR1",
        "LA1",
        "LA2",
        "NA1",
        "EUN1",
        "EUW1",
        "TR1",
        "RU",
        "JP1",
        "KR",
        "OC1",
        "PH2",
        "SG2",
        "TH2",
        "TW2",
        "VN2",
    ]
]


class MatchHistoryBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.session: aiohttp.ClientSession | None = None
        self.riot_api: RiotAPI | None = None

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        self.riot_api = RiotAPI(RIOT_API_KEY, self.session)
        await self.tree.sync()

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()
        await super().close()


bot = MatchHistoryBot()


async def safe_defer(interaction: discord.Interaction) -> None:
    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)


def build_error_embed(message: str) -> discord.Embed:
    return discord.Embed(title="Erro", description=message, color=discord.Color.red())


def format_ranked_entries(entries: Iterable[dict]) -> str:
    entries = list(entries)
    if not entries:
        return "Sem dados ranqueados no momento."

    lines: list[str] = []
    for entry in entries:
        queue_type = entry.get("queueType", "UNKNOWN_QUEUE")
        queue_label = {
            "RANKED_SOLO_5x5": "Solo/Duo",
            "RANKED_FLEX_SR": "Flex",
            "RANKED_TFT": "TFT",
        }.get(queue_type, queue_type)
        tier = entry.get("tier", "UNRANKED")
        rank = entry.get("rank", "")
        league_points = entry.get("leaguePoints", 0)
        wins = entry.get("wins", 0)
        losses = entry.get("losses", 0)
        lines.append(f"**{queue_label}**: {tier} {rank} - {league_points} LP ({wins}W/{losses}L)")
    return "\n".join(lines)


def match_duration_minutes(match_info: dict) -> str:
    duration = match_info.get("gameDuration", 0)
    minutes, seconds = divmod(int(duration), 60)
    return f"{minutes}m {seconds:02d}s"


def build_player_embed(account: dict, summoner: dict, platform: str, ranked_entries: list[dict]) -> discord.Embed:
    riot_id = f"{account.get('gameName', 'Unknown')}#{account.get('tagLine', 'Unknown')}"
    embed = discord.Embed(
        title=f"Perfil de {riot_id}",
        description=f"Plataforma: **{platform}**",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Nivel", value=str(summoner.get("summonerLevel", "-")), inline=True)
    embed.add_field(name="PUUID", value=f"`{account.get('puuid', '-')[:20]}...`", inline=False)
    embed.add_field(name="Ranked", value=format_ranked_entries(ranked_entries), inline=False)
    return embed


def build_recent_matches_embed(account: dict, platform: str, matches: list[dict]) -> discord.Embed:
    riot_id = f"{account.get('gameName', 'Unknown')}#{account.get('tagLine', 'Unknown')}"
    embed = discord.Embed(
        title=f"Historico recente - {riot_id}",
        description=f"Plataforma: **{platform}**",
        color=discord.Color.green(),
    )

    if not matches:
        embed.add_field(name="Partidas", value="Nenhuma partida encontrada.", inline=False)
        return embed

    for index, match in enumerate(matches, start=1):
        info = match["match"]
        player = match["player"]
        result = "Vitoria" if player.get("win") else "Derrota"
        queue = queue_name(info.get("queueId"))
        champion = player.get("championName", "Unknown")
        kda = f"{player.get('kills', 0)}/{player.get('deaths', 0)}/{player.get('assists', 0)}"
        cs = player.get("totalMinionsKilled", 0) + player.get("neutralMinionsKilled", 0)
        duration = match_duration_minutes(info)
        value = (
            f"**Resultado:** {result}\n"
            f"**Fila:** {queue}\n"
            f"**Campeao:** {champion}\n"
            f"**KDA:** {kda}\n"
            f"**Farm:** {cs}\n"
            f"**Duracao:** {duration}"
        )
        embed.add_field(name=f"#{index} - {info.get('gameMode', 'Unknown')}", value=value, inline=False)

    return embed


@bot.tree.command(name="ping", description="Verifica se o bot esta online.")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Pong!", ephemeral=True)


@bot.tree.command(name="player", description="Busca perfil e ranked de um jogador pelo Riot ID.")
@app_commands.describe(
    game_name="Parte antes do # no Riot ID",
    tag_line="Parte depois do # no Riot ID",
    platform="Servidor/plataforma, ex.: BR1",
)
@app_commands.choices(platform=PLATFORM_CHOICES)
async def player(
    interaction: discord.Interaction,
    game_name: str,
    tag_line: str,
    platform: app_commands.Choice[str] | None = None,
) -> None:
    await safe_defer(interaction)

    selected_platform = (platform.value if platform else DEFAULT_PLATFORM).upper()

    try:
        assert bot.riot_api is not None
        lookup = await bot.riot_api.lookup_player(game_name, tag_line, selected_platform)
        ranked_entries = await bot.riot_api.get_ranked_entries(selected_platform, lookup.summoner["id"])
        embed = build_player_embed(lookup.account, lookup.summoner, selected_platform, ranked_entries)
        await interaction.followup.send(embed=embed)
    except RiotAPIError as exc:
        await interaction.followup.send(embed=build_error_embed(str(exc)), ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(
            embed=build_error_embed(f"Erro interno ao consultar jogador: {exc}"),
            ephemeral=True,
        )


@bot.tree.command(name="recent", description="Mostra as ultimas partidas de um jogador pelo Riot ID.")
@app_commands.describe(
    game_name="Parte antes do # no Riot ID",
    tag_line="Parte depois do # no Riot ID",
    platform="Servidor/plataforma, ex.: BR1",
    count="Quantidade de partidas para exibir (1 a 10)",
)
@app_commands.choices(platform=PLATFORM_CHOICES)
async def recent(
    interaction: discord.Interaction,
    game_name: str,
    tag_line: str,
    count: app_commands.Range[int, 1, 10] = 5,
    platform: app_commands.Choice[str] | None = None,
) -> None:
    await safe_defer(interaction)
    selected_platform = (platform.value if platform else DEFAULT_PLATFORM).upper()

    try:
        assert bot.riot_api is not None
        regional_route = bot.riot_api.get_regional_route(selected_platform)
        lookup = await bot.riot_api.lookup_player(game_name, tag_line, selected_platform)
        match_ids = await bot.riot_api.get_match_ids(regional_route, lookup.account["puuid"], count=count)

        matches: list[dict] = []
        for match_id in match_ids:
            match_data = await bot.riot_api.get_match(regional_route, match_id)
            participant = find_participant(match_data, lookup.account["puuid"])
            matches.append({"match": match_data.get("info", {}), "player": participant})

        embed = build_recent_matches_embed(lookup.account, selected_platform, matches)
        await interaction.followup.send(embed=embed)
    except RiotAPIError as exc:
        await interaction.followup.send(embed=build_error_embed(str(exc)), ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(
            embed=build_error_embed(f"Erro interno ao consultar partidas: {exc}"),
            ephemeral=True,
        )


async def main() -> None:
    if not DISCORD_TOKEN:
        raise RuntimeError("Defina DISCORD_TOKEN no arquivo .env")
    if not RIOT_API_KEY:
        raise RuntimeError("Defina RIOT_API_KEY no arquivo .env")

    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
