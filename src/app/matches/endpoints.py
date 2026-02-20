from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Body, HTTPException, status

# Necessary fun so that all endpoints can access the db
from app.models.db import get_db

# Services
from app.matches.services import MatchService
from app.player.services import PlayerServices
from app.cards.services import CardsServices
from app.secrets.services import SecretsServices
from app.sets.services import SetServices
from app.events.services import EventServices
from app.piles.services import PileServices
from app.messages.services import MessageServices
from app.matches.turn_service import TurnServices
from app.matches.lifecycle_service import MatchLifecycleServices

from app.matches.ending import handle_match_ended

# Schemas
from app.matches.schemas import (
    MatchIn,
    Match_number_of_Player,
    MatchResponse,
    Cards_by_Match_Schema,
    Players_by_Match_Schema,
    MatchJoinIn,
)
from app.cards.schemas import (
    Match_Card_Schema,
    discard_Match_Cards_in,
    take_Match_Cards_in,
)
from app.secrets.schemas import (
    Match_Secret_Schema,
    SecretUpdate,
)
from app.sets.schemas import (
    SetIn,
    MatchSetOut,
    AddSetIn,
    stoleSetIn,
)
from app.messages.schemas import (
    MatchMessageOut,
    MatchMessageIn,
)

# Utils
from app.matches.utils import db_match_2_match_schema
from app.cards.utils import db_match_card_2_match_card_schema
from app.secrets.utils import db_match_secret_2_match_secret_schema
from app.sets.utils import db_match_set_2_match_set_schema
from websocketManager.ws_messages import make_ws_message

# Enums from models
from app.matches.models import MatchEventType, MatchStatus
from app.events.models import EventStatus
from app.secrets.models import Secret_action
from app.sets.models import SetType
from app.matches.ending import MatchEndedReason
from websocketManager.ws_messages import WSEvent

# WebSockets
from websocketManager.ws_routes import manager

# Exceptions
from app.matches.exceptions import MatchValidationError
from app.cards.exceptions import CardInvalidAction

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

router = APIRouter(tags=["matches"], prefix="/matches")

# ------------------------------------------------------------------------------
# ----------------------- CRUD de la entidad Match (sin update) ----------------


@router.get(
    "/", status_code=status.HTTP_200_OK, response_model=List[Match_number_of_Player]
)
async def get_all_matches(db=Depends(get_db)) -> List[Match_number_of_Player]:

    matches = MatchService(db).get_all()
    return matches


@router.get(
    "/{match_id}", status_code=status.HTTP_200_OK, response_model=Match_number_of_Player
)
async def get_match_by_match_ID(match_id: UUID, db=Depends(get_db)):

    match_service = MatchService(db)

    match = match_service.get_match_by_id(match_id)
    match_extended = match_service.extended_match(match)
    return match_extended


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=MatchResponse)
async def create_match(match_in: MatchIn, db=Depends(get_db)) -> MatchResponse:

    match_service = MatchService(db)

    new_match = match_service.create(
        match_in.to_dto()
    )

    # Enviando por WS el nuevo match
    match_dict = new_match.model_dump(mode="json")
    match_dict["current_player_count"] = 1
    await manager.waiting_room_broadcast(make_ws_message(WSEvent.MATCH, match_dict))
    await manager.waiting_room_to_specific_player(make_ws_message(WSEvent.ONGOING_MATCH, match_dict), [new_match.owner_id])

    return MatchResponse(id=new_match.id)


@router.get(
    "/player/{player_id}", status_code=status.HTTP_200_OK, response_model=List[Match_number_of_Player]
)
async def get_all_ongoing_matches_of_player(player_id: UUID, db=Depends(get_db)) -> List[Match_number_of_Player]:

    match_player = MatchService(db).get_ongoing_matches_of_player(player_id)
    return match_player

# ------------------------------------------------------------------------------
# ------------- Unirse, salir, cancelar o iniciar una partida ------------------


@router.post("/{match_id}/join", status_code=status.HTTP_200_OK)
async def join_match(match_id: UUID, player_id: UUID, body: MatchJoinIn = Body(MatchJoinIn()), db=Depends(get_db)):

    match_service = MatchService(db)

    match = match_service.get_match_by_id(match_id)
    if match.password is not None and body.password is None:
        raise MatchValidationError("Password is required")
    if match.password is not None and match.password != body.password:
        raise MatchValidationError("Invalid password")

    # Añadir al jugador a la partida en la db y al WS broadcast de la partida
    MatchLifecycleServices(db).join(match_id, player_id)

    # Mensaje por WS de que ingreso un jugador
    info_player = PlayerServices(db).get_player(player_id)
    payload = {
        "id": info_player.id,
        "name": info_player.name,
        "avatar": info_player.avatar,
        "birthday": info_player.birthday,
    }
    await manager.specificBroadcast(
        make_ws_message(WSEvent.PLAYER_JOIN, payload, match_id), match_id
    )

    # Mensaje por WS para actualizar el contador de jugadores en la lista de partidas
    match = match_service.get_match_by_id(match_id)
    players_in_match = match_service.get_players_from_match(match_id)
    new_match = db_match_2_match_schema(match)
    match_dict = new_match.model_dump(mode="json")
    match_dict["current_player_count"] = len(players_in_match)
    await manager.waiting_room_broadcast(make_ws_message(WSEvent.MATCH, match_dict))
    players_ids = [p.player_id for p in players_in_match]
    await manager.waiting_room_to_specific_player(make_ws_message(WSEvent.ONGOING_MATCH, match_dict), players_ids)

    # Log de que un jugador entro al lobby
    await MessageServices(db).send_player_join_to_match(match_id, player_id)

    return {"match_id": match_id}


@router.put("/{match_id}/quit", status_code=status.HTTP_200_OK)
async def quit_match(match_id: UUID, player_id: UUID, db=Depends(get_db)):

    match_service = MatchService(db)

    # Quitando al jugador de la partida en la DB y del WS broadcast de la partida
    MatchLifecycleServices(db).quit_match(match_id, player_id)

    # Mensaje por WS de que un jugador abandono la partida
    info_player = PlayerServices(db).get_player(player_id)
    payload = {
        "id": info_player.id,
        "name": info_player.name,
        "avatar": info_player.avatar,
        "birthday": info_player.birthday,
    }
    await manager.specificBroadcast(
        make_ws_message(WSEvent.PLAYER_QUIT, payload, match_id), match_id
    )

    # Mensaje por WS para actualizar el contador de jugadores en la lista de partidas
    match = match_service.get_match_by_id(match_id)
    players_in_match = match_service.get_players_from_match(match_id)
    new_match = db_match_2_match_schema(match)
    match_dict = new_match.model_dump(mode="json")
    match_dict["current_player_count"] = len(players_in_match)
    await manager.waiting_room_broadcast(make_ws_message(WSEvent.MATCH, match_dict))
    players_ids = [p.player_id for p in players_in_match]
    await manager.waiting_room_to_specific_player(make_ws_message(WSEvent.ONGOING_MATCH, match_dict), players_ids)

    # Log de que se fue un jugador
    await MessageServices(db).send_player_quit_to_match(match_id, player_id)

    return {"status": "success"}


@router.post("/{match_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_match(match_id: UUID, owner_id: UUID, db=Depends(get_db)):

    match_service = MatchService(db)

    # Eliminando el match de la DB y se elimina el WS broadcast para esa partida
    cancelled_match = match_service.cancel_match(match_id, owner_id)
    manager.close_match(match_id)

    # Mensaje por WS de que se cerro la partida
    cancelled_match.status = MatchStatus.COMPLETED
    players_in_match = match_service.get_players_from_match(match_id)
    match_dict = cancelled_match.model_dump(mode="json")
    match_dict["current_player_count"] = len(players_in_match)
    await manager.waiting_room_broadcast(make_ws_message(WSEvent.MATCH, match_dict))
    players_ids = [p.player_id for p in players_in_match]
    await manager.waiting_room_to_specific_player(make_ws_message(WSEvent.ONGOING_MATCH, match_dict), players_ids)

    payload = cancelled_match.model_dump(mode="json")
    await manager.specificBroadcast(
        make_ws_message(WSEvent.MATCH, payload, match_id), match_id, True
    )

    return {
        "status": "Match cancelled and deleted successfully",
        "match_id": match_id,
    }


@router.post("/{match_id}/start", status_code=status.HTTP_200_OK)
async def start_match(match_id: UUID, db=Depends(get_db)):

    # Actualizando el estado de la partida para indicar que comenzó el juego
    match = MatchLifecycleServices(db).start_game(match_id)

    # Mensaje por WS de que la partida comenzó
    players_in_match = MatchService(db).get_players_from_match(match_id)
    match_dict = match.model_dump(mode="json")
    match_dict["current_player_count"] = len(players_in_match)
    await manager.waiting_room_broadcast(make_ws_message(WSEvent.MATCH, match_dict))
    players_ids = [p.player_id for p in players_in_match]
    await manager.waiting_room_to_specific_player(make_ws_message(WSEvent.ONGOING_MATCH, match_dict), players_ids)

    payload = match.model_dump(mode="json")
    TurnServices(db).set_timeout_turn_by_match_id(match_id)
    await manager.specificBroadcast(
        make_ws_message(WSEvent.MATCH, payload, match_id), match_id
    )

    # Log que para saber de quien es el turno actual
    await MessageServices(db).send_curr_player_turn_in_match(match_id)

    return {"status": "Match started successfully"}

# ------------------------------------------------------------------------------
# ---------------------- Obtener datos de la partida ---------------------------


@router.get(
    "/{match_id}/players",
    status_code=status.HTTP_200_OK,
    response_model=List[Players_by_Match_Schema],
)
async def get_player_by_ID_match(
    match_id: UUID, db=Depends(get_db)
) -> List[Players_by_Match_Schema]:

    players_match = MatchService(db).get_players_by_match(match_id)
    return players_match


@router.get(
    "/{match_id}/cards",
    status_code=status.HTTP_200_OK,
    response_model=List[Cards_by_Match_Schema],
)
async def get_cards(match_id: UUID, db=Depends(get_db)):

    cards = MatchService(db).get_cards_by_match(match_id)
    return cards


@router.get("/{match_id}/secrets", status_code=status.HTTP_200_OK)
async def get_secrets(match_id: UUID, db=Depends(get_db)):

    secrets = MatchService(db).get_secrets_by_match(match_id)
    return secrets


@router.get(
    "/{match_id}/sets", status_code=status.HTTP_200_OK, response_model=List[MatchSetOut]
)
async def get_sets(match_id: UUID, db=Depends(get_db)):

    sets = SetServices(db).get_sets_by_match(match_id)
    return sets

# ------------------------------------------------------------------------------
# ------------------------ Obtener y enviar mensajes ---------------------------


@router.get(
    "/{match_id}/messages", status_code=status.HTTP_200_OK, response_model=List[MatchMessageOut]
)
async def get_all_messages(match_id: UUID, db=Depends(get_db)) -> List[MatchMessageOut]:

    messages = MessageServices(db).get_msgs_by_match(match_id)
    return messages


@router.post("/{match_id}/messages", status_code=status.HTTP_201_CREATED)
async def player_send_message(
    match_id: UUID, msgIn: MatchMessageIn, db=Depends(get_db)
) -> MatchMessageOut:

    msg = await MessageServices(db).create_and_propagate_msg(
        match_id=match_id,
        message=f"[MESSAGE] {msgIn.message}",
        event_type=MatchEventType.PLAYER_SEND_MESSAGE,
        player_id=msgIn.player_id,
        is_system_msg=False,
    )

    return msg

# ------------------------------------------------------------------------------
# -------------------------- Descartar y levantar cartas -----------------------


@router.put("/{match_id}/cards/discard", status_code=status.HTTP_200_OK)
async def discard_card(
    match_id: UUID, cards: discard_Match_Cards_in, db=Depends(get_db)
):

    player_id = cards.player_id
    discarded_cards_ids = cards.card_ids

    # ? Esto es validación, se debería de sacar a un método
    # TODO
    # * Esto en especifico debería de ser un middleware en los endpoints
    # * que afectan al juego
    PlayerServices(
        db).get_player_in_match(player_id, match_id)

    # ? ------------------------------------------------------------------------

    # Se valida de que el jugador puede descartar
    CardsServices(
        db).validate_player_can_discard(player_id, match_id, len(discarded_cards_ids))

    # Se descarta
    PileServices(db).discard_cards(
        player_id, match_id, discarded_cards_ids
    )

    ids = list(set(discarded_cards_ids))
    results = MatchService(db).get_extended_cards_by_match(
        match_id, ids
    )

    # Mensaje WS de las cartas descartadas
    try:
        payload = [
            {
                "id": card[0],
                "card_id": card[1],
                "match_id": card[2],
                "player_id": card[3],
                "is_discarded": card[4],
                "discarded_at": card[5],
                "name": card[6],
                "type": card[7].value if hasattr(card[7], "value") else card[7],
                "description": card[8],
            }
            for card in results
        ]
        await manager.specificBroadcast(
            make_ws_message(WSEvent.CARDS, payload, match_id), match_id
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error with WebSockets",
        )

    # Log de que un jugador descarto x numero de cartas
    await MessageServices(db).send_player_discard_cards(
        match_id,
        player_id,
        results,
        len(discarded_cards_ids)
    )

    return {"status": "success", "cards_discarded": len(discarded_cards_ids)}


@router.put("/{match_id}/cards/take", status_code=status.HTTP_200_OK)
async def take_card(match_id: UUID, cards: take_Match_Cards_in, db=Depends(get_db)):

    player_id = cards.player_id
    taken_cards_ids = cards.card_ids

    # ? Esto es validación, se debería de sacar a un método
    # TODO
    # * Esto en especifico debería de ser un middleware en los endpoints
    # * que afectan al juego
    PlayerServices(
        db).get_player_in_match(player_id, match_id)

    # ?-------------------------------------------------------------------------

    # Se valida si se puede tomar x numero de cartas
    count_cards_pile = PileServices(db).get_count_cards_pile(match_id)
    CardsServices(db).validate_player_can_take(
        player_id, match_id, len(taken_cards_ids), count_cards_pile)

    # Toma las cartas
    PileServices(db).take_cards(player_id, match_id, taken_cards_ids)

    ids = list(set(taken_cards_ids))
    results = MatchService(db).get_extended_cards_by_match(
        match_id, ids
    )

    # Verificar si se terminaron las cartas de mano
    remaining_after = PileServices(db).get_count_cards_pile(match_id)
    if remaining_after <= 3:
        try:
            await handle_match_ended(
                db, manager, match_id, MatchEndedReason.DECK_FINISHED
            )
        except Exception as e:
            print(f"Error al handle_match_ended en take_card: {e}")

    # Mensaje WS de las cartas que tomo el jugador
    try:
        payload = [
            {
                "id": card[0],
                "card_id": card[1],
                "match_id": card[2],
                "player_id": card[3],
                "is_discarded": card[4],
                "discarded_at": card[5],
                "name": card[6],
                "type": card[7].value if hasattr(card[7], "value") else card[7],
                "description": card[8],
            }
            for card in results
        ]

        await manager.specificBroadcast(
            make_ws_message(WSEvent.CARDS, payload, match_id), match_id
        )

    except Exception as e:
        print("[Error] manager.specificBroadcast - take_card: ", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )

    # Log de que el un jugador agarro x cartas
    await MessageServices(db).send_player_take_cards(
        match_id,
        player_id,
        len(taken_cards_ids)
    )

    return {"status": "success", "cards_taken": len(taken_cards_ids)}


# ------------------------------------------------------------------------------
# --------------------- Finalizar turno por jugador o timeout-------------------


@router.put("/{match_id}/pass_turn", status_code=status.HTTP_200_OK)
async def pass_turn(match_id: UUID, db=Depends(get_db)):

    turn_service = TurnServices(db)

    # Se pasa el turno
    match = turn_service.pass_turn_by_id(match_id)

    # Mensaje WS sobre el cambio de turno
    current_player_id = turn_service.get_current_player_by_match(match_id)
    match_dict = db_match_2_match_schema(match).model_dump(mode="json")
    if current_player_id:
        match_dict["current_player_id"] = str(current_player_id)
    msg = make_ws_message(WSEvent.TURN, match_dict, match_id)
    try:
        await manager.specificBroadcast(msg, match_id)
    except Exception as ws_err:
        print(f"[WS] pass_turn broadcast error: {ws_err}")

    # Logs sobre el jugador que actualmente esta en su turno
    await MessageServices(db).send_curr_player_turn_in_match(match_id, current_player_id)

    return {"match_id": match_id}


@router.put("/{match_id}/timeout/{player_id}", status_code=status.HTTP_200_OK)
async def time_out(
    match_id: UUID, player_id: UUID, db=Depends(get_db)
) -> Optional[List[Match_Card_Schema]]:

    match_service = MatchService(db)
    card_service = CardsServices(db)
    turn_service = TurnServices(db)
    pile_service = PileServices(db)

    # Se valida que se este en timeout
    is_timeout = match_service.is_timeout(match_id)
    if not is_timeout:
        return None

    # TODO
    # Se valida de que el jugador este en partida
    PlayerServices(db).get_player_in_match(player_id, match_id)

    ids = set()
    # Se obtiene una carta en posesión del jugador, en caso que la tenga se descarta
    random_card_from_player = card_service.get_random_card_from_player_in_match(
        match_id, player_id)
    if random_card_from_player:
        PileServices(db).discard_cards(
            random_card_from_player.player_id, match_id, [
                random_card_from_player.id], delete=False
        )
        db_match_card_2_match_card_schema(random_card_from_player)

        ids.add(random_card_from_player.id)

    # Obtener una carta del mazo regular para dársela al jugador
    card_of_regular_deck = card_service.get_first_card_of_regular_deck(
        match_id)
    if not card_of_regular_deck:
        raise CardInvalidAction("Can't get a card from the regular deck")

    # Se le da la carta
    pile_service.take_cards(
        player_id, match_id, cards=[card_of_regular_deck.id]
    )

    # Mensaje WS de que el jugador descarto y/o tomo una carta
    ids.add(card_of_regular_deck.id)
    ids = list(ids)
    results = MatchService(
        db).get_extended_cards_by_match(match_id, ids)
    payload = [
        {
            "id": card[0],
            "card_id": card[1],
            "match_id": card[2],
            "player_id": card[3],
            "is_discarded": card[4],
            "discarded_at": card[5],
            "name": card[6],
            "type": card[7].value if hasattr(card[7], "value") else card[7],
            "description": card[8],
        }
        for card in results
    ]
    await manager.specificBroadcast(
        make_ws_message(WSEvent.CARDS, payload, match_id), match_id
    )

    # Verificar si se terminaron las cartas de mano
    remaining_after = pile_service.get_count_cards_pile(match_id)
    if remaining_after <= 3:
        try:
            await handle_match_ended(
                db, manager, match_id, MatchEndedReason.DECK_FINISHED
            )

        except Exception as e:
            print(f"Error al handle_match_ended en take_card: {e}")

        return results

    # Pasar turno
    match = turn_service.pass_turn_by_id(match_id)

    # Mensaje WS de que se paso de torno
    current_player_id = turn_service.get_current_player_by_match(
        match_id
    )
    match_dict = db_match_2_match_schema(match).model_dump(mode="json")
    if current_player_id:
        match_dict["current_player_id"] = str(current_player_id)
    try:
        msg = make_ws_message(WSEvent.TURN, match_dict, match_id)
        await manager.specificBroadcast(msg, match_id)
    except Exception as ws_err:
        print(f"[WS] pass_turn broadcast error: {ws_err}")

    # Logs del jugador que se encuentra actualmente en turno
    await MessageServices(db).send_curr_player_turn_in_match(
        match_id,
        current_player_id,
        is_timeout=True
    )

    return results


# --- Jugar sets, bajar detective a un set o jugar set robado (por evento) -----
# ------------------------------------------------------------------------------


@router.post("/{match_id}/sets", status_code=status.HTTP_201_CREATED)
async def play_set(
    match_id: UUID, setIn: SetIn, db=Depends(get_db)
) -> Optional[MatchSetOut]:

    match_card_ids: List[UUID] = setIn.card_ids
    set_service = SetServices(db)
    event_service = EventServices(db)

    # Validaciones del set
    set_service.set_verification(
        match_card_ids,
        match_id,
        setIn.type,
        setIn.target_player_id,
        setIn.target_secret_id,
    )

    set_data = {
        "type": setIn.type,
        "card_ids": match_card_ids,
        "player_id": setIn.player_id,
        "target_player_id": setIn.target_player_id,
        "target_secret_id": setIn.target_secret_id,
        "match_id": match_id,
    }
    match_set: Optional[MatchSetOut] = None

    if setIn.type != SetType.LADY_EILEEN:
        # En caso de que el set no sea del tipo LADY_EILEEN, se eliminan las cartas
        # que lo conforman ya que se transforman en la entidad Set
        match_set = set_service.create_set(set_data)

        PileServices(db).discard_cards(
            None, match_id, setIn.card_ids, delete=True
        )

        match_set_out = db_match_set_2_match_set_schema(match_set)
        payload = match_set_out.model_dump(mode="json")
        payload.update(
            {"deleted_cards": [str(uuid) for uuid in match_card_ids]})
        ws_msj = make_ws_message(WSEvent.SET, payload, match_id)
        await manager.specificBroadcast(ws_msj, match_id)

    if setIn.type == SetType.TWO_BERESFORD:
        # Se crea y se resuelve el evento set, ya que TWO_BERESFORD no puede
        # ser cancelado
        set_payload = set_service.create_set_payload(
            match_id, setIn, is_Oliver=False
        )
        new_event = event_service.create_event(
            match_id,
            setIn.player_id,
            setIn.type.value,
            None,
            set_payload,
            EventStatus.RESOLVED,
        )

        # Mensaje por WS de que un jugador debe revelar su secreto
        payload = event_service.resolve_event(new_event)
        await manager.specificBroadcast(
            make_ws_message(
                WSEvent.PLAYER_SECRET_REVEAL,
                {"target_player_id": [payload["target_player_id"]]},
                match_id,
            ),
            match_id,
        )
    elif setIn.type == SetType.LADY_EILEEN:
        # Se crea el set y el evento
        set_payload = set_service.create_set_payload(
            match_id, setIn, is_Oliver=False
        )

        set_payload.update({"is_create_set": True})
        new_set_data = {
            "type": setIn.type.value,
            "card_ids": [str(card_id) for card_id in setIn.card_ids],
            "player_id": str(setIn.player_id),
            "target_player_id": str(setIn.target_player_id),
            "target_secret_id": str(setIn.target_secret_id),
            "match_id": str(match_id),
        }
        set_payload.update({"set_data": new_set_data})
        new_event = event_service.create_event(
            match_id, setIn.player_id, setIn.type.value, None, set_payload
        )

        # Mensaje por WS de que se jugo un set y puede ser cancelado por una NSF
        payload = {
            "event_id": str(new_event.id),
            "event_type": setIn.type.value,
            "player_id": str(setIn.player_id),
            "resolve_at_utc": new_event.resolve_at.isoformat(),
            "nsf_count": new_event.nsf_count,
            "discarded_card": None,
        }
        await manager.specificBroadcast(
            make_ws_message(
                WSEvent.CANCELLATION_WINDOW_OPEN, payload, match_id), match_id
        )
    else:
        # Se crea el set y el evento
        set_payload = set_service.create_set_payload(
            match_id, setIn, is_Oliver=False
        )
        new_event = event_service.create_event(
            match_id, setIn.player_id, setIn.type.value, None, set_payload
        )

        # Mensaje WS de que se puede cancelar el set mediante una carta NSF
        payload = {
            "event_id": str(new_event.id),
            "event_type": setIn.type.value,
            "player_id": str(setIn.player_id),
            "resolve_at_utc": new_event.resolve_at.isoformat(),
            "nsf_count": new_event.nsf_count,
            "discarded_card": None,
        }
        await manager.specificBroadcast(
            make_ws_message(
                WSEvent.CANCELLATION_WINDOW_OPEN, payload, match_id), match_id
        )

    # Logs sel set jugado y si se puede o no cancelar con una NSF
    await MessageServices(db).send_player_play_set(
        match_id,
        setIn.player_id,
        setIn.type
    )

    return match_set


@router.put("/{match_id}/sets/{set_id}", status_code=200)
async def put_down_a_detective(
    match_id: UUID, set_id: UUID, set_info: AddSetIn, db=Depends(get_db)
) -> MatchSetOut:

    match_card_ids = set_info.card_ids
    set_service = SetServices(db)
    event_service = EventServices(db)

    # Verificaciones del set
    set_service.add_card_verification(
        match_card_ids, set_id, set_info.target_player_id, set_info.target_secret_id
    )
    match_set = set_service.get_match_set(set_id, match_id)
    match_set_out = db_match_set_2_match_set_schema(match_set)
    card_name = set_service._get_card_names(match_card_ids)[0]

    if (
        match_set.type != SetType.LADY_EILEEN
        or card_name == SetType.ADRIADNE_OLIVER.value
    ):
        # Si el detective que se baje un detective diferente a LADY_EILEEN, se
        # eliminan las cartas de detectives

        if set_service.beresford_brothers_in_set_two_beresford(
            card_name, match_set.type
        ):
            # En caso de que se baje un detective Beresford a un set del otro
            # hermano/a Beresford, se trasforma el tipo del set a TWO_BERESFORD
            match_set = set_service.update_setType(
                set_id, SetType.TWO_BERESFORD)
            match_set_out = db_match_set_2_match_set_schema(match_set)

        payload = match_set_out.model_dump(mode="json")

        PileServices(db).discard_cards(
            None, match_id, set_info.card_ids, delete=True
        )

        # Mensaje WS de las cartas eliminadas
        payload.update(
            {"deleted_cards": [str(uuid) for uuid in match_card_ids]})
        ws_msj = make_ws_message(WSEvent.SET, payload, match_id)
        await manager.specificBroadcast(ws_msj, match_id)

    set_type = match_set.type
    set_in_complete = SetIn(
        type=set_type,
        card_ids=set_info.card_ids,
        player_id=set_info.player_id,
        target_player_id=set_info.target_player_id,
        target_secret_id=set_info.target_secret_id,
    )

    if card_name == SetType.ADRIADNE_OLIVER.value:
        # Si se baja el detective ADRIADNE_OLIVER, se crea el evento en el cual
        # el dueño del set seleccionado debe revelar una carta
        set_in_Oliver = SetIn(
            type=SetType.ADRIADNE_OLIVER,
            card_ids=set_info.card_ids,
            player_id=set_info.player_id,
            target_player_id=set_info.target_player_id,
            target_secret_id=set_info.target_secret_id,
        )
        set_payload = set_service.create_set_payload(
            match_id, set_in_Oliver, is_Oliver=True
        )
        new_event = event_service.create_event(
            match_id,
            set_info.player_id,
            SetType.ADRIADNE_OLIVER.value,
            None,
            set_payload,
        )

        # Mensaje WS del evento y su tiempo de cancelación con una NSF
        payload = {
            "event_id": str(new_event.id),
            "event_type": set_in_complete.type.value,
            "player_id": str(set_info.player_id),
            "resolve_at_utc": new_event.resolve_at.isoformat(),
            "nsf_count": new_event.nsf_count,
            "discarded_card": None,
        }
        await manager.specificBroadcast(
            make_ws_message(
                WSEvent.CANCELLATION_WINDOW_OPEN, payload, match_id), match_id
        )
    elif match_set.type == SetType.TWO_BERESFORD:
        # Se crea el evento del set TWO_BERESFORD y se resuelve, ya que no puede
        # ser cancelado
        set_payload = set_service.create_set_payload(
            match_id, set_in_complete, is_Oliver=False
        )
        new_event = event_service.create_event(
            match_id,
            set_info.player_id,
            set_in_complete.type.value,
            None,
            set_payload,
            EventStatus.RESOLVED,
        )

        # Mensaje WS de que un jugador debe revelar su secreto
        payload = event_service.resolve_event(new_event)
        await manager.specificBroadcast(
            make_ws_message(
                WSEvent.PLAYER_SECRET_REVEAL,
                {"target_player_id": [payload["target_player_id"]]},
                match_id,
            ),
            match_id,
        )
    elif match_set.type == SetType.LADY_EILEEN:
        # Se crea el evento del set LADY_EILEEN y se da tiempo para jugar una NSF
        set_payload = set_service.create_set_payload(
            match_id, set_in_complete, is_Oliver=False
        )
        set_payload.update({"is_create_set": False})
        set_payload.update({"set_id": str(match_set.id)})
        new_event = event_service.create_event(
            match_id,
            set_info.player_id,
            set_in_complete.type.value,
            match_card_ids[0],
            set_payload,
        )

        # Mensaje WS del evento y su tiempo de cancelación con una NSF
        payload = {
            "event_id": str(new_event.id),
            "event_type": set_in_complete.type.value,
            "player_id": str(set_info.player_id),
            "resolve_at_utc": new_event.resolve_at.isoformat(),
            "nsf_count": new_event.nsf_count,
            "discarded_card": None,
        }
        await manager.specificBroadcast(
            make_ws_message(
                WSEvent.CANCELLATION_WINDOW_OPEN, payload, match_id), match_id
        )
    else:
        # Se crea el evento de set y se da tiempo para jugar una NSF
        set_payload = set_service.create_set_payload(
            match_id, set_in_complete, is_Oliver=False
        )
        new_event = event_service.create_event(
            match_id,
            set_info.player_id,
            set_in_complete.type.value,
            None,
            set_payload,
        )

        # Mensaje WS del evento y su tiempo de cancelación con una NSF
        payload = {
            "event_id": str(new_event.id),
            "event_type": set_in_complete.type.value,
            "player_id": str(set_info.player_id),
            "resolve_at_utc": new_event.resolve_at.isoformat(),
            "nsf_count": new_event.nsf_count,
            "discarded_card": None,
        }
        await manager.specificBroadcast(
            make_ws_message(
                WSEvent.CANCELLATION_WINDOW_OPEN, payload, match_id), match_id
        )

    # Log de que se bajo un detective y si se puede o no cancelar con una carta NSF
    await MessageServices(db).send_player_put_down_a_detective(
        match_id,
        set_id,
        new_event.event_type
    )

    return match_set


@router.put("/{match_id}/sets/{set_id}/stolen", status_code=200)
async def play_set_stolen(
    match_id: UUID,
    set_id: UUID,
    stolen_setIn: stoleSetIn,
    db=Depends(get_db),
) -> MatchSetOut:

    set_service = SetServices(db)
    secret_service = SecretsServices(db)

    # Se valida si se puede jugar el set
    match_set = set_service.get_match_set(set_id, match_id)
    set_type = match_set.type
    target_secret = stolen_setIn.target_secret_id
    target_player = stolen_setIn.target_player_id
    set_service.verification_play_stolen_set(
        set_type, target_player, target_secret)

    if target_secret is not None:
        if match_set.type in [SetType.HERCULE_POIROT, SetType.MISS_MARPLE]:
            # Se revela el secreto seleccionado
            target_secret = secret_service.update_secret(
                Secret_action.REVEAL, target_secret, target_player
            )
            match_secret_out = db_match_secret_2_match_secret_schema(
                target_secret)

            try:
                # Se verifica si el acecino fue revelado o todos los inocentes
                # están en desgracia social
                res = secret_service.is_murderer_revealed(match_id)
                if res:
                    await handle_match_ended(
                        db, manager, match_id, MatchEndedReason.MURDERER_REVEALED
                    )
                elif secret_service.is_everyone_in_social_disgrace(match_id):
                    await handle_match_ended(
                        db, manager, match_id, MatchEndedReason.SOCIAL_DISGRACE
                    )
            except Exception as e:
                print(f"Error al verificar condiciones de victoria: {e}")

        if match_set.type == SetType.PARKER_PYNE:
            # Se oculta el secreto seleccionado
            target_secret = secret_service.update_secret(
                Secret_action.HIDE, target_secret, target_player
            )
            match_secret_out = db_match_secret_2_match_secret_schema(
                target_secret)

        # Mensaje WS del secreto revelado/ocultado
        payload = match_secret_out.model_dump(mode="json")
        ws_msj = make_ws_message(WSEvent.SECRET, payload, match_id)
        await manager.specificBroadcast(ws_msj, match_id)
    else:
        # Mensaje WS de que el jugador seleccionado debe revelar un secreto propio
        payload = {"target_player_id": [target_player]}
        ws_msj = make_ws_message(
            WSEvent.PLAYER_SECRET_REVEAL, payload, match_id)
        await manager.specificBroadcast(ws_msj, match_id)

    match_set_out = db_match_set_2_match_set_schema(match_set)

    # Log de que el jugador jugo el set robado
    await MessageServices(db).send_player_stolen_set(
        match_id,
        player_id=match_set_out.player_id,
        set_type=match_set_out.type
    )

    return match_set_out

# ------------------------------------------------------------------------------
# -------------------------------- Eventos -------------------------------------


@router.post("/{match_id}/events", status_code=status.HTTP_200_OK)
async def play_event(
    match_id: UUID,
    player_id: UUID,
    match_card_id: UUID,
    event_payload: dict | None,
    db=Depends(get_db),
):

    card_service = CardsServices(db)
    event_service = EventServices(db)

    card_service.validate_card_ownership(
        player_id, match_id, match_card_id
    )

    typeEvent = card_service.get_event_type_by_card(
        match_card_id
    )

    if card_service.is_instant_event(typeEvent.value):
        # Como es un evento instantánea, el evento se crea y resuelve, ya que no
        # se puede cancelar con una NSF
        new_event = event_service.create_event(
            match_id,
            player_id,
            typeEvent.value,
            match_card_id,
            event_payload,
            EventStatus.RESOLVED,
        )
        payload = event_service.resolve_event(new_event)

        # Se descarta la carta de evento jugada
        PileServices(db).discard_cards(
            player_id, match_id, [match_card_id], delete=False
        )

        # Mensaje WS sobre la carta de evento jugada
        discarded_card = card_service.get_card_by_id(match_card_id)
        discarded_card_event = db_match_card_2_match_card_schema(
            discarded_card
        ).model_dump(mode="json")
        payload["discarded_card_event"] = discarded_card_event
        await manager.specificBroadcast(
            make_ws_message(WSEvent.CARD_EVENT, payload, match_id), match_id
        )

        # Log de la carta de evento jugada y no puede ser cancelada con un NSF
        await MessageServices(db).send_player_play_event_not_cancelable(
            match_id,
            player_id,
            typeEvent
        )
    else:
        # El evento se crea y se da el tiempo para poder cancelarla con la NSF
        new_event = event_service.create_event(
            match_id, player_id, typeEvent.value, match_card_id, event_payload
        )

        # Se descarta la carta jugada
        PileServices(db).discard_cards(
            player_id, match_id, [match_card_id], delete=False
        )

        # Mensaje WS para indicar que se jugo una carta de evento y puede ser
        # cancelada por una NSF
        discarded_card = card_service.get_card_by_id(match_card_id)
        discarded_card_event = db_match_card_2_match_card_schema(
            discarded_card
        ).model_dump(mode="json")
        payload = {
            "event_id": str(new_event.id),
            "event_type": typeEvent.value,
            "player_id": player_id,
            "resolve_at_utc": new_event.resolve_at.isoformat(),
            "nsf_count": new_event.nsf_count,
            "discarded_card": discarded_card_event,
        }
        await manager.specificBroadcast(
            make_ws_message(
                WSEvent.CANCELLATION_WINDOW_OPEN, payload, match_id
            ),
            match_id,
        )

        # Log de la carta de evento jugada y que puede ser cancelada con un NSF
        await MessageServices(db).send_player_play_event_cancelable(
            match_id,
            player_id,
            typeEvent
        )

    return {"status": "event_created", "event_id": new_event.id}


@router.post("/{match_id}/card_trade", status_code=status.HTTP_200_OK)
async def play_card_trade(
    match_id: UUID,
    player_id: UUID,
    event_id: UUID,
    event_payload: dict,
    db=Depends(get_db),
):
    event_service = EventServices(db)

    # Validación
    CardsServices(db).validate_card_ownership(
        player_id, match_id, event_payload["target_card_id"]
    )

    # Se actualiza los datos del evento en base a los nuevos datos
    event_update = event_service.update_info_event(
        event_id, player_id, event_payload["target_card_id"]
    )

    # Log de carta seleccionada
    await MessageServices(db).send_player_select_card_to_trade(
        match_id,
        player_id,
        MatchEventType.CARD_TRADE
    )

    if event_service.is_event_ready_to_resolve(event_update):
        # Si el evento ya tiene todos los datos para finalizar, se lo finaliza
        # y se envía la info por WS
        payload = event_service.resolve_event(event_update)
        await manager.specificBroadcast(
            make_ws_message(WSEvent.CARD_EVENT, payload, match_id), match_id
        )

        # Se revisa si se intercambio alguna carta devious, si es asi, el jugador
        # que la recibió debe revelar un secreto propio
        devious_card_targets_players = event_service.get_players_target_devious_card(
            event_update)
        if len(devious_card_targets_players) >= 1:
            await manager.specificBroadcast(
                make_ws_message(
                    WSEvent.PLAYER_SECRET_REVEAL,
                    {
                        "target_player_id": devious_card_targets_players
                    },
                    match_id
                ),
                match_id,
            )

            # Log, ya que se intercambio una carta devious
            await MessageServices(db).send_player_trade_devious_card(
                match_id,
                player_id,
                MatchEventType.CARD_TRADE
            )

    return {"status": "ok", "message": "CardTrade de lujo"}


@router.post("/{match_id}/dead_card_folly", status_code=status.HTTP_200_OK)
async def play_dead_card_folly(
    match_id: UUID,
    player_id: UUID,
    event_id: UUID,
    event_payload: dict,
    db=Depends(get_db),
):

    event_service = EventServices(db)

    # Validación
    CardsServices(db).validate_card_ownership(
        player_id, match_id, event_payload["target_card_id"]
    )

    # Se actualiza los datos del evento en base a los nuevos datos
    event_update = event_service.update_info_event(
        event_id, player_id, event_payload["target_card_id"]
    )

    # Log de carta seleccionada
    await MessageServices(db).send_player_select_card_to_trade(
        match_id,
        player_id,
        MatchEventType.DEAD_CARD_FOLLY
    )

    if event_service.is_event_ready_to_resolve(event_update):
        # Si el evento ya tiene todos los datos para finalizar, se lo finaliza
        # y se envía la info por WS
        payload = event_service.resolve_event(event_update)
        await manager.specificBroadcast(
            make_ws_message(WSEvent.CARD_EVENT, payload, match_id), match_id
        )

        # Se revisa si se intercambio alguna carta devious, si es asi, el jugador
        # que la recibió debe revelar un secreto propio
        devious_card_targets_players = event_service.get_players_target_devious_card(
            event_update)
        if len(devious_card_targets_players) >= 1:
            await manager.specificBroadcast(
                make_ws_message(
                    WSEvent.PLAYER_SECRET_REVEAL,
                    {
                        "target_player_id": devious_card_targets_players
                    },
                    match_id,
                ),
                match_id,
            )

            # Log, ya que se intercambio una carta devious
            await MessageServices(db).send_player_trade_devious_card(
                match_id,
                player_id,
                MatchEventType.DEAD_CARD_FOLLY
            )

    return {"status": "ok", "message": "Dead card folly de lujo"}


@router.post("/{match_id}/point_your_suspicions", status_code=status.HTTP_200_OK)
async def play_point_your_suspicions(
    match_id: UUID,
    player_id: UUID,
    event_id: UUID,
    event_payload: dict,
    db=Depends(get_db),
):

    event_service = EventServices(db)

    # Se actualiza los datos del evento en base a los nuevos datos
    event_update = event_service.update_info_event(
        event_id, player_id, event_payload["target_player_id"]
    )

    # Log de un jugador dudando de otro
    await MessageServices(db).send_player_point_suspicions(
        match_id,
        player_id,
        event_payload["target_player_id"]
    )

    if event_service.is_event_ready_to_resolve(event_update):
        # Si el evento ya tiene todos los datos para finalizar, se lo finaliza
        # y se envía la info por WS
        payload = event_service.resolve_event(event_update)
        await manager.specificBroadcast(
            make_ws_message(
                WSEvent.PLAYER_SECRET_REVEAL,
                {"target_player_id": [payload["target_player_id"]]},
                match_id
            ),
            match_id
        )

    return {"status": "ok", "message": "Point your suspicions de lujo"}


@router.post("/{match_id}/not_so_fast", status_code=status.HTTP_200_OK)
async def play_not_so_fast(
    match_id: UUID,
    player_id: UUID,
    match_card_id: UUID,
    event_id: UUID,
    nsf_count: int,
    db=Depends(get_db),
):

    card_service = CardsServices(db)
    event_service = EventServices(db)

    # Validaciones
    card_service.validate_card_ownership(
        player_id, match_id, match_card_id
    )
    typeEvent = card_service.get_event_type_by_card(
        match_card_id
    )
    if typeEvent.value != "NOT SO FAST":
        raise CardInvalidAction("Carta jugada no es una not so fast")

    # Se modifica el campo nsf del evento para indicar que se jugo una carta NSF
    updated_event = event_service.update_event_nsf(
        event_id, nsf_count
    )

    # Log, jugador jugo un NSF
    await MessageServices(db).send_player_play_nsf(match_id, player_id)

    # Se descarta la carta NSF jugada
    PileServices(db).discard_cards(
        player_id, match_id, [match_card_id], delete=False
    )

    # Mensaje WS de que se re-abre la ventana para poder jugar otra NSF
    discarded_card = card_service.get_card_by_id(match_card_id)
    discarded_card_event = db_match_card_2_match_card_schema(
        discarded_card)
    payload = {
        "event_id": str(updated_event.id),
        "event_type": typeEvent.value,
        "player_id": player_id,
        "resolve_at_utc": updated_event.resolve_at.isoformat(),
        "nsf_count": updated_event.nsf_count,
        "discarded_card": discarded_card_event.model_dump(mode="json"),
    }
    await manager.specificBroadcast(
        make_ws_message(
            WSEvent.CANCELLATION_WINDOW_OPEN,
            payload,
            match_id,
        ), match_id
    )

    return {"status": "ok", "message": "Cancelaste la accion"}


# ------------------------------------------------------------------------------
# --------------------------- Voltear secreto ----------------------------------
@router.put("/{match_id}/secrets/{secret_id}", status_code=200)
async def update_secret_in_match(
    match_id: UUID,
    secret_id: UUID,
    secretIn: SecretUpdate,
    db=Depends(get_db),
) -> Match_Secret_Schema:

    secret_service = SecretsServices(db)

    # Validaciones
    secret_service.secret_update_verification(
        match_id, secret_id, secretIn)

    match_secret_old = secret_service.get_match_secret_by_id(secret_id)

    # Actualización del secreto
    match_secret = secret_service.update_secret(
        secretIn.action, secret_id, secretIn.target_player_id
    )
    match_secret_out = db_match_secret_2_match_secret_schema(match_secret)

    # Mensaje WS donde se envía el secreto actualizado
    payload = match_secret_out.model_dump(mode="json")
    msj_ws = make_ws_message(WSEvent.SECRET, payload, match_id)
    await manager.specificBroadcast(msj_ws, match_id)

    if (
        secretIn.action == Secret_action.REVEAL
        and match_secret_out.is_revealed == True
    ):
        # Se revisa si el secreto revelado es del acecino, en ese caso se envía
        # un mensaje por WS para finalizar el juego
        try:
            res = secret_service.is_murderer_revealed(match_id)
            if res:
                await handle_match_ended(
                    db, manager, match_id, MatchEndedReason.MURDERER_REVEALED
                )
            elif secret_service.is_everyone_in_social_disgrace(match_id):
                await handle_match_ended(
                    db, manager, match_id, MatchEndedReason.SOCIAL_DISGRACE
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Log, jugador x actualizo un secreto
    await MessageServices(db).send_update_secret(
        match_id,
        player_id=match_secret_old.player_id,
        secret_action=secretIn.action
    )

    return match_secret_out
