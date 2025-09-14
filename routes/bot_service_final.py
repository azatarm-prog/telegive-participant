from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import secrets
import logging
import requests
import os

logger = logging.getLogger(__name__)

bot_service_final_bp = Blueprint('bot_service_final', __name__)

def log_api_call(endpoint, user_id=None, giveaway_id=None, success=True, error=None):
    """Log all API calls for debugging and analytics"""
    logger.info(f"API: {endpoint} | User: {user_id} | Giveaway: {giveaway_id} | Success: {success} | Error: {error}")

@bot_service_final_bp.route('/api/v2/participants/captcha-status/<int:user_id>', methods=['GET'])
def get_captcha_status_v2(user_id):
    """
    Check if user has completed captcha globally
    Used by Bot Service to optimize participation flow
    """
    try:
        # Import models and use proper app context
        from models import db, UserCaptchaRecord
        
        captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
        
        if captcha_record:
            log_api_call('/api/v2/participants/captcha-status', user_id, None, True, 'STATUS_FOUND')
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
            log_api_call('/api/v2/participants/captcha-status', user_id, None, True, 'NEW_USER')
            return jsonify({
                'success': True,
                'captcha_completed': False,
                'total_participations': 0,
                'total_wins': 0
            }), 200
            
    except Exception as e:
        log_api_call('/api/v2/participants/captcha-status', user_id, None, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Failed to get captcha status: {str(e)}',
            'error_code': 'CAPTCHA_STATUS_ERROR'
        }), 500

@bot_service_final_bp.route('/api/v2/participants/winner-status/<int:user_id>/<int:giveaway_id>', methods=['GET'])
def get_winner_status_v2(user_id, giveaway_id):
    """
    Check if user won the giveaway
    Used for VIEW RESULTS functionality
    """
    try:
        from models import db, Participant
        
        # Check if user participated
        participation = Participant.query.filter_by(
            giveaway_id=giveaway_id, 
            user_id=user_id
        ).first()
        
        if not participation:
            log_api_call('/api/v2/participants/winner-status', user_id, giveaway_id, True, 'USER_NOT_PARTICIPATED')
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
        
        log_api_call('/api/v2/participants/winner-status', user_id, giveaway_id, True, f'WINNER_STATUS_{participation.is_winner}')
        return jsonify({
            'success': True,
            'participated': True,
            'is_winner': participation.is_winner,
            'winner_selected_at': participation.winner_selected_at.isoformat() if participation.winner_selected_at else None,
            'total_winners': total_winners,
            'participant_id': participation.id
        }), 200
        
    except Exception as e:
        log_api_call('/api/v2/participants/winner-status', user_id, giveaway_id, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Failed to get winner status: {str(e)}',
            'error_code': 'WINNER_STATUS_ERROR'
        }), 500

@bot_service_final_bp.route('/api/v2/participants/count/<int:giveaway_id>', methods=['GET'])
def get_participant_count_v2(giveaway_id):
    """
    Get participant count for giveaway
    Used for real-time participant counter
    """
    try:
        from models import db, Participant
        
        count = Participant.query.filter_by(giveaway_id=giveaway_id).count()
        
        log_api_call('/api/v2/participants/count', None, giveaway_id, True, f'COUNT_{count}')
        return jsonify({
            'success': True,
            'giveaway_id': giveaway_id,
            'count': count
        }), 200
        
    except Exception as e:
        log_api_call('/api/v2/participants/count', None, giveaway_id, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Failed to get participant count: {str(e)}',
            'error_code': 'PARTICIPANT_COUNT_ERROR'
        }), 500

@bot_service_final_bp.route('/api/v2/participants/register', methods=['POST'])
def register_participant_v2():
    """
    Enhanced participant registration with captcha logic
    Handles both new users (captcha required) and returning users
    """
    try:
        from models import db, Participant, UserCaptchaRecord, CaptchaSession
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['giveaway_id', 'user_id']
        for field in required_fields:
            if field not in data:
                log_api_call('/api/v2/participants/register', data.get('user_id'), data.get('giveaway_id'), False, f'MISSING_FIELD_{field}')
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
            log_api_call('/api/v2/participants/register', user_id, giveaway_id, False, 'DUPLICATE_PARTICIPATION')
            return jsonify({
                'success': False,
                'error': 'User already participating in this giveaway',
                'error_code': 'DUPLICATE_PARTICIPATION'
            }), 409
        
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
            
            log_api_call('/api/v2/participants/register', user_id, giveaway_id, True, 'CAPTCHA_REQUIRED')
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
            
            log_api_call('/api/v2/participants/register', user_id, giveaway_id, True, 'PARTICIPATION_CONFIRMED')
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
        log_api_call('/api/v2/participants/register', data.get('user_id') if 'data' in locals() else None, data.get('giveaway_id') if 'data' in locals() else None, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}',
            'error_code': 'REGISTRATION_ERROR'
        }), 500

@bot_service_final_bp.route('/api/v2/participants/validate-captcha', methods=['POST'])
def validate_captcha_v2():
    """
    Enhanced captcha validation with retry logic
    Handle retry logic and participation confirmation
    """
    try:
        from models import db, Participant, UserCaptchaRecord, CaptchaSession
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'giveaway_id', 'answer', 'session_id']
        for field in required_fields:
            if field not in data:
                log_api_call('/api/v2/participants/validate-captcha', data.get('user_id'), data.get('giveaway_id'), False, f'MISSING_FIELD_{field}')
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
            log_api_call('/api/v2/participants/validate-captcha', user_id, giveaway_id, False, 'CAPTCHA_SESSION_NOT_FOUND')
            return jsonify({
                'success': False,
                'error': 'Captcha session not found or expired',
                'error_code': 'CAPTCHA_EXPIRED'
            }), 404
        
        # Check if session expired
        if datetime.utcnow() > captcha_session.expires_at:
            db.session.delete(captcha_session)
            db.session.commit()
            log_api_call('/api/v2/participants/validate-captcha', user_id, giveaway_id, False, 'CAPTCHA_EXPIRED')
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
            
            log_api_call('/api/v2/participants/validate-captcha', user_id, giveaway_id, True, 'CAPTCHA_COMPLETED')
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
                
                log_api_call('/api/v2/participants/validate-captcha', user_id, giveaway_id, True, 'NEW_QUESTION_GENERATED')
                return jsonify({
                    'success': True,
                    'captcha_completed': False,
                    'attempts_remaining': 3,
                    'new_question': question,
                    'message': 'New question generated after maximum attempts'
                }), 200
            else:
                db.session.commit()
                
                log_api_call('/api/v2/participants/validate-captcha', user_id, giveaway_id, True, 'INCORRECT_ANSWER')
                return jsonify({
                    'success': True,
                    'captcha_completed': False,
                    'attempts_remaining': captcha_session.max_attempts - captcha_session.attempts,
                    'message': f'Incorrect answer. {captcha_session.max_attempts - captcha_session.attempts} attempts remaining.'
                }), 200
                
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass
        log_api_call('/api/v2/participants/validate-captcha', data.get('user_id') if 'data' in locals() else None, data.get('giveaway_id') if 'data' in locals() else None, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Captcha validation failed: {str(e)}',
            'error_code': 'CAPTCHA_VALIDATION_ERROR'
        }), 500

@bot_service_final_bp.route('/api/v2/participants/select-winners', methods=['POST'])
def select_winners_v2():
    """
    Select winners using cryptographically secure random selection
    Called by Giveaway Service when finishing giveaway
    """
    try:
        from models import db, Participant, UserCaptchaRecord, WinnerSelectionLog
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['giveaway_id', 'winner_count']
        for field in required_fields:
            if field not in data:
                log_api_call('/api/v2/participants/select-winners', None, data.get('giveaway_id'), False, f'MISSING_FIELD_{field}')
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
            log_api_call('/api/v2/participants/select-winners', None, giveaway_id, False, 'NO_PARTICIPANTS')
            return jsonify({
                'success': False,
                'error': 'No eligible participants found',
                'error_code': 'NO_PARTICIPANTS'
            }), 400
        
        total_participants = len(eligible_participants)
        actual_winner_count = min(winner_count, total_participants)
        
        # Perform cryptographically secure selection
        participant_ids = [p.id for p in eligible_participants]
        selected_indices = set()
        
        while len(selected_indices) < actual_winner_count:
            random_index = secrets.randbelow(len(participant_ids))
            selected_indices.add(random_index)
        
        selected_ids = [participant_ids[i] for i in selected_indices]
        
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
        
        log_api_call('/api/v2/participants/select-winners', None, giveaway_id, True, f'SELECTED_{actual_winner_count}_WINNERS')
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
        try:
            db.session.rollback()
        except:
            pass
        log_api_call('/api/v2/participants/select-winners', None, data.get('giveaway_id') if 'data' in locals() else None, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Winner selection failed: {str(e)}',
            'error_code': 'WINNER_SELECTION_ERROR'
        }), 500

@bot_service_final_bp.route('/api/v2/participants/list/<int:giveaway_id>', methods=['GET'])
def get_participant_list_v2(giveaway_id):
    """
    Get paginated participant list for giveaway
    Used by Dashboard Service for participant management
    """
    try:
        from models import db, Participant
        
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        # Limit maximum page size
        limit = min(limit, 100)
        
        participants_query = Participant.query.filter_by(giveaway_id=giveaway_id)
        total_count = participants_query.count()
        
        participants = participants_query.offset((page - 1) * limit).limit(limit).all()
        
        participant_list = [p.to_dict() for p in participants]
        
        log_api_call('/api/v2/participants/list', None, giveaway_id, True, f'PAGE_{page}_LIMIT_{limit}')
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
        log_api_call('/api/v2/participants/list', None, giveaway_id, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Failed to get participant list: {str(e)}',
            'error_code': 'PARTICIPANT_LIST_ERROR'
        }), 500

