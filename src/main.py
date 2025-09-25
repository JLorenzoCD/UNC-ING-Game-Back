from fastapi import FastAPI
from websocketManager.ws_routes import websocket_router
from sqlalchemy.orm import Session
import uuid

from app.models.db import engine

from app.matches.models import Match, Match_Player
from app.player.models import Player
from app.cards.models import Card, Match_Card
from app.secrets.models import Secret, Match_Secret

from app.models.db import Base, engine
from app.player.endpoints import player_router
from app.matches.endpoints import router as matches_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # o ["*"] para todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_router)
app.include_router(player_router)
app.include_router(matches_router)

def init_data():
    with Session(engine) as session:
        # Verificar si ya existen secretos
        if not session.query(Secret).first():
            session.add_all([
                Secret(id=uuid.uuid4(), type="MURDERER", content="You are the Murderer!"),
                Secret(id=uuid.uuid4(), type="ACCOMPLICE", content="You are the Accomplice!"),
                Secret(id=uuid.uuid4(), type="INNOCENT", content="You are Innocent!")
            ])
            session.commit()
        
        if not session.query(Card).first():
            session.add_all([
                # Instant Cards
                Card(id=uuid.uuid4(), name="NOT SO FAST", type="INSTANT", description="Play this card at any time, even if it is not your turn. It cancels an action before it is taken, unless otherwise stated, including cancelling another 'Not so fast...' card."),
        
                # Detective Cards
                Card(id=uuid.uuid4(), name="PARKER PYNE", type="DETECTIVE", description="Parker Pyne focuses on helping his clients achieve happiness... Instead of revealing a secret card, flip any face-up secret card face-down. This may remove social disgrace."),
                Card(id=uuid.uuid4(), name="LADY EILEEN", type="DETECTIVE", description="Bundle realises a vital clue was missed... Choose a player who must reveal a secret card of their choice. If cancelled by a 'Not so fast...' card, return the detective set to your hand."),
                Card(id=uuid.uuid4(), name="TOMMY BERESFORD", type="DETECTIVE", description="Tommy finds a clue... Choose a player, who must reveal a secret card of their choice. If a Tommy and a Tuppence are in the same set, the action cannot be cancelled by a 'Not so Fast...' card."),
                Card(id=uuid.uuid4(), name="TUPPENCE BERESFORD", type="DETECTIVE", description="Tuppence finds a clue... Choose a player, who must reveal a secret card of their choice. If a Tuppence and Tommy are in the same set, the action cannot be cancelled by a 'Not so Fast...' card."),
                Card(id=uuid.uuid4(), name="HARLEY QUIN WILDCARD", type="DETECTIVE", description="Quin has an almost supernatural gift for helping solve the crime... Play in conjunction with any original detective card to play a set in front of you."),
                Card(id=uuid.uuid4(), name="ARIADNE OLIVER", type="DETECTIVE", description="Mrs Oliver spots something that others had missed... Add to any existing set on the table. The player owning the set must reveal a secret card of their choice. May only be added, and not played as a set."),
                Card(id=uuid.uuid4(), name="HERCULE POIROT", type="DETECTIVE", description="Poirot finds a suspicious document once thought lost... Choose a player, who must reveal a secret card of your choice."),
                Card(id=uuid.uuid4(), name="MISS MARPLE", type="DETECTIVE", description="Miss Marple notices a small detail that grows in importance... Choose a player, who must reveal a secret card of your choice."),
                Card(id=uuid.uuid4(), name="MR SATTERTHWAITE", type="DETECTIVE", description="Mr Satterthwaite finds an odd thing... Choose a player, who must reveal a secret card of their choice. If this set is played with a Harley Quin Wildcard, add the revealed secret card, face-down, to your secrets."),
                
                # Event Cards
                Card(id=uuid.uuid4(), name="CARDS OFF THE TABLE", type="EVENT", description="Their plans are discovered! Choose a player, who must discard all the 'Not so fast...' cards in their hand. The action cannot be cancelled by a 'Not so fast...' card."),
                Card(id=uuid.uuid4(), name="ANOTHER VICTIM", type="EVENT", description="Take any existing set from another player and play it in front of you. You now own this set."),
                Card(id=uuid.uuid4(), name="DEAD CARD FOLLY", type="EVENT", description="All players must pass one card from their hand, face-down, to the player on their right or left. The active player decides which direction. You may ask for a card of your choice, but beware you may be tricked."),
                Card(id=uuid.uuid4(), name="LOOK INTO THE ASHES", type="EVENT", description="A pattern emerges! You may look though the top five cards of the discard pile and take one into your hand."),
                Card(id=uuid.uuid4(), name="CARD TRADE", type="EVENT", description="Meet in the drawing room for high tea. Choose another player and exchange one card from your hand with them. They cannot refuse. You may ask for a card of your choice, but beware you may be tricked."),
                Card(id=uuid.uuid4(), name="AND THEN THERE WAS ONE MORE", type="EVENT", description="Choose one revealed secret card and add it, face-down, to any player's secrets, including your own. This may remove social disgrace."),
                Card(id=uuid.uuid4(), name="DELAY THE MURDERER ESCAPE", type="EVENT", description="Take up to five cards from the top of the discard pile and place them face-down on the draw pile in any order, then remove this card from the game."),
                Card(id=uuid.uuid4(), name="EARLY TRAIN TO PADDINGTON", type="EVENT", description="The murderer's escape nears! Take the top six cards from the draw pile and place them face-up on the discard pile, then remove this card from the game. Discarding this card is treated the same as if you had played it."),
                Card(id=uuid.uuid4(), name="POINT YOUR SUSPICIONS", type="EVENT", description="All the guests are gathered in the dining room... The active player counts down: 3-2-1. Then all players must point at the person they suspect as the Murderer. The active player breaks ties. The most suspected player must reveal a secret card of their choice."),
                
                # Devious Cards
                Card(id=uuid.uuid4(), name="BLACKMAILED", type="DEVIOUS", description="You have been blackmailed! If you have received this card from another player, you must show them one secret card of their choice, before returning it face-down to your secrets. This action cannot be cancelled by a 'Not so fast...' card. This card can only be used during a Card Trade or a Dead Card Folly."),
                Card(id=uuid.uuid4(), name="SOCIAL FAUX PAS", type="DEVIOUS", description="At dinner, you have been tricked into ordering a dessert wine with a starter... If you have received this card from another player, you must reveal a secret card of your choice. This card can only be used during a Card Trade or a Dead Card Folly.")
            ])
            session.commit()

Base.metadata.create_all(bind=engine)
init_data()