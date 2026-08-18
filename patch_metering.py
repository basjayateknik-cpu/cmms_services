import re

with open('d:/github/22-06-2026/cmms/templates/assets/tabs/metering.html', 'r', encoding='utf8') as f:
    content = f.read()

# 1. Inject filter logic
filter_code = """
{% set start_date_filter = request.args.get('start_date', '') %}
{% set end_date_filter = request.args.get('end_date', '') %}
{% set meter_readings_map = {} %}

{% for m in asset.meters %}
    {% set filtered_readings = [] %}
    {% for r in m.readings %}
        {% set include = true %}
        {% if start_date_filter and r.reading_date.strftime('%Y-%m-%d') < start_date_filter %}
            {% set include = false %}
        {% endif %}
        {% if end_date_filter and r.reading_date.strftime('%Y-%m-%d') > end_date_filter %}
            {% set include = false %}
        {% endif %}
        {% if include %}
            {% set _ = filtered_readings.append(r) %}
        {% endif %}
    {% endfor %}
    {% set _ = meter_readings_map.update({m.id: filtered_readings}) %}
{% endfor %}

<div class="mb-3 d-flex justify-content-end">
    <form method="GET" action="{{ url_for('assets.view', id=asset.id) }}" class="d-flex align-items-center gap-2">
        <input type="hidden" name="tab" value="metering">
        <div class="input-group input-group-sm shadow-sm" style="max-width: 400px;">
            <span class="input-group-text bg-white text-primary"><i class="bi bi-calendar-range"></i></span>
            <input type="date" name="start_date" class="form-control" value="{{ start_date_filter }}" title="Start Date">
            <span class="input-group-text bg-light text-muted">-</span>
            <input type="date" name="end_date" class="form-control" value="{{ end_date_filter }}" title="End Date">
            <button type="submit" class="btn btn-primary"><i class="bi bi-funnel-fill me-1"></i> Filter</button>
            {% if start_date_filter or end_date_filter %}
            <a href="{{ url_for('assets.view', id=asset.id, tab='metering') }}" class="btn btn-outline-secondary" title="Reset Filter"><i class="bi bi-x-lg"></i></a>
            {% endif %}
        </div>
    </form>
</div>
"""

content = content.replace('{% if asset.meters %}\n<div id="logsheetSection"', '{% if asset.meters %}\n' + filter_code + '\n<div id="logsheetSection"')

# 2. Replace meter.readings with meter_readings_map[meter.id]
content = content.replace("meter.readings|sort", "meter_readings_map[meter.id]|sort")

# 3. Remove "TREND" text from the label
content = content.replace("{% if meter.api_url %}LIVE{% else %}TREND{% endif %}", "{% if meter.api_url %}LIVE{% endif %}")

with open('d:/github/22-06-2026/cmms/templates/assets/tabs/metering.html', 'w', encoding='utf8') as f:
    f.write(content)

print("Patched successfully")
