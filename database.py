# FlaskProject/database.py - Database Models

from datetime import datetime, timezone
from sqlalchemy import JSON
from extensions import db

class Game(db.Model):
    """Game model for storing quiz game instances."""
    __tablename__ = 'games'
    
    pin = db.Column(db.String(6), primary_key=True)
    host_name = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(20), default='waiting')  # waiting, playing, finished
    current_question = db.Column(db.Integer, default=0)
    questions = db.Column(JSON)  # Store questions as JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    players = db.relationship('Player', backref='game', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Game {self.pin}: {self.host_name}>'

class Player(db.Model):
    """Player model for storing player information."""
    __tablename__ = 'players'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    name = db.Column(db.String(50), nullable=False)
    game_pin = db.Column(db.String(6), db.ForeignKey('games.pin'), nullable=False)
    score = db.Column(db.Integer, default=0)
    answers = db.Column(JSON, default=list)  # Store player answers
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Player {self.name} in game {self.game_pin}>'

class PlayerStats(db.Model):
    """Enhanced statistics for solo quiz games."""
    __tablename__ = 'player_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    player_name = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    difficulty = db.Column(db.String(10), nullable=True)  # Track difficulty level
    language = db.Column(db.String(2), nullable=True)     # Track language used
    avg_response_time = db.Column(db.Float, nullable=True) # Average response time
    streak = db.Column(db.Integer, default=0)             # Correct answer streak
    played_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<PlayerStats {self.player_name}: {self.score}/{self.total_questions}>'

class QuizSet(db.Model):
    """Custom quiz sets created by users."""
    __tablename__ = 'quiz_sets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    questions = db.relationship('CustomQuestion', backref='quiz_set', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<QuizSet {self.name} by {self.author}>'

class CustomQuestion(db.Model):
    """Enhanced custom questions within quiz sets."""
    __tablename__ = 'custom_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    question_type = db.Column(db.String(10), default='text')  # text, mc, image, timer
    options = db.Column(JSON, default=list)  # For multiple choice questions
    difficulty = db.Column(db.String(10), default='medium')  # easy, medium, hard, heavy
    category = db.Column(db.String(50), nullable=True)       # Question category/tag
    image_url = db.Column(db.String(255), nullable=True)     # For image questions
    timer_seconds = db.Column(db.Integer, default=30)       # Question timer
    points = db.Column(db.Integer, default=100)             # Base points for question
    quiz_set_id = db.Column(db.Integer, db.ForeignKey('quiz_sets.id'), nullable=False)
    
    def __repr__(self):
        return f'<CustomQuestion {self.question[:30]}...>'

class User(db.Model):
    """User accounts for persistent data and enhanced features."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Optional for guest users
    display_name = db.Column(db.String(100), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    is_guest = db.Column(db.Boolean, default=True)           # Guest vs registered user
    total_score = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)
    questions_answered = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    best_streak = db.Column(db.Integer, default=0)
    preferred_language = db.Column(db.String(2), default='de')
    theme_preference = db.Column(db.String(10), default='dark') # dark, light
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    achievements = db.relationship('UserAchievement', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Achievement(db.Model):
    """Achievement definitions."""
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), nullable=False)          # Emoji or icon class
    category = db.Column(db.String(50), nullable=False)      # score, streak, games, etc
    requirement_type = db.Column(db.String(20), nullable=False) # count, streak, percentage
    requirement_value = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, default=10)              # Achievement points
    rarity = db.Column(db.String(10), default='common')     # common, rare, epic, legendary
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Achievement {self.name}>'

class UserAchievement(db.Model):
    """User achievement unlocks."""
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    progress = db.Column(db.Integer, default=0)             # Current progress towards achievement
    
    # Relationships
    achievement = db.relationship('Achievement', backref='user_achievements')
    
    def __repr__(self):
        return f'<UserAchievement {self.user_id}-{self.achievement_id}>'
