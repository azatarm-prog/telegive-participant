import requests
import os
from typing import Dict, Optional

class ChannelService:
    """Service for communicating with the Channel Service"""
    
    def __init__(self):
        self.base_url = os.getenv('TELEGIVE_CHANNEL_URL', 'https://telegive-channel.railway.app')
        self.service_name = os.getenv('SERVICE_NAME', 'participant-service')
    
    def get_service_headers(self) -> Dict[str, str]:
        """Get headers for inter-service communication"""
        return {
            'Content-Type': 'application/json',
            'X-Service-Name': self.service_name,
            'User-Agent': f'{self.service_name}/1.0.0'
        }
    
    def get_channel_info(self, account_id: int) -> Optional[Dict]:
        """Get channel information for an account"""
        try:
            response = requests.get(
                f'{self.base_url}/api/channels/account/{account_id}',
                headers=self.get_service_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('channel')
            
            return None
            
        except requests.RequestException as e:
            print(f"Error getting channel info from channel service: {e}")
            return None
    
    def get_channel_by_giveaway(self, giveaway_id: int) -> Optional[Dict]:
        """Get channel information for a specific giveaway"""
        try:
            response = requests.get(
                f'{self.base_url}/api/channels/giveaway/{giveaway_id}',
                headers=self.get_service_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('channel')
            
            return None
            
        except requests.RequestException as e:
            print(f"Error getting channel info for giveaway: {e}")
            return None
    
    def update_channel_stats(self, channel_id: int, stats: Dict) -> bool:
        """Update channel statistics"""
        try:
            response = requests.put(
                f'{self.base_url}/api/channels/{channel_id}/stats',
                json=stats,
                headers=self.get_service_headers(),
                timeout=10
            )
            
            return response.status_code == 200
            
        except requests.RequestException as e:
            print(f"Error updating channel stats: {e}")
            return False

# Global instance
channel_service = ChannelService()

