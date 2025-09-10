from flask import Blueprint, request, jsonify
from datetime import datetime
from models import db, Participant, UserCaptchaRecord, WinnerSelectionLog
from services.telegive_service import telegive_service
from utils.captcha_generator import captcha_generator
from utils.winner_selection import winner_selector
from utils.subscription_checker import subscription_checker
from utils.validation import input_validator

participants_bp = Blueprint('participants', __name__)

@participants_bp.route('/api/participants/register', methods=['POST'])
def register_participation():
    """Register user participation in giveaway"""
    try:
        data = request.get_json()
        
        # Validate input
        validation = input_validator.validate_participation_request(data)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'error': 'Invalid input data',
                'validation_errors': validation['errors']
            }), 400
        
        validated_data = validation['validated_data']
        giveaway_id = validated_data['giveaway_id']
        user_id = validated_data['user_id']
        
        # Check if giveaway is active
        if not telegive_service.is_giveaway_active(giveaway_id):
            return jsonify({
                'success': False,
                'error': 'Giveaway is not active',
                'error_code': 'GIVEAWAY_NOT_ACTIVE'
            }), 400
        
        # Check if user already participated
        existing_participant = Participant.query.filter_by(
            giveaway_id=giveaway_id,
            user_id=user_id
        ).first()
        
        if existing_participant:
            return jsonify({
                'success': False,
                'error': 'User already participated in this giveaway',
                'error_code': 'ALREADY_PARTICIPATED'
            }), 400
        
        # Check if user has completed captcha globally
        captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
        
        if not captcha_record or not captcha_record.captcha_completed:
            # User needs to complete captcha first
            captcha_data = captcha_generator.generate_captcha_data()
            
            # Create captcha session
            from models.captcha_session import CaptchaSession
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
                'requires_captcha': True,
                'captcha_question': captcha_data['question'],
                'captcha_session_id': f"sess_{captcha_session.id}",
                'attempts_remaining': captcha_data['max_attempts']
            })
        
        # User has completed captcha, verify subscription
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
        
        # Create participant record
        participant = Participant(
            giveaway_id=giveaway_id,
            user_id=user_id,
            username=validated_data.get('username'),
            first_name=validated_data.get('first_name'),
            last_name=validated_data.get('last_name'),
            captcha_completed=True,
            subscription_verified=True,
            subscription_verified_at=datetime.utcnow()
        )
        
        db.session.add(participant)
        
        # Update user captcha record
        if captcha_record:
            captcha_record.total_participations += 1
            captcha_record.last_participation_at = datetime.utcnow()
        else:
            captcha_record = UserCaptchaRecord(
                user_id=user_id,
                captcha_completed=True,
                captcha_completed_at=datetime.utcnow(),
                total_participations=1
            )
            db.session.add(captcha_record)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'requires_captcha': False,
            'participation_confirmed': True,
            'participant_id': participant.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}',
            'error_code': 'REGISTRATION_ERROR'
        }), 500

@participants_bp.route('/api/participants/list/<int:giveaway_id>', methods=['GET'])
def get_participant_list(giveaway_id):
    """Get participant list for giveaway"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        # Validate giveaway_id
        giveaway_validation = input_validator.validate_giveaway_id(giveaway_id)
        if not giveaway_validation['valid']:
            return jsonify({
                'success': False,
                'error': giveaway_validation['error'],
                'error_code': giveaway_validation['error_code']
            }), 400
        
        # Get participants with pagination
        participants_query = Participant.query.filter_by(giveaway_id=giveaway_id)
        total = participants_query.count()
        
        participants = participants_query.offset((page - 1) * limit).limit(limit).all()
        
        # Calculate statistics
        stats = {
            'total': total,
            'captcha_completed': participants_query.filter_by(captcha_completed=True).count(),
            'subscription_verified': participants_query.filter_by(subscription_verified=True).count(),
            'winners': participants_query.filter_by(is_winner=True).count()
        }
        
        return jsonify({
            'success': True,
            'participants': [p.to_dict() for p in participants],
            'stats': stats,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get participant list: {str(e)}',
            'error_code': 'LIST_ERROR'
        }), 500

@participants_bp.route('/api/participants/select-winners/<int:giveaway_id>', methods=['POST'])
def select_winners(giveaway_id):
    """Select winners for giveaway"""
    try:
        data = request.get_json()
        
        # Validate giveaway_id
        giveaway_validation = input_validator.validate_giveaway_id(giveaway_id)
        if not giveaway_validation['valid']:
            return jsonify({
                'success': False,
                'error': giveaway_validation['error'],
                'error_code': giveaway_validation['error_code']
            }), 400
        
        # Validate winner_count
        winner_count = data.get('winner_count', 1)
        winner_validation = input_validator.validate_winner_count(winner_count)
        if not winner_validation['valid']:
            return jsonify({
                'success': False,
                'error': winner_validation['error'],
                'error_code': winner_validation['error_code']
            }), 400
        
        winner_count = winner_validation['value']
        
        # Get eligible participants
        eligible_participants = Participant.query.filter_by(
            giveaway_id=giveaway_id,
            captcha_completed=True,
            subscription_verified=True
        ).all()
        
        if len(eligible_participants) == 0:
            return jsonify({
                'success': False,
                'error': 'No eligible participants found',
                'error_code': 'INSUFFICIENT_PARTICIPANTS'
            }), 400
        
        if winner_count > len(eligible_participants):
            winner_count = len(eligible_participants)
        
        # Extract user IDs for selection
        participant_user_ids = [p.user_id for p in eligible_participants]
        
        # Select winners
        selection_result = winner_selector.select_winners(participant_user_ids, winner_count)
        selected_user_ids = selection_result['winners']
        
        # Update participant records
        winners = []
        for user_id in selected_user_ids:
            participant = next(p for p in eligible_participants if p.user_id == user_id)
            participant.is_winner = True
            participant.winner_selected_at = datetime.utcnow()
            
            winners.append({
                'user_id': participant.user_id,
                'username': participant.username,
                'first_name': participant.first_name,
                'participant_id': participant.id
            })
        
        # Create winner selection log
        selection_log = WinnerSelectionLog.create_log(
            giveaway_id=giveaway_id,
            total_participants=len(eligible_participants),
            winner_count_requested=data.get('winner_count', 1),
            selected_user_ids=selected_user_ids,
            selection_method=selection_result['selection_method'],
            selection_seed=selection_result.get('selection_seed')
        )
        
        db.session.add(selection_log)
        
        # Update user captcha records for winners
        for user_id in selected_user_ids:
            captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
            if captcha_record:
                captcha_record.total_wins += 1
        
        db.session.commit()
        
        # Notify giveaway service
        telegive_service.notify_winners_selected(giveaway_id, winners)
        
        return jsonify({
            'success': True,
            'winners': winners,
            'total_participants': len(eligible_participants),
            'selection_method': selection_result['selection_method'],
            'selection_timestamp': selection_result['selection_timestamp']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Winner selection failed: {str(e)}',
            'error_code': 'SELECTION_ERROR'
        }), 500

@participants_bp.route('/api/participants/history/<int:user_id>', methods=['GET'])
def get_user_history(user_id):
    """Get user participation history"""
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
                'user_stats': {
                    'user_id': user_id,
                    'captcha_completed': False,
                    'total_participations': 0,
                    'total_wins': 0,
                    'first_participation': None,
                    'last_participation': None
                },
                'recent_participations': []
            })
        
        # Get recent participations
        recent_participations = Participant.query.filter_by(user_id=user_id)\
            .order_by(Participant.participated_at.desc())\
            .limit(10).all()
        
        participations_data = []
        for participation in recent_participations:
            giveaway = telegive_service.get_giveaway(participation.giveaway_id)
            participations_data.append({
                'giveaway_id': participation.giveaway_id,
                'giveaway_title': giveaway.get('title', 'Unknown Giveaway') if giveaway else 'Unknown Giveaway',
                'participated_at': participation.participated_at.isoformat() if participation.participated_at else None,
                'is_winner': participation.is_winner,
                'giveaway_status': giveaway.get('status', 'unknown') if giveaway else 'unknown'
            })
        
        return jsonify({
            'success': True,
            'user_stats': captcha_record.to_dict(),
            'recent_participations': participations_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get user history: {str(e)}',
            'error_code': 'HISTORY_ERROR'
        }), 500

@participants_bp.route('/api/participants/verify-subscription', methods=['POST'])
def verify_subscription():
    """Verify user subscription to channel"""
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        account_id = data.get('account_id')
        
        # Validate inputs
        user_validation = input_validator.validate_user_id(user_id)
        if not user_validation['valid']:
            return jsonify({
                'success': False,
                'error': user_validation['error'],
                'error_code': user_validation['error_code']
            }), 400
        
        if not account_id:
            return jsonify({
                'success': False,
                'error': 'Account ID is required',
                'error_code': 'MISSING_ACCOUNT_ID'
            }), 400
        
        # Verify subscription
        result = subscription_checker.verify_subscription(user_validation['value'], account_id)
        
        if result.get('success'):
            result['verified_at'] = datetime.utcnow().isoformat()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Subscription verification failed: {str(e)}',
            'error_code': 'VERIFICATION_ERROR'
        }), 500

@participants_bp.route('/api/participants/update-delivery-status', methods=['PUT'])
def update_delivery_status():
    """Update message delivery status"""
    try:
        data = request.get_json()
        
        participant_ids = data.get('participant_ids', [])
        delivered = data.get('delivered', False)
        delivery_timestamp = data.get('delivery_timestamp')
        
        if not participant_ids:
            return jsonify({
                'success': False,
                'error': 'Participant IDs are required',
                'error_code': 'MISSING_PARTICIPANT_IDS'
            }), 400
        
        # Parse delivery timestamp
        if delivery_timestamp:
            try:
                delivery_timestamp = datetime.fromisoformat(delivery_timestamp.replace('Z', '+00:00'))
            except ValueError:
                delivery_timestamp = datetime.utcnow()
        else:
            delivery_timestamp = datetime.utcnow()
        
        # Update participants
        updated_count = 0
        failed_updates = []
        
        for participant_id in participant_ids:
            try:
                participant = Participant.query.get(participant_id)
                if participant:
                    participant.message_delivered = delivered
                    participant.delivery_timestamp = delivery_timestamp
                    participant.delivery_attempts += 1
                    updated_count += 1
                else:
                    failed_updates.append({
                        'participant_id': participant_id,
                        'error': 'Participant not found'
                    })
            except Exception as e:
                failed_updates.append({
                    'participant_id': participant_id,
                    'error': str(e)
                })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'failed_updates': failed_updates
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update delivery status: {str(e)}',
            'error_code': 'UPDATE_ERROR'
        }), 500

