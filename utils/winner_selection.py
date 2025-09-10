import secrets
import os
import hashlib
from typing import List, Dict, Any
from datetime import datetime

class WinnerSelector:
    """Cryptographically secure winner selection system"""
    
    def __init__(self):
        self.selection_method = os.getenv('SELECTION_METHOD', 'cryptographic_random')
        self.audit_enabled = os.getenv('SELECTION_AUDIT_ENABLED', 'true').lower() == 'true'
    
    def select_winners_cryptographic(self, participants: List[int], winner_count: int) -> List[int]:
        """
        Select winners using cryptographically secure random selection
        
        Args:
            participants: List of participant user IDs
            winner_count: Number of winners to select
            
        Returns:
            List of selected winner user IDs
        """
        if not participants:
            return []
        
        if winner_count >= len(participants):
            return participants.copy()
        
        if winner_count <= 0:
            return []
        
        # Use secrets module for cryptographically secure randomness
        selected_winners = []
        available_participants = participants.copy()
        
        for _ in range(winner_count):
            if not available_participants:
                break
                
            # Generate cryptographically secure random index
            random_index = secrets.randbelow(len(available_participants))
            winner = available_participants.pop(random_index)
            selected_winners.append(winner)
        
        return selected_winners
    
    def select_winners_with_seed(self, participants: List[int], winner_count: int, seed: str) -> List[int]:
        """
        Select winners using a deterministic seed (for reproducible results)
        
        Args:
            participants: List of participant user IDs
            winner_count: Number of winners to select
            seed: Seed string for deterministic selection
            
        Returns:
            List of selected winner user IDs
        """
        if not participants:
            return []
        
        if winner_count >= len(participants):
            return participants.copy()
        
        if winner_count <= 0:
            return []
        
        # Create deterministic random generator from seed
        import random
        random.seed(seed)
        
        # Create a copy and shuffle deterministically
        available_participants = participants.copy()
        random.shuffle(available_participants)
        
        # Select first N participants
        return available_participants[:winner_count]
    
    def generate_selection_seed(self, giveaway_id: int) -> str:
        """Generate a unique seed for deterministic selection"""
        timestamp = datetime.utcnow().isoformat()
        random_bytes = secrets.token_bytes(16)
        
        # Create seed from giveaway ID, timestamp, and random data
        seed_data = f"{giveaway_id}:{timestamp}:{random_bytes.hex()}"
        
        # Hash to create a consistent length seed
        return hashlib.sha256(seed_data.encode()).hexdigest()
    
    def select_winners(self, participants: List[int], winner_count: int, 
                      use_seed: bool = False, custom_seed: str = None) -> Dict[str, Any]:
        """
        Main winner selection method with audit logging
        
        Args:
            participants: List of participant user IDs
            winner_count: Number of winners to select
            use_seed: Whether to use deterministic seed selection
            custom_seed: Custom seed (if None, generates one)
            
        Returns:
            Dictionary with selection results and audit info
        """
        if use_seed:
            seed = custom_seed or self.generate_selection_seed(0)
            winners = self.select_winners_with_seed(participants, winner_count, seed)
            method = 'deterministic_seed'
        else:
            winners = self.select_winners_cryptographic(participants, winner_count)
            seed = None
            method = 'cryptographic_random'
        
        result = {
            'winners': winners,
            'total_participants': len(participants),
            'winner_count_requested': winner_count,
            'winner_count_selected': len(winners),
            'selection_method': method,
            'selection_seed': seed,
            'selection_timestamp': datetime.utcnow().isoformat()
        }
        
        return result
    
    def validate_selection_integrity(self, participants: List[int], winners: List[int]) -> Dict[str, bool]:
        """
        Validate the integrity of a winner selection
        
        Args:
            participants: Original list of participants
            winners: Selected winners
            
        Returns:
            Dictionary with validation results
        """
        validations = {
            'all_winners_are_participants': all(winner in participants for winner in winners),
            'no_duplicate_winners': len(winners) == len(set(winners)),
            'winner_count_reasonable': len(winners) <= len(participants),
            'winners_not_empty': len(winners) > 0 if participants else True
        }
        
        validations['overall_valid'] = all(validations.values())
        
        return validations

# Global instance
winner_selector = WinnerSelector()

# Convenience functions for backward compatibility
def select_winners_cryptographic(participants: List[int], winner_count: int) -> List[int]:
    """Select winners using cryptographically secure random selection"""
    return winner_selector.select_winners_cryptographic(participants, winner_count)

def select_winners(participants: List[int], winner_count: int) -> Dict[str, Any]:
    """Main winner selection function"""
    return winner_selector.select_winners(participants, winner_count)

