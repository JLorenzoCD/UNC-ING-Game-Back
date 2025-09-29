from uuid import UUID
from datetime import date
import random
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from typing import List

from app.matches.models import Match, Match_Player, MatchStatus
from app.matches import schemas as match_schemas
from app.secrets import schemas as secret_schemas
from app.secrets.models import Secret, Match_Secret, Secret_Type
from app.player.models import Player

from app.matches.utils import db_match_2_match_schema
from app.player.models import Player
from app.cards.models import Match_Card, Card
from app.cards.services import Cards_Services
from app.secrets.models import Match_Secret, Secret, Secret_Type
from app.secrets.services import Secrets_Services


# Excepciones
class OwnerNotFound(Exception):
    pass

class MatchNotFound(Exception):
    pass

class MatchValidationError(Exception):
    pass



class MatchService:
    def __init__(self, db):
        self._db = db
    
    def create(self, match_dto: match_schemas.MatchDTO) -> match_schemas.MatchOut:
        if match_dto.min_players < 2 or match_dto.max_players > 6:
            raise MatchValidationError("Incorrect number of players")
        
        owner:Player = self._db.get(Player, match_dto.owner_id)
        if not owner:
            raise OwnerNotFound()
        
        new_match = Match(
            name = match_dto.name,
            min_players = match_dto.min_players,
            max_players = match_dto.max_players,
            owner_id = owner.id
        )
        try:
            self._db.add(new_match)
            self._db.commit()
            self._db.refresh(new_match)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        try:
            match_player = Match_Player (match_id = new_match.id, player_id=owner.id, order=0)
            self._db.add(match_player)
            self._db.commit()
            self._db.refresh(match_player)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        match_out = db_match_2_match_schema(new_match)
        return match_out  
      

    def get_all(self) -> List[match_schemas.Match_number_of_Player]:
        try:
            matches = self._db.query(Match).all()
            
            combined = []
            for match in matches:
                # Convertir a schema base
                match_out = db_match_2_match_schema(match)
                
                # Obtener conteo de jugadores
                player_count = self.count_players_by_match(match.id)
                
                # Crear schema extendido
                extended_match = match_schemas.Match_number_of_Player(
                    **match_out.model_dump(),
                    current_player_count=player_count
                )
                combined.append(extended_match)
            
            return combined
        except SQLAlchemyError as e:
            self._db.rollback()
            raise
        except Exception as e:
            raise

    def get_match_by_id(self, match_id: UUID) -> Match | None:
        try:
            match: Match = self._db.query(Match).filter(Match.id == match_id).first()
            if not Match:
                raise Exception("Partida no encontrada")
        except Exception:
            raise
        return match
    
    def extended_match(self, match:Match) -> match_schemas.Match_number_of_Player | None:
        # Convertir a schema base
        match_out = db_match_2_match_schema(match)
                
            # Obtener conteo de jugadores
        player_count = self.count_players_by_match(match.id)
                
            # Crear schema extendido
        extended_match = match_schemas.Match_number_of_Player(
                    **match_out.model_dump(),
                    current_player_count=player_count
                )
        return extended_match
        
    def get_players_by_match(self, match_id: UUID) -> List[match_schemas.Players_by_Match_Schema]:
        
        try:    
            match = self._db.query(Match).filter(Match.id == match_id).first()
            if not match:
                raise Exception("Partida no encontrada")
            
            result = []
            for mp in match.match_players:
                result.append({
                    "id": mp.player.id,
                    "player_id": mp.player.id,
                    "match_id" : mp.match.id,
                    "role": mp.role.value if mp.role else None,
                    "order": mp.order,
                    "name": mp.player.name,
                    "avatar": mp.player.avatar,
                    "birthday": mp.player.birthday 
                })
        except Exception as e:
            raise 
        return result
    
    def count_players_by_match(self, match_id: UUID) -> int:
        return (
        self._db.query(Match_Player)
        .filter(Match_Player.match_id == match_id)
        .count()
    )   

    def join(self, match_id:UUID, player_id:UUID):
        match = self._db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        # contar jugadores con el nuevo servicio
        current_players = self.count_players_by_match(match_id)
        if current_players >= match.max_players:
            raise HTTPException(status_code=400, detail="Match is full")
        
        #no se mete 2 veces el mismo jugador
        already_joined = (
        self._db.query(Match_Player)
        .filter(Match_Player.match_id == match_id, Match_Player.player_id == player_id)
        .first()
        )
        if already_joined:
            raise HTTPException(status_code=400, detail="Player already in")

        match_player = Match_Player (match_id = match_id, player_id=player_id, order=0)
        self._db.add(match_player)
        self._db.commit()
        self._db.refresh(match_player)

    def get_cards_by_match (self, match_id:UUID) -> List[match_schemas.Cards_by_Match_Schema]:
          
        try:
            match = self._db.query(Match).filter(Match.id == match_id).first()
            if not match:
                raise Exception("Partida no encontrada")
            
            results = self._db.query(
                Match_Card.id,
                Match_Card.card_id,
                Match_Card.match_id,
                Match_Card.player_id,
                Match_Card.is_discarded,
                Card.name,
                Card.type,
                Card.description
            ).join(Card, Match_Card.card_id == Card.id)\
            .filter(Match_Card.match_id == match_id)\
            .all()
            
            combined: List[match_schemas.Cards_by_Match_Schema] = []
            for r in results:
                combined.append({
                    "id": r.id,
                    "card_id": r.card_id,
                    "match_id": r.match_id,
                    "player_id": r.player_id,
                    "is_discarded": r.is_discarded,
                    "name": r.name,
                    "type": r.type,
                    "description": r.description  
                })
            
            return combined
        except SQLAlchemyError as e:
            raise Exception(f"Database error: {str(e)}")

    def count_players_by_match(self, match_id: UUID) -> int:
        return (
        self._db.query(Match_Player)
        .filter(Match_Player.match_id == match_id)
        .count()
    )

    def get_secrets_by_match(self, match_id: UUID):
        results = (
            self._db.query(Match_Secret, Secret)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .filter(Match_Secret.match_id == match_id)
            .all()
        )

        #formato de info de lo que pide el front
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

    def update_match() -> Match:
        pass

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

    def deal_secrets(self, match_id: UUID, match_secrets: list[Match_Secret], match_players: list[Match_Player]) -> None:
        # Obtener todos los IDs de secretos por tipo
        murderer_secret = self._db.query(Secret).filter(Secret.type == Secret_Type.MURDERER).first()
        accomplice_secret = self._db.query(Secret).filter(Secret.type == Secret_Type.ACCOMPLICE).first()
        innocent_secret_ids = [s.id for s in self._db.query(Secret.id).filter(Secret.type == Secret_Type.INNOCENT).all()]
        
        # Filtrar match_secrets por tipo
        innocent_match_secrets = [ms for ms in match_secrets if ms.secret_id in innocent_secret_ids]
        
        # Crear COPIA de la lista para no modificar la original
        available_players = match_players.copy()
        
        # Reparto de MURDERER
        murderer = random.choice(available_players)
        available_players.remove(murderer)  # ✅ Ahora solo modificas la copia
        
        # Asignar carta de MURDERER
        murderer_secret_match = next(ms for ms in match_secrets if ms.secret_id == murderer_secret.id)
        murderer_secret_match.player_id = murderer.player_id
        murderer.role = Secret_Type.MURDERER
        match_secrets.remove(murderer_secret_match)
        
        # Asignar 2 secretos inocentes al murderer
        for i in range(2):
            innocent_match_secrets[i].player_id = murderer.player_id
            match_secrets.remove(innocent_match_secrets[i])
        
        innocent_match_secrets = innocent_match_secrets[2:]
        
        # Reparto de ACCOMPLICE (solo si existe)
        accomplice_secret_match = next((ms for ms in match_secrets if ms.secret_id == accomplice_secret.id), None)
        
        if accomplice_secret_match:
            accomplice = random.choice(available_players)
            available_players.remove(accomplice)  # ✅ Modificas la copia
            
            accomplice_secret_match.player_id = accomplice.player_id
            accomplice.role = Secret_Type.ACCOMPLICE
            match_secrets.remove(accomplice_secret_match)
            
            # Asignar 2 secretos inocentes al accomplice
            for i in range(2):
                innocent_match_secrets[i].player_id = accomplice.player_id
                match_secrets.remove(innocent_match_secrets[i])
            
            innocent_match_secrets = innocent_match_secrets[2:]
        
        # Repartir el resto de secretos aleatoriamente
        random.shuffle(match_secrets)
        
        if len(available_players) > 0:  # ✅ Usas la copia aquí también
            secrets_per_player = len(match_secrets) // len(available_players)
            
            for idx, player in enumerate(available_players):
                player.role = Secret_Type.INNOCENT
                for i in range(secrets_per_player):
                    secret_idx = idx * secrets_per_player + i
                    match_secrets[secret_idx].player_id = player.player_id
        
        self._db.commit()

    def deal_cards(self, match_id: UUID, match_cards: list[Match_Card], match_players: list[Match_Player]) -> None:
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

    def start_game(self, match_id: UUID) -> None:
        match = self.get_match_by_id(match_id)
        if match.status == MatchStatus.WAITING:
            # Estado de la partida
            self.update_status_match(match_id, MatchStatus.IN_PROGRESS)

            match_players: list[Match_Player] = self.get_players_from_match(match_id)

            # Inicializar cartas y secretos
            Cards_Services(self._db).init_match_cards(match_id, len(match_players))
            Secrets_Services(self._db).init_match_secrets(len(match_players), match_id)

            # Obtener cartas y secretos
            match_cards: list[Match_Card] = Cards_Services(self._db).get_cards_by_match(match_id)
            match_secrets: list[Match_Secret] = Secrets_Services(self._db).get_secrets_by_match(match_id)

            random.shuffle(match_cards)
            random.shuffle(match_secrets)

            # Reparto de secretos
            self.deal_secrets(match_id, match_secrets, match_players)

            # Reparto de cartas
            self.deal_cards(match_id, match_cards, match_players)

            self.assign_player_order(match_id)

            try:
                self._db.commit()
            except SQLAlchemyError as exception:
                self._db.rollback()
                raise exception
        else:
            raise MatchValidationError("Match is not in a valid state to start")