# FlaskProject/views/player_routes.py - Refactored with improved security

import logging
import random
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, RadioField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

from config import get_config
from database import db, Game, Player, PlayerStats
from game_logic import load_questions, add_player_to_game
from utils.security import validate_pin, validate_player_name

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')
config = get_config()

player_bp = Blueprint('player', __name__)


# ... (Rest der Datei ist unverändert)
# --- Formulare (Flask-WTF für Sicherheit und Validierung) ---

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
    return render_template('stats.html', stats=all_stats)


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
        name = form.player_name.data.strip()
        mode = form.mode.data
        difficulty = form.difficulty.data
        language = form.language.data

        all_questions = load_questions(language)
        if not all_questions:
            flash(f'Keine Fragen für die Sprache "{language}" gefunden!', 'danger')
            return redirect(url_for('player.index'))

        questions = [q for q in all_questions if
                     q.get('difficulty') == difficulty] if mode == 'difficulty' else all_questions

        if not questions:
            flash(f'Keine Fragen für den Schwierigkeitsgrad "{difficulty}" gefunden!', 'warning')
            return redirect(url_for('player.index'))

        final_questions = random.sample(questions, min(10, len(questions)))

        session.clear()
        session['player_name'] = name
        session['questions'] = final_questions
        session['current'] = 0
        session['score'] = 0

        return redirect(url_for('player.quiz'))

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
        answer = request.form.get('answer', '').strip()
        if not answer:
            flash('Bitte gib eine Antwort ein!', 'warning')
            return redirect(url_for('player.quiz'))

        current_q = session['questions'][session['current']]
        correct_answer = str(current_q.get('answer', '')).strip().lower()

        was_correct = answer.lower() == correct_answer
        if was_correct:
            session['score'] += 1

        session['feedback'] = {'was_correct': was_correct, 'correct_answer': current_q.get('answer')}
        session['current'] += 1

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

    new_stat = PlayerStats(
        player_name=name, score=score, total_questions=total, percentage=percentage
    )
    db.session.add(new_stat)
    db.session.commit()

    return render_template('result.html', name=name, score=score, total=total)
