import re

with open('warehouse.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix export
export_code = """
@warehouse_bp.route('/site/<int:site_id>/export')
@login_required
def export_site_inventory(site_id):
    if current_user.role == 'Technician' or (current_user.site_id and current_user.site_id != site_id):
        return redirect(url_for('dashboard'))
    
    site = Site.query.get_or_404(site_id)
    search_query = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)
    
    query = StockLevel.query.filter_by(site_id=site_id)
    if category_id:
        query = query.join(Part).filter(Part.category_id == category_id)
    if search_query:
        search_term = f"%{search_query}%"
        query = query.join(Part).filter(
            db.or_(Part.part_number.ilike(search_term), Part.name.ilike(search_term))
        )
        
    stocks = query.all()
    
    data = []
    for stock in stocks:
        data.append({
            'Part Number': stock.part.part_number,
            'Part Name': stock.part.name,
            'Category': stock.part.category.name if stock.part.category else '',
            'Quantity': stock.quantity,
            'Min Level': stock.min_level,
            'Max Level': stock.max_level,
            'Location': stock.location or '',
            'Unit Price': stock.part.unit_price or 0
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'inventory_{site.name.replace(" ", "_")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
"""
content = re.sub(r"@warehouse_bp\.route\('/site/<int:site_id>/export'\).*?headers={\"Content-disposition\": f\"attachment; filename=inventory_\{site\.name\.replace\(' ', '_'\)\}\.csv\"\}\n    \)", export_code.strip(), content, flags=re.DOTALL)

# Fix import
import_code = """
@warehouse_bp.route('/site/<int:site_id>/import', methods=['POST'])
@login_required
def import_site_inventory(site_id):
    if current_user.role == 'Technician' or (current_user.site_id and current_user.site_id != site_id):
        return redirect(url_for('dashboard'))
        
    site = Site.query.get_or_404(site_id)
    
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('warehouse.site_parts', site_id=site_id))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('warehouse.site_parts', site_id=site_id))
        
    if file:
        filename = file.filename
        try:
            if filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
            else:
                flash('Unsupported file format. Please upload Excel (.xlsx, .xls).', 'danger')
                return redirect(url_for('warehouse.site_parts', site_id=site_id))
"""
content = re.sub(r"@warehouse_bp\.route\('/site/<int:site_id>/import', methods=\\['POST'\\]\).*?return redirect\(url_for\('warehouse\.site_parts', site_id=site_id\)\)", import_code.strip(), content, flags=re.DOTALL)

with open('warehouse.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated warehouse.py")
