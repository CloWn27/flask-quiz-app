# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is an interactive Flask-based quiz application with real-time multiplayer capabilities. The application supports:
- Solo quiz gameplay with different difficulty levels
- Multiplayer quiz sessions with PIN-based joining
- Custom question creation and management
- Real-time communication via Socket.IO
- Multi-language support (German/English)
- Host dashboard for game management

## Development Setup

### Prerequisites
- Python 3.8+
- Virtual environment (located in `.venv/`)
- Dependencies in virtual environment include: Flask, Flask-SocketIO, Flask-WTF, Flask-SQLAlchemy, Flask-Migrate, etc.

### Environment Configuration
1. Copy `.env.example` to `.env`
2. Generate secure keys: `flask generate-secrets` (if command exists)
3. Configure database URL, rate limiting, and security settings as needed

### Running the Application

**⚠️ MISSING MAIN APPLICATION FILE**
The main application entry point (`app.py`, `main.py`, or `run.py`) is not present in this directory. You'll need to create or locate the main Flask application file that:
- Initializes the Flask app
- Configures extensions (database, socketio, migrations, etc.)
- Registers blueprints from the `views/` directory
- Sets up logging and security configurations

### Basic Development Commands
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run development server (once main app file exists)
flask run
# OR
python app.py

# Database operations (Flask-Migrate)
flask db init
flask db migrate -m "Migration message"
flask db upgrade

# Run tests (if test files exist)
pytest
# OR
python -m pytest tests/
```

## Architecture Overview

### Directory Structure
```
FlaskProject/
├── views/                  # Blueprint route handlers
│   ├── api_routes.py      # REST API endpoints for game operations
│   ├── host_routes.py     # Host dashboard and game management
│   └── player_routes.py   # Player joining and quiz gameplay
├── templates/             # Jinja2 HTML templates
│   ├── host/             # Host dashboard templates
│   └── player/           # Player game interface templates
├── static/css/           # Stylesheets (Kahoot-style UI)
├── questions_*.json      # Question banks (German/English)
└── .env.example         # Environment configuration template
```

### Key Components

#### Missing Core Files
The following essential files are referenced in imports but missing:
- **Main application file** (`app.py` or similar) - Flask app factory and configuration
- `extensions.py` - Flask extension initialization (db, socketio, etc.)
- `game_logic.py` - Core game mechanics and state management
- `config.py` - Application configuration management
- `database.py` - SQLAlchemy models (Game, Player, QuizSet, etc.)
- `utils/security.py` - Input validation and security utilities
- `utils/network.py` - Network information utilities

#### Application Flow
1. **Solo Mode**: Player creates session → Questions loaded from JSON → Real-time quiz interface
2. **Multiplayer**: Host creates game with PIN → Players join via PIN → Real-time synchronized gameplay
3. **Custom Questions**: Host creates question sets → Stored in database → Available for game creation

### Database Models (Inferred)
- `Game`: Stores game sessions with PIN, state, questions
- `Player`: Player information and scores
- `QuizSet`: Custom question collections
- `CustomQuestion`: Individual questions within sets
- `PlayerStats`: Historical performance data

### Key Features
- **Security**: CSRF protection, input validation, rate limiting, session management
- **Real-time**: Socket.IO for live game updates and player synchronization
- **Internationalization**: Multi-language question support (German/English)
- **Responsive UI**: Cyberpunk/Kahoot-inspired styling
- **Question Types**: Multiple choice and text input questions

## Development Notes

### Security Considerations
- Rate limiting enabled by default
- Session security with HTTP-only cookies
- Input validation for all user inputs
- CORS configuration for multi-device access

### Game Mechanics
- PIN-based game joining (6-digit codes)
- Real-time player synchronization
- Scoring system with leaderboards
- Question progression and result display
- Support for up to 50 players per game (configurable)

### Testing Strategy
- Test individual route handlers in `views/`
- Test game logic functions
- Test real-time Socket.IO events
- Test database operations and migrations
- Test security validation functions

### Common Development Tasks

#### Adding New Question Types
1. Update question JSON structure
2. Modify templates for new UI components
3. Update game logic for scoring
4. Add validation in `utils/security.py`

#### Extending Multiplayer Features
1. Add new Socket.IO event handlers
2. Update game state management
3. Modify client-side JavaScript
4. Test real-time synchronization

#### Adding New Languages
1. Create new `questions_[lang].json` file
2. Update language selection in templates
3. Add localization for UI elements
4. Update `load_questions()` function

## Production Deployment

### Environment Variables
Key production settings in `.env`:
- `FLASK_ENV=production`
- `SSL_ENABLED=True`
- `SESSION_COOKIE_SECURE=True`
- `RATELIMIT_STORAGE_URL=redis://localhost:6379/0`

### Database
- SQLite for development
- PostgreSQL recommended for production
- Regular backups of question sets and player stats

### Performance
- Redis for session storage and rate limiting
- Database connection pooling
- Static file serving via CDN