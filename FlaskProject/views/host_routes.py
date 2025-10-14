# FlaskProject/views/host_routes.py

import random

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from database import db, Game, QuizSet, CustomQuestion
from game_logic import create_new_game, load_questions

host_bp = Blueprint('host', __name__)


@host_bp.route('/host')
def host_dashboard():
    quiz_sets = QuizSet.query.all()
    return render_template('host/dashboard.html', quiz_sets=quiz_sets)


@host_bp.route('/host/create-game', methods=['POST'])
def create_game():
    host_name = request.form.get('host_name', '').strip()
    if not host_name:
        flash('Bitte geben Sie einen Host-Namen ein!')
        return redirect(url_for('host.host_dashboard'))

    # NEU: Quiz-Set Auswahl
    quiz_source = request.form.get('quiz_source', 'default_de')
    max_questions = int(request.form.get('max_questions', 10))
    questions = []

    if quiz_source.startswith('default_'):
        language = quiz_source.split('_')[1]
        difficulty = request.form.get('difficulty', 'easy')
        all_questions = load_questions(language)

        if difficulty != 'mixed':
            questions = [q for q in all_questions if q.get('difficulty') == difficulty]
        else:
            questions = all_questions
    else:  # Eigenes Quiz-Set laden
        quiz_set_id = int(quiz_source)
        quiz_set = QuizSet.query.get(quiz_set_id)
        if quiz_set:
            set_questions = [{
                'question': q.question,
                'answer': q.answer,
                'options': q.options,
                'type': q.question_type,
                'difficulty': q.difficulty
            } for q in quiz_set.questions]
            questions = set_questions

    if not questions:
        flash('Keine Fragen für die Auswahl gefunden!')
        return redirect(url_for('host.host_dashboard'))

    final_questions = random.sample(questions, min(max_questions, len(questions)))
    new_game = create_new_game(host_name, final_questions)

    session['host_pin'] = new_game.pin
    session['is_host'] = True

    return redirect(url_for('host.host_lobby', pin=new_game.pin))


@host_bp.route('/host/lobby/<pin>')
def host_lobby(pin):
    from utils.network import get_network_urls
    from config import get_config
    
    game = Game.query.get(pin)
    if not game:
        flash('Spiel nicht gefunden!')
        return redirect(url_for('host.host_dashboard'))
    if session.get('host_pin') != pin:
        flash('Keine Berechtigung für dieses Spiel!')
        return redirect(url_for('host.host_dashboard'))
    
    players = game.players.all()  # Konvertiere zu Liste
    config = get_config()
    
    # Get all network URLs and QR codes
    network_urls = get_network_urls(port=config.FLASK_PORT)
    
    return render_template('host/lobby.html', 
                          game=game, 
                          pin=pin, 
                          players=players, 
                          network_urls=network_urls)


@host_bp.route('/host/control/<pin>')
def host_control(pin):
    game = Game.query.get(pin)
    if not game:
        flash('Spiel nicht gefunden!')
        return redirect(url_for('host.host_dashboard'))
    if session.get('host_pin') != pin:
        flash('Keine Berechtigung für dieses Spiel!')
        return redirect(url_for('host.host_dashboard'))
    return render_template('host/control.html', game=game, pin=pin)


# --- NEUE ROUTEN FÜR FRAGEN-EDITOR ---
@host_bp.route('/host/editor')
def editor_list():
    quiz_sets = QuizSet.query.order_by(QuizSet.created_at.desc()).all()
    return render_template('host/editor_list.html', quiz_sets=quiz_sets)


@host_bp.route('/host/editor/new', methods=['GET', 'POST'])
def create_quiz_set():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Bitte geben Sie einen Namen für das Quiz-Set ein.')
            return render_template('host/editor.html', quiz_set=None)

        new_set = QuizSet(name=name, author=session.get('player_name', 'Admin'))
        db.session.add(new_set)
        db.session.commit()
        return redirect(url_for('host.edit_quiz_set', set_id=new_set.id))

    return render_template('host/editor.html', quiz_set=None, question=None)


@host_bp.route('/host/editor/<int:set_id>', methods=['GET', 'POST'])
def edit_quiz_set(set_id):
    quiz_set = QuizSet.query.get_or_404(set_id)
    if request.method == 'POST':
        question_text = request.form.get('question', '').strip()
        answer_text = request.form.get('answer', '').strip()
        q_type = request.form.get('question_type')

        if not question_text or not answer_text:
            flash("Frage und Antwort dürfen nicht leer sein!")
            return render_template('host/editor.html', quiz_set=quiz_set, question=None)

        options = []
        if q_type == 'mc':
            options = [o.strip() for o in request.form.getlist('options') if o.strip()]
            if answer_text not in options:
                flash("Die korrekte Antwort muss eine der Optionen sein!")
                return render_template('host/editor.html', quiz_set=quiz_set, question=None)

        new_question = CustomQuestion(
            question=question_text,
            answer=answer_text,
            question_type=q_type,
            options=options,
            quiz_set_id=set_id
        )
        db.session.add(new_question)
        db.session.commit()
        return redirect(url_for('host.edit_quiz_set', set_id=set_id))

    return render_template('host/editor.html', quiz_set=quiz_set, question=None)


@host_bp.route('/host/editor/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    question = CustomQuestion.query.get_or_404(question_id)
    set_id = question.quiz_set_id
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('host.edit_quiz_set', set_id=set_id))


@host_bp.route('/host/editor/delete_set/<int:set_id>', methods=['POST'])
def delete_quiz_set(set_id):
    quiz_set = QuizSet.query.get_or_404(set_id)
    db.session.delete(quiz_set)
    db.session.commit()
    return redirect(url_for('host.editor_list'))
