# FlaskProject/views/player_routes.py - Refactored with improved security

import logging
import random
import time
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, RadioField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

from config import get_config
from database import db, Game, Player, PlayerStats, User, Achievement, UserAchievement
from game_logic import load_questions, add_player_to_game, get_user_or_create_guest, process_achievements
from utils.security import validate_pin, validate_player_name, sanitize_answer

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')
config = get_config()

player_bp = Blueprint('player', __name__)


# --- Forms (Flask-WTF for security and validation) ---

class JoinGameForm(FlaskForm):
    pin = StringField('Spiel-PIN', validators=[
        DataRequired('PIN ist erforderlich.'),
        Regexp(r'^\d{6}$', message='PIN muss aus 6 Ziffern bestehen.')
    ])
    player_name = StringField('Spielername', validators=[
        DataRequired('Name ist erforderlich.'),
        Length(min=2, max=20, message='Name muss zwischen 2 und 20 Zeichen lang sein.')
    ])
    submit = SubmitField('Spiel beitreten')


class SoloQuizForm(FlaskForm):
    player_name = StringField('Dein Name', validators=[
        DataRequired('Name ist erforderlich.'),
        Length(min=2, max=20)
    ])
    mode = RadioField('Spielmodus', choices=[('difficulty', 'Nach Schwierigkeit'), ('random', 'Zufällig')],
                      default='difficulty')
    difficulty = SelectField('Schwierigkeitsgrad', choices=[
        ('easy', '🟢 Einfach'), ('medium', '🟡 Mittel'), ('hard', '🟠 Schwer'), ('heavy', '🔴 Sehr Schwer')
    ])
    language = SelectField('Sprache', choices=[('de', '🇩🇪 Deutsch'), ('en', '🇺🇸 English')], default='de')
    submit = SubmitField('🚀 Quiz starten')


# --- Routen ---

@player_bp.route('/')
def index():
    form = SoloQuizForm()
    return render_template('index.html', form=form)


@player_bp.route('/stats')
def stats():
    all_stats = PlayerStats.query.order_by(PlayerStats.played_at.desc()).limit(50).all()
    
    # Calculate aggregate statistics
    total_games = PlayerStats.query.count()
    avg_accuracy = db.session.query(db.func.avg(PlayerStats.percentage)).scalar() or 0
    top_players = PlayerStats.query.order_by(PlayerStats.percentage.desc(), PlayerStats.score.desc()).limit(10).all()
    
    # Language and difficulty statistics
    language_stats = db.session.query(
        PlayerStats.language, 
        db.func.count(PlayerStats.id),
        db.func.avg(PlayerStats.percentage)
    ).filter(PlayerStats.language.isnot(None)).group_by(PlayerStats.language).all()
    
    difficulty_stats = db.session.query(
        PlayerStats.difficulty,
        db.func.count(PlayerStats.id),
        db.func.avg(PlayerStats.percentage),
        db.func.avg(PlayerStats.avg_response_time)
    ).filter(PlayerStats.difficulty.isnot(None)).group_by(PlayerStats.difficulty).all()
    
    analytics_data = {
        'total_games': total_games,
        'avg_accuracy': round(avg_accuracy, 1),
        'top_players': top_players,
        'language_stats': language_stats,
        'difficulty_stats': difficulty_stats
    }
    
    return render_template('stats.html', stats=all_stats, analytics=analytics_data)

@player_bp.route('/achievements')
def achievements():
    """Display achievement system and user progress."""
    player_name = session.get('player_name')
    user_achievements = []
    user_progress = {}
    
    if player_name:
        user = User.query.filter_by(username=player_name, is_guest=True).first()
        if user:
            user_achievements = UserAchievement.query.filter_by(user_id=user.id).all()
            
            # Calculate progress for locked achievements
            all_achievements = Achievement.query.filter_by(is_active=True).all()
            for achievement in all_achievements:
                if not any(ua.achievement_id == achievement.id for ua in user_achievements):
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
                    
                    progress_percentage = min(100, (current_value / achievement.requirement_value) * 100)
                    user_progress[achievement.id] = {
                        'current': current_value,
                        'required': achievement.requirement_value,
                        'percentage': progress_percentage
                    }
    
    all_achievements = Achievement.query.filter_by(is_active=True).order_by(Achievement.rarity, Achievement.points).all()
    
    return render_template('achievements.html', 
                         achievements=all_achievements,
                         user_achievements=user_achievements,
                         user_progress=user_progress,
                         player_name=player_name)


@player_bp.route('/join', methods=['GET', 'POST'])
def join_game():
    """Join game with enhanced security validation."""
    form = JoinGameForm()
    if form.validate_on_submit():
        pin = form.pin.data
        raw_player_name = form.player_name.data

        # Additional security validation
        if not validate_pin(pin):
            security_logger.warning(f"Invalid PIN format attempted: {pin[:2]}****")
            flash('Invalid PIN format!', 'danger')
            return redirect(url_for('player.join_game'))

        # Validate and sanitize player name
        clean_player_name = validate_player_name(raw_player_name)
        if not clean_player_name:
            security_logger.warning(f"Invalid player name attempted: {raw_player_name[:10]}...")
            flash('Invalid player name. Use only letters, numbers, and basic punctuation.', 'danger')
            return redirect(url_for('player.join_game'))

        try:
            game = Game.query.get(pin)
            if not game:
                logger.info(f"Game not found for PIN: {pin}")
                flash('Game with this PIN not found!', 'danger')
                return redirect(url_for('player.join_game'))

            if game.state != 'waiting':
                logger.info(f"Attempt to join game {pin} not in waiting state")
                flash('This game has already started!', 'warning')
                return redirect(url_for('player.join_game'))

            # Check player limit
            if game.players.count() >= config.MAX_PLAYERS_PER_GAME:
                logger.info(f"Game {pin} has reached maximum player limit")
                flash('This game is full!', 'warning')
                return redirect(url_for('player.join_game'))

            player_id = str(uuid.uuid4())
            new_player = add_player_to_game(game.pin, player_id, clean_player_name)

            if not new_player:
                flash('Failed to join game. Please try again.', 'danger')
                return redirect(url_for('player.join_game'))

            # Set session data with secure values
            session['player_id'] = player_id
            session['game_pin'] = pin
            session['player_name'] = clean_player_name
            session.permanent = True  # Enable session timeout

            security_logger.info(f"Player {clean_player_name} joined game {pin}")
            flash(f'Successfully joined game! Welcome, {clean_player_name}!', 'success')
            return redirect(url_for('player.game_lobby', pin=pin))

        except Exception as e:
            logger.error(f"Error joining game: {e}")
            flash('An error occurred while joining the game. Please try again.', 'danger')
            return redirect(url_for('player.join_game'))

    return render_template('player/join.html', form=form)


@player_bp.route('/game/<pin>')
def game_lobby(pin):
    game = Game.query.get_or_404(pin)
    player = Player.query.get(session.get('player_id'))

    if not player or player.game_pin != pin:
        flash('Du bist nicht für dieses Spiel angemeldet!', 'danger')
        return redirect(url_for('player.join_game'))

    return render_template('player/game.html', game=game, pin=pin)


@player_bp.route('/start_quiz', methods=['POST'])
def start_quiz():
    
    form = SoloQuizForm()
    if form.validate_on_submit():
        # Additional validation and sanitization
        raw_name = form.player_name.data
        clean_name = validate_player_name(raw_name)
        
        if not clean_name:
            flash('Ungültiger Name. Bitte verwende nur Buchstaben, Zahlen und Grundzeichen.', 'danger')
            return redirect(url_for('player.index'))
        
        mode = form.mode.data
        difficulty = form.difficulty.data
        language = form.language.data
        
        # Validate selected options
        if mode not in ['difficulty', 'random']:
            flash('Ungültiger Spielmodus.', 'danger')
            return redirect(url_for('player.index'))
            
        if difficulty not in ['easy', 'medium', 'hard', 'heavy']:
            flash('Ungültiger Schwierigkeitsgrad.', 'danger')
            return redirect(url_for('player.index'))
            
        if language not in ['de', 'en']:
            flash('Ungültige Sprache.', 'danger')
            return redirect(url_for('player.index'))

        try:
            all_questions = load_questions(language)
            if not all_questions:
                flash(f'Keine Fragen für die Sprache "{language}" gefunden!', 'danger')
                return redirect(url_for('player.index'))

            questions = [q for q in all_questions if
                         q.get('difficulty') == difficulty] if mode == 'difficulty' else all_questions

            if not questions:
                flash(f'Keine Fragen für den Schwierigkeitsgrad "{difficulty}" gefunden!', 'warning')
                return redirect(url_for('player.index'))

            # Ensure we have enough questions
            num_questions = min(10, len(questions))
            final_questions = random.sample(questions, num_questions)

            # Clear and set up new session
            session.clear()
            session['player_name'] = clean_name
            session['questions'] = final_questions
            session['current'] = 0
            session['score'] = 0
            session['quiz_started_at'] = time.time()
            session.permanent = True  # Enable session timeout

            logger.info(f"Solo quiz started by {clean_name}, {num_questions} questions, language: {language}")
            return redirect(url_for('player.quiz'))
            
        except Exception as e:
            logger.error(f"Error starting quiz: {e}")
            flash('Ein Fehler ist aufgetreten beim Starten des Quiz. Bitte versuche es erneut.', 'danger')
            return redirect(url_for('player.index'))

    # Bei Validierungsfehler zurück zum Index
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{error}", "danger")
    return redirect(url_for('player.index'))


@player_bp.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'questions' not in session:
        flash('Quiz-Session nicht gefunden. Bitte starte ein neues Quiz.', 'warning')
        return redirect(url_for('player.index'))

    if request.method == 'POST':
        raw_answer = request.form.get('answer', '')
        answer = sanitize_answer(raw_answer).strip()
        response_time = float(request.form.get('response_time', 30))
        is_timeout = request.form.get('timeout') == 'true'
        
        if not answer and not is_timeout:
            flash('Bitte gib eine Antwort ein!', 'warning')
            return redirect(url_for('player.quiz'))

        try:
            current_q = session['questions'][session['current']]
            correct_answer = str(current_q.get('answer', '')).strip().lower()
            question_timer = current_q.get('timer_seconds', 30)
            base_points = current_q.get('points', 100)

            was_correct = answer.lower() == correct_answer if not is_timeout else False
            points_earned = 0
            
            if was_correct:
                session['score'] += 1
                session['correct_streak'] = session.get('correct_streak', 0) + 1
                
                # Enhanced scoring with time bonus
                time_percentage = max(0, (question_timer - response_time) / question_timer)
                time_bonus = int(base_points * 0.5 * time_percentage)
                difficulty_multiplier = {
                    'easy': 1.0, 'medium': 1.2, 'hard': 1.5, 'heavy': 2.0
                }.get(current_q.get('difficulty', 'medium'), 1.0)
                
                points_earned = int((base_points + time_bonus) * difficulty_multiplier)
                session['total_points'] = session.get('total_points', 0) + points_earned
            else:
                session['correct_streak'] = 0

            # Store response time for analytics
            if 'response_times' not in session:
                session['response_times'] = []
            session['response_times'].append(response_time)

            session['feedback'] = {
                'was_correct': was_correct, 
                'correct_answer': current_q.get('answer'),
                'user_answer': raw_answer,
                'response_time': response_time,
                'points_earned': points_earned,
                'is_timeout': is_timeout,
                'streak': session.get('correct_streak', 0) if was_correct else 0
            }
            session['current'] += 1

        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error processing quiz answer: {e}")
            flash('Ein Fehler ist aufgetreten. Quiz wird neu gestartet.', 'danger')
            session.clear()
            return redirect(url_for('player.index'))

        return redirect(url_for('player.quiz'))

    if session.get('current', 0) >= len(session.get('questions', [])):
        return redirect(url_for('player.result'))

    question = session['questions'][session['current']]
    feedback = session.pop('feedback', None)  # Feedback nur einmal anzeigen

    return render_template('quiz.html', question=question, number=session['current'] + 1, feedback=feedback)


@player_bp.route('/result')
def result():
    if 'player_name' not in session or 'questions' not in session:
        flash('Quiz-Ergebnisse nicht verfügbar.', 'warning')
        return redirect(url_for('player.index'))

    name = session.get('player_name')
    score = session.get('score', 0)
    total = len(session.get('questions', []))
    percentage = (score / total * 100) if total > 0 else 0
    total_points = session.get('total_points', 0)
    best_streak = session.get('correct_streak', 0)
    response_times = session.get('response_times', [])
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Get or create user for achievement tracking
    user = get_user_or_create_guest(name)
    unlocked_achievements = []
    
    if user:
        # Update user statistics
        user.games_played += 1
        user.questions_answered += total
        user.correct_answers += score
        user.total_score += total_points
        user.best_streak = max(user.best_streak, best_streak)
        user.last_active = time.time()
        
        # Enhanced PlayerStats with new fields
        new_stat = PlayerStats(
            player_name=name, 
            score=score, 
            total_questions=total, 
            percentage=percentage,
            difficulty=session.get('difficulty', 'medium'),
            language=session.get('language', 'de'),
            avg_response_time=avg_response_time,
            streak=best_streak
        )
        db.session.add(new_stat)
        
        # Process achievements
        unlocked_achievements = process_achievements(user.id)
        
        db.session.commit()
        
        logger.info(f"Quiz completed by {name}: {score}/{total} ({percentage:.1f}%), {len(unlocked_achievements)} achievements unlocked")
    
    # Calculate performance metrics
    performance_data = {
        'accuracy': percentage,
        'speed_score': (30 - avg_response_time) / 30 * 100 if avg_response_time < 30 else 0,
        'streak_score': (best_streak / total * 100) if total > 0 else 0,
        'overall_grade': get_performance_grade(percentage, avg_response_time, best_streak)
    }

    return render_template('result.html', 
                         name=name, 
                         score=score, 
                         total=total, 
                         percentage=percentage,
                         total_points=total_points,
                         best_streak=best_streak,
                         avg_response_time=avg_response_time,
                         unlocked_achievements=unlocked_achievements,
                         performance_data=performance_data)

def get_performance_grade(accuracy, avg_response_time, streak):
    """Calculate overall performance grade."""
    if accuracy >= 90 and avg_response_time < 10:
        return 'S+'
    elif accuracy >= 80 and avg_response_time < 15:
        return 'A'
    elif accuracy >= 70 and avg_response_time < 20:
        return 'B'
    elif accuracy >= 60:
        return 'C'
    else:
        return 'D'
