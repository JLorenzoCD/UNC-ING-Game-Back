import pytest
from uuid import UUID, uuid4

from app.secrets.models import Secret, Match_Secret, Secret_Type, Secret_action
from app.secrets.schemas import Secret_Schema
from app.secrets.services import Secrets_Services, SecretNotFound
from app.secrets.tests.conftest import setup_match_and_players
from app.matches.services import MatchService
from app.matches.schemas import MatchOut

def test_update_secret(db_session, client):
    
    # Proceso inicial
    setup_data = setup_match_and_players(client, db_session)
    if not setup_data:
        pytest.fail("Error en el set up de la partida")
    
    match_id: UUID = setup_data["match_id"]
    owner_id: UUID = setup_data["owner_id"]
    player2_id: UUID = setup_data["player2_id"]
    
    match_service = MatchService(db_session)
    match_out: MatchOut = match_service.start_game(match_id)
    
    if not match_out or match_out.id != match_id:
        pytest.fail("Error al iniciar partida")
        
    secret_to_test = db_session.query(Match_Secret).filter(Match_Secret.player_id == owner_id).first()
    if not secret_to_test:
        pytest.fail("No se encontraron secretos para el jugador owner")

    secret_service = Secrets_Services(db_session)
    
    secret_not_found:UUID = uuid4()

    # 1. Probar REVEAL
    secret_service.update_secret(Secret_action.REVEAL, secret_to_test.id)
    db_session.refresh(secret_to_test)
    assert secret_to_test.is_revealed is True

    # 2. Probar HIDE
    secret_service.update_secret(Secret_action.HIDE, secret_to_test.id)
    db_session.refresh(secret_to_test)
    assert secret_to_test.is_revealed is False

    # 3. Probar STEAL
    secret_service.update_secret(Secret_action.STEAL, secret_to_test.id, player2_id)
    db_session.refresh(secret_to_test)
    assert secret_to_test.player_id == player2_id

    # 4. Probar excepciones
    with pytest.raises(ValueError, match="Invalid action"):
        secret_service.update_secret("invalid_action", secret_to_test.id)

    with pytest.raises(ValueError, match="Player ID is required for steal action"):
        secret_service.update_secret(Secret_action.STEAL, secret_to_test.id)
        
    with pytest.raises(SecretNotFound, match="Secret not found"):
        secret_service.update_secret(Secret_action.REVEAL, secret_not_found)
    
    