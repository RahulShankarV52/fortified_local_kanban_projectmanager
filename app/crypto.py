from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("ENCRYPTION_KEY")

if not key:
    raise ValueError("No ENCRYPTION_KEY found in .env file!")

cipher = Fernet(key)

def encrypt_data(data: str) -> str:
    """Takes a plain string, returns an encrypted string."""
    if not data:
        return None
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(data: str) -> str:
    """Takes an encrypted string, returns the plain string."""
    if not data:
        return None
    try:
        return cipher.decrypt(data.encode()).decode()
    except Exception:
        # If decryption fails (e.g., bad key or data wasn't encrypted), 
        # return the raw data or an error marker.
        return "[Decryption Error]"
