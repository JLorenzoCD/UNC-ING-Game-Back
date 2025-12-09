from datetime import date

from app.player.models import Player
from app.player.schemas import Player_Schema_out
from app.player.utils import db_player_2_Player_Schema_out


def test_create_player(db_session):
    """
    Testea que un Player se pueda crear, guardar en la DB y convertir a schema.
    """
    new_player = Player(name="Hernan", avatar="avatar1", birthday=date(2005, 6, 21))
    db_session.add(new_player)
    db_session.commit()
    db_session.refresh(new_player)
    assert new_player.id is not None
    assert new_player.name == "Hernan"
    assert new_player.avatar == "avatar1"
    player_schema = db_player_2_Player_Schema_out(new_player)
    assert isinstance(player_schema, Player_Schema_out)
    assert player_schema.id == new_player.id
    assert player_schema.name == new_player.name
    assert player_schema.avatar == new_player.avatar
    player_dict = player_schema.model_dump()
    assert "id" in player_dict
    assert player_dict["name"] == "Hernan"
    assert player_dict["avatar"] == "avatar1"
