import random
from collections import defaultdict
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.cards.models import Card, Match_Card
from app.cards.services import Cards_Services
from app.matches.models import Match, MatchStatus
from app.matches.schemas import MatchOut
from app.matches.utils import db_match_2_match_schema
from app.player.models import Match_Player, Player
from app.secrets.models import Match_Secret, Secret, Secret_Type
from app.secrets.services import Secrets_Services


class MatchLifecycleService:
    """Service for match lifecycle operations (start, cancel, join, quit)."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def assign_player_order(self, match_id: UUID) -> None:
        """Assign player order based on birthday proximity to September 15."""
        from app.matches.services import MatchService

        match_players: list[Match_Player] = MatchService(
            self._db
        ).get_players_from_match(match_id)

        def distance_to_september_15(birthday: date) -> int:
            """Distance to september 15.

            Args:
                birthday: Parameter birthday.

            Returns:
                Return value."""
            target = birthday.replace(month=9, day=15)
            days_diff = abs((birthday - target).days)
            return min(days_diff, 366 - days_diff)

        grouped = defaultdict(list)
        for mp in match_players:
            player = self._db.get(Player, mp.player_id)
            if player:
                distance = distance_to_september_15(player.birthday)
                grouped[distance].append((mp, player))
        order = 1
        for distance in sorted(grouped.keys()):
            tied = grouped[distance]
            random.shuffle(tied)
            for mp, _ in tied:
                mp.order = order
                order += 1
        try:
            self._db.commit()
        except SQLAlchemyError:
            raise

    def deal_cards(
        self, match_cards: list[Match_Card], match_players: list[Match_Player]
    ) -> None:
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
        remaining_not_so_fast = not_so_fast_cards[len(match_players) :]
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

    def deal_secrets(
        self, match_secrets: list[Match_Secret], match_players: list[Match_Player]
    ) -> None:
        """Deal secrets to players according to game rules."""
        murderer_secret = (
            self._db.query(Secret).filter(Secret.type == Secret_Type.MURDERER).first()
        )
        accomplice_secret = (
            self._db.query(Secret).filter(Secret.type == Secret_Type.ACCOMPLICE).first()
        )
        innocent_secret_ids = [
            s.id
            for s in self._db.query(Secret.id)
            .filter(Secret.type == Secret_Type.INNOCENT)
            .all()
        ]
        innocent_match_secrets = [
            ms for ms in match_secrets if ms.secret_id in innocent_secret_ids
        ]
        available_players = match_players.copy()
        murderer = random.choice(available_players)
        available_players.remove(murderer)
        murderer_secret_match = next(
            (ms for ms in match_secrets if ms.secret_id == murderer_secret.id)
        )
        murderer_secret_match.player_id = murderer.player_id
        murderer.role = Secret_Type.MURDERER
        match_secrets.remove(murderer_secret_match)
        for i in range(2):
            innocent_match_secrets[i].player_id = murderer.player_id
            match_secrets.remove(innocent_match_secrets[i])
        innocent_match_secrets = innocent_match_secrets[2:]
        accomplice_secret_match = next(
            (ms for ms in match_secrets if ms.secret_id == accomplice_secret.id), None
        )
        if accomplice_secret_match:
            accomplice = random.choice(available_players)
            available_players.remove(accomplice)
            accomplice_secret_match.player_id = accomplice.player_id
            accomplice.role = Secret_Type.ACCOMPLICE
            match_secrets.remove(accomplice_secret_match)
            for i in range(2):
                innocent_match_secrets[i].player_id = accomplice.player_id
                match_secrets.remove(innocent_match_secrets[i])
            innocent_match_secrets = innocent_match_secrets[2:]
        random.shuffle(match_secrets)
        if len(available_players) > 0:
            secrets_per_player = len(match_secrets) // len(available_players)
            for idx, player in enumerate(available_players):
                player.role = Secret_Type.INNOCENT
                for i in range(secrets_per_player):
                    secret_idx = idx * secrets_per_player + i
                    match_secrets[secret_idx].player_id = player.player_id
        self._db.commit()

    def join(self, match_id: UUID, player_id: UUID):
        """Add a player to a match."""
        from app.matches.services import MatchService

        match = self._db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        current_players = MatchService(self._db).count_players_by_match(match_id)
        if current_players >= match.max_players:
            raise HTTPException(status_code=400, detail="Match is full")
        already_joined = (
            self._db.query(Match_Player)
            .filter(
                Match_Player.match_id == match_id, Match_Player.player_id == player_id
            )
            .first()
        )
        if already_joined:
            raise HTTPException(status_code=400, detail="Player already in")
        match_player = Match_Player(match_id=match_id, player_id=player_id, order=0)
        self._db.add(match_player)
        self._db.commit()
        self._db.refresh(match_player)

    def quit_match(self, match_id: UUID, player_id: UUID) -> None:
        """Quit match.

        Args:
            match_id: Parameter match_id.
            player_id: Parameter player_id.

        Returns:
            Return value."""
        from app.matches.services import PlayerNotInMatch

        match_player = (
            self._db.query(Match_Player)
            .filter(
                Match_Player.match_id == match_id, Match_Player.player_id == player_id
            )
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

    def start_game(self, match_id: UUID) -> MatchOut:
        """Start a match if conditions are met."""
        from app.matches.services import MatchService, MatchValidationError

        match_service = MatchService(self._db)
        match = match_service.get_match_by_id(match_id)
        match_players: list[Match_Player] = match_service.get_players_from_match(
            match_id
        )
        len_match_players = len(match_players)
        if len_match_players >= match.min_players:
            if match.status == MatchStatus.WAITING:
                match_service.update_status_match(match_id, MatchStatus.IN_PROGRESS)
                Cards_Services(self._db).init_match_cards(match_id, len(match_players))
                Secrets_Services(self._db).init_match_secrets(
                    len(match_players), match_id
                )
                match_cards: list[Match_Card] = Cards_Services(
                    self._db
                ).get_cards_by_match(match_id)
                match_secrets: list[Match_Secret] = Secrets_Services(
                    self._db
                ).get_secrets_by_match(match_id)
                random.shuffle(match_cards)
                random.shuffle(match_secrets)
                self.deal_secrets(match_secrets, match_players)
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
