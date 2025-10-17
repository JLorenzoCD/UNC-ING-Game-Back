from uuid import UUID
from enum import Enum
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from app.matches.models import Match,MatchStatus

class MatchEndedReason(Enum):
    DECK_FINISHED = "deck_finished"
    MURDERER_REVEALED = "murderer_revealed"

async def handle_match_ended(db, manager, match_id: UUID,
                             reason: MatchEndedReason
                             ):
    #imports locales para no destruir todo con dependencia circulares
    from app.matches.services import MatchService
    from app.secrets.services import Secrets_Services
    from websocketManager.ws_messages import WSEvent, make_ws_message
    
    #traemos la fila del match (objeto) para leer status de forma robusta
    try:
        match_row = db.query(Match).filter(Match.id == match_id).first()
    except SQLAlchemyError as e:
        raise e

    if match_row is None:
        #no existe el match
        return None
    
    #evita 2 veces la llamada a esta funcion
    if match_row.status == MatchStatus.COMPLETED:
        #ya fue llamado en otro request
        return None

    try:
        MatchService(db).update_status_match(match_id, MatchStatus.COMPLETED)
    except SQLAlchemyError as e:
        raise e
    

    info=Secrets_Services(db).get_full_info(match_id)
    if not info:
        #evitamos keyerror(intentar acceder a claves de un dict que no existe o es None)
        return None
    detailstmp=""
    if reason==MatchEndedReason.MURDERER_REVEALED:
        if info['accomplice_name']:
            detailstmp=f"El asesino fue revelado. {info['murderer_name']} era el asesino y {info['accomplice_name']} era su cómplice"
        else:
            detailstmp=f"El asesino fue revelado. {info['murderer_name']} era el asesino"
    else:
        if info['accomplice_name']:
            detailstmp=f"El asesino {info['murderer_name']} se escapo!. Fue ayudado por su cómplice {info['accomplice_name']}"
        else:
            detailstmp=f"El asesino {info['murderer_name']} se escapo!."
            
            
    payload = {
        "match_id": str(match_id),
        "secret_murderer_id": str(info['murderer_secret_id']) ,
        "secret_accomplice_id": str(info['accomplice_secret_id']) if info['accomplice_secret_id'] else None,
        "reason": reason.value,
        "details": detailstmp
    }
    
    try:
        await manager.specificBroadcast(make_ws_message(WSEvent.MATCH_ENDED, payload), match_id)
    except Exception as e:
        print(f"Error al enviar WS: {e}")

    try:
        manager.close_match(match_id)
    except Exception as e:
        print(f"Error al cerrar la partida: {e}")
    
    return payload