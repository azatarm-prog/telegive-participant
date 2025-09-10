import requests
import os
from typing import Dict, Optional

class TelegramAPI:
    """Service for interacting with Telegram Bot API"""
    
    def __init__(self):
        self.api_base = os.getenv('TELEGRAM_API_BASE', 'https://api.telegram.org')
    
    def check_channel_membership(self, bot_token: str, channel_id: int, user_id: int) -> Dict:
        """
        Check if a user is a member of a channel
        
        Args:
            bot_token: Bot token for API authentication
            channel_id: Channel ID (negative for channels)
            user_id: User ID to check
            
        Returns:
            Dict with success status and membership info
        """
        try:
            url = f"{self.api_base}/bot{bot_token}/getChatMember"
            params = {
                'chat_id': channel_id,
                'user_id': user_id
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('ok'):
                    member_info = data.get('result', {})
                    status = member_info.get('status', 'left')
                    
                    # Member statuses that count as subscribed
                    subscribed_statuses = ['member', 'administrator', 'creator']
                    is_member = status in subscribed_statuses
                    
                    return {
                        'success': True,
                        'is_member': is_member,
                        'status': status,
                        'member_info': member_info
                    }
                else:
                    error_description = data.get('description', 'Unknown error')
                    return {
                        'success': False,
                        'error': f"Telegram API error: {error_description}",
                        'is_member': False
                    }
            else:
                return {
                    'success': False,
                    'error': f"HTTP error: {response.status_code}",
                    'is_member': False
                }
                
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f"Request error: {str(e)}",
                'is_member': False
            }
    
    def get_chat_info(self, bot_token: str, chat_id: int) -> Optional[Dict]:
        """Get information about a chat/channel"""
        try:
            url = f"{self.api_base}/bot{bot_token}/getChat"
            params = {'chat_id': chat_id}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result')
            
            return None
            
        except requests.RequestException as e:
            print(f"Error getting chat info: {e}")
            return None
    
    def get_chat_member_count(self, bot_token: str, chat_id: int) -> Optional[int]:
        """Get the number of members in a chat/channel"""
        try:
            url = f"{self.api_base}/bot{bot_token}/getChatMemberCount"
            params = {'chat_id': chat_id}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result')
            
            return None
            
        except requests.RequestException as e:
            print(f"Error getting chat member count: {e}")
            return None

# Global instance
telegram_api = TelegramAPI()

# Convenience function for backward compatibility
def check_channel_membership(bot_token: str, channel_id: int, user_id: int) -> Dict:
    """Check if a user is a member of a channel"""
    return telegram_api.check_channel_membership(bot_token, channel_id, user_id)

