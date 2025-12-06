import os
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from app import models, schemas, database, security, crypto, utils

router = APIRouter(tags=["Boards"])

# --- BOARDS ---

@router.post("/boards", response_model=schemas.BoardResponse)
async def create_board(
    board: schemas.BoardCreate, 
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    # 1. Create Board
    new_board = models.Board(title=board.title, owner_id=current_user.id)
    db.add(new_board)
    await db.commit()
    await db.refresh(new_board)
    
    # 2. Create Default Columns
    default_columns = ["To Do", "In Progress", "Done"]
    for index, title in enumerate(default_columns):
        new_column = models.KanbanColumn(title=title, position=index, board_id=new_board.id)
        db.add(new_column)
    
    # 3. Log
    await utils.log_action(db, user_id=current_user.id, action="CREATE_BOARD", details=f"Title: {board.title}")
    await db.commit()
    return new_board

@router.get("/boards", response_model=List[schemas.BoardResponse])
async def read_boards(
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.Board).where(models.Board.owner_id == current_user.id))
    return result.scalars().all()

@router.delete("/boards/{board_id}", status_code=204)
async def delete_board(
    board_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.Board).where(models.Board.id == board_id, models.Board.owner_id == current_user.id))
    board = result.scalars().first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    await db.delete(board) 
    await utils.log_action(db, user_id=current_user.id, action="DELETE_BOARD", details=f"ID: {board_id}")
    await db.commit()
    return

# --- COLUMNS (Dynamic) ---

@router.get("/boards/{board_id}/columns", response_model=List[schemas.ColumnResponse])
async def read_board_columns(
    board_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    # Verify board ownership
    result = await db.execute(select(models.Board).where(models.Board.id == board_id, models.Board.owner_id == current_user.id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Board not found")

    # Fetch columns sorted by position
    result = await db.execute(select(models.KanbanColumn).where(models.KanbanColumn.board_id == board_id).order_by(models.KanbanColumn.position))
    return result.scalars().all()

@router.post("/boards/{board_id}/columns", response_model=schemas.ColumnResponse)
async def create_column(
    board_id: int,
    col: schemas.ColumnCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    # 1. Verify Board
    result = await db.execute(select(models.Board).where(models.Board.id == board_id, models.Board.owner_id == current_user.id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Board not found")

    # 2. Calculate Position (Append to end)
    # Get current max position
    stmt = select(models.KanbanColumn).where(models.KanbanColumn.board_id == board_id).order_by(models.KanbanColumn.position.desc())
    result = await db.execute(stmt)
    last_col = result.scalars().first()
    new_position = (last_col.position + 1) if last_col else 0

    # 3. Create
    new_col = models.KanbanColumn(title=col.title, position=new_position, board_id=board_id)
    db.add(new_col)
    
    # 4. Log
    await utils.log_action(db, user_id=current_user.id, action="CREATE_COLUMN", details=f"Title: {col.title}")
    
    await db.commit()
    await db.refresh(new_col)
    return new_col

@router.delete("/columns/{column_id}", status_code=204)
async def delete_column(
    column_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    # 1. Get Column (and check board ownership via join, or just trust ID for MVP)
    # For security, we should ideally check if the user owns the board this column is on.
    stmt = (
        select(models.KanbanColumn)
        .join(models.Board)
        .where(models.KanbanColumn.id == column_id, models.Board.owner_id == current_user.id)
    )
    result = await db.execute(stmt)
    col = result.scalars().first()
    
    if not col:
        raise HTTPException(status_code=404, detail="Column not found or access denied")

    # 2. Delete (Cascade will handle cards)
    await db.delete(col)
    await utils.log_action(db, user_id=current_user.id, action="DELETE_COLUMN", details=f"ID: {column_id}")
    await db.commit()
    return

# --- CARDS ---

@router.get("/boards/{board_id}/cards", response_model=List[schemas.CardResponse])
async def read_board_cards(
    board_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    stmt = (
        select(models.Card)
        .options(selectinload(models.Card.attachments), selectinload(models.Card.checklist))
        .join(models.KanbanColumn)
        .where(models.KanbanColumn.board_id == board_id)
    )
    result = await db.execute(stmt)
    cards = result.scalars().all()
    
    for card in cards:
        try: card.description = crypto.decrypt_data(card.description)
        except: card.description = "[Error Decrypting]"
        for item in card.checklist:
            try: item.content = crypto.decrypt_data(item.content)
            except: item.content = "[Error Decrypting]"
    return cards

@router.post("/cards", response_model=schemas.CardResponse)
async def create_card(
    card: schemas.CardCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    encrypted_description = crypto.encrypt_data(card.description)
    new_card = models.Card(title=card.title, description=encrypted_description, column_id=card.column_id, position=card.position)
    db.add(new_card)
    await db.commit()
    
    stmt = select(models.Card).options(selectinload(models.Card.attachments), selectinload(models.Card.checklist)).where(models.Card.id == new_card.id)
    result = await db.execute(stmt)
    final_card = result.scalars().first()
    final_card.description = card.description 
    return final_card

@router.patch("/cards/{card_id}/move", response_model=schemas.CardResponse)
async def move_card(
    card_id: int, column_id: int, position: int,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.Card).where(models.Card.id == card_id))
    card = result.scalars().first()
    if not card: raise HTTPException(status_code=404, detail="Card not found")
    card.column_id = column_id
    card.position = position
    await db.commit()
    await db.refresh(card)
    return card

@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(
    card_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.Card).where(models.Card.id == card_id))
    card = result.scalars().first()
    if not card: raise HTTPException(status_code=404, detail="Card not found")
    
    await db.delete(card)
    await utils.log_action(db, user_id=current_user.id, action="DELETE_CARD", details=f"ID: {card_id}")
    await db.commit()
    return

# --- ATTACHMENTS ---

from app.limiter import limiter # Need limiter imported to use it, though decorator handles it in main

@router.post("/cards/{card_id}/attachments", response_model=schemas.AttachmentResponse)
async def upload_attachment(
    request: Request, # <--- FIXED: Must be 'Request' type
    card_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.Card).where(models.Card.id == card_id))
    card = result.scalars().first()
    if not card: raise HTTPException(status_code=404, detail="Card not found")

    try:
        file_data = await utils.validate_and_save_file(file)
    except HTTPException as e:
        await utils.log_action(db, user_id=current_user.id, action="MALWARE_DETECTED", details=f"File: {file.filename} | Error: {e.detail}")
        await db.commit()
        raise e 

    new_attachment = models.Attachment(
        filename=file_data["filename"], file_path=file_data["file_path"],
        file_size=file_data["file_size"], content_type=file.content_type, card_id=card_id
    )
    db.add(new_attachment)
    await utils.log_action(db, user_id=current_user.id, action="UPLOAD_FILE", details=file_data["filename"])
    await db.commit()
    await db.refresh(new_attachment)
    return new_attachment

@router.get("/attachments/{attachment_id}")
async def download_attachment(
    attachment_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.Attachment).where(models.Attachment.id == attachment_id))
    attachment = result.scalars().first()
    if not attachment: raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(path=attachment.file_path, filename=attachment.filename, media_type=attachment.content_type)

@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.Attachment).where(models.Attachment.id == attachment_id))
    attachment = result.scalars().first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Forensic Preservation: We delete from DB but keep the file on disk
    await db.delete(attachment)
    
    await utils.log_action(
        db, 
        user_id=current_user.id, 
        action="UNLINK_FILE", 
        details=f"ID: {attachment_id} | Filename: {attachment.filename} | (Evidence Preserved on Disk)"
    )
    
    await db.commit()
    return

# --- CHECKLISTS ---

@router.post("/cards/{card_id}/checklist", response_model=schemas.ChecklistItemResponse)
async def create_checklist_item(
    card_id: int, item: schemas.ChecklistItemCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    encrypted_content = crypto.encrypt_data(item.content)
    new_item = models.ChecklistItem(content=encrypted_content, card_id=card_id, is_completed=False)
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    new_item.content = item.content
    return new_item

@router.patch("/checklist/{item_id}", response_model=schemas.ChecklistItemResponse)
async def update_checklist_item(
    item_id: int, update_data: schemas.ChecklistItemUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.ChecklistItem).where(models.ChecklistItem.id == item_id))
    item = result.scalars().first()
    if not item: raise HTTPException(status_code=404, detail="Item not found")

    item.is_completed = update_data.is_completed
    action = "COMPLETED_SUBTASK" if item.is_completed else "UNCHECKED_SUBTASK"
    await utils.log_action(db, user_id=current_user.id, action=action, details=f"Item ID: {item_id}")
    await db.commit()
    await db.refresh(item)
    item.content = crypto.decrypt_data(item.content)
    return item

@router.delete("/checklist/{item_id}", status_code=204)
async def delete_checklist_item(
    item_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.ChecklistItem).where(models.ChecklistItem.id == item_id))
    item = result.scalars().first()
    if not item: raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(item)
    await utils.log_action(db, user_id=current_user.id, action="DELETE_SUBTASK", details=f"ID: {item_id}")
    await db.commit()
    return
