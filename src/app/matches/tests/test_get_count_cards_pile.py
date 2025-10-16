import uuid
import pytest
from app.matches.tests.conftest import setup_match_and_players

from app.matches.services import MatchService, PileService
from app.cards.models import Match_Card

@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_get_count_cards_pile_for_various_player_counts(db_session, client, num_players):
    """
    Crea una partida base con 2 jugadores usando setup_match_and_players (de conftest),
    luego agrega jugadores hasta num_players (si hace falta), inicia la partida y verifica:
        pile_count == total_match_cards - 6 * num_players
    """

    #setup inicial: crea match con 2 jugadores (owner + player2) y cartas/secrets del conftest
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    #si necesitamos más jugadores, los creamos y los unimos a la partida
    current_count = 2
    while current_count < num_players:
        resp = client.post("/players", json={
            "name":     f"Extra Player {current_count}",
            "avatar":   f"avatar{current_count}",
            "birthday": "1990-01-01"
        })
        assert resp.status_code == 201
        new_player = resp.json()
        #meter a la partida
        resp2 = client.post(f"/matches/{match_str_id}/join", params={"player_id": new_player["id"]})
        assert resp2.status_code == 200
        current_count += 1

    #iniciar la partida
    resp_start=client.post(f"/matches/{match_str_id}/start")
    assert resp_start.status_code==200

    #contar todas las cartas del match
    total_cards = (
        db_session.query(Match_Card)
        .filter(Match_Card.match_id == match_id)
        .count()
    )

    #llamar a la funcion testeada
    pile_count = PileService(db_session).get_count_cards_pile(match_id)

    expected = total_cards - 6 * num_players
    assert pile_count == expected, f"pile_count {pile_count} != expected {expected} (total_cards={total_cards}, players={num_players})"