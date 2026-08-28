import re

with open('templates/warehouse/site_parts.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Export dropdown with a single Export Excel button
export_dropdown = """
                        <!-- Export Dropdown -->
                        <div class="dropdown">
                            <button class="btn btn-light border shadow-sm rounded-pill px-3 dropdown-toggle" type="button" id="exportDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="bi bi-download me-1"></i> Export
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="exportDropdown">
                                <li><a class="dropdown-item" href="{{ url_for('warehouse.export_site_inventory', site_id=site.id, format='excel') }}"><i class="bi bi-file-earmark-excel me-2 text-success"></i>Excel (.xlsx)</a></li>
                                <li><a class="dropdown-item" href="{{ url_for('warehouse.export_site_inventory', site_id=site.id, format='csv') }}"><i class="bi bi-file-earmark-spreadsheet me-2 text-primary"></i>CSV (.csv)</a></li>
                            </ul>
                        </div>
"""
new_export_btn = """
                        <a href="{{ url_for('warehouse.export_site_inventory', site_id=site.id) }}" class="btn btn-light border shadow-sm rounded-pill px-3">
                            <i class="bi bi-file-earmark-excel me-1 text-success"></i> Export Excel
                        </a>
"""
# Note: The dropdown might have slightly different spacing, so regex is safer.
content = re.sub(r"<!-- Export Dropdown -->.*?</div>", new_export_btn.strip(), content, flags=re.DOTALL)

with open('templates/warehouse/site_parts.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated site_parts.html export button")
