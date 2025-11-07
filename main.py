import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, g, jsonify
from dotenv import load_dotenv
import stripe
import markdown2
import openai


load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'changeme')

GUIDE_PATHS = {
    'facebook': 'c:/Users/user/OneDrive/Documents/airizzos/backoffice_site/myaistore/guides/facebook_affiliate_guide.md',
    'tiktok': 'c:/Users/user/OneDrive/Documents/airizzos/backoffice_site/myaistore/guides/tiktok_affiliate_guide.md',
    'instagram': 'c:/Users/user/OneDrive/Documents/airizzos/backoffice_site/myaistore/guides/instagram_affiliate_guide.md',
    'sneaky': 'c:/Users/user/OneDrive/Documents/airizzos/backoffice_site/myaistore/guides/sneaky_tricks_guide.md',
    'free-facebook': 'c:/Users/user/OneDrive/Documents/airizzos/backoffice_site/myaistore/guides/free_facebook_posts_guide.md',
}

def render_guide(guide_key, title):
    from flask import session
    path = GUIDE_PATHS.get(guide_key)
    if not path or not os.path.exists(path):
        return f"<h1>{title}</h1><p>Guide not found.</p>"
    with open(path, encoding='utf-8') as f:
        md = f.read()
    # Replace username placeholder with logged-in user's username (or rizzosai for admin4)
    username = session.get('username', 'yourusername')
    if username == 'admin4':
        username = 'rizzosai'
    md = md.replace('YOURUSERNAME', username)
    html = markdown2.markdown(md)
    return f"""
    <html><head><title>{title}</title>
    <style>body {{ font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 30px; }} h1 {{ color: #e63946; }} a {{ color: #457b9d; }}</style>
    </head><body>{html}<br><a href='/dashboard'>Back to Dashboard</a></body></html>
    """

@app.route('/guides/facebook')
def guide_facebook():
    return render_guide('facebook', 'Facebook Affiliate Guide')

@app.route('/guides/tiktok')
def guide_tiktok():
    return render_guide('tiktok', 'TikTok Affiliate Guide')

@app.route('/guides/instagram')
def guide_instagram():
    return render_guide('instagram', 'Instagram Affiliate Guide')

@app.route('/guides/sneaky')
def guide_sneaky():
    return render_guide('sneaky', 'Sneaky Tricks Guide')

@app.route('/guides/free-facebook')
def guide_free_facebook():
    return render_guide('free-facebook', 'Free Facebook Posts Guide')

# Load Stripe secret key from .env
STRIPE_API_KEY = os.getenv('STRIPE_SECRET_KEY')
print("Loaded Stripe API Key:", STRIPE_API_KEY)
stripe.api_key = STRIPE_API_KEY

# Database setup
DATABASE = os.path.join(os.path.dirname(__file__), 'users.db')


# Add payment_status to stripe_status table if not exists
def add_payment_status_column():
    with sqlite3.connect(DATABASE) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS stripe_status (
            username TEXT PRIMARY KEY,
            stripe_setup INTEGER DEFAULT 0,
            payment_status INTEGER DEFAULT 0
        )''')
        # Create leaderboard table if not exists
        db.execute('''CREATE TABLE IF NOT EXISTS leaderboard (
            username TEXT PRIMARY KEY,
            referrals INTEGER DEFAULT 0,
            earnings REAL DEFAULT 0.0,
            level TEXT DEFAULT ''
        )''')
add_payment_status_column()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def init_db():
    with sqlite3.connect(DATABASE) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS stripe_status (
            username TEXT PRIMARY KEY,
            stripe_setup INTEGER DEFAULT 0
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS leaderboard (
            username TEXT PRIMARY KEY,
            referrals INTEGER DEFAULT 0,
            earnings REAL DEFAULT 0.0,
            level TEXT DEFAULT ''
        )''')

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

init_db()

USERS = {
    "admin": {"password": "password123", "role": "admin"},
    "admin1": {"password": "password123", "role": "user", "plan": "$29 Basic Starter"},
    "admin2": {"password": "password123", "role": "user", "plan": "$99 Pro"},
    "admin3": {"password": "password123", "role": "user", "plan": "$249 Elite"},
    "admin4": {"password": "password123", "role": "user", "plan": "$499 VIP"},
    "basic": {"password": "password123", "role": "user", "plan": "Basic Starter"},
    "pro": {"password": "password123", "role": "user", "plan": "Pro"},
    "elite": {"password": "password123", "role": "user", "plan": "Elite"},
    "vip": {"password": "password123", "role": "user", "plan": "VIP"},
    # Real affiliate accounts as requested
    "rizzosai": {"password": "ilovemyselfTodaynyesterday71", "role": "user", "plan": "$499 VIP"},
    "rizzo": {"password": "FuckUCunt81271", "role": "user", "plan": "$499 VIP"},
    "gre": {"password": "FuckUCunt81271", "role": "user", "plan": "$249 Elite"},
    "ned": {"password": "FuckUCunt81271", "role": "user", "plan": "$99 Pro"},
    "jas": {"password": "FuckUCunt81271", "role": "user", "plan": "$29 Basic Starter"}
}

# Login page template
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
            background: linear-gradient(90deg, #e63946 0%%, #ffffff 50%%, #457b9d 100%%);
<head>
    <meta charset="UTF-8">
    <title>Login - RizzosAI Affiliate Backoffice</title>
    <style>
        body {
            background: linear-gradient(90deg, #e63946 0%%, #ffffff 50%%, #457b9d 100%%);
            color: #222;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 400px;
            margin: 60px auto;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }
        h2 {
            color: #e63946;
        }
        .error {
            color: #e63946;
            width: 100%%;
        }
        label {
            font-weight: bold;
        }
        input[type="text"], input[type="password"] {
            width: 100%%;
            padding: 8px;
            margin-bottom: 15px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        input[type="submit"] {
            background: #457b9d;
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            font-weight: bold;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background: #e63946;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Affiliate Login</h2>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="post">
            <label>Username:</label><br>
            <input type="text" name="username"><br>
            <label>Password:</label><br>
            <input type="password" name="password"><br><br>
            <input type="submit" value="Login">
        </form>
    </div>
</body>
</html>
'''

# User dashboard template
USER_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Rizzos AI - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: linear-gradient(90deg, #e63946 0%%, #ffffff 50%%, #457b9d 100%%); }
        .nav { background: #f8f9fa; padding: 15px; margin-bottom: 20px; border-radius: 8px; }
        .nav a { margin-right: 20px; text-decoration: none; color: #007cba; font-weight: bold; }
        .card { border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 8px; background: #fff; }
        .highlight-card { background: linear-gradient(135deg, #667eea 0%%, #764ba2 100%%); color: white; }
        .commission-item { background: #f0f8ff; padding: 10px; margin: 5px 0; border-left: 4px solid #007cba; }
        .queue-status { background: #fff3cd; padding: 15px; border: 1px solid #ffeaa7; border-radius: 8px; }
        .btn-main { background: #e63946; color: #fff; padding: 12px 28px; border-radius: 5px; font-weight: bold; text-decoration: none; display: inline-block; margin: 10px 0; }
        .btn-main:hover { background: #457b9d; }
        input[type="text"] { width: 100%%; padding: 10px; }
    </style>
</head>
<body>

    <!-- Stripe Upgrade Banner -->
    <div style="background:linear-gradient(90deg,#e63946 0%,#fff 50%,#457b9d 100%);color:#fff;padding:32px 20px 32px 20px;margin-bottom:30px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.10);text-align:center;position:relative;">
        <h1 style="font-size:2.2em;font-weight:bold;margin-bottom:10px;color:#fff;text-shadow:1px 1px 8px #e63946, 0 2px 8px #457b9d;">Upgrade Your Stripe Account To Get Paid!</h1>
        <p style="font-size:1.25em;color:#222;font-weight:bold;margin-bottom:18px;">Download the Stripe Upgrade Guide and follow the steps to ensure you receive your affiliate commissions.</p>
        <a href="/static/guides/upgrade_stripe_account.pdf" download style="display:inline-block;background:#457b9d;color:#fff;font-size:1.3em;font-weight:bold;padding:18px 38px;border-radius:8px;text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,0.12);transition:background 0.2s;">⬇️ Download Stripe Guide (PDF)</a>
    </div>
    <div class="nav">
        <a href="/dashboard">Dashboard</a>
        <a href="/guides/facebook">Training Center</a>
        <a href="/logout">Logout</a>
    </div>

    <h1>Welcome, {% if username == 'admin4' %}rizzosai{% else %}{{ username }}{% endif %}!</h1>
    <div class="card">
        <h3>Your Package: {{ plan }}</h3>
        <p>Level: {{ plan }}</p>
        {% if plan == '$29 Basic Starter' or plan == 'Basic Starter' %}
            <p>Price: $29</p>
            <p>Features: Starter affiliate package, basic commissions, access to guides.</p>
        {% elif plan == '$99 Pro' or plan == 'Pro' %}
            <p>Price: $99</p>
            <p>Features: Higher commissions, more guides, priority support.</p>
        {% elif plan == '$249 Elite' or plan == 'Elite' %}
            <p>Price: $249</p>
            <p>Features: Elite commissions, all guides, advanced support.</p>
        {% elif plan == '$499 VIP' or plan == 'VIP' %}
            <p>Price: $499</p>
            <p>Features: VIP commissions, all features unlocked, dedicated manager.</p>
        {% endif %}
    </div>


    <!-- Domain Packages Section -->

    {# Domain Packages Section - show only next available upgrade #}
    {% set plan_map = {
        '$29 Basic Starter': 29, 'Basic Starter': 29,
        '$99 Pro': 99, 'Pro': 99,
        '$249 Elite': 249, 'Elite': 249,
        '$499 VIP': 499, 'VIP': 499
    } %}
    {% set user_level = plan_map.get(plan, 0) %}
    {% if user_level < 99 %}
    <div class="card" style="background: #f8f9fa;">
        <h2 style="color:#e63946;">RizzosAI Domain Packages</h2>
        <p style="font-size: 1.1em;">Complete Business Solutions with Expert Training Guides</p>
        <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:32px;margin-top:30px;">
            {% if user_level == 29 %}
                <!-- Show PRO, ELITE, and EMPIRE for Starter ($29) users -->
                <div style="background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,31,91,0.08);border:2px solid #e60000;max-width:320px;padding:24px 16px;text-align:center;">
                    <div style="background:#001f5b;color:#fff;font-weight:bold;font-size:1.1em;padding:8px 0;border-radius:8px;margin-bottom:12px;">PRO</div>
                    <div style="font-size:1.7em;color:#001f5b;font-weight:bold;margin-bottom:12px;">$99 + GST</div>
                    <h4>🚀 13 Advanced Business Guides</h4>
                    <ul style="text-align:left;font-size:0.98em;">
                        <li>Everything in Starter</li>
                        <li>Facebook Ads Mastery</li>
                        <li>Conversion Psychology</li>
                        <li>Email Marketing Empire</li>
                        <li>SEO Domination</li>
                        <li>Social Media Profits</li>
                        <li>Analytics & Tracking</li>
                        <li>Brand Building Secrets</li>
                        <li>Competitor Analysis</li>
                    </ul>
                    <a href="https://buy.stripe.com/7sY6oH4d1gs8asF9w91ZS0j" target="_blank" class="btn-main" style="background:#001f5b;">Buy Pro</a>
                </div>
                <div style="background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,31,91,0.08);border:2px solid #e60000;max-width:320px;padding:24px 16px;text-align:center;">
                    <div style="background:#e60000;color:#fff;font-weight:bold;font-size:1.1em;padding:8px 0;border-radius:8px;margin-bottom:12px;">ELITE</div>
                    <div style="font-size:1.7em;color:#001f5b;font-weight:bold;margin-bottom:12px;">$249 + GST</div>
                    <h4>⚡ 20 Elite Strategy Guides</h4>
                    <ul style="text-align:left;font-size:0.98em;">
                        <li>Everything in Pro</li>
                        <li>Six-Figure Scaling</li>
                        <li>Automation Mastery</li>
                        <li>High-Ticket Sales</li>
                        <li>Team Building Secrets</li>
                        <li>Investment Strategies</li>
                        <li>Tax Optimization</li>
                        <li>Exit Strategies</li>
                    </ul>
                    <a href="https://buy.stripe.com/4gM3cv7pd0ta9oBbEh1ZS0k" target="_blank" class="btn-main" style="background:#e60000;">Buy Elite</a>
                </div>
                <div style="background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,31,91,0.08);border:2px solid #e60000;max-width:320px;padding:24px 16px;text-align:center;">
                    <div style="background:linear-gradient(90deg,#e60000 33%,#fff 33%,#fff 66%,#001f5b 66%);color:#001f5b;font-weight:bold;font-size:1.1em;padding:8px 0;border-radius:8px;margin-bottom:12px;">EMPIRE</div>
                    <div style="font-size:1.7em;color:#001f5b;font-weight:bold;margin-bottom:12px;">$499 + GST</div>
                    <h4>👑 35 Empire Building Guides</h4>
                    <ul style="text-align:left;font-size:0.98em;">
                        <li>Everything in Elite</li>
                        <li>Million Dollar Mindset</li>
                        <li>Multi-Stream Income</li>
                        <li>Global Expansion</li>
                        <li>Joint Ventures</li>
                        <li>Personal Branding</li>
                        <li>Speaking & Coaching</li>
                        <li>Product Creation</li>
                        <li>Licensing & Franchising</li>
                        <li>Investment Portfolio</li>
                        <li>Legacy Planning</li>
                        <li>Crisis Management</li>
                        <li>Innovation Strategies</li>
                        <li>Leadership Excellence</li>
                        <li>Negotiation Mastery</li>
                        <li>Empire Succession</li>
                    </ul>
                    <a href="https://buy.stripe.com/8x214naBp3FmgR3bEh1ZS0h" target="_blank" class="btn-main" style="background:#001f5b;">Buy Empire</a>
                    <a href="https://buy.stripe.com/eVq6oHcJx4JqasF4bP1ZS0o" target="_blank" class="btn-main" style="background:#e60000;margin-left:8px;">Free Trial</a>
                </div>
            {% elif user_level == 99 %}
                <!-- Only show ELITE and EMPIRE for Pro ($99) users -->
                <div style="background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,31,91,0.08);border:2px solid #e60000;max-width:320px;padding:24px 16px;text-align:center;">
                    <div style="background:#e60000;color:#fff;font-weight:bold;font-size:1.1em;padding:8px 0;border-radius:8px;margin-bottom:12px;">ELITE</div>
                    <div style="font-size:1.7em;color:#001f5b;font-weight:bold;margin-bottom:12px;">$249 + GST</div>
                    <h4>⚡ 20 Elite Strategy Guides</h4>
                    <ul style="text-align:left;font-size:0.98em;">
                        <li>Everything in Pro</li>
                        <li>Six-Figure Scaling</li>
                        <li>Automation Mastery</li>
                        <li>High-Ticket Sales</li>
                        <li>Team Building Secrets</li>
                        <li>Investment Strategies</li>
                        <li>Tax Optimization</li>
                        <li>Exit Strategies</li>
                    </ul>
                    <a href="https://buy.stripe.com/4gM3cv7pd0ta9oBbEh1ZS0k" target="_blank" class="btn-main" style="background:#e60000;">Buy Elite</a>
                </div>
                <div style="background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,31,91,0.08);border:2px solid #e60000;max-width:320px;padding:24px 16px;text-align:center;">
                    <div style="background:linear-gradient(90deg,#e60000 33%,#fff 33%,#fff 66%,#001f5b 66%);color:#001f5b;font-weight:bold;font-size:1.1em;padding:8px 0;border-radius:8px;margin-bottom:12px;">EMPIRE</div>
                    <div style="font-size:1.7em;color:#001f5b;font-weight:bold;margin-bottom:12px;">$499 + GST</div>
                    <h4>👑 35 Empire Building Guides</h4>
                    <ul style="text-align:left;font-size:0.98em;">
                        <li>Everything in Elite</li>
                        <li>Million Dollar Mindset</li>
                        <li>Multi-Stream Income</li>
                        <li>Global Expansion</li>
                        <li>Joint Ventures</li>
                        <li>Personal Branding</li>
                        <li>Speaking & Coaching</li>
                        <li>Product Creation</li>
                        <li>Licensing & Franchising</li>
                        <li>Investment Portfolio</li>
                        <li>Legacy Planning</li>
                        <li>Crisis Management</li>
                        <li>Innovation Strategies</li>
                        <li>Leadership Excellence</li>
                        <li>Negotiation Mastery</li>
                        <li>Empire Succession</li>
                    </ul>
                    <a href="https://buy.stripe.com/8x214naBp3FmgR3bEh1ZS0h" target="_blank" class="btn-main" style="background:#001f5b;">Buy Empire</a>
                    <a href="https://buy.stripe.com/eVq6oHcJx4JqasF4bP1ZS0o" target="_blank" class="btn-main" style="background:#e60000;margin-left:8px;">Free Trial</a>
                </div>
            {% elif user_level == 249 %}
                <!-- Only show EMPIRE for Elite ($249) users -->
                <div style="background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,31,91,0.08);border:2px solid #e60000;max-width:320px;padding:24px 16px;text-align:center;">
                    <div style="background:linear-gradient(90deg,#e60000 33%,#fff 33%,#fff 66%,#001f5b 66%);color:#001f5b;font-weight:bold;font-size:1.1em;padding:8px 0;border-radius:8px;margin-bottom:12px;">EMPIRE</div>
                    <div style="font-size:1.7em;color:#001f5b;font-weight:bold;margin-bottom:12px;">$499 + GST</div>
                    <h4>👑 35 Empire Building Guides</h4>
                    <ul style="text-align:left;font-size:0.98em;">
                        <li>Everything in Elite</li>
                        <li>Million Dollar Mindset</li>
                        <li>Multi-Stream Income</li>
                        <li>Global Expansion</li>
                        <li>Joint Ventures</li>
                        <li>Personal Branding</li>
                        <li>Speaking & Coaching</li>
                        <li>Product Creation</li>
                        <li>Licensing & Franchising</li>
                        <li>Investment Portfolio</li>
                        <li>Legacy Planning</li>
                        <li>Crisis Management</li>
                        <li>Innovation Strategies</li>
                        <li>Leadership Excellence</li>
                        <li>Negotiation Mastery</li>
                        <li>Empire Succession</li>
                    </ul>
                    <a href="https://buy.stripe.com/8x214naBp3FmgR3bEh1ZS0h" target="_blank" class="btn-main" style="background:#001f5b;">Buy Empire</a>
                    <a href="https://buy.stripe.com/eVq6oHcJx4JqasF4bP1ZS0o" target="_blank" class="btn-main" style="background:#e60000;margin-left:8px;">Free Trial</a>
                </div>
            {% endif %}
        </div>
    </div>
    {% elif user_level == 99 %}
    <div class="card" style="background: #f8f9fa;">
        <h2 style="color:#e63946;">Upgrade to Elite or Empire</h2>
        <p style="font-size: 1.1em;">Unlock more guides and features by upgrading!</p>
        <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:32px;margin-top:30px;">
            <!-- ELITE PACKAGE -->
            <div style="background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,31,91,0.08);border:2px solid #e60000;max-width:320px;padding:24px 16px;text-align:center;">
                <div style="background:#e60000;color:#fff;font-weight:bold;font-size:1.1em;padding:8px 0;border-radius:8px;margin-bottom:12px;">ELITE</div>
                <div style="font-size:1.7em;color:#001f5b;font-weight:bold;margin-bottom:12px;">$249 + GST</div>
                <h4>⚡ 20 Elite Strategy Guides</h4>
                <ul style="text-align:left;font-size:0.98em;">
                    <li>Everything in Pro</li>
                    <li>Six-Figure Scaling</li>
                    <li>Automation Mastery</li>
                    <li>High-Ticket Sales</li>
                    <li>Team Building Secrets</li>
                    <li>Investment Strategies</li>
                    <li>Tax Optimization</li>
                    <li>Exit Strategies</li>
                </ul>
                <a href="https://buy.stripe.com/4gM3cv7pd0ta9oBbEh1ZS0k" target="_blank" class="btn-main" style="background:#e60000;">Buy Elite</a>
            </div>
            <!-- EMPIRE PACKAGE -->
            <div style="background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,31,91,0.08);border:2px solid #e60000;max-width:320px;padding:24px 16px;text-align:center;">
                <div style="background:linear-gradient(90deg,#e60000 33%,#fff 33%,#fff 66%,#001f5b 66%);color:#001f5b;font-weight:bold;font-size:1.1em;padding:8px 0;border-radius:8px;margin-bottom:12px;">EMPIRE</div>
                <div style="font-size:1.7em;color:#001f5b;font-weight:bold;margin-bottom:12px;">$499 + GST</div>
                <h4>👑 35 Empire Building Guides</h4>
                <ul style="text-align:left;font-size:0.98em;">
                    <li>Everything in Elite</li>
                    <li>Million Dollar Mindset</li>
                    <li>Multi-Stream Income</li>
                    <li>Global Expansion</li>
                    <li>Joint Ventures</li>
                    <li>Personal Branding</li>
                    <li>Speaking & Coaching</li>
                    <li>Product Creation</li>
                    <li>Licensing & Franchising</li>
                    <li>Investment Portfolio</li>
                    <li>Legacy Planning</li>
                    <li>Crisis Management</li>
                    <li>Innovation Strategies</li>
                    <li>Leadership Excellence</li>
                    <li>Negotiation Mastery</li>
                    <li>Empire Succession</li>
                </ul>
                <a href="https://buy.stripe.com/8x214naBp3FmgR3bEh1ZS0h" target="_blank" class="btn-main" style="background:#001f5b;">Buy Empire</a>
                <a href="https://buy.stripe.com/eVq6oHcJx4JqasF4bP1ZS0o" target="_blank" class="btn-main" style="background:#e60000;margin-left:8px;">Free Trial</a>
            </div>
        </div>
    </div>
    {% elif user_level == 249 %}
    <div class="card" style="background: #f8f9fa;">
        <h2 style="color:#e63946;">Upgrade to Empire</h2>
        <p style="font-size: 1.1em;">Unlock all guides and features by upgrading to Empire!</p>
        <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:32px;margin-top:30px;">
            <!-- EMPIRE PACKAGE -->
            <div style="background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,31,91,0.08);border:2px solid #e60000;max-width:320px;padding:24px 16px;text-align:center;">
                <div style="background:linear-gradient(90deg,#e60000 33%,#fff 33%,#fff 66%,#001f5b 66%);color:#001f5b;font-weight:bold;font-size:1.1em;padding:8px 0;border-radius:8px;margin-bottom:12px;">EMPIRE</div>
                <div style="font-size:1.7em;color:#001f5b;font-weight:bold;margin-bottom:12px;">$499 + GST</div>
                <h4>👑 35 Empire Building Guides</h4>
                <ul style="text-align:left;font-size:0.98em;">
                    <li>Everything in Elite</li>
                    <li>Million Dollar Mindset</li>
                    <li>Multi-Stream Income</li>
                    <li>Global Expansion</li>
                    <li>Joint Ventures</li>
                    <li>Personal Branding</li>
                    <li>Speaking & Coaching</li>
                    <li>Product Creation</li>
                    <li>Licensing & Franchising</li>
                    <li>Investment Portfolio</li>
                    <li>Legacy Planning</li>
                    <li>Crisis Management</li>
                    <li>Innovation Strategies</li>
                    <li>Leadership Excellence</li>
                    <li>Negotiation Mastery</li>
                    <li>Empire Succession</li>
                </ul>
                <a href="https://buy.stripe.com/8x214naBp3FmgR3bEh1ZS0h" target="_blank" class="btn-main" style="background:#001f5b;">Buy Empire</a>
                <a href="https://buy.stripe.com/eVq6oHcJx4JqasF4bP1ZS0o" target="_blank" class="btn-main" style="background:#e60000;margin-left:8px;">Free Trial</a>
            </div>
        </div>
    </div>
    {% endif %}





    <!-- Coey Chatbot Section -->
    <div class="card" style="background: #f1faee; margin-top: 30px;">
        <div style="font-size:2em;font-weight:bold;color:#e63946;text-align:center;margin-bottom:10px;">Ask Coey anything to do with making money online with RizzosAI and see what Coey says!</div>
        <h3 style="color:#457b9d;">Coey Chatbot (Claude Style)</h3>
        <div class="chat-window" id="chat-window" style="background:#fff;border:1px solid #457b9d;border-radius:6px;min-height:100px;padding:10px;margin-bottom:10px;font-size:1em;">Hi! I am Coey, your AI assistant. How can I help you today?</div>
        <form id="chat-form" onsubmit="return false;">
            <input type="text" class="chat-input" id="chat-input" placeholder="Type your message..." style="width:90%;padding:8px;border:1px solid #e63946;border-radius:4px;">
            <button class="send-btn" onclick="sendMessage()" style="background:#457b9d;color:#fff;border:none;padding:8px 16px;border-radius:4px;font-weight:bold;cursor:pointer;">Send</button>
        </form>
    </div>
    <script>
        async function sendMessage() {
            var input = document.getElementById('chat-input');
            var windowDiv = document.getElementById('chat-window');
            var userMsg = input.value.trim();
            if (userMsg !== '') {
                windowDiv.innerHTML += '<br><b>You:</b> ' + userMsg;
                input.value = '';
                windowDiv.innerHTML += '<br><b>Coey:</b> <span id="coey-typing">...</span>';
                // Send to backend
                try {
                    let resp = await fetch('/coey_chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: userMsg })
                    });
                    let data = await resp.json();
                    document.getElementById('coey-typing').outerHTML = data.reply ? data.reply : '(No response)';
                } catch (e) {
                    document.getElementById('coey-typing').outerHTML = '(Error contacting Coey)';
                }
            }
        }
    </script>

    <!-- Referrals and Earnings Section -->
    <div class="card">
        <h3>Referral & Earnings Overview</h3>
        <p><strong>Total Referrals:</strong> {{ referrals or 0 }}</p>
        <p><strong>Total Earned:</strong> ${{ earnings or '0.00' }}</p>
        <p>Your affiliate link:</p>
        <input type="text" value="https://rizzosai.com/ref={{ username }}" readonly onclick="this.select()">
        <br><br>
        <p><strong>Your Affiliate Code:</strong> {{ username }}</p>
    </div>

    <!-- Leaderboard Section -->
    <div class="card" style="background: #f1faee;">
        <h3 style="color:#e63946;">Affiliate Leaderboard</h3>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="background:#e63946;color:#fff;">
                    <th style="padding:8px;border-radius:4px 0 0 4px;">Rank</th>
                    <th style="padding:8px;">Username</th>
                    <th style="padding:8px;">Referrals</th>
                    <th style="padding:8px;">Earnings</th>
                    <th style="padding:8px;border-radius:0 4px 4px 0;">Level</th>
                </tr>
            </thead>
            <tbody>
                {% for entry in leaderboard %}
                <tr style="background:{{ '#fff' if loop.index0 % 2 == 0 else '#f8f9fa' }};">
                    <td style="padding:8px;text-align:center;">{{ loop.index }}</td>
                    <td style="padding:8px;">{{ entry.username }}</td>
                    <td style="padding:8px;text-align:center;">{{ entry.referrals }}</td>
                    <td style="padding:8px;text-align:center;">${{ entry.earnings }}</td>
                    <td style="padding:8px;text-align:center;">{{ entry.level }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <p style="font-size:0.95em;color:#888;margin-top:10px;">Top affiliates ranked by referrals and earnings.</p>
    </div>

    <!-- Guides Section -->
    <div class="card">
        <h3>Guides & Resources</h3>
        <a href="/guides/facebook">Facebook Affiliate Guide</a> |
        <a href="/guides/tiktok">TikTok Guide</a> |
        <a href="/guides/instagram">Instagram Guide</a> |
        <a href="/guides/sneaky">Sneaky Tricks</a> |
        <a href="/guides/free-facebook">Free Facebook Posts</a>
        <hr>
        <a href="/static/guides/upgrade_stripe_account.pdf" download>Upgrade Stripe Account (PDF)</a> |
        <a href="/static/guides/make_money_online_beginner.pdf" download>Make Money Online (PDF)</a>
    </div>

    <div class="card">
        <a href="{{ url_for('logout') }}" class="btn-main">Logout</a>
    </div>


'''

# Coey Chatbot backend route

@app.route('/coey_chat', methods=['POST'])
def coey_chat():
    data = request.get_json()
    user_message = data.get('message', '')
    if not user_message:
        return jsonify({'reply': "Please enter a message."})
    try:
        # Debug: print the API key value and working directory
        api_key = os.getenv('OPENAI_API_KEY')
        print('[DEBUG] OPENAI_API_KEY:', api_key)
        print('[DEBUG] Current working directory:', os.getcwd())
        print('[DEBUG] .env expected at:', os.path.join(os.getcwd(), '.env'))
        if not api_key or api_key.strip() == '' or not api_key.startswith('sk-'):
            return jsonify({'reply': "Sorry, Coey cannot access the OpenAI API key. Please check your .env file and restart the server."})
        # For openai>=1.0.0: use OpenAI client object
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Coey, a friendly and helpful AI assistant for affiliate marketers. Your job is to give step-by-step, copy-paste, beginner-friendly directions for making money online with RizzosAI. Imagine the user is a 2-year-old: take them by the hand and teach them how to get customers with RizzosAI, using simple language and clear steps. Always encourage them that all they have to do is copy and paste your instructions."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=400,
            temperature=0.7
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'reply': f"Sorry, Coey had an error: {str(e)}"})

# Admin dashboard template
ADMIN_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin Dashboard</title>
    <style>
        body {
                background: linear-gradient(90deg, #e63946 0%%, #ffffff 50%%, #457b9d 100%%);
            color: #222;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 700px;
            margin: 40px auto;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }
        h2 {
            color: #e63946;
        }
        .guides-list {
            margin: 20px 0;
            padding: 15px;
            background: #f1faee;
            border-radius: 8px;
        }
        .guides-list a {
            display: block;
            color: #457b9d;
            font-weight: bold;
            margin-bottom: 8px;
            text-decoration: none;
        }
        .guides-list a:hover {
            text-decoration: underline;
        }
        .chatbot {
            margin-top: 30px;
            background: #f1faee;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        }
        .chatbot h3 {
            color: #457b9d;
            margin-bottom: 10px;
        }
        .chat-window {
            background: #fff;
            border: 1px solid #457b9d;
            border-radius: 6px;
            min-height: 120px;
            padding: 10px;
            margin-bottom: 10px;
            font-size: 1em;
        }
        .chat-input {
                width: 90%%;
            padding: 8px;
            border: 1px solid #e63946;
            border-radius: 4px;
        }
        .send-btn {
            background: #457b9d;
            color: #fff;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            cursor: pointer;
        }
        .send-btn:hover {
            background: #e63946;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Welcome, Admin!</h2>
        <p>You are logged in.</p>
        <div class="guides-list">
            <h3>Guides</h3>
            <a href="/guides/facebook">Facebook Affiliate Guide</a>
            <a href="/guides/tiktok">TikTok Affiliate Guide</a>
            <a href="/guides/instagram">Instagram Affiliate Guide</a>
            <a href="/guides/sneaky">Sneaky Tricks Guide</a>
            <a href="/guides/free-facebook">Free Facebook Posts Guide</a>
        </div>
        <div class="chatbot">
            <h3>Coey Chatbot (Claude Style)</h3>
            <div class="chat-window" id="chat-window">Hi! I am Coey, your AI assistant. How can I help you today?</div>
            <form id="chat-form" onsubmit="return false;">
                <input type="text" class="chat-input" id="chat-input" placeholder="Type your message...">
                <button class="send-btn" onclick="sendMessage()">Send</button>
            </form>
        </div>
        <a href="{{ url_for('logout') }}">Logout</a>
    </div>
    <script>
        function sendMessage() {
            var input = document.getElementById('chat-input');
            var windowDiv = document.getElementById('chat-window');
            if (input.value.trim() !== '') {
                windowDiv.innerHTML += '<br><b>You:</b> ' + input.value;
                // Placeholder for Coey response
                windowDiv.innerHTML += '<br><b>Coey:</b> (This is a placeholder response.)';
                input.value = '';
            }
        }
    </script>
</body>
</html>
'''

# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = USERS.get(username, None)
        if user and password == user['password']:
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user['role']
            if user['role'] == 'user':
                session['plan'] = user['plan']
            # Ensure a stripe_status row exists for this user
            db = sqlite3.connect(DATABASE)
            db.execute('INSERT OR IGNORE INTO stripe_status (username, stripe_setup, payment_status) VALUES (?, 0, 0)', (username,))
            db.commit()
            db.close()
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials.'
    return render_template_string(LOGIN_TEMPLATE, error=error)

# Stripe payment route
@app.route('/pay')
def pay():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    username = session.get('username')
    plan = session.get('plan', 'Basic Starter')
    # Set price based on plan
    price_map = {
        '$29 Basic Starter': 2900,
        '$99 Pro': 9900,
        '$249 Elite': 24900,
        '$499 VIP': 49900,
        'Basic Starter': 2900,
        'Pro': 9900,
        'Elite': 24900,
        'VIP': 49900
    }
    amount = price_map.get(plan, 2900)
    # Create Stripe Checkout session
    session_obj = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f'Affiliate Package: {plan}',
                },
                'unit_amount': amount,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('dashboard', _external=True) + '?paid=success',
        cancel_url=url_for('dashboard', _external=True) + '?paid=cancel',
        metadata={'username': username, 'plan': plan}
    )
    # Render payment page with Stripe Checkout link
    pay_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Pay Affiliate Fee</title>
        <style>
            body { background: linear-gradient(90deg, #e63946 0%%, #ffffff 50%%, #457b9d 100%%); color: #222; font-family: Arial, sans-serif; }
            .container { max-width: 400px; margin: 60px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 30px; }
            h2 { color: #e63946; }
            .btn { background: #457b9d; color: #fff; border: none; padding: 12px 28px; border-radius: 4px; font-weight: bold; cursor: pointer; text-decoration: none; }
            .btn:hover { background: #e63946; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Pay Your Affiliate Fee</h2>
            <p>Package: <b>{{ plan }}</b></p>
            <p>Amount: <b>${{ amount/100 }}</b></p>
            <a href="{{ checkout_url }}" class="btn">Pay with Stripe</a>
            <p style="margin-top:20px;">After payment, you will be redirected to your dashboard.</p>
        </div>
    </body>
    </html>
    '''
    # Use .url if available, else ['url'] for dict
    checkout_url = getattr(session_obj, 'url', None)
    if checkout_url is None and isinstance(session_obj, dict):
        checkout_url = session_obj.get('url')
    return render_template_string(pay_template, plan=plan, amount=amount, checkout_url=checkout_url)

# Stripe webhook endpoint for payment automation
import requests
from flask import jsonify

@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400


    # Handle successful payment for checkout session
    if event['type'] == 'checkout.session.completed':
        session_obj = event['data']['object']
        username = session_obj['metadata'].get('username')
        plan = session_obj['metadata'].get('plan')
        print(f"[DEBUG] Webhook received for username: {username}, plan: {plan}")
        # Update payment status in DB
        db = sqlite3.connect(DATABASE)
        db.execute('UPDATE stripe_status SET payment_status=1 WHERE username=?', (username,))
        db.commit()
        # Print out the updated row for debug
        cur = db.execute('SELECT stripe_setup, payment_status FROM stripe_status WHERE username=?', (username,))
        row = cur.fetchone()
        print(f"[DEBUG] Webhook DB row after update: {row}")
        db.close()
        # Update leaderboard earnings and level
        # Set plan->level mapping for display
        plan_level = plan.replace('$29 Basic Starter', 'Starter').replace('Basic Starter', 'Starter').replace('$99 Pro', 'Pro').replace('Pro', 'Pro').replace('$249 Elite', 'Elite').replace('Elite', 'Elite').replace('$499 VIP', 'VIP').replace('VIP', 'VIP')
        # Set earnings amount based on plan
        plan_amounts = {
            '$29 Basic Starter': 29.00, 'Basic Starter': 29.00,
            '$99 Pro': 99.00, 'Pro': 99.00,
            '$249 Elite': 249.00, 'Elite': 249.00,
            '$499 VIP': 499.00, 'VIP': 499.00
        }
        earned = plan_amounts.get(plan, 0.0)
        # Fetch current earnings and referrals
        with sqlite3.connect(DATABASE) as db:
            cur = db.execute('SELECT referrals, earnings FROM leaderboard WHERE username=?', (username,))
            stats = cur.fetchone()
            if stats:
                new_earnings = stats[1] + earned
                db.execute('UPDATE leaderboard SET earnings=?, level=? WHERE username=?', (new_earnings, plan_level, username))
            else:
                db.execute('INSERT INTO leaderboard (username, referrals, earnings, level) VALUES (?, ?, ?, ?)', (username, 0, earned, plan_level))
            db.commit()
        # Send affiliate info to Zapier
        zapier_webhook_url = os.getenv('ZAPIER_WEBHOOK_URL', '')
        if zapier_webhook_url:
            data = {
                'username': username,
                'plan': plan,
                'event': 'affiliate_paid'
            }
            try:
                requests.post(zapier_webhook_url, json=data, timeout=5)
            except Exception as zap_err:
                pass

    # Handle successful invoice payment
    if event['type'] == 'invoice.payment_succeeded':
        invoice_obj = event['data']['object']
        # Try to get username from metadata if present
        username = None
        plan = None
        if 'metadata' in invoice_obj and invoice_obj['metadata']:
            username = invoice_obj['metadata'].get('username')
            plan = invoice_obj['metadata'].get('plan')
        # If not in metadata, try to get from subscription or customer (customize as needed)
        if not username:
            print("[DEBUG] invoice.payment_succeeded: No username in metadata. Manual intervention may be required.")
        else:
            print(f"[DEBUG] Invoice webhook received for username: {username}, plan: {plan}")
            db = sqlite3.connect(DATABASE)
            db.execute('UPDATE stripe_status SET payment_status=1 WHERE username=?', (username,))
            db.commit()
            cur = db.execute('SELECT stripe_setup, payment_status FROM stripe_status WHERE username=?', (username,))
            row = cur.fetchone()
            print(f"[DEBUG] Invoice Webhook DB row after update: {row}")
            db.close()
            # Update leaderboard earnings and level
            plan_level = plan.replace('$29 Basic Starter', 'Starter').replace('Basic Starter', 'Starter').replace('$99 Pro', 'Pro').replace('Pro', 'Pro').replace('$249 Elite', 'Elite').replace('Elite', 'Elite').replace('$499 VIP', 'VIP').replace('VIP', 'VIP')
            plan_amounts = {
                '$29 Basic Starter': 29.00, 'Basic Starter': 29.00,
                '$99 Pro': 99.00, 'Pro': 99.00,
                '$249 Elite': 249.00, 'Elite': 249.00,
                '$499 VIP': 499.00, 'VIP': 499.00
            }
            earned = plan_amounts.get(plan, 0.0)
            with sqlite3.connect(DATABASE) as db:
                cur = db.execute('SELECT referrals, earnings FROM leaderboard WHERE username=?', (username,))
                stats = cur.fetchone()
                if stats:
                    new_earnings = stats[1] + earned
                    db.execute('UPDATE leaderboard SET earnings=?, level=? WHERE username=?', (new_earnings, plan_level, username))
                else:
                    db.execute('INSERT INTO leaderboard (username, referrals, earnings, level) VALUES (?, ?, ?, ?)', (username, 0, earned, plan_level))
                db.commit()
            zapier_webhook_url = os.getenv('ZAPIER_WEBHOOK_URL', '')
            if zapier_webhook_url:
                data = {
                    'username': username,
                    'plan': plan,
                    'event': 'affiliate_paid_invoice'
                }
                try:
                    requests.post(zapier_webhook_url, json=data, timeout=5)
                except Exception as zap_err:
                    pass
# Utility function to increment referrals (call this when a referral is made)
def increment_referrals(username, level=None):
    with sqlite3.connect(DATABASE) as db:
        cur = db.execute('SELECT referrals FROM leaderboard WHERE username=?', (username,))
        stats = cur.fetchone()
        if stats:
            new_referrals = stats[0] + 1
            if level:
                db.execute('UPDATE leaderboard SET referrals=?, level=? WHERE username=?', (new_referrals, level, username))
            else:
                db.execute('UPDATE leaderboard SET referrals=? WHERE username=?', (new_referrals, username))
        else:
            db.execute('INSERT INTO leaderboard (username, referrals, earnings, level) VALUES (?, ?, ?, ?)', (username, 1, 0.0, level or ''))
        db.commit()
    return jsonify({'status': 'success'})

# Stripe setup route
@app.route('/stripe_setup', methods=['POST'])
def stripe_setup():
    username = session.get('username')
    if username:
        db = get_db()
        db.execute('INSERT OR REPLACE INTO stripe_status (username, stripe_setup) VALUES (?, ?)', (username, 1))
        db.commit()
    return redirect(url_for('dashboard'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if session.get('role') == 'admin':
        return render_template_string(ADMIN_DASHBOARD_TEMPLATE)
    else:
        username = session.get('username')
        print(f"[DEBUG] Dashboard loaded for username: {username}")
        with sqlite3.connect(DATABASE) as db:
            cur = db.execute('SELECT stripe_setup, payment_status FROM stripe_status WHERE username=?', (username,))
            row = cur.fetchone()
        stripe_setup = bool(row[0]) if row else False
        payment_status = bool(row[1]) if row and len(row) > 1 else False
        # Fetch referrals and earnings for this user from leaderboard table
        with sqlite3.connect(DATABASE) as db:
            cur = db.execute('SELECT referrals, earnings FROM leaderboard WHERE username=?', (username,))
            user_stats = cur.fetchone()
            if user_stats:
                referrals = user_stats[0]
                earnings = f"{user_stats[1]:.2f}"
            else:
                referrals = 0
                earnings = "0.00"
        print(f"[DEBUG] Dashboard DB row: {row} (stripe_setup={stripe_setup}, payment_status={payment_status})")
        # Query top 10 leaderboard entries by referrals, then earnings
        with sqlite3.connect(DATABASE) as db:
            cur = db.execute('SELECT username, referrals, earnings, level FROM leaderboard ORDER BY referrals DESC, earnings DESC LIMIT 10')
            leaderboard = [
                {
                    'username': r[0],
                    'referrals': r[1],
                    'earnings': f"{r[2]:.2f}",
                    'level': r[3]
                } for r in cur.fetchall()
            ]
        return render_template_string(
            USER_DASHBOARD_TEMPLATE,
            username=username,
            plan=session.get('plan'),
            stripe_setup=stripe_setup,
            payment_status=payment_status,
            referrals=referrals,
            earnings=earnings,
            leaderboard=leaderboard
        )

# Utility function to update leaderboard stats
def update_leaderboard(username, referrals=None, earnings=None, level=None):
    with sqlite3.connect(DATABASE) as db:
        # Check if user exists
        cur = db.execute('SELECT username FROM leaderboard WHERE username=?', (username,))
        exists = cur.fetchone()
        if exists:
            # Update only provided fields
            if referrals is not None:
                db.execute('UPDATE leaderboard SET referrals=? WHERE username=?', (referrals, username))
            if earnings is not None:
                db.execute('UPDATE leaderboard SET earnings=? WHERE username=?', (earnings, username))
            if level is not None:
                db.execute('UPDATE leaderboard SET level=? WHERE username=?', (level, username))
        else:
            db.execute('INSERT INTO leaderboard (username, referrals, earnings, level) VALUES (?, ?, ?, ?)',
                       (username, referrals or 0, earnings or 0.0, level or ''))
        db.commit()

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
