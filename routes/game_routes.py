from flask import Blueprint, render_template, redirect, url_for
from config import LOCAL_IP, PORT

game_bp = Blueprint('game', __name__)

@game_bp.route('/')
def index():
    """Main landing hub providing clear direct links to Host, Projector, and Team views."""
    return render_template('index.html', local_ip=LOCAL_IP, port=PORT)

@game_bp.route('/control')
def control():
    """Shortcut redirect to /host/dashboard."""
    return redirect(url_for('host.dashboard'))
