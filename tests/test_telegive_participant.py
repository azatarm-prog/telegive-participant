import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
import json

from app import create_app
from models import db, Participant, UserCaptchaRecord, CaptchaSession, WinnerSelectionLog
from config import TestingConfig

class TestParticipantService:
    
    @pytest.fixture
    def app(self):
        """Create test application"""
        app = create_app('testing')
        app.config.from_object(TestingConfig)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                yield client
                db.drop_all()
    
    @pytest.fixture
    def sample_giveaway(self):
        """Sample giveaway data"""
        return {
            'id': 1,
            'account_id': 1,
            'title': 'Test Giveaway',
            'main_body': 'Test content',
            'winner_count': 2,
            'status': 'active'
        }
    
    @patch('services.telegram_api.telegram_api.check_channel_membership')
    @patch('services.telegive_service.telegive_service.get_giveaway')
    @patch('services.telegive_service.telegive_service.is_giveaway_active')
    def test_register_participation_new_user(self, mock_active, mock_giveaway, mock_membership, client, sample_giveaway):
        """Test participation registration for new user (requires captcha)"""
        mock_active.return_value = True
        mock_giveaway.return_value = sample_giveaway
        mock_membership.return_value = {
            'success': True,
            'is_member': True
        }
        
        response = client.post('/api/participants/register', 
                             json={
                                 'giveaway_id': 1,
                                 'user_id': 123456789,
                                 'username': 'testuser',
                                 'first_name': 'Test',
                                 'last_name': 'User'
                             },
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['requires_captcha'] == True
        assert 'captcha_question' in data
    
    @patch('services.telegram_api.telegram_api.check_channel_membership')
    @patch('services.telegive_service.telegive_service.get_giveaway')
    @patch('services.telegive_service.telegive_service.is_giveaway_active')
    def test_register_participation_returning_user(self, mock_active, mock_giveaway, mock_membership, client, sample_giveaway):
        """Test participation registration for returning user (no captcha)"""
        mock_active.return_value = True
        mock_giveaway.return_value = sample_giveaway
        mock_membership.return_value = {
            'success': True,
            'is_member': True
        }
        
        # Create existing captcha record
        captcha_record = UserCaptchaRecord(
            user_id=123456789,
            captcha_completed=True,
            captcha_completed_at=datetime.utcnow()
        )
        db.session.add(captcha_record)
        db.session.commit()
        
        response = client.post('/api/participants/register',
                             json={
                                 'giveaway_id': 1,
                                 'user_id': 123456789,
                                 'username': 'testuser',
                                 'first_name': 'Test',
                                 'last_name': 'User'
                             },
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['requires_captcha'] == False
        assert data['participation_confirmed'] == True
    
    @patch('services.telegram_api.telegram_api.check_channel_membership')
    @patch('services.telegive_service.telegive_service.is_giveaway_active')
    def test_register_participation_not_subscribed(self, mock_active, mock_membership, client):
        """Test participation registration for non-subscribed user"""
        mock_active.return_value = True
        mock_membership.return_value = {
            'success': True,
            'is_member': False
        }
        
        # Create existing captcha record
        captcha_record = UserCaptchaRecord(
            user_id=123456789,
            captcha_completed=True,
            captcha_completed_at=datetime.utcnow()
        )
        db.session.add(captcha_record)
        db.session.commit()
        
        with patch('services.telegive_service.telegive_service.get_giveaway') as mock_giveaway:
            mock_giveaway.return_value = {'account_id': 1}
            
            response = client.post('/api/participants/register',
                                 json={
                                     'giveaway_id': 1,
                                     'user_id': 123456789,
                                     'username': 'testuser'
                                 },
                                 content_type='application/json')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'not subscribed' in data['error'].lower()
    
    def test_validate_captcha_correct_answer(self, client):
        """Test captcha validation with correct answer"""
        # Create captcha session
        session = CaptchaSession(
            user_id=123456789,
            giveaway_id=1,
            question='What is 5 + 3?',
            correct_answer=8,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(session)
        db.session.commit()
        
        with patch('services.telegive_service.telegive_service.get_giveaway') as mock_giveaway, \
             patch('services.telegram_api.telegram_api.check_channel_membership') as mock_membership:
            
            mock_giveaway.return_value = {'account_id': 1}
            mock_membership.return_value = {
                'success': True,
                'is_member': True
            }
            
            response = client.post('/api/participants/validate-captcha',
                                 json={
                                     'user_id': 123456789,
                                     'giveaway_id': 1,
                                     'answer': 8
                                 },
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == True
            assert data['captcha_completed'] == True
    
    def test_validate_captcha_wrong_answer(self, client):
        """Test captcha validation with wrong answer"""
        # Create captcha session
        session = CaptchaSession(
            user_id=123456789,
            giveaway_id=1,
            question='What is 5 + 3?',
            correct_answer=8,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(session)
        db.session.commit()
        
        response = client.post('/api/participants/validate-captcha',
                             json={
                                 'user_id': 123456789,
                                 'giveaway_id': 1,
                                 'answer': 7
                             },
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['attempts_remaining'] == 2
        assert 'incorrect' in data['error'].lower()
    
    def test_select_winners_success(self, client):
        """Test successful winner selection"""
        # Create participants
        participants = [
            Participant(giveaway_id=1, user_id=111, captcha_completed=True, subscription_verified=True),
            Participant(giveaway_id=1, user_id=222, captcha_completed=True, subscription_verified=True),
            Participant(giveaway_id=1, user_id=333, captcha_completed=True, subscription_verified=True),
            Participant(giveaway_id=1, user_id=444, captcha_completed=True, subscription_verified=True),
            Participant(giveaway_id=1, user_id=555, captcha_completed=True, subscription_verified=True)
        ]
        for p in participants:
            db.session.add(p)
        db.session.commit()
        
        with patch('services.telegive_service.telegive_service.notify_winners_selected') as mock_notify:
            mock_notify.return_value = True
            
            response = client.post('/api/participants/select-winners/1',
                                 json={
                                     'winner_count': 2
                                 },
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == True
            assert len(data['winners']) == 2
            assert data['total_participants'] == 5
    
    def test_get_participant_list(self, client):
        """Test getting participant list for giveaway"""
        # Create participants
        participants = [
            Participant(giveaway_id=1, user_id=111, username='user1', captcha_completed=True),
            Participant(giveaway_id=1, user_id=222, username='user2', captcha_completed=True),
            Participant(giveaway_id=1, user_id=333, username='user3', captcha_completed=False)
        ]
        for p in participants:
            db.session.add(p)
        db.session.commit()
        
        response = client.get('/api/participants/list/1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['participants']) == 3
        assert data['stats']['total'] == 3
        assert data['stats']['captcha_completed'] == 2
    
    def test_get_user_history(self, client):
        """Test getting user participation history"""
        # Create user captcha record
        captcha_record = UserCaptchaRecord(
            user_id=123456789,
            captcha_completed=True,
            total_participations=3,
            total_wins=1
        )
        db.session.add(captcha_record)
        db.session.commit()
        
        with patch('services.telegive_service.telegive_service.get_giveaway') as mock_giveaway:
            mock_giveaway.return_value = {
                'title': 'Test Giveaway',
                'status': 'active'
            }
            
            response = client.get('/api/participants/history/123456789')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['user_stats']['total_participations'] == 3
            assert data['user_stats']['total_wins'] == 1
            assert data['user_stats']['captcha_completed'] == True
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['service'] == 'participant-service'
        assert 'status' in data
    
    def test_invalid_input_validation(self, client):
        """Test input validation for invalid data"""
        # Test invalid user ID
        response = client.post('/api/participants/register',
                             json={
                                 'giveaway_id': 1,
                                 'user_id': 'invalid',
                                 'username': 'testuser'
                             },
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'validation_errors' in data
    
    def test_captcha_session_expiry(self, client):
        """Test captcha session expiry handling"""
        # Create expired captcha session
        session = CaptchaSession(
            user_id=123456789,
            giveaway_id=1,
            question='What is 5 + 3?',
            correct_answer=8,
            expires_at=datetime.utcnow() - timedelta(minutes=1)  # Expired
        )
        db.session.add(session)
        db.session.commit()
        
        response = client.post('/api/participants/validate-captcha',
                             json={
                                 'user_id': 123456789,
                                 'giveaway_id': 1,
                                 'answer': 8
                             },
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'expired' in data['error'].lower()
    
    def test_duplicate_participation(self, client):
        """Test prevention of duplicate participation"""
        # Create existing participant
        participant = Participant(
            giveaway_id=1,
            user_id=123456789,
            captcha_completed=True,
            subscription_verified=True
        )
        db.session.add(participant)
        db.session.commit()
        
        with patch('services.telegive_service.telegive_service.is_giveaway_active') as mock_active:
            mock_active.return_value = True
            
            response = client.post('/api/participants/register',
                                 json={
                                     'giveaway_id': 1,
                                     'user_id': 123456789,
                                     'username': 'testuser'
                                 },
                                 content_type='application/json')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'already participated' in data['error'].lower()

if __name__ == '__main__':
    pytest.main([__file__])

