#what databse looks like
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# 1. THE USERS TABLE
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # We store the HASH, never the password itself
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="viewer") # For RBAC later
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship: One User has many Boards
    boards = relationship("Board", back_populates="owner")


# 2. THE BOARDS TABLE
class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship("User", back_populates="boards")
    columns = relationship("KanbanColumn", back_populates="board", cascade="all, delete-orphan")


# 3. THE COLUMNS TABLE (e.g., "To Do", "In Progress")
class KanbanColumn(Base):
    __tablename__ = "kanban_columns"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False) # "To Do", "Done"
    position = Column(Integer, nullable=False) # 0, 1, 2 (Order on screen)
    board_id = Column(Integer, ForeignKey("boards.id"))

    # Relationships
    board = relationship("Board", back_populates="columns")
    cards = relationship("Card", back_populates="column", cascade="all, delete-orphan")


# 4. THE CARDS TABLE (The tasks)
class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True) # Will be Encrypted later!
    position = Column(Integer, nullable=False) # Order within the column
    column_id = Column(Integer, ForeignKey("kanban_columns.id"))

    # Metadata for Security/Auditing
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    column = relationship("KanbanColumn", back_populates="cards")
    attachments = relationship("Attachment", back_populates="card", cascade="all, delete-orphan")
    checklist = relationship("ChecklistItem", back_populates="card", cascade="all, delete-orphan")

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False) # Original name (e.g., "virus.exe")
    file_path = Column(String, nullable=False) # Secure path (e.g., "uploads/550e84...")
    file_size = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False) # MIME type
    
    # Link to a Card
    card_id = Column(Integer, ForeignKey("cards.id"))
    
    # Metadata for Auditing
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    card = relationship("Card", back_populates="attachments")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)      # e.g., "CREATE_CARD", "MALWARE_DETECTED"
    details = Column(String, nullable=True)      # e.g., "Card ID: 5", "Virus Name: Eicar"
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user = relationship("User")

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False) # Will be Encrypted!
    is_completed = Column(Boolean, default=False)
    card_id = Column(Integer, ForeignKey("cards.id"))

    # Relationship
    card = relationship("Card", back_populates="checklist")
