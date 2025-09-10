import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from utils.winner_selection import select_winners_cryptographic
from utils.captcha_generator import captcha_generator
from utils.validation import input_validator

class TestPerformance:
    
    def test_winner_selection_performance_small(self):
        """Test winner selection performance with small dataset"""
        participants = list(range(1, 101))  # 100 participants
        winner_count = 10
        
        start_time = time.time()
        winners = select_winners_cryptographic(participants, winner_count)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete very quickly for small dataset
        assert execution_time < 0.01  # 10ms
        assert len(winners) == winner_count
    
    def test_winner_selection_performance_medium(self):
        """Test winner selection performance with medium dataset"""
        participants = list(range(1, 1001))  # 1,000 participants
        winner_count = 50
        
        start_time = time.time()
        winners = select_winners_cryptographic(participants, winner_count)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete quickly for medium dataset
        assert execution_time < 0.05  # 50ms
        assert len(winners) == winner_count
    
    def test_winner_selection_performance_large(self):
        """Test winner selection performance with large dataset"""
        participants = list(range(1, 10001))  # 10,000 participants
        winner_count = 100
        
        start_time = time.time()
        winners = select_winners_cryptographic(participants, winner_count)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete reasonably quickly for large dataset
        assert execution_time < 0.1  # 100ms
        assert len(winners) == winner_count
    
    def test_winner_selection_performance_very_large(self):
        """Test winner selection performance with very large dataset"""
        participants = list(range(1, 100001))  # 100,000 participants
        winner_count = 1000
        
        start_time = time.time()
        winners = select_winners_cryptographic(participants, winner_count)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete within reasonable time for very large dataset
        assert execution_time < 1.0  # 1 second
        assert len(winners) == winner_count
    
    def test_captcha_generation_performance(self):
        """Test captcha generation performance"""
        iterations = 1000
        
        start_time = time.time()
        for _ in range(iterations):
            question, answer = captcha_generator.generate_question()
            assert question is not None
            assert isinstance(answer, int)
        end_time = time.time()
        
        execution_time = end_time - start_time
        avg_time_per_generation = execution_time / iterations
        
        # Should generate captchas very quickly
        assert avg_time_per_generation < 0.001  # 1ms per generation
        assert execution_time < 1.0  # Total time under 1 second
    
    def test_input_validation_performance(self):
        """Test input validation performance"""
        test_data = {
            'giveaway_id': 123,
            'user_id': 456789012,
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        iterations = 1000
        
        start_time = time.time()
        for _ in range(iterations):
            result = input_validator.validate_participation_request(test_data)
            assert result['valid'] == True
        end_time = time.time()
        
        execution_time = end_time - start_time
        avg_time_per_validation = execution_time / iterations
        
        # Should validate inputs very quickly
        assert avg_time_per_validation < 0.001  # 1ms per validation
        assert execution_time < 1.0  # Total time under 1 second
    
    def test_concurrent_winner_selection(self):
        """Test winner selection under concurrent load"""
        participants = list(range(1, 1001))  # 1,000 participants
        winner_count = 10
        num_threads = 10
        selections_per_thread = 10
        
        def run_selections():
            results = []
            for _ in range(selections_per_thread):
                winners = select_winners_cryptographic(participants, winner_count)
                results.append(len(winners))
            return results
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(run_selections) for _ in range(num_threads)]
            
            all_results = []
            for future in as_completed(futures):
                results = future.result()
                all_results.extend(results)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # All selections should return correct number of winners
        assert all(count == winner_count for count in all_results)
        assert len(all_results) == num_threads * selections_per_thread
        
        # Should complete within reasonable time under concurrent load
        assert execution_time < 5.0  # 5 seconds
    
    def test_concurrent_captcha_generation(self):
        """Test captcha generation under concurrent load"""
        num_threads = 20
        generations_per_thread = 50
        
        def generate_captchas():
            results = []
            for _ in range(generations_per_thread):
                question, answer = captcha_generator.generate_question()
                results.append((question is not None, isinstance(answer, int)))
            return results
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(generate_captchas) for _ in range(num_threads)]
            
            all_results = []
            for future in as_completed(futures):
                results = future.result()
                all_results.extend(results)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # All generations should be successful
        assert all(valid_question and valid_answer for valid_question, valid_answer in all_results)
        assert len(all_results) == num_threads * generations_per_thread
        
        # Should complete quickly under concurrent load
        assert execution_time < 2.0  # 2 seconds
    
    def test_memory_usage_winner_selection(self):
        """Test memory efficiency of winner selection"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform many selections with large datasets
        for _ in range(100):
            participants = list(range(1, 10001))  # 10,000 participants
            winners = select_winners_cryptographic(participants, 100)
            assert len(winners) == 100
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024  # 100MB
    
    def test_scalability_winner_selection(self):
        """Test scalability of winner selection with increasing dataset sizes"""
        sizes = [100, 500, 1000, 5000, 10000]
        times = []
        
        for size in sizes:
            participants = list(range(1, size + 1))
            winner_count = min(10, size)  # Select 10 winners or all if less
            
            start_time = time.time()
            winners = select_winners_cryptographic(participants, winner_count)
            end_time = time.time()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            
            assert len(winners) == winner_count
        
        # Execution time should scale reasonably (not exponentially)
        # Check that time doesn't increase too dramatically
        for i in range(1, len(times)):
            # Each step should not be more than 10x slower than previous
            assert times[i] < times[i-1] * 10
    
    def test_repeated_operations_performance(self):
        """Test performance of repeated operations"""
        participants = list(range(1, 1001))
        iterations = 100
        
        # Test repeated winner selections
        start_time = time.time()
        for _ in range(iterations):
            winners = select_winners_cryptographic(participants, 10)
            assert len(winners) == 10
        end_time = time.time()
        
        selection_time = end_time - start_time
        
        # Test repeated captcha generations
        start_time = time.time()
        for _ in range(iterations):
            question, answer = captcha_generator.generate_question()
            assert question is not None
        end_time = time.time()
        
        captcha_time = end_time - start_time
        
        # Test repeated validations
        test_data = {
            'giveaway_id': 123,
            'user_id': 456789012,
            'username': 'testuser'
        }
        
        start_time = time.time()
        for _ in range(iterations):
            result = input_validator.validate_participation_request(test_data)
            assert result['valid'] == True
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        # All operations should complete quickly
        assert selection_time < 1.0  # 1 second for 100 selections
        assert captcha_time < 0.1   # 100ms for 100 captcha generations
        assert validation_time < 0.1  # 100ms for 100 validations
    
    def test_thread_safety(self):
        """Test thread safety of core operations"""
        participants = list(range(1, 101))
        num_threads = 10
        operations_per_thread = 20
        
        results = []
        errors = []
        lock = threading.Lock()
        
        def worker():
            try:
                for _ in range(operations_per_thread):
                    # Winner selection
                    winners = select_winners_cryptographic(participants, 5)
                    
                    # Captcha generation
                    question, answer = captcha_generator.generate_question()
                    
                    # Validation
                    validation = input_validator.validate_user_id(123456789)
                    
                    with lock:
                        results.append({
                            'winners_count': len(winners),
                            'captcha_valid': question is not None and isinstance(answer, int),
                            'validation_valid': validation['valid']
                        })
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        threads = []
        start_time = time.time()
        
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # No errors should occur
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # All operations should succeed
        assert len(results) == num_threads * operations_per_thread
        assert all(r['winners_count'] == 5 for r in results)
        assert all(r['captcha_valid'] for r in results)
        assert all(r['validation_valid'] for r in results)
        
        # Should complete within reasonable time
        assert execution_time < 5.0  # 5 seconds

if __name__ == '__main__':
    pytest.main([__file__])

