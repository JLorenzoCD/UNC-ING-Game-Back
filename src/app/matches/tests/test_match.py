import uuid
from app.matches.models import Match
from app.matches.schemas import MatchOut, MatchIn
from app.matches.dto import MatchDTO
from app.matches.models import MatchStatus
from app.matches.utils import db_match_2_match_schema
from app.player.models import Player
from datetime import date

def test_create_match(db_session):
    
    """"
    
    Creamos un Player owner de Match
    Testeamos la correcta creacion de Match con su owner_id
    Testeamos schemas MatchIn MAtchOut
    
    """
    
    #Creamos Player owner de Match
    
    new_player_owner = Player(
        name="Elian",
        avatar="Mao Zedong",
        birthday=date(2000, 8, 22)
    )
    db_session.add(new_player_owner)
    db_session.commit()
    db_session.refresh(new_player_owner)
    
    #Creamos Match
    
    new_match = Match(
        name = "AGE 3",
        min_player = 4,
        max_player = 6,
        owner_id = new_player_owner.id
        )
    
    db_session.add(new_match)
    db_session.commit()
    db_session.refresh(new_match)
    
    #Testeo de entidad Match
    
    assert new_match.name == "AGE 3"
    assert new_match.min_player == 4
    assert new_match.max_player == 6
    assert new_match.owner_id is not None
    assert new_match.owner_id == new_player_owner.id
    assert new_match.status == MatchStatus.WAITING
    assert new_match.current_player_order == 0
    
    #Schema de Match
    
    new_schemas_match = db_match_2_match_schema(new_match)
    
    #Testeo de schema
    
    assert isinstance(new_schemas_match, MatchOut)
    assert new_schemas_match.id == new_match.id
    assert new_schemas_match.name == new_match.name
    assert new_schemas_match.status == new_match.status
    assert new_schemas_match.min_player == new_match.min_player
    assert new_schemas_match.max_player == new_match.max_player
    assert new_schemas_match.owner_id == new_match.owner_id
    assert new_schemas_match.current_player_order == new_match.current_player_order
    
    # Validar que se puede serializar a dict (como JSON)
     
    match_dict = new_schemas_match.model_dump()
    
    assert "id" in match_dict
    for key in [
        "id", "name", "status",
        "min_player", "max_player",
        "owner_id", "current_player_order"
    ]:
        assert key in match_dict
    
    #Datos de entrada simulando un request JSON
    owner_id = uuid.uuid4()
    data = {
        "name": "Partida Test",
        "min_players": 2,
        "max_players": 6,
        "owner_id": str(owner_id),
    }

    #Schema MatchIN
    match_in = MatchIn(**data)

    # Aserciones de validación
    assert match_in.name == "Partida Test"
    assert match_in.min_players == 2
    assert match_in.max_players == 6
    assert isinstance(match_in.owner_id, uuid.UUID)
    assert match_in.owner_id == owner_id

    # Convertir a DTO
    dto = match_in.to_dto()
    assert isinstance(dto, MatchDTO)
    assert dto.name == match_in.name
    assert dto.min_player == match_in.min_players
    assert dto.max_player == match_in.max_players
    assert dto.owner_id == match_in.owner_id

    # Serializar el schema a dict
    dumped = match_in.model_dump()
    for key in ["name", "min_players", "max_players", "owner_id"]:
        assert key in dumped
        
    def test_endpoint_matcher_POST(client, db_session):
        
        #Creamos Player owner de Match
    
        new_player_owner = Player(
            name="Elian",
            avatar="Mao Zedong",
            birthday=date(2000, 8, 22)
        )
        db_session.add(new_player_owner)
        db_session.commit()
        db_session.refresh(new_player_owner)
        
        # Payload
        match_post = {
            "name": "Partida Test",
            "min_player": 2,
            "max_player": 6,
            "owner_id": str(new_player_owner.id),
        }

        # Llamada al endpoint
        response = client.post("/matches/", json=match_post)
        assert response.status_code == 201

        body = response.json()
        assert "id" in body

        # Validar en la DB
        from app.matches.models import Match
        created = db_session.get(Match, uuid.UUID(body["id"]))
        assert created is not None
        assert created.name == "Partida Test"
        assert created.owner_id == new_player_owner.id