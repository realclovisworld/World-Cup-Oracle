"""Pydantic request/response schemas (IMPLEMENTATION.md §1.3).

Field names adapted to the actual model modules. The bracket schemas are
defined here so Phase 3 (api/bracket.py) can populate them.
"""

from typing import Optional

from pydantic import BaseModel


class MatchupRequest(BaseModel):
    team_a: str  # team code or display name
    team_b: str


class TeamRow(BaseModel):
    code: str
    name: str
    flag: str
    group: str
    elo: int


class OddsRow(TeamRow):
    p_r16: float
    p_qf: float
    p_sf: float
    p_final: float
    p_title: float


class MatchupResult(BaseModel):
    win_a: float
    draw: float
    win_b: float
    xg_a: float
    xg_b: float
    score_a: int
    score_b: int


class BracketMatch(BaseModel):
    team_a: str
    team_b: str
    flag_a: str
    flag_b: str
    code_a: str = ""             # 3-letter code, for flag images (IMPLEMENTATION_FIFA)
    code_b: str = ""
    score_a: int
    score_b: int
    pens_a: Optional[int] = None  # penalty-shootout score, when a level tie
    pens_b: Optional[int] = None
    winner: str                  # 'a' or 'b'
    win_prob: float              # winner's probability (0–100); 100 for played
    xg_a: Optional[float]        # None when is_actual is True
    xg_b: Optional[float]
    is_actual: bool = False      # True = real result, False = prediction
    date: Optional[str] = None   # "2026-07-04" (played or scheduled)
    venue: Optional[str] = None
    match_no: Optional[str] = None  # "M89" — FIFA match numbering


class BracketRound(BaseModel):
    name: str
    matches: list[BracketMatch]


class BracketData(BaseModel):
    rounds: list[BracketRound]


class StatusResponse(BaseModel):
    ready: bool
    running: bool
    n_sims: int
    cached_at: Optional[float]
    last_result_date: Optional[str] = None  # max date of live results applied
