# FlaskProject/socketio_events.py - SocketIO Event Handlers

import logging

from flask import session, request
from flask_socketio import emit, join_room, leave_room

from database import Game
from extensions import socketio
from game_logic import submit_answer

logger = logging.getLogger(__name__)

# Dictionary to track connected players and their rooms
connected_players = {}


@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection."""
    client_id = request.sid
    logger.info(f"Client connected: {client_id}")
    
    # Send connection confirmation
    emit('connected', {'message': 'Successfully connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    client_id = request.sid
    logger.info(f"Client disconnected: {client_id}")
    
    # Clean up player from tracking
    if client_id in connected_players:
        room = connected_players[client_id].get('room')
        if room:
            leave_room(room)
        del connected_players[client_id]


@socketio.on('join_room')
def handle_join_room(data):
    """Handle player joining a game room."""
    client_id = request.sid
    pin = data.get('pin')
    
    if not pin:
        logger.warning(f"Client {client_id} attempted to join room without PIN")
        emit('error', {'message': 'Game PIN is required'})
        return
    
    try:
        # Verify the game exists
        game = Game.query.get(pin)
        if not game:
            logger.warning(f"Client {client_id} attempted to join non-existent game {pin}")
            emit('error', {'message': 'Game not found'})
            return
        
        # Join the room
        join_room(pin)
        
        # Track the player
        import time
        connected_players[client_id] = {
            'room': pin,
            'joined_at': time.time()
        }
        
        # Send confirmation
        emit('room_joined', {
            'pin': pin,
            'message': f'Successfully joined game {pin}',
            'game_state': game.state
        })
        
        # Get player info from session if available
        player_name = session.get('player_name', 'Unknown Player')
        
        # Notify other players in the room
        emit('player_connected', {
            'message': f'{player_name} connected to the game',
            'total_players': game.players.count()
        }, include_self=False)
        
        logger.info(f"Client {client_id} ({player_name}) successfully joined room {pin}")
        
    except Exception as e:
        logger.error(f"Error handling join_room for client {client_id}: {e}")
        emit('error', {'message': 'Failed to join game room'})


@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle player leaving a game room."""
    client_id = request.sid
    pin = data.get('pin')
    
    if not pin:
        emit('error', {'message': 'Game PIN is required'})
        return
    
    try:
        leave_room(pin)
        
        # Clean up tracking
        if client_id in connected_players:
            del connected_players[client_id]
        
        player_name = session.get('player_name', 'Unknown Player')
        
        # Notify other players
        emit('player_disconnected', {
            'message': f'{player_name} left the game'
        }, room=pin, include_self=False)
        
        emit('room_left', {'pin': pin})
        logger.info(f"Client {client_id} ({player_name}) left room {pin}")
        
    except Exception as e:
        logger.error(f"Error handling leave_room for client {client_id}: {e}")
        emit('error', {'message': 'Failed to leave game room'})


@socketio.on('submit_answer')
def handle_submit_answer(data):
    """Handle player answer submission."""
    client_id = request.sid
    
    try:
        pin = data.get('pin')
        answer = data.get('answer')
        response_time = data.get('response_time', 30)
        
        if not pin or answer is None:
            emit('error', {'message': 'PIN and answer are required'})
            return
        
        # Get player info from session
        player_id = session.get('player_id')
        if not player_id:
            emit('error', {'message': 'Player not authenticated'})
            return
        
        # Submit the answer
        success = submit_answer(pin, player_id, answer, response_time)
        
        if success:
            emit('answer_submitted', {
                'message': 'Answer submitted successfully',
                'answer': answer,
                'response_time': response_time
            })
            
            player_name = session.get('player_name', 'Player')
            logger.info(f"Player {player_name} ({player_id}) submitted answer for game {pin}")
        else:
            emit('answer_error', {'message': 'Failed to submit answer'})
            
    except Exception as e:
        logger.error(f"Error handling submit_answer for client {client_id}: {e}")
        emit('error', {'message': 'Failed to submit answer'})


@socketio.on('ping')
def handle_ping():
    """Handle ping/pong for connection health check."""
    emit('pong')


@socketio.on('get_game_status')
def handle_get_game_status(data):
    """Handle request for current game status."""
    client_id = request.sid
    pin = data.get('pin')
    
    if not pin:
        emit('error', {'message': 'Game PIN is required'})
        return
    
    try:
        game = Game.query.get(pin)
        if not game:
            emit('error', {'message': 'Game not found'})
            return
        
        status = {
            'pin': pin,
            'state': game.state,
            'current_question': game.current_question + 1,
            'total_questions': len(game.questions),
            'total_players': game.players.count()
        }
        
        emit('game_status', status)
        
    except Exception as e:
        logger.error(f"Error getting game status for client {client_id}: {e}")
        emit('error', {'message': 'Failed to get game status'})


# Error handler
@socketio.on_error_default
def default_error_handler(e):
    """Handle SocketIO errors."""
    client_id = request.sid
    logger.error(f"SocketIO error for client {client_id}: {e}")
    emit('error', {'message': 'An unexpected error occurred'})