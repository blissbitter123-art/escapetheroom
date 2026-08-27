import os
import socket

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'event.db')
SCHEMA_PATH = os.path.join(DATABASE_DIR, 'schema.sql')

SECRET_KEY = os.environ.get('SECRET_KEY', 'final-60-escape-room-secret-key-2026')
HOST_PASSWORD = os.environ.get('HOST_PASSWORD', 'apnakaamkr420')

EVENT_CONFIG_PATH = os.path.join(DATA_DIR, 'event_config.json')
TEAMS_DATA_PATH = os.path.join(DATA_DIR, 'teams.json')
CHALLENGES_DATA_PATH = os.path.join(DATA_DIR, 'challenges.json')

def get_local_ip():
    """Find local IPv4 address for LAN connectivity."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually connect, used to find interface IP
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

LOCAL_IP = get_local_ip()
PORT = 5000
