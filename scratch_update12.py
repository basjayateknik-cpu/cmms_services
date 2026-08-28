import re

with open('reports.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix export
export_code = """
@reports_bp.route('/export/<report_id>')
@login_required
def export_excel(report_id):
    headers, rows = get_report_data(report_id)
    if headers is None:
        return "Report not found", 404

    import pandas as pd
    import io
    from flask import send_file
    
    df = pd.DataFrame(rows, columns=headers)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name=f"{report_id}_export.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
"""
content = re.sub(r"@reports_bp\.route\('/export/<report_id>'\).*?output\.headers\[\"Content-type\"\] = \"text/csv\"\n    return output", export_code.strip(), content, flags=re.DOTALL)

with open('reports.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated reports.py")
