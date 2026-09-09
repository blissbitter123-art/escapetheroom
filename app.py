import os
import sys
import logging
from flask import Flask
from config import SECRET_KEY, LOCAL_IP, PORT, UPLOADS_DIR, MAX_UPLOAD_SIZE
from database import init_db
from game.game_engine import GameEngine

# Import Blueprints
from routes.host_routes import host_bp
from routes.projector_routes import projector_bp
from routes.team_routes import team_bp
from routes.api_routes import api_bp
from routes.game_routes import game_bp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('app')

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

    # Ensure uploads directory exists
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Register custom Jinja filters
    import json
    app.jinja_env.filters['from_json'] = lambda s: json.loads(s) if s else []

    # Register blueprints
    app.register_blueprint(game_bp)
    app.register_blueprint(host_bp)
    app.register_blueprint(projector_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(api_bp)

    # Initialize Database & Engine
    init_db()
    GameEngine.initialize()

    return app

app = create_app()

if __name__ == '__main__':
    print("=" * 65)
    print("        ESCAPE THE ROOM: THE FINAL 60 - GAME SHOW SERVER        ")
    print("=" * 65)
    print(f" HOST CONTROL PANEL:   http://127.0.0.1:{PORT}/control")
    print(f" PROJECTOR DISPLAY:    http://127.0.0.1:{PORT}/projector")
    print(f" TEAM DEVICE LAN URL:  http://{LOCAL_IP}:{PORT}/team/login")
    print("=" * 65)
    print(" Server running locally over Wi-Fi/LAN (Offline First mode)...")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
