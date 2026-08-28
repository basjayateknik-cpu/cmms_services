import re

with open('assets.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix export
export_code = """
@assets_bp.route('/export')
@login_required
@supervisor_or_admin_required
def export_assets():
    query = Asset.query
    if current_user.site_id:
        query = query.filter_by(site_id=current_user.site_id)
        
    assets = query.all()
    
    data = []
    for asset in assets:
        data.append({
            'Asset Code': asset.code,
            'Name': asset.name,
            'Serial Number': asset.serial_number,
            'Model/Brand': asset.model_brand,
            'Site': asset.site.name if asset.site else '',
            'Location': asset.location.name if asset.location else '',
            'Category': asset.category.name if asset.category else '',
            'Sub Category': asset.sub_category.name if asset.sub_category else '',
            'Status': asset.status
        })
        
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Assets')
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name="assets.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
"""
content = re.sub(r"@assets_bp\.route\('/export'\).*?return Response\(output\.getvalue\(\), mimetype=\"text/csv\", headers={\"Content-disposition\": \"attachment; filename=assets\.csv\"\}\)", export_code.strip(), content, flags=re.DOTALL)

# Fix import
import_code = """
@assets_bp.route('/import', methods=['POST'])
@login_required
@supervisor_or_admin_required
def import_assets():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('assets.index'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('assets.index'))
        
    if file:
        filename = file.filename
        try:
            if filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
            else:
                flash('Unsupported file format. Please upload Excel (.xlsx, .xls).', 'danger')
                return redirect(url_for('assets.index'))
"""
content = re.sub(r"@assets_bp\.route\('/import', methods=\['POST'\]\)\s*@login_required\s*@supervisor_or_admin_required\s*def import_assets\(\):.*?return redirect\(url_for\('assets\.index'\)\)\s*if filename\.endswith\('\.csv'\):\s*df = pd\.read_csv\(file\)\s*elif filename\.endswith\('\.xlsx'\) or filename\.endswith\('\.xls'\):\s*df = pd\.read_excel\(file\)\s*else:\s*flash\('Unsupported file format\. Please upload CSV or Excel\.', 'danger'\)\s*return redirect\(url_for\('assets\.index'\)\)", import_code.strip(), content, flags=re.DOTALL)

with open('assets.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated assets.py")
