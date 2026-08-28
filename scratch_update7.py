import re

with open('templates/work_orders/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Export dropdown items
export_dropdown = """
            <li><a class="dropdown-item" href="{{ url_for('work_orders.export_all', format='excel', **request.args) }}"><i class="bi bi-file-earmark-excel text-success"></i> Excel (.xlsx)</a></li>
            <li><a class="dropdown-item" href="{{ url_for('work_orders.export_all', format='csv', **request.args) }}"><i class="bi bi-file-earmark-text text-primary"></i> CSV (.csv)</a></li>
"""
new_export = """
            <li><a class="dropdown-item" href="{{ url_for('work_orders.export_all', format='excel', **request.args) }}"><i class="bi bi-file-earmark-excel text-success"></i> Excel (.xlsx)</a></li>
"""
content = content.replace(export_dropdown, new_export)

# Fix import Modal accept
content = content.replace('accept=".csv,.xlsx,.xls"', 'accept=".xlsx,.xls"')
content = content.replace('CSV or Excel', 'Excel')

with open('templates/work_orders/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated templates/work_orders/index.html")
