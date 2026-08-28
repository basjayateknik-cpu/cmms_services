import re

with open('settings.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace helpdesk module export/import/template
hd_module_code = """
@settings_bp.route('/helpdesk_module/template', methods=['GET'])
@login_required
def download_hd_module_template():
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
    import pandas as pd
    import io
    from flask import send_file
    df = pd.DataFrame(columns=['Name', 'Site ID'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="helpdesk_modules_template.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@settings_bp.route('/helpdesk_module/export', methods=['GET'])
@login_required
def export_hd_modules():
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
    import pandas as pd
    import io
    from flask import send_file
    data = []
    modules = HelpdeskModule.query.all()
    for m in modules:
        data.append({'Name': m.name, 'Site ID': m.site_id or ''})
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="helpdesk_modules.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@settings_bp.route('/helpdesk_module/import', methods=['POST'])
@login_required
def import_hd_modules():
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
    import pandas as pd
    file = request.files.get('file')
    if not file or not file.filename.endswith(('.xlsx', '.xls')):
        flash('Please upload a valid Excel file.', 'error')
        return redirect(url_for('settings.index') + '#hd-modules')
    try:
        df = pd.read_excel(file)
        count = 0
        for index, row in df.iterrows():
            name = str(row.get('Name', '')).strip()
            if name == 'nan' or not name: continue
            site_id = str(row.get('Site ID', '')).strip()
            site_id = int(float(site_id)) if site_id != 'nan' and site_id else None
            existing = HelpdeskModule.query.filter_by(name=name, site_id=site_id).first()
            if not existing:
                new_mod = HelpdeskModule(name=name, site_id=site_id)
                db.session.add(new_mod)
                count += 1
        db.session.commit()
        flash(f'Imported {count} helpdesk modules.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error importing Excel: {str(e)}', 'error')
    return redirect(url_for('settings.index') + '#hd-modules')
"""

content = re.sub(r"@settings_bp\.route\('/helpdesk_module/export', methods=\['GET'\]\).*?return redirect\(url_for\('settings\.index'\) \+ '#hd-modules'\)", hd_module_code.strip(), content, flags=re.DOTALL)


# Replace helpdesk location export/import/template
hd_location_code = """
@settings_bp.route('/helpdesk_location/template', methods=['GET'])
@login_required
def download_hd_location_template():
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
    import pandas as pd
    import io
    from flask import send_file
    df = pd.DataFrame(columns=['Name', 'Site ID'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="helpdesk_locations_template.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@settings_bp.route('/helpdesk_location/export', methods=['GET'])
@login_required
def export_hd_locations():
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
    import pandas as pd
    import io
    from flask import send_file
    data = []
    locations = HelpdeskLocation.query.all()
    for m in locations:
        data.append({'Name': m.name, 'Site ID': m.site_id or ''})
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="helpdesk_locations.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@settings_bp.route('/helpdesk_location/import', methods=['POST'])
@login_required
def import_hd_locations():
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
    import pandas as pd
    file = request.files.get('file')
    if not file or not file.filename.endswith(('.xlsx', '.xls')):
        flash('Please upload a valid Excel file.', 'error')
        return redirect(url_for('settings.index') + '#hd-locations')
    try:
        df = pd.read_excel(file)
        count = 0
        for index, row in df.iterrows():
            name = str(row.get('Name', '')).strip()
            if name == 'nan' or not name: continue
            site_id = str(row.get('Site ID', '')).strip()
            site_id = int(float(site_id)) if site_id != 'nan' and site_id else None
            existing = HelpdeskLocation.query.filter_by(name=name, site_id=site_id).first()
            if not existing:
                new_mod = HelpdeskLocation(name=name, site_id=site_id)
                db.session.add(new_mod)
                count += 1
        db.session.commit()
        flash(f'Imported {count} helpdesk locations.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error importing Excel: {str(e)}', 'error')
    return redirect(url_for('settings.index') + '#hd-locations')
"""

content = re.sub(r"@settings_bp\.route\('/helpdesk_location/export', methods=\['GET'\]\).*?return redirect\(url_for\('settings\.index'\) \+ '#hd-locations'\)", hd_location_code.strip(), content, flags=re.DOTALL)


with open('settings.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated settings.py")
