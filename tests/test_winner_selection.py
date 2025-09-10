import pytest
import time
import secrets
from collections import Counter

from utils.winner_selection import winner_selector, select_winners_cryptographic, select_winners

class TestWinnerSelection:
    
    def test_cryptographic_randomness(self):
        """Test cryptographic randomness of winner selection"""
        participants = list(range(1, 101))  # 100 participants
        winner_count = 10
        
        # Run selection multiple times
        selections = []
        for _ in range(100):
            winners = select_winners_cryptographic(participants, winner_count)
            selections.append(sorted(winners))
        
        # Check that selections are different (very high probability)
        unique_selections = set(tuple(s) for s in selections)
        assert len(unique_selections) > 90  # At least 90% unique
        
        # Check that each selection has correct count
        for selection in selections:
            assert len(selection) == winner_count
            assert len(set(selection)) == winner_count  # No duplicates
    
    def test_winner_selection_edge_cases(self):
        """Test winner selection edge cases"""
        # More winners than participants
        participants = [1, 2, 3]
        winners = select_winners_cryptographic(participants, 5)
        assert len(winners) == 3
        assert set(winners) == set(participants)
        
        # Zero winners requested
        winners = select_winners_cryptographic(participants, 0)
        assert len(winners) == 0
        
        # Empty participant list
        winners = select_winners_cryptographic([], 5)
        assert len(winners) == 0
        
        # Single participant
        winners = select_winners_cryptographic([42], 1)
        assert winners == [42]
    
    def test_winner_selection_fairness(self):
        """Test that winner selection is fair over many iterations"""
        participants = list(range(1, 11))  # 10 participants
        winner_count = 3
        iterations = 1000
        
        # Count how many times each participant is selected
        selection_counts = Counter()
        
        for _ in range(iterations):
            winners = select_winners_cryptographic(participants, winner_count)
            for winner in winners:
                selection_counts[winner] += 1
        
        # Each participant should be selected roughly the same number of times
        # Expected: (iterations * winner_count) / len(participants) = 300
        expected = (iterations * winner_count) / len(participants)
        
        for participant in participants:
            count = selection_counts[participant]
            # Allow 20% deviation from expected
            assert abs(count - expected) < expected * 0.2
    
    def test_deterministic_seed_selection(self):
        """Test deterministic selection with seed"""
        participants = list(range(1, 21))  # 20 participants
        winner_count = 5
        seed = "test_seed_123"
        
        # Multiple selections with same seed should be identical
        winners1 = winner_selector.select_winners_with_seed(participants, winner_count, seed)
        winners2 = winner_selector.select_winners_with_seed(participants, winner_count, seed)
        winners3 = winner_selector.select_winners_with_seed(participants, winner_count, seed)
        
        assert winners1 == winners2 == winners3
        assert len(winners1) == winner_count
        assert all(w in participants for w in winners1)
    
    def test_different_seeds_different_results(self):
        """Test that different seeds produce different results"""
        participants = list(range(1, 51))  # 50 participants
        winner_count = 10
        
        seeds = ["seed1", "seed2", "seed3", "seed4", "seed5"]
        results = []
        
        for seed in seeds:
            winners = winner_selector.select_winners_with_seed(participants, winner_count, seed)
            results.append(sorted(winners))
        
        # All results should be different
        unique_results = set(tuple(r) for r in results)
        assert len(unique_results) == len(seeds)
    
    def test_selection_integrity_validation(self):
        """Test selection integrity validation"""
        participants = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        # Valid selection
        winners = [2, 5, 8]
        validation = winner_selector.validate_selection_integrity(participants, winners)
        assert validation['overall_valid'] == True
        assert validation['all_winners_are_participants'] == True
        assert validation['no_duplicate_winners'] == True
        assert validation['winner_count_reasonable'] == True
        assert validation['winners_not_empty'] == True
        
        # Invalid selection - winner not in participants
        invalid_winners = [2, 5, 15]
        validation = winner_selector.validate_selection_integrity(participants, invalid_winners)
        assert validation['overall_valid'] == False
        assert validation['all_winners_are_participants'] == False
        
        # Invalid selection - duplicate winners
        duplicate_winners = [2, 5, 2]
        validation = winner_selector.validate_selection_integrity(participants, duplicate_winners)
        assert validation['overall_valid'] == False
        assert validation['no_duplicate_winners'] == False
        
        # Invalid selection - too many winners
        too_many_winners = list(range(1, 15))
        validation = winner_selector.validate_selection_integrity(participants, too_many_winners)
        assert validation['overall_valid'] == False
        assert validation['winner_count_reasonable'] == False
    
    def test_selection_performance(self):
        """Test that winner selection performs well with large datasets"""
        # Large participant list
        participants = list(range(1, 10001))  # 10,000 participants
        winner_count = 100
        
        start_time = time.time()
        winners = select_winners_cryptographic(participants, winner_count)
        end_time = time.time()
        
        # Should complete in under 100ms
        assert end_time - start_time < 0.1
        assert len(winners) == winner_count
        assert len(set(winners)) == winner_count  # No duplicates
        assert all(w in participants for w in winners)
    
    def test_main_select_winners_function(self):
        """Test the main select_winners function with audit info"""
        participants = list(range(1, 21))
        winner_count = 5
        
        # Test cryptographic selection
        result = select_winners(participants, winner_count)
        
        assert result['winner_count_requested'] == winner_count
        assert result['winner_count_selected'] == winner_count
        assert result['total_participants'] == len(participants)
        assert result['selection_method'] == 'cryptographic_random'
        assert result['selection_seed'] is None
        assert len(result['winners']) == winner_count
        assert 'selection_timestamp' in result
        
        # Test deterministic selection
        result = winner_selector.select_winners(participants, winner_count, use_seed=True, custom_seed="test")
        
        assert result['selection_method'] == 'deterministic_seed'
        assert result['selection_seed'] == "test"
        assert len(result['winners']) == winner_count
    
    def test_seed_generation(self):
        """Test selection seed generation"""
        giveaway_id = 123
        
        # Generate multiple seeds
        seeds = []
        for _ in range(10):
            seed = winner_selector.generate_selection_seed(giveaway_id)
            seeds.append(seed)
        
        # All seeds should be different
        assert len(set(seeds)) == len(seeds)
        
        # All seeds should be strings of consistent length (SHA256 hex = 64 chars)
        for seed in seeds:
            assert isinstance(seed, str)
            assert len(seed) == 64
            assert all(c in '0123456789abcdef' for c in seed)
    
    def test_winner_selection_with_large_winner_count(self):
        """Test winner selection when winner count equals participant count"""
        participants = [1, 2, 3, 4, 5]
        winner_count = 5
        
        winners = select_winners_cryptographic(participants, winner_count)
        
        assert len(winners) == 5
        assert set(winners) == set(participants)
    
    def test_winner_selection_consistency(self):
        """Test that selection is consistent within the same process"""
        participants = list(range(1, 101))
        winner_count = 10
        
        # Use secrets module directly to ensure we're testing the right thing
        original_randbelow = secrets.randbelow
        
        # Mock secrets.randbelow to return predictable sequence
        call_count = 0
        def mock_randbelow(n):
            nonlocal call_count
            call_count += 1
            return call_count % n
        
        # Test with mocked randomness
        with pytest.MonkeyPatch().context() as m:
            m.setattr(secrets, 'randbelow', mock_randbelow)
            
            winners = select_winners_cryptographic(participants, winner_count)
            assert len(winners) == winner_count
            assert len(set(winners)) == winner_count
        
        # Restore original function
        secrets.randbelow = original_randbelow
    
    def test_empty_and_none_inputs(self):
        """Test handling of empty and None inputs"""
        # Empty participants list
        assert select_winners_cryptographic([], 5) == []
        assert select_winners_cryptographic([], 0) == []
        
        # None participants (should raise error)
        with pytest.raises(TypeError):
            select_winners_cryptographic(None, 5)
        
        # Negative winner count
        participants = [1, 2, 3, 4, 5]
        assert select_winners_cryptographic(participants, -1) == []
        assert select_winners_cryptographic(participants, -10) == []
    
    def test_winner_selection_with_duplicate_participants(self):
        """Test winner selection with duplicate participant IDs"""
        # This shouldn't happen in real usage, but test robustness
        participants = [1, 2, 3, 2, 4, 3, 5]  # Duplicates
        winner_count = 3
        
        winners = select_winners_cryptographic(participants, winner_count)
        
        assert len(winners) == winner_count
        # Winners should be from the original list (may include duplicates)
        assert all(w in participants for w in winners)

if __name__ == '__main__':
    pytest.main([__file__])

