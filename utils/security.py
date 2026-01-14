"""
Security utilities for IAM and access control.
"""

import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..core.exceptions import CloudBillingError


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_symbols: bool = True
    session_timeout_minutes: int = 60
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    require_mfa: bool = False
    allowed_ip_ranges: List[str] = None
    audit_log_retention_days: int = 90


@dataclass
class UserSession:
    """User session information."""
    user_id: str
    username: str
    roles: List[str]
    permissions: Set[str]
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    ip_address: str
    user_agent: str
    session_token: str


@dataclass
class AuditLog:
    """Audit log entry."""
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    result: str  # "success", "failure", "denied"
    details: Dict[str, Any]
    ip_address: str
    user_agent: str


class SecurityUtils:
    """Security utilities for IAM and access control."""
    
    def __init__(self, config: Any, policy: Optional[SecurityPolicy] = None):
        self.config = config
        self.policy = policy or SecurityPolicy()
        self.active_sessions: Dict[str, UserSession] = {}
        self.failed_attempts: Dict[str, int] = {}
        self.locked_accounts: Dict[str, datetime] = {}
        self.audit_logs: List[AuditLog] = []
        self.encryption_key = self._generate_encryption_key()
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
        """Hash password using PBKDF2."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        password_hash = kdf.derive(password.encode())
        
        return password_hash.hex(), salt
    
    def verify_password(self, password: str, stored_hash: str, salt: bytes) -> bool:
        """Verify password against stored hash."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        try:
            kdf.verify(password.encode(), bytes.fromhex(stored_hash))
            return True
        except Exception:
            return False
    
    def validate_password_strength(self, password: str) -> tuple[bool, List[str]]:
        """Validate password strength against policy."""
        errors = []
        
        if len(password) < self.policy.password_min_length:
            errors.append(f"Password must be at least {self.policy.password_min_length} characters long")
        
        if self.policy.password_require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.policy.password_require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.policy.password_require_numbers and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if self.policy.password_require_symbols and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    def generate_session_token(self, user_id: str, username: str, 
                             roles: List[str], ip_address: str, 
                             user_agent: str) -> str:
        """Generate a secure session token."""
        # Create session
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=self.policy.session_timeout_minutes)
        
        # Calculate permissions from roles
        permissions = self._get_permissions_for_roles(roles)
        
        session = UserSession(
            user_id=user_id,
            username=username,
            roles=roles,
            permissions=permissions,
            created_at=datetime.now(),
            expires_at=expires_at,
            last_accessed=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            session_token=session_id
        )
        
        # Store session
        self.active_sessions[session_id] = session
        
        # Create JWT token
        payload = {
            'session_id': session_id,
            'user_id': user_id,
            'username': username,
            'roles': roles,
            'exp': expires_at.timestamp(),
            'iat': datetime.now().timestamp()
        }
        
        token = jwt.encode(payload, self.encryption_key, algorithm='HS256')
        
        # Log session creation
        self._log_audit_event(
            user_id=user_id,
            action="session_created",
            resource="session",
            result="success",
            details={'session_id': session_id, 'ip_address': ip_address},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return token
    
    def validate_session_token(self, token: str, ip_address: str, 
                              user_agent: str) -> Optional[UserSession]:
        """Validate session token and return session."""
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.encryption_key, algorithms=['HS256'])
            session_id = payload.get('session_id')
            
            if not session_id:
                return None
            
            # Check if session exists
            session = self.active_sessions.get(session_id)
            if not session:
                return None
            
            # Check if session is expired
            if datetime.now() > session.expires_at:
                self._cleanup_session(session_id)
                return None
            
            # Check IP address if policy requires it
            if self.policy.allowed_ip_ranges:
                if not self._is_ip_allowed(ip_address):
                    self._log_audit_event(
                        user_id=session.user_id,
                        action="session_denied",
                        resource="session",
                        result="denied",
                        details={'reason': 'ip_not_allowed', 'ip_address': ip_address},
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    return None
            
            # Update last accessed
            session.last_accessed = datetime.now()
            
            return session
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            raise CloudBillingError(f"Session validation error: {e}")
    
    def check_permission(self, session: UserSession, permission: str) -> bool:
        """Check if session has required permission."""
        return permission in session.permissions
    
    def check_role(self, session: UserSession, role: str) -> bool:
        """Check if session has required role."""
        return role in session.roles
    
    def revoke_session(self, session_id: str, reason: str = "manual_revocation") -> bool:
        """Revoke a session."""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # Log session revocation
        self._log_audit_event(
            user_id=session.user_id,
            action="session_revoked",
            resource="session",
            result="success",
            details={'session_id': session_id, 'reason': reason},
            ip_address=session.ip_address,
            user_agent=session.user_agent
        )
        
        # Remove session
        del self.active_sessions[session_id]
        return True
    
    def revoke_all_user_sessions(self, user_id: str, reason: str = "user_logout") -> int:
        """Revoke all sessions for a user."""
        revoked_count = 0
        
        sessions_to_remove = []
        for session_id, session in self.active_sessions.items():
            if session.user_id == user_id:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            if self.revoke_session(session_id, reason):
                revoked_count += 1
        
        return revoked_count
    
    def handle_failed_login(self, username: str, ip_address: str, 
                           user_agent: str) -> tuple[bool, str]:
        """Handle failed login attempt."""
        # Check if account is locked
        if username in self.locked_accounts:
            lockout_time = self.locked_accounts[username]
            if datetime.now() < lockout_time:
                remaining_minutes = int((lockout_time - datetime.now()).total_seconds() / 60)
                return False, f"Account locked. Try again in {remaining_minutes} minutes."
            else:
                # Lockout expired, remove it
                del self.locked_accounts[username]
        
        # Increment failed attempts
        self.failed_attempts[username] = self.failed_attempts.get(username, 0) + 1
        
        # Check if should lock account
        if self.failed_attempts[username] >= self.policy.max_login_attempts:
            lockout_time = datetime.now() + timedelta(minutes=self.policy.lockout_duration_minutes)
            self.locked_accounts[username] = lockout_time
            
            # Log lockout
            self._log_audit_event(
                user_id=username,
                action="account_locked",
                resource="account",
                result="failure",
                details={
                    'failed_attempts': self.failed_attempts[username],
                    'lockout_duration': self.policy.lockout_duration_minutes
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return False, f"Account locked due to too many failed attempts. Try again in {self.policy.lockout_duration_minutes} minutes."
        
        return False, f"Invalid credentials. {self.policy.max_login_attempts - self.failed_attempts[username]} attempts remaining."
    
    def handle_successful_login(self, username: str, user_id: str, ip_address: str, 
                               user_agent: str) -> None:
        """Handle successful login."""
        # Reset failed attempts
        if username in self.failed_attempts:
            del self.failed_attempts[username]
        
        # Remove from locked accounts if present
        if username in self.locked_accounts:
            del self.locked_accounts[username]
        
        # Log successful login
        self._log_audit_event(
            user_id=user_id,
            action="login_success",
            resource="account",
            result="success",
            details={'username': username},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def _get_permissions_for_roles(self, roles: List[str]) -> Set[str]:
        """Get permissions for a list of roles."""
        permissions = set()
        
        # Define role-based permissions
        role_permissions = {
            'admin': {
                'read:all', 'write:all', 'delete:all', 'manage:users',
                'manage:credentials', 'manage:config', 'manage:alerts',
                'manage:reports', 'system:admin'
            },
            'operator': {
                'read:all', 'write:costs', 'write:alerts', 'manage:alerts',
                'manage:reports', 'read:credentials'
            },
            'viewer': {
                'read:all', 'read:costs', 'read:alerts', 'read:reports'
            },
            'billing_manager': {
                'read:all', 'write:costs', 'write:budget', 'manage:alerts',
                'manage:reports', 'read:credentials'
            },
            'devops': {
                'read:all', 'write:costs', 'write:alerts', 'manage:alerts',
                'manage:credentials', 'read:config'
            }
        }
        
        for role in roles:
            if role in role_permissions:
                permissions.update(role_permissions[role])
        
        return permissions
    
    def _is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is in allowed ranges."""
        if not self.policy.allowed_ip_ranges:
            return True
        
        import ipaddress
        
        try:
            ip = ipaddress.ip_address(ip_address)
            
            for allowed_range in self.policy.allowed_ip_ranges:
                if '/' in allowed_range:
                    network = ipaddress.ip_network(allowed_range)
                    if ip in network:
                        return True
                else:
                    if ip == ipaddress.ip_address(allowed_range):
                        return True
            
            return False
            
        except ValueError:
            return False
    
    def _log_audit_event(self, user_id: str, action: str, resource: str, 
                         result: str, details: Dict[str, Any], 
                         ip_address: str, user_agent: str) -> None:
        """Log an audit event."""
        audit_log = AuditLog(
            timestamp=datetime.now(),
            user_id=user_id,
            action=action,
            resource=resource,
            result=result,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.audit_logs.append(audit_log)
        
        # Cleanup old audit logs
        self._cleanup_audit_logs()
    
    def _cleanup_audit_logs(self) -> None:
        """Remove old audit logs based on retention policy."""
        cutoff_date = datetime.now() - timedelta(days=self.policy.audit_log_retention_days)
        
        self.audit_logs = [
            log for log in self.audit_logs 
            if log.timestamp >= cutoff_date
        ]
    
    def _cleanup_session(self, session_id: str) -> None:
        """Clean up expired session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Log session expiration
            self._log_audit_event(
                user_id=session.user_id,
                action="session_expired",
                resource="session",
                result="success",
                details={'session_id': session_id},
                ip_address=session.ip_address,
                user_agent=session.user_agent
            )
            
            del self.active_sessions[session_id]
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key for JWT tokens."""
        return Fernet.generate_key().decode()
    
    def get_active_sessions(self) -> List[UserSession]:
        """Get all active sessions."""
        # Clean up expired sessions first
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if datetime.now() > session.expires_at:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self._cleanup_session(session_id)
        
        return list(self.active_sessions.values())
    
    def get_audit_logs(self, days: int = 30, user_id: Optional[str] = None,
                      action: Optional[str] = None) -> List[AuditLog]:
        """Get audit logs with optional filtering."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        logs = [
            log for log in self.audit_logs 
            if log.timestamp >= cutoff_date
        ]
        
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        
        if action:
            logs = [log for log in logs if log.action == action]
        
        return logs
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics for monitoring."""
        active_sessions = self.get_active_sessions()
        
        return {
            'active_sessions': len(active_sessions),
            'locked_accounts': len(self.locked_accounts),
            'failed_attempts': dict(self.failed_attempts),
            'total_audit_logs': len(self.audit_logs),
            'recent_logins': len([log for log in self.audit_logs 
                                 if log.action in ['login_success', 'account_locked']
                                 and log.timestamp >= datetime.now() - timedelta(hours=24)]),
            'policy': {
                'session_timeout_minutes': self.policy.session_timeout_minutes,
                'max_login_attempts': self.policy.max_login_attempts,
                'lockout_duration_minutes': self.policy.lockout_duration_minutes,
                'require_mfa': self.policy.require_mfa
            }
        }
