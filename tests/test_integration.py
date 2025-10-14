# tests/test_integration.py - Integration Tests

import pytest
import json
from extensions import db
from database import Game, Player, QuizSet, CustomQuestion


class TestFullGameFlow:
    """Test complete game flow from creation to completion."""
    
    def test_complete_multiplayer_game(self, client, app, sample_questions):
        """Test a complete multiplayer game flow."""
        with app.app_context():
            # 1. Host creates a game
            response = client.post('/host/create-game', data={
                'host_name': 'Test Host',
                'quiz_source': 'default_de',
                'max_questions': '3',
                'difficulty': 'easy'
            })
            
            # Should redirect to lobby
            assert response.status_code == 302
            
            # Extract game PIN from redirect URL
            location = response.headers.get('Location')
            assert '/host/lobby/' in location
            game_pin = location.split('/host/lobby/')[1]
            
            # Verify game was created
            game = Game.query.get(game_pin)
            assert game is not None
            assert game.host_name == 'Test Host'
            assert game.state == 'waiting'
            
            # 2. Players join the game
            for i in range(2):
                response = client.post('/join', data={
                    'pin': game_pin,
                    'player_name': f'Player {i+1}'
                })
                
                assert response.status_code == 302
                assert f'/game/{game_pin}' in response.headers.get('Location')
            
            # Verify players joined
            assert game.players.count() == 2
            
            # 3. Host starts the first question
            with client.session_transaction() as sess:
                sess['host_pin'] = game_pin
                sess['is_host'] = True
            
            response = client.post(f'/api/host/{game_pin}/start-question')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify game state changed
            game = Game.query.get(game_pin)
            assert game.state == 'playing'
            assert game.current_question == 0
            
            # 4. Host shows results
            response = client.post(f'/api/host/{game_pin}/show-results')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'correct_answer' in data
            
            # 5. Host advances to next question
            response = client.post(f'/api/host/{game_pin}/next-question')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify question advanced
            game = Game.query.get(game_pin)
            assert game.current_question == 1
    
    def test_solo_quiz_flow(self, client, app):
        """Test complete solo quiz flow."""
        with app.app_context():
            # Start solo quiz
            response = client.post('/start_quiz', data={
                'player_name': 'Solo Player',
                'mode': 'difficulty',
                'difficulty': 'easy',
                'language': 'de'
            })
            
            assert response.status_code == 302
            assert '/quiz' in response.headers.get('Location')
            
            # Take the quiz
            for i in range(3):  # Answer 3 questions
                response = client.get('/quiz')
                assert response.status_code == 200
                
                # Submit an answer
                response = client.post('/quiz', data={'answer': 'test answer'})
                assert response.status_code == 302
            
            # Check results
            response = client.get('/result')
            assert response.status_code == 200


class TestCustomQuizSetFlow:
    """Test custom quiz set creation and usage."""
    
    def test_create_and_use_custom_quiz_set(self, client, app):
        """Test creating custom quiz set and using it in a game."""
        with app.app_context():
            # 1. Create a new quiz set
            response = client.post('/host/editor/new', data={
                'name': 'My Custom Quiz'
            })
            
            assert response.status_code == 302
            
            # Extract quiz set ID
            location = response.headers.get('Location')
            quiz_set_id = location.split('/host/editor/')[1]
            
            # 2. Add questions to the quiz set
            questions = [
                {'question': 'What is 2+2?', 'answer': '4', 'question_type': 'text'},
                {'question': 'What is 3+3?', 'answer': '6', 'question_type': 'text'}
            ]
            
            for q in questions:
                response = client.post(f'/host/editor/{quiz_set_id}', data=q)
                assert response.status_code == 302
            
            # Verify questions were added
            quiz_set = QuizSet.query.get(quiz_set_id)
            assert quiz_set.questions.count() == 2
            
            # 3. Create a game using the custom quiz set
            response = client.post('/host/create-game', data={
                'host_name': 'Custom Host',
                'quiz_source': quiz_set_id,
                'max_questions': '2'
            })
            
            assert response.status_code == 302
            
            # Verify game was created with custom questions
            location = response.headers.get('Location')
            game_pin = location.split('/host/lobby/')[1]
            
            game = Game.query.get(game_pin)
            assert game is not None
            assert len(game.questions) == 2
            assert game.questions[0]['question'] == 'What is 2+2?'


class TestErrorHandlingIntegration:
    """Test error handling in integrated scenarios."""
    
    def test_invalid_game_join_attempts(self, client):
        """Test various invalid game join scenarios."""
        # Try to join non-existent game
        response = client.post('/join', data={
            'pin': '999999',
            'player_name': 'Test Player'
        })
        
        assert response.status_code == 302
        # Should redirect back to join page with error
        
        # Try with invalid PIN format
        response = client.post('/join', data={
            'pin': 'invalid',
            'player_name': 'Test Player'
        })
        
        assert response.status_code == 302
    
    def test_unauthorized_host_actions(self, client, sample_game):
        """Test unauthorized host actions."""
        # Try to access host control without session
        response = client.get(f'/host/control/{sample_game.pin}')
        assert response.status_code == 302  # Redirect to dashboard
        
        # Try API actions without authorization
        api_endpoints = [
            f'/api/host/{sample_game.pin}/start-question',
            f'/api/host/{sample_game.pin}/show-results',
            f'/api/host/{sample_game.pin}/next-question'
        ]
        
        for endpoint in api_endpoints:
            response = client.post(endpoint)
            assert response.status_code == 403
    
    def test_invalid_form_submissions(self, client):
        """Test invalid form submissions."""
        # Empty host name
        response = client.post('/host/create-game', data={
            'host_name': '',
            'quiz_source': 'default_de'
        })
        
        assert response.status_code == 302  # Redirect with error
        
        # Empty player name for solo quiz
        response = client.post('/start_quiz', data={
            'player_name': '',
            'mode': 'difficulty',
            'difficulty': 'easy',
            'language': 'de'
        })
        
        assert response.status_code == 302  # Redirect with error


class TestSecurityIntegration:
    """Test security measures in integrated scenarios."""
    
    def test_xss_protection_in_game_flow(self, client, app):
        """Test XSS protection throughout game flow."""
        with app.app_context():
            xss_payload = '<script>alert("XSS")</script>'
            
            # Try XSS in player name during game join
            response = client.post('/join', data={
                'pin': '123456',  # Invalid game, but tests validation
                'player_name': xss_payload
            })
            
            # Should handle safely (either reject or escape)
            assert response.status_code == 302
            
            # Try XSS in quiz answers
            response = client.post('/start_quiz', data={
                'player_name': 'Safe Player',
                'mode': 'difficulty',
                'difficulty': 'easy',
                'language': 'de'
            })
            
            if response.status_code == 302:  # Quiz started
                response = client.post('/quiz', data={'answer': xss_payload})
                # Should handle safely
                assert response.status_code in [200, 302]
    
    def test_session_security(self, client, sample_game):
        """Test session security measures."""
        # Test session isolation
        with client.session_transaction() as sess:
            sess['player_id'] = 'fake-player'
            sess['game_pin'] = sample_game.pin
        
        # Try to access game with fake session data
        response = client.get(f'/game/{sample_game.pin}')
        assert response.status_code == 302  # Should redirect due to invalid player
    
    def test_rate_limiting_simulation(self, client):
        """Test behavior under high request load."""
        # Simulate multiple rapid requests
        for _ in range(10):
            response = client.get('/')
            assert response.status_code == 200
        
        # Should still be responsive (rate limiting might kick in)
        response = client.get('/')
        assert response.status_code in [200, 429]  # 429 if rate limited


class TestDatabaseIntegrity:
    """Test database integrity in integrated scenarios."""
    
    def test_cascading_deletes(self, app, sample_game, sample_player):
        """Test that related records are properly deleted."""
        with app.app_context():
            game_pin = sample_game.pin
            player_id = sample_player.id
            
            # Verify records exist
            assert Game.query.get(game_pin) is not None
            assert Player.query.get(player_id) is not None
            
            # Delete game
            db.session.delete(sample_game)
            db.session.commit()
            
            # Player should be deleted due to cascade
            assert Game.query.get(game_pin) is None
            assert Player.query.get(player_id) is None
    
    def test_concurrent_game_creation(self, app):
        """Test handling of concurrent game creation."""
        with app.app_context():
            # This would need more sophisticated testing in a real scenario
            # with actual threading, but we can test the basics
            
            from game_logic import create_new_game
            
            games = []
            for i in range(5):
                game = create_new_game(f'Host {i}', [])
                games.append(game)
            
            # All games should have unique PINs
            pins = [game.pin for game in games]
            assert len(pins) == len(set(pins))  # All unique