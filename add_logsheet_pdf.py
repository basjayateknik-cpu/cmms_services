import os

file_path = r"d:\github\22-06-2026\cmms\app.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_content = """    @app.route('/dashboard/logsheet/<int:id>', methods=['GET'])
    @login_required
    def logsheet_detail(id):"""

new_content = """    @app.route('/dashboard/logsheet/<int:id>/export_pdf', methods=['GET'])
    @login_required
    def logsheet_export_pdf(id):
        \"\"\"Export logsheet to PDF\"\"\"
        import os
        from fpdf import FPDF
        from models import Logsheet
        from datetime import datetime
        from flask import make_response, current_app, redirect, flash, url_for

        logsheet = Logsheet.query.get_or_404(id)
        
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # --- 0. COVER PAGE ---
        pdf.add_page()
        
        # Background Image
        title_image_path = os.path.join(current_app.root_path, 'static', 'images', 'judul.png')
        if os.path.exists(title_image_path):
            pdf.image(title_image_path, x=0, y=0, w=pdf.w, h=pdf.h)
        
        # Get Site Name and Period
        site_name = logsheet.site.name if logsheet.site else "Unknown Site"
        ls_date = logsheet.date or datetime.now()
        month_map = {
            1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL", 5: "MEI", 6: "JUNI",
            7: "JULI", 8: "AGUSTUS", 9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DESEMBER"
        }
        
        line1 = f"LAPORAN LOGSHEET"
        line1_sub = "MAINTENANCE"
        line2 = f"{site_name.upper()}"
        line3 = f"{logsheet.asset.name.upper() if logsheet.asset else ''}"
        line4 = f"{logsheet.code}"
        
        # Positioning text at bottom left
        pdf.set_y(-105)
        pdf.set_left_margin(20)
        
        pdf.set_font('helvetica', 'B', 24)
        pdf.cell(0, 12, line1, 0, 1, 'L')
        pdf.set_font('helvetica', 'B', 24)
        pdf.cell(0, 12, line1_sub, 0, 1, 'L')
        
        pdf.set_font('helvetica', 'B', 18)
        pdf.cell(0, 10, line2, 0, 1, 'L')
        
        pdf.set_font('helvetica', 'B', 18)
        pdf.cell(0, 10, line3, 0, 1, 'L')
        
        pdf.set_font('helvetica', 'B', 18)
        pdf.cell(0, 10, line4, 0, 1, 'L')
        
        # Reset for main report
        pdf.set_left_margin(10)
        pdf.add_page()
        # --- END COVER PAGE ---
        
        try:
            pdf.set_font("helvetica", style="B", size=10)
        except:
            pdf.set_font("Arial", style="B", size=10)
            
        start_x = pdf.get_x()
        start_y = pdf.get_y()
        
        # 1. NEW HEADER
        pdf.cell(35, 24, "", border=1) # Logo area box
        
        logo_path = os.path.join(current_app.root_path, 'static', 'images', 'Logo Jaya Teknik.png')
        if os.path.exists(logo_path):
            try:
                pdf.image(logo_path, x=start_x + 2, y=start_y + 2, w=31)
            except:
                pass
        
        # Title
        pdf.set_font("helvetica", style="B", size=14)
        pdf.set_xy(start_x + 35, start_y)
        pdf.cell(105, 24, "", border=1)
       
        pdf.set_xy(start_x + 35, start_y + 12)
        pdf.cell(105, 8, "REPORT LOGSHEET", align="C")
        
        # Info box right
        pdf.set_font("helvetica", size=8)
        pdf.set_xy(start_x + 140, start_y)
        pdf.cell(20, 6, "No.Dok", border=1)
        pdf.cell(30, 6, "RP - JT - 26", border=1)
        
        pdf.set_xy(start_x + 140, start_y + 6)
        pdf.cell(20, 6, "Ref.", border=1)
        pdf.cell(30, 6, "7; 7.1.3 & 7.1.4", border=1)
        
        pdf.set_xy(start_x + 140, start_y + 12)
        pdf.cell(20, 6, "Rev.", border=1)
        pdf.cell(30, 6, "Original", border=1)
        
        pdf.set_xy(start_x + 140, start_y + 18)
        pdf.cell(20, 6, "Tanggal", border=1)
        printed_date = datetime.now().strftime("%d %b %Y")
        pdf.cell(30, 6, printed_date, border=1)
        
        # Details Body
        pdf.set_xy(start_x, start_y + 24)
        pdf.set_font("helvetica", size=9)
        pdf.cell(190, 24, "", border=1)
        pdf.set_xy(start_x, start_y + 24)
        
        def fmt_dt(dt):
            if not dt: return '-'
            if isinstance(dt, datetime): return dt.strftime('%d-%m-%Y %H:%M')
            return dt.strftime('%d-%m-%Y')
            
        nomor_val = logsheet.code or '-'
        asset_val = f"{logsheet.asset.name} ({logsheet.asset.code})" if logsheet.asset else '-'
        resp_val = logsheet.filled_by.name if logsheet.filled_by else "N/A"
        
        proj_val = (logsheet.asset.project_code if logsheet.asset and logsheet.asset.project_code else "-") or '-'
        
        loc_val = '-'
        if logsheet.asset and hasattr(logsheet.asset, 'location') and logsheet.asset.location:
            loc_val = logsheet.asset.location.name if hasattr(logsheet.asset.location, 'name') else str(logsheet.asset.location)
        
        act_val = fmt_dt(logsheet.date)
        shift_val = logsheet.shift or '-'
        
        # Line 1
        pdf.cell(20, 6, "Form", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, "LOGSHEET", border=0)
        pdf.cell(20, 6, "Project", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(proj_val)[:35], border=0, ln=1)
        
        # Line 2
        pdf.cell(20, 6, "Nomor", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(nomor_val)[:35], border=0)
        pdf.cell(20, 6, "Location", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(loc_val)[:35], border=0, ln=1)
        
        # Line 3
        pdf.cell(20, 6, "Asset", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(asset_val)[:35], border=0)
        pdf.cell(20, 6, "Shift", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(shift_val)[:40], border=0, ln=1)
        
        # Line 4
        pdf.cell(20, 6, "Responsible", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(resp_val)[:35], border=0)
        pdf.cell(20, 6, "Date", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(act_val)[:40], border=0, ln=1)
        
        pdf.ln(5)
        
        # 1.5 TECHNICIAN
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("helvetica", style="B", size=10)
        pdf.cell(190, 6, "TECHNICIAN", border=1, align="C", fill=True, ln=1)
        pdf.cell(190, 6, "Name", border=1, align="C", fill=True, ln=1)
        pdf.set_font("helvetica", size=9)
        pdf.cell(190, 6, str(resp_val), border=1, align="L", ln=1)
        pdf.ln(5)
        
        # 2. CHECKING REPORT
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("helvetica", style="B", size=10)
        pdf.cell(190, 6, "CHECKING REPORT", border=1, align="C", fill=True, ln=1)
        
        pdf.set_font("helvetica", style="B", size=8)
        pdf.cell(75, 8, "Description (Unit Check)", border=1, align="C", fill=True)
        pdf.cell(25, 8, "Standard", border=1, align="C", fill=True)
        pdf.cell(25, 8, "Actual", border=1, align="C", fill=True)
        pdf.cell(25, 8, "Check", border=1, align="C", fill=True)
        pdf.cell(40, 8, "Note", border=1, align="C", fill=True, ln=1)
        
        pdf.set_font("helvetica", size=8)
        for entry in logsheet.entries:
            desc = (entry.parameter_name[:40] + '...') if entry.parameter_name and len(entry.parameter_name) > 42 else (entry.parameter_name or entry.description or '-')
            pdf.cell(75, 6, str(desc), border=1)
            
            std_val = "-"
            if entry.standard_min is not None and entry.standard_max is not None:
                std_val = f"{entry.standard_min} - {entry.standard_max}"
            elif entry.standard_min is not None:
                std_val = f">= {entry.standard_min}"
            elif entry.standard_max is not None:
                std_val = f"<= {entry.standard_max}"
                
            pdf.cell(25, 6, str(std_val)[:15], border=1, align="C")
            
            actual_val = str(entry.value) if entry.value else "-"
            pdf.cell(25, 6, actual_val[:15], border=1, align="C")
            
            check_val = "OK"
            if entry.entry_type == 'task' or entry.entry_type == 'observation':
                check_val = "v" if entry.is_completed else "-"
            elif actual_val != "-":
                check_val = "v"
            else:
                check_val = "-"
                
            pdf.cell(25, 6, "OK" if check_val == "v" else "-", border=1, align="C")
            
            note_val = str(entry.description) if entry.description and entry.entry_type != 'task' else ""
            pdf.cell(40, 6, note_val[:20], border=1, ln=1)
        
        pdf.ln(5)
        
        # 3. WORK LOGS / ACTIVITY (Notes in Logsheet)
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("helvetica", style="B", size=10)
        pdf.cell(190, 6, "NOTES", border=1, align="C", fill=True, ln=1)
        pdf.set_font("helvetica", size=8)
        if not logsheet.notes:
            pdf.cell(190, 6, "No notes recorded.", border=1, align="C", ln=1)
        else:
            pdf.multi_cell(190, 6, logsheet.notes, border=1)
                
        pdf.ln(5)
        
        # 3.6 SIGNATURES
        pdf.ln(5)
        
        first_tech = logsheet.filled_by
        tech_name = first_tech.name if first_tech else "....."
        tech_role = first_tech.role if first_tech else "....."
        site_name = logsheet.site.name.upper() if logsheet.site else "....."
        
        if pdf.get_y() > 240:
            pdf.add_page()
            
        sig_y = pdf.get_y()
        
        c_name_print = "....."
        c_title_print = "....."
        
        # Right Column (Pihak Kedua)
        pdf.set_xy(110, sig_y)
        pdf.set_font("helvetica", style="B", size=9)
        pdf.cell(85, 5, "PELAKSANA,", ln=1)
        pdf.set_x(110)
        pdf.cell(85, 5, "PT JAYA TEKNIK INDONESIA", ln=1)
        
        # Add technician signature if exists in LogsheetSignature
        import tempfile
        import base64
        def save_temp_image(b64_str):
            if not b64_str or ',' not in b64_str: return None
            try:
                _, encoded = b64_str.split(",", 1)
                data = base64.b64decode(encoded)
                fd, temp_path = tempfile.mkstemp(suffix='.png')
                with os.fdopen(fd, 'wb') as f:
                    f.write(data)
                return temp_path
            except:
                return None

        # Operator Signature
        op_sig = next((s for s in logsheet.signatures if s.signature_type == 'operator'), None)
        if op_sig and op_sig.signature_data:
            t_img_path = save_temp_image(op_sig.signature_data)
            if t_img_path:
                try:
                    pdf.image(t_img_path, x=110, y=sig_y + 10, h=14)
                    os.remove(t_img_path)
                except: pass
                if op_sig.signed_name:
                    tech_name = op_sig.signed_name

        pdf.set_xy(110, sig_y + 25)
        pdf.set_font("helvetica", size=9)
        pdf.cell(85, 5, f"Nama : {tech_name}", ln=1)
        pdf.set_x(110)
        pdf.cell(85, 5, f"Jabatan : {tech_role}", ln=1)
        
        # Left Column (Pihak Pertama)
        pdf.set_xy(15, sig_y)
        pdf.set_font("helvetica", style="B", size=9)
        pdf.cell(90, 5, "DIKETAHUI OLEH,", ln=1)
        pdf.set_x(15)
        pdf.cell(90, 5, site_name, ln=1)
        
        sup_sig = next((s for s in logsheet.signatures if s.signature_type == 'supervisor'), None)
        if sup_sig and sup_sig.signature_data:
            c_img_path = save_temp_image(sup_sig.signature_data)
            if c_img_path:
                try:
                    pdf.image(c_img_path, x=15, y=sig_y + 10, h=14)
                    os.remove(c_img_path)
                except: pass
                if sup_sig.signed_name:
                    c_name_print = sup_sig.signed_name

        pdf.set_xy(15, sig_y + 25)
        pdf.set_font("helvetica", size=9)
        pdf.cell(90, 5, f"Nama : {c_name_print}", ln=1)
        pdf.set_x(15)
        pdf.cell(90, 5, f"Jabatan : {c_title_print}", ln=1)
        
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=logsheet_{logsheet.code}.pdf'
        return response

    @app.route('/dashboard/logsheet/<int:id>', methods=['GET'])
    @login_required
    def logsheet_detail(id):"""

content = content.replace(target_content, new_content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied to app.py")
