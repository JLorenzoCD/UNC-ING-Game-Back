import random
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import DateTime

from app.cards.models import Card, Match_Card
from app.cards.schemas import Match_Card_Schema
from app.cards.services import Cards_Services
from app.cards.utils import db_match_card_2_match_card_schema
from app.matches import schemas as match_schemas
from app.matches.models import Match, MatchLogs, MatchStatus
from app.matches.schemas import MatchOut
from app.matches.utils import db_match_2_match_schema, db_match_log_2_match_log_schema
from app.player.models import Match_Player, Player
from app.secrets.models import Match_Secret, Secret, Secret_Type
from app.secrets.services import Secrets_Services
from app.sets.models import Match_Set
from app.sets.schemas import MatchSetOut
from app.sets.utils import db_match_set_2_match_set_schema



# Custom Exceptions
class OwnerNotFound(Exception):
    """Raised when the match owner is not found."""
    pass


class MatchNotFound(Exception):
    """Raised when a match is not found."""
    pass


class MatchValidationError(Exception):
    """Raised when match validation fails."""
    pass


class PlayerNotInMatch(Exception):
    """Raised when a player is not in the specified match."""
    pass


class MatchService:
    """Service class for managing matches."""
    
    def __init__(self, db):
        self._db = db
    
    def create(self, match_dto: match_schemas.MatchDTO) -> match_schemas.MatchOut:
        """Create a new match."""
        if match_dto.min_players < 2 or match_dto.max_players > 6:
            raise MatchValidationError("Incorrect number of players")
        
        owner: Player = self._db.get(Player, match_dto.owner_id)
        if not owner:
            raise OwnerNotFound()
        
        new_match = Match(
            name=match_dto.name,
            min_players=match_dto.min_players,
            max_players=match_dto.max_players,
            owner_id=owner.id,
            timer_turn=datetime.now(timezone.utc)
        )
        print(new_match.timer_turn)
        try:
            self._db.add(new_match)
            self._db.commit()
            self._db.refresh(new_match)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        
        try:
            match_player = Match_Player(match_id=new_match.id, player_id=owner.id)
            self._db.add(match_player)
            self._db.commit()
            self._db.refresh(match_player)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        
        match_out = db_match_2_match_schema(new_match)
        return match_out  
      
    def get_all(self) -> List[match_schemas.Match_number_of_Player]:
        """Get all matches with player count."""
        try:
            matches = self._db.query(Match).all()
            
            combined = []
            for match in matches:
                # Convert to base schema
                match_out = db_match_2_match_schema(match)
                
                # Get player count
                player_count = self.count_players_by_match(match.id)
                
                # Create extended schema
                extended_match = match_schemas.Match_number_of_Player(
                    **match_out.model_dump(),
                    current_player_count=player_count
                )
                combined.append(extended_match)
            
            return combined
        except SQLAlchemyError:
            self._db.rollback()
            raise
        except Exception:
            raise

    def get_match_by_id(self, match_id: UUID) -> Match | None:
        """Get a match by its ID."""
        try:
            match: Match = self._db.query(Match).filter(Match.id == match_id).first()
            if not match:
                raise Exception("Match not Found")
        except Exception:
            raise
        return match

    def get_current_player_by_match(self, match_id: UUID) -> Optional[UUID]:
        """Get the current player ID based on current_player_order."""
        try:
            match = self.get_match_by_id(match_id)
            if match.current_player_order is None:
                return None
            
            # Get the player with the current order
            current_player = (
                self._db.query(Match_Player)
                .filter(
                    Match_Player.match_id == match_id,
                    Match_Player.order == match.current_player_order
                )
                .first()
            )
            
            return current_player.player_id if current_player else None
        except Exception:
            return None

    def pass_turn_by_id(self, match_id: UUID):
        """Pass the turn to the next player."""
        try:
            match = self.get_match_by_id(match_id)
        except Exception:
            raise MatchNotFound

        count_players = self.count_players_by_match(match_id)
        if match.status != MatchStatus.IN_PROGRESS:
            raise ValueError("The match is not in progress")
        if match.current_player_order is None:
            raise ValueError("current_player_order Invalid")
        if match.current_player_order >= count_players:
            match.current_player_order = 1
        else:
            match.current_player_order = match.current_player_order + 1
        
        match.timer_turn = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(match)
        
        print(match.timer_turn)
        return match

    def extended_match(self, match: Match) -> match_schemas.Match_number_of_Player | None:
        """Create an extended match schema with player count."""
        # Convert to base schema
        match_out = db_match_2_match_schema(match)
        
        # Get player count
        player_count = self.count_players_by_match(match.id)
        
        # Create extended schema
        extended_match = match_schemas.Match_number_of_Player(
            **match_out.model_dump(),
            current_player_count=player_count
        )
        return extended_match
      
    def get_players_by_match(self, match_id: UUID) -> List[match_schemas.Players_by_Match_Schema]:
        """Get all players in a match."""
        try:
            match = self._db.query(Match).filter(Match.id == match_id).first()
            if not match:
                raise Exception("Partida no encontrada")
            
            result = []
            for mp in match.match_players:
                result.append({
                    "id": mp.player.id,
                    "player_id": mp.player.id,
                    "match_id": mp.match.id,
                    "role": mp.role.value if mp.role else None,
                    "order": mp.order,
                    "name": mp.player.name,
                    "avatar": mp.player.avatar,
                    "birthday": mp.player.birthday 
                })
        except Exception:
            raise 
        return result
    
    def count_players_by_match(self, match_id: UUID) -> int:
        """Count the number of players in a match."""
        return (
            self._db.query(Match_Player)
            .filter(Match_Player.match_id == match_id)
            .count()
        )

    def join(self, match_id: UUID, player_id: UUID):
        """Add a player to a match."""
        match = self._db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        # Count players with the new service
        current_players = self.count_players_by_match(match_id)
        if current_players >= match.max_players:
            raise HTTPException(status_code=400, detail="Match is full")
        
        # Check if player already joined
        already_joined = (
            self._db.query(Match_Player)
            .filter(Match_Player.match_id == match_id, Match_Player.player_id == player_id)
            .first()
        )
        if already_joined:
            raise HTTPException(status_code=400, detail="Player already in")

        match_player = Match_Player(match_id=match_id, player_id=player_id, order=0)
        self._db.add(match_player)
        self._db.commit()
        self._db.refresh(match_player)

    def get_cards_by_match(self, match_id: UUID) -> List[match_schemas.Cards_by_Match_Schema]:
        """Get all cards in a match."""
        try:
            match = self._db.query(Match).filter(Match.id == match_id).first()
            if not match:
                raise Exception("Match not found")
            
            results = self._db.query(
                Match_Card.id,
                Match_Card.card_id,
                Match_Card.match_id,
                Match_Card.player_id,
                Match_Card.is_discarded,
                Match_Card.discarded_at,
                Card.name,
                Card.type,
                Card.description
            ).join(Card, Match_Card.card_id == Card.id)\
            .filter(Match_Card.match_id == match_id)\
            .order_by(Match_Card.id).all()
            
            combined: List[match_schemas.Cards_by_Match_Schema] = []
            for r in results:
                combined.append({
                    "id": r.id,
                    "card_id": r.card_id,
                    "match_id": r.match_id,
                    "player_id": r.player_id,
                    "is_discarded": r.is_discarded,
                    "discarded_at": r.discarded_at,
                    "name": r.name,
                    "type": r.type,
                    "description": r.description  
                })
            
            return combined
        except SQLAlchemyError as e:
            raise Exception(f"Database error: {str(e)}")

    def get_extended_cards_by_match(self, match_id: UUID, ids: List[UUID]) -> List[Match_Card_Schema]:
        """Get extended card information for specific cards in a match."""
        result = (
            self._db.query(
                Match_Card.id,
                Match_Card.card_id,
                Match_Card.match_id,
                Match_Card.player_id,
                Match_Card.is_discarded,
                Match_Card.discarded_at,
                Card.name,
                Card.type,
                Card.description,
            )
            .join(Card, Match_Card.card_id == Card.id)
            .filter(
                Match_Card.match_id == match_id,
                Match_Card.id.in_(ids),
            )
            .all()
        )
        return result

    def get_secrets_by_match(self, match_id: UUID):
        """Get all secrets in a match."""
        results = (
            self._db.query(Match_Secret, Secret)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .filter(Match_Secret.match_id == match_id)
            .all()
        )

        # Format info as requested by frontend
        combined = []
        for ms, s in results:
            combined.append({
                "id": ms.id,
                "secret_id": ms.secret_id,
                "match_id": ms.match_id,
                "player_id": ms.player_id,
                "is_revealed": ms.is_revealed,
                "type": s.type,
                "content": s.content,
            })
        return combined

    def update_match(self) -> Match:
        """Update match - placeholder method."""
        pass

    def update_status_match(self, match_id: UUID, new_status: str) -> None:
        """Update the status of a match."""
        match: Match = self.get_match_by_id(match_id)
        if not match:
            raise MatchNotFound()
        match.status = new_status
        try:
            self._db.commit()
            self._db.refresh(match)
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise exception

    def cancel_match(self, match_id: UUID, owner_id: UUID) -> MatchOut:
        try:
            match: Match = self.get_match_by_id(match_id)
        except Exception:
            raise MatchNotFound()
        
        if not match:
            raise MatchNotFound()
        
        if match.owner_id != owner_id:
            raise MatchValidationError("Solo el propietario de la partida puede cancelarla.")
        
        if match.status != MatchStatus.WAITING:
            raise MatchValidationError("Solo se pueden cancelar partidas en estado 'waiting'.")
        
        match_out = db_match_2_match_schema(match)

        self._delete_match_completely(match_id)
        
        return match_out

    def _delete_match_completely(self, match_id: UUID) -> None:
        """Delete a match and all its related data from the database."""
        try:
            # Delete Match_Player entries
            self._db.query(Match_Player).filter(Match_Player.match_id == match_id).delete()
            
            # Delete MatchLogs entries
            self._db.query(MatchLogs).filter(MatchLogs.match_id == match_id).delete()
            
            # Delete the match itself
            self._db.query(Match).filter(Match.id == match_id).delete()
            
            self._db.commit()
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise exception

    def get_players_from_match(self, match_id: UUID):
        """Get all players from a match."""
        return (
            self._db.query(Match_Player)
            .filter(Match_Player.match_id == match_id)
            .all()
        )

    def assign_player_order(self, match_id: UUID) -> None:
        """Assign player order based on birthday proximity to September 15."""
        # Get match players
        match_players: list[Match_Player] = self.get_players_from_match(match_id)
        
        # Calculate distance to September 15
        def distance_to_september_15(birthday: date) -> int:
            target = birthday.replace(month=9, day=15)
            days_diff = abs((birthday - target).days)
            return min(days_diff, 366 - days_diff)
        
        # Group by distance and get players
        grouped = defaultdict(list)
        for mp in match_players:
            player = self._db.get(Player, mp.player_id)
            if player:
                distance = distance_to_september_15(player.birthday)
                grouped[distance].append((mp, player))
        
        # Assign orders with randomization for ties
        order = 1
        for distance in sorted(grouped.keys()):
            tied = grouped[distance]
            random.shuffle(tied)
            for mp, _ in tied:
                mp.order = order
                order += 1
        
        try:
            self._db.commit()
        except SQLAlchemyError as exception:
            raise

    def deal_secrets(self, match_secrets: list[Match_Secret], match_players: list[Match_Player]) -> None:
        """Deal secrets to players according to game rules."""
        # Get all secret IDs by type
        murderer_secret = self._db.query(Secret).filter(Secret.type == Secret_Type.MURDERER).first()
        accomplice_secret = self._db.query(Secret).filter(Secret.type == Secret_Type.ACCOMPLICE).first()
        innocent_secret_ids = [s.id for s in self._db.query(Secret.id).filter(Secret.type == Secret_Type.INNOCENT).all()]
        
        # Filter match_secrets by type
        innocent_match_secrets = [ms for ms in match_secrets if ms.secret_id in innocent_secret_ids]
        
        # Create COPY of the list to not modify the original
        available_players = match_players.copy()
        
        # Deal MURDERER
        murderer = random.choice(available_players)
        available_players.remove(murderer)
        
        # Assign MURDERER card
        murderer_secret_match = next(ms for ms in match_secrets if ms.secret_id == murderer_secret.id)
        murderer_secret_match.player_id = murderer.player_id
        murderer.role = Secret_Type.MURDERER
        match_secrets.remove(murderer_secret_match)
        
        # Assign 2 innocent secrets to murderer
        for i in range(2):
            innocent_match_secrets[i].player_id = murderer.player_id
            match_secrets.remove(innocent_match_secrets[i])
        
        innocent_match_secrets = innocent_match_secrets[2:]
        
        # Deal ACCOMPLICE (only if exists)
        accomplice_secret_match = next((ms for ms in match_secrets if ms.secret_id == accomplice_secret.id), None)
        
        if accomplice_secret_match:
            accomplice = random.choice(available_players)
            available_players.remove(accomplice)
            
            accomplice_secret_match.player_id = accomplice.player_id
            accomplice.role = Secret_Type.ACCOMPLICE
            match_secrets.remove(accomplice_secret_match)
            
            # Assign 2 innocent secrets to accomplice
            for i in range(2):
                innocent_match_secrets[i].player_id = accomplice.player_id
                match_secrets.remove(innocent_match_secrets[i])
            
            innocent_match_secrets = innocent_match_secrets[2:]
        
        # Deal remaining secrets randomly
        random.shuffle(match_secrets)
        
        if len(available_players) > 0:
            secrets_per_player = len(match_secrets) // len(available_players)
            
            for idx, player in enumerate(available_players):
                player.role = Secret_Type.INNOCENT
                for i in range(secrets_per_player):
                    secret_idx = idx * secrets_per_player + i
                    match_secrets[secret_idx].player_id = player.player_id
        
        self._db.commit()

    def deal_cards(self, match_cards: list[Match_Card], match_players: list[Match_Player]) -> None:
        """Deal cards to players according to game rules."""
        not_so_fast_cards = []
        other_cards = []

        for card in match_cards:
            card_obj = self._db.get(Card, card.card_id)
            if card_obj and card_obj.name == "NOT SO FAST":
                not_so_fast_cards.append(card)
            else:
                other_cards.append(card)

        for i, player in enumerate(match_players):
            if i < len(not_so_fast_cards):
                not_so_fast_cards[i].player_id = player.player_id

        remaining_not_so_fast = not_so_fast_cards[len(match_players):]
        other_cards.extend(remaining_not_so_fast)

        random.shuffle(other_cards)

        card_index = 0
        for player in match_players:
            cards_dealt = 0
            while cards_dealt < 5 and card_index < len(other_cards):
                other_cards[card_index].player_id = player.player_id
                card_index += 1
                cards_dealt += 1

        self._db.commit()

    def start_game(self, match_id: UUID) -> MatchOut:
        """Start a match if conditions are met."""
        match = self.get_match_by_id(match_id)
        match_players: list[Match_Player] = self.get_players_from_match(match_id)
        len_match_players = len(match_players)
        
        if len_match_players >= match.min_players: 
            if match.status == MatchStatus.WAITING:
                # Update match status
                self.update_status_match(match_id, MatchStatus.IN_PROGRESS)

                # Initialize cards and secrets
                Cards_Services(self._db).init_match_cards(match_id, len(match_players))
                Secrets_Services(self._db).init_match_secrets(len(match_players), match_id)

                # Get cards and secrets
                match_cards: list[Match_Card] = Cards_Services(self._db).get_cards_by_match(match_id)
                match_secrets: list[Match_Secret] = Secrets_Services(self._db).get_secrets_by_match(match_id)

                random.shuffle(match_cards)
                random.shuffle(match_secrets)

                # Deal secrets
                self.deal_secrets(match_secrets, match_players)

                # Deal cards
                self.deal_cards(match_cards, match_players)

                self.assign_player_order(match_id)

                try:
                    self._db.commit()
                except SQLAlchemyError as exception:
                    self._db.rollback()
                    raise exception
                
                return db_match_2_match_schema(match)
            else:
                raise MatchValidationError("Match is not in a valid state to start")
        else:
            raise MatchValidationError("Match is not in a valid state to start")
    
    def quit_match(self, match_id: UUID, player_id: UUID) -> None:
        match_player = (
            self._db.query(Match_Player)
            .filter(Match_Player.match_id == match_id, Match_Player.player_id == player_id)
            .first()
        )
        if not match_player:
            raise PlayerNotInMatch()
        
        try:
            self._db.delete(match_player)
            self._db.commit()
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise exception


class PileService:
    """Service class for managing the card pile."""
    
    def __init__(self, db):
        self._db = db

    def take_cards(self, player_id: UUID, match_id: UUID, cards: list[UUID]) -> None:
        """Take cards from the pile and assign to player."""
        try:
            for card in cards:
                match_card = self._db.query(Match_Card).filter(Match_Card.id == card).first()
                if match_card and (match_card.player_id is None and match_card.match_id == match_id):
                    match_card.player_id = player_id
                    match_card.is_discarded = False
                    match_card.discarded_at = None
            self._db.commit()
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail={"error": "Database error", "details": str(exception)}
            )
    
    def discard_cards(self, player_id: UUID, match_id: UUID, cards: list[UUID]) -> None:
        """Discard cards from player to the pile."""
        try:
            for card in cards:
                match_card = self._db.query(Match_Card).filter(Match_Card.id == card).first()
                if match_card and (match_card.player_id == player_id and match_card.match_id == match_id):
                    match_card.player_id = None
                    match_card.is_discarded = True
                    match_card.discarded_at = datetime.now()
            self._db.commit()
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail={"error": "Database error", "details": str(exception)}
            )

    def get_count_cards_pile(self, match_id: UUID) -> int:
        """Get the count of available cards in the pile."""
        return (
            self._db.query(Match_Card)
            .filter(
                Match_Card.match_id == match_id,
                Match_Card.player_id.is_(None),
                Match_Card.is_discarded.is_(False),
            )
            .count()
        )


class SetService:
    """Service class for managing match sets."""
    
    def __init__(self, db):
        self._db = db

    def get_sets_by_match(self, match_id: UUID) -> List[MatchSetOut]:
        """Get all sets for a match."""
        result = self._db.query(Match_Set).filter(Match_Set.match_id == match_id).all()
        
        return [db_match_set_2_match_set_schema(match_set) for match_set in result]


class LogService:
    """Service class for managing match logs."""
    
    def __init__(self, db):
        self._db = db

    def create_log(self, match_id: UUID, message: str, event_type: str, player_id: Optional[UUID] = None) -> UUID:
        """Create a new log entry for a match."""
        new_log = MatchLogs(
            match_id=match_id,
            message=message,
            event_type=event_type,
            player_id=player_id,
            created_at=datetime.now()
        )
        try:
            self._db.add(new_log)
            self._db.commit()
            self._db.refresh(new_log)
            return new_log.id
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise exception
        
    def get_logs_by_match(self, match_id: UUID) -> List[match_schemas.MatchLogOut]:
        """Get all logs for a match."""
        result = self._db.query(MatchLogs).filter(MatchLogs.match_id == match_id).all()

        return [db_match_log_2_match_log_schema(match_log) for match_log in result]
    
    def get_log_by_id(self, log_id: UUID) -> match_schemas.MatchLogOut:
        """Get a specific log by ID."""
        try:
            log = self._db.query(MatchLogs).filter(MatchLogs.id == log_id).first()
            return db_match_log_2_match_log_schema(log)
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise exception


class PlayersService:
    """Service class for managing players in matches."""
    
    def __init__(self, db):
        self._db = db

    def get_player(self, player_id: UUID) -> Player:
        """Get a player by ID."""
        player = self._db.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        return player
