from sqlalchemy import Column, Integer, String, Date, Table, ForeignKey
from sqlalchemy.orm import relationship, mapped_column
from typing import List
from sqlalchemy.orm import Mapped
from db import Base
from datetime import date

class Player(Base):
    """
    Represent a Player

    """

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[str] = mapped_column(String, nullable=False)
    birthday: Mapped[date] = mapped_column(Date,nullable=False)