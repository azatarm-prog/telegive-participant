import requests
import os
from typing import Dict, Optional

class TelegiveService:
    """Service for communicating with the main Giveaway Service"""
    
    def __init__(self):
        self.base_url = os.getenv('TELEGIVE_GIVEAWAY_URL', 'https://telegive-service.railway.app')
        self.service_name = os.getenv('SERVICE_NAME', 'participant-service')
    
    def get_service_headers(self) -> Dict[str, str]:
        """Get headers for inter-service communication"""
        return {
            'Content-Type': 'application/json',
            'X-Service-Name': self.service_name,
            'User-Agent': f'{self.service_name}/1.0.0'
        }
    
    def get_giveaway(self, giveaway_id: int) -> Optional[Dict]:
        """Get giveaway information"""
        try:
            response = requests.get(
                f'{self.base_url}/api/giveaways/{giveaway_id}',
                headers=self.get_service_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('giveaway')
            
            return None
            
        except requests.RequestException as e:
            print(f"Error getting giveaway from telegive service: {e}")
            return None
    
    def update_giveaway_stats(self, giveaway_id: int, stats: Dict) -> bool:
        """Update giveaway statistics"""
        try:
            response = requests.put(
                f'{self.base_url}/api/giveaways/{giveaway_id}/stats',
                json=stats,
                headers=self.get_service_headers(),
                timeout=10
            )
            
            return response.status_code == 200
            
        except requests.RequestException as e:
            print(f"Error updating giveaway stats: {e}")
            return False
    
    def notify_winners_selected(self, giveaway_id: int, winners: list) -> bool:
        """Notify the giveaway service that winners have been selected"""
        try:
            response = requests.post(
                f'{self.base_url}/api/giveaways/{giveaway_id}/winners-selected',
                json={'winners': winners},
                headers=self.get_service_headers(),
                timeout=10
            )
            
            return response.status_code == 200
            
        except requests.RequestException as e:
            print(f"Error notifying winners selected: {e}")
            return False
    
    def get_giveaway_status(self, giveaway_id: int) -> Optional[str]:
        """Get the current status of a giveaway"""
        giveaway = self.get_giveaway(giveaway_id)
        if giveaway:
            return giveaway.get('status')
        return None
    
    def is_giveaway_active(self, giveaway_id: int) -> bool:
        """Check if a giveaway is currently active"""
        status = self.get_giveaway_status(giveaway_id)
        return status == 'active'

# Global instance
telegive_service = TelegiveService()

