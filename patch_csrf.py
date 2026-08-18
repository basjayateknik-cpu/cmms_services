import os
import re

TEMPLATE_DIR = r'\\100.84.178.115\developing\cmms_app\templates'
CSRF_INPUT = '\n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>'

# Regex to match <form ...> ignoring case. It handles attributes that span multiple lines minimally.
form_tag_re = re.compile(r'(<form[^>]*method=["\']post["\'][^>]*>)', re.IGNORECASE)

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find forms
    new_content = content
    
    # We want to replace <form ...> with <form ...> + CSRF_INPUT
    # But only if it doesn't already contain a csrf_token inside the form (or we just inject it and let WTForms pick the first).
    # To be safer, we inject it right after the opening tag.
    
    # Actually, a better approach: 
    # Use re.sub to inject CSRF_INPUT right after the matched group 1
    # Check if csrf_token is already in the file to avoid double injecting if run twice
    
    # But some forms might already have it. 
    # Let's do a simple replace:
    def replacer(match):
        original = match.group(1)
        return original + CSRF_INPUT

    if 'csrf_token()' not in new_content:
        # It's possible the form uses action="/somewhere" method="POST"
        # We also want to catch method=POST or method="POST" or METHOD='post'
        # Regex updated in compile: method=["\']post["\']
        
        # Let's use a broader regex to catch all forms, since even GET forms might be fine to have the token (though unnecessary).
        # Actually, Flask-WTF only checks POST/PUT/PATCH/DELETE.
        # Let's patch ALL <form...> tags that have method="POST".
        new_content = form_tag_re.sub(replacer, new_content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Patched {filepath}")

def main():
    if not os.path.isdir(TEMPLATE_DIR):
        print(f"Error: Directory {TEMPLATE_DIR} not found.")
        return
        
    for root, dirs, files in os.walk(TEMPLATE_DIR):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                patch_file(filepath)

if __name__ == "__main__":
    main()
