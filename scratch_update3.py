with open('templates/settings/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('Export CSV', 'Export Excel')
content = content.replace('Import CSV', 'Import Excel')
content = content.replace('Choose CSV File', 'Choose Excel File')
content = content.replace('accept=".csv"', 'accept=".xlsx,.xls"')

import_hd_mod_target = '<input type="file" name="file" class="form-control" accept=".xlsx,.xls" required>'
import_hd_mod_replace = '''
<div class="d-flex justify-content-between align-items-center mb-2">
    <p class="small text-muted mb-0">Upload Excel file (.xlsx) with columns: Name, Site ID</p>
    <a href="{{ url_for('settings.download_hd_module_template') }}" class="btn btn-sm btn-outline-info"><i class="bi bi-file-earmark-excel"></i> Download Template</a>
</div>
<input type="file" name="file" class="form-control" accept=".xlsx,.xls" required>
'''
content = content.replace(import_hd_mod_target, import_hd_mod_replace, 1)

import_hd_loc_replace = '''
<div class="d-flex justify-content-between align-items-center mb-2">
    <p class="small text-muted mb-0">Upload Excel file (.xlsx) with columns: Name, Site ID</p>
    <a href="{{ url_for('settings.download_hd_location_template') }}" class="btn btn-sm btn-outline-info"><i class="bi bi-file-earmark-excel"></i> Download Template</a>
</div>
<input type="file" name="file" class="form-control" accept=".xlsx,.xls" required>
'''
content = content.replace(import_hd_mod_target, import_hd_loc_replace, 1)

with open('templates/settings/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated templates/settings/index.html")
