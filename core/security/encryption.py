# ============================
# WOLLOYEWA STORE BOT - ENCRYPTION
# ============================
"""Data encryption and hashing utilities for sensitive information."""

import base64
import hashlib
import secrets
from typing import Optional, Union, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from core.config import settings
from core.logger import logger


class EncryptionManager:
    """
    Manages encryption and decryption of sensitive data.
    
    Supports:
    - Fernet symmetric encryption
    - AES-256 encryption
    - PBKDF2 key derivation
    """
    
    def __init__(self):
        self._fernet = None
        self._init_fernet()
    
    def _init_fernet(self) -> None:
        """Initialize Fernet encryption."""
        key = settings.ENCRYPTION_KEY
        if key:
            try:
                self._fernet = Fernet(key.encode())
                return
            except ValueError as exc:
                msg = (
                    "ENCRYPTION_KEY is set but invalid (wrong length/format). "
                    "Generate a valid key with: "
                    "python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
                if settings.ENVIRONMENT == "production":
                    raise RuntimeError(msg) from exc
                logger.warning(msg + " — falling back to temporary key (development only).")

        if settings.ENVIRONMENT == "production":
            raise RuntimeError(
                "ENCRYPTION_KEY must be set to a valid Fernet key in production. "
                "Generate one with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        # Development/testing only: use a per-session temporary key
        temp_key = Fernet.generate_key()
        self._fernet = Fernet(temp_key)
        logger.warning(
            "Using a temporary per-session encryption key. "
            "Encrypted data will NOT survive restarts. Set ENCRYPTION_KEY for persistence."
        )
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data using Fernet.
        
        Args:
            data: Data to encrypt (string or bytes)
            
        Returns:
            Base64 encoded encrypted string
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = self._fernet.encrypt(data)
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data using Fernet.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted string
        """
        try:
            data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted = self._fernet.decrypt(data)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
    
    def encrypt_aes(
        self,
        data: Union[str, bytes],
        password: str,
        salt: Optional[bytes] = None,
    ) -> tuple:
        """
        Encrypt data using AES-256.
        
        Args:
            data: Data to encrypt
            password: Password for key derivation
            salt: Salt for key derivation (generated if not provided)
            
        Returns:
            Tuple of (ciphertext, salt, iv)
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if salt is None:
            salt = secrets.token_bytes(16)
        
        # Derive key using PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key = kdf.derive(password.encode('utf-8'))
        
        # Generate IV
        iv = secrets.token_bytes(16)
        
        # Encrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CFB(iv),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return ciphertext, salt, iv
    
    def decrypt_aes(
        self,
        ciphertext: bytes,
        password: str,
        salt: bytes,
        iv: bytes,
    ) -> str:
        """
        Decrypt AES-256 encrypted data.
        
        Args:
            ciphertext: Encrypted data
            password: Password for key derivation
            salt: Salt used during encryption
            iv: Initialization vector used during encryption
            
        Returns:
            Decrypted string
        """
        # Derive key using PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key = kdf.derive(password.encode('utf-8'))
        
        # Decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CFB(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(ciphertext) + decryptor.finalize()
        
        return decrypted.decode('utf-8')


def encrypt_data(data: Union[str, bytes]) -> str:
    """Encrypt data using default encryption manager."""
    return encryption_manager.encrypt(data)


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data using default encryption manager."""
    return encryption_manager.decrypt(encrypted_data)


def hash_data(
    data: Union[str, bytes],
    algorithm: str = "sha256",
    salt: Optional[bytes] = None,
) -> str:
    """
    Hash data using specified algorithm.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
        salt: Optional salt for salted hash
        
    Returns:
        Hex digest of hash
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    if salt:
        data = salt + data
    
    if algorithm == "md5":
        return hashlib.md5(data).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(data).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(data).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def verify_hash(data: Union[str, bytes], hash_value: str, salt: Optional[bytes] = None) -> bool:
    """Verify data against a hash."""
    computed_hash = hash_data(data, salt=salt)
    return secrets.compare_digest(computed_hash, hash_value)


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def generate_api_key() -> str:
    """Generate a new API key."""
    prefix = "woy_"
    random_part = secrets.token_urlsafe(24)
    return f"{prefix}{random_part}"


def mask_sensitive_data(data: str, visible_start: int = 2, visible_end: int = 2) -> str:
    """Mask sensitive data (e.g., credit card numbers, phone numbers)."""
    if not data:
        return ""
    
    if len(data) <= visible_start + visible_end:
        return "*" * len(data)
    
    return (
        data[:visible_start] +
        "*" * (len(data) - visible_start - visible_end) +
        data[-visible_end:]
    )


# Global encryption manager
encryption_manager = EncryptionManager()


__all__ = [
    "encrypt_data",
    "decrypt_data",
    "hash_data",
    "verify_hash",
    "generate_secure_token",
    "generate_api_key",
    "mask_sensitive_data",
    "EncryptionManager",
    "encryption_manager",
]