"""Contratos de lectura; campos opcionales permanecen desconocidos, no se rellenan con cero."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class APIModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True, hide_input_in_errors=True)


class Player(APIModel):
    id: StrictInt = Field(gt=0)
    name: str
    slug: str | None = None
    team_id: StrictInt | None = Field(default=None, alias="teamID")
    position: StrictInt | None = None
    price: StrictInt | None = None
    price_increment: StrictInt | None = Field(default=None, alias="priceIncrement")
    points: StrictInt | None = None
    status: str | None = None
    status_info: str | None = Field(default=None, alias="statusInfo")
    fitness: list[StrictInt | str | None] | None = None
    played_home: StrictInt | None = Field(default=None, alias="playedHome")
    played_away: StrictInt | None = Field(default=None, alias="playedAway")


class Team(APIModel):
    id: StrictInt
    name: str
    next_games: list[dict[str, Any]] | None = Field(default=None, alias="nextGames")


class Season(APIModel):
    id: str | StrictInt
    name: str
    slug: str


class Score(APIModel):
    id: StrictInt
    name: str
    kind: str | None = None


class Catalog(APIModel):
    id: StrictInt
    slug: str
    name: str
    currency: str
    score_id: StrictInt = Field(alias="scoreID")
    scores: list[Score]
    season: Season
    players: dict[str, Player]
    teams: dict[str, Team]
    update: StrictInt | None = None


class OwnedPlayer(APIModel):
    id: StrictInt = Field(gt=0)
    owner: dict[str, Any] | None = None


class Lineup(APIModel):
    formation: str | None = Field(default=None, alias="type")
    player_ids: list[StrictInt | None] = Field(alias="playersID")


class UserData(APIModel):
    id: StrictInt = Field(gt=0)
    name: str | None = None
    players: list[OwnedPlayer]
    lineup: Lineup | None = None
    balance: StrictInt | None = None


class Member(APIModel):
    id: StrictInt = Field(ge=0)
    name: str | None = None


class Sale(APIModel):
    player: OwnedPlayer
    user: Member | None = None
    price: StrictInt | None = None
    until: StrictInt | None = None


class Offer(APIModel):
    id: StrictInt = Field(gt=0)
    requested_players: list[StrictInt] = Field(alias="requestedPlayers")
    amount: StrictInt | None = None
    sender: Member | None = Field(default=None, alias="from")
    status: str | None = None
    type: str | None = None
    until: StrictInt | None = None


class MarketStatus(APIModel):
    balance: StrictInt | None = None
    maximum_bid: StrictInt | None = Field(default=None, alias="maximumBid")


class MarketData(APIModel):
    sales: list[Sale]
    offers: list[Offer]
    status: MarketStatus


class League(APIModel):
    id: StrictInt = Field(gt=0)
    name: str | None = None
    mode: str | None = None
    type: str | None = None
    market_mode: str | None = Field(default=None, alias="marketMode")
    score_id: StrictInt | None = Field(default=None, alias="scoreID")
    score: StrictInt | dict[str, Any] | None = None
    settings: dict[str, Any] | None = None


class Event(APIModel):
    type: str
    date: StrictInt | None = None
    round: dict[str, Any] | None = None


class HomeData(APIModel):
    league: League
    user: Member
    competition: str | dict[str, Any] | None = None
    events: list[Event] | None = None


class PlayerDetail(APIModel):
    id: StrictInt = Field(gt=0)
    name: str
    slug: str
    score_id: StrictInt | None = Field(default=None, alias="scoreID")
    competition: dict[str, Any] | None = None
    team: dict[str, Any] | None = None
    reports: list[dict[str, Any]] | None = None
    prices: list[list[StrictInt]] | None = None
    news: list[dict[str, Any]] | None = None


class Evolution(APIModel):
    competition: dict[str, Any]
    values: list[list[StrictInt]]
    ups: list[dict[str, Any]] | None = None
    downs: list[dict[str, Any]] | None = None
