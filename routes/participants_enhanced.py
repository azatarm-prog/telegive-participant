from flask import Blueprint, request, jsonify
from models import db, Participant, UserCaptchaRecord, CaptchaSession, WinnerSelectionLog
from datetime import datetime, timedelta
import secrets
import logging
import requests
import os

logger = logging.getLogger(__name__)

participants_bp = Blueprint('participants', __name__)

def log_api_call(endpoint, user_id=None, giveaway_id=None, success=True, error=None):
    """Log all API calls for debugging and analytics"""
    logger.info(f"API: {endpoint} | User: {user_id} | Giveaway: {giveaway_id} | Success: {success} | Error: {error}")

@participants_bp.route('/api/participants/register', methods=['POST'])
def register_participant():
    """
    Enhanced participant registration with captcha logic
    Handles both new users (captcha required) and returning users
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['giveaway_id', 'user_id']
        for field in required_fields:
            if field not in data:
                log_api_call('/api/participants/register', data.get('user_id'), data.get('giveaway_id'), False, f'MISSING_FIELD_{field}')
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'error_code': 'MISSING_FIELD'
                }), 400
        
        giveaway_id = data['giveaway_id']
        user_id = data['user_id']
        username = data.get('username')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        # Check for duplicate participation
        existing = Participant.query.filter_by(
            giveaway_id=giveaway_id, 
            user_id=user_id
        ).first()
        
        if existing:
            log_api_call('/api/participants/register', user_id, giveaway_id, False, 'DUPLICATE_PARTICIPATION')
            return jsonify({
                'success': False,
                'error': 'User already participating in this giveaway',
                'error_code': 'DUPLICATE_PARTICIPATION'
            }), 409
        
        # Check if user has completed captcha globally
        captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
        
        if not captcha_record or not captcha_record.captcha_completed:
            # New user - generate captcha
            from utils.captcha_generator import captcha_generator
            question, answer = captcha_generator.generate_question()
            
            # Create captcha session
            session_id = secrets.token_urlsafe(16)
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            
            captcha_session = CaptchaSession(
                user_id=user_id,
                giveaway_id=giveaway_id,
                session_id=session_id,
                question=question,
                correct_answer=answer,
                expires_at=expires_at
            )
            
            db.session.add(captcha_session)
            db.session.commit()
            
            log_api_call('/api/participants/register', user_id, giveaway_id, True, 'CAPTCHA_REQUIRED')
            return jsonify({
                'success': True,
                'requires_captcha': True,
                'captcha_question': question,
                'session_id': session_id,
                'message': 'First-time participation requires verification'
            }), 200
        else:
            # Returning user - register participation directly
            participant = Participant(
                giveaway_id=giveaway_id,
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                captcha_completed=True,
                subscription_verified=True
            )
            
            db.session.add(participant)
            
            # Update user statistics
            captcha_record.total_participations += 1
            
            db.session.commit()
            
            log_api_call('/api/participants/register', user_id, giveaway_id, True, 'PARTICIPATION_CONFIRMED')
            return jsonify({
                'success': True,
                'requires_captcha': False,
                'participant_id': participant.id,
                'message': 'Participation confirmed'
            }), 200
            
    except Exception as e:
        db.session.rollback()
        log_api_call('/api/participants/register', data.get('user_id'), data.get('giveaway_id'), False, str(e))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/api/participants/captcha-status/<int:user_id>', methods=['GET'])
def get_captcha_status(user_id):
    """
    Check if user has completed captcha globally
    Used by Bot Service to optimize participation flow
    """
    try:
        captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
        
        if captcha_record:
            log_api_call('/api/participants/captcha-status', user_id, None, True, 'STATUS_FOUND')
            return jsonify({
                'success': True,
                'captcha_completed': captcha_record.captcha_completed,
                'completed_at': captcha_record.captcha_completed_at.isoformat() if captcha_record.captcha_completed_at else None,
                'total_participations': captcha_record.total_participations,
                'total_wins': captcha_record.total_wins,
                'first_participation': captcha_record.first_participation_at.isoformat() if captcha_record.first_participation_at else None
            }), 200
        else:
            # New user
            log_api_call('/api/participants/captcha-status', user_id, None, True, 'NEW_USER')
            return jsonify({
                'success': True,
                'captcha_completed': False,
                'total_participations': 0,
                'total_wins': 0
            }), 200
            
    except Exception as e:
        log_api_call('/api/participants/captcha-status', user_id, None, False, str(e))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/api/participants/validate-captcha', methods=['POST'])
def validate_captcha():
    """
    Enhanced captcha validation with retry logic
    Handle retry logic and participation confirmation
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'giveaway_id', 'answer', 'session_id']
        for field in required_fields:
            if field not in data:
                log_api_call('/api/participants/validate-captcha', data.get('user_id'), data.get('giveaway_id'), False, f'MISSING_FIELD_{field}')
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'error_code': 'MISSING_FIELD'
                }), 400
        
        user_id = data['user_id']
        giveaway_id = data['giveaway_id']
        user_answer = data['answer']
        session_id = data['session_id']
        
        # Get active captcha session
        captcha_session = CaptchaSession.query.filter_by(
            session_id=session_id,
            user_id=user_id,
            giveaway_id=giveaway_id
        ).first()
        
        if not captcha_session:
            log_api_call('/api/participants/validate-captcha', user_id, giveaway_id, False, 'CAPTCHA_SESSION_NOT_FOUND')
            return jsonify({
                'success': False,
                'error': 'Captcha session not found or expired',
                'error_code': 'CAPTCHA_EXPIRED'
            }), 404
        
        # Check if session expired
        if datetime.utcnow() > captcha_session.expires_at:
            db.session.delete(captcha_session)
            db.session.commit()
            log_api_call('/api/participants/validate-captcha', user_id, giveaway_id, False, 'CAPTCHA_EXPIRED')
            return jsonify({
                'success': False,
                'error': 'Captcha session expired, please try again',
                'error_code': 'CAPTCHA_EXPIRED'
            }), 410
        
        # Validate answer
        if user_answer == captcha_session.correct_answer:
            # Correct answer - complete captcha globally
            captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
            
            if captcha_record:
                captcha_record.captcha_completed = True
                captcha_record.captcha_completed_at = datetime.utcnow()
                captcha_record.total_participations += 1
            else:
                captcha_record = UserCaptchaRecord(
                    user_id=user_id,
                    captcha_completed=True,
                    captcha_completed_at=datetime.utcnow(),
                    first_participation_at=datetime.utcnow(),
                    total_participations=1,
                    total_wins=0
                )
                db.session.add(captcha_record)
            
            # Create participation record
            participant = Participant(
                giveaway_id=giveaway_id,
                user_id=user_id,
                username=data.get('username'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                captcha_completed=True,
                subscription_verified=True
            )
            
            db.session.add(participant)
            
            # Clean up captcha session
            db.session.delete(captcha_session)
            
            db.session.commit()
            
            log_api_call('/api/participants/validate-captcha', user_id, giveaway_id, True, 'CAPTCHA_COMPLETED')
            return jsonify({
                'success': True,
                'captcha_completed': True,
                'participation_confirmed': True,
                'participant_id': participant.id,
                'message': 'Verification complete! Participation confirmed.'
            }), 200
        else:
            # Wrong answer - increment attempts
            captcha_session.attempts += 1
            
            if captcha_session.attempts >= captcha_session.max_attempts:
                # Generate new question after max attempts
                from utils.captcha_generator import captcha_generator
                question, answer = captcha_generator.generate_question()
                
                captcha_session.question = question
                captcha_session.correct_answer = answer
                captcha_session.attempts = 0
                captcha_session.expires_at = datetime.utcnow() + timedelta(minutes=10)
                
                db.session.commit()
                
                log_api_call('/api/participants/validate-captcha', user_id, giveaway_id, True, 'NEW_QUESTION_GENERATED')
                return jsonify({
                    'success': True,
                    'captcha_completed': False,
                    'attempts_remaining': 3,
                    'new_question': question,
                    'message': 'New question generated after maximum attempts'
                }), 200
            else:
                db.session.commit()
                
                log_api_call('/api/participants/validate-captcha', user_id, giveaway_id, True, 'INCORRECT_ANSWER')
                return jsonify({
                    'success': True,
                    'captcha_completed': False,
                    'attempts_remaining': captcha_session.max_attempts - captcha_session.attempts,
                    'message': f'Incorrect answer. {captcha_session.max_attempts - captcha_session.attempts} attempts remaining.'
                }), 200
                
    except Exception as e:
        db.session.rollback()
        log_api_call('/api/participants/validate-captcha', data.get('user_id'), data.get('giveaway_id'), False, str(e))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/api/participants/winner-status/<int:user_id>/<int:giveaway_id>', methods=['GET'])
def get_winner_status(user_id, giveaway_id):
    """
    Check if user won the giveaway
    Used for VIEW RESULTS functionality
    """
    try:
        # Check if user participated
        participation = Participant.query.filter_by(
            giveaway_id=giveaway_id, 
            user_id=user_id
        ).first()
        
        if not participation:
            log_api_call('/api/participants/winner-status', user_id, giveaway_id, True, 'USER_NOT_PARTICIPATED')
            return jsonify({
                'success': True,
                'participated': False,
                'is_winner': False,
                'message': 'User did not participate in this giveaway'
            }), 200
        
        # Get total winner count
        total_winners = Participant.query.filter_by(
            giveaway_id=giveaway_id, 
            is_winner=True
        ).count()
        
        log_api_call('/api/participants/winner-status', user_id, giveaway_id, True, f'WINNER_STATUS_{participation.is_winner}')
        return jsonify({
            'success': True,
            'participated': True,
            'is_winner': participation.is_winner,
            'winner_selected_at': participation.winner_selected_at.isoformat() if participation.winner_selected_at else None,
            'total_winners': total_winners,
            'participant_id': participation.id
        }), 200
        
    except Exception as e:
        log_api_call('/api/participants/winner-status', user_id, giveaway_id, False, str(e))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/api/participants/select-winners', methods=['POST'])
def select_winners():
    """
    Select winners using cryptographically secure random selection
    Called by Giveaway Service when finishing giveaway
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['giveaway_id', 'winner_count']
        for field in required_fields:
            if field not in data:
                log_api_call('/api/participants/select-winners', None, data.get('giveaway_id'), False, f'MISSING_FIELD_{field}')
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'error_code': 'MISSING_FIELD'
                }), 400
        
        giveaway_id = data['giveaway_id']
        winner_count = data['winner_count']
        selection_method = data.get('selection_method', 'cryptographic_random')
        
        # Get all eligible participants
        eligible_participants = Participant.query.filter_by(
            giveaway_id=giveaway_id,
            captcha_completed=True,
            subscription_verified=True
        ).all()
        
        if not eligible_participants:
            log_api_call('/api/participants/select-winners', None, giveaway_id, False, 'NO_PARTICIPANTS')
            return jsonify({
                'success': False,
                'error': 'No eligible participants found',
                'error_code': 'NO_PARTICIPANTS'
            }), 400
        
        total_participants = len(eligible_participants)
        actual_winner_count = min(winner_count, total_participants)
        
        # Perform cryptographically secure selection
        from utils.winner_selection import select_winners_cryptographic
        participant_ids = [p.id for p in eligible_participants]
        selected_ids = select_winners_cryptographic(participant_ids, actual_winner_count)
        
        # Update winner status
        selection_timestamp = datetime.utcnow()
        winner_user_ids = []
        
        for participant in eligible_participants:
            if participant.id in selected_ids:
                participant.is_winner = True
                participant.winner_selected_at = selection_timestamp
                winner_user_ids.append(participant.user_id)
        
        # Log selection for audit
        selection_log = WinnerSelectionLog(
            giveaway_id=giveaway_id,
            total_participants=total_participants,
            winner_count_requested=winner_count,
            winner_count_selected=actual_winner_count,
            selection_method=selection_method,
            winner_user_ids=winner_user_ids,
            selection_timestamp=selection_timestamp
        )
        
        db.session.add(selection_log)
        
        # Update user win statistics
        for user_id in winner_user_ids:
            captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
            if captcha_record:
                captcha_record.total_wins += 1
        
        db.session.commit()
        
        log_api_call('/api/participants/select-winners', None, giveaway_id, True, f'SELECTED_{actual_winner_count}_WINNERS')
        return jsonify({
            'success': True,
            'winners': winner_user_ids,
            'total_participants': total_participants,
            'winner_count_requested': winner_count,
            'winner_count_selected': actual_winner_count,
            'selection_timestamp': selection_timestamp.isoformat(),
            'selection_method': selection_method
        }), 200
        
    except Exception as e:
        db.session.rollback()
        log_api_call('/api/participants/select-winners', None, data.get('giveaway_id'), False, str(e))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/api/participants/count/<int:giveaway_id>', methods=['GET'])
def get_participant_count(giveaway_id):
    """
    Get participant count for giveaway
    Used for real-time participant counter
    """
    try:
        count = Participant.query.filter_by(giveaway_id=giveaway_id).count()
        
        log_api_call('/api/participants/count', None, giveaway_id, True, f'COUNT_{count}')
        return jsonify({
            'success': True,
            'giveaway_id': giveaway_id,
            'count': count
        }), 200
        
    except Exception as e:
        log_api_call('/api/participants/count', None, giveaway_id, False, str(e))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/api/participants/list/<int:giveaway_id>', methods=['GET'])
def get_participant_list(giveaway_id):
    """
    Get paginated participant list for giveaway
    Used by Dashboard Service for participant management
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        # Limit maximum page size
        limit = min(limit, 100)
        
        participants_query = Participant.query.filter_by(giveaway_id=giveaway_id)
        total_count = participants_query.count()
        
        participants = participants_query.offset((page - 1) * limit).limit(limit).all()
        
        participant_list = [p.to_dict() for p in participants]
        
        log_api_call('/api/participants/list', None, giveaway_id, True, f'PAGE_{page}_LIMIT_{limit}')
        return jsonify({
            'success': True,
            'participants': participant_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        log_api_call('/api/participants/list', None, giveaway_id, False, str(e))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/api/participants/update-delivery-status', methods=['PUT'])
def update_delivery_status():
    """
    Update message delivery status for participants
    Called by Bot Service after sending DMs
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['participant_ids', 'delivered']
        for field in required_fields:
            if field not in data:
                log_api_call('/api/participants/update-delivery-status', None, None, False, f'MISSING_FIELD_{field}')
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'error_code': 'MISSING_FIELD'
                }), 400
        
        participant_ids = data['participant_ids']
        delivered = data['delivered']
        delivery_timestamp = datetime.utcnow()
        
        # Update delivery status in database
        updated_count = 0
        for participant_id in participant_ids:
            participant = Participant.query.get(participant_id)
            if participant:
                participant.message_delivered = delivered
                participant.delivery_timestamp = delivery_timestamp
                participant.delivery_attempts += 1
                updated_count += 1
        
        db.session.commit()
        
        log_api_call('/api/participants/update-delivery-status', None, None, True, f'UPDATED_{updated_count}_RECORDS')
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'delivery_timestamp': delivery_timestamp.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        log_api_call('/api/participants/update-delivery-status', None, None, False, str(e))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/api/participants/verify-subscription', methods=['POST'])
def verify_subscription():
    """
    Verify user subscription to Telegram channel
    Called by Bot Service for subscription verification
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'account_id']
        for field in required_fields:
            if field not in data:
                log_api_call('/api/participants/verify-subscription', data.get('user_id'), None, False, f'MISSING_FIELD_{field}')
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'error_code': 'MISSING_FIELD'
                }), 400
        
        user_id = data['user_id']
        account_id = data['account_id']
        
        # Get bot token and channel info from services
        from services import auth_service, channel_service
        
        # Get bot token
        bot_token = auth_service.get_bot_token(account_id)
        if not bot_token:
            log_api_call('/api/participants/verify-subscription', user_id, None, False, 'BOT_TOKEN_NOT_FOUND')
            return jsonify({
                'success': False,
                'error': 'Bot token not found for account',
                'error_code': 'BOT_TOKEN_NOT_FOUND'
            }), 404
        
        # Get channel info
        channel_info = channel_service.get_channel_info(account_id)
        if not channel_info:
            log_api_call('/api/participants/verify-subscription', user_id, None, False, 'CHANNEL_NOT_CONFIGURED')
            return jsonify({
                'success': False,
                'error': 'Channel not configured for account',
                'error_code': 'CHANNEL_NOT_CONFIGURED'
            }), 404
        
        # Check subscription via Telegram API
        is_subscribed = check_telegram_subscription(bot_token, channel_info['channel_id'], user_id)
        
        if is_subscribed:
            # Update subscription status for all user's participations
            participants = Participant.query.filter_by(user_id=user_id).all()
            for participant in participants:
                participant.subscription_verified = True
                participant.subscription_verified_at = datetime.utcnow()
            
            db.session.commit()
            
            log_api_call('/api/participants/verify-subscription', user_id, None, True, 'SUBSCRIPTION_VERIFIED')
            return jsonify({
                'success': True,
                'is_subscribed': True,
                'verified_at': datetime.utcnow().isoformat(),
                'channel_info': {
                    'id': channel_info['channel_id'],
                    'username': channel_info.get('username'),
                    'title': channel_info.get('title')
                }
            }), 200
        else:
            log_api_call('/api/participants/verify-subscription', user_id, None, True, 'USER_NOT_SUBSCRIBED')
            return jsonify({
                'success': True,
                'is_subscribed': False,
                'channel_info': {
                    'id': channel_info['channel_id'],
                    'username': channel_info.get('username'),
                    'title': channel_info.get('title')
                }
            }), 200
            
    except Exception as e:
        db.session.rollback()
        log_api_call('/api/participants/verify-subscription', data.get('user_id'), None, False, str(e))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

def check_telegram_subscription(bot_token, channel_id, user_id):
    """Check user subscription via Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
        params = {
            'chat_id': channel_id,
            'user_id': user_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result['ok']:
                member_status = result['result']['status']
                return member_status in ['member', 'administrator', 'creator']
        
        return False
        
    except Exception as e:
        logger.error(f"Telegram API error: {str(e)}")
        return False

