from uuid import UUID
from datetime import date
import random

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.matches.models import Match, Match_Player, MatchStatus
from app.matches import schemas
from app.matches.utils import db_match_2_match_schema

from app.player.models import Player

from app.cards.models import Card, Match_Card
from app.cards.schemas import Match_Card_Schema
from app.cards.services import Cards_Services

from app.secrets.models import Secret, Match_Secret, Secret_Type
from app.secrets.services import Secrets_Services


# Excepciones
class OwnerNotFound(Exception):
    pass


class MatchNotFound(Exception):
    pass


class MatchValidationError(Exception):
    pass


class MatchService:
    def __init__(self, db: Session):
        self._db = db

    def create(self, match_dto: schemas.MatchDTO) -> schemas.MatchResponse:
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
        )
        try:
            self._db.add(new_match)
            self._db.commit()
            self._db.refresh(new_match)
        except SQLAlchemyError:
            self._db.rollback()
            raise

        try:
            match_player = Match_Player(
                match_id=new_match.id,
                player_id=owner.id,
                order=0,
            )
            self._db.add(match_player)
            self._db.commit()
            self._db.refresh(match_player)
        except SQLAlchemyError:
            self._db.rollback()
            raise

        match_out = db_match_2_match_schema(new_match)
        return schemas.MatchResponse(id=match_out.id)

    def get_all(self) -> list[Match]:
        return self._db.query(Match).all()

    def get_match_by_id(self, match_id: UUID) -> Match | None:
        return self._db.query(Match).filter(Match.id == match_id).first()

    def update_status_match(self, match_id: UUID, new_status: str) -> None:
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

    def get_players_from_match(self, match_id: UUID):
        return (
            self._db.query(Match_Player)
            .filter(Match_Player.match_id == match_id)
            .all()
        )

    def assign_player_order(self, match_id: UUID) -> None:
        # Obtener jugadores de la partida
        match_players: list[Match_Player] = self.get_players_from_match(match_id)
        players: list[Player] = []

        for mp in match_players:
            player = self._db.get(Player, mp.player_id)
            if player:
                players.append(player)

        # Función para calcular distancia al 15 de septiembre
        def distance_to_september_15(birthday: date) -> int:
            target_month, target_day = 9, 15

            def day_of_year(month, day):
                days_per_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                return sum(days_per_month[: month - 1]) + day

            target_day_of_year = day_of_year(target_month, target_day)
            birthday_day_of_year = day_of_year(birthday.month, birthday.day)

            direct_distance = abs(target_day_of_year - birthday_day_of_year)
            circular_distance = 366 - direct_distance

            return min(direct_distance, circular_distance)

        # Calcular distancias
        players_with_distance = [
            (player, distance_to_september_15(player.birthday))
            for player in players
        ]

        # Agrupar por distancia
        grouped_distances = {}
        for player, distance in players_with_distance:
            if distance not in grouped_distances:
                grouped_distances[distance] = []
            grouped_distances[distance].append(player)

        # Ordenar por distancia y randomizar empates
        final_order = []
        for distance in sorted(grouped_distances.keys()):
            tied_players = grouped_distances[distance]
            random.shuffle(tied_players)
            final_order.extend(tied_players)

        # Asignar órdenes (empezando en 1)
        for new_order, player in enumerate(final_order, start=1):
            match_player = next(
                (mp for mp in match_players if mp.player_id == player.id),
                None,
            )
            if match_player:
                match_player.order = new_order

        try:
            self._db.commit()
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise exception

    def start_game(self, match_id: UUID) -> None:
        # Estado de la partida
        self.update_status_match(match_id, MatchStatus.IN_PROGRESS)

        match_players: list[Match_Player] = self.get_players_from_match(match_id)

        # Inicializar cartas y secretos
        Cards_Services(self._db).init_match_cards(match_id)
        Secrets_Services(self._db).init_match_secrets(len(match_players), match_id)

        # Obtener cartas y secretos
        match_cards: list[Match_Card] = Cards_Services(self._db).get_cards_by_match(match_id)
        match_secrets: list[Match_Secret] = Secrets_Services(self._db).get_secrets_by_match(match_id)

        random.shuffle(match_cards)
        random.shuffle(match_secrets)

        # Reparto de secretos
        secrets_unassigned = len(match_secrets)
        while secrets_unassigned > 0:
            for player in match_players:
                if secrets_unassigned == 0:
                    break

                match_secret = match_secrets[secrets_unassigned - 1]
                match_secret.player_id = player.player_id
                secrets_unassigned -= 1

                secret_obj = self._db.get(Secret, match_secret.secret_id)

                if secret_obj and secret_obj.type == Secret_Type.MURDERER:
                    player.role = Secret_Type.MURDERER
                elif player.role == Secret_Type.MURDERER:
                    continue
                else:
                    player.role = Secret_Type.INNOCENT

        # Reparto de cartas
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

        self.assign_player_order(match_id)

        try:
            self._db.commit()
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise exception
