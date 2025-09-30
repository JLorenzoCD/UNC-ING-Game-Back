import uuid
from datetime       import date
from app.matches.models  import Match, MatchStatus
from app.matches.schemas import MatchOut, MatchIn
from app.matches.dto     import MatchDTO
from app.matches.utils   import db_match_2_match_schema
from app.player.models   import Player


def test_create_match(db_session):
    """
    Creamos un Player owner de Match
    Testeamos la correcta creación de Match con su owner_id
    Testeamos schemas MatchIn y MatchOut
    """

    # ─── Crear Player owner de Match ────────────────────────────────
    new_player_owner = Player(
        name     = "Elian",
        avatar   = "Mao Zedong",
        birthday = date(2000, 8, 22)
    )
    db_session.add(new_player_owner)
    db_session.commit()
    db_session.refresh(new_player_owner)

    # ─── Crear Match ───────────────────────────────────────────────
    new_match = Match(
        name        = "AGE 3",
        min_players = 4,
        max_players = 6,
        owner_id    = new_player_owner.id
    )
    db_session.add(new_match)
    db_session.commit()
    db_session.refresh(new_match)

    # ─── Testeo de entidad Match ───────────────────────────────────
    assert new_match.name                 == "AGE 3"
    assert new_match.min_players          == 4
    assert new_match.max_players          == 6
    assert new_match.owner_id is not None
    assert new_match.owner_id             == new_player_owner.id
    assert new_match.status               == MatchStatus.WAITING
    assert new_match.current_player_order == 1

    # ─── Schema de Match ───────────────────────────────────────────
    new_schemas_match = db_match_2_match_schema(new_match)

    # Testeo de schema
    assert isinstance(new_schemas_match, MatchOut)
    assert new_schemas_match.id                  == new_match.id
    assert new_schemas_match.name                == new_match.name
    assert new_schemas_match.status              == new_match.status
    assert new_schemas_match.min_players         == new_match.min_players
    assert new_schemas_match.max_players         == new_match.max_players
    assert new_schemas_match.owner_id            == new_match.owner_id
    assert new_schemas_match.current_player_order == new_match.current_player_order

    # Validar que se puede serializar a dict (como JSON)
    match_dict = new_schemas_match.model_dump()
    for key in [
        "id", "name", "status",
        "min_players", "max_players",
        "owner_id", "current_player_order"
    ]:
        assert key in match_dict

    # ─── Datos de entrada simulando un request JSON ────────────────
    owner_id = uuid.uuid4()
    data     = {
        "name"       : "Partida Test",
        "min_players": 2,
        "max_players": 6,
        "owner_id"   : str(owner_id),
    }

    # ─── Schema MatchIn ───────────────────────────────────────────
    match_in = MatchIn(**data)

    # Aserciones de validación
    assert match_in.name        == "Partida Test"
    assert match_in.min_players == 2
    assert match_in.max_players == 6
    assert isinstance(match_in.owner_id, uuid.UUID)
    assert match_in.owner_id    == owner_id

    # ─── Convertir a DTO ──────────────────────────────────────────
    dto = match_in.to_dto()
    assert isinstance(dto, MatchDTO)
    assert dto.name        == match_in.name
    assert dto.min_players == match_in.min_players
    assert dto.max_players == match_in.max_players
    assert dto.owner_id    == match_in.owner_id

    # ─── Serializar el schema a dict ──────────────────────────────
    dumped = match_in.model_dump()
    for key in ["name", "min_players", "max_players", "owner_id"]:
        assert key in dumped
