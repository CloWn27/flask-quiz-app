# FlaskProject/views/api_routes.py - Refactored

import logging

from flask import Blueprint, jsonify, session

from extensions import socketio
from game_logic import (
    start_question,
    calculate_scores_for_question,
    get_leaderboard,
    advance_to_next_question
)
from utils.network import get_network_info

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/network-info')
def network_info():
    """API endpoint for network information with improved error handling."""
    try:
        info = get_network_info()
        logger.debug(f"Network info requested: {info}")
        return jsonify(info)
    except Exception as e:
        logger.error(f"Critical error in network detection: {e}")
        fallback_info = {'local_ip': '127.0.0.1', 'error': 'Network detection failed'}
        return jsonify(fallback_info), 500


def _validate_host_session(pin: str) -> bool:
    """Validate host session for game operations."""
    if session.get('host_pin') != pin:
        security_logger.warning(
            f"Unauthorized host operation attempted for game {pin} "
            f"by session {session.get('host_pin', 'none')}"
        )
        return False
    return True


@api_bp.route('/api/host/<pin>/start-question', methods=['POST'])
def start_question_api(pin):
    """Start a question with improved security and error handling."""
    if not _validate_host_session(pin):
        return jsonify({'error': 'Unauthorized', 'message': 'Invalid host session'}), 403

    try:
        game = start_question(pin)
        if not game:
            logger.warning(f"Failed to start question for game {pin}")
            return jsonify({'error': 'Game not found or finished'}), 404

        # Emit to all players in the game room
        socketio.emit('question_started', {
            'question': game.questions[game.current_question],
            'question_number': game.current_question + 1,
            'total_questions': len(game.questions)
        }, room=pin)

        logger.info(f"Question {game.current_question + 1} started for game {pin}")
        return jsonify({
            'success': True,
            'question_number': game.current_question + 1
        })

    except Exception as e:
        logger.error(f"Error starting question for game {pin}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/api/host/<pin>/show-results', methods=['POST'])
def show_results_api(pin):
    """Show question results with improved error handling."""
    if not _validate_host_session(pin):
        return jsonify({'error': 'Unauthorized', 'message': 'Invalid host session'}), 403

    try:
        game = calculate_scores_for_question(pin)
        if not game:
            logger.warning(f"Failed to calculate scores for game {pin}")
            return jsonify({'error': 'Game not found'}), 404

        if game.current_question >= len(game.questions):
            return jsonify({'error': 'Invalid question index'}), 400

        correct_answer = game.questions[game.current_question]['answer']
        leaderboard_data = get_leaderboard(pin)
        leaderboard = [
            {'id': p.id, 'name': p.name, 'score': p.score}
            for p in leaderboard_data
        ]

        # Emit results to all players
        socketio.emit('results_shown', {
            'correct_answer': correct_answer,
            'leaderboard': leaderboard
        }, room=pin)

        logger.info(f"Results shown for question {game.current_question + 1} in game {pin}")
        return jsonify({
            'success': True,
            'correct_answer': correct_answer,
            'leaderboard_count': len(leaderboard)
        })

    except Exception as e:
        logger.error(f"Error showing results for game {pin}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/api/host/<pin>/next-question', methods=['POST'])
def next_question_api(pin):
    """Advance to next question with improved state management."""
    if not _validate_host_session(pin):
        return jsonify({'error': 'Unauthorized', 'message': 'Invalid host session'}), 403

    try:
        game = advance_to_next_question(pin)
        if not game:
            logger.warning(f"Failed to advance question for game {pin}")
            return jsonify({'error': 'Game not found'}), 404

        response_data = {
            'success': True,
            'state': game.state,
            'question_number': game.current_question + 1
        }

        if game.state == 'finished':
            leaderboard_data = get_leaderboard(pin)
            leaderboard = [
                {'id': p.id, 'name': p.name, 'score': p.score}
                for p in leaderboard_data
            ]

            socketio.emit('game_finished', {
                'leaderboard': leaderboard
            }, room=pin)

            response_data['final_leaderboard'] = leaderboard
            logger.info(f"Game {pin} finished with {len(leaderboard)} players")
        else:
            logger.info(f"Game {pin} advanced to question {game.current_question + 1}")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error advancing to next question for game {pin}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
