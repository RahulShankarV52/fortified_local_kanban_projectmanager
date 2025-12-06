import os
import uuid
import yara
from fastapi import UploadFile, HTTPException
from app import models
from sqlalchemy.ext.asyncio import AsyncSession

# 1. DEFINE MALWARE RULES (YARA)
# We use r""" (Raw String) so Python doesn't mess with the backslashes.
# In YARA, we must escape the backslash, so we write \\ to mean "one backslash".
YARA_RULES = r"""
rule Eicar_Test_File {
    strings:
        $eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    condition:
        $eicar
}
"""
scanner = yara.compile(source=YARA_RULES)

# 2. MAGIC BYTE VALIDATION
ALLOWED_MAGIC_BYTES = {
    b'\xFF\xD8\xFF': "image/jpeg",
    b'\x89PNG\r\n\x1a\n': "image/png",
    b'%PDF': "application/pdf"
}

async def validate_and_save_file(file: UploadFile, upload_dir: str = "uploads") -> dict:
    # A. Read the first 2048 bytes (Header)
    header = await file.read(2048)
    await file.seek(0) # Reset cursor to start
    
    # B. Check Magic Bytes
    # For the portfolio demo, we will LOG invalid types but allow them 
    # so you can test uploading the "virus.txt" (which is text, not an image).
    is_valid = False
    for magic_bytes, mime_type in ALLOWED_MAGIC_BYTES.items():
        if header.startswith(magic_bytes):
            is_valid = True
            break
            
    # If you want strict security, uncomment the lines below:
    # if not is_valid:
    #     raise HTTPException(400, "Invalid file type. Only Images and PDF allowed.")

    # C. YARA SCAN (Memory Scan)
    content = await file.read()
    matches = scanner.match(data=content)
    if matches:
        raise HTTPException(400, f"Malware Detected: {matches[0]}")
    
    await file.seek(0) # Reset cursor again

    # D. Sanitization (Rename)
    file_ext = os.path.splitext(file.filename)[1]
    secure_filename = f"{uuid.uuid4()}{file_ext}"
    save_path = os.path.join(upload_dir, secure_filename)
    
    # Ensure directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    # E. Save to Disk
    import aiofiles
    async with aiofiles.open(save_path, 'wb') as out_file:
        while content := await file.read(1024 * 1024):
            await out_file.write(content)
            
    return {
        "filename": file.filename,
        "file_path": save_path,
        "file_size": os.path.getsize(save_path)
    }
async def log_action(db: AsyncSession, user_id: int, action: str, details: str = None):
    """
    Records a security event to the database.
    """
    new_log = models.AuditLog(
        user_id=user_id,
        action=action,
        details=details
    )
    db.add(new_log)
    # We don't commit here because this is usually part of a larger transaction.
    # The caller will commit.
