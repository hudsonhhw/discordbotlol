from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp


PLATFORM_TO_REGIONAL = {
    "BR1": "americas",
    "LA1": "americas",
    "LA2": "americas",
    "NA1": "americas",
    "EUN1": "europe",
    "EUW1": "europe",
    "TR1": "europe",
    "RU": "europe",
    "JP1": "asia",
    "KR": "asia",
    "OC1": "sea",
    "PH2": "sea",
    "SG2": "sea",
    "TH2": "sea",
    "TW2": "sea",
    "VN2": "sea",
}


QUEUE_NAMES = {
    400: "Normal Draft",
    420: "Ranked Solo/Duo",
    430: "Normal Blind",
    440: "Ranked Flex",
    450: "ARAM",
    700: "Clash",
    720: "ARAM Clash",
    830: "Co-op vs AI Intro",
    840: "Co-op vs AI Beginner",
    850: "Co-op vs AI Intermediate",
    900: "URF",
    1020: "One for All",
    1090: "Teamfight Tactics Normal",
    1100: "Ranked TFT",
    1400: "Ultimate Spellbook",
    1700: "Arena",
    1710: "Arena",
    1810: "Swiftplay",
    1900: "URF",
}


class RiotAPIError(Exception):
    """Raised when Riot API returns an error or unexpected payload."""


@dataclass(slots=True)
class PlayerLookup:
    account: dict[str, Any]
    summoner: dict[str, Any]


class RiotAPI:
    def __init__(self, api_key: str, session: aiohttp.ClientSession) -> None:
        self.api_key = api_key
        self.session = session

    @staticmethod
    def get_regional_route(platform: str) -> str:
        normalized = platform.upper().strip()
        regional = PLATFORM_TO_REGIONAL.get(normalized)
        if not regional:
            raise RiotAPIError(
                f"Platform '{platform}' nao suportada. Use uma entre: {', '.join(sorted(PLATFORM_TO_REGIONAL))}."
            )
        return regional

    async def _request(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        headers = {"X-Riot-Token": self.api_key}
        async with self.session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=20)) as response:
            if response.status == 200:
                return await response.json()

            if response.status == 404:
                raise RiotAPIError("Jogador ou partida nao encontrado.")
            if response.status == 401:
                raise RiotAPIError("Chave da Riot invalida ou expirada.")
            if response.status == 403:
                raise RiotAPIError("Acesso negado pela Riot API.")
            if response.status == 429:
                retry_after = response.headers.get("Retry-After", "alguns segundos")
                raise RiotAPIError(f"Limite de requisicoes atingido. Tente novamente em {retry_after}.")

            try:
                payload = await response.json()
            except Exception:
                payload = await response.text()
            raise RiotAPIError(f"Erro da Riot API ({response.status}): {payload}")

    async def get_account_by_riot_id(self, game_name: str, tag_line: str, regional_route: str) -> dict[str, Any]:
        url = (
            f"https://{regional_route}.api.riotgames.com/riot/account/v1/accounts/"
            f"by-riot-id/{game_name}/{tag_line}"
        )
        return await self._request(url)

    async def get_summoner_by_puuid(self, platform: str, puuid: str) -> dict[str, Any]:
        url = f"https://{platform.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        return await self._request(url)

    async def get_ranked_entries(self, platform: str, encrypted_summoner_id: str) -> list[dict[str, Any]]:
        url = (
            f"https://{platform.lower()}.api.riotgames.com/lol/league/v4/entries/"
            f"by-summoner/{encrypted_summoner_id}"
        )
        return await self._request(url)

    async def get_match_ids(
        self,
        regional_route: str,
        puuid: str,
        *,
        start: int = 0,
        count: int = 5,
    ) -> list[str]:
        url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"start": start, "count": count}
        return await self._request(url, params=params)

    async def get_match(self, regional_route: str, match_id: str) -> dict[str, Any]:
        url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return await self._request(url)

    async def lookup_player(self, game_name: str, tag_line: str, platform: str) -> PlayerLookup:
        regional_route = self.get_regional_route(platform)
        account = await self.get_account_by_riot_id(game_name, tag_line, regional_route)
        summoner = await self.get_summoner_by_puuid(platform, account["puuid"])
        return PlayerLookup(account=account, summoner=summoner)


def find_participant(match_data: dict[str, Any], puuid: str) -> dict[str, Any]:
    participants = match_data.get("info", {}).get("participants", [])
    for participant in participants:
        if participant.get("puuid") == puuid:
            return participant
    raise RiotAPIError("Nao foi possivel localizar o jogador dentro dos dados da partida.")


def queue_name(queue_id: int | None) -> str:
    if queue_id is None:
        return "Fila desconhecida"
    return QUEUE_NAMES.get(queue_id, f"Fila {queue_id}")
