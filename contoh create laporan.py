@app.route('/report/pdf/<string:chiller_id>', methods=['GET', 'POST'])
def export_pdf(chiller_id):
    """
    Menghasilkan laporan PDF untuk chiller.
    """
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
            api_url = f'http://202.10.47.245:8000/chillers/{chiller_id}/history'
            response_history = requests.get(api_url, params=params)
            response_history.raise_for_status()
            historical_data = response_history.json()
        except requests.exceptions.RequestException as e:
            print(f"Permintaan API gagal: {e}")
            flash(f'Gagal mengambil data dari API untuk laporan: {e}', 'danger')
            return redirect(url_for('test', chiller_id=chiller_id))

        if not historical_data:
            flash('Tidak ada data historis untuk periode yang dipilih.', 'warning')
            return redirect(url_for('test', chiller_id=chiller_id, start_date=start_date.strftime('%Y-%m-%dT%H:%M'), end_date=end_date.strftime('%Y-%m-%dT%H:%M')))

        interval_hours = request.args.get('interval', 1, type=int)
        if historical_data and interval_hours > 0:
            sampled_data = []
            last_timestamp = None
            
            historical_data.sort(key=lambda x: x['timestamp'])

            for data_point in historical_data:
                current_timestamp = datetime.fromisoformat(data_point['timestamp'].replace('Z', '+00:00'))
                
                if last_timestamp is None or (current_timestamp - last_timestamp) >= timedelta(hours=interval_hours):
                    sampled_data.append(data_point)
                    last_timestamp = current_timestamp
            historical_data = sampled_data

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

        # --- Data "Customer On Call" (kosong) ---
        on_call_data = []
        # --- End ---

        generation_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        pdf = PDFWithMargins(generation_time=generation_time, with_template_background=True, header_align_left=False)
        pdf.set_auto_page_break(auto=True, margin=25)

        # Halaman Judul
        pdf.add_page()
        title_image_path = os.path.join(app.static_folder, 'images', 'judul.png')
        if os.path.exists(title_image_path):
            pdf.image(title_image_path, x=0, y=0, w=pdf.w, h=pdf.h)

        # Tambahkan judul laporan di kiri bawah
        site_name = session.get('current_site_name', 'Unknown Site')
        month_map = {
            1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL", 5: "MEI", 6: "JUNI",
            7: "JULI", 8: "AGUSTUS", 9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DESEMBER"
        }
        bulan_awal = month_map.get(start_date.month, "")
        tahun_awal = start_date.year
        bulan_akhir = month_map.get(end_date.month, "")
        tahun_akhir = end_date.year

        if bulan_awal == bulan_akhir and tahun_awal == tahun_akhir:
            periode = f"{bulan_awal} {tahun_awal}"
        elif tahun_awal != tahun_akhir:
            periode = f"{bulan_awal} {tahun_awal} - {bulan_akhir} {tahun_akhir}"
        else:
            periode = f"{bulan_awal} - {bulan_akhir} {tahun_awal}"

        line1 = "LAPORAN PEMELIHARAAN"
        line2 = f"{site_name.upper()} "
        line3 = f"PERIODE {periode}"

        pdf.set_y(-95) # 80 mm from bottom

        # Line 1
        pdf.set_font('helvetica', 'B', 28) # Bigger font
        pdf.cell(0, 10, line1, 0, 1, 'L') # ln=1 to move to next line, align Left

        # Line 2
        pdf.set_font('helvetica', 'B', 22) # Smaller font
        pdf.cell(0, 10, line2, 0, 1, 'L')

        # Line 3
        pdf.set_font('helvetica', 'B', 22)
        pdf.cell(0, 10, line3, 0, 0, 'L')

        # Halaman Surat
        pdf.add_page()
        pdf.set_font('helvetica', '', 12)
        
        pdf.cell(0, 10, '[bulan tahun]', 0, 1, 'L')
        pdf.cell(0, 10, '[site]', 0, 1, 'L')
        pdf.ln(10)

        pdf.cell(0, 10, 'Dear Bapak [nama cus],', 0, 1, 'L')
        pdf.ln(5)

        body_text = """Terima kasih atas kepercayaannya menggunakan PT Jaya Teknik Indonesia Untuk melakukan pemeliharaan chiller di [site].

Bersama ini kami sampaikan review laporan bulanan untuk periode januari 2024. dalam laporan ini kami sampaikan rekomendasi dan hasil pemeliharaan chiller di [site].

Kami bersedia untuk melakukan diskusi lanjutan untuk membahas laporan ini sehingga kami bisa mensupport kegiatan bisnis di [site]."""
        pdf.multi_cell(0, 5, body_text)
        pdf.ln(10)

        pdf.cell(0, 10, 'Hormat Kami,', 0, 1, 'L')
        pdf.ln(15)

        signature_text = """Penanggung jawab
PT Jaya Teknik Indonesia
Service Manager /jabatan penanggung jawab
Arif.Imran@jayateknik.com / email
+62 83887"""
        pdf.multi_cell(0, 7, signature_text)

        # Halaman Konten Laporan - Chiller Details
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
            "Compressor Model": chiller_details.get('compressor_model'),
            "Ton of Refrigeration": chiller_details.get('ton_of_refrigeration')
        }
        for key, value in details_to_show.items():
            if value is not None and str(value).strip():
                pdf.set_x(start_x)
                pdf.cell(col_width_key, 10, f'{key}:', 1, 0)
                pdf.cell(col_width_value, 10, str(value), 1, 1)
        pdf.ln(10)

       

        # --- Penambahan Halaman Customer On Call ---
        pdf.add_page()

        # Header block yang lebih kecil dengan latar belakang biru
        block_height = 10
        block_width = 60
        pdf.set_fill_color(0, 123, 255)
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(block_width, block_height, 'Customer On Call', 0, 0, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(block_height + 5)

        # Tentukan lebar kolom dan header
        headers = ['No.', 'Date', 'Problem Reported', 'Initiation', 'Call in\nTime', 'Time Taken to\nComplete', 'Action Complete', 'Downtime\n(hours)', 'Remarks']

        # Atur lebar kolom secara manual dalam mm. Total harus 190mm untuk A4 portrait (w=210, margin 10x2)
        col_widths = [10, 20, 35, 20, 20, 25, 25, 15, 20]

        # Cetak header tabel dengan gaya dari gambar
        pdf.set_font('helvetica', 'B', 7)
        pdf.set_fill_color(0, 86, 179)
        pdf.set_text_color(255, 255, 255)

        # Cetak setiap sel header
        current_y = pdf.get_y()
        current_x = pdf.get_x()

        for i, header in enumerate(headers):
            pdf.set_xy(current_x, current_y)
            # Draw background and border
            pdf.cell(col_widths[i], block_height, '', 1, 0, 'C', True)
            
            # Calculate y position for vertically centered text
            line_height = 4 
            num_lines = header.count('\n') + 1
            text_height = num_lines * line_height
            y_text = current_y + (block_height - text_height) / 2
            
            # Set position and draw multi-line text
            pdf.set_xy(current_x, y_text)
            pdf.multi_cell(col_widths[i], line_height, header, 0, 'C')
            
            # Move to next cell's x position for the next iteration
            current_x += col_widths[i]

        pdf.set_y(current_y + block_height)  # Move position down below the header

        # Cetak grid kosong untuk diisi manual
        pdf.set_text_color(0, 0, 0)
        row_height = 10
        for i in range(1, 11):
            fill_color = 240 if i % 2 == 0 else 255
            pdf.set_fill_color(fill_color, fill_color, fill_color)
            
            if pdf.get_y() + row_height > pdf.page_break_trigger:
                pdf.add_page()
                pdf.set_fill_color(0, 86, 179)
                pdf.set_text_color(255, 255, 255)
                current_y_new_page = pdf.get_y()
                current_x_new_page = pdf.get_x()
                for i_h, header_h in enumerate(headers):
                    pdf.set_xy(current_x_new_page, current_y_new_page)
                    pdf.cell(col_widths[i_h], block_height, header_h, 1, 'C', True)
                    current_x_new_page += col_widths[i_h]
                pdf.ln(block_height)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(255, 255, 255)

            pdf.cell(col_widths[0], row_height, str(i), 1, 0, 'C', True)
            
            for col_width in col_widths[1:]:
                pdf.cell(col_width, row_height, '', 1, 0, 'C', True)
            pdf.ln()

        pdf.ln(10)

        
        # --- Penambahan Halaman Work Order ---
        pdf.add_page()

        # Header block untuk Work Order
        block_height = 10
        block_width = 60
        pdf.set_fill_color(0, 123, 255)
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(block_width, block_height, 'Work Order', 0, 0, 'L', True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(block_height + 5)

        # Konten teks Work Order
        pdf.set_font('helvetica', '', 10)
        work_order_text = f"""Pada bagian ini kami menyampaikan list work order terhadap chiller di {site_name}, high priority work order adalah work order yang kami sarankan untuk segera dilakukan untuk mencegah kerusakan lebih lanjut. Open work order adalah work order yang perlu dilakukan action sehingga bisa closed. Closed work order adalah list work order yang telah dilakukan sehingga bisa dilakukan analisa terhadap chiller tersebut"""
        pdf.multi_cell(0, 5, work_order_text)
        pdf.ln(10)
        # --- Penambahan High Priority WO ---

        # Header block untuk High Priority WO
        block_height = 10
        block_width = 60
        pdf.set_fill_color(255, 0, 0) # Red color
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(block_width, block_height, 'High Priority WO', 0, 0, 'L', True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(block_height + 5)

        # Tabel High Priority WO
        wo_headers = ['WO NUMBER', 'DATE CREATED', 'DESCRIPTION', 'COMMENTS']
        wo_col_widths = [30, 30, 80, 50] # Total 190mm

        # Cetak header tabel
        pdf.set_font('helvetica', 'B', 7)
        pdf.set_fill_color(0, 123, 255) # Red background for header
        pdf.set_text_color(255, 255, 255)

        current_y = pdf.get_y()
        current_x = pdf.get_x()

        for i, header in enumerate(wo_headers):
            pdf.set_xy(current_x, current_y)
            # Draw background and border
            pdf.cell(wo_col_widths[i], block_height, '', 1, 0, 'C', True)
            
            # Calculate y position for vertically centered text
            line_height = 4 
            num_lines = header.count('\n') + 1
            text_height = num_lines * line_height
            y_text = current_y + (block_height - text_height) / 2
            
            # Set position and draw multi-line text
            pdf.set_xy(current_x, y_text)
            pdf.multi_cell(wo_col_widths[i], line_height, header, 0, 'C')
            
            # Move to next cell's x position
            current_x += wo_col_widths[i]

        pdf.set_y(current_y + block_height) # Move position down below the header

        # Cetak grid kosong untuk diisi manual (contoh 3 baris)
        pdf.set_text_color(0, 0, 0)
        row_height = 10
        for i in range(3): # Example 3 empty rows
            fill_color = 240 if i % 2 == 0 else 255
            pdf.set_fill_color(fill_color, fill_color, fill_color)
            
            if pdf.get_y() + row_height > pdf.page_break_trigger:
                pdf.add_page()
                # Re-print header on new page if it breaks
                pdf.set_font('helvetica', 'B', 7)
                pdf.set_fill_color(255, 0, 0)
                pdf.set_text_color(255, 255, 255)
                current_y_new_page = pdf.get_y()
                current_x_new_page = pdf.get_x()
                for i_h, header_h in enumerate(wo_headers):
                    pdf.set_xy(current_x_new_page, current_y_new_page)
                    pdf.cell(wo_col_widths[i_h], block_height, '', 1, 0, 'C', True)
                    pdf.set_xy(current_x_new_page, current_y_new_page + (block_height - (header_h.count('\n') + 1) * line_height) / 2)
                    pdf.multi_cell(wo_col_widths[i_h], line_height, header_h, 0, 'C')
                    current_x_new_page += wo_col_widths[i_h]
                pdf.set_y(current_y_new_page + block_height)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(255, 255, 255)

            for col_width in wo_col_widths:
                pdf.cell(col_width, row_height, '', 1, 0, 'C', True)
            pdf.ln()
        pdf.ln(10)
        # --- Penambahan Open Work Order ---

        # Header block untuk Open Work Order
        block_height = 10
        block_width = 60
        pdf.set_fill_color(0, 123, 255) # Blue color
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(block_width, block_height, 'Open Work Order', 0, 0, 'L', True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(block_height + 5)

        # Tabel Open Work Order
        wo_headers = ['No', 'WO NUMBER', 'DATE CREATED', 'DESCRIPTION', 'COMMENTS']
        wo_col_widths = [10, 30, 30, 80, 40] # Total 190mm

        # Cetak header tabel
        pdf.set_font('helvetica', 'B', 7)
        pdf.set_fill_color(0, 123, 255) # Blue background for header
        pdf.set_text_color(255, 255, 255)

        current_y = pdf.get_y()
        current_x = pdf.get_x()

        for i, header in enumerate(wo_headers):
            pdf.set_xy(current_x, current_y)
            # Draw background and border
            pdf.cell(wo_col_widths[i], block_height, '', 1, 0, 'C', True)
            
            # Calculate y position for vertically centered text
            line_height = 4 
            num_lines = header.count('\n') + 1
            text_height = num_lines * line_height
            y_text = current_y + (block_height - text_height) / 2
            
            # Set position and draw multi-line text
            pdf.set_xy(current_x, y_text)
            pdf.multi_cell(wo_col_widths[i], line_height, header, 0, 'C')
            
            # Move to next cell's x position
            current_x += wo_col_widths[i]

        pdf.set_y(current_y + block_height) # Move position down below the header

        # Cetak grid kosong untuk diisi manual (contoh 3 baris)
        pdf.set_text_color(0, 0, 0)
        row_height = 10
        for i in range(3): # Example 3 empty rows
            fill_color = 240 if i % 2 == 0 else 255
            pdf.set_fill_color(fill_color, fill_color, fill_color)
            
            if pdf.get_y() + row_height > pdf.page_break_trigger:
                pdf.add_page()
                # Re-print header on new page if it breaks
                pdf.set_font('helvetica', 'B', 7)
                pdf.set_fill_color(0, 123, 255)
                pdf.set_text_color(255, 255, 255)
                current_y_new_page = pdf.get_y()
                current_x_new_page = pdf.get_x()
                for i_h, header_h in enumerate(wo_headers):
                    pdf.set_xy(current_x_new_page, current_y_new_page)
                    pdf.cell(wo_col_widths[i_h], block_height, '', 1, 0, 'C', True)
                    pdf.set_xy(current_x_new_page, current_y_new_page + (block_height - (header_h.count('\n') + 1) * line_height) / 2)
                    pdf.multi_cell(wo_col_widths[i_h], line_height, header_h, 0, 'C')
                    current_x_new_page += wo_col_widths[i_h]
                pdf.set_y(current_y_new_page + block_height)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(255, 255, 255)

            for col_width in wo_col_widths:
                pdf.cell(col_width, row_height, '', 1, 0, 'C', True)
            pdf.ln()
        pdf.ln(10)
        # --- Akhir Penambahan Open Work Order ---

        # --- Penambahan Closed Work Order ---

        # Header block untuk Closed Work Order
        block_height = 10
        block_width = 60
        pdf.set_fill_color(0, 123, 255) # Blue color
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(block_width, block_height, 'Closed Work Order', 0, 0, 'L', True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(block_height + 5)

        # Tabel Closed Work Order
        wo_headers = ['No', 'WO NUMBER', 'DATE CREATED', 'DATE CLOSED', 'DESCRIPTION', 'COMMENTS']
        wo_col_widths = [10, 30, 30, 30, 50, 40] # Total 190mm

        # Cetak header tabel
        pdf.set_font('helvetica', 'B', 7)
        pdf.set_fill_color(0, 123, 255) # Blue background for header
        pdf.set_text_color(255, 255, 255)

        current_y = pdf.get_y()
        current_x = pdf.get_x()

        for i, header in enumerate(wo_headers):
            pdf.set_xy(current_x, current_y)
            # Draw background and border
            pdf.cell(wo_col_widths[i], block_height, '', 1, 0, 'C', True)
            
            line_height = 4 
            num_lines = header.count('\n') + 1
            text_height = num_lines * line_height
            y_text = current_y + (block_height - text_height) / 2
            
            # Set position and draw multi-line text
            pdf.set_xy(current_x, y_text)
            pdf.multi_cell(wo_col_widths[i], line_height, header, 0, 'C')
            
            # Move to next cell's x position
            current_x += wo_col_widths[i]

        pdf.set_y(current_y + block_height) # Move position down below the header

        # Cetak grid kosong untuk diisi manual (contoh 3 baris)
        pdf.set_text_color(0, 0, 0)
        row_height = 10
        for i in range(3): # Example 3 empty rows
            fill_color = 240 if i % 2 == 0 else 255
            pdf.set_fill_color(fill_color, fill_color, fill_color)
            
            if pdf.get_y() + row_height > pdf.page_break_trigger:
                pdf.add_page()
                # Re-print header on new page if it breaks
                pdf.set_font('helvetica', 'B', 7)
                pdf.set_fill_color(0, 123, 255)
                pdf.set_text_color(255, 255, 255)
                current_y_new_page = pdf.get_y()
                current_x_new_page = pdf.get_x()
                for i_h, header_h in enumerate(wo_headers):
                    pdf.set_xy(current_x_new_page, current_y_new_page)
                    pdf.cell(wo_col_widths[i_h], block_height, '', 1, 0, 'C', True)
                    pdf.set_xy(current_x_new_page, current_y_new_page + (block_height - (header_h.count('\n') + 1) * line_height) / 2)
                    pdf.multi_cell(wo_col_widths[i_h], line_height, header_h, 0, 'C')
                    current_x_new_page += wo_col_widths[i_h]
                pdf.set_y(current_y_new_page + block_height)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(255, 255, 255)

            for col_width in wo_col_widths:
                pdf.cell(col_width, row_height, '', 1, 0, 'C', True)
            pdf.ln()
        pdf.ln(10)
        # --- Akhir Penambahan Closed Work Order ---

        # --- Penambahan Halaman Chiller Overview ---
        pdf.add_page()
        # Header block untuk Chiller Overview
        block_height = 10
        block_width = 60
        pdf.set_fill_color(0, 123, 255) # Blue color
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(255, 255, 255)
        chiller_num = chiller_details.get('chiller_num', chiller_id)
        pdf.cell(block_width, block_height, f'Chiller {chiller_num} Overview', 0, 0, 'L', True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(block_height + 5)
        
        image_path = os.path.join(app.static_folder, 'images', 'chiller_page.png')
        if os.path.exists(image_path):
            # Hitung posisi x untuk pemusatan gambar dengan lebar 150mm
            image_width = 150
            page_width = pdf.w - pdf.l_margin - pdf.r_margin
            x_centered = pdf.l_margin + (page_width - image_width) / 2
            
            pdf.image(image_path, x=x_centered, y=pdf.get_y(), w=image_width)
            pdf.ln(85) # Adjust line break after image

        # --- Akhir Penambahan Halaman Chiller Overview ---
        pdf.ln(10)
        # --- Akhir Penambahan High Priority WO ---
        # --- Akhir Penambahan Halaman Work Order ---
# --- Akhir Penambahan Halaman Customer On Call ---


        timestamps = [datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')) for d in historical_data]
        for section_title, parameters_in_section in chart_sections.items():
            if not any(p['key'] in historical_data[0] for p in parameters_in_section):
                continue
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 14)
            pdf.cell(0, 9, section_title, 0, 1, 'L')
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
                    ax.set_title(param['label'])
                    ax.set_xlabel('Waktu')
                    ax.set_ylabel(param['label'].split(' ')[-1])
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
            data_points_per_table =9
            data_chunks = [historical_data[i:i + data_points_per_table] for i in range(0, len(historical_data), data_points_per_table)]
            header_height = 8
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
                timestamps = [datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')).strftime('%H:%M %d-%m-%y') for d in table_data]
                header_labels = ['Parameter', 'Range'] + timestamps # Added 'Safe Range'
                
                param_col_width = 55
                safe_range_col_width = 30 # New column width
                num_data_cols = len(table_data)
                remaining_width = pdf.w - 20 - param_col_width - safe_range_col_width # Adjusted remaining width
                data_col_width = remaining_width / num_data_cols if num_data_cols > 0 else 0
                col_widths = [param_col_width, safe_range_col_width] + [data_col_width] * num_data_cols # Adjusted col_widths
                
                pdf.set_font('helvetica', 'B', 8)
                y_start = pdf.get_y()
                x_start = pdf.get_x()
                
                current_x_header = x_start
                for i, header_text in enumerate(header_labels): # Loop through all headers
                    pdf.set_xy(current_x_header, y_start)
                    # Draw background and border
                    pdf.cell(col_widths[i], header_height, '', 1, 0, 'C', True)
                    
                    # Calculate y position for vertically centered text
                    line_height = 4 
                    num_lines = header_text.count('\n') + 1
                    text_height = num_lines * line_height
                    y_text = y_start + (header_height - text_height) / 2
                    
                    # Set position and draw multi-line text
                    pdf.set_xy(current_x_header, y_text)
                    pdf.multi_cell(col_widths[i], line_height, header_text, 0, 'C')
                    
                    current_x_header += col_widths[i]
                
                pdf.set_y(y_start + header_height)
                pdf.set_font('helvetica', '', 9)
                for param_info in valid_parameters:
                    param_key = param_info['key']
                    param_label = param_info['label']
                    
                    # Print Parameter label
                    pdf.cell(col_widths[0], row_height, param_label, 1)
                    
                    # Print Safe Range
                    safe_range_str = '-'
                    if param_key in safe_ranges:
                        s_range = safe_ranges[param_key]
                        if s_range['min'] is not None and s_range['max'] is not None:
                            safe_range_str = f"{s_range['min']:.2f} - {s_range['max']:.2f}"
                        elif s_range['min'] is not None:
                            safe_range_str = f"> {s_range['min']:.2f}"
                        elif s_range['max'] is not None:
                            safe_range_str = f"< {s_range['max']:.2f}"
                    pdf.cell(col_widths[1], row_height, safe_range_str, 1, align='C') # col_widths[1] for safe range
                    
                    # Print data values
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
                
                
                
        # --- Halaman Alarm Overview ---
        pdf.add_page()
        pdf.set_font('helvetica', 'B', 16)
        pdf.cell(0, 10, 'Alarm Overview', 0, 1, 'C')
        pdf.ln(10)

        alarms = []
        active_alarms = {}

        fault_types = [
            ('safety_fault', safety_codes, 'Safety'),
            ('cycling_fault', cycling_codes, 'Cycling'),
            ('warning_fault', warning_codes, 'Warning')
        ]

        if historical_data:
            # Sort data by timestamp to process chronologically
            historical_data.sort(key=lambda x: x['timestamp'])
            
            # Add a final data point to ensure all alarms are closed
            final_data_point = historical_data[-1].copy()
            final_timestamp = datetime.fromisoformat(final_data_point['timestamp'].replace('Z', '+00:00')) + timedelta(seconds=1)
            final_data_point['timestamp'] = final_timestamp.isoformat()
            for fault_key, _, _ in fault_types:
                final_data_point[fault_key] = 0
            
            extended_historical_data = historical_data + [final_data_point]

            for data_point in extended_historical_data:
                timestamp = datetime.fromisoformat(data_point['timestamp'].replace('Z', '+00:00'))
                
                for fault_key, code_dict, alarm_type in fault_types:
                    fault_code = data_point.get(fault_key, 0)
                    
                    active_alarm = active_alarms.get(fault_key)

                    if active_alarm is not None:
                        if fault_code != active_alarm['code']:
                            alarm = active_alarms.pop(fault_key)
                            alarm['end_date'] = timestamp
                            alarms.append(alarm)
                    
                    if fault_code != 0 and fault_key not in active_alarms:
                        active_alarms[fault_key] = {
                            'code': fault_code,
                            'description': code_dict.get(fault_code, "Unknown"),
                            'start_date': timestamp,
                            'type': alarm_type
                        }

        if alarms:
            pdf.set_font('helvetica', 'B', 9)
            # Headers
            pdf.cell(20, 10, 'Type', 1, 0, 'C')
            pdf.cell(20, 10, 'Code', 1, 0, 'C')
            pdf.cell(70, 10, 'Description', 1, 0, 'C')
            pdf.cell(40, 10, 'Start Time', 1, 0, 'C')
            pdf.cell(40, 10, 'End Time', 1, 1, 'C')
            pdf.set_font('helvetica', '', 8)

            for alarm in alarms:
                line_height = 5
                # Calculate height of the row based on description
                lines = pdf.multi_cell(70, line_height, alarm['description'], split_only=True)
                row_height = len(lines) * line_height
                if row_height < 10:
                    row_height = 10

                # Check for page break
                if pdf.get_y() + row_height > pdf.page_break_trigger:
                    pdf.add_page()
                    pdf.set_font('helvetica', 'B', 9)
                    pdf.cell(20, 10, 'Type', 1, 0, 'C')
                    pdf.cell(20, 10, 'Code', 1, 0, 'C')
                    pdf.cell(70, 10, 'Description', 1, 0, 'C')
                    pdf.cell(40, 10, 'Start Time', 1, 0, 'C')
                    pdf.cell(40, 10, 'End Time', 1, 1, 'C')
                    pdf.set_font('helvetica', '', 8)

                y_start = pdf.get_y()
                x_start = pdf.get_x()

                pdf.multi_cell(20, row_height, alarm['type'], 1, 'C')
                pdf.set_xy(x_start + 20, y_start)
                
                pdf.multi_cell(20, row_height, str(alarm['code']), 1, 'C')
                pdf.set_xy(x_start + 40, y_start)

                pdf.multi_cell(70, line_height, alarm['description'], 1, 'L')
                pdf.set_xy(x_start + 110, y_start)
                
                start_time_str = alarm['start_date'].strftime('%Y-%m-%d\n%H:%M')
                pdf.multi_cell(40, row_height/2, start_time_str, 1, 'C')
                pdf.set_xy(x_start + 150, y_start)

                end_time_str = alarm['end_date'].strftime('%Y-%m-%d\n%H:%M') if alarm['end_date'] else 'Ongoing'
                pdf.multi_cell(40, row_height/2, end_time_str, 1, 'C')

                pdf.set_y(y_start + row_height)

        else:
            pdf.set_font('helvetica', 'I', 12)
            pdf.cell(0, 10, 'No alarms recorded during this period.', 0, 1, 'C')
        
        pdf.ln(10)

        # --- Penambahan Halaman Checklist ---
       # --- Penambahan Halaman Checklist ---
        pdf.add_page()
        # Header block untuk Checklist
        block_height = 10
        block_width = 60
        pdf.set_fill_color(0, 123, 255) # Blue color
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(block_width, block_height, 'Checklist', 0, 0, 'L', True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(block_height + 5)

        image_path = os.path.join(app.static_folder, 'images', 'floor_layout.png')
        if os.path.exists(image_path):
            image_width = 200
            page_width = pdf.w - pdf.l_margin - pdf.r_margin
            x_centered = pdf.l_margin + (page_width - image_width) / 2
            pdf.image(image_path, x=x_centered, y=pdf.get_y(), w=image_width) # Adjust width as needed
            pdf.ln(85) # Adjust line break after image
        # --- Akhir Penambahan Halaman Checklist ---

        # --- Tambahkan Tabel Checklist seperti di gambar ---
        # Data untuk tabel dari gambar
        checklist_sections = [
            {'title' : 'Spring / Mounting Pad', 'items' : [
                ('Cek Spring Mounting Pad A', 'Baik / Tidak'),
                ('Cek Spring Mounting Pad B', 'Baik / Tidak'),
                ('Cek Spring Mounting Pad C', 'Baik / Tidak'),
                ('Cek Spring Mounting Pad D', 'Baik / Tidak'),
            ]},
            {'title': 'Evaporator', 'items': [
                ('LWT Sensor', ''),
                ('Cek Sensor', 'Baik / Tidak'),
                ('Cek Sensor Well', 'Baik / Tidak'),
                ('Cek Socket Sensor', 'Baik / Tidak'),
                ('RWT Sensor', ''),
                ('Cek Sensor', 'Baik / Tidak'),
                ('Cek Sensor Well', 'Baik / Tidak'),
                ('Cek Socket Sensor', 'Baik / Tidak'),
                ('Inlet Pressure Gauge', ''),
                ('Cek Pressure Gauge', 'Baik / Tidak'),
                ('Cek Pressure Gauge Valve', 'Baik / Tidak'),
                ('Cek Pressure Gauge Pipa', 'Baik / Tidak'),
                ('Outlet Pressure Gauge', ''),
                ('Cek Pressure Gauge', 'Baik / Tidak'),
                ('Cek Pressure Gauge Valve', 'Baik / Tidak'),
                ('Cek Pressure Gauge Pipa', 'Baik / Tidak'),
                ('Flow Switch', ''),
                ('Cek kondisi Flow Switch', 'Baik / Tidak'),
                ('Flow Meter', ''),
                ('Cek Kondisi Flow meter', 'Baik / Tidak'),
                ('Water box', ''),
                ('Cek Kondisi Water Box', 'Baik / Tidak'),
                ('Cek Kanal Gasket', 'Baik / Tidak'),
                ('Cek Kondisi Endsheet', 'Baik / Tidak'),
                ('Evaporator Pressure Transducer', ''),
                ('Cek Kondisi Transducer', 'Baik / Tidak'),
                ('Cek Kondisi Socket Transducer', 'Baik / Tidak'),
                ('Evap Refrigerant Temp Sensor', ''),
                ('Cek Sensor', 'Baik / Tidak'),
                ('Cek Sensor Well', 'Baik / Tidak'),
                ('Cek Socket Sensor', 'Baik / Tidak'),
                ('Sight Glass', ''),
                ('Cek Kondisi Sight Glass', 'Baik / Tidak'),
                ('Cek Kondisi Koneksi Sight Glass', 'Baik / Tidak'),
                ('Evaporator Body', ''),
                ('Cek Kondisi Insulasi', 'Baik / Tidak'),
                ('Cek visual dari kebocoran', 'Baik / Tidak'),
            ]},
            {'title' : 'condenser', 'items' : [
                ('LWT Sensor', ''),
                ('Cek Sensor', 'Baik / Tidak'),
                ('Cek Sensor Well', 'Baik / Tidak'),
                ('Cek Socket Sensor', 'Baik / Tidak'),
                ('RWT Sensor', ''),
                ('Cek Sensor', 'Baik / Tidak'),
                ('Cek Sensor Well', 'Baik / Tidak'),
                ('Cek Socket Sensor', 'Baik / Tidak'),
                ('Inlet Pressure Gauge', ''),
                ('Cek Pressure Gauge', 'Baik / Tidak'),
                ('Cek Pressure Gauge Valve', 'Baik / Tidak'),
                ('Cek Pressure Gauge Pipa', 'Baik / Tidak'),
                ('Outlet Pressure Gauge', ''),
                ('Cek Pressure Gauge', 'Baik / Tidak'),
                ('Cek Pressure Gauge Valve', 'Baik / Tidak'),
                ('Cek Pressure Gauge Pipa', 'Baik / Tidak'),
                ('Flow Switch', ''),
                ('Cek kondisi Flow Switch', 'Baik / Tidak'),
                ('Flow Meter', ''),
                ('Cek Kondisi Flow meter', 'Baik / Tidak'),
                ('Water box', ''),
                ('Cek Kondisi Water Box', 'Baik / Tidak'),
                ('Cek Kanal Gasket', 'Baik / Tidak'),
                ('Cek Kondisi Endsheet', 'Baik / Tidak'),
                ('Condenser Pressure Transducer', ''),
                ('Cek Kondisi Transducer', 'Baik / Tidak'),
                ('Cek Kondisi Socket Transducer', 'Baik / Tidak'),
                ('Condenser drop leg Temp Sensor', ''),
                ('Cek Sensor', 'Baik / Tidak'),
                ('Cek Sensor Well', 'Baik / Tidak'),
                ('Cek Socket Sensor', 'Baik / Tidak'),
                ('Level Refrigerant \xa0Sensor', ''),
                ('Cek Sensor', 'Baik / Tidak'),
                ('Cek Socket Sensor', 'Baik / Tidak'),
                ('Sight Glass', ''),
                ('Cek Kondisi Sight Glass', 'Baik / Tidak'),
                ('Cek Kondisi Koneksi Sight Glass', 'Baik / Tidak'),
                ('Condenser Body', ''),
                ('Cek Kondisi Insulasi', 'Baik / Tidak'),
                ('Cek visual dari kebocoran', 'Baik / Tidak'),
            ]},
            {
                'title': 'Oil System',
                'items': [
                    ('Oil Temperature Sensor', ''),
                    ('Cek Sensor', 'Baik / Tidak'),
                    ('Cek Socket Sensor', 'Baik / Tidak'),
                    ('Cek Sensor', 'Baik / Tidak'),
                    ('Oil Pressure Transducer HOP', ''),
                    ('Cek Kondisi Transducer', 'Baik / Tidak'),
                    ('Cek Kondisi Socket Transducer', 'Baik / Tidak'),
                    ('Oil Pressure Transducer LOP', ''),
                    ('Cek Kondisi Transducer', 'Baik / Tidak'),
                    ('Cek Kondisi Socket Transducer', 'Baik / Tidak'),
                    ('Solenoid Valve', ''),
                    ('Cek Kondisi Solenoid', 'Baik / Tidak'),
                    ('Oil Heater', ''),
                    ('Cek Kondisi Oil Heater', 'Baik / Tidak'),
                    ('Cek Koneksi Oil Heater', 'Baik / Tidak'),
                    ('Oil Filter', ''),
                    ('Cek Kondisi Body Oil Filter', 'Baik / Tidak'),
                    ('Cek Kondisi Valve Oil Filter', 'Baik / Tidak'),
                    ('Cek Kondisi Seal dari kebocoran', 'Baik / Tidak'),
                    ('Sight Glass', ''),
                    ('Cek Kondisi Sight Glass', 'Baik / Tidak'),
                    ('Cek Kondisi Koneksi Sight Glass', 'Baik / Tidak'),
                    ('Oil Sump', ''),
                    ('Cek Kondisi Oil Sump', 'Baik / Tidak'),
                    ('Cek Tutup Oil Sump dari kebocoran', 'Baik / Tidak'),
                    ('Oil Piping', ''),
                    ('Cek Kondisi Oil Piping', 'Baik / Tidak'),
                    ('Cek Oil piping dari kebocoran', 'Baik / Tidak'),
                    ('Oil Cooler', ''),
                    ('Cek TXV Oil Cooler', 'Baik / Tidak'),
                    ('Cek Oil Cooler', 'Baik / Tidak'),
                    ('Cek Oil Cooler Piping', 'Baik / Tidak'),
                    ('VSOP', ''),
                    ('Cek VSOP body', 'Baik / Tidak'),
                    ('Cek VSOP board', 'Baik / Tidak'),
                ]
            },
            {
                'title': 'Compressor',
                'items': [
                    ('Cek Compressor Body', 'Baik / Tidak'),
                    ('Cek Pipa Discharge', 'Baik / Tidak'),
                    ('Cek Pipa Suction', 'Baik / Tidak'),
                    ('Proximity Sensor', ''),
                    ('Cek Sensor', 'Baik / Tidak'),
                    ('Cek Socket Sensor', 'Baik / Tidak'),
                    ('PRV Actuator', ''),
                    ('Cek Kondisi Body PRV Actuator', 'Baik / Tidak'),
                    ('Cek Kondisi Lever PRV', 'Baik / Tidak'),
                    ('Shaft Seal', ''),
                    ('Cek Kondisi Penampungan Oli Shaft Seal', '0 - 100%'),
                    ('HPCO', ''),
                    ('Cek Kondisi HPCO', 'Baik / Tidak'),
                    ('Motor', ''),
                    ('Motor Body', ''),
                ]
            },
            {
                'title': 'Matering Device',
                'items': [
                    ('Orifice', ''),
                    ('Cek Kondisi Actuator Orrifice', 'Baik / Tidak'),
                    ('Cek Body Orrifice', 'Baik / Tidak'),
                    ('Charging Valve', ''),
                    ('Cek Kondisi Charging Valve', 'Baik / Tidak'),
                    ('Cek kebocoran Charging Valve', 'Baik / Tidak'),
                    ('Pemipaan', ''),
                    ('Cek Kondisi Pipa', 'Baik / Tidak'),
                ]
            },
            {
                'title': 'Control Center',
                'items': [
                    ('Cek Kondisi Body Panel', 'Baik / Tidak'),
                    ('Cek Kondisi Keypad', 'Baik / Tidak'),
                    ('Cek Kondisi Display', 'Baik / Tidak'),
                    ('Cek Kondisi Rocker Switch', 'Baik / Tidak'),
                    ('Cek Kondisi Microboard', 'Baik / Tidak'),
                    ('Cek Kondisi CM2', 'Baik / Tidak'),
                    ('Cek Kondisi IO Board', 'Baik / Tidak'),
                    ('Cek Kondisi Kabel', 'Baik / Tidak'),
                    ('Cek Kondisi Trafo', 'Baik / Tidak'),
                    ('Cek Kondisi Fuse', 'Baik / Tidak'),
                    ('Thermographic', 'Baik / Tidak'),
                ]
            },
            {
                'title': 'Panel Starter',
                'items': [
                    ('Cek Kondisi Kontaktor', 'Baik / Tidak'),
                    ('Cek Kondisi timer', 'Baik / Tidak'),
                    ('Cek kondisi Kabel', 'Baik / Tidak'),
                    ('Cek kondisi Kabel Power', 'Baik / Tidak'),
                    ('Cek Kondisi Trafo', 'Baik / Tidak'),
                    ('Cek Kondisi Panel', 'Baik / Tidak'),
                    ('Thermographic', 'Baik / Tidak'),
                ]
            }
        ]

        def to_roman(n):
            """Converts an integer to a Roman numeral."""
            if n > 3999: return str(n)
            thousands = ["", "M", "MM", "MMM"]
            hundreds = ["", "C", "CC", "CCC", "CD", "D", "DC", "DCC", "DCCC", "CM"]
            tens = ["", "X", "XX", "XXX", "XL", "L", "LX", "LXX", "LXXX", "XC"]
            ones = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
            return (thousands[n // 1000] + hundreds[n % 1000 // 100] +
                    tens[n % 100 // 10] + ones[n % 10])

        row_height = 8
        header_widths = [10, 60, 40, 40, 40]
        header_texts = ['NO', 'Description', 'Range', 'Remarks', 'Note']
        no_counter = 1

        pdf.set_font('helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(255, 255, 255)

        for section in checklist_sections:
            # Logic to force a new page for the Compressor section and add image spacing
            if section['title'] == 'Compressor':
                pdf.add_page()
                image_path_compressor = os.path.join(app.static_folder, 'images', 'compressor.png')
                if os.path.exists(image_path_compressor):
                    # Set image height to avoid overlap and provide sufficient space
                    image_height = 150
                    image_width = 150
                    page_width = pdf.w - pdf.l_margin - pdf.r_margin
                    x_centered = pdf.l_margin + (page_width - image_width) / 2
                    pdf.image(image_path_compressor, x=x_centered, y=pdf.get_y(), w=image_width, h=image_height)
                    # Add a line break to ensure the table starts below the image
                    pdf.ln(image_height + 1)
            else:
                # Add a break before each new table for other sections
                pdf.ln(10)

            # Header tabel
            pdf.set_font('helvetica', 'B', 12)
            pdf.set_fill_color(0, 123, 255)
            pdf.set_text_color(255, 255, 255)
            for i, header_text in enumerate(header_texts):
                pdf.cell(header_widths[i], 10, header_text, 1, 0, 'C', True)
            pdf.ln()
            pdf.set_font('helvetica', 'B', 10)
            pdf.set_text_color(0, 0, 0)

            # Print the main section row
            pdf.cell(header_widths[0], row_height, to_roman(no_counter), 1, 0, 'C')
            pdf.cell(header_widths[1], row_height, section['title'], 1, 0, 'L')
            pdf.cell(header_widths[2] + header_widths[3] + header_widths[4], row_height, '', 1, 1, 'L')
            pdf.set_font('helvetica', '', 10)

            # Print the sub-items
            for i, (description, range_val) in enumerate(section['items']):
                # Check for page break
                if pdf.get_y() + row_height > pdf.page_break_trigger:
                    pdf.add_page()
                    # Draw 'Checklist' header on new page
                    pdf.set_fill_color(0, 123, 255)
                    pdf.set_font('helvetica', 'B', 16)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(block_width, block_height, 'Checklist', 0, 0, 'L', True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(block_height + 5)
                    
                    # Re-print table header on new page
                    pdf.set_font('helvetica', 'B', 12)
                    pdf.set_fill_color(0, 123, 255)
                    pdf.set_text_color(255, 255, 255)
                    for h_i, h_text in enumerate(header_texts):
                        pdf.cell(header_widths[h_i], 10, h_text, 1, 0, 'C', True)
                    pdf.ln()
                    pdf.set_font('helvetica', '', 10)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_fill_color(255, 255, 255)

                # Use bold font for sub-headers like "LWT Sensor"
                if range_val == '':
                    pdf.set_font('helvetica', 'B', 10)
                    pdf.set_fill_color(240, 240, 240)
                else:
                    pdf.set_font('helvetica', '', 10)
                    pdf.set_fill_color(255, 255, 255)

                pdf.cell(header_widths[0], row_height, '', 1, 0, 'C', True)
                pdf.cell(header_widths[1], row_height, description, 1, 0, 'L', True)
                pdf.cell(header_widths[2], row_height, range_val, 1, 0, 'C', True)
                pdf.cell(header_widths[3], row_height, '', 1, 0, 'C', True)
                pdf.cell(header_widths[4], row_height, '', 1, 1, 'C', True)

            # Logic to only add Recommendation for the first section and fill the rest of the page
            if section['title'] == 'Spring / Mounting Pad':
                # Add Recommendation row
                pdf.ln(2) # Small space
                pdf.set_font('helvetica', 'B', 10)
                pdf.cell(header_widths[0] + header_widths[1], row_height, 'Recommendation:', 1, 0, 'L')
                pdf.cell(header_widths[2] + header_widths[3] + header_widths[4], row_height, '', 1, 1, 'C')

                # Calculate remaining space and fill with empty rows
                # 1. Height of the Recommendation row
                current_y_rec = pdf.get_y()
                # 2. Page bottom margin
                bottom_margin = pdf.h - pdf.b_margin
                # 3. Available height
                available_height = bottom_margin - current_y_rec
                
                num_fill_rows = int(available_height / row_height)
                
                for _ in range(num_fill_rows):
                    pdf.cell(header_widths[0] + header_widths[1], row_height, '', 1, 0, 'L')
                    pdf.cell(header_widths[2] + header_widths[3] + header_widths[4], row_height, '', 1, 1, 'C')

            # Add a final space after each table
            pdf.ln(5)

            no_counter += 1

        # --- Akhir Tabel Checklist ---
        
        
        #----Awal Tabel Semi Annually----
        pdf.add_page()
        
        
        #----Akhir tabel Semi Annually--
        
        

        pdf_output = pdf.output(dest='S').encode('latin-1')
        return Response(pdf_output, mimetype='application/pdf', headers={'Content-Disposition': f'inline; filename=report_{chiller_id}_{start_date.strftime("%Y%m%d")}.pdf'})

    except Exception as e:
        import traceback
        print(f"An error occurred during PDF generation for chiller {chiller_id}:")
        traceback.print_exc()
        flash(f"Gagal membuat laporan PDF karena kesalahan internal: {e}", "danger")
        return redirect(url_for('test', chiller_id=chiller_id))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
