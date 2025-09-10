import re
from typing import Dict, Any, Optional, List

class InputValidator:
    """Utility for validating API inputs and data"""
    
    def __init__(self):
        # Telegram user ID constraints
        self.min_user_id = 1
        self.max_user_id = 2**63 - 1  # Max BigInteger value
        
        # Username constraints
        self.username_pattern = re.compile(r'^[a-zA-Z0-9_]{5,32}$')
        
        # Name constraints
        self.max_name_length = 100
        
        # Giveaway ID constraints
        self.min_giveaway_id = 1
        
        # Winner count constraints
        self.max_winner_count = 1000
    
    def validate_user_id(self, user_id: Any) -> Dict[str, Any]:
        """Validate Telegram user ID"""
        try:
            user_id = int(user_id)
            
            if user_id < self.min_user_id or user_id > self.max_user_id:
                return {
                    'valid': False,
                    'error': f'User ID must be between {self.min_user_id} and {self.max_user_id}',
                    'error_code': 'INVALID_USER_ID_RANGE'
                }
            
            return {'valid': True, 'value': user_id}
            
        except (ValueError, TypeError):
            return {
                'valid': False,
                'error': 'User ID must be a valid integer',
                'error_code': 'INVALID_USER_ID_FORMAT'
            }
    
    def validate_giveaway_id(self, giveaway_id: Any) -> Dict[str, Any]:
        """Validate giveaway ID"""
        try:
            giveaway_id = int(giveaway_id)
            
            if giveaway_id < self.min_giveaway_id:
                return {
                    'valid': False,
                    'error': f'Giveaway ID must be at least {self.min_giveaway_id}',
                    'error_code': 'INVALID_GIVEAWAY_ID'
                }
            
            return {'valid': True, 'value': giveaway_id}
            
        except (ValueError, TypeError):
            return {
                'valid': False,
                'error': 'Giveaway ID must be a valid integer',
                'error_code': 'INVALID_GIVEAWAY_ID_FORMAT'
            }
    
    def validate_username(self, username: Any) -> Dict[str, Any]:
        """Validate Telegram username"""
        if username is None:
            return {'valid': True, 'value': None}
        
        if not isinstance(username, str):
            return {
                'valid': False,
                'error': 'Username must be a string',
                'error_code': 'INVALID_USERNAME_TYPE'
            }
        
        username = username.strip()
        
        if not username:
            return {'valid': True, 'value': None}
        
        # Remove @ prefix if present
        if username.startswith('@'):
            username = username[1:]
        
        if not self.username_pattern.match(username):
            return {
                'valid': False,
                'error': 'Username must be 5-32 characters, alphanumeric and underscores only',
                'error_code': 'INVALID_USERNAME_FORMAT'
            }
        
        return {'valid': True, 'value': username}
    
    def validate_name(self, name: Any, field_name: str = 'name') -> Dict[str, Any]:
        """Validate first name or last name"""
        if name is None:
            return {'valid': True, 'value': None}
        
        if not isinstance(name, str):
            return {
                'valid': False,
                'error': f'{field_name} must be a string',
                'error_code': 'INVALID_NAME_TYPE'
            }
        
        name = name.strip()
        
        if not name:
            return {'valid': True, 'value': None}
        
        if len(name) > self.max_name_length:
            return {
                'valid': False,
                'error': f'{field_name} must be {self.max_name_length} characters or less',
                'error_code': 'NAME_TOO_LONG'
            }
        
        return {'valid': True, 'value': name}
    
    def validate_winner_count(self, winner_count: Any) -> Dict[str, Any]:
        """Validate winner count"""
        try:
            winner_count = int(winner_count)
            
            if winner_count < 1:
                return {
                    'valid': False,
                    'error': 'Winner count must be at least 1',
                    'error_code': 'INVALID_WINNER_COUNT_MIN'
                }
            
            if winner_count > self.max_winner_count:
                return {
                    'valid': False,
                    'error': f'Winner count cannot exceed {self.max_winner_count}',
                    'error_code': 'INVALID_WINNER_COUNT_MAX'
                }
            
            return {'valid': True, 'value': winner_count}
            
        except (ValueError, TypeError):
            return {
                'valid': False,
                'error': 'Winner count must be a valid integer',
                'error_code': 'INVALID_WINNER_COUNT_FORMAT'
            }
    
    def validate_captcha_answer(self, answer: Any) -> Dict[str, Any]:
        """Validate captcha answer"""
        try:
            answer = int(str(answer).strip())
            return {'valid': True, 'value': answer}
            
        except (ValueError, TypeError):
            return {
                'valid': False,
                'error': 'Captcha answer must be a valid number',
                'error_code': 'INVALID_CAPTCHA_ANSWER'
            }
    
    def validate_participation_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate participation registration request"""
        errors = []
        validated_data = {}
        
        # Validate required fields
        required_fields = ['giveaway_id', 'user_id']
        for field in required_fields:
            if field not in data:
                errors.append({
                    'field': field,
                    'error': f'{field} is required',
                    'error_code': 'MISSING_REQUIRED_FIELD'
                })
        
        # Validate giveaway_id
        if 'giveaway_id' in data:
            giveaway_validation = self.validate_giveaway_id(data['giveaway_id'])
            if giveaway_validation['valid']:
                validated_data['giveaway_id'] = giveaway_validation['value']
            else:
                errors.append({
                    'field': 'giveaway_id',
                    'error': giveaway_validation['error'],
                    'error_code': giveaway_validation['error_code']
                })
        
        # Validate user_id
        if 'user_id' in data:
            user_validation = self.validate_user_id(data['user_id'])
            if user_validation['valid']:
                validated_data['user_id'] = user_validation['value']
            else:
                errors.append({
                    'field': 'user_id',
                    'error': user_validation['error'],
                    'error_code': user_validation['error_code']
                })
        
        # Validate optional fields
        optional_fields = {
            'username': self.validate_username,
            'first_name': lambda x: self.validate_name(x, 'first_name'),
            'last_name': lambda x: self.validate_name(x, 'last_name')
        }
        
        for field, validator in optional_fields.items():
            if field in data:
                validation = validator(data[field])
                if validation['valid']:
                    validated_data[field] = validation['value']
                else:
                    errors.append({
                        'field': field,
                        'error': validation['error'],
                        'error_code': validation['error_code']
                    })
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'validated_data': validated_data
        }
    
    def validate_captcha_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate captcha validation request"""
        errors = []
        validated_data = {}
        
        # Validate required fields
        required_fields = ['user_id', 'giveaway_id', 'answer']
        for field in required_fields:
            if field not in data:
                errors.append({
                    'field': field,
                    'error': f'{field} is required',
                    'error_code': 'MISSING_REQUIRED_FIELD'
                })
        
        # Validate fields
        if 'user_id' in data:
            user_validation = self.validate_user_id(data['user_id'])
            if user_validation['valid']:
                validated_data['user_id'] = user_validation['value']
            else:
                errors.append({
                    'field': 'user_id',
                    'error': user_validation['error'],
                    'error_code': user_validation['error_code']
                })
        
        if 'giveaway_id' in data:
            giveaway_validation = self.validate_giveaway_id(data['giveaway_id'])
            if giveaway_validation['valid']:
                validated_data['giveaway_id'] = giveaway_validation['value']
            else:
                errors.append({
                    'field': 'giveaway_id',
                    'error': giveaway_validation['error'],
                    'error_code': giveaway_validation['error_code']
                })
        
        if 'answer' in data:
            answer_validation = self.validate_captcha_answer(data['answer'])
            if answer_validation['valid']:
                validated_data['answer'] = answer_validation['value']
            else:
                errors.append({
                    'field': 'answer',
                    'error': answer_validation['error'],
                    'error_code': answer_validation['error_code']
                })
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'validated_data': validated_data
        }

# Global instance
input_validator = InputValidator()

