"""2026 FIFA World Cup teams, groups, and CSV name mapping.

`csv_name` is how the team appears in the historical results dataset; `name`
is the display name used everywhere in this app.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WCTeam:
    csv_name: str
    name: str
    code: str
    group: str
    flag: str


WC2026_TEAMS: list[WCTeam] = [
    # Group A
    WCTeam("United States", "USA", "USA", "A", "🇺🇸"),
    WCTeam("Panama", "Panama", "PAN", "A", "🇵🇦"),
    WCTeam("Uruguay", "Uruguay", "URU", "A", "🇺🇾"),
    WCTeam("Bolivia", "Bolivia", "BOL", "A", "🇧🇴"),
    # Group B
    WCTeam("Mexico", "Mexico", "MEX", "B", "🇲🇽"),
    WCTeam("Jamaica", "Jamaica", "JAM", "B", "🇯🇲"),
    WCTeam("Venezuela", "Venezuela", "VEN", "B", "🇻🇪"),
    WCTeam("Ecuador", "Ecuador", "ECU", "B", "🇪🇨"),
    # Group C
    WCTeam("Canada", "Canada", "CAN", "C", "🇨🇦"),
    WCTeam("Honduras", "Honduras", "HON", "C", "🇭🇳"),
    WCTeam("New Zealand", "New Zealand", "NZL", "C", "🇳🇿"),
    WCTeam("Malaysia", "Malaysia", "MAS", "C", "🇲🇾"),
    # Group D
    WCTeam("Brazil", "Brazil", "BRA", "D", "🇧🇷"),
    WCTeam("Colombia", "Colombia", "COL", "D", "🇨🇴"),
    WCTeam("Japan", "Japan", "JPN", "D", "🇯🇵"),
    WCTeam("Morocco", "Morocco", "MAR", "D", "🇲🇦"),
    # Group E
    WCTeam("Argentina", "Argentina", "ARG", "E", "🇦🇷"),
    WCTeam("Chile", "Chile", "CHI", "E", "🇨🇱"),
    WCTeam("Peru", "Peru", "PER", "E", "🇵🇪"),
    WCTeam("Cameroon", "Cameroon", "CMR", "E", "🇨🇲"),
    # Group F
    WCTeam("France", "France", "FRA", "F", "🇫🇷"),
    WCTeam("Algeria", "Algeria", "ALG", "F", "🇩🇿"),
    WCTeam("Saudi Arabia", "Saudi Arabia", "KSA", "F", "🇸🇦"),
    WCTeam("Indonesia", "Indonesia", "IDN", "F", "🇮🇩"),
    # Group G
    WCTeam("England", "England", "ENG", "G", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    WCTeam("Serbia", "Serbia", "SRB", "G", "🇷🇸"),
    WCTeam("Senegal", "Senegal", "SEN", "G", "🇸🇳"),
    WCTeam("Tunisia", "Tunisia", "TUN", "G", "🇹🇳"),
    # Group H
    WCTeam("Germany", "Germany", "GER", "H", "🇩🇪"),
    WCTeam("Poland", "Poland", "POL", "H", "🇵🇱"),
    WCTeam("Costa Rica", "Costa Rica", "CRC", "H", "🇨🇷"),
    WCTeam("Ghana", "Ghana", "GHA", "H", "🇬🇭"),
    # Group I
    WCTeam("Spain", "Spain", "ESP", "I", "🇪🇸"),
    WCTeam("Egypt", "Egypt", "EGY", "I", "🇪🇬"),
    WCTeam("Nigeria", "Nigeria", "NGA", "I", "🇳🇬"),
    WCTeam("El Salvador", "El Salvador", "SLV", "I", "🇸🇻"),
    # Group J
    WCTeam("Portugal", "Portugal", "POR", "J", "🇵🇹"),
    WCTeam("Netherlands", "Netherlands", "NED", "J", "🇳🇱"),
    WCTeam("South Korea", "South Korea", "KOR", "J", "🇰🇷"),
    WCTeam("Iran", "Iran", "IRN", "J", "🇮🇷"),
    # Group K
    WCTeam("Belgium", "Belgium", "BEL", "K", "🇧🇪"),
    WCTeam("Croatia", "Croatia", "CRO", "K", "🇭🇷"),
    WCTeam("Australia", "Australia", "AUS", "K", "🇦🇺"),
    WCTeam("Qatar", "Qatar", "QAT", "K", "🇶🇦"),
    # Group L
    WCTeam("Italy", "Italy", "ITA", "L", "🇮🇹"),
    WCTeam("Turkey", "Turkey", "TUR", "L", "🇹🇷"),
    WCTeam("Austria", "Austria", "AUT", "L", "🇦🇹"),
    WCTeam("Iraq", "Iraq", "IRQ", "L", "🇮🇶"),
]

GROUPS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]


def find_team(query: str) -> WCTeam | None:
    """Match a team by display name or code, case-insensitively."""
    q = query.strip().lower()
    for t in WC2026_TEAMS:
        if t.name.lower() == q or t.code.lower() == q:
            return t
    # Fall back to a partial / prefix match on the display name.
    for t in WC2026_TEAMS:
        if q and (q in t.name.lower() or t.name.lower().startswith(q)):
            return t
    return None
