from typing import Dict, Optional
from services.auth_service import auth_service
from services.channel_service import channel_service
from services.telegram_api import telegram_api

class SubscriptionChecker:
    """Utility for verifying user subscription to channels"""
    
    def __init__(self):
        pass
    
    def verify_subscription(self, user_id: int, account_id: int) -> Dict:
        """
        Verify if a user is subscribed to the channel for a given account
        
        Args:
            user_id: Telegram user ID
            account_id: Account ID to get channel info for
            
        Returns:
            Dictionary with verification results
        """
        try:
            # Get channel information for the account
            channel_info = channel_service.get_channel_info(account_id)
            if not channel_info:
                return {
                    'success': False,
                    'is_subscribed': False,
                    'error': 'Channel information not found for account',
                    'error_code': 'CHANNEL_NOT_FOUND'
                }
            
            channel_id = channel_info.get('telegram_id')
            if not channel_id:
                return {
                    'success': False,
                    'is_subscribed': False,
                    'error': 'Channel Telegram ID not configured',
                    'error_code': 'CHANNEL_ID_MISSING'
                }
            
            # Get bot token for the account
            bot_token = auth_service.get_bot_token(account_id)
            if not bot_token:
                return {
                    'success': False,
                    'is_subscribed': False,
                    'error': 'Bot token not found for account',
                    'error_code': 'BOT_TOKEN_MISSING'
                }
            
            # Check membership via Telegram API
            membership_result = telegram_api.check_channel_membership(
                bot_token, channel_id, user_id
            )
            
            if not membership_result.get('success'):
                return {
                    'success': False,
                    'is_subscribed': False,
                    'error': membership_result.get('error', 'Failed to check membership'),
                    'error_code': 'TELEGRAM_API_ERROR'
                }
            
            is_subscribed = membership_result.get('is_member', False)
            
            return {
                'success': True,
                'is_subscribed': is_subscribed,
                'verified_at': None,  # Will be set by caller
                'channel_info': {
                    'id': channel_id,
                    'title': channel_info.get('title', 'Unknown Channel')
                },
                'membership_status': membership_result.get('status', 'unknown')
            }
            
        except Exception as e:
            return {
                'success': False,
                'is_subscribed': False,
                'error': f'Subscription verification failed: {str(e)}',
                'error_code': 'VERIFICATION_ERROR'
            }
    
    def verify_subscription_by_giveaway(self, user_id: int, giveaway_id: int) -> Dict:
        """
        Verify subscription using giveaway ID to get channel info
        
        Args:
            user_id: Telegram user ID
            giveaway_id: Giveaway ID to get channel info for
            
        Returns:
            Dictionary with verification results
        """
        try:
            # Get channel information for the giveaway
            channel_info = channel_service.get_channel_by_giveaway(giveaway_id)
            if not channel_info:
                return {
                    'success': False,
                    'is_subscribed': False,
                    'error': 'Channel information not found for giveaway',
                    'error_code': 'CHANNEL_NOT_FOUND'
                }
            
            account_id = channel_info.get('account_id')
            if not account_id:
                return {
                    'success': False,
                    'is_subscribed': False,
                    'error': 'Account ID not found for channel',
                    'error_code': 'ACCOUNT_ID_MISSING'
                }
            
            # Use the main verification method
            return self.verify_subscription(user_id, account_id)
            
        except Exception as e:
            return {
                'success': False,
                'is_subscribed': False,
                'error': f'Subscription verification failed: {str(e)}',
                'error_code': 'VERIFICATION_ERROR'
            }
    
    def batch_verify_subscriptions(self, user_ids: list, account_id: int) -> Dict:
        """
        Verify subscriptions for multiple users at once
        
        Args:
            user_ids: List of Telegram user IDs
            account_id: Account ID to check subscriptions for
            
        Returns:
            Dictionary with batch verification results
        """
        results = {}
        errors = []
        
        for user_id in user_ids:
            try:
                result = self.verify_subscription(user_id, account_id)
                results[user_id] = result
            except Exception as e:
                error_info = {
                    'user_id': user_id,
                    'error': str(e)
                }
                errors.append(error_info)
                results[user_id] = {
                    'success': False,
                    'is_subscribed': False,
                    'error': str(e),
                    'error_code': 'BATCH_VERIFICATION_ERROR'
                }
        
        return {
            'success': len(errors) == 0,
            'results': results,
            'errors': errors,
            'total_checked': len(user_ids),
            'successful_checks': len([r for r in results.values() if r.get('success')])
        }

# Global instance
subscription_checker = SubscriptionChecker()

