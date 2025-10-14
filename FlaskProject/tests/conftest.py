# tests/conftest.py - Test Configuration and Fixtures

import pytest
import tempfile
import os
from pathlib import Path

from app import create_app
from extensions import db
from database import Game, Player, PlayerStats, QuizSet, CustomQuestion


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file for the test database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        yield app
        
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def sample_questions():
    """Sample questions for testing."""
    return [
        {
            "question": "What is 2+2?",
            "answer": "4",
            "type": "text",
            "difficulty": "easy"
        },
        {
            "question": "Which color is primary?",
            "options": ["Red", "Green", "Purple", "Brown"],
            "answer": "Red",
            "type": "mc",
            "difficulty": "medium"
        },
        {
            "question": "What is the capital of France?",
            "answer": "Paris",
            "type": "text",
            "difficulty": "hard"
        }
    ]


@pytest.fixture
def sample_game(app, sample_questions):
    """Create a sample game for testing."""
    with app.app_context():
        game = Game(
            pin="123456",
            host_name="Test Host",
            questions=sample_questions,
            state="waiting"
        )
        db.session.add(game)
        db.session.commit()
        return game


@pytest.fixture
def sample_player(app, sample_game):
    """Create a sample player for testing."""
    with app.app_context():
        player = Player(
            id="test-player-1",
            name="Test Player",
            game_pin=sample_game.pin
        )
        db.session.add(player)
        db.session.commit()
        return player


@pytest.fixture
def quiz_set(app):
    """Create a sample quiz set for testing."""
    with app.app_context():
        quiz_set = QuizSet(
            name="Test Quiz Set",
            author="Test Author"
        )
        db.session.add(quiz_set)
        db.session.flush()  # Get the ID
        
        # Add some questions to the quiz set
        questions = [
            CustomQuestion(
                question="Test Question 1?",
                answer="Answer 1",
                question_type="text",
                difficulty="easy",
                quiz_set_id=quiz_set.id
            ),
            CustomQuestion(
                question="Test Question 2?",
                answer="Answer 2",
                question_type="mc",
                options=["Answer 1", "Answer 2", "Answer 3"],
                difficulty="medium",
                quiz_set_id=quiz_set.id
            )
        ]
        
        for q in questions:
            db.session.add(q)
        
        db.session.commit()
        return quiz_set


@pytest.fixture
def authenticated_host_session(client, sample_game):
    """Create a session with authenticated host."""
    with client.session_transaction() as sess:
        sess['host_pin'] = sample_game.pin
        sess['is_host'] = True


@pytest.fixture
def authenticated_player_session(client, sample_player):
    """Create a session with authenticated player."""
    with client.session_transaction() as sess:
        sess['player_id'] = sample_player.id
        sess['game_pin'] = sample_player.game_pin
        sess['player_name'] = sample_player.name