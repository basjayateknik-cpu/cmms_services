import re

with open('work_orders.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix export_all
export_code = """
@work_orders_bp.route('/export')
@login_required
@supervisor_or_admin_required
def export_all():
    from models import Site
    status_filter = request.args.get('status')
    assigned_filter = request.args.get('assigned_to')
    site_filter = request.args.get('site_id', type=int)
    mt_filter = request.args.get('maintenance_type')
    
    query = WorkOrder.query
    
    if current_user.site_id:
        query = query.join(Asset).filter(Asset.site_id == current_user.site_id)
    elif site_filter:
        query = query.join(Asset).filter(Asset.site_id == site_filter)
    
    if current_user.role == 'Technician':
        query = query.filter(WorkOrder.assignees.any(id=current_user.id))
    
    if status_filter:
        if status_filter in ['Active', 'Pending', 'Closed', 'Draft']:
            query = query.join(WorkOrderStatus).filter(WorkOrderStatus.control_type == status_filter)
        else:
            if str(status_filter).isdigit():
                query = query.filter(WorkOrder.status_id == int(status_filter))
            else:
                query = query.join(WorkOrderStatus).filter(WorkOrderStatus.name == status_filter)
    if assigned_filter:
        query = query.filter(WorkOrder.assignees.any(id=assigned_filter))
    if mt_filter:
        query = query.filter(WorkOrder.maintenance_type == mt_filter)
        
    work_orders = query.all()
    
    data = []
    for wo in work_orders:
        procedures_list = []
        for p in wo.procedures:
            status = "Done" if p.is_completed else "Pending"
            procedures_list.append(f"- {p.name} ({status})")
        procedures_text = "\\n".join(procedures_list)

        checklist_list = []
        for c in wo.checklist_parameters:
            val = c.value if c.value else "N/A"
            checklist_list.append(f"- {c.parameter}: {val} (Std: {c.standard})")
        checklist_text = "\\n".join(checklist_list)

        parts_list = []
        for up in wo.used_parts:
            parts_list.append(f"- {up.part.name} (Qty: {up.quantity_used})")
        parts_text = "\\n".join(parts_list)

        data.append({
            'Code': wo.code,
            'Description': wo.description,
            'Status': wo.current_status.name if wo.current_status else '',
            'Priority': wo.priority,
            'Maintenance Type': wo.maintenance_type,
            'Asset Code': wo.asset.code if wo.asset else '',
            'Asset Name': wo.asset.name if wo.asset else '',
            'Site': wo.asset.site.name if wo.asset and wo.asset.site else '',
            'Assigned Technicians': ", ".join([u.name for u in wo.assignees]),
            'Project Code': wo.project_code,
            'Start Date': wo.start_date.strftime('%Y-%m-%d %H:%M') if wo.start_date else '',
            'End Date': wo.end_date.strftime('%Y-%m-%d %H:%M') if wo.end_date else '',
            'Suggested Start': wo.suggested_start_date.strftime('%Y-%m-%d %H:%M') if wo.suggested_start_date else '',
            'Suggested Completion': wo.suggested_completion_date.strftime('%Y-%m-%d %H:%M') if wo.suggested_completion_date else '',
            'Estimated Hours': wo.estimated_hours,
            'Tasklist': wo.tasklist.name if wo.tasklist else '',
            'Checklist': wo.checklist.name if wo.checklist else '',
            'Procedures/Tasks': procedures_text,
            'Checklist Results': checklist_text,
            'Parts Used': parts_text
        })
        
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Work Orders')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f'work_orders_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
"""
content = re.sub(r"@work_orders_bp\.route\('/export'\)\s*@login_required\s*@supervisor_or_admin_required\s*def export_all\(\):.*?return Response\(output\.getvalue\(\), mimetype=\"text/csv\", headers={\"Content-disposition\": f\"attachment; filename=work_orders_\{datetime\.now\(\)\.strftime\('%Y%m%d_%H%M'\)\}\.csv\"\}\)", export_code.strip(), content, flags=re.DOTALL)

import_code = """
@work_orders_bp.route('/import', methods=['POST'])
@login_required
@supervisor_or_admin_required
def import_all():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('work_orders.index'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('work_orders.index'))
        
    if file:
        filename = file.filename
        try:
            if filename.endswith('.xlsx') or filename.endswith('.xls'):
                df = pd.read_excel(file)
            else:
                flash('Unsupported file format. Please upload Excel (.xlsx, .xls).', 'danger')
                return redirect(url_for('work_orders.index'))
"""
content = re.sub(r"@work_orders_bp\.route\('/import', methods=\['POST'\]\)\s*@login_required\s*@supervisor_or_admin_required\s*def import_all\(\):.*?return redirect\(url_for\('work_orders\.index'\)\)\s*if filename\.endswith\('\.csv'\):\s*df = pd\.read_csv\(file\)\s*elif filename\.endswith\('\.xlsx'\) or filename\.endswith\('\.xls'\):\s*df = pd\.read_excel\(file\)\s*else:\s*flash\('Unsupported file format\. Please upload CSV or Excel\.', 'danger'\)\s*return redirect\(url_for\('work_orders\.index'\)\)\s*success_count = 0", import_code.strip() + "\n            success_count = 0", content, flags=re.DOTALL)

with open('work_orders.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated work_orders.py")
