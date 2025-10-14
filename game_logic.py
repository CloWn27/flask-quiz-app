# FlaskProject/game_logic.py - Core Game Logic

import json
import logging
import random
import time
from pathlib import Path

from extensions import db, socketio
from database import Game, Player

logger = logging.getLogger(__name__)

# Question data cache
_question_cache = {}

def load_questions(language='de'):
    """Load questions from JSON file with caching."""
    if language in _question_cache:
        return _question_cache[language]
    
    try:
        questions_file = Path(__file__).parent / f'questions_{language}.json'
        if not questions_file.exists():
            logger.error(f"Questions file not found: {questions_file}")
            return []
        
        with open(questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Flatten the questions from all difficulty levels
        all_questions = []
        for difficulty, questions in data.items():
            all_questions.extend(questions)
        
        _question_cache[language] = all_questions
        logger.info(f"Loaded {len(all_questions)} questions for language '{language}'")
        return all_questions
        
    except Exception as e:
        logger.error(f"Error loading questions for language '{language}': {e}")
        return []

def generate_pin():
    """Generate a unique 6-digit game PIN."""
    while True:
        pin = f"{random.randint(100000, 999999)}"
        if not Game.query.get(pin):
            return pin

def create_new_game(host_name, questions):
    """Create a new game with the given host and questions."""
    try:
        pin = generate_pin()
        
        new_game = Game(
            pin=pin,
            host_name=host_name,
            questions=questions,
            state='waiting'
        )
        
        db.session.add(new_game)
        db.session.commit()
        
        logger.info(f"Created new game {pin} hosted by {host_name}")
        return new_game
        
    except Exception as e:
        logger.error(f"Error creating new game: {e}")
        db.session.rollback()
        return None

def add_player_to_game(pin, player_id, player_name):
    """Add a player to an existing game."""
    try:
        game = Game.query.get(pin)
        if not game:
            logger.warning(f"Attempted to join non-existent game: {pin}")
            return None
            
        if game.state != 'waiting':
            logger.warning(f"Attempted to join game {pin} not in waiting state")
            return None
        
        # Check if player name already exists in this game
        existing_player = Player.query.filter_by(game_pin=pin, name=player_name).first()
        if existing_player:
            logger.warning(f"Player name '{player_name}' already exists in game {pin}")
            return None
        
        new_player = Player(
            id=player_id,
            name=player_name,
            game_pin=pin
        )
        
        db.session.add(new_player)
        db.session.commit()
        
        # Notify all players in the game room about the new player
        players_list = [{'id': p.id, 'name': p.name} for p in game.players.all()]
        socketio.emit('player_joined', {
            'player_name': player_name,
            'total_players': game.players.count(),
            'players': players_list,
            'player_count': game.players.count()
        }, room=pin)
        
        logger.info(f"Player '{player_name}' joined game {pin}")
        return new_player
        
    except Exception as e:
        logger.error(f"Error adding player to game {pin}: {e}")
        db.session.rollback()
        return None

def start_question(pin):
    """Start the current question for a game."""
    try:
        game = Game.query.get(pin)
        if not game:
            return None
            
        if game.state == 'waiting':
            game.state = 'playing'
        
        if game.current_question >= len(game.questions):
            logger.warning(f"No more questions for game {pin}")
            return None
        
        db.session.commit()
        logger.info(f"Started question {game.current_question + 1} for game {pin}")
        return game
        
    except Exception as e:
        logger.error(f"Error starting question for game {pin}: {e}")
        db.session.rollback()
        return None

def submit_answer(pin, player_id, answer, response_time):
    """Submit an answer for a player."""
    try:
        player = Player.query.get(player_id)
        if not player or player.game_pin != pin:
            logger.warning(f"Invalid player {player_id} for game {pin}")
            return False
        
        game = Game.query.get(pin)
        if not game or game.state != 'playing':
            logger.warning(f"Game {pin} not in playing state")
            return False
        
        # Check if this question was already answered
        current_answers = player.answers or []
        question_index = game.current_question
        
        # Ensure answers list is long enough
        while len(current_answers) <= question_index:
            current_answers.append(None)
        
        # Don't allow re-answering the same question
        if current_answers[question_index] is not None:
            logger.warning(f"Player {player_id} already answered question {question_index}")
            return False
        
        # Store the answer with metadata
        answer_data = {
            'answer': answer,
            'response_time': response_time,
            'timestamp': time.time()
        }
        current_answers[question_index] = answer_data
        player.answers = current_answers
        
        db.session.commit()
        
        logger.info(f"Player {player.name} submitted answer for question {question_index + 1} in game {pin}")
        return True
        
    except Exception as e:
        logger.error(f"Error submitting answer for game {pin}, player {player_id}: {e}")
        db.session.rollback()
        return False

def calculate_scores_for_question(pin):
    """Calculate scores for the current question."""
    try:
        game = Game.query.get(pin)
        if not game:
            return None
        
        current_question = game.questions[game.current_question]
        correct_answer = str(current_question['answer']).strip().lower()
        
        for player in game.players:
            answers = player.answers or []
            if len(answers) > game.current_question:
                answer_data = answers[game.current_question]
                if answer_data and answer_data['answer']:
                    player_answer = str(answer_data['answer']).strip().lower()
                    if player_answer == correct_answer:
                        # Award points based on response time (max 1000 points)
                        response_time = answer_data.get('response_time', 30)
                        base_points = 500
                        time_bonus = max(0, 500 - (response_time * 10))
                        player.score += int(base_points + time_bonus)
        
        db.session.commit()
        logger.info(f"Calculated scores for question {game.current_question + 1} in game {pin}")
        return game
        
    except Exception as e:
        logger.error(f"Error calculating scores for game {pin}: {e}")
        db.session.rollback()
        return None

def advance_to_next_question(pin):
    """Advance to the next question or finish the game."""
    try:
        game = Game.query.get(pin)
        if not game:
            return None
        
        game.current_question += 1
        
        if game.current_question >= len(game.questions):
            game.state = 'finished'
            logger.info(f"Game {pin} finished")
        else:
            logger.info(f"Game {pin} advanced to question {game.current_question + 1}")
        
        db.session.commit()
        return game
        
    except Exception as e:
        logger.error(f"Error advancing question for game {pin}: {e}")
        db.session.rollback()
        return None

def get_leaderboard(pin):
    """Get the current leaderboard for a game."""
    try:
        game = Game.query.get(pin)
        if not game:
            return []
        
        return game.players.order_by(Player.score.desc()).all()
        
    except Exception as e:
        logger.error(f"Error getting leaderboard for game {pin}: {e}")
        return []

def cleanup_old_games():
    """Clean up games older than 24 hours."""
    try:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=1)
        
        old_games = Game.query.filter(Game.created_at < cutoff).all()
        for game in old_games:
            db.session.delete(game)
        
        db.session.commit()
        logger.info(f"Cleaned up {len(old_games)} old games")
        
    except Exception as e:
        logger.error(f"Error cleaning up old games: {e}")
        db.session.rollback()