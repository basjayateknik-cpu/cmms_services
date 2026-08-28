import re

with open('helpdesk.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix export_all
export_code = """
@helpdesk_bp.route('/export')
@login_required
@supervisor_or_admin_required
def export_all():
    status_filter = request.args.get('status')
    module_filter = request.args.get('module')
    
    query = HelpdeskTicket.query
    
    if current_user.site_id:
        query = query.filter_by(site_id=current_user.site_id)
        
    if status_filter:
        query = query.filter_by(status=status_filter)
    if module_filter:
        query = query.filter_by(module=module_filter)
        
    tickets = query.order_by(HelpdeskTicket.date_created.desc()).all()
    
    data = []
    for t in tickets:
        data.append({
            'Ticket Code': t.ticket_code,
            'Module': t.module,
            'Location': t.location,
            'Problem Description': t.problem_description,
            'PIC': t.pic,
            'Status': t.status,
            'Priority': t.priority,
            'Date Created': t.date_created.strftime('%Y-%m-%d %H:%M:%S'),
            'Created By': t.created_by.name if t.created_by else 'Unknown',
            'Work Order Code': t.work_order.code if t.work_order else ''
        })
        
    import pandas as pd
    import io
    from flask import send_file
    from datetime import datetime
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Helpdesk Tickets')
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name=f'helpdesk_tickets_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
"""
content = re.sub(r"@helpdesk_bp\.route\('/export'\).*?def export_all\(\):.*?return Response\(output\.getvalue\(\), mimetype=\"text/csv\", headers={\"Content-disposition\": f\"attachment; filename=helpdesk_tickets_\{datetime\.now\(\)\.strftime\('%Y%m%d_%H%M'\)\}\.csv\"\}\)", export_code.strip(), content, flags=re.DOTALL)


import_code = """
@helpdesk_bp.route('/import', methods=['POST'])
@login_required
@supervisor_or_admin_required
def import_tickets():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('helpdesk.index'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('helpdesk.index'))
        
    if file:
        filename = file.filename
        try:
            import pandas as pd
            if filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
            else:
                flash('Unsupported file format. Please upload Excel (.xlsx, .xls).', 'danger')
                return redirect(url_for('helpdesk.index'))
"""
content = re.sub(r"@helpdesk_bp\.route\('/import', methods=\['POST'\]\)\s*@login_required\s*@supervisor_or_admin_required\s*def import_tickets\(\):.*?return redirect\(url_for\('helpdesk\.index'\)\)\s*if filename\.endswith\('\.csv'\):\s*df = pd\.read_csv\(file\)\s*elif filename\.endswith\('\.xlsx'\) or filename\.endswith\('\.xls'\):\s*df = pd\.read_excel\(file\)\s*else:\s*flash\('Unsupported file format\. Please upload CSV or Excel\.', 'danger'\)\s*return redirect\(url_for\('helpdesk\.index'\)\)", import_code.strip(), content, flags=re.DOTALL)

with open('helpdesk.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated helpdesk.py")
