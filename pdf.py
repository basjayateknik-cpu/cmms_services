@app.route('/export/pdf/<string:chiller_id>', methods=['GET', 'POST'])
def report_pdf(chiller_id):
    if 'logged_in' not in session:
        flash('Anda harus login untuk mengakses laporan.', 'warning')
        return redirect(url_for('auth.login'))

    notes = {}
    if request.method == 'POST':
        for key, value in request.form.items():
            if key.startswith('notes_'):
                notes[key[6:]] = value
        unit = request.form.get('unit', 'celsius')
    else:
        unit = request.args.get('unit', 'celsius')


    conn = get_db_connection()
    if not conn:
        flash("Tidak dapat terhubung ke database.", "danger")
        return redirect(url_for('index'))

    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM chillers WHERE id = %s", (chiller_id,))
        chiller_details = cursor.fetchone()
        
        if not chiller_details:
            flash("Chiller tidak ditemukan.", "danger")
            return redirect(url_for('index'))
            
        site_id = chiller_details['site_id']
        user_id = session.get('user_id')
        user_role = session.get('role')

        if user_role not in ['Admin', 'Viewer']:
            cursor.execute("SELECT user_id FROM user_site_access WHERE user_id = %s AND site_id = %s", (user_id, site_id))
            if not cursor.fetchone():
                flash("Anda tidak memiliki izin untuk mengakses laporan chiller ini.", "danger")
                return redirect(url_for('select_site'))

        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        now = datetime.now()
        start_date = datetime.fromisoformat(start_date_str) if start_date_str else now - timedelta(hours=12)
        end_date = datetime.fromisoformat(end_date_str) if end_date_str else now

        historical_data = []
        try:
            params = {
                'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%S'),
                'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%S')
            }
            api_url = f'http://127.0.0.1:8000/chillers/{chiller_id}/history'
            response_history = requests.get(api_url, params=params)
            response_history.raise_for_status()
            historical_data = response_history.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            flash(f'Gagal mengambil data dari API untuk laporan: {e}', 'danger')
            return redirect(url_for('test', chiller_id=chiller_id))

        if not historical_data:
            flash('Tidak ada data historis untuk periode yang dipilih.', 'warning')
            return redirect(url_for('test', chiller_id=chiller_id, start_date=start_date.strftime('%Y-%m-%dT%H:%M'), end_date=end_date.strftime('%Y-%m-%dT%H:%M')))

        safe_ranges = {
            "evap_lwt": {"min": 5.5, "max": 8.8}, "evap_rwt": {"min": 11.11, "max": 14.44},
            "evap_satur_temp": {"min": 3.33, "max": 6.67}, "cond_lwt": {"min": 32.22, "max": 35.55},
            "cond_rwt": {"min": 26.67, "max": 30.0}, "cond_satur_temp": {"min": 32.22, "max": 40.56},
            "oil_sump_temp": {"min": 40.56, "max": 53.89}, "discharge_temp": {"min": 40.56, "max": 53.89},
        }
        chart_sections = {
            "Evaporator": [{"key": "evap_lwt", "label": "Evap LWT (°C)"}, {"key": "evap_rwt", "label": "Evap RWT (°C)"}, {"key": "evap_pressure", "label": "Evap Pressure (kPa)"}, {"key": "evap_satur_temp", "label": "Evap Sat. Temp (°C)"}],
            "Condenser": [{"key": "cond_lwt", "label": "Cond LWT (°C)"}, {"key": "cond_rwt", "label": "Cond RWT (°C)"}, {"key": "cond_pressure", "label": "Cond Pressure (kPa)"}, {"key": "cond_satur_temp", "label": "Cond Sat. Temp (°C)"}],
            "Oil & Discharge": [{"key": "oil_sump_temp", "label": "Oil Sump Temp (°C)"}, {"key": "discharge_temp", "label": "Discharge Temp (°C)"}],
            "Power": [{"key": "fla", "label": "FLA (%)"}, {"key": "input_power", "label": "Input Power (kW)"}, {"key": "VSD_Input_Power", "label": "Input Power (kW)"}]
        }

        if unit == 'fahrenheit':
            temp_keys_to_convert = []
            pressure_keys_to_convert = []
            for section in chart_sections.values():
                for param in section:
                    if "(°C)" in param['label']:
                        temp_keys_to_convert.append(param['key'])
                        param['label'] = param['label'].replace('°C', '°F')
                    elif "(kPa)" in param['label']:
                        pressure_keys_to_convert.append(param['key'])
                        param['label'] = param['label'].replace('kPa', 'psi')
            
            for d in historical_data:
                for key in temp_keys_to_convert:
                    if key in d and d[key] is not None:
                        d[key] = celsius_to_fahrenheit(d[key])
                for key in pressure_keys_to_convert:
                    if key in d and d[key] is not None:
                        d[key] = kpa_to_psi(d[key])
            
            for key in temp_keys_to_convert:
                if key in safe_ranges:
                    safe_ranges[key]['min'] = celsius_to_fahrenheit(safe_ranges[key]['min'])
                    safe_ranges[key]['max'] = celsius_to_fahrenheit(safe_ranges[key]['max'])
            
            for key in pressure_keys_to_convert:
                if key in safe_ranges:
                    safe_ranges[key]['min'] = kpa_to_psi(safe_ranges[key]['min'])
                    safe_ranges[key]['max'] = kpa_to_psi(safe_ranges[key]['max'])

        generation_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        pdf = PDFWithMargins(generation_time=generation_time, with_template_background=True)
        pdf.set_auto_page_break(auto=True, margin=25)
        pdf.add_page()

        pdf.set_font('helvetica', 'B', 16)
        site_name = session.get('current_site_name', 'Unknown Site')
        chiller_name = chiller_details.get('chiller_num', chiller_id)
        pdf.cell(0, 10, f'Laporan Chiller - {site_name}', 0, 1, 'C')
        pdf.cell(0, 10, f'Chiller: {chiller_name}', 0, 1, 'C')
        pdf.ln(10)

        # Determine chiller image based on chiller_category
        chiller_category = chiller_details.get('chiller-cat', '').lower() if chiller_details else ''
        if chiller_category == 'air cooled':
            image_filename = 'aircool_off.png'
        elif chiller_category == 'screw':
            image_filename = 'screw-off.png'
        else:
            image_filename = 'chiller.png'
        
        image_path = os.path.join(app.static_folder, 'images', image_filename)
        if os.path.exists(image_path):
            # Hitung posisi x untuk pemusatan gambar dengan lebar 150mm
            image_width = 150
            page_width = pdf.w - pdf.l_margin - pdf.r_margin
            x_centered = pdf.l_margin + (page_width - image_width) / 2

            pdf.image(image_path, x=x_centered, y=pdf.get_y(), w=image_width)
            pdf.ln(85)

        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(0, 10, 'Chiller Details', 0, 1, 'C')
        pdf.ln(5)
        pdf.set_font('helvetica', '', 10)
        table_width = 150
        col_width_key = 60
        col_width_value = 90
        start_x = (pdf.w - table_width) / 2
        # Display only: Serial Number, Model Number, Compressor Model, Ton of Refrigeration
        details_to_show = {
            "Serial Number": chiller_details.get('serial_number'),
            "Model Number": chiller_details.get('model_number'),
            "Ton of Refrigeration": chiller_details.get('ton_of_refrigeration')
        }
        for key, value in details_to_show.items():
            if value is not None and str(value).strip():
                pdf.set_x(start_x)
                pdf.cell(col_width_key, 10, f'{key}:', 1, 0)
                pdf.cell(col_width_value, 10, str(value), 1, 1)
        pdf.ln(10)

        timestamps = [datetime.fromisoformat(d['timestamp']) for d in historical_data]
        for section_title, parameters_in_section in chart_sections.items():
            if not any(p['key'] in historical_data[0] for p in parameters_in_section):
                continue
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 14)
            pdf.cell(0, 10, section_title, 0, 1, 'L')
            pdf.ln(2)
            for param in parameters_in_section:
                if param['key'] in historical_data[0] and historical_data[0][param['key']] is not None:
                    values = [d.get(param['key']) for d in historical_data]
                    plot_data = [(t, v) for t, v in zip(timestamps, values) if v is not None]
                    if not plot_data: continue
                    plot_timestamps, plot_values = zip(*plot_data)
                    if pdf.get_y() + 90 > pdf.page_break_trigger:
                        pdf.add_page()
                        pdf.set_font('helvetica', 'B', 14)
                        pdf.cell(0, 10, section_title, 0, 1, 'L')
                        pdf.ln(2)
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(plot_timestamps, plot_values, marker='.', linestyle='-', markersize=8, zorder=2)
                    if param['key'] in safe_ranges:
                        s_range = safe_ranges[param['key']]
                        ax.axhspan(s_range['min'], s_range['max'], color='green', alpha=0.2, label='Safe Range', zorder=1)
                        ax.legend()
                    ax.set_title(param['label'], fontsize=14)
                    ax.set_xlabel('Waktu', fontsize=10)
                    ax.set_ylabel(param['label'].split(' ')[-1], fontsize=10)
                    ax.grid(True)
                    fig.autofmt_xdate()
                    plt.tight_layout()
                    img_buffer = BytesIO()
                    fig.savefig(img_buffer, format='png', dpi=100)
                    img_buffer.seek(0)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                        tmpfile.write(img_buffer.read())
                        tmp_filename = tmpfile.name
                    try:
                        pdf.image(tmp_filename, x=None, y=None, w=190)
                    finally:
                        os.remove(tmp_filename)
                    plt.close(fig)
                    pdf.ln(2)
                    note = notes.get(param['key'], '').strip()
                    pdf.set_font('helvetica', 'B', 10)
                    pdf.cell(0, 5, 'NOTE:', 0, 1, 'L')
                    pdf.set_font('helvetica', '', 10)
                    if note:
                        pdf.multi_cell(0, 5, note)
                    else:
                        pdf.multi_cell(0, 5, '-')
                    pdf.ln(10)

        if historical_data:
            parameters_to_plot = []
            for section_params in chart_sections.values():
                parameters_to_plot.extend(section_params)
            valid_parameters = [p for p in parameters_to_plot if p['key'] in historical_data[0] and any(d.get(p['key']) is not None for d in historical_data)]
            data_points_per_table =10
            data_chunks = [historical_data[i:i + data_points_per_table] for i in range(0, len(historical_data), data_points_per_table)]
            header_height = 20
            row_height = 5
            table_height = header_height + (len(valid_parameters) * row_height) + 2
            pdf.add_page(orientation='L')
            pdf.set_font('helvetica', 'B', 12)
            pdf.cell(0, 10, 'Data Historis', 0, 1, 'L')
            
            is_first_table_on_page = True
            for table_data in data_chunks:
                if not is_first_table_on_page and (pdf.get_y() + table_height > pdf.page_break_trigger):
                    pdf.add_page(orientation='L')
                    pdf.set_font('helvetica', 'B', 12)
                    pdf.cell(0, 10, 'Data Historis (Lanjutan)', 0, 1, 'L')
                    is_first_table_on_page = True
                if not is_first_table_on_page:
                    pdf.ln(2)
                timestamps = [datetime.fromisoformat(d['timestamp']).strftime('%H:%M %d-%m-%y') for d in table_data]
                header_labels = ['Parameter'] + timestamps
                param_col_width = 55
                num_data_cols = len(table_data)
                data_col_width = (pdf.w - 20 - param_col_width) / num_data_cols if num_data_cols > 0 else 0
                col_widths = [param_col_width] + [data_col_width] * num_data_cols
                pdf.set_font('helvetica', 'B', 8)
                y_start = pdf.get_y()
                x_start = pdf.get_x()
                pdf.multi_cell(col_widths[0], header_height, header_labels[0], border=1, align='C')
                current_x = x_start + col_widths[0]
                for i, header in enumerate(header_labels[1:]):
                    pdf.set_xy(current_x, y_start)
                    pdf.multi_cell(col_widths[i+1], header_height, header, border=1, align='C')
                    current_x += col_widths[i+1]
                pdf.set_y(y_start + header_height)
                pdf.set_font('helvetica', '', 9)
                for param_info in valid_parameters:
                    param_key = param_info['key']
                    param_label = param_info['label']
                    pdf.cell(col_widths[0], row_height, param_label, 1)
                    for data_point in table_data:
                        value = data_point.get(param_key)
                        if value is None:
                            display_value = '-'
                        elif isinstance(value, float):
                            display_value = f'{value:.2f}'
                        else:
                            display_value = str(value)
                        pdf.cell(data_col_width, row_height, display_value, 1, align='C')
                    pdf.ln()
                is_first_table_on_page = False

        pdf_output = pdf.output(dest='S').encode('latin-1')
        return Response(pdf_output, mimetype='application/pdf', headers={'Content-Disposition': f'inline; filename=report_{chiller_id}_{start_date.strftime("%Y%m%d")}.pdf'})

    except Exception as e:
        import traceback
        print(f"An error occurred during PDF generation for chiller {chiller_id}:")
        traceback.print_exc()
        flash(f"Gagal membuat laporan PDF karena kesalahan internal: {e}", "danger")
        return redirect(url_for('test', chiller_id=chiller_id))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
