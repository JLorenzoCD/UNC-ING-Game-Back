import uuid

from sqlalchemy.orm import Session

from app.cards.models import Card, Card_Type
from app.secrets.models import Secret


class DatabaseInitService:
    """
    Servicio para inicializar datos base en la base de datos.
    Maneja la creación de cartas y secretos iniciales necesarios para el juego.
    """

    def __init__(self, db: Session):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def init_all_data(self) -> None:
        """Inicializa todos los datos base del juego."""
        self.init_base_secrets()
        self.init_base_cards()

    def init_base_cards(self) -> None:
        """Inicializa las cartas base del juego si no existen."""
        if not self._db.query(Card).first():
            cards = [
                Card(
                    id=uuid.uuid4(),
                    name="NOT_SO_FAST",
                    type=Card_Type.INSTANT,
                    description="Play this card at any time, even if it is not your turn. It cancels an action before it is taken, unless otherwise stated, including cancelling another 'Not so fast...' card.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="PARKER_PYNE",
                    type=Card_Type.DETECTIVE,
                    description="Parker Pyne focuses on helping his clients achieve happiness... Instead of revealing a secret card, flip any face-up secret card face-down. This may remove social disgrace.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="LADY_EILEEN",
                    type=Card_Type.DETECTIVE,
                    description="Bundle realises a vital clue was missed... Choose a player who must reveal a secret card of their choice. If cancelled by a 'Not so fast...' card, return the detective set to your hand.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="TOMMY_BERESFORD",
                    type=Card_Type.DETECTIVE,
                    description="Tommy finds a clue... Choose a player, who must reveal a secret card of their choice. If a Tommy and a Tuppence are in the same set, the action cannot be cancelled by a 'Not so Fast...' card.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="TUPPENCE_BERESFORD",
                    type=Card_Type.DETECTIVE,
                    description="Tuppence finds a clue... Choose a player, who must reveal a secret card of their choice. If a Tuppence and Tommy are in the same set, the action cannot be cancelled by a 'Not so Fast...' card.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="HARLEY_QUIN_WILDCARD",
                    type=Card_Type.DETECTIVE,
                    description="Quin has an almost supernatural gift for helping solve the crime... Play in conjunction with any original detective card to play a set in front of you.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="ARIADNE_OLIVER",
                    type=Card_Type.DETECTIVE,
                    description="Mrs Oliver spots something that others had missed... Add to any existing set on the table. The player owning the set must reveal a secret card of their choice. May only be added, and not played as a set.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="HERCULE_POIROT",
                    type=Card_Type.DETECTIVE,
                    description="Poirot finds a suspicious document once thought lost... Choose a player, who must reveal a secret card of your choice.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="MISS_MARPLE",
                    type=Card_Type.DETECTIVE,
                    description="Miss Marple notices a small detail that grows in importance... Choose a player, who must reveal a secret card of your choice.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="MR_SATTERTHWAITE",
                    type=Card_Type.DETECTIVE,
                    description="Mr Satterthwaite finds an odd thing... Choose a player, who must reveal a secret card of their choice. If this set is played with a Harley Quin Wildcard, add the revealed secret card, face-down, to your secrets.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="CARDS_OFF_THE_TABLE",
                    type=Card_Type.EVENT,
                    description="Their plans are discovered! Choose a player, who must discard all the 'Not so fast...' cards in their hand. The action cannot be cancelled by a 'Not so fast...' card.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="ANOTHER_VICTIM",
                    type=Card_Type.EVENT,
                    description="Take any existing set from another player and play it in front of you. You now own this set.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="DEAD_CARD_FOLLY",
                    type=Card_Type.EVENT,
                    description="All players must pass one card from their hand, face-down, to the player on their right or left. The active player decides which direction. You may ask for a card of your choice, but beware you may be tricked.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="LOOK_INTO_THE_ASHES",
                    type=Card_Type.EVENT,
                    description="A pattern emerges! You may look though the top five cards of the discard pile and take one into your hand.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="CARD_TRADE",
                    type=Card_Type.EVENT,
                    description="Meet in the drawing room for high tea. Choose another player and exchange one card from your hand with them. They cannot refuse. You may ask for a card of your choice, but beware you may be tricked.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="AND_THEN_THERE_WAS_ONE_MORE",
                    type=Card_Type.EVENT,
                    description="Choose one revealed secret card and add it, face-down, to any player's secrets, including your own. This may remove social disgrace.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="DELAY_THE_MURDERER_ESCAPE",
                    type=Card_Type.EVENT,
                    description="Take up to five cards from the top of the discard pile and place them face-down on the draw pile in any order, then remove this card from the game.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="EARLY_TRAIN_TO_PADDINGTON",
                    type=Card_Type.EVENT,
                    description="The murderer's escape nears! Take the top six cards from the draw pile and place them face-up on the discard pile, then remove this card from the game. Discarding this card is treated the same as if you had played it.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="POINT_YOUR_SUSPICIONS",
                    type=Card_Type.EVENT,
                    description="All the guests are gathered in the dining room... The active player counts down: 3-2-1. Then all players must point at the person they suspect as the Murderer. The active player breaks ties. The most suspected player must reveal a secret card of their choice.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="BLACKMAILED",
                    type=Card_Type.DEVIOUS,
                    description="You have been blackmailed! If you have received this card from another player, you must show them one secret card of their choice, before returning it face-down to your secrets. This action cannot be cancelled by a 'Not so fast...' card. This card can only be used during a Card Trade or a Dead Card Folly.",
                ),
                Card(
                    id=uuid.uuid4(),
                    name="SOCIAL_FAUX_PAS",
                    type=Card_Type.DEVIOUS,
                    description="At dinner, you have been tricked into ordering a dessert wine with a starter... If you have received this card from another player, you must reveal a secret card of your choice. This card can only be used during a Card Trade or a Dead Card Folly.",
                ),
            ]
            self._db.add_all(cards)
            self._db.commit()

    def init_base_secrets(self) -> None:
        """Inicializa los secretos base del juego si no existen."""
        if not self._db.query(Secret).first():
            secrets = [
                Secret(
                    id=uuid.uuid4(), type="MURDERER", content="You are the Murderer!"
                ),
                Secret(
                    id=uuid.uuid4(),
                    type="ACCOMPLICE",
                    content="You are the Accomplice!",
                ),
                Secret(id=uuid.uuid4(), type="INNOCENT", content="You are Innocent!"),
            ]
            self._db.add_all(secrets)
            self._db.commit()


def init_data(db: Session) -> None:
    """Función de conveniencia para inicializar todos los datos base."""
    service = DatabaseInitService(db)
    service.init_all_data()
