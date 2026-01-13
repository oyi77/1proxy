import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext

# Get SECRET_KEY from environment - NO DEFAULT for security
SECRET_KEY = os.getenv("SECRET_KEY")
if (
    not SECRET_KEY
    or SECRET_KEY == "your-secret-key-change-in-production-VERY-IMPORTANT"
):
    raise RuntimeError(
        "🔐 CRITICAL: SECRET_KEY must be set in environment variables!\n"
        "   Set a strong secret key (min 32 characters):\n"
        "   export SECRET_KEY='your-secure-random-key-here'\n"
        "   Or add to .env file: SECRET_KEY=your-secure-random-key-here"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
