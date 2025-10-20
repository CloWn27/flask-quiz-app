# FlaskProject/game_logic.py - Core Game Logic

import json
import logging
import random
import time
from pathlib import Path

from extensions import db, socketio
from database import Game, Player, User, Achievement, UserAchievement

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
    """Enhanced score calculation with timer and achievement support."""
    try:
        game = Game.query.get(pin)
        if not game:
            return None
        
        current_question = game.questions[game.current_question]
        correct_answer = str(current_question['answer']).strip().lower()
        question_timer = current_question.get('timer_seconds', 30)
        base_points = current_question.get('points', 100)
        
        for player in game.players:
            answers = player.answers or []
            if len(answers) > game.current_question:
                answer_data = answers[game.current_question]
                if answer_data and answer_data['answer']:
                    player_answer = str(answer_data['answer']).strip().lower()
                    response_time = answer_data.get('response_time', question_timer)
                    
                    if player_answer == correct_answer:
                        # Enhanced scoring system
                        time_percentage = max(0, (question_timer - response_time) / question_timer)
                        time_bonus = int(base_points * 0.5 * time_percentage)  # Up to 50% bonus for speed
                        difficulty_multiplier = {
                            'easy': 1.0, 'medium': 1.2, 'hard': 1.5, 'heavy': 2.0
                        }.get(current_question.get('difficulty', 'medium'), 1.0)
                        
                        final_score = int((base_points + time_bonus) * difficulty_multiplier)
                        player.score += final_score
                        
                        # Track streak for achievements
                        if not hasattr(player, 'current_streak'):
                            player.current_streak = 0
                        player.current_streak += 1
                        
                        logger.info(f"Player {player.name} scored {final_score} points (base: {base_points}, time bonus: {time_bonus}, multiplier: {difficulty_multiplier})")
                    else:
                        # Reset streak on wrong answer
                        if hasattr(player, 'current_streak'):
                            player.current_streak = 0
        
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

def process_achievements(user_id, game_stats=None):
    """Process and unlock achievements for a user."""
    try:
        user = User.query.get(user_id)
        if not user:
            return []
        
        unlocked_achievements = []
        achievements = Achievement.query.filter_by(is_active=True).all()
        
        for achievement in achievements:
            # Check if user already has this achievement
            existing = UserAchievement.query.filter_by(
                user_id=user_id, achievement_id=achievement.id
            ).first()
            
            if existing:
                continue
                
            # Check achievement requirements
            requirement_met = False
            current_value = 0
            
            if achievement.requirement_type == 'total_score':
                current_value = user.total_score
            elif achievement.requirement_type == 'games_played':
                current_value = user.games_played
            elif achievement.requirement_type == 'streak':
                current_value = user.best_streak
            elif achievement.requirement_type == 'accuracy':
                if user.questions_answered > 0:
                    current_value = int((user.correct_answers / user.questions_answered) * 100)
            
            if current_value >= achievement.requirement_value:
                # Unlock achievement
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    progress=current_value
                )
                db.session.add(user_achievement)
                unlocked_achievements.append(achievement)
                
                logger.info(f"Achievement '{achievement.name}' unlocked for user {user.username}")
        
        db.session.commit()
        return unlocked_achievements
        
    except Exception as e:
        logger.error(f"Error processing achievements for user {user_id}: {e}")
        db.session.rollback()
        return []

def initialize_default_achievements():
    """Create default achievements if they don't exist."""
    try:
        if Achievement.query.count() > 0:
            return  # Already initialized
            
        default_achievements = [
            {
                'name': 'First Steps', 'description': 'Complete your first quiz',
                'icon': '🎯', 'category': 'games', 'requirement_type': 'games_played',
                'requirement_value': 1, 'points': 10, 'rarity': 'common'
            },
            {
                'name': 'Century Club', 'description': 'Score 100 points in a single game',
                'icon': '💯', 'category': 'score', 'requirement_type': 'total_score',
                'requirement_value': 100, 'points': 20, 'rarity': 'common'
            },
            {
                'name': 'Speed Demon', 'description': 'Answer 5 questions correctly in under 5 seconds each',
                'icon': '⚡', 'category': 'speed', 'requirement_type': 'streak',
                'requirement_value': 5, 'points': 30, 'rarity': 'rare'
            },
            {
                'name': 'Perfect Score', 'description': 'Get 100% accuracy in a 10+ question quiz',
                'icon': '🏆', 'category': 'accuracy', 'requirement_type': 'accuracy',
                'requirement_value': 100, 'points': 50, 'rarity': 'epic'
            },
            {
                'name': 'Quiz Master', 'description': 'Play 50 games',
                'icon': '👑', 'category': 'games', 'requirement_type': 'games_played',
                'requirement_value': 50, 'points': 100, 'rarity': 'legendary'
            }
        ]
        
        for ach_data in default_achievements:
            achievement = Achievement(**ach_data)
            db.session.add(achievement)
        
        db.session.commit()
        logger.info(f"Initialized {len(default_achievements)} default achievements")
        
    except Exception as e:
        logger.error(f"Error initializing achievements: {e}")
        db.session.rollback()

def get_user_or_create_guest(player_name):
    """Get existing user or create guest user."""
    try:
        # Try to find existing guest user by name
        user = User.query.filter_by(username=player_name, is_guest=True).first()
        
        if not user:
            # Create new guest user
            user = User(
                username=player_name,
                display_name=player_name,
                is_guest=True
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created guest user: {player_name}")
        
        return user
        
    except Exception as e:
        logger.error(f"Error creating/retrieving user {player_name}: {e}")
        db.session.rollback()
        return None

def cleanup_old_games():
    """Clean up games older than 24 hours."""
    try:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        
        old_games = Game.query.filter(Game.created_at < cutoff).all()
        for game in old_games:
            db.session.delete(game)
        
        db.session.commit()
        logger.info(f"Cleaned up {len(old_games)} old games")
        
    except Exception as e:
        logger.error(f"Error cleaning up old games: {e}")
        db.session.rollback()
