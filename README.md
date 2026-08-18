# CMMS (Computerized Maintenance Management System) Application

## 📖 Deskripsi Proyek
Sistem Manajemen Pemeliharaan Terkomputerisasi (CMMS) berbasis web komprehensif yang dibangun menggunakan **Python Flask**. Sistem ini didesain secara khusus untuk mengatur, melacak, dan merencanakan seluruh kegiatan operasional fasilitas (Facility Management). Mulai dari pendataan aset, pengelolaan tiket perbaikan (*helpdesk*), penjadwalan pemeliharaan preventif, hingga pemantauan mesin (*IoT Chiller Monitoring*).

---

## 🚀 Fitur Utama & Modul (Modules)

Aplikasi ini dibagi menjadi beberapa modul yang saling terintegrasi:

1. **Dashboard & Laporan (`reports.py`, `pdf.py`)** 
   - Pantauan umum kondisi operasional.
   - Ekspor dan pembuatan laporan (PDF/Excel) secara sistematis.
2. **Manajemen Aset (`assets.py`, `models.py`)** 
   - Pendataan dan pelacakan seluruh aset mesin/properti beserta *barcode* atau *QR code*.
3. **Surat Perintah Kerja / Work Orders (`work_orders.py`, `schedule.py`)**
   - Pembuatan tiket kerja otomatis dan manual.
   - Penjadwalan pemeliharaan preventif secara rutin (Preventive Maintenance).
4. **Inventaris Suku Cadang (`supplies.py`)**
   - Manajemen material, pelacakan stok masuk/keluar untuk operasional pemeliharaan.
5. **Pembelian / Purchasing (`purchasing.py`)**
   - Proses pembuatan *Purchase Request* (PR) dan *Purchase Order* (PO).
6. **Layanan Bantuan / Helpdesk (`helpdesk.py`)**
   - Portal untuk menerima pelaporan masalah/kendal dari departemen/pengguna luar ke tim teknisi.
7. **IoT & Monitoring Teknis (`chiller_monitoring.py`, `mqtt_client.py`)**
   - Pemantauan metrik *Chiller* dan parameter teknik lainnya secara *real-time* via protokol MQTT.
8. **Keamanan & Konfigurasi (`auth.py`, `settings.py`)**
   - Pengaturan hak akses (Administrator, Technician, User), serta manajemen properti gedung.

---

## ⚙️ Persyaratan Sistem (Prerequisites)

- Python 3.10+
- OS: Windows / Linux / macOS
- Docker & Docker Compose (Opsional tapi ***Sangat Direkomendasikan***)

---

## 🛠️ Cara Instalasi & Menjalankan (Deployment)

Anda memiliki dua pilihan untuk menjalankan aplikasi ini. Pilihan menggunakan **Docker** lebih disarankan agar mudah saat ingin ditransfer antar-server tanpa harus bermasalah di perbedaan versi *library* (*Dependency Hell*).

### Pilihan 1: Menggunakan Docker (Rekomendasi!)
1. Pastikan Docker Desktop sudah menyala di sistem Anda.
2. Buka Terminal (atau CMD/PowerShell), arahkan ke folder proyek ini.
3. Ketik perintah berikut dan tunggu hingga selesai (`build image`):
   ```bash
   docker-compose up -d --build
   ```
4. Buka *browser* pilihan Anda dan pergi ke `http://localhost:5000` (atau IP server port `5000`).

> **Catatan Docker:** Dataabase `cmms.db` yang ada akan dipertahankan datanya selama *container* disetel dengan konfigurasi `volumes` yang ada dalam `docker-compose.yml`.

### Pilihan 2: Cara Manual (Local Virtual Environment)
1. Buka Terminal, arahkan (cd) ke folder ini.
2. Buat lingkungan virtual khusus (VENV) agar saling terisolasi dengan App lain:
   ```bash
   python -m venv venv
   ```
3. Aktifkan Virtual Environment tersebut:
   - **Windows:** `venv\Scripts\activate`
   - **Linux/Mac:** `source venv/bin/activate`
4. Instal semua ekstensi Python yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```
5. Terakhir, jalankan server *development*:
   ```bash
   flask run
   ```
   Server Flask akan menyala di `http://127.0.0.1:5000`.

---

## 🗄️ Struktur Basis Data (Database)
Aplikasi ini secara seragap (default) menggunakan manajemen **SQLite** (terekam pada file `cmms.db`) karena ringan dan bersifat portabel. Seluruh interaksi tabel dikontrol melalui **Flask-SQLAlchemy** (bisa merujuk pada `models.py`).

Skema utama termasuk: `User`, `Asset`, `WorkOrder`, `Supplies`, dan `HelpdeskTicket`.

---

## 👨‍💻 Kontributor / Pengembang
Sistem dibangun oleh Irvan Nurfauzan Saputra. Jika ada gangguan atau ingin melakukan pembaruan kode, Anda bisa menyesuaikannya melalui file Python terkait dan jangan lupa lakukan pembaruan *container* dengan `docker-compose up -d --build`.
