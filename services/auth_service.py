import requests
import os
from typing import Dict, Optional

class AuthService:
    """Service for communicating with the Auth Service"""
    
    def __init__(self):
        self.base_url = os.getenv('TELEGIVE_AUTH_URL', 'https://web-production-ddd7e.up.railway.app')
        self.service_name = os.getenv('SERVICE_NAME', 'participant-service')
        self.service_token = os.getenv('AUTH_SERVICE_TOKEN', 'ch4nn3l_s3rv1c3_t0k3n_2025_s3cur3_r4nd0m_str1ng')
    
    def get_service_headers(self) -> Dict[str, str]:
        """Get headers for inter-service communication with authentication"""
        return {
            'Content-Type': 'application/json',
            'X-Service-Name': self.service_name,
            'X-Service-Token': self.service_token,
            'User-Agent': f'{self.service_name}/1.0.0'
        }
    
    def get_bot_token(self, account_id: int) -> Optional[str]:
        """Get bot token for a specific account"""
        try:
            response = requests.get(
                f'{self.base_url}/api/auth/bot-token/{account_id}',
                headers=self.get_service_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('bot_token')
            
            return None
            
        except requests.RequestException as e:
            print(f"Error getting bot token from auth service: {e}")
            return None
    
    def verify_service_token(self, token: str) -> bool:
        """Verify a service token with the auth service"""
        try:
            response = requests.post(
                f'{self.base_url}/api/auth/verify-service-token',
                json={'token': token},
                headers=self.get_service_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('success', False)
            
            return False
            
        except requests.RequestException as e:
            print(f"Error verifying service token: {e}")
            return False
    
    def get_account_info(self, account_id: int) -> Optional[Dict]:
        """Get account information"""
        try:
            response = requests.get(
                f'{self.base_url}/api/auth/account/{account_id}',
                headers=self.get_service_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('account')
            
            return None
            
        except requests.RequestException as e:
            print(f"Error getting account info: {e}")
            return None

# Global instance
auth_service = AuthService()

