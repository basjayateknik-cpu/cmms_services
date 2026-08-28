import re

with open('settings.py', 'r', encoding='utf-8') as f:
    content = f.read()

safe_ranges_code = """
@settings_bp.route('/site/<int:id>/safe_ranges/export')
@login_required
def export_safe_ranges(id):
    from models import Site
    import pandas as pd
    import io
    from flask import send_file
    
    site = Site.query.get_or_404(id)
    data = []
    for r in site.safe_ranges:
        data.append({
            'Parameter Key': r.parameter_key,
            'Min Value': r.min_value if r.min_value is not None else '',
            'Max Value': r.max_value if r.max_value is not None else ''
        })
    df = pd.DataFrame(data, columns=['Parameter Key', 'Min Value', 'Max Value'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    
    filename = f'safe_ranges_{site.name.replace(" ", "_")}.xlsx'
    return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
"""

content = re.sub(r"@settings_bp\.route\('/site/<int:id>/safe_ranges/export'\).*?return response", safe_ranges_code.strip(), content, flags=re.DOTALL)

with open('settings.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated safe ranges in settings.py")
