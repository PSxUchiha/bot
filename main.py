import os
import sys
from flask import Flask, request, render_template, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Import our custom modules
from distro_detector import get_distro_info
from command_executor import execute_command, is_safe_command, filter_unnecessary_sudo
from ollama_interface import interpret_command
from user_info import get_user_info

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for sessions

# Get distribution and user info at startup
DISTRO_INFO = get_distro_info()
USER_INFO = get_user_info()

print(f"Detected system distribution:\n{DISTRO_INFO}")
print(f"User information:\n{USER_INFO}")

# Simulated user database (replace with a real database in production)
users = {
    "admin": generate_password_hash("adminpassword")
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    if username in users and check_password_hash(users[username], password):
        session['username'] = username
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/logout')
def logout():
    session.pop('username', None)
    return jsonify({"message": "Logged out successfully"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
@login_required
def execute():
    user_input = request.json.get('command', '')
    
    print(f"User input: {user_input}")
    
    # Interpret the natural language command using structured output
    command, notes = interpret_command(user_input, DISTRO_INFO, USER_INFO)
    print(f"Interpreted command: {command}")
    print(f"Notes: {notes}")
    
    # Check if command is safe and execute
    if not is_safe_command(command):
        result = "This command requires manual intervention for safety reasons."
    else:
        result = execute_command(command, USER_INFO)
    
    return jsonify({
        'interpreted_command': command,
        'notes': notes,
        'result': result
    })

def test_cli_mode():
    """Simple CLI mode for testing without web interface"""
    print("Command Assistant CLI Mode")
    print(f"System: {DISTRO_INFO.splitlines() if isinstance(DISTRO_INFO, str) else DISTRO_INFO}")
    
    while True:
        user_input = input("\nEnter command in natural language (or 'exit' to quit): ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        # Use structured output for command interpretation
        command, notes = interpret_command(user_input, DISTRO_INFO, USER_INFO)
        print(f"\nInterpreted command: {command}")
        
        if notes:
            print(f"Notes: {notes}")
        
        if not is_safe_command(command):
            print("This command requires manual intervention for safety reasons.")
            continue
            
        proceed = input("Execute this command? (y/n): ")
        if proceed.lower() != 'y':
            continue
            
        result = execute_command(command, USER_INFO)
        if isinstance(result, dict):
            print("\nOutput:")
            if result['stdout']:
                print(result['stdout'])
            if result['stderr']:
                print("Errors:")
                print(result['stderr'])
            print(f"Return code: {result['returncode']}")
        else:
            print(f"\nResult: {result}")

if __name__ == '__main__':
    # Check if CLI mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        test_cli_mode()
    else:
        print("Starting web interface on http://127.0.0.1:5000")
        app.run(debug=True)
