# tests/test_game_logic.py - Game Logic Tests

import pytest
from extensions import db
from game_logic import (
    load_questions,
    create_new_game,
    add_player_to_game,
    start_question,
    submit_answer,
    calculate_scores_for_question,
    advance_to_next_question,
    get_leaderboard,
    generate_pin
)
from database import Game, Player


class TestLoadQuestions:
    """Test question loading functionality."""
    
    def test_load_questions_de(self):
        """Test loading German questions."""
        questions = load_questions('de')
        assert len(questions) > 0
        assert all('question' in q for q in questions)
        assert all('answer' in q for q in questions)
    
    def test_load_questions_en(self):
        """Test loading English questions."""
        questions = load_questions('en')
        assert len(questions) > 0
        assert all('question' in q for q in questions)
        assert all('answer' in q for q in questions)
    
    def test_load_questions_invalid_language(self):
        """Test loading with invalid language."""
        questions = load_questions('invalid')
        assert questions == []


class TestGameCreation:
    """Test game creation functionality."""
    
    def test_generate_pin(self, app):
        """Test PIN generation."""
        with app.app_context():
            pin1 = generate_pin()
            pin2 = generate_pin()
            
            assert len(pin1) == 6
            assert len(pin2) == 6
            assert pin1.isdigit()
            assert pin2.isdigit()
    
    def test_create_new_game(self, app, sample_questions):
        """Test creating a new game."""
        with app.app_context():
            game = create_new_game("Test Host", sample_questions)
            
            assert game is not None
            assert game.host_name == "Test Host"
            assert game.questions == sample_questions
            assert game.state == "waiting"
            assert game.current_question == 0
            
            # Verify it's in the database
            db_game = Game.query.get(game.pin)
            assert db_game is not None
            assert db_game.host_name == "Test Host"
    
    def test_create_game_empty_questions(self, app):
        """Test creating game with empty questions list."""
        with app.app_context():
            game = create_new_game("Test Host", [])
            
            assert game is not None
            assert len(game.questions) == 0


class TestPlayerManagement:
    """Test player joining and management."""
    
    def test_add_player_to_game(self, app, sample_game):
        """Test adding a player to a game."""
        with app.app_context():
            player = add_player_to_game(sample_game.pin, "player-123", "Test Player")
            
            assert player is not None
            assert player.name == "Test Player"
            assert player.game_pin == sample_game.pin
            assert player.score == 0
            
            # Verify it's in the database
            db_player = Player.query.get("player-123")
            assert db_player is not None
    
    def test_add_player_nonexistent_game(self, app):
        """Test adding player to non-existent game."""
        with app.app_context():
            player = add_player_to_game("999999", "player-123", "Test Player")
            assert player is None
    
    def test_add_player_duplicate_name(self, app, sample_game, sample_player):
        """Test adding player with duplicate name."""
        with app.app_context():
            # Try to add another player with the same name
            player = add_player_to_game(sample_game.pin, "player-456", sample_player.name)
            assert player is None
    
    def test_add_player_game_not_waiting(self, app, sample_game):
        """Test adding player to game that's not in waiting state."""
        with app.app_context():
            sample_game.state = "playing"
            db.session.commit()
            
            player = add_player_to_game(sample_game.pin, "player-123", "Test Player")
            assert player is None


class TestGameFlow:
    """Test game flow functionality."""
    
    def test_start_question(self, app, sample_game):
        """Test starting a question."""
        with app.app_context():
            game = start_question(sample_game.pin)
            
            assert game is not None
            assert game.state == "playing"
            assert game.current_question == 0
    
    def test_start_question_nonexistent_game(self, app):
        """Test starting question for non-existent game."""
        with app.app_context():
            game = start_question("999999")
            assert game is None
    
    def test_submit_answer(self, app, sample_game, sample_player):
        """Test submitting an answer."""
        with app.app_context():
            # Start the question first
            sample_game.state = "playing"
            db.session.commit()
            
            success = submit_answer(sample_game.pin, sample_player.id, "4", 5.0)
            
            assert success is True
            
            # Check that answer was stored
            player = Player.query.get(sample_player.id)
            assert len(player.answers) > 0
            assert player.answers[0]['answer'] == "4"
            assert player.answers[0]['response_time'] == 5.0
    
    def test_submit_answer_twice(self, app, sample_game, sample_player):
        """Test submitting answer twice for same question."""
        with app.app_context():
            sample_game.state = "playing"
            db.session.commit()
            
            # Submit first answer
            success1 = submit_answer(sample_game.pin, sample_player.id, "4", 5.0)
            assert success1 is True
            
            # Try to submit second answer
            success2 = submit_answer(sample_game.pin, sample_player.id, "5", 3.0)
            assert success2 is False
    
    def test_calculate_scores_correct_answer(self, app, sample_game, sample_player):
        """Test score calculation for correct answer."""
        with app.app_context():
            sample_game.state = "playing"
            
            # Submit correct answer
            sample_player.answers = [{'answer': '4', 'response_time': 5.0}]
            db.session.commit()
            
            game = calculate_scores_for_question(sample_game.pin)
            
            assert game is not None
            
            # Check score was awarded
            player = Player.query.get(sample_player.id)
            assert player.score > 0
    
    def test_calculate_scores_wrong_answer(self, app, sample_game, sample_player):
        """Test score calculation for wrong answer."""
        with app.app_context():
            sample_game.state = "playing"
            
            # Submit wrong answer
            sample_player.answers = [{'answer': '5', 'response_time': 5.0}]
            db.session.commit()
            
            game = calculate_scores_for_question(sample_game.pin)
            
            assert game is not None
            
            # Check no score was awarded
            player = Player.query.get(sample_player.id)
            assert player.score == 0
    
    def test_advance_to_next_question(self, app, sample_game):
        """Test advancing to next question."""
        with app.app_context():
            game = advance_to_next_question(sample_game.pin)
            
            assert game is not None
            assert game.current_question == 1
            assert game.state == "playing"
    
    def test_advance_to_finish_game(self, app, sample_game):
        """Test advancing past last question finishes game."""
        with app.app_context():
            # Set to last question
            sample_game.current_question = len(sample_game.questions) - 1
            db.session.commit()
            
            game = advance_to_next_question(sample_game.pin)
            
            assert game is not None
            assert game.current_question == len(sample_game.questions)
            assert game.state == "finished"


class TestLeaderboard:
    """Test leaderboard functionality."""
    
    def test_get_leaderboard_empty(self, app, sample_game):
        """Test getting leaderboard with no players."""
        with app.app_context():
            leaderboard = get_leaderboard(sample_game.pin)
            assert leaderboard == []
    
    def test_get_leaderboard_with_players(self, app, sample_game):
        """Test getting leaderboard with players."""
        with app.app_context():
            # Add multiple players with different scores
            player1 = Player(id="p1", name="Player 1", game_pin=sample_game.pin, score=100)
            player2 = Player(id="p2", name="Player 2", game_pin=sample_game.pin, score=200)
            player3 = Player(id="p3", name="Player 3", game_pin=sample_game.pin, score=150)
            
            db.session.add_all([player1, player2, player3])
            db.session.commit()
            
            leaderboard = get_leaderboard(sample_game.pin)
            
            assert len(leaderboard) == 3
            assert leaderboard[0].score == 200  # Highest score first
            assert leaderboard[1].score == 150
            assert leaderboard[2].score == 100
    
    def test_get_leaderboard_nonexistent_game(self, app):
        """Test getting leaderboard for non-existent game."""
        with app.app_context():
            leaderboard = get_leaderboard("999999")
            assert leaderboard == []