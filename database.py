# FlaskProject/database.py - Database Models

from datetime import datetime
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Player {self.name} in game {self.game_pin}>'

class PlayerStats(db.Model):
    """Statistics for solo quiz games."""
    __tablename__ = 'player_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    player_name = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    played_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PlayerStats {self.player_name}: {self.score}/{self.total_questions}>'

class QuizSet(db.Model):
    """Custom quiz sets created by users."""
    __tablename__ = 'quiz_sets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('CustomQuestion', backref='quiz_set', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<QuizSet {self.name} by {self.author}>'

class CustomQuestion(db.Model):
    """Custom questions within quiz sets."""
    __tablename__ = 'custom_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    question_type = db.Column(db.String(10), default='text')  # text, mc (multiple choice)
    options = db.Column(JSON, default=list)  # For multiple choice questions
    difficulty = db.Column(db.String(10), default='medium')  # easy, medium, hard, heavy
    quiz_set_id = db.Column(db.Integer, db.ForeignKey('quiz_sets.id'), nullable=False)
    
    def __repr__(self):
        return f'<CustomQuestion {self.question[:30]}...>'