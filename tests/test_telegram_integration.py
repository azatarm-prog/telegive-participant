import pytest
from unittest.mock import patch, Mock
import requests

from services.telegram_api import telegram_api, check_channel_membership

class TestTelegramSubscriptionIntegration:
    
    @patch('requests.get')
    def test_check_channel_membership_success(self, mock_get):
        """Test successful channel membership check"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ok': True,
            'result': {
                'status': 'member',
                'user': {
                    'id': 123456789,
                    'is_bot': False,
                    'first_name': 'Test'
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
        
        assert result['success'] == True
        assert result['is_member'] == True
        assert result['status'] == 'member'
    
    @patch('requests.get')
    def test_check_channel_membership_not_member(self, mock_get):
        """Test channel membership check for non-member"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ok': True,
            'result': {
                'status': 'left',
                'user': {
                    'id': 123456789,
                    'is_bot': False,
                    'first_name': 'Test'
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
        
        assert result['success'] == True
        assert result['is_member'] == False
        assert result['status'] == 'left'
    
    @patch('requests.get')
    def test_check_channel_membership_administrator(self, mock_get):
        """Test channel membership check for administrator"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ok': True,
            'result': {
                'status': 'administrator',
                'user': {
                    'id': 123456789,
                    'is_bot': False,
                    'first_name': 'Admin'
                },
                'can_be_edited': False,
                'can_manage_chat': True
            }
        }
        mock_get.return_value = mock_response
        
        result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
        
        assert result['success'] == True
        assert result['is_member'] == True
        assert result['status'] == 'administrator'
    
    @patch('requests.get')
    def test_check_channel_membership_creator(self, mock_get):
        """Test channel membership check for creator"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ok': True,
            'result': {
                'status': 'creator',
                'user': {
                    'id': 123456789,
                    'is_bot': False,
                    'first_name': 'Creator'
                },
                'is_anonymous': False
            }
        }
        mock_get.return_value = mock_response
        
        result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
        
        assert result['success'] == True
        assert result['is_member'] == True
        assert result['status'] == 'creator'
    
    @patch('requests.get')
    def test_check_channel_membership_api_error(self, mock_get):
        """Test channel membership check with Telegram API error"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ok': False,
            'error_code': 400,
            'description': 'Bad Request: chat not found'
        }
        mock_get.return_value = mock_response
        
        result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
        
        assert result['success'] == False
        assert result['is_member'] == False
        assert 'Bad Request' in result['error']
    
    @patch('requests.get')
    def test_check_channel_membership_http_error(self, mock_get):
        """Test channel membership check with HTTP error"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
        
        assert result['success'] == False
        assert result['is_member'] == False
        assert 'HTTP error: 404' in result['error']
    
    @patch('requests.get')
    def test_check_channel_membership_network_error(self, mock_get):
        """Test channel membership check with network error"""
        mock_get.side_effect = requests.RequestException('Network error')
        
        result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
        
        assert result['success'] == False
        assert result['is_member'] == False
        assert 'Request error' in result['error']
    
    @patch('requests.get')
    def test_get_chat_info_success(self, mock_get):
        """Test successful chat info retrieval"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ok': True,
            'result': {
                'id': -1001234567890,
                'title': 'Test Channel',
                'type': 'channel',
                'description': 'Test channel description'
            }
        }
        mock_get.return_value = mock_response
        
        result = telegram_api.get_chat_info('bot_token', -1001234567890)
        
        assert result is not None
        assert result['id'] == -1001234567890
        assert result['title'] == 'Test Channel'
        assert result['type'] == 'channel'
    
    @patch('requests.get')
    def test_get_chat_member_count_success(self, mock_get):
        """Test successful chat member count retrieval"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ok': True,
            'result': 1250
        }
        mock_get.return_value = mock_response
        
        result = telegram_api.get_chat_member_count('bot_token', -1001234567890)
        
        assert result == 1250
    
    def test_check_channel_membership_convenience_function(self):
        """Test the convenience function for backward compatibility"""
        with patch.object(telegram_api, 'check_channel_membership') as mock_method:
            mock_method.return_value = {
                'success': True,
                'is_member': True,
                'status': 'member'
            }
            
            result = check_channel_membership('bot_token', -1001234567890, 123456789)
            
            assert result['success'] == True
            assert result['is_member'] == True
            mock_method.assert_called_once_with('bot_token', -1001234567890, 123456789)
    
    def test_telegram_api_base_url_configuration(self):
        """Test Telegram API base URL configuration"""
        import os
        
        # Test default URL
        api = telegram_api
        assert api.api_base == 'https://api.telegram.org'
        
        # Test custom URL from environment
        with patch.dict(os.environ, {'TELEGRAM_API_BASE': 'https://custom.api.telegram.org'}):
            from services.telegram_api import TelegramAPI
            custom_api = TelegramAPI()
            assert custom_api.api_base == 'https://custom.api.telegram.org'
    
    @patch('requests.get')
    def test_check_channel_membership_timeout(self, mock_get):
        """Test channel membership check with timeout"""
        mock_get.side_effect = requests.Timeout('Request timeout')
        
        result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
        
        assert result['success'] == False
        assert result['is_member'] == False
        assert 'timeout' in result['error'].lower()
    
    @patch('requests.get')
    def test_check_channel_membership_invalid_json(self, mock_get):
        """Test channel membership check with invalid JSON response"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError('Invalid JSON')
        mock_get.return_value = mock_response
        
        result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
        
        assert result['success'] == False
        assert result['is_member'] == False
    
    def test_membership_status_mapping(self):
        """Test that all valid membership statuses are correctly mapped"""
        valid_statuses = ['member', 'administrator', 'creator']
        invalid_statuses = ['left', 'kicked', 'restricted']
        
        for status in valid_statuses:
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.ok = True
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'ok': True,
                    'result': {'status': status}
                }
                mock_get.return_value = mock_response
                
                result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
                assert result['is_member'] == True
        
        for status in invalid_statuses:
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.ok = True
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'ok': True,
                    'result': {'status': status}
                }
                mock_get.return_value = mock_response
                
                result = telegram_api.check_channel_membership('bot_token', -1001234567890, 123456789)
                assert result['is_member'] == False

if __name__ == '__main__':
    pytest.main([__file__])

