#!/usr/bin/env python3
"""
QENEX Authentication System - User management and API authentication
"""

import hashlib
import secrets
import jwt
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
from functools import wraps
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthenticationManager:
    def __init__(self, db_path="/opt/qenex-os/data/qenex.db", secret_key=None):
        self.db_path = db_path
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.jwt_algorithm = 'HS256'
        self.token_expiry_hours = 24
        self.api_key_length = 32
        
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        return f"qnx_{secrets.token_urlsafe(self.api_key_length)}"
    
    def generate_jwt_token(self, user_id: int, username: str, role: str) -> str:
        """Generate JWT token for user"""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.jwt_algorithm)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def create_user(self, username: str, password: str, email: str = None, 
                   role: str = 'user') -> Dict[str, Any]:
        """Create a new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            password_hash = self.hash_password(password)
            api_key = self.generate_api_key()
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, api_key, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, api_key, role))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Created user: {username} with role: {role}")
            
            return {
                'user_id': user_id,
                'username': username,
                'api_key': api_key,
                'role': role
            }
            
        except sqlite3.IntegrityError:
            logger.error(f"User {username} already exists")
            return None
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, password_hash, role, is_active, api_key
            FROM users
            WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        
        if user and user[3]:  # is_active
            user_id, password_hash, role, _, api_key = user
            
            if self.verify_password(password, password_hash):
                # Update last login
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                
                token = self.generate_jwt_token(user_id, username, role)
                
                conn.close()
                return {
                    'user_id': user_id,
                    'username': username,
                    'role': role,
                    'token': token,
                    'api_key': api_key
                }
        
        conn.close()
        return None
    
    def authenticate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Authenticate with API key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, role, is_active
            FROM users
            WHERE api_key = ?
        ''', (api_key,))
        
        user = cursor.fetchone()
        
        if user and user[3]:  # is_active
            user_id, username, role, _ = user
            
            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            
            conn.close()
            return {
                'user_id': user_id,
                'username': username,
                'role': role
            }
        
        conn.close()
        return None
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change user password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result and self.verify_password(old_password, result[0]):
            new_hash = self.hash_password(new_password)
            cursor.execute('''
                UPDATE users SET password_hash = ?
                WHERE id = ?
            ''', (new_hash, user_id))
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def regenerate_api_key(self, user_id: int) -> str:
        """Regenerate API key for user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        new_key = self.generate_api_key()
        cursor.execute('''
            UPDATE users SET api_key = ?
            WHERE id = ?
        ''', (new_key, user_id))
        
        conn.commit()
        conn.close()
        
        return new_key
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user details"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, role, created_at, last_login, is_active
            FROM users
            WHERE id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'user_id': user[0],
                'username': user[1],
                'email': user[2],
                'role': user[3],
                'created_at': user[4],
                'last_login': user[5],
                'is_active': user[6]
            }
        
        return None
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, role, created_at, last_login, is_active
            FROM users
            ORDER BY created_at DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'user_id': row[0],
                'username': row[1],
                'email': row[2],
                'role': row[3],
                'created_at': row[4],
                'last_login': row[5],
                'is_active': row[6]
            })
        
        conn.close()
        return users
    
    def deactivate_user(self, user_id: int):
        """Deactivate a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET is_active = 0
            WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def check_permission(self, user_role: str, required_role: str) -> bool:
        """Check if user has required permission"""
        role_hierarchy = {
            'admin': 3,
            'operator': 2,
            'user': 1,
            'viewer': 0
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level

# Decorators for route protection
def require_auth(required_role='user'):
    """Decorator to require authentication"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: web.Request, *args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            api_key = request.headers.get('X-API-Key', '')
            
            auth_manager = request.app.get('auth_manager')
            if not auth_manager:
                return web.json_response({'error': 'Authentication not configured'}, status=500)
            
            user = None
            
            # Try JWT token
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                user = auth_manager.verify_jwt_token(token)
            
            # Try API key
            elif api_key:
                user = auth_manager.authenticate_api_key(api_key)
            
            if not user:
                return web.json_response({'error': 'Unauthorized'}, status=401)
            
            # Check role permission
            if not auth_manager.check_permission(user.get('role'), required_role):
                return web.json_response({'error': 'Insufficient permissions'}, status=403)
            
            # Add user to request
            request['user'] = user
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

# Authentication routes
class AuthRoutes:
    def __init__(self, auth_manager: AuthenticationManager):
        self.auth = auth_manager
    
    async def register(self, request: web.Request) -> web.Response:
        """Register a new user"""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            
            if not username or not password:
                return web.json_response({'error': 'Username and password required'}, status=400)
            
            user = self.auth.create_user(username, password, email)
            if user:
                return web.json_response({
                    'message': 'User created successfully',
                    'user_id': user['user_id'],
                    'api_key': user['api_key']
                })
            else:
                return web.json_response({'error': 'User already exists'}, status=409)
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def login(self, request: web.Request) -> web.Response:
        """Login user"""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return web.json_response({'error': 'Username and password required'}, status=400)
            
            user = self.auth.authenticate_user(username, password)
            if user:
                return web.json_response({
                    'message': 'Login successful',
                    'token': user['token'],
                    'api_key': user['api_key'],
                    'user': {
                        'id': user['user_id'],
                        'username': user['username'],
                        'role': user['role']
                    }
                })
            else:
                return web.json_response({'error': 'Invalid credentials'}, status=401)
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    @require_auth()
    async def profile(self, request: web.Request) -> web.Response:
        """Get user profile"""
        user_id = request['user']['user_id']
        user = self.auth.get_user(user_id)
        
        if user:
            return web.json_response(user)
        else:
            return web.json_response({'error': 'User not found'}, status=404)
    
    @require_auth()
    async def change_password(self, request: web.Request) -> web.Response:
        """Change password"""
        try:
            data = await request.json()
            old_password = data.get('old_password')
            new_password = data.get('new_password')
            
            if not old_password or not new_password:
                return web.json_response({'error': 'Both passwords required'}, status=400)
            
            user_id = request['user']['user_id']
            if self.auth.change_password(user_id, old_password, new_password):
                return web.json_response({'message': 'Password changed successfully'})
            else:
                return web.json_response({'error': 'Invalid old password'}, status=400)
                
        except Exception as e:
            logger.error(f"Password change error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    @require_auth()
    async def regenerate_key(self, request: web.Request) -> web.Response:
        """Regenerate API key"""
        user_id = request['user']['user_id']
        new_key = self.auth.regenerate_api_key(user_id)
        
        return web.json_response({
            'message': 'API key regenerated',
            'api_key': new_key
        })
    
    @require_auth('admin')
    async def list_users(self, request: web.Request) -> web.Response:
        """List all users (admin only)"""
        users = self.auth.list_users()
        return web.json_response({'users': users})

from typing import List

# Initialize default admin user
def init_default_admin(auth_manager: AuthenticationManager):
    """Create default admin user if none exists"""
    conn = sqlite3.connect(auth_manager.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = cursor.fetchone()[0]
    
    if admin_count == 0:
        admin = auth_manager.create_user(
            username='admin',
            password='QenexAdmin2024!',  # Change this immediately!
            email='admin@qenex.local',
            role='admin'
        )
        
        if admin:
            logger.info(f"Created default admin user. API Key: {admin['api_key']}")
            logger.warning("IMPORTANT: Change the default admin password immediately!")
    
    conn.close()

if __name__ == "__main__":
    # Test authentication system
    auth = AuthenticationManager()
    init_default_admin(auth)
    
    # Create test user
    user = auth.create_user('testuser', 'testpass123', 'test@example.com')
    if user:
        print(f"Created user: {user}")
        
        # Test login
        login = auth.authenticate_user('testuser', 'testpass123')
        print(f"Login result: {login}")
        
        # Test API key auth
        api_auth = auth.authenticate_api_key(user['api_key'])
        print(f"API key auth: {api_auth}")