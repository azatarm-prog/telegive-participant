from flask import Blueprint, request, jsonify
from datetime import datetime
from models import db, CaptchaSession, UserCaptchaRecord, Participant
from utils.captcha_generator import captcha_generator
from utils.validation import input_validator

captcha_bp = Blueprint('captcha', __name__)

@captcha_bp.route('/api/participants/validate-captcha', methods=['POST'])
def validate_captcha():
    """Validate captcha answer"""
    try:
        data = request.get_json()
        
        # Validate input
        validation = input_validator.validate_captcha_request(data)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'error': 'Invalid input data',
                'validation_errors': validation['errors']
            }), 400
        
        validated_data = validation['validated_data']
        user_id = validated_data['user_id']
        giveaway_id = validated_data['giveaway_id']
        answer = validated_data['answer']
        
        # Find active captcha session
        captcha_session = CaptchaSession.query.filter_by(
            user_id=user_id,
            giveaway_id=giveaway_id,
            completed=False
        ).order_by(CaptchaSession.created_at.desc()).first()
        
        if not captcha_session:
            return jsonify({
                'success': False,
                'error': 'No active captcha session found',
                'error_code': 'CAPTCHA_SESSION_NOT_FOUND'
            }), 404
        
        # Check if session is expired
        if captcha_session.is_expired():
            return jsonify({
                'success': False,
                'error': 'Captcha session has expired',
                'error_code': 'CAPTCHA_EXPIRED'
            }), 400
        
        # Check if user can still attempt
        if not captcha_session.can_attempt():
            return jsonify({
                'success': False,
                'error': 'Maximum attempts exceeded',
                'error_code': 'CAPTCHA_ATTEMPTS_EXCEEDED'
            }), 400
        
        # Increment attempts
        captcha_session.increment_attempts()
        
        # Validate answer
        is_correct = captcha_generator.validate_answer(str(answer), captcha_session.correct_answer)
        
        if is_correct:
            # Mark session as completed
            captcha_session.mark_completed()
            
            # Update or create user captcha record
            captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
            if captcha_record:
                if not captcha_record.captcha_completed:
                    captcha_record.captcha_completed = True
                    captcha_record.captcha_completed_at = datetime.utcnow()
            else:
                captcha_record = UserCaptchaRecord(
                    user_id=user_id,
                    captcha_completed=True,
                    captcha_completed_at=datetime.utcnow(),
                    total_participations=0
                )
                db.session.add(captcha_record)
            
            db.session.commit()
            
            # Now proceed with participation registration
            # This is similar to the registration logic but without captcha check
            from services.telegive_service import telegive_service
            from utils.subscription_checker import subscription_checker
            
            # Verify subscription
            giveaway = telegive_service.get_giveaway(giveaway_id)
            if not giveaway:
                return jsonify({
                    'success': False,
                    'error': 'Giveaway not found',
                    'error_code': 'GIVEAWAY_NOT_FOUND'
                }), 404
            
            account_id = giveaway.get('account_id')
            subscription_result = subscription_checker.verify_subscription(user_id, account_id)
            
            if not subscription_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': subscription_result.get('error', 'Subscription verification failed'),
                    'error_code': subscription_result.get('error_code', 'SUBSCRIPTION_ERROR')
                }), 400
            
            if not subscription_result.get('is_subscribed'):
                return jsonify({
                    'success': False,
                    'error': 'User is not subscribed to the required channel',
                    'error_code': 'USER_NOT_SUBSCRIBED',
                    'channel_info': subscription_result.get('channel_info')
                }), 400
            
            # Check if user already participated
            existing_participant = Participant.query.filter_by(
                giveaway_id=giveaway_id,
                user_id=user_id
            ).first()
            
            if existing_participant:
                return jsonify({
                    'success': True,
                    'captcha_completed': True,
                    'participation_confirmed': True,
                    'participant_id': existing_participant.id,
                    'note': 'User already participated'
                })
            
            # Create participant record
            participant = Participant(
                giveaway_id=giveaway_id,
                user_id=user_id,
                captcha_completed=True,
                subscription_verified=True,
                subscription_verified_at=datetime.utcnow()
            )
            
            db.session.add(participant)
            
            # Update user captcha record participation count
            captcha_record.total_participations += 1
            captcha_record.last_participation_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'captcha_completed': True,
                'participation_confirmed': True,
                'participant_id': participant.id
            })
        
        else:
            # Wrong answer
            db.session.commit()
            
            attempts_remaining = captcha_session.max_attempts - captcha_session.attempts
            
            if attempts_remaining <= 0:
                # Generate new question after max attempts
                new_captcha_data = captcha_generator.generate_captcha_data()
                
                # Create new session
                new_session = CaptchaSession.create_session(
                    user_id=user_id,
                    giveaway_id=giveaway_id,
                    question=new_captcha_data['question'],
                    correct_answer=new_captcha_data['correct_answer'],
                    timeout_minutes=new_captcha_data['timeout_minutes']
                )
                
                db.session.add(new_session)
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'captcha_completed': False,
                    'error': 'Maximum attempts exceeded. New question generated.',
                    'attempts_remaining': new_captcha_data['max_attempts'],
                    'new_question': new_captcha_data['question']
                })
            else:
                return jsonify({
                    'success': False,
                    'captcha_completed': False,
                    'error': 'Incorrect answer',
                    'attempts_remaining': attempts_remaining
                })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Captcha validation failed: {str(e)}',
            'error_code': 'CAPTCHA_VALIDATION_ERROR'
        }), 500

@captcha_bp.route('/api/participants/captcha-status/<int:user_id>', methods=['GET'])
def get_captcha_status(user_id):
    """Check if user has completed captcha globally"""
    try:
        # Validate user_id
        user_validation = input_validator.validate_user_id(user_id)
        if not user_validation['valid']:
            return jsonify({
                'success': False,
                'error': user_validation['error'],
                'error_code': user_validation['error_code']
            }), 400
        
        user_id = user_validation['value']
        
        # Get user captcha record
        captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
        
        if not captcha_record:
            return jsonify({
                'success': True,
                'captcha_completed': False,
                'completed_at': None,
                'total_participations': 0,
                'total_wins': 0
            })
        
        return jsonify({
            'success': True,
            'captcha_completed': captcha_record.captcha_completed,
            'completed_at': captcha_record.captcha_completed_at.isoformat() if captcha_record.captcha_completed_at else None,
            'total_participations': captcha_record.total_participations,
            'total_wins': captcha_record.total_wins
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get captcha status: {str(e)}',
            'error_code': 'CAPTCHA_STATUS_ERROR'
        }), 500

@captcha_bp.route('/api/participants/generate-captcha', methods=['POST'])
def generate_captcha():
    """Generate a new captcha question for a user"""
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        giveaway_id = data.get('giveaway_id')
        
        # Validate inputs
        user_validation = input_validator.validate_user_id(user_id)
        if not user_validation['valid']:
            return jsonify({
                'success': False,
                'error': user_validation['error'],
                'error_code': user_validation['error_code']
            }), 400
        
        giveaway_validation = input_validator.validate_giveaway_id(giveaway_id)
        if not giveaway_validation['valid']:
            return jsonify({
                'success': False,
                'error': giveaway_validation['error'],
                'error_code': giveaway_validation['error_code']
            }), 400
        
        user_id = user_validation['value']
        giveaway_id = giveaway_validation['value']
        
        # Check if user already has captcha completed globally
        captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
        if captcha_record and captcha_record.captcha_completed:
            return jsonify({
                'success': False,
                'error': 'User has already completed captcha globally',
                'error_code': 'CAPTCHA_ALREADY_COMPLETED'
            }), 400
        
        # Generate new captcha
        captcha_data = captcha_generator.generate_captcha_data()
        
        # Create captcha session
        captcha_session = CaptchaSession.create_session(
            user_id=user_id,
            giveaway_id=giveaway_id,
            question=captcha_data['question'],
            correct_answer=captcha_data['correct_answer'],
            timeout_minutes=captcha_data['timeout_minutes']
        )
        
        db.session.add(captcha_session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'captcha_question': captcha_data['question'],
            'captcha_session_id': f"sess_{captcha_session.id}",
            'attempts_remaining': captcha_data['max_attempts'],
            'expires_at': captcha_session.expires_at.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to generate captcha: {str(e)}',
            'error_code': 'CAPTCHA_GENERATION_ERROR'
        }), 500

@captcha_bp.route('/api/participants/captcha-sessions/cleanup', methods=['POST'])
def cleanup_expired_sessions():
    """Cleanup expired captcha sessions"""
    try:
        # Delete expired sessions
        expired_sessions = CaptchaSession.query.filter(
            CaptchaSession.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired_sessions)
        
        for session in expired_sessions:
            db.session.delete(session)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'cleaned_sessions': count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to cleanup sessions: {str(e)}',
            'error_code': 'CLEANUP_ERROR'
        }), 500

