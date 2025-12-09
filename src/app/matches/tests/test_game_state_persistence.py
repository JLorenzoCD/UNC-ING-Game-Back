import pytest

from app.cards.models import Match_Card
from app.matches.models import Match, MatchStatus
from app.matches.tests.conftest import setup_match_and_players
from app.player.models import Match_Player
from app.secrets.models import Match_Secret


class TestGameStatePersistence:
    """Tests para verificar que se mantenga el estado de la partida"""

    def test_cards_remain_associated_after_game_start(self, client, db_session):
        """Verifica que las cartas mantengan su asociación después del inicio del juego"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        total_cards = (
            db_session.query(Match_Card).filter(Match_Card.match_id == match_id).count()
        )
        assert total_cards > 0
        player_cards_count = (
            db_session.query(Match_Card)
            .filter(Match_Card.match_id == match_id, Match_Card.player_id.isnot(None))
            .count()
        )
        deck_cards_count = (
            db_session.query(Match_Card)
            .filter(Match_Card.match_id == match_id, Match_Card.player_id.is_(None))
            .count()
        )
        assert player_cards_count + deck_cards_count == total_cards
        for _ in range(3):
            current_total = (
                db_session.query(Match_Card)
                .filter(Match_Card.match_id == match_id)
                .count()
            )
            assert current_total == total_cards

    def test_match_basic_properties_persist(self, client, db_session):
        """Verifica que las propiedades básicas de la partida se mantengan"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        initial_match = db_session.get(Match, match_id)
        initial_name = initial_match.name
        initial_min_players = initial_match.min_players
        initial_max_players = initial_match.max_players
        initial_owner_id = initial_match.owner_id
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        updated_match = db_session.get(Match, match_id)
        assert updated_match.name == initial_name
        assert updated_match.min_players == initial_min_players
        assert updated_match.max_players == initial_max_players
        assert updated_match.owner_id == initial_owner_id

    def test_match_id_consistency(self, client, db_session):
        """Verifica que el ID de la partida se mantenga consistente"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        original_match_id = str(match_id)
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        match = db_session.get(Match, match_id)
        assert str(match.id) == original_match_id
        for _ in range(5):
            current_match = db_session.get(Match, match_id)
            assert str(current_match.id) == original_match_id

    def test_match_owner_persistence(self, client, db_session):
        """Verifica que el propietario de la partida se mantenga"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        original_owner_id = setup_data["owner_id"]
        match = db_session.get(Match, match_id)
        assert match.owner_id == original_owner_id
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        updated_match = db_session.get(Match, match_id)
        assert updated_match.owner_id == original_owner_id
        for _ in range(3):
            current_match = db_session.get(Match, match_id)
            assert current_match.owner_id == original_owner_id

    def test_match_state_consistency_after_queries(self, client, db_session):
        """Verifica que el estado se mantenga consistente después de múltiples consultas"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match_str_id = setup_data["match_str_id"]
        client.post(f"/matches/{match_str_id}/start")
        initial_match = db_session.get(Match, match_id)
        initial_status = initial_match.status
        initial_turn = initial_match.current_player_order
        for _ in range(5):
            response = client.get(f"/matches/{match_str_id}")
            assert response.status_code == 200
            current_match = db_session.get(Match, match_id)
            assert current_match.status == initial_status
            assert current_match.current_player_order == initial_turn

    def test_match_status_persists_after_start(self, client, db_session):
        """Verifica que el estado de la partida cambie a IN_PROGRESS y se mantenga"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match = db_session.get(Match, match_id)
        assert match.status == MatchStatus.WAITING
        response = client.post(f"/matches/{setup_data['match_str_id']}/start")
        assert response.status_code == 200
        updated_match = db_session.get(Match, match_id)
        assert updated_match.status == MatchStatus.IN_PROGRESS
        for _ in range(3):
            match_check = db_session.get(Match, match_id)
            assert match_check.status == MatchStatus.IN_PROGRESS

    def test_player_associations_persist(self, client, db_session):
        """Verifica que las asociaciones de jugadores con la partida se mantengan"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        players_before_count = (
            db_session.query(Match_Player)
            .filter(Match_Player.match_id == match_id)
            .count()
        )
        assert players_before_count == 2
        players_before_ids = (
            db_session.query(Match_Player.player_id)
            .filter(Match_Player.match_id == match_id)
            .all()
        )
        before_ids_set = {str(player_id[0]) for player_id in players_before_ids}
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        players_after_count = (
            db_session.query(Match_Player)
            .filter(Match_Player.match_id == match_id)
            .count()
        )
        assert players_after_count == players_before_count
        players_after_ids = (
            db_session.query(Match_Player.player_id)
            .filter(Match_Player.match_id == match_id)
            .all()
        )
        after_ids_set = {str(player_id[0]) for player_id in players_after_ids}
        assert before_ids_set == after_ids_set

    def test_secrets_remain_associated_after_game_start(self, client, db_session):
        """Verifica que los secretos mantengan su asociación después del inicio del juego"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        total_secrets = (
            db_session.query(Match_Secret)
            .filter(Match_Secret.match_id == match_id)
            .count()
        )
        assert total_secrets > 0
        player_secrets_count = (
            db_session.query(Match_Secret)
            .filter(
                Match_Secret.match_id == match_id, Match_Secret.player_id.isnot(None)
            )
            .count()
        )
        assert player_secrets_count > 0
        for _ in range(3):
            current_total = (
                db_session.query(Match_Secret)
                .filter(Match_Secret.match_id == match_id)
                .count()
            )
            assert current_total == total_secrets
            current_player_secrets = (
                db_session.query(Match_Secret)
                .filter(
                    Match_Secret.match_id == match_id,
                    Match_Secret.player_id.isnot(None),
                )
                .count()
            )
            assert current_player_secrets == player_secrets_count

    @pytest.mark.parametrize("num_additional_players", [1, 2, 3])
    def test_state_persistence_with_different_player_counts(
        self, client, db_session, num_additional_players
    ):
        """Verifica que el estado se mantenga con diferentes números de jugadores"""
        setup_data = setup_match_and_players(client, db_session)
        match_str_id = setup_data["match_str_id"]
        match_id = setup_data["match_id"]
        for i in range(num_additional_players):
            response = client.post(
                "/players",
                json={
                    "name": f"Extra Player {i + 1}",
                    "avatar": f"extra_avatar_{i + 1}",
                    "birthday": "2000-01-01",
                },
            )
            assert response.status_code == 201
            extra_player = response.json()
            response = client.post(
                f"/matches/{match_str_id}/join",
                params={"player_id": extra_player["id"]},
            )
            assert response.status_code == 200
        players_before = (
            db_session.query(Match_Player)
            .filter(Match_Player.match_id == match_id)
            .count()
        )
        expected_count = 2 + num_additional_players
        assert players_before == expected_count
        response = client.post(f"/matches/{match_str_id}/start")
        assert response.status_code == 200
        match = db_session.get(Match, match_id)
        assert match.status == MatchStatus.IN_PROGRESS
        players_after = (
            db_session.query(Match_Player)
            .filter(Match_Player.match_id == match_id)
            .count()
        )
        assert players_after == expected_count
