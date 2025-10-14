# 🎯 Interactive Quiz Game - Flask Application

A modern, interactive quiz application built with Flask that supports both solo and multiplayer quiz games. Features real-time gameplay with WebSockets, custom question sets, and a cyberpunk-style UI.

## ✨ Features

### Core Functionality
- **Solo Quiz Mode**: Individual quiz sessions with different difficulty levels
- **Multiplayer Games**: Real-time multiplayer quiz games with unique game PINs
- **Custom Question Sets**: Create and manage your own quiz questions
- **Multi-language Support**: German and English question sets
- **Real-time Updates**: WebSocket integration for live game updates
- **Responsive Design**: Works on desktop and mobile devices

### Security Features
- Input validation and sanitization
- CSRF protection
- Rate limiting
- Session security
- XSS prevention
- SQL injection protection

### Technical Features
- Modern Flask architecture with blueprints
- SQLAlchemy ORM with migrations
- Comprehensive test coverage
- Docker support (optional)
- Production-ready configuration

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd FlaskProject
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env file with your settings
   ```

5. **Initialize the database**
   ```bash
   python -m flask db init
   python -m flask db migrate -m "Initial migration"
   python -m flask db upgrade
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   Open your browser and navigate to `http://127.0.0.1:5000`

## 🎮 How to Use

### Solo Quiz
1. Go to the main page
2. Click "Solo spielen" (Solo Play)
3. Enter your name and select preferences
4. Start answering questions!

### Multiplayer Game
1. **Host a Game**:
   - Click "Quiz hosten" (Host Quiz)
   - Enter your name and configure game settings
   - Share the 6-digit PIN with players

2. **Join a Game**:
   - Click "PIN eingeben" (Enter PIN)
   - Enter the game PIN and your name
   - Wait for the host to start the game

### Custom Questions
1. Go to "Quiz hosten" → "Fragen-Editor"
2. Create a new quiz set
3. Add your custom questions
4. Use the quiz set when creating a game

## 🛠️ Development

### Project Structure
```
FlaskProject/
├── app.py              # Main application file
├── config.py           # Configuration management
├── extensions.py       # Flask extensions
├── database.py         # Database models
├── game_logic.py       # Core game functionality
├── requirements.txt    # Python dependencies
├── views/             # Route blueprints
│   ├── api_routes.py
│   ├── host_routes.py
│   └── player_routes.py
├── utils/             # Utility functions
│   ├── network.py
│   └── security.py
├── templates/         # HTML templates
├── static/           # CSS, JS, images
├── tests/            # Test files
└── instance/         # Instance-specific files
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest -m "unit"      # Unit tests only
pytest -m "integration"  # Integration tests only
pytest -m "security"     # Security tests only
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .

# Type checking (if using mypy)
mypy .
```

## 🔧 Configuration

### Environment Variables
Key environment variables (see `.env.example` for full list):

- `FLASK_SECRET_KEY`: Secret key for session encryption
- `FLASK_ENV`: Environment (development/production)
- `DATABASE_URL`: Database connection string
- `FLASK_HOST`: Host address (0.0.0.0 for network access)
- `FLASK_PORT`: Port number (default: 5000)

### Database Configuration
The application uses SQLite by default. For production, configure a PostgreSQL or MySQL database:

```env
DATABASE_URL=postgresql://user:password@localhost/quiz_app
```

### Security Configuration
For production deployment:

```env
FLASK_ENV=production
SSL_ENABLED=True
SESSION_COOKIE_SECURE=True
RATELIMIT_DEFAULT=50 per hour
```

## 📊 Database Schema

### Main Tables
- **games**: Quiz game instances with PINs and questions
- **players**: Player information and scores
- **quiz_sets**: Custom question collections
- **custom_questions**: Individual questions in quiz sets
- **player_stats**: Statistics for solo games

### Relationships
- Game → Players (One-to-Many)
- QuizSet → CustomQuestions (One-to-Many)

## 🚀 Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker
```dockerfile
# Dockerfile example
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 🧪 Testing

The project includes comprehensive tests:

- **Unit Tests**: Test individual functions and components
- **Integration Tests**: Test complete workflows
- **Security Tests**: Test security measures and validation
- **API Tests**: Test API endpoints and responses

### Test Coverage
- Game logic functions
- Database models and relationships
- API endpoints and security
- Input validation and sanitization
- Complete user workflows

## 🔒 Security Features

- **Input Validation**: All user inputs are validated and sanitized
- **CSRF Protection**: Forms protected against cross-site request forgery
- **Rate Limiting**: API endpoints protected against abuse
- **Session Security**: Secure session handling with timeouts
- **XSS Prevention**: Output escaping and content security policies
- **SQL Injection Protection**: Parameterized queries with SQLAlchemy

## 📝 API Documentation

### Network Info
- `GET /api/network-info` - Get server network information

### Host Game Control
- `POST /api/host/<pin>/start-question` - Start current question
- `POST /api/host/<pin>/show-results` - Show question results
- `POST /api/host/<pin>/next-question` - Advance to next question

All host API endpoints require valid host session authentication.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation as needed
- Ensure security best practices

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Roadmap

- [ ] User accounts and persistent statistics
- [ ] More question types (image, audio)
- [ ] Advanced game modes (team play, tournaments)
- [ ] Mobile app development
- [ ] Analytics dashboard for hosts
- [ ] Internationalization improvements

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check DATABASE_URL in .env
   - Ensure database server is running
   - Run migrations: `flask db upgrade`

2. **Port Already in Use**
   - Change FLASK_PORT in .env
   - Kill existing process: `pkill -f python`

3. **Template Not Found**
   - Ensure templates directory exists
   - Check template file names and paths

4. **WebSocket Connection Failed**
   - Check firewall settings
   - Verify SocketIO client version compatibility

For more help, please open an issue on the repository.

---
Made with ❤️ and Flask