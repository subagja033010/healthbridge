# HealthBridge AI - Manual Guide

## Panduan Instalasi dan Penggunaan

---

## 📋 Daftar Isi

1. [Persyaratan Sistem](#1-persyaratan-sistem)
2. [Instalasi Local Development](#2-instalasi-local-development)
3. [Instalasi dengan Docker](#3-instalasi-dengan-docker)
4. [Konfigurasi Environment](#4-konfigurasi-environment)
5. [Panduan Penggunaan](#5-panduan-penggunaan)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Persyaratan Sistem

### Software Requirements

| Software | Versi Minimum | Keterangan |
|----------|---------------|------------|
| Node.js | 18.x | Untuk frontend |
| Python | 3.9+ | Untuk backend |
| Docker | 20.x | Opsional |
| Git | 2.x | Version control |

### Hardware Requirements

| Komponen | Minimum | Rekomendasi |
|----------|---------|-------------|
| RAM | 4 GB | 8 GB |
| Storage | 2 GB | 5 GB |
| CPU | 2 Core | 4 Core |

---

## 2. Instalasi Local Development

### Step 1: Clone Repository

```bash
git clone https://github.com/username/healthbridge.git
cd healthbridge
```

### Step 2: Setup Backend

```bash
# Masuk ke folder backend
cd healthbridge-backend-main

# Buat virtual environment (recommended)
python -m venv venv

# Aktivasi virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Buat file .env dari template
copy .env.example .env
# Linux: cp .env.example .env

# Edit .env dengan kredensial Anda
notepad .env

# Jalankan backend
uvicorn main:app --reload
```

Backend berjalan di: **http://127.0.0.1:8000**

### Step 3: Setup Frontend

```bash
# Buka terminal baru
cd healthbridge-frontend-main

# Install dependencies
npm install

# Jalankan frontend
npm run dev
```

Frontend berjalan di: **http://localhost:5173**

### Step 4: Akses Aplikasi

1. Buka browser
2. Navigasi ke **http://localhost:5173**
3. Aplikasi siap digunakan!

---

## 3. Instalasi dengan Docker

### Step 1: Build dengan Docker Compose

```bash
# Di folder root project
docker-compose up -d
```

### Step 2: Akses Aplikasi

- Frontend: **http://localhost:3000**
- Backend: **http://localhost:8000**

### Docker Commands

```bash
# Lihat container running
docker ps

# Lihat logs
docker-compose logs -f

# Stop containers
docker-compose down

# Rebuild images
docker-compose build --no-cache
docker-compose up -d
```

---

## 4. Konfigurasi Environment

### Backend Environment (.env)

Buat file `.env` di folder `healthbridge-backend-main`:

```env
# JWT Authentication
SECRET_KEY=your-super-secret-key-change-this

# Google Gemini AI API
GEMINI_API_KEY=your_gemini_api_key

# Database (default SQLite, atau PostgreSQL untuk production)
DATABASE_URL=sqlite:///./healthbridge.db
# DATABASE_URL=postgresql://user:pass@host:5432/healthbridge

# AWS S3 (opsional)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=healthbridge-storage
```

### Cara Mendapatkan API Keys

#### Google Gemini API
1. Buka https://aistudio.google.com/app/apikey
2. Login dengan akun Google
3. Klik "Create API Key"
4. Copy API key ke file `.env`

#### AWS S3
1. Buka AWS Console → IAM → Users
2. Buat user baru dengan akses S3
3. Download credentials (Access Key ID & Secret)
4. Buat S3 bucket
5. Copy credentials ke file `.env`

---

## 5. Panduan Penggunaan

### A. Untuk User

#### Register & Login
1. Klik **"Daftar"** di navbar
2. Isi form: Nama, Email, Password
3. Klik **"Masuk"** untuk login

#### Konsultasi AI
1. Klik **"Konsultasi Sekarang"**
2. Masukkan nama dan keluhan
3. Pilih referensi penyakit (opsional)
4. Klik **"Cek Diagnosa"**
5. Lihat hasil diagnosa dan rekomendasi obat

#### Beli Obat
1. Klik **"Toko Obat"**
2. Cari atau pilih kategori obat
3. Klik **"Beli"** pada obat
4. Lihat detail dan tambah ke keranjang
5. Klik icon 🛒 untuk checkout
6. Isi data pengiriman
7. Konfirmasi pesanan

#### Cek Status Pesanan
1. Klik **"📋 Pesanan"** di navbar
2. Masukkan nomor telepon
3. Lihat status pesanan:
   - ⏳ Menunggu (kuning)
   - 🔄 Diproses (biru)
   - 🚚 Dikirim (ungu)
   - ✅ Sampai (hijau)
   - ❌ Dibatalkan (merah)

---

### B. Untuk Admin

#### Login Admin
- Email: `admin@healthbridge.com`
- Password: `admin123`

#### Dashboard
- Statistik: Total users, orders, revenue
- Pesanan terbaru

#### Kelola Pesanan
1. Klik **"📦 Pesanan"** di sidebar
2. Ubah status via dropdown

#### Kelola Produk
1. Klik **"💊 Produk"** di sidebar
2. Gambar produk ditampilkan di tabel
3. Klik **"+ Tambah Produk"** untuk produk baru
4. Isi nama produk **SEBELUM** upload gambar (auto-rename)
5. Upload gambar atau pilih dari galeri

#### Kelola Pengguna
1. Klik **"👥 Pengguna"** di sidebar
2. Lihat daftar semua user

---

## 6. Troubleshooting

### Error: PowerShell Execution Policy

```powershell
# Jalankan PowerShell sebagai Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Error: Port Already in Use

```bash
# Windows - Cari proses
netstat -ano | findstr :8000
# Kill proses
taskkill /PID <PID> /F
```

### Error: Module Not Found (Python)

```bash
pip install -r requirements.txt
```

### Error: npm ERR!

```bash
# Hapus node_modules
rm -rf node_modules
npm install
```

### Error: Database Connection

```bash
# Pastikan DATABASE_URL benar di .env
# Untuk SQLite, pastikan folder writable
# Untuk PostgreSQL, cek koneksi dan credentials
```

### Error: CORS

1. Pastikan backend berjalan di port 8000
2. Frontend mengakses `http://127.0.0.1:8000`
3. Jika deploy, tambahkan frontend URL ke CORS origins di `main.py`

### Error: Gambar Tidak Muncul

1. Pastikan folder `static/images/` ada dan writable
2. Cek image_url di database tidak null
3. Untuk produk baru, upload gambar via admin panel

---

## 📞 Kontak & Support

Jika menemukan masalah:
1. Cek dokumentasi ini
2. Lihat error di console browser (F12)
3. Lihat log terminal backend/frontend
4. Lihat `docker logs` jika menggunakan Docker

---

*HealthBridge AI - Sistem Konsultasi Kesehatan dan E-Commerce Obat*
