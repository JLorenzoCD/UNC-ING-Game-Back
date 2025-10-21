import uuid
import pytest
from datetime            import date
from app.sets.models     import Match_Set, SetType
from app.player.models   import Player
from app.matches.models  import Match

def test_match_set_model(db_session):
    """
    A partir de una Partida y Jugadores
    creamos match_sets para testear
    """

    # ─── Inicializacion ────────────────────────────────
    new_player_owner = Player(
        name     = "Elian",
        avatar   = "Mao Zedong",
        birthday = date(2000, 8, 22)
    )
    db_session.add(new_player_owner)
    db_session.commit()
    db_session.refresh(new_player_owner)

    new_match = Match(
        name        = "AGE 3",
        min_players = 4,
        max_players = 6,
        owner_id    = new_player_owner.id
    )
    db_session.add(new_match)
    db_session.commit()
    db_session.refresh(new_match)
    
    #──── Testeo ────────────────────────────────
    
    match: Match   = db_session.query(Match).first()
    player: Player = db_session.query(Player).first()
    
    if not (match and player):
        pytest.fail("No se pudieron obtener todos los datos")
    
    new_match_set = Match_Set (
        type      = SetType.HERCULE_POIROT,
        match_id  = match.id,
        player_id = player.id,
        quin_count = 1
    )
    
    db_session.add(new_match_set)
    db_session.commit()
    db_session.refresh(new_match_set)

    test_match_set:Match_Set = db_session.get(Match_Set, new_match_set.id)
    
    if not test_match_set:
        pytest.fail("No se obtuvo el match_set de la db")
    
    assert test_match_set.id is not None
    assert test_match_set.type      == SetType.HERCULE_POIROT
    assert test_match_set.match_id  == match.id
    assert test_match_set.player_id == player.id
    assert test_match_set.quin_play == False
    assert test_match_set.quin_count == 1