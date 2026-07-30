import jwt
from app.core.config import settings

class JWTService:
    """
    Handles JWT signature and expiration verification for authorization.
    """
    def decode_token(self, token: str) -> dict:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp"]}
        )

jwt_service = JWTService()
