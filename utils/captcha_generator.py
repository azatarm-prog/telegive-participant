import random
import os
from typing import Tuple

class CaptchaGenerator:
    """Generate simple math captcha questions for user verification"""
    
    def __init__(self):
        self.min_number = int(os.getenv('CAPTCHA_MIN_NUMBER', 1))
        self.max_number = int(os.getenv('CAPTCHA_MAX_NUMBER', 10))
    
    def generate_addition_question(self) -> Tuple[str, int]:
        """Generate a simple addition question"""
        num1 = random.randint(self.min_number, self.max_number)
        num2 = random.randint(self.min_number, self.max_number)
        
        question = f"What is {num1} + {num2}?"
        answer = num1 + num2
        
        return question, answer
    
    def generate_subtraction_question(self) -> Tuple[str, int]:
        """Generate a simple subtraction question (always positive result)"""
        num1 = random.randint(self.min_number + 2, self.max_number)
        num2 = random.randint(self.min_number, num1 - 1)  # Ensure positive result
        
        question = f"What is {num1} - {num2}?"
        answer = num1 - num2
        
        return question, answer
    
    def generate_multiplication_question(self) -> Tuple[str, int]:
        """Generate a simple multiplication question (small numbers)"""
        # Use smaller numbers for multiplication to keep answers reasonable
        max_mult = min(5, self.max_number)
        num1 = random.randint(1, max_mult)
        num2 = random.randint(1, max_mult)
        
        question = f"What is {num1} × {num2}?"
        answer = num1 * num2
        
        return question, answer
    
    def generate_question(self) -> Tuple[str, int]:
        """Generate a random math question"""
        question_types = [
            self.generate_addition_question,
            self.generate_subtraction_question,
            self.generate_multiplication_question
        ]
        
        # Weight addition more heavily as it's the simplest
        weights = [0.5, 0.3, 0.2]
        question_type = random.choices(question_types, weights=weights)[0]
        
        return question_type()
    
    def validate_answer(self, user_answer: str, correct_answer: int) -> bool:
        """Validate user's answer against the correct answer"""
        try:
            user_answer_int = int(user_answer.strip())
            return user_answer_int == correct_answer
        except (ValueError, AttributeError):
            return False
    
    def generate_captcha_data(self) -> dict:
        """Generate complete captcha data for API responses"""
        question, answer = self.generate_question()
        
        return {
            'question': question,
            'correct_answer': answer,
            'max_attempts': int(os.getenv('CAPTCHA_MAX_ATTEMPTS', 3)),
            'timeout_minutes': int(os.getenv('CAPTCHA_TIMEOUT_MINUTES', 10))
        }

# Global instance
captcha_generator = CaptchaGenerator()

