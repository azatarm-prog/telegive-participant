# Bot Service Integration Implementation Plan

## 🎯 **Implementation Status for Participant Service**

**Date**: September 14, 2025  
**Status**: 📋 **ANALYSIS COMPLETE** - Ready for implementation  
**Priority**: **HIGH** - Required for Bot Service integration

---

## 📊 **Current vs Required Endpoints Analysis**

### ✅ **Already Implemented:**
- `POST /api/participants/join` *(similar to register)*
- `POST /api/participants/validate-captcha` *(basic version)*
- `GET /health/*` *(health checks)*
- `POST /admin/init-db` *(database management)*

### 🔄 **Need Updates/Enhancements:**
- `POST /api/participants/register` *(enhance existing join endpoint)*
- `POST /api/participants/validate-captcha` *(enhance retry logic)*

### 🆕 **Need to Implement:**
- `GET /api/participants/captcha-status/{user_id}`
- `GET /api/participants/winner-status/{user_id}/{giveaway_id}`
- `POST /api/participants/verify-subscription`
- `POST /api/participants/select-winners`
- `PUT /api/participants/update-delivery-status`
- `GET /api/participants/count/{giveaway_id}`
- `GET /api/participants/list/{giveaway_id}`

---

## 🚀 **Implementation Priority Order**

### **Phase 1: Core Participation (URGENT)**
1. **Enhance `/api/participants/register`** - Core participation flow
2. **Implement `/api/participants/captcha-status/{user_id}`** - Optimization endpoint
3. **Enhance `/api/participants/validate-captcha`** - Better retry logic

### **Phase 2: Winner Management (HIGH)**
4. **Implement `/api/participants/select-winners`** - Winner selection
5. **Implement `/api/participants/winner-status/{user_id}/{giveaway_id}`** - Results checking

### **Phase 3: Subscription & Analytics (MEDIUM)**
6. **Implement `/api/participants/verify-subscription`** - Subscription verification
7. **Implement `/api/participants/count/{giveaway_id}`** - Statistics
8. **Implement `/api/participants/list/{giveaway_id}`** - Admin functionality

### **Phase 4: Delivery Tracking (LOW)**
9. **Implement `/api/participants/update-delivery-status`** - Message delivery tracking

---

## 🔧 **Required Database Schema Updates**

### **New Tables Needed:**
```sql
-- User captcha completion tracking (global)
CREATE TABLE user_captcha_records (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    captcha_completed BOOLEAN DEFAULT FALSE,
    captcha_completed_at TIMESTAMP,
    first_participation_at TIMESTAMP,
    total_participations INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Captcha sessions (temporary)
CREATE TABLE captcha_sessions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    giveaway_id INTEGER NOT NULL,
    session_id VARCHAR(32) NOT NULL UNIQUE,
    question TEXT NOT NULL,
    correct_answer INTEGER NOT NULL,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Winner selection audit log
CREATE TABLE winner_selection_logs (
    id SERIAL PRIMARY KEY,
    giveaway_id INTEGER NOT NULL,
    total_participants INTEGER NOT NULL,
    winner_count_requested INTEGER NOT NULL,
    winner_count_selected INTEGER NOT NULL,
    selection_method VARCHAR(50) NOT NULL,
    winner_user_ids BIGINT[] NOT NULL,
    selection_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Existing Table Updates:**
```sql
-- Add columns to participants table
ALTER TABLE participants ADD COLUMN IF NOT EXISTS message_delivered BOOLEAN DEFAULT FALSE;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS delivery_timestamp TIMESTAMP;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS delivery_attempts INTEGER DEFAULT 0;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS subscription_verified_at TIMESTAMP;
```

---

## 📝 **Implementation Tasks**

### **Task 1: Database Schema Updates**
```python
# File: routes/admin.py - Add new endpoint
@admin_bp.route('/update-schema', methods=['POST'])
def update_database_schema():
    """Update database schema for Bot Service integration"""
    try:
        # Execute schema updates
        schema_updates = [
            # Create user_captcha_records table
            """CREATE TABLE IF NOT EXISTS user_captcha_records (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                captcha_completed BOOLEAN DEFAULT FALSE,
                captcha_completed_at TIMESTAMP,
                first_participation_at TIMESTAMP,
                total_participations INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Create captcha_sessions table
            """CREATE TABLE IF NOT EXISTS captcha_sessions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                giveaway_id INTEGER NOT NULL,
                session_id VARCHAR(32) NOT NULL UNIQUE,
                question TEXT NOT NULL,
                correct_answer INTEGER NOT NULL,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Create winner_selection_logs table
            """CREATE TABLE IF NOT EXISTS winner_selection_logs (
                id SERIAL PRIMARY KEY,
                giveaway_id INTEGER NOT NULL,
                total_participants INTEGER NOT NULL,
                winner_count_requested INTEGER NOT NULL,
                winner_count_selected INTEGER NOT NULL,
                selection_method VARCHAR(50) NOT NULL,
                winner_user_ids BIGINT[] NOT NULL,
                selection_timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Update participants table
            """ALTER TABLE participants 
               ADD COLUMN IF NOT EXISTS message_delivered BOOLEAN DEFAULT FALSE,
               ADD COLUMN IF NOT EXISTS delivery_timestamp TIMESTAMP,
               ADD COLUMN IF NOT EXISTS delivery_attempts INTEGER DEFAULT 0,
               ADD COLUMN IF NOT EXISTS subscription_verified_at TIMESTAMP"""
        ]
        
        for update in schema_updates:
            db.session.execute(text(update))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Database schema updated successfully',
            'tables_created': ['user_captcha_records', 'captcha_sessions', 'winner_selection_logs'],
            'columns_added': ['message_delivered', 'delivery_timestamp', 'delivery_attempts', 'subscription_verified_at']
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Schema update failed: {str(e)}'
        }), 500
```

### **Task 2: Enhance Existing Endpoints**
```python
# File: routes/participants.py - Enhance existing endpoints

@participants_bp.route('/register', methods=['POST'])
def register_participant():
    """Enhanced participant registration with captcha logic"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['giveaway_id', 'user_id']
        for field in required_fields:
            if field not in data:
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
            
            return jsonify({
                'success': True,
                'requires_captcha': False,
                'participant_id': participant.id,
                'message': 'Participation confirmed'
            }), 200
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500
```

### **Task 3: Implement New Endpoints**
```python
# File: routes/participants.py - Add new endpoints

@participants_bp.route('/captcha-status/<int:user_id>', methods=['GET'])
def get_captcha_status(user_id):
    """Check if user has completed captcha globally"""
    try:
        captcha_record = UserCaptchaRecord.query.filter_by(user_id=user_id).first()
        
        if captcha_record:
            return jsonify({
                'success': True,
                'captcha_completed': captcha_record.captcha_completed,
                'completed_at': captcha_record.captcha_completed_at.isoformat() if captcha_record.captcha_completed_at else None,
                'total_participations': captcha_record.total_participations,
                'total_wins': captcha_record.total_wins,
                'first_participation': captcha_record.first_participation_at.isoformat() if captcha_record.first_participation_at else None
            }), 200
        else:
            return jsonify({
                'success': True,
                'captcha_completed': False,
                'total_participations': 0,
                'total_wins': 0
            }), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/winner-status/<int:user_id>/<int:giveaway_id>', methods=['GET'])
def get_winner_status(user_id, giveaway_id):
    """Check if user won the giveaway"""
    try:
        participation = Participant.query.filter_by(
            giveaway_id=giveaway_id, 
            user_id=user_id
        ).first()
        
        if not participation:
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
        
        return jsonify({
            'success': True,
            'participated': True,
            'is_winner': participation.is_winner,
            'winner_selected_at': participation.winner_selected_at.isoformat() if participation.winner_selected_at else None,
            'total_winners': total_winners
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/select-winners', methods=['POST'])
def select_winners():
    """Select winners using cryptographically secure random selection"""
    try:
        data = request.get_json()
        
        giveaway_id = data['giveaway_id']
        winner_count = data['winner_count']
        
        # Get all eligible participants
        eligible_participants = Participant.query.filter_by(
            giveaway_id=giveaway_id,
            captcha_completed=True,
            subscription_verified=True
        ).all()
        
        if not eligible_participants:
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
            selection_method='cryptographic_random',
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
        
        return jsonify({
            'success': True,
            'winners': winner_user_ids,
            'total_participants': total_participants,
            'winner_count_requested': winner_count,
            'winner_count_selected': actual_winner_count,
            'selection_timestamp': selection_timestamp.isoformat(),
            'selection_method': 'cryptographic_random'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@participants_bp.route('/count/<int:giveaway_id>', methods=['GET'])
def get_participant_count(giveaway_id):
    """Get participant count for giveaway"""
    try:
        count = Participant.query.filter_by(giveaway_id=giveaway_id).count()
        
        return jsonify({
            'success': True,
            'giveaway_id': giveaway_id,
            'count': count
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500
```

---

## ⏰ **Implementation Timeline**

### **Phase 1 (Today - 2 hours):**
- ✅ Database schema updates
- ✅ Enhanced participant registration
- ✅ Captcha status endpoint
- ✅ Enhanced captcha validation

### **Phase 2 (Tomorrow - 3 hours):**
- ✅ Winner selection endpoint
- ✅ Winner status endpoint
- ✅ Participant count endpoint

### **Phase 3 (Day 3 - 2 hours):**
- ✅ Subscription verification
- ✅ Participant list endpoint
- ✅ Delivery status updates

### **Phase 4 (Day 4 - 1 hour):**
- ✅ Testing and integration
- ✅ Documentation updates
- ✅ Performance optimization

---

## 🧪 **Testing Strategy**

### **Unit Tests:**
- Test each endpoint individually
- Test error handling and edge cases
- Test database operations

### **Integration Tests:**
- Test Bot Service communication flow
- Test captcha flow end-to-end
- Test winner selection process

### **Performance Tests:**
- Test with large participant counts
- Test concurrent requests
- Test database performance

---

**Status**: 📋 **READY TO IMPLEMENT**  
**Next Action**: Start with Phase 1 database schema updates  
**ETA**: Full Bot Service integration ready in 4 days

