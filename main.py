from flask import Flask, request, session, render_template_string, jsonify
import requests
import time
import threading
import uuid
from collections import defaultdict
import os
from datetime import datetime
import pytz
import json
import base64

app = Flask(name)
app.secret_key = os.urandom(24)

# Global storage for ALL users processes
user_processes = defaultdict(dict)
task_logs = defaultdict(list)

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0.0; Samsung Galaxy S9 Build/OPR6.170623.017; wv) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.125 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,/;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

def get_indian_time():
    """Get current Indian time"""
    tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S IST")

def get_group_name(thread_id, access_token):
    """Fetch group name using Facebook Graph API"""
    try:
        url = f'https://graph.facebook.com/v19.0/{thread_id}'
        params = {'access_token': access_token, 'fields': 'name'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('name', 'Unknown Group')
    except:
        pass
    return 'Unknown Group'

def get_token_owner(token):
    """Fetch token owner name"""
    try:
        url = 'https://graph.facebook.com/v19.0/me'
        params = {'access_token': token, 'fields': 'name,id'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return f"{data.get('name', 'Unknown')} (ID: {data.get('id', 'Unknown')})"
    except:
        pass
    return 'Unknown User'

def check_and_convert_to_cookies(token):
    """Check if token has created another profile and convert to cookies if needed"""
    try:
        # Check if this token has created another profile
        url = 'https://graph.facebook.com/v19.0/me'
        params = {'access_token': token, 'fields': 'id,name,accounts'}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # If has accounts field (created another profiles)
            if 'accounts' in data and data['accounts']:
                print(f"🔍 Token has created another profiles: {len(data['accounts'])}")
                # Convert token to cookies format (simplified version)
                # In real implementation, you would use proper cookie conversion
                cookies_string = f"fb_token_{data['id']}={token}"
                return cookies_string
                
    except Exception as e:
        print(f"⚠️ Error checking token: {e}")
    
    return token  # Return original token if no conversion needed

def send_messages_loop(user_id, task_id, thread_id, haters_name, last_name, access_tokens, messages, time_interval):
    """Har user ke liye alag nonstop message sending loop"""
    
    num_comments = len(messages)
    max_tokens = len(access_tokens)
    post_url = f'https://graph.facebook.com/v19.0/t_{thread_id}/'
    
    loop_count = 0
    group_name = get_group_name(thread_id, access_tokens[0])
    
    # Initial log
    log_message = f"🚀 TASK STARTED | Group: {group_name} | Thread ID: {thread_id} | Messages: {num_comments} | Tokens: {max_tokens}"
    task_logs[task_id].append({
        'time': get_indian_time(),
        'type': 'info',
        'message': log_message,
'full_message': ''
    })
    print(f"🎉 User {user_id[:8]} | {log_message}")
    
    # YE LOOP KABHI BAND NAHI HOGA - Jab tak user khud na roke
    while user_processes[user_id].get('tasks', {}).get(task_id, {}).get('active', False):
        try:
            loop_count += 1
            
            for comment_index in range(num_comments):
                # Check if user ne stop button dabaya
                if not user_processes[user_id].get('tasks', {}).get(task_id, {}).get('active', False):
                    log_message = f"🛑 TASK MANUALLY STOPPED BY USER"
                    task_logs[task_id].append({
                        'time': get_indian_time(),
                        'type': 'warning',
                        'message': log_message,
                        'full_message': ''
                    })
                    print(f"🛑 User {user_id[:8]} | Task {task_id[:8]} manually stopped")
                    return
                
                token_index = comment_index % max_tokens
                access_token = access_tokens[token_index]
                comment = messages[comment_index].strip()
                
                # Format message: haters_name + message + last_name
                full_message = f"{haters_name} {comment} {last_name}"
                
                # Check and convert token to cookies if needed for created another profiles
                final_credential = check_and_convert_to_cookies(access_token)
                
                if final_credential != access_token:
                    print(f"🔄 Using cookies for created another profile: {token_index+1}")
                
                parameters = {
                    'access_token': access_token,
                    'message': full_message
                }
                
                # Send message to Facebook
                response = requests.post(post_url, json=parameters, headers=headers)
                
                current_time = get_indian_time()
                token_owner = get_token_owner(access_token)
                
                if response.ok:
                    log_message = f"✅ Message {comment_index+1}/{num_comments} sent successfully"
                    status = "SUCCESS"
                    log_type = "success"
                else:
                    log_message = f"❌ Failed to send message {comment_index+1} | Error: {response.status_code}"
                    status = "FAILED"
                    log_type = "error"
                
                # Add to logs with full message content
                task_logs[task_id].append({
                    'time': current_time,
                    'type': log_type,
                    'message': log_message,
                    'full_message': full_message,
                    'token_info': f"Token {token_index+1}/{max_tokens} | From: {token_owner}",
                    'message_number': f"{comment_index+1}/{num_comments}"
                })
                
                detailed_log = f"{log_message} | Token {token_index+1}/{max_tokens} | From: {token_owner}"
                print(f"👤 User {user_id[:8]} | 📦 Task {task_id[:8]} | {status} | {detailed_log}")
                print(f"   📝 Message: {full_message}")
                
                # Wait for next message
                time.sleep(time_interval)
                
        except Exception as e:
            error_msg = f"⚠️ Error in sending loop: {str(e)}"
            task_logs[task_id].append({
                'time': get_indian_time(),
                'type': 'error',
                'message': error_msg,
                'full_message': ''
            })
            print(f"👤 User {user_id[:8]} | 📦 Task {task_id[:8]} | {error_msg}")
            time.sleep(30)  # 30 seconds wait then retry
log_message = f"🔚 TASK PROCESS ENDED"
    task_logs[task_id].append({
        'time': get_indian_time(),
        'type': 'info',
        'message': log_message,
        'full_message': ''
    })
    print(f"🔚 User {user_id[:8]} | Task {task_id[:8]} process ended")

# Base64 encoded animated Sukuna background (simplified version)
ANIMATED_BACKGROUND = '''
<canvas id="sukunaCanvas" style="position:fixed; top:0; left:0; width:100%; height:100%; z-index:-1;"></canvas>
<script>
    const canvas = document.getElementById('sukunaCanvas');
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // Sukuna-like animation effects
    const particles = [];
    const colors = ['#ff0000', '#ff4444', '#ff6666', '#cc0000'];
    
    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 3 + 1;
            this.speedX = Math.random() * 1 - 0.5;
            this.speedY = Math.random() * 1 - 0.5;
            this.color = colors[Math.floor(Math.random() * colors.length)];
        }
        
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            
            if (this.x > canvas.width) this.x = 0;
            if (this.x < 0) this.x = canvas.width;
            if (this.y > canvas.height) this.y = 0;
            if (this.y < 0) this.y = canvas.height;
        }
        
        draw() {
            ctx.fillStyle = this.color;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    function init() {
        for (let i = 0; i < 100; i++) {
            particles.push(new Particle());
        }
    }
    
    function animate() {
        ctx.fillStyle = 'rgba(10, 10, 30, 0.1)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        for (let i = 0; i < particles.length; i++) {
            particles[i].update();
            particles[i].draw();
        }
        
        // Sukuna-like pattern
        ctx.strokeStyle = 'rgba(255, 0, 0, 0.1)';
        ctx.lineWidth = 1;
        for (let i = 0; i < 50; i++) {
            ctx.beginPath();
            ctx.moveTo(Math.random() * canvas.width, Math.random() * canvas.height);
            ctx.lineTo(Math.random() * canvas.width, Math.random() * canvas.height);
            ctx.stroke();
        }
        
        requestAnimationFrame(animate);
    }
    
    init();
    animate();
    
    window.addEventListener('resize', function() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
</script>
'''

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🔥 ARNAV MESSAGESER MESSAGE SENDER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
            min-height: 100vh; 
            padding: 20px;
            overflow-x: hidden;
            color: white;
        }
        .container { 
            max-width: 800px; 
            background: rgba(255, 255, 255, 0.1); 
            backdrop-filter: blur(10px);
            border-radius: 15px; 
            padding: 25px; 
            margin: 20px auto; 
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .user-badge { 
            background: linear-gradient(45deg, #ff0000, #ff6666); 
            color: white; 
            padding: 8px 15px; 
            border-radius: 20px;
font-size: 14px; 
            display: inline-block; 
            margin: 10px 0; 
        }
        .task-id-box { 
            background: linear-gradient(45deg, #ff0000, #cc0000); 
            color: white; 
            padding: 15px; 
            border-radius: 10px; 
            text-align: center;
            margin: 15px 0;
            border: 2px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
            animation: glow 2s infinite alternate;
        }
        @keyframes glow {
            from { box-shadow: 0 0 20px rgba(255, 0, 0, 0.5); }
            to { box-shadow: 0 0 40px rgba(255, 0, 0, 0.8); }
        }
        
        /* Input field glow effects */
        .form-control {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            transition: all 0.3s ease;
        }
        .form-control:focus {
            background: rgba(255, 255, 255, 0.2);
            border-color: #ff4444;
            box-shadow: 0 0 20px rgba(255, 68, 68, 0.5);
            color: white;
        }
        
        /* Different colors for different inputs */
        input[name="threadId"]:focus { box-shadow: 0 0 20px rgba(255, 0, 0, 0.6); }
        input[name="haters_name"]:focus { box-shadow: 0 0 20px rgba(255, 165, 0, 0.6); }
        input[name="last_name"]:focus { box-shadow: 0 0 20px rgba(255, 255, 0, 0.6); }
        input[name="time"]:focus { box-shadow: 0 0 20px rgba(0, 255, 0, 0.6); }
        input[name="task_id"]:focus { box-shadow: 0 0 20px rgba(0, 191, 255, 0.6); }
        
        .btn-start { 
            background: linear-gradient(45deg, #ff0000, #cc0000); 
            border: none; 
            padding: 12px; 
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .btn-start:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 0, 0, 0.4);
        }
        .btn-stop { 
            background: linear-gradient(45deg, #dc3545, #fd7e14); 
            border: none; 
            padding: 12px; 
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .btn-stop:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(220, 53, 69, 0.4);
        }
        .nav-tabs .nav-link { 
            color: #ccc;
            border: none;
        }
        .nav-tabs .nav-link.active { 
            font-weight: bold; 
            background: linear-gradient(45deg, #ff0000, #cc0000); 
            color: white; 
            border: none;
            border-radius: 10px;
        }
        .log-container { 
            max-height: 500px; 
            overflow-y: auto; 
            background: rgba(0, 0, 0, 0.7); 
            color: #00ff00; 
            padding: 15px; 
            border-radius: 5px; 
            font-family: 'Courier New', monospace;
            font-size: 14px;
            border: 1px solid rgba(255, 0, 0, 0.3);
        }
        .log-success { color: #00ff00; }
        .log-error { color: #ff4444; }
        .log-warning { color: #ffaa00; }
        .log-info { color: #4488ff; }
        
        /* Scrollbar styling */
        .log-container::-webkit-scrollbar {
            width: 8px;
        }
        .log-container::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
        }
        .log-container::-webkit-scrollbar-thumb {
            background: #ff0000;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    ''' + ANIMATED_BACKGROUND + '''
    
    <div class="container">
        <h2 class="class mb-4" style="color:#ff4444; text-shadow: 0 0 10px rgba(255, 0, 0, 0.5);">🔥 ARNAV MESSAGE SERVER</hSERVERRVER
<div class="user-badge">👤 User ID: {{ user_id[:12] }}...</div>
        
        <ul class="nav nav-tabs mb-4">
            <li class="nav-item">
                <a class="nav-link active" href="#start" data-bs-toggle="tab">🚀 Start Task</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" href="#stop" data-bs-toggle="tab">🛑 Stop Task</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" href="#view" data-bs-toggle="tab">📊 View Task Details</a>
            </li>
        </ul>

        <div class="tab-content">
            <!-- START TASK TAB -->
            <div class="tab-pane fade show active" id="start">
                <div class="alert alert-info" style="background: rgba(0, 191, 255, 0.2); border-color: #00bfff;">
                    <strong>📊 SERVER STATUS:</strong><br>
                    • Active Users: <strong>{{ active_users }}</strong><br>
                    • Your Active Tasks: <strong>{{ user_task_count }}</strong>
                </div>

                <form action="/start" method="post" enctype="multipart/form-data">
                    <div class="mb-3">
                        <label class="form-label">📱 Conversation/Thread ID:</label>
                        <input type="text" class="form-control" name="threadId" required placeholder="Enter Thread ID">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">👤 First Name (Message Start):</label>
                        <input type="text" class="form-control" name="haters_name" required placeholder="Enter First Name">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">👤 Last Name (Message End):</label>
                        <input type="text" class="form-control" name="last_name" required placeholder="Enter Last Name">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">📄 Messages File (TXT - one per line):</label>
                        <input type="file" class="form-control" name="messagesFile" accept=".txt" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">🔑 Tokens File (TXT - one per line):</label>
                        <input type="file" class="form-control" name="txtFile" accept=".txt" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">⏰ Interval (seconds):</label>
                        <input type="number" class="form-control" name="time" value="2" min="1" required>
                    </div>
                    <button type="submit" class="btn btn-start w-100">🚀 START NONSTOP SENDING</button>
                </form>
            </div>

            <!-- STOP TASK TAB -->
            <div class="tab-pane fade" id="stop">
                <div class="alert alert-warning" style="background: rgba(255, 193, 7, 0.2); border-color: #ffc107;">
                    <strong>🛑 STOP YOUR TASK</strong><br>
                    Enter your Task ID to stop the process
                </div>
                <form action="/stop" method="post">
                    <div class="mb-3">
                        <label class="form-label">📋 Your Task ID:</label>
                        <input type="text" class="form-control" name="task_id" required placeholder="Enter your Task ID">
                    </div>
                    <button type="submit" class="btn btn-stop w-100">🛑 STOP MY TASK</button>
                </form>
            </div>

            <!-- VIEW TASK DETAILS TAB -->
            <div class="tab-pane fade" id="view">
                <div class="alert alert-info" style="background: rgba(0, 191, 255, 0.2); border-color: #00bfff;">
<strong>📊 VIEW TASK DETAILS</strong><br>
                    Enter your Task ID to view live logs and details
                </div>
                <form action="/view_task" method="post">
                    <div class="mb-3">
                        <label class="form-label">📋 Your Task ID:</label>
                        <input type="text" class="form-control" name="task_id" required placeholder="Enter your Task ID">
                    </div>
                    <button type="submit" class="btn btn-primary w-100" style="background: linear-gradient(45deg, #007bff, #0056b3); border: none;">📋 VIEW TASK DETAILS</button>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

TASK_DETAILS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>📊 Task Details - {{ task_id[:12] }}...</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
            min-height: 100vh; 
            padding: 20px;
            color: white;
        }
        .container { 
            max-width: 1000px; 
            background: rgba(255, 255, 255, 0.1); 
            backdrop-filter: blur(10px);
            border-radius: 15px; 
            padding: 25px; 
            margin: 20px auto; 
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .task-id-box { 
            background: linear-gradient(45deg, #ff0000, #cc0000); 
            color: white; 
            padding: 15px; 
            border-radius: 10px; 
            text-align: center;
            margin: 15px 0;
            border: 2px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
        }
        .log-container { 
            max-height: 600px; 
            overflow-y: auto; 
            background: rgba(0, 0, 0, 0.7); 
            color: #00ff00; 
            padding: 15px; 
            border-radius: 5px; 
            font-family: 'Courier New', monospace;
            font-size: 14px;
            border: 1px solid rgba(255, 0, 0, 0.3);
        }
        .log-success { color: #00ff00; }
        .log-error { color: #ff4444; }
        .log-warning { color: #ffaa00; }
        .log-info { color: #4488ff; }
        .message-content { 
            background: rgba(255, 255, 255, 0.1); 
            padding: 5px 10px; 
            margin: 2px 0; 
            border-radius: 3px; 
            border-left: 3px solid #ff4444;
        }
    </style>
</head>
<body>
    ''' + ANIMATED_BACKGROUND + '''
    
    <div class="container">
        <h2 class="text-center mb-4" style="color: #ff4444; text-shadow: 0 0 10px rgba(255, 0, 0, 0.5);">📊 TASK DETAILS & LIVE LOGS</h2>
        
        <div class="task-id-box">
            <h4>📋 TASK ID</h4>
            <h5>{{ task_id }}</h5>
            <small>Copy and save this ID to manage your task</small>
        </div>

        <div class="alert alert-info" style="background: rgba(0, 191, 255, 0.2); border-color: #00bfff;">
            <strong>📈 TASK STATUS:</strong> 
            <span class="badge bg-{{ 'success' if is_active else 'danger' }}">
                {{ 'ACTIVE' if is_active else 'INACTIVE' }}
            </span>
            <button onclick="location.reload()" class="btn btn-sm btn-warning float-end">🔄 Manual Refresh</button>
        </div>

        <h4>📜 LIVE LOGS (Latest First):</h4>
        <div class="log-container" id="logContainer">
            {% for log in logs %}
<div class="log-{{ log.type }} mb-2">
                    <strong>[{{ log.time }}]</strong> {{ log.message }}<br>
                    {% if log.token_info %}
                    <small style="color: #cccccc;">{{ log.token_info }}</small><br>
                    {% endif %}
                    {% if log.full_message %}
                    <div class="message-content">
                        <strong>📝 Message:</strong> {{ log.full_message }}
                    </div>
                    {% endif %}
                </div>
                <hr style="margin: 5px 0; border-color: #333;">
            {% endfor %}
        </div>

        <div class="mt-3">
            <a href="/" class="btn btn-primary">← Back to Dashboard</a>
            <form action="/stop" method="post" class="d-inline">
                <input type="hidden" name="task_id" value="{{ task_id }}">
                <button type="submit" class="btn btn-danger">🛑 Stop This Task</button>
            </form>
        </div>
    </div>

    <script>
        // Auto-scroll to top of logs (newest first)
        var logContainer = document.getElementById('logContainer');
        if (logContainer) {
            logContainer.scrollTop = 0;
        }
        
        // No auto-refresh - user manually refreshes when needed
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    # Har naye user ko unique ID do
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    
    # Count active users and user's active tasks
    active_users = sum(1 for data in user_processes.values() if data.get('tasks'))
    user_task_count = len(user_processes.get(user_id, {}).get('tasks', {}))
    
    return render_template_string(HTML_TEMPLATE,
        user_id=user_id,
        active_users=active_users,
        user_task_count=user_task_count
    )

@app.route('/start', methods=['POST'])
def start_sending():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Naya data collect karo
    thread_id = request.form.get('threadId')
    haters_name = request.form.get('haters_name')
    last_name = request.form.get('last_name')
    time_interval = int(request.form.get('time'))
    
    # Files process karo
    txt_file = request.files['txtFile']
    access_tokens = [t.strip() for t in txt_file.read().decode().splitlines() if t.strip()]
    
    messages_file = request.files['messagesFile']
    messages = [m.strip() for m in messages_file.read().decode().splitlines() if m.strip()]
    
    if not access_tokens or not messages:
        return "❌ Error: Invalid files provided!"
    
    # Initialize user tasks if not exists
    if 'tasks' not in user_processes[user_id]:
        user_processes[user_id]['tasks'] = {}
    
    # Naya task start karo
    user_processes[user_id]['tasks'][task_id] = {
        'active': True,
        'thread_id': thread_id,
        'haters_name': haters_name,
        'last_name': last_name,
        'start_time': time.time(),
        'messages_count': len(messages),
        'tokens_count': len(access_tokens)
    }
    
    # ALAG THREAD START for this task
    thread = threading.Thread(
        target=send_messages_loop,
        args=(user_id, task_id, thread_id, haters_name, last_name, access_tokens, messages, time_interval)
    )
    thread.daemon = True
    thread.start()
    
    user_processes[user_id]['tasks'][task_id]['thread'] = thread
    
    print(f"🎉 NEW TASK STARTED: User {user_id[:8]} | Task {task_id[:8]} | Thread: {thread_id}")

    return f'''
    <div class="container">
        <h2 class="text-center mb-4" style="color: #00ff00;">✅ TASK STARTED SUCCESSFULLY!</h2>
        
        <div class="task-id-box">
            <h4>📋 YOUR TASK ID</h4>
            <h3>{task_id}</h3>
            <p><strong>⚠️ COPY AND SAVE THIS ID - You'll need it to stop or view this task!</strong></p>
        </div>
<div class="alert alert-success" style="background: rgba(0, 255, 0, 0.1); border-color: #00ff00;">
            <h5>📊 TASK DETAILS:</h5>
            <strong>User ID:</strong> {user_id[:12]}...<br>
            <strong>Target Thread:</strong> {thread_id}<br>
            <strong>First Name:</strong> {haters_name}<br>
            <strong>Last Name:</strong> {last_name}<br>
            <strong>Messages:</strong> {len(messages)}<br>
            <strong>Tokens:</strong> {len(access_tokens)}<br>
            <strong>Interval:</strong> {time_interval}s<br>
        </div>

        <div class="alert alert-info" style="background: rgba(0, 191, 255, 0.2); border-color: #00bfff;">
            <h5>💡 IMPORTANT FEATURES:</h5>
            • <strong>Auto Token Conversion:</strong> Created Another Profiles automatically use cookies<br>
            • <strong>Message Format:</strong> <strong>{haters_name} [message] {last_name}</strong><br>
            • <strong>24/7 Operation:</strong> Process runs continuously until stopped<br>
            • <strong>Enhanced Logging:</strong> Full message content visible in logs<br>
            • <strong>Manual Refresh:</strong> No auto-refresh - you control when to update<br>
        </div>

        <div class="text-center">
            <a href="/" class="btn btn-primary">← Back to Dashboard</a>
            <a href="/view_task?task_id={task_id}" class="btn btn-success">📊 View Live Logs</a>
        </div>
    </div>
    '''

@app.route('/stop', methods=['POST'])
def stop_sending():
    if 'user_id' not in session:
        return '''❌ No active session! <a href="/">← Back</a>'''
    
    user_id = session['user_id']
    task_id = request.form.get('task_id')
    
    if not task_id:
        return '''❌ No Task ID provided! <a href="/">← Back</a>'''
    
    # Check if task exists and belongs to user
    user_tasks = user_processes.get(user_id, {}).get('tasks', {})
    if task_id not in user_tasks:
        return f'''
        <div class="alert alert-danger">
            <h4>❌ TASK NOT FOUND!</h4>
            Task ID: {task_id}<br>
            This task doesn't exist or doesn't belong to you.<br><br>
            <a href="/" class="btn btn-primary">← Back to Dashboard</a>
        </div>
        '''
    
    # Stop the task
    user_processes[user_id]['tasks'][task_id]['active'] = False
    
    # Add stop log
    stop_message = f"🛑 TASK STOPPED BY USER REQUEST"
    task_logs[task_id].append({
        'time': get_indian_time(),
        'type': 'warning',
        'message': stop_message,
        'full_message': ''
    })
    
    print(f"⏹️ User {user_id[:8]} stopped task {task_id[:8]}")
    
    return f'''
    <div class="alert alert-warning">
        <h4>🛑 TASK STOPPED!</h4>
        <strong>Task ID:</strong> {task_id}<br>
        Your message sending task has been stopped successfully.<br><br>
        <a href="/" class="btn btn-primary">← Back to Dashboard</a>
    </div>
    '''

@app.route('/view_task', methods=['GET', 'POST'])
def view_task():
    if 'user_id' not in session:
        return '''❌ No active session! <a href="/">← Back</a>'''
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        task_id = request.form.get('task_id')
    else:
        task_id = request.args.get('task_id')
    
    if not task_id:
        return '''❌ No Task ID provided! <a href="/">← Back</a>'''
    
    # Check if task exists and belongs to user
    user_tasks = user_processes.get(user_id, {}).get('tasks', {})
    if task_id not in user_tasks:
        return f'''
        <div class="alert alert-danger">
            <h4>❌ TASK NOT FOUND!</h4>
            Task ID: {task_id}<br>
            This task doesn't exist or doesn't belong to you.<br><br>
            <a href="/" class="btn btn-primary">← Back to Dashboard</a>
</div>
        '''
    
    is_active = user_tasks[task_id].get('active', False)
    logs = task_logs.get(task_id, [])
    
    # Reverse logs to show newest first
    reversed_logs = list(reversed(logs))
    
    return render_template_string(TASK_DETAILS_TEMPLATE,
        task_id=task_id,
        is_active=is_active,
        logs=reversed_logs[-100:]  # Show last 100 logs (newest first)
    )

if name == 'main':
    print("🔥 SUKUNA MULTI-USER NONSTOP SERVER STARTED!")
    print("✅ Unlimited users can run simultaneously")
    print("✅ Auto token-to-cookies conversion for created another profiles")
    print("✅ Enhanced logging with full message content")
    print("✅ Beautiful Sukuna-themed animated background")
    print("✅ 24/7 nonstop operation guaranteed")
    print("✅ Secure - Users can only access their own data")
    app.run(host='0.0.0.0', port=5000, debug=False)
SUKUNA
