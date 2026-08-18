import re

with open('templates/assets/tabs/metering.html', 'r', encoding='utf8') as f:
    content = f.read()

# 1. Add AI Button
ai_button = """        <button class="btn btn-sm btn-warning text-dark fw-bold me-2" data-bs-toggle="modal" data-bs-target="#aiAnalysisModal"><i class="bi bi-stars"></i> Analisis AI</button>
        <button class="btn btn-sm btn-primary\""""
content = content.replace('        <button class="btn btn-sm btn-primary"', ai_button)

# 2. Add AI Modal
ai_modal = """
<!-- AI Analysis Modal -->
<div class="modal fade" id="aiAnalysisModal" tabindex="-1">
    <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
            <div class="modal-header bg-warning text-dark">
                <h5 class="modal-title fw-bold"><i class="bi bi-stars"></i> Analisis Kondisi Aset dengan AI</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="alert alert-info py-2 mb-3">
                    <h6 class="fw-bold mb-1"><i class="bi bi-info-circle"></i> Konteks Aset</h6>
                    <ul class="mb-0 ps-3 small">
                        <li><strong>Unit:</strong> {{ asset.name }} ({{ asset.code }})</li>
                        <li><strong>Kategori:</strong> {{ asset.category.name if asset.category else '-' }}</li>
                        <li><strong>Subkategori:</strong> {{ asset.subcategory.name if asset.subcategory else '-' }}</li>
                        <li><strong>Lokasi:</strong> {{ asset.location.name if asset.location else '-' }} ({{ asset.site.name if asset.site else '-' }})</li>
                        {% if asset.specifications %}
                        <li><strong>Spesifikasi:</strong> {{ asset.specifications[:100] }}...</li>
                        {% endif %}
                    </ul>
                </div>

                <h6 class="fw-bold mb-2">Pilih Parameter yang Dianalisis:</h6>
                <form id="aiAnalysisForm">
                    <div class="row mb-3">
                        {% for meter in asset.meters %}
                        {% set latest_reading = meter_readings_map[meter.id][0] if meter_readings_map.get(meter.id) else none %}
                        <div class="col-md-6 mb-2">
                            <div class="form-check">
                                <input class="form-check-input ai-meter-checkbox" type="checkbox" value="{{ meter.id }}" id="aiMeter{{ meter.id }}" checked 
                                    data-meter-name="{{ meter.name }}" 
                                    data-meter-value="{{ latest_reading.reading_value if latest_reading else 'N/A' }}">
                                <label class="form-check-label" for="aiMeter{{ meter.id }}">
                                    {{ meter.name }} 
                                    <span class="badge bg-secondary ms-1">{{ latest_reading.reading_value if latest_reading else 'N/A' }} {{ meter.unit or '' }}</span>
                                </label>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </form>

                <div id="aiAnalysisResult" class="d-none mt-4 p-3 bg-light border rounded">
                    <!-- Result goes here -->
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Tutup</button>
                <button type="button" class="btn btn-warning fw-bold" id="btnRunAiAnalysis"><i class="bi bi-lightning-charge"></i> Mulai Analisis</button>
            </div>
        </div>
    </div>
</div>
"""
# Find a place to insert the modal, e.g. right before "<!-- Add Meter Modal -->"
content = content.replace("<!-- Add Meter Modal -->", ai_modal + "\n<!-- Add Meter Modal -->")

# 3. Add JS logic
js_logic = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    const btnRun = document.getElementById('btnRunAiAnalysis');
    const resultDiv = document.getElementById('aiAnalysisResult');
    
    if (btnRun) {
        btnRun.addEventListener('click', function() {
            // Build Prompt
            let prompt = `Tolong analisis kondisi aset berikut berdasarkan data meter/sensor terbarunya. Berikan ringkasan kondisi, deteksi anomali jika ada, dan rekomendasi perawatan.\\n\\n`;
            prompt += `Informasi Aset:\\n`;
            prompt += `- Nama: {{ asset.name }} ({{ asset.code }})\\n`;
            prompt += `- Kategori: {{ asset.category.name if asset.category else '-' }}\\n`;
            prompt += `- Subkategori: {{ asset.subcategory.name if asset.subcategory else '-' }}\\n`;
            prompt += `- Lokasi: {{ asset.location.name if asset.location else '-' }}\\n\\n`;
            prompt += `Data Parameter Terpilih:\\n`;
            
            const checkboxes = document.querySelectorAll('.ai-meter-checkbox:checked');
            if(checkboxes.length === 0) {
                alert("Pilih minimal satu parameter untuk dianalisis!");
                return;
            }
            
            checkboxes.forEach(cb => {
                prompt += `- ${cb.getAttribute('data-meter-name')}: ${cb.getAttribute('data-meter-value')}\\n`;
            });
            
            // Show loading
            resultDiv.classList.remove('d-none');
            resultDiv.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-warning" role="status"></div><p class="mt-2 text-muted">Sedang menganalisis data...</p></div>';
            btnRun.disabled = true;
            
            // Post to backend
            fetch("{{ url_for('assets.analyze_meters', id=asset.id) }}", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token() }}'
                },
                body: JSON.stringify({ prompt: prompt })
            })
            .then(res => res.json())
            .then(data => {
                btnRun.disabled = false;
                if(data.success) {
                    if (typeof marked !== 'undefined') {
                        resultDiv.innerHTML = marked.parse(data.output);
                    } else {
                        resultDiv.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit;">${data.output}</pre>`;
                    }
                } else {
                    resultDiv.innerHTML = `<div class="alert alert-danger">${data.message || 'Terjadi kesalahan'}</div>`;
                }
            })
            .catch(err => {
                btnRun.disabled = false;
                resultDiv.innerHTML = `<div class="alert alert-danger">Error komunikasi dengan server: ${err}</div>`;
            });
        });
    }
});
</script>
"""
# Insert JS before final script tag or at end of file
content = content + js_logic

with open('templates/assets/tabs/metering.html', 'w', encoding='utf8') as f:
    f.write(content)

print("AI Patch applied successfully")
