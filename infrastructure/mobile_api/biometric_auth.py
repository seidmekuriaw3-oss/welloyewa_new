# ============================
# WOLLOYEWA STORE BOT - BIOMETRIC AUTH
# ============================
"""Biometric authentication support for mobile apps."""

import hashlib
import secrets
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from infrastructure.redis.client import get_redis_client
from core.logger import logger


class BiometricType(str, Enum):
    """Biometric authentication types."""
    FINGERPRINT = "fingerprint"
    FACE_ID = "face_id"
    IRIS = "iris"
    VOICE = "voice"


class BiometricStatus(str, Enum):
    """Biometric session status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class BiometricSession:
    """Biometric authentication session."""
    
    session_id: str
    user_id: int
    biometric_type: BiometricType
    device_id: str
    device_name: Optional[str]
    status: BiometricStatus = BiometricStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BiometricVerificationResult:
    """Biometric verification result."""
    
    verified: bool
    session_id: str
    user_id: int
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BiometricAuthManager:
    """
    Biometric authentication manager.
    
    Features:
    - Biometric session management
    - Secure token generation
    - Device binding
    - Session expiration
    """
    
    def __init__(self):
        self._redis = None
        self._sessions: Dict[str, BiometricSession] = {}
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def create_biometric_session(
        self,
        user_id: int,
        biometric_type: BiometricType,
        device_id: str,
        device_name: Optional[str] = None,
    ) -> BiometricSession:
        """
        Create a biometric authentication session.
        
        Args:
            user_id: User ID
            biometric_type: Type of biometric
            device_id: Device identifier
            device_name: Optional device name
            
        Returns:
            BiometricSession
        """
        import uuid
        redis = await self._get_redis()
        
        session_id = str(uuid.uuid4())
        
        session = BiometricSession(
            session_id=session_id,
            user_id=user_id,
            biometric_type=biometric_type,
            device_id=device_id,
            device_name=device_name,
        )
        
        # Store session
        self._sessions[session_id] = session
        
        # Store in Redis for persistence
        key = f"biometric:session:{session_id}"
        await redis.setex(
            key,
            30 * 86400,  # 30 days
            self._session_to_dict(session),
        )
        
        # Add to user's sessions
        await redis.sadd(f"biometric:user:{user_id}:sessions", session_id)
        
        logger.info(f"Created biometric session {session_id} for user {user_id}")
        return session
    
    async def verify_biometric(
        self,
        session_id: str,
        biometric_data: str,
    ) -> BiometricVerificationResult:
        """
        Verify biometric authentication.
        
        Args:
            session_id: Session ID
            biometric_data: Biometric data (token/encrypted)
            
        Returns:
            Verification result
        """
        redis = await self._get_redis()
        
        # Get session
        session = await self.get_session(session_id)
        
        if not session:
            return BiometricVerificationResult(
                verified=False,
                session_id=session_id,
                user_id=0,
                message="Session not found",
            )
        
        if session.status != BiometricStatus.ACTIVE:
            return BiometricVerificationResult(
                verified=False,
                session_id=session_id,
                user_id=session.user_id,
                message=f"Session is {session.status.value}",
            )
        
        if session.expires_at < datetime.utcnow():
            session.status = BiometricStatus.EXPIRED
            await self.update_session(session)
            return BiometricVerificationResult(
                verified=False,
                session_id=session_id,
                user_id=session.user_id,
                message="Session expired",
            )
        
        # Verify biometric data
        # In production, this would involve cryptographic verification
        # using device-generated tokens
        
        is_valid = await self._verify_biometric_data(session, biometric_data)
        
        if is_valid:
            session.last_used = datetime.utcnow()
            await self.update_session(session)
            logger.info(f"Biometric verification successful for session {session_id}")
            
            return BiometricVerificationResult(
                verified=True,
                session_id=session_id,
                user_id=session.user_id,
                message="Verification successful",
            )
        else:
            logger.warning(f"Biometric verification failed for session {session_id}")
            
            return BiometricVerificationResult(
                verified=False,
                session_id=session_id,
                user_id=session.user_id,
                message="Verification failed",
            )
    
    async def _verify_biometric_data(
        self,
        session: BiometricSession,
        biometric_data: str,
    ) -> bool:
        """Verify biometric data against stored credentials."""
        # In production, this would use proper cryptographic verification
        # For now, simple check
        stored_key = f"biometric:key:{session.user_id}:{session.device_id}"
        redis = await self._get_redis()
        
        expected = await redis.get(stored_key)
        
        if expected:
            return biometric_data == expected
        
        # First time - store the biometric data as the reference
        await redis.setex(stored_key, 30 * 86400, biometric_data)
        return True
    
    async def revoke_biometric_session(self, session_id: str) -> bool:
        """
        Revoke a biometric session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if revoked
        """
        redis = await self._get_redis()
        
        session = await self.get_session(session_id)
        
        if not session:
            return False
        
        session.status = BiometricStatus.REVOKED
        await self.update_session(session)
        
        # Remove from user's sessions
        await redis.srem(f"biometric:user:{session.user_id}:sessions", session_id)
        
        logger.info(f"Revoked biometric session {session_id}")
        return True
    
    async def get_session(self, session_id: str) -> Optional[BiometricSession]:
        """Get biometric session by ID."""
        if session_id in self._sessions:
            return self._sessions[session_id]
        
        redis = await self._get_redis()
        key = f"biometric:session:{session_id}"
        data = await redis.get(key)
        
        if data:
            return self._dict_to_session(data)
        
        return None
    
    async def update_session(self, session: BiometricSession) -> None:
        """Update biometric session."""
        self._sessions[session.session_id] = session
        
        redis = await self._get_redis()
        key = f"biometric:session:{session.session_id}"
        await redis.setex(key, 30 * 86400, self._session_to_dict(session))
    
    async def get_user_sessions(self, user_id: int) -> List[BiometricSession]:
        """Get all biometric sessions for a user."""
        redis = await self._get_redis()
        
        session_ids = await redis.smembers(f"biometric:user:{user_id}:sessions")
        
        sessions = []
        for sid in session_ids:
            sid = sid.decode() if isinstance(sid, bytes) else sid
            session = await self.get_session(sid)
            if session:
                sessions.append(session)
        
        return sessions
    
    def _session_to_dict(self, session: BiometricSession) -> str:
        """Convert session to dict string."""
        import json
        return json.dumps({
            "session_id": session.session_id,
            "user_id": session.user_id,
            "biometric_type": session.biometric_type.value,
            "device_id": session.device_id,
            "device_name": session.device_name,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "last_used": session.last_used.isoformat() if session.last_used else None,
            "metadata": session.metadata,
        }, default=str)
    
    def _dict_to_session(self, data: str) -> BiometricSession:
        """Create session from dict string."""
        import json
        data = json.loads(data)
        return BiometricSession(
            session_id=data["session_id"],
            user_id=data["user_id"],
            biometric_type=BiometricType(data["biometric_type"]),
            device_id=data["device_id"],
            device_name=data.get("device_name"),
            status=BiometricStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            metadata=data.get("metadata", {}),
        )


# Global biometric auth manager
biometric_auth = BiometricAuthManager()


async def create_biometric_session(
    user_id: int,
    biometric_type: str,
    device_id: str,
    device_name: Optional[str] = None,
) -> BiometricSession:
    """Create a biometric authentication session."""
    return await biometric_auth.create_biometric_session(
        user_id, BiometricType(biometric_type), device_id, device_name
    )


async def verify_biometric(session_id: str, biometric_data: str) -> BiometricVerificationResult:
    """Verify biometric authentication."""
    return await biometric_auth.verify_biometric(session_id, biometric_data)


async def revoke_biometric_session(session_id: str) -> bool:
    """Revoke a biometric session."""
    return await biometric_auth.revoke_biometric_session(session_id)


__all__ = [
    "BiometricAuthManager",
    "BiometricSession",
    "BiometricType",
    "BiometricStatus",
    "BiometricVerificationResult",
    "biometric_auth",
    "create_biometric_session",
    "verify_biometric",
    "revoke_biometric_session",
]