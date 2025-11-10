import uuid
import pytest

from app.matches.models import Match, MatchStatus
from app.matches.services import MatchService
from app.player.models import Player, Match_Player
from app.cards.models import Match_Card
from app.secrets.models import Match_Secret
from app.matches.tests.conftest import setup_match_and_players


class TestGameStatePersistence:
    """Tests para verificar que se mantenga el estado de la partida"""

    def test_match_status_persists_after_start(self, client, db_session):
        """Verifica que el estado de la partida cambie a IN_PROGRESS y se mantenga"""
        # Setup inicial
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        
        # Verificar estado inicial
        match = db_session.get(Match, match_id)
        assert match.status == MatchStatus.WAITING
        
        # Iniciar partida
        response = client.post(f"/matches/{setup_data['match_str_id']}/start")
        assert response.status_code == 200
        
        # Verificar que el estado cambió consultando nuevamente
        updated_match = db_session.get(Match, match_id)
        assert updated_match.status == MatchStatus.IN_PROGRESS
        
        # Verificar que el estado se mantiene después de múltiples consultas
        for _ in range(3):
            match_check = db_session.get(Match, match_id)
            assert match_check.status == MatchStatus.IN_PROGRESS

    def test_match_basic_properties_persist(self, client, db_session):
        """Verifica que las propiedades básicas de la partida se mantengan"""
        # Setup inicial
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        
        # Obtener propiedades iniciales
        initial_match = db_session.get(Match, match_id)
        initial_name = initial_match.name
        initial_min_players = initial_match.min_players
        initial_max_players = initial_match.max_players
        initial_owner_id = initial_match.owner_id
        
        # Iniciar partida
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        
        # Verificar que las propiedades se mantienen
        updated_match = db_session.get(Match, match_id)
        assert updated_match.name == initial_name
        assert updated_match.min_players == initial_min_players
        assert updated_match.max_players == initial_max_players
        assert updated_match.owner_id == initial_owner_id

    def test_player_associations_persist(self, client, db_session):
        """Verifica que las asociaciones de jugadores con la partida se mantengan"""
        # Setup inicial
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        
        # Contar jugadores asociados antes de iniciar
        players_before_count = db_session.query(Match_Player).filter(
            Match_Player.match_id == match_id
        ).count()
        assert players_before_count == 2  # Owner + 1 jugador adicional
        
        # Obtener IDs de jugadores antes
        players_before_ids = db_session.query(Match_Player.player_id).filter(
            Match_Player.match_id == match_id
        ).all()
        before_ids_set = {str(player_id[0]) for player_id in players_before_ids}
        
        # Iniciar partida
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        
        # Verificar que las asociaciones se mantienen después del inicio
        players_after_count = db_session.query(Match_Player).filter(
            Match_Player.match_id == match_id
        ).count()
        assert players_after_count == players_before_count
        
        # Verificar que los IDs de jugadores son los mismos
        players_after_ids = db_session.query(Match_Player.player_id).filter(
            Match_Player.match_id == match_id
        ).all()
        after_ids_set = {str(player_id[0]) for player_id in players_after_ids}
        assert before_ids_set == after_ids_set

    def test_cards_remain_associated_after_game_start(self, client, db_session):
        """Verifica que las cartas mantengan su asociación después del inicio del juego"""
        # Setup inicial
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        
        # Iniciar partida
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        
        # Contar cartas totales asociadas al match
        total_cards = db_session.query(Match_Card).filter(
            Match_Card.match_id == match_id
        ).count()
        
        # Debe haber cartas asociadas después del inicio
        assert total_cards > 0
        
        # Contar cartas asignadas a jugadores
        player_cards_count = db_session.query(Match_Card).filter(
            Match_Card.match_id == match_id,
            Match_Card.player_id.isnot(None)
        ).count()
        
        # Contar cartas no asignadas (en el mazo)
        deck_cards_count = db_session.query(Match_Card).filter(
            Match_Card.match_id == match_id,
            Match_Card.player_id.is_(None)
        ).count()
        
        # La suma debe ser igual al total
        assert player_cards_count + deck_cards_count == total_cards
        
        # Verificar que las asociaciones se mantienen
        for _ in range(3):
            current_total = db_session.query(Match_Card).filter(
                Match_Card.match_id == match_id
            ).count()
            assert current_total == total_cards

    def test_secrets_remain_associated_after_game_start(self, client, db_session):
        """Verifica que los secretos mantengan su asociación después del inicio del juego"""
        # Setup inicial
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        
        # Iniciar partida
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        
        # Contar secretos totales asociados al match
        total_secrets = db_session.query(Match_Secret).filter(
            Match_Secret.match_id == match_id
        ).count()
        
        # Debe haber secretos asociados después del inicio
        assert total_secrets > 0
        
        # Contar secretos asignados a jugadores
        player_secrets_count = db_session.query(Match_Secret).filter(
            Match_Secret.match_id == match_id,
            Match_Secret.player_id.isnot(None)
        ).count()
        
        # Debe haber secretos asignados
        assert player_secrets_count > 0
        
        # Verificar que las asociaciones se mantienen
        for _ in range(3):
            current_total = db_session.query(Match_Secret).filter(
                Match_Secret.match_id == match_id
            ).count()
            assert current_total == total_secrets
            
            current_player_secrets = db_session.query(Match_Secret).filter(
                Match_Secret.match_id == match_id,
                Match_Secret.player_id.isnot(None)
            ).count()
            assert current_player_secrets == player_secrets_count

    def test_match_state_consistency_after_queries(self, client, db_session):
        """Verifica que el estado se mantenga consistente después de múltiples consultas"""
        # Setup inicial
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        
        # Iniciar partida
        client.post(f"/matches/{match_str_id}/start")
        
        # Obtener estado inicial
        initial_match = db_session.get(Match, match_id)
        initial_status = initial_match.status
        initial_turn = initial_match.current_player_order
        
        # Realizar múltiples consultas que no deberían cambiar el estado
        for _ in range(5):
            # Consultar el match
            response = client.get(f"/matches/{match_str_id}")
            assert response.status_code == 200
            
            # Verificar que el estado no cambió
            current_match = db_session.get(Match, match_id)
            assert current_match.status == initial_status
            assert current_match.current_player_order == initial_turn

    @pytest.mark.parametrize("num_additional_players", [1, 2, 3])
    def test_state_persistence_with_different_player_counts(self, client, db_session, num_additional_players):
        """Verifica que el estado se mantenga con diferentes números de jugadores"""
        # Setup inicial con jugador base
        setup_data = setup_match_and_players(client, db_session)
        match_str_id = setup_data['match_str_id']
        match_id = setup_data['match_id']
        
        # Agregar jugadores adicionales
        for i in range(num_additional_players):
            response = client.post("/players", json={
                "name": f"Extra Player {i+1}",
                "avatar": f"extra_avatar_{i+1}",
                "birthday": "2000-01-01"
            })
            assert response.status_code == 201
            extra_player = response.json()
            
            response = client.post(f"/matches/{match_str_id}/join", 
                                params={"player_id": extra_player['id']})
            assert response.status_code == 200
        
        # Verificar número de jugadores antes del inicio
        players_before = db_session.query(Match_Player).filter(
            Match_Player.match_id == match_id
        ).count()
        expected_count = 2 + num_additional_players  # Owner + 1 original + extras
        assert players_before == expected_count
        
        # Iniciar partida
        response = client.post(f"/matches/{match_str_id}/start")
        assert response.status_code == 200
        
        # Verificar que el estado y asociaciones se mantienen
        match = db_session.get(Match, match_id)
        assert match.status == MatchStatus.IN_PROGRESS
        
        players_after = db_session.query(Match_Player).filter(
            Match_Player.match_id == match_id
        ).count()
        assert players_after == expected_count

    def test_match_id_consistency(self, client, db_session):
        """Verifica que el ID de la partida se mantenga consistente"""
        # Setup inicial
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        original_match_id = str(match_id)
        
        # Iniciar partida
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        
        # Verificar que el ID no cambió
        match = db_session.get(Match, match_id)
        assert str(match.id) == original_match_id
        
        # Verificar múltiples veces
        for _ in range(5):
            current_match = db_session.get(Match, match_id)
            assert str(current_match.id) == original_match_id

    def test_match_owner_persistence(self, client, db_session):
        """Verifica que el propietario de la partida se mantenga"""
        # Setup inicial
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        original_owner_id = setup_data['owner_id']
        
        # Verificar owner inicial
        match = db_session.get(Match, match_id)
        assert match.owner_id == original_owner_id
        
        # Iniciar partida
        client.post(f"/matches/{setup_data['match_str_id']}/start")
        
        # Verificar que el owner se mantiene
        updated_match = db_session.get(Match, match_id)
        assert updated_match.owner_id == original_owner_id
        
        # Verificar múltiples veces
        for _ in range(3):
            current_match = db_session.get(Match, match_id)
            assert current_match.owner_id == original_owner_id