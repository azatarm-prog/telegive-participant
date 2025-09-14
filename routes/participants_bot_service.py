from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import secrets
import logging
import requests
import os

logger = logging.getLogger(__name__)

bot_service_bp = Blueprint('bot_service', __name__)

def log_api_call(endpoint, user_id=None, giveaway_id=None, success=True, error=None):
    """Log all API calls for debugging and analytics"""
    logger.info(f"API: {endpoint} | User: {user_id} | Giveaway: {giveaway_id} | Success: {success} | Error: {error}")

@bot_service_bp.route('/api/participants/captcha-status/<int:user_id>', methods=['GET'])
def get_captcha_status(user_id):
    """
    Check if user has completed captcha globally
    Used by Bot Service to optimize participation flow
    """
    try:
        # Import models within app context to avoid SQLAlchemy issues
        with current_app.app_context():
            from models import db, UserCaptchaRecord
            
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
            'error': f'Failed to get captcha status: {str(e)}',
            'error_code': 'CAPTCHA_STATUS_ERROR'
        }), 500

@bot_service_bp.route('/api/participants/winner-status/<int:user_id>/<int:giveaway_id>', methods=['GET'])
def get_winner_status(user_id, giveaway_id):
    """
    Check if user won the giveaway
    Used for VIEW RESULTS functionality
    """
    try:
        with current_app.app_context():
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
                'total_winners': total_winners,
                'participant_id': participation.id
            }), 200
            
    except Exception as e:
        log_api_call('/api/participants/winner-status', user_id, giveaway_id, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Failed to get winner status: {str(e)}',
            'error_code': 'WINNER_STATUS_ERROR'
        }), 500

@bot_service_bp.route('/api/participants/count/<int:giveaway_id>', methods=['GET'])
def get_participant_count(giveaway_id):
    """
    Get participant count for giveaway
    Used for real-time participant counter
    """
    try:
        with current_app.app_context():
            from models import db, Participant
            
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
            'error': f'Failed to get participant count: {str(e)}',
            'error_code': 'PARTICIPANT_COUNT_ERROR'
        }), 500

@bot_service_bp.route('/api/participants/register-enhanced', methods=['POST'])
def register_participant_enhanced():
    """
    Enhanced participant registration with captcha logic
    Handles both new users (captcha required) and returning users
    """
    try:
        with current_app.app_context():
            from models import db, Participant, UserCaptchaRecord, CaptchaSession
            
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['giveaway_id', 'user_id']
            for field in required_fields:
                if field not in data:
                    log_api_call('/api/participants/register-enhanced', data.get('user_id'), data.get('giveaway_id'), False, f'MISSING_FIELD_{field}')
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
                log_api_call('/api/participants/register-enhanced', user_id, giveaway_id, False, 'DUPLICATE_PARTICIPATION')
                return jsonify({
                    'success': False,
                    'error': 'User already participating in this giveaway',
                    'error_code': 'DUPLICATE_PARTICIPATION'
                }), 409
            
            # Check if user has completed captcha globally
            captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
            
            if not captcha_record or not captcha_record.captcha_completed:
                # New user - generate captcha
                try:
                    from utils.captcha_generator import captcha_generator
                    question, answer = captcha_generator.generate_question()
                except:
                    # Fallback captcha generation
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
                
                log_api_call('/api/participants/register-enhanced', user_id, giveaway_id, True, 'CAPTCHA_REQUIRED')
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
                
                log_api_call('/api/participants/register-enhanced', user_id, giveaway_id, True, 'PARTICIPATION_CONFIRMED')
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
        log_api_call('/api/participants/register-enhanced', data.get('user_id') if 'data' in locals() else None, data.get('giveaway_id') if 'data' in locals() else None, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}',
            'error_code': 'REGISTRATION_ERROR'
        }), 500

@bot_service_bp.route('/api/participants/validate-captcha-enhanced', methods=['POST'])
def validate_captcha_enhanced():
    """
    Enhanced captcha validation with retry logic
    Handle retry logic and participation confirmation
    """
    try:
        with current_app.app_context():
            from models import db, Participant, UserCaptchaRecord, CaptchaSession
            
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['user_id', 'giveaway_id', 'answer', 'session_id']
            for field in required_fields:
                if field not in data:
                    log_api_call('/api/participants/validate-captcha-enhanced', data.get('user_id'), data.get('giveaway_id'), False, f'MISSING_FIELD_{field}')
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
                log_api_call('/api/participants/validate-captcha-enhanced', user_id, giveaway_id, False, 'CAPTCHA_SESSION_NOT_FOUND')
                return jsonify({
                    'success': False,
                    'error': 'Captcha session not found or expired',
                    'error_code': 'CAPTCHA_EXPIRED'
                }), 404
            
            # Check if session expired
            if datetime.utcnow() > captcha_session.expires_at:
                db.session.delete(captcha_session)
                db.session.commit()
                log_api_call('/api/participants/validate-captcha-enhanced', user_id, giveaway_id, False, 'CAPTCHA_EXPIRED')
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
                
                log_api_call('/api/participants/validate-captcha-enhanced', user_id, giveaway_id, True, 'CAPTCHA_COMPLETED')
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
                    try:
                        from utils.captcha_generator import captcha_generator
                        question, answer = captcha_generator.generate_question()
                    except:
                        # Fallback captcha generation
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
                    
                    log_api_call('/api/participants/validate-captcha-enhanced', user_id, giveaway_id, True, 'NEW_QUESTION_GENERATED')
                    return jsonify({
                        'success': True,
                        'captcha_completed': False,
                        'attempts_remaining': 3,
                        'new_question': question,
                        'message': 'New question generated after maximum attempts'
                    }), 200
                else:
                    db.session.commit()
                    
                    log_api_call('/api/participants/validate-captcha-enhanced', user_id, giveaway_id, True, 'INCORRECT_ANSWER')
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
        log_api_call('/api/participants/validate-captcha-enhanced', data.get('user_id') if 'data' in locals() else None, data.get('giveaway_id') if 'data' in locals() else None, False, str(e))
        return jsonify({
            'success': False,
            'error': f'Captcha validation failed: {str(e)}',
            'error_code': 'CAPTCHA_VALIDATION_ERROR'
        }), 500

