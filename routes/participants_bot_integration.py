from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import secrets
import logging
import requests
import os

logger = logging.getLogger(__name__)

participants_bot_bp = Blueprint('participants_bot', __name__)

def log_api_call(endpoint, user_id=None, giveaway_id=None, success=True, error=None):
    """Log all API calls for debugging and analytics"""
    logger.info(f"API: {endpoint} | User: {user_id} | Giveaway: {giveaway_id} | Success: {success} | Error: {error}")

@participants_bot_bp.route('/api/participants/captcha-status/<int:user_id>', methods=['GET'])
def captcha_status_check(user_id):
    """
    Check if user has already completed captcha globally
    Called by Bot Service before showing captcha to optimize user experience
    """
    try:
        from models import db, UserCaptchaRecord
        
        captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
        
        if captcha_record:
            log_api_call('/api/participants/captcha-status', user_id, None, True, 'STATUS_FOUND')
            return jsonify({
                'success': True,
                'captcha_completed': captcha_record.captcha_completed,
                'total_participations': captcha_record.total_participations,
                'total_wins': captcha_record.total_wins
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
            'error': 'User lookup failed',
            'error_code': 'USER_LOOKUP_ERROR'
        }), 500

@participants_bot_bp.route('/api/participants/register', methods=['POST'])
def participation_registration():
    """
    Register user participation in a giveaway
    Called when user clicks "🎯 Participate" button
    """
    try:
        from models import db, Participant, UserCaptchaRecord, CaptchaSession
        
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
            }), 200
        
        # Check if user has completed captcha globally
        captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
        
        if not captcha_record or not captcha_record.captcha_completed:
            # New user - generate captcha
            import random
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            question = f"What is {a} + {b}?"
            answer = a + b
            
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
                'message': 'Captcha required for new user'
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
        try:
            db.session.rollback()
        except:
            pass
        log_api_call('/api/participants/register', data.get('user_id') if 'data' in locals() else None, data.get('giveaway_id') if 'data' in locals() else None, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}',
            'error_code': 'REGISTRATION_ERROR'
        }), 500

@participants_bot_bp.route('/api/participants/validate-captcha', methods=['POST'])
def captcha_validation():
    """
    Validate user's captcha answer and complete participation
    Called when user submits captcha answer
    """
    try:
        from models import db, Participant, UserCaptchaRecord, CaptchaSession
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'giveaway_id', 'answer']
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
        
        # Get active captcha session
        captcha_session = CaptchaSession.query.filter_by(
            user_id=user_id,
            giveaway_id=giveaway_id
        ).first()
        
        if not captcha_session:
            log_api_call('/api/participants/validate-captcha', user_id, giveaway_id, False, 'CAPTCHA_SESSION_NOT_FOUND')
            return jsonify({
                'success': False,
                'error': 'Captcha session expired, please try again',
                'error_code': 'CAPTCHA_EXPIRED'
            }), 400
        
        # Check if session expired
        if datetime.utcnow() > captcha_session.expires_at:
            db.session.delete(captcha_session)
            db.session.commit()
            log_api_call('/api/participants/validate-captcha', user_id, giveaway_id, False, 'CAPTCHA_EXPIRED')
            return jsonify({
                'success': False,
                'error': 'Captcha session expired, please try again',
                'error_code': 'CAPTCHA_EXPIRED'
            }), 400
        
        # Validate answer format
        try:
            user_answer = int(user_answer)
        except (ValueError, TypeError):
            log_api_call('/api/participants/validate-captcha', user_id, giveaway_id, False, 'INVALID_ANSWER_FORMAT')
            return jsonify({
                'success': False,
                'error': 'Invalid answer format',
                'error_code': 'INVALID_CAPTCHA_ANSWER'
            }), 400
        
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
                'message': 'Captcha completed and participation confirmed'
            }), 200
        else:
            # Wrong answer - increment attempts
            captcha_session.attempts += 1
            
            if captcha_session.attempts >= captcha_session.max_attempts:
                # Generate new question after 3 attempts
                import random
                a = random.randint(1, 10)
                b = random.randint(1, 10)
                question = f"What is {a} + {b}?"
                answer = a + b
                
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
                    'message': 'New question generated after multiple attempts'
                }), 200
            else:
                db.session.commit()
                
                log_api_call('/api/participants/validate-captcha', user_id, giveaway_id, True, 'INCORRECT_ANSWER')
                return jsonify({
                    'success': True,
                    'captcha_completed': False,
                    'attempts_remaining': captcha_session.max_attempts - captcha_session.attempts,
                    'message': 'Incorrect answer, try again'
                }), 200
                
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass
        log_api_call('/api/participants/validate-captcha', data.get('user_id') if 'data' in locals() else None, data.get('giveaway_id') if 'data' in locals() else None, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Captcha validation failed: {str(e)}',
            'error_code': 'CAPTCHA_VALIDATION_ERROR'
        }), 500

@participants_bot_bp.route('/api/participants/winner-status/<int:user_id>/<int:giveaway_id>', methods=['GET'])
def winner_status_check(user_id, giveaway_id):
    """
    Check if user won a specific giveaway
    Called when user clicks "VIEW RESULTS" button
    """
    try:
        from models import db, Participant
        
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
            'total_winners': total_winners
        }), 200
        
    except Exception as e:
        log_api_call('/api/participants/winner-status', user_id, giveaway_id, False, str(e))
        return jsonify({
            'success': False,
            'error': 'Failed to get winner status',
            'error_code': 'WINNER_STATUS_ERROR'
        }), 500

@participants_bot_bp.route('/api/participants/verify-subscription', methods=['POST'])
def subscription_verification():
    """
    Verify user is subscribed to required channel
    Called during participation process if subscription required
    """
    try:
        from services.telegram_api import telegram_api
        
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
        
        # Get channel info from Channel Service
        try:
            from services.channel_service import channel_service
            channel_info = channel_service.get_channel_info(account_id)
            
            if not channel_info:
                log_api_call('/api/participants/verify-subscription', user_id, None, False, 'CHANNEL_NOT_FOUND')
                return jsonify({
                    'success': False,
                    'error': 'Channel not found',
                    'error_code': 'CHANNEL_NOT_FOUND'
                }), 404
        except Exception as e:
            log_api_call('/api/participants/verify-subscription', user_id, None, False, f'CHANNEL_SERVICE_ERROR: {str(e)}')
            return jsonify({
                'success': False,
                'error': 'Channel service unavailable',
                'error_code': 'SERVICE_UNAVAILABLE'
            }), 500
        
        # Check subscription via Telegram API
        try:
            is_subscribed = telegram_api.check_channel_membership(user_id, channel_info.get('username'))
            
            log_api_call('/api/participants/verify-subscription', user_id, None, True, f'SUBSCRIPTION_STATUS_{is_subscribed}')
            
            response_data = {
                'success': True,
                'is_subscribed': is_subscribed,
                'channel_info': {
                    'username': channel_info.get('username'),
                    'title': channel_info.get('title')
                },
                'verified_at': datetime.utcnow().isoformat()
            }
            
            if not is_subscribed:
                response_data['message'] = 'User is not subscribed to the required channel'
            
            return jsonify(response_data), 200
            
        except Exception as e:
            log_api_call('/api/participants/verify-subscription', user_id, None, False, f'TELEGRAM_API_ERROR: {str(e)}')
            return jsonify({
                'success': False,
                'error': 'Subscription verification failed',
                'error_code': 'VERIFICATION_ERROR'
            }), 500
            
    except Exception as e:
        log_api_call('/api/participants/verify-subscription', data.get('user_id') if 'data' in locals() else None, None, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Subscription verification failed: {str(e)}',
            'error_code': 'SUBSCRIPTION_ERROR'
        }), 500

@participants_bot_bp.route('/api/participants/update-delivery-status', methods=['PUT'])
def delivery_status_update():
    """
    Update message delivery status for analytics
    Called after sending result messages to participants
    """
    try:
        from models import db, Participant
        
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
        delivery_timestamp = data.get('delivery_timestamp', datetime.utcnow().isoformat())
        
        # Validate participant_ids is a list
        if not isinstance(participant_ids, list):
            log_api_call('/api/participants/update-delivery-status', None, None, False, 'INVALID_PARTICIPANT_IDS')
            return jsonify({
                'success': False,
                'error': 'participant_ids must be a list',
                'error_code': 'INVALID_PARTICIPANT_IDS'
            }), 400
        
        # Update delivery status
        updated_count = 0
        failed_count = 0
        
        for participant_id in participant_ids:
            try:
                participant = Participant.query.get(participant_id)
                if participant:
                    participant.message_delivered = delivered
                    participant.delivery_timestamp = datetime.fromisoformat(delivery_timestamp.replace('Z', '+00:00'))
                    updated_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.warning(f"Failed to update participant {participant_id}: {e}")
                failed_count += 1
        
        db.session.commit()
        
        log_api_call('/api/participants/update-delivery-status', None, None, True, f'UPDATED_{updated_count}_FAILED_{failed_count}')
        
        if failed_count == 0:
            return jsonify({
                'success': True,
                'updated_count': updated_count,
                'message': f'Delivery status updated for {updated_count} participants'
            }), 200
        else:
            return jsonify({
                'success': True,
                'updated_count': updated_count,
                'failed_count': failed_count,
                'message': f'Delivery status updated for {updated_count} participants, {failed_count} failed'
            }), 200
            
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass
        log_api_call('/api/participants/update-delivery-status', None, None, False, str(e))
        return jsonify({
            'success': False,
            'error': 'Failed to update delivery status',
            'error_code': 'DELIVERY_UPDATE_ERROR'
        }), 500

