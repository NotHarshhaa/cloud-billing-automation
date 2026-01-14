"""
Encryption utilities for secure data handling.
"""

import os
import secrets
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from ..core.exceptions import CloudBillingError


class EncryptionUtils:
    """Utilities for secure data encryption and decryption."""
    
    def __init__(self, key_file: Optional[Path] = None):
        self.key_file = key_file or Path.home() / ".cba" / "encryption.key"
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self._encryption_key = None
        self._fernet = None
    
    def get_or_create_key(self) -> bytes:
        """Get or create encryption key."""
        if self.key_file.exists():
            # Load existing key
            try:
                with open(self.key_file, 'rb') as f:
                    key_data = f.read()
                
                # Verify key is valid Fernet key
                try:
                    Fernet(key_data)
                    return key_data
                except Exception:
                    # Key is invalid, create new one
                    return self._create_new_key()
                    
            except Exception as e:
                raise CloudBillingError(f"Failed to load encryption key: {e}")
        else:
            return self._create_new_key()
    
    def _create_new_key(self) -> bytes:
        """Create a new encryption key."""
        key = Fernet.generate_key()
        
        try:
            # Set restrictive permissions
            os.chmod(self.key_file, 0o600)
            
            # Write key to file
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            return key
            
        except Exception as e:
            raise CloudBillingError(f"Failed to create encryption key: {e}")
    
    def get_fernet(self) -> Fernet:
        """Get Fernet cipher instance."""
        if self._fernet is None:
            key = self.get_or_create_key()
            self._fernet = Fernet(key)
        
        return self._fernet
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt string data."""
        try:
            fernet = self.get_fernet()
            encrypted_data = fernet.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            raise CloudBillingError(f"Failed to encrypt data: {e}")
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        try:
            fernet = self.get_fernet()
            decrypted_data = fernet.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            raise CloudBillingError(f"Failed to decrypt data: {e}")
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary data."""
        import json
        json_data = json.dumps(data, separators=(',', ':'))
        return self.encrypt_data(json_data)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt dictionary data."""
        import json
        json_data = self.decrypt_data(encrypted_data)
        return json.loads(json_data)
    
    def encrypt_file(self, file_path: Path, output_path: Optional[Path] = None) -> Path:
        """Encrypt a file."""
        if not file_path.exists():
            raise CloudBillingError(f"File not found: {file_path}")
        
        if output_path is None:
            output_path = file_path.with_suffix(file_path.suffix + '.enc')
        
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Encrypt data
            fernet = self.get_fernet()
            encrypted_data = fernet.encrypt(file_data)
            
            # Write encrypted file
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            os.chmod(output_path, 0o600)
            
            return output_path
            
        except Exception as e:
            raise CloudBillingError(f"Failed to encrypt file {file_path}: {e}")
    
    def decrypt_file(self, encrypted_path: Path, output_path: Optional[Path] = None) -> Path:
        """Decrypt a file."""
        if not encrypted_path.exists():
            raise CloudBillingError(f"Encrypted file not found: {encrypted_path}")
        
        if output_path is None:
            if encrypted_path.suffix == '.enc':
                output_path = encrypted_path.with_suffix(encrypted_path.suffix[:-4])
            else:
                output_path = encrypted_path.with_suffix('.dec')
        
        try:
            # Read encrypted file
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt data
            fernet = self.get_fernet()
            decrypted_data = fernet.decrypt(encrypted_data)
            
            # Write decrypted file
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            return output_path
            
        except Exception as e:
            raise CloudBillingError(f"Failed to decrypt file {encrypted_path}: {e}")
    
    def hash_data(self, data: str, algorithm: str = 'sha256') -> str:
        """Hash data using specified algorithm."""
        try:
            if algorithm.lower() == 'sha256':
                hasher = hashlib.sha256()
            elif algorithm.lower() == 'sha512':
                hasher = hashlib.sha512()
            elif algorithm.lower() == 'md5':
                hasher = hashlib.md5()
            else:
                raise CloudBillingError(f"Unsupported hash algorithm: {algorithm}")
            
            hasher.update(data.encode())
            return hasher.hexdigest()
            
        except Exception as e:
            raise CloudBillingError(f"Failed to hash data: {e}")
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)
    
    def generate_api_key(self, prefix: str = "cba") -> str:
        """Generate an API key with prefix."""
        token = secrets.token_urlsafe(32)
        return f"{prefix}_{token}"
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None,
                                iterations: int = 100000) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        
        return kdf.derive(password.encode())
    
    def encrypt_with_password(self, data: str, password: str, 
                             salt: Optional[bytes] = None) -> tuple[str, bytes]:
        """Encrypt data with password-derived key."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        key = self.derive_key_from_password(password, salt)
        
        try:
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data.encode())
            return encrypted_data.decode(), salt
            
        except Exception as e:
            raise CloudBillingError(f"Failed to encrypt with password: {e}")
    
    def decrypt_with_password(self, encrypted_data: str, password: str, salt: bytes) -> str:
        """Decrypt data with password-derived key."""
        key = self.derive_key_from_password(password, salt)
        
        try:
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
            
        except Exception as e:
            raise CloudBillingError(f"Failed to decrypt with password: {e}")
    
    def secure_delete_file(self, file_path: Path, passes: int = 3) -> None:
        """Securely delete a file by overwriting it multiple times."""
        if not file_path.exists():
            return
        
        try:
            file_size = file_path.stat().st_size
            
            # Overwrite file with random data multiple times
            with open(file_path, 'wb') as f:
                for _ in range(passes):
                    random_data = secrets.token_bytes(file_size)
                    f.write(random_data)
                    f.seek(0)
            
            # Delete the file
            file_path.unlink()
            
        except Exception as e:
            raise CloudBillingError(f"Failed to securely delete file {file_path}: {e}")
    
    def verify_file_integrity(self, file_path: Path, expected_hash: str) -> bool:
        """Verify file integrity using hash."""
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            file_hash = self.hash_data(file_data.decode('utf-8', errors='ignore'))
            return file_hash == expected_hash
            
        except Exception:
            return False
    
    def create_file_hash(self, file_path: Path) -> str:
        """Create hash for file integrity verification."""
        if not file_path.exists():
            raise CloudBillingError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            return self.hash_data(file_data.decode('utf-8', errors='ignore'))
            
        except Exception as e:
            raise CloudBillingError(f"Failed to create file hash: {e}")
    
    def encrypt_sensitive_dict(self, data: Dict[str, Any], 
                             sensitive_keys: List[str]) -> Dict[str, Any]:
        """Encrypt sensitive fields in a dictionary."""
        encrypted_data = data.copy()
        
        for key in sensitive_keys:
            if key in encrypted_data and isinstance(encrypted_data[key], str):
                try:
                    encrypted_data[key] = self.encrypt_data(encrypted_data[key])
                except Exception:
                    # If encryption fails, leave original value
                    pass
        
        return encrypted_data
    
    def decrypt_sensitive_dict(self, data: Dict[str, Any], 
                             sensitive_keys: List[str]) -> Dict[str, Any]:
        """Decrypt sensitive fields in a dictionary."""
        decrypted_data = data.copy()
        
        for key in sensitive_keys:
            if key in decrypted_data and isinstance(decrypted_data[key], str):
                try:
                    decrypted_data[key] = self.decrypt_data(decrypted_data[key])
                except Exception:
                    # If decryption fails, leave original value
                    pass
        
        return decrypted_data
    
    def rotate_encryption_key(self) -> str:
        """Rotate encryption key and return new key info."""
        try:
            # Backup old key file
            if self.key_file.exists():
                backup_path = self.key_file.with_suffix('.backup')
                self.key_file.rename(backup_path)
            
            # Create new key
            new_key = self._create_new_key()
            
            return f"New encryption key created. Backup saved to {backup_path if 'backup_path' in locals() else 'No backup created'}"
            
        except Exception as e:
            raise CloudBillingError(f"Failed to rotate encryption key: {e}")
    
    def get_key_info(self) -> Dict[str, Any]:
        """Get information about the encryption key."""
        try:
            if self.key_file.exists():
                stat = self.key_file.stat()
                return {
                    'key_file': str(self.key_file),
                    'exists': True,
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'permissions': oct(stat.st_mode)[-3:]
                }
            else:
                return {
                    'key_file': str(self.key_file),
                    'exists': False
                }
                
        except Exception as e:
            raise CloudBillingError(f"Failed to get key info: {e}")
