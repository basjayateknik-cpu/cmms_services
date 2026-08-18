from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Admin':
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def supervisor_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['Admin', 'Supervisor']:
            flash('Access denied. Supervisor or Administrator privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function
def send_whatsapp_notification(phone, message):
    import requests
    import os
    
    token = os.getenv('FONNTE_TOKEN')
    api_url = os.getenv('FONNTE_API_URL', 'https://api.fonnte.com/send')
    
    if not token or not phone:
        print(f"Skipping WA: Token or phone missing. Phone: {phone}")
        return False
        
    payload = {
        'target': phone,
        'message': message,
        'countryCode': '62', # Default Indonesia
    }
    headers = {
        'Authorization': token
    }
    
    try:
        response = requests.post(api_url, data=payload, headers=headers)
        print(f"WA Notification sent to {phone}. Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending WA notification: {e}")
        return False
