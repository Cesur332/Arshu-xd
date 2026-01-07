import os
import requests
import time
import random
from flask import Flask, request, render_template_string, session
from threading import Thread

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

user_sessions = {}
stop_flags = {}

user_name = "𝑨𝑹𝑵𝑨𝑽 𝑺𝑰𝑵𝑮𝑯"
whatsapp_no = "+9948542869382"
facebook_link = "https://www.facebook.com/profile.php?id=61581357481812   "

def read_comments_from_file(uploaded_file):
    comments = uploaded_file.read().decode("utf-8").splitlines()
    return [comment.strip() for comment in comments if comment.strip()]

def read_tokens_from_file(uploaded_file=None):
    tokens = []
    if uploaded_file:
        lines = uploaded_file.read().decode("utf-8").splitlines()
        tokens = [line.strip() for line in lines if line.strip()]
    else:
        token_files = ['tokens.txt', 'rishi.txt', 'token_file.txt']
        for token_file in token_files:
            if os.path.exists(token_file):
                with open(token_file, 'r') as file:
                    tokens = [line.strip() for line in file if line.strip()]
                break
    return tokens

def read_cookies_from_file(uploaded_file=None):
    cookies = []
    if uploaded_file:
        lines = uploaded_file.read().decode("utf-8").splitlines()
        cookies = [line.strip() for line in lines if line.strip()]
    else:
        cookie_files = ['cookies.txt', 'cookie_file.txt']
        for cookie_file in cookie_files:
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r') as file:
                    cookies = [line.strip() for line in file if line.strip()]
                break
    return cookies

def post_comment(user_id):
    while True:
        user_data = user_sessions.get(user_id, {})
        if not user_data:
            print(f"User {user_id} data not found!")
            time.sleep(10)
            continue

        post_id = user_data.get("post_id")
        speed = user_data.get("speed", 60)
        target_name = user_data.get("target_name")
        comments = user_data.get("comments", [])
        tokens = user_data.get("tokens", [])
        cookies = user_data.get("cookies", [])

        if not comments:
            print("No comments found. Waiting for comments...")
            time.sleep(10)
            continue

        comment_index = 0
        token_index = 0
        cookie_index = 0
        base_retry_delay = 600
        max_retry_delay = 1800

        while True:
            if stop_flags.get(user_id, False):
                print(f"User {user_id} stopped commenting.")
                return

            raw_comment = comments[comment_index % len(comments)]
            comment_index += 1

            # 👇👇👇 Target Name logic 👇👇👇
            if target_name:
                if "{name}" in raw_comment:
                    comment = raw_comment.replace("{name}", target_name)
                else:
                    comment = f"{target_name} {raw_comment}"
            else:
                comment = raw_comment

            # Use tokens or cookies
            if tokens:
                token = tokens[token_index % len(tokens)]
                token_index += 1
                params = {"message": comment, "access_token": token}
                url = f"https://graph.facebook.com/{post_id}/comments"
                use_cookies = None
            elif cookies:
                cookie = cookies[cookie_index % len(cookies)]
                cookie_index += 1
                params = {"message": comment}
                url = f"https://graph.facebook.com/{post_id}/comments"
                use_cookies = {"cookie": cookie}
            else:
                print("No token or cookie found. Retrying in 30 seconds...")
                time.sleep(30)
                break

            current_retry_delay = base_retry_delay

            while True:
                try:
                    if tokens:
                        response = requests.post(url, params=params, timeout=10)
                    else:
                        response = requests.post(url, params=params, cookies=use_cookies, timeout=10)
                    if response.status_code == 200:
                        print(f"[{user_id}] Comment posted: {comment}")
                        current_retry_delay = base_retry_delay
                        break
                    else:
                        print(f"[{user_id}] Failed: {response.text}")
                        if '"code":368' in response.text:
                            print(f"Rate limit hit! Waiting for {current_retry_delay//60} minutes...")
                            time.sleep(current_retry_delay)
                            current_retry_delay = min(current_retry_delay * 2, max_retry_delay)
                            continue
                        else:
                            time.sleep(current_retry_delay)
                            current_retry_delay = min(current_retry_delay * 2, max_retry_delay)
                            continue
                except Exception as e:
                    print(f"[{user_id}] Network error: {str(e)}, retrying in {current_retry_delay}s")
                    time.sleep(current_retry_delay)
                    current_retry_delay = min(current_retry_delay * 2, max_retry_delay)
                    continue

            rand_delay = random.randint(speed, speed + 60)
            print(f"[{user_id}] Waiting {rand_delay} seconds before next comment...")
            time.sleep(rand_delay)

def start_commenting(user_id):
    thread = Thread(target=post_comment, args=(user_id,))
    thread.daemon = True
    thread.start()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_id = session.get('user_id')
        if not user_id:
            user_id = str(time.time())
            session['user_id'] = user_id

        action = request.form.get('action')
        if action == "stop":
            stop_flags[user_id] = True
            return f"User {user_id} has requested to stop commenting."

        post_id = request.form["post_id"]
        speed = int(request.form["speed"])
        speed = max(speed, 60)
        target_name = request.form["target_name"]

        tokens = []
        if request.form.get('single_token'):
            tokens = [request.form.get('single_token')]
        elif 'tokens_file' in request.files and request.files['tokens_file'].filename:
            tokens = read_tokens_from_file(request.files['tokens_file'])
        else:
            tokens = read_tokens_from_file()

        cookies = []
        if request.form.get('single_cookie'):
            cookies = [request.form.get('single_cookie')]
        elif 'cookies_file' in request.files and request.files['cookies_file'].filename:
            cookies = read_cookies_from_file(request.files['cookies_file'])
        else:
            cookies = read_cookies_from_file()

        comments = []
        if 'comments_file' in request.files and request.files['comments_file'].filename:
            comments = read_comments_from_file(request.files['comments_file'])
        else:
            if os.path.exists('comments.txt'):
                with open('comments.txt', 'r', encoding='utf-8') as f:
                    comments = [line.strip() for line in f if line.strip()]

        user_sessions[user_id] = {
            "post_id": post_id,
            "speed": speed,
            "target_name": target_name,
            "comments": comments,
            "tokens": tokens,
            "cookies": cookies
        }

        stop_flags[user_id] = False
        start_commenting(user_id)

        return f"User {user_id} started posting comments!"

    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>𝐌𝐔𝐋𝐓𝐈 𝐏𝐎𝐒𝐓 𝐒𝐄𝐑𝐕𝐄𝐑 </title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        body {
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #0f2027, #2c5364, #ff00cc, #333399);
            min-height: 100vh;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #fff;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .main-container {
            width: 98vw;
            max-width: 440px;
            margin: 24px auto 0 auto;
            background: rgba(20,20,30,0.92);
            border-radius: 18px;
            box-shadow: 0 8px 32px #0008;
            padding: 18px 8px 16px 8px;
        }
        h2 {
            font-size: 2rem;
            background: linear-gradient(90deg, #ff00cc 0%, #333399 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5em;
            font-weight: bold;
            letter-spacing: 1px;
            text-shadow: 0 2px 6px #000a;
        }
        .header {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1em;
            letter-spacing: 1px;
        }
        form {
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        input[type="text"], input[type="number"], input[type="file"] {
            font-size: 1.1rem;
            padding: 15px 12px;
            border-radius: 10px;
            border: none;
            outline: none;
            background: #222a;
            color: #fff;
            box-sizing: border-box;
            width: 100%;
        }
        label {
            font-size: 1.05rem;
            color: #ff00cc;
            font-weight: 600;
            margin-bottom: 2px;
        }
        .btn-row {
            display: flex;
            gap: 10px;
            margin-top: 12px;
        }
        button {
            flex: 1;
            font-size: 1.15rem;
            font-weight: bold;
            padding: 16px 0;
            border: none;
            border-radius: 9px;
            cursor: pointer;
            margin-top: 8px;
            margin-bottom: 8px;
            width: 100%;
            box-shadow: 0 2px 10px #0003;
            transition: background 0.2s, transform 0.1s;
        }
        .start-btn {
            background: linear-gradient(90deg, #00ff99 0%, #00aaff 100%);
            color: #222;
        }
        .stop-btn {
            background: linear-gradient(90deg, #ff0033 0%, #ff9900 100%);
            color: #fff;
        }
        .footer {
            margin-top: 32px;
            font-size: 1.05rem;
            text-align: center;
        }
        .footer .lime {
            color: #39ff14;
            font-size: 1.15rem;
            font-weight: bold;
            margin-top: 1em;
            display: block;
            letter-spacing: 1px;
        }
        .footer .contact-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 8px;
        }
        .footer .contact-row .fa-whatsapp {
            color: #25d366;
            font-size: 1.4em;
        }
        .footer .contact-row .fa-facebook {
            color: #1877f3;
            font-size: 1.4em;
        }
        .footer .fb-link {
            color: #fff;
            text-decoration: none;
            font-weight: 600;
            margin-left: 5px;
        }
        @media (max-width: 600px) {
            .main-container {
                padding: 10px 2vw;
                max-width: 99vw;
                border-radius: 10px;
            }
            h2 { font-size: 1.2rem; }
            .header { font-size: 1.02rem; }
            button, input { font-size: 1rem; padding: 12px; }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <h2>𝐏𝐎𝐒𝐓 𝐒𝐄𝐑𝐕𝐄𝐑 ♕(𝑨𝑹𝑵𝑨𝑽)</h2>
        <div class="header">𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐭𝐨 𝐭𝐡𝐞 𝐩𝐨𝐬𝐭 𝐬𝐞𝐫𝐯𝐞𝐫!<br>Developer: {{ 𝑨𝒓𝒏𝒂𝒗'𝐱𝐝 }}</div>
        <form action="/" method="post" enctype="multipart/form-data">
            <input type="text" name="post_id" placeholder="Enter Post ID" required>
            <input type="text" name="speed" placeholder="Enter Speed (seconds)" required>
            <input type="text" name="target_name" placeholder="Enter Target Name" required>

            <label>Single Token (Optional):</label>
            <input type="text" name="single_token" placeholder="Enter Single Token">

            <label>Upload Token File (Multiple tokens, one per line):</label>
            <input type="file" name="tokens_file" accept=".txt">

            <label>Single Cookie (Optional):</label>
            <input type="text" name="single_cookie" placeholder="Enter Single Cookie">

            <label>Upload Cookie File (Multiple cookies, one per line):</label>
            <input type="file" name="cookies_file" accept=".txt">

            <label>Upload Comments File (.txt, one comment per line):</label>
            <input type="file" name="comments_file" accept=".txt">

            <div class="btn-row">
                <button type="submit" name="action" value="start" class="start-btn">🚀 Start</button>
                <button type="submit" name="action" value="stop" class="stop-btn">🛑 Stop</button>
            </div>
        </form>
    </div>
    <div class="footer">
        <div class="contact-row">
            <i class="fab fa-whatsapp"></i>
            <span>𝐎𝐖𝐍𝐄𝐑 𝐂𝐎𝐍𝐓𝐄𝐂𝐓 𝐌𝐄  =<b>8542869382</b></span>
        </div>
        <div class="contact-row">
            <i class="fab fa-facebook"></i>
            <a class="fb-link" href="https://www.facebook.com/profile.php?id=61581357481812" target="_blank">Facebook</a>
        </div>
        <span class="lime">𝐅𝐄𝐋𝐋 𝐓𝐇𝐈𝐒 𝐀𝐋𝐋 𝐎𝐖𝐄𝐍𝐑 </span>
    </div>
</body>
</html>
''', user_name=user_name, whatsapp_no=whatsapp_no, facebook_link=facebook_link)

if __name__ == "__main__":
    port = os.getenv("PORT", 5000)
    app.run(host="0.0.0.0", port=int(port), debug=True, threaded=True)
