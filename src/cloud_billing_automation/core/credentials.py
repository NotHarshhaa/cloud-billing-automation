"""
Secure credential management for cloud billing automation.
"""

import os
import keyring
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from .exceptions import CredentialError


class CredentialManager:
    """Manages secure storage and retrieval of cloud credentials."""
    
    def __init__(self, service_name: str = "cloud-billing-automation"):
        self.service_name = service_name
        self._encryption_key = None
    
    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for credential storage."""
        if self._encryption_key is None:
            key_path = Path.home() / ".cba" / "encryption.key"
            key_path.parent.mkdir(exist_ok=True)
            
            if key_path.exists():
                with open(key_path, 'rb') as f:
                    self._encryption_key = f.read()
            else:
                self._encryption_key = Fernet.generate_key()
                with open(key_path, 'wb') as f:
                    f.write(self._encryption_key)
                # Set restrictive permissions
                os.chmod(key_path, 0o600)
        
        return self._encryption_key
    
    def _encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential for storage."""
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(credential.encode())
        return encrypted.decode()
    
    def _decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a stored credential."""
        key = self._get_encryption_key()
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_credential.encode())
        return decrypted.decode()
    
    def store_credential(self, provider: str, credential_type: str, value: str) -> None:
        """Store a credential securely."""
        try:
            key = f"{provider}_{credential_type}"
            encrypted_value = self._encrypt_credential(value)
            keyring.set_password(self.service_name, key, encrypted_value)
        except Exception as e:
            raise CredentialError(f"Failed to store credential for {provider}: {e}")
    
    def get_credential(self, provider: str, credential_type: str) -> Optional[str]:
        """Retrieve a stored credential."""
        try:
            key = f"{provider}_{credential_type}"
            encrypted_value = keyring.get_password(self.service_name, key)
            if encrypted_value:
                return self._decrypt_credential(encrypted_value)
            return None
        except Exception as e:
            raise CredentialError(f"Failed to retrieve credential for {provider}: {e}")
    
    def delete_credential(self, provider: str, credential_type: str) -> None:
        """Delete a stored credential."""
        try:
            key = f"{provider}_{credential_type}"
            keyring.delete_password(self.service_name, key)
        except Exception as e:
            raise CredentialError(f"Failed to delete credential for {provider}: {e}")
    
    def list_credentials(self) -> Dict[str, Dict[str, str]]:
        """List all stored credentials (without values)."""
        credentials = {}
        
        # This is a simplified implementation
        # In practice, you'd need to use keyring-specific methods to list keys
        # or maintain a separate index of stored credentials
        
        providers = ["aws", "azure", "gcp"]
        credential_types = ["access_key", "secret_key", "subscription_id", "service_account_key"]
        
        for provider in providers:
            credentials[provider] = {}
            for cred_type in credential_types:
                key = f"{provider}_{cred_type}"
                if keyring.get_password(self.service_name, key):
                    credentials[provider][cred_type] = "stored"
        
        return credentials
    
    def setup_aws_credentials(self, access_key_id: str, secret_access_key: str, 
                             session_token: Optional[str] = None) -> None:
        """Setup AWS credentials."""
        self.store_credential("aws", "access_key_id", access_key_id)
        self.store_credential("aws", "secret_access_key", secret_access_key)
        if session_token:
            self.store_credential("aws", "session_token", session_token)
    
    def setup_azure_credentials(self, tenant_id: str, client_id: str, 
                              client_secret: str, subscription_id: str) -> None:
        """Setup Azure service principal credentials."""
        self.store_credential("azure", "tenant_id", tenant_id)
        self.store_credential("azure", "client_id", client_id)
        self.store_credential("azure", "client_secret", client_secret)
        self.store_credential("azure", "subscription_id", subscription_id)
    
    def setup_gcp_credentials(self, service_account_key: str) -> None:
        """Setup GCP service account credentials."""
        self.store_credential("gcp", "service_account_key", service_account_key)
    
    def get_aws_credentials(self) -> Dict[str, str]:
        """Get AWS credentials."""
        credentials = {}
        
        access_key = self.get_credential("aws", "access_key_id")
        secret_key = self.get_credential("aws", "secret_access_key")
        session_token = self.get_credential("aws", "session_token")
        
        if access_key:
            credentials["access_key_id"] = access_key
        if secret_key:
            credentials["secret_access_key"] = secret_key
        if session_token:
            credentials["session_token"] = session_token
        
        return credentials
    
    def get_azure_credentials(self) -> Dict[str, str]:
        """Get Azure credentials."""
        credentials = {}
        
        tenant_id = self.get_credential("azure", "tenant_id")
        client_id = self.get_credential("azure", "client_id")
        client_secret = self.get_credential("azure", "client_secret")
        subscription_id = self.get_credential("azure", "subscription_id")
        
        if tenant_id:
            credentials["tenant_id"] = tenant_id
        if client_id:
            credentials["client_id"] = client_id
        if client_secret:
            credentials["client_secret"] = client_secret
        if subscription_id:
            credentials["subscription_id"] = subscription_id
        
        return credentials
    
    def get_gcp_credentials(self) -> Dict[str, str]:
        """Get GCP credentials."""
        credentials = {}
        
        service_account_key = self.get_credential("gcp", "service_account_key")
        if service_account_key:
            credentials["service_account_key"] = service_account_key
        
        return credentials
    
    def validate_credentials(self, provider: str) -> bool:
        """Validate that required credentials are stored for a provider."""
        if provider == "aws":
            access_key = self.get_credential("aws", "access_key_id")
            secret_key = self.get_credential("aws", "secret_access_key")
            return bool(access_key and secret_key)
        
        elif provider == "azure":
            tenant_id = self.get_credential("azure", "tenant_id")
            client_id = self.get_credential("azure", "client_id")
            client_secret = self.get_credential("azure", "client_secret")
            subscription_id = self.get_credential("azure", "subscription_id")
            return bool(tenant_id and client_id and client_secret and subscription_id)
        
        elif provider == "gcp":
            service_account_key = self.get_credential("gcp", "service_account_key")
            return bool(service_account_key)
        
        return False
    
    def clear_all_credentials(self) -> None:
        """Clear all stored credentials."""
        providers = ["aws", "azure", "gcp"]
        credential_types = [
            "access_key_id", "secret_access_key", "session_token",
            "tenant_id", "client_id", "client_secret", "subscription_id",
            "service_account_key"
        ]
        
        for provider in providers:
            for cred_type in credential_types:
                try:
                    self.delete_credential(provider, cred_type)
                except:
                    pass  # Ignore if credential doesn't exist
