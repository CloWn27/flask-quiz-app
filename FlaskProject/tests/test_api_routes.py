# tests/test_api_routes.py - API Routes Tests

import pytest
import json
from extensions import db
from database import Game, Player


class TestNetworkInfoAPI:
    """Test network information API."""
    
    def test_network_info_endpoint(self, client):
        """Test network info endpoint returns valid data."""
        response = client.get('/api/network-info')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'local_ip' in data
        assert data['local_ip']  # Should not be empty


class TestHostGameControlAPI:
    """Test host game control API endpoints."""
    
    def test_start_question_unauthorized(self, client, sample_game):
        """Test starting question without host authorization."""
        response = client.post(f'/api/host/{sample_game.pin}/start-question')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['error'] == 'Unauthorized'
    
    def test_start_question_authorized(self, client, app, sample_game, authenticated_host_session):
        """Test starting question with host authorization."""
        with app.app_context():
            response = client.post(f'/api/host/{sample_game.pin}/start-question')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'question_number' in data
            
            # Check game state changed
            game = Game.query.get(sample_game.pin)
            assert game.state == 'playing'
    
    def test_start_question_nonexistent_game(self, client, authenticated_host_session):
        """Test starting question for non-existent game."""
        with client.session_transaction() as sess:
            sess['host_pin'] = '999999'
        
        response = client.post('/api/host/999999/start-question')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_show_results_unauthorized(self, client, sample_game):
        """Test showing results without authorization."""
        response = client.post(f'/api/host/{sample_game.pin}/show-results')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['error'] == 'Unauthorized'
    
    def test_show_results_authorized(self, client, app, sample_game, sample_player, authenticated_host_session):
        """Test showing results with authorization."""
        with app.app_context():
            # Set up game state
            sample_game.state = 'playing'
            sample_player.answers = [{'answer': '4', 'response_time': 5.0}]
            db.session.commit()
            
            response = client.post(f'/api/host/{sample_game.pin}/show-results')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'correct_answer' in data
            assert 'leaderboard_count' in data
    
    def test_next_question_unauthorized(self, client, sample_game):
        """Test advancing to next question without authorization."""
        response = client.post(f'/api/host/{sample_game.pin}/next-question')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['error'] == 'Unauthorized'
    
    def test_next_question_authorized(self, client, app, sample_game, authenticated_host_session):
        """Test advancing to next question with authorization."""
        with app.app_context():
            sample_game.state = 'playing'
            db.session.commit()
            
            response = client.post(f'/api/host/{sample_game.pin}/next-question')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'state' in data
            assert 'question_number' in data
            
            # Check game advanced
            game = Game.query.get(sample_game.pin)
            assert game.current_question == 1
    
    def test_next_question_finishes_game(self, client, app, sample_game, authenticated_host_session):
        """Test advancing past last question finishes game."""
        with app.app_context():
            # Set to last question
            sample_game.state = 'playing'
            sample_game.current_question = len(sample_game.questions) - 1
            db.session.commit()
            
            response = client.post(f'/api/host/{sample_game.pin}/next-question')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['state'] == 'finished'
            assert 'final_leaderboard' in data


class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_malformed_pin(self, client):
        """Test API with malformed PIN."""
        with client.session_transaction() as sess:
            sess['host_pin'] = 'invalid'
        
        response = client.post('/api/host/invalid/start-question')
        
        # Should handle gracefully (might return 403 or 404)
        assert response.status_code in [403, 404]
    
    def test_missing_game_data(self, client, authenticated_host_session):
        """Test API endpoints with missing game data."""
        with client.session_transaction() as sess:
            sess['host_pin'] = '999999'
        
        response = client.post('/api/host/999999/show-results')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestAPIValidation:
    """Test API input validation."""
    
    def test_pin_validation_in_routes(self, client):
        """Test that routes validate PIN format."""
        invalid_pins = ['12345', '1234567', 'abcdef', '12345a']
        
        for pin in invalid_pins:
            with client.session_transaction() as sess:
                sess['host_pin'] = pin
            
            response = client.post(f'/api/host/{pin}/start-question')
            # Should return error for invalid PIN format
            assert response.status_code in [400, 403, 404]
    
    def test_session_security(self, client, sample_game):
        """Test that session validation works correctly."""
        # Try to access game with wrong PIN in session
        with client.session_transaction() as sess:
            sess['host_pin'] = '111111'  # Wrong PIN
        
        response = client.post(f'/api/host/{sample_game.pin}/start-question')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['error'] == 'Unauthorized'


class TestAPIContentType:
    """Test API content type handling."""
    
    def test_json_response_format(self, client):
        """Test that API returns proper JSON."""
        response = client.get('/api/network-info')
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        # Should be valid JSON
        data = json.loads(response.data)
        assert isinstance(data, dict)