import re

with open('templates/assets/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Export dropdown items
export_dropdown = """
                        <!-- Export Dropdown -->
                        <div class="dropdown">
                            <button class="btn btn-light border shadow-sm rounded-pill px-3 dropdown-toggle" type="button" id="exportDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="bi bi-download me-1"></i> Export
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="exportDropdown">
                                <li><a class="dropdown-item" href="{{ url_for('assets.export_assets', format='excel') }}"><i class="bi bi-file-earmark-excel me-2 text-success"></i>Excel (.xlsx)</a></li>
                                <li><a class="dropdown-item" href="{{ url_for('assets.export_assets', format='csv') }}"><i class="bi bi-file-earmark-spreadsheet me-2 text-primary"></i>CSV (.csv)</a></li>
                            </ul>
                        </div>
"""
new_export = """
                        <a href="{{ url_for('assets.export_assets') }}" class="btn btn-light border shadow-sm rounded-pill px-3">
                            <i class="bi bi-file-earmark-excel me-1 text-success"></i> Export Excel
                        </a>
"""
# Note: If it's slightly different, we will use regex.
content = re.sub(r"<!-- Export Dropdown -->.*?</div>", new_export.strip(), content, flags=re.DOTALL)

# Fix import Modal accept
content = content.replace('accept=".csv,.xlsx,.xls"', 'accept=".xlsx,.xls"')
content = content.replace('CSV or Excel', 'Excel')

with open('templates/assets/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated templates/assets/index.html")
