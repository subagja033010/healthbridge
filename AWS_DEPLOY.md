# HealthBridge AI - AWS Deployment Guide

Panduan lengkap deploy HealthBridge ke AWS dengan **2 EC2 instances** + **RDS PostgreSQL** + **Cloudflare CDN**.

**Domain**: `healthbridge.my.id`

---

## 📋 Prerequisites

Sebelum memulai, pastikan Anda memiliki:
- ✅ AWS Account aktif
- ✅ Domain: `healthbridge.my.id`
- ✅ Akun Cloudflare (gratis)
- ✅ Repository GitHub sudah di-clone

---

## 🏗️ Architecture Overview

```mermaid
flowchart TB
    subgraph Internet
        User["👤 User"]
    end

    subgraph Cloudflare["Cloudflare"]
        CF["🌐 Cloudflare CDN<br/>healthbridge.my.id"]
    end

    subgraph AWS["AWS Cloud"]
        subgraph VPC["VPC 10.0.0.0/16"]
            subgraph PublicSubnet1["Public Subnet 1<br/>10.0.1.0/24"]
                EC2_FE["🖥️ EC2 Frontend<br/>Nginx + React<br/>Port 80"]
                EC2_BE["🖥️ EC2 Backend<br/>FastAPI<br/>Port 8000"]
            end
            
            subgraph PublicSubnet2["Public Subnet 2<br/>10.0.2.0/24"]
                RDS["🗄️ RDS PostgreSQL<br/>Port 5432"]
            end
        end

        S3["📦 S3 Bucket<br/>Product Images"]
    end

    User --> CF --> EC2_FE --> EC2_BE
    EC2_BE --> RDS
    EC2_BE --> S3
```

### Komponen:
| Komponen | Lokasi | Fungsi |
|----------|--------|--------|
| Cloudflare | CDN | SSL, Cache, DDoS Protection |
| Frontend EC2 | Public Subnet 1 | Serve React app via Nginx |
| Backend EC2 | Public Subnet 1 | FastAPI API Server |
| RDS PostgreSQL | Public Subnet 2 | Database (production) |
| S3 Bucket | AWS S3 | Penyimpanan gambar (production) |

### Catatan Storage:
- **Development**: SQLite + `static/images/` (lokal)
- **Production**: PostgreSQL (RDS) + S3 Bucket (cloud)

---

## ⚠️ File yang TIDAK Ada di GitHub

Setelah clone, Anda harus **membuat/install sendiri**:

| File/Folder | Cara Mendapatkan |
|-------------|------------------|
| `node_modules/` | `npm install` |
| `.env` | Buat dari `.env.example` |
| `healthbridge.db` | Otomatis (SQLite) atau gunakan RDS |
| `static/images/` | `mkdir -p static/images` |
| `venv/` | `python -m venv venv` |

---

# TAHAP 1: Buat VPC

## 1.1 Buka AWS Console
1. Buka browser → https://console.aws.amazon.com
2. Login dengan akun AWS Anda
3. Pastikan region: **Asia Pacific (Singapore) ap-southeast-1**

## 1.2 Buat VPC Baru
1. Ketik **VPC** di search bar → Klik **VPC**
2. Klik **Create VPC**
3. Isi form:
   ```
   Name tag: healthbridge-vpc
   IPv4 CIDR block: 10.0.0.0/16
   ```
4. Klik **Create VPC**

## 1.3 Buat Subnet 1 (untuk EC2)
1. Klik **Subnets** → **Create subnet**
2. Isi form:
   ```
   VPC ID: healthbridge-vpc
   Subnet name: healthbridge-public-subnet-1
   Availability Zone: ap-southeast-1a
   IPv4 CIDR block: 10.0.1.0/24
   ```
3. Klik **Create subnet**

## 1.4 Buat Subnet 2 (untuk RDS)
1. Klik **Create subnet** lagi
2. Isi form:
   ```
   VPC ID: healthbridge-vpc
   Subnet name: healthbridge-public-subnet-2
   Availability Zone: ap-southeast-1b
   IPv4 CIDR block: 10.0.2.0/24
   ```
3. Klik **Create subnet**

## 1.5 Buat Internet Gateway
1. Klik **Internet Gateways** → **Create internet gateway**
2. Name: `healthbridge-igw`
3. Klik **Create**
4. Klik **Actions** → **Attach to VPC** → Pilih `healthbridge-vpc`

## 1.6 Konfigurasi Route Table
1. Klik **Route Tables** → Pilih route table `healthbridge-vpc`
2. Tab **Routes** → **Edit routes** → **Add route**:
   ```
   Destination: 0.0.0.0/0
   Target: healthbridge-igw
   ```
3. Tab **Subnet associations** → Centang kedua subnet → **Save**

## 1.7 Enable Auto-assign Public IP
Untuk **kedua subnet**:
1. Klik subnet → **Actions** → **Edit subnet settings**
2. ✅ Enable auto-assign public IPv4 address
3. **Save**

---

# TAHAP 2: Buat Security Groups

## 2.1 Security Group Frontend
1. **EC2** → **Security Groups** → **Create security group**
2. Isi:
   ```
   Name: healthbridge-frontend-sg
   VPC: healthbridge-vpc
   ```
3. **Inbound rules**:
   | Type | Port | Source |
   |------|------|--------|
   | HTTP | 80 | 0.0.0.0/0 |
   | HTTPS | 443 | 0.0.0.0/0 |
   | SSH | 22 | My IP |

## 2.2 Security Group Backend
1. Name: `healthbridge-backend-sg`
2. **Inbound rules**:
   | Type | Port | Source |
   |------|------|--------|
   | Custom TCP | 8000 | 0.0.0.0/0 |
   | SSH | 22 | My IP |

## 2.3 Security Group RDS
1. Name: `healthbridge-rds-sg`
2. **Inbound rules**:
   | Type | Port | Source |
   |------|------|--------|
   | PostgreSQL | 5432 | healthbridge-backend-sg |

---

# TAHAP 3: Buat RDS PostgreSQL

## 3.1 Buat DB Subnet Group
1. **RDS** → **Subnet groups** → **Create DB subnet group**
2. Isi:
   ```
   Name: healthbridge-db-subnet-group
   VPC: healthbridge-vpc
   Subnets: Pilih kedua subnet
   ```
3. **Create**

## 3.2 Buat RDS Instance
1. **Databases** → **Create database**
2. Isi:
   ```
   Engine: PostgreSQL 15.x
   Template: Free tier
   DB instance identifier: healthbridge-db
   Master username: postgres
   Master password: YourSecurePassword123!
   Instance class: db.t3.micro
   Storage: 20 GiB gp2
   VPC: healthbridge-vpc
   Subnet group: healthbridge-db-subnet-group
   Public access: Yes
   Security group: healthbridge-rds-sg
   Initial database name: healthbridge
   ```
3. **Create database**
4. Tunggu status **Available** → Catat **Endpoint**

---

# TAHAP 4: Buat Key Pair

1. **EC2** → **Key Pairs** → **Create key pair**
2. Isi:
   ```
   Name: healthbridge-key
   Type: RSA
   Format: .pem
   ```
3. File akan terdownload → Simpan dengan aman!

---

# TAHAP 5: Launch EC2 Frontend

1. **EC2** → **Instances** → **Launch instances**
2. Isi:
   ```
   Name: healthbridge-frontend
   AMI: Ubuntu Server 22.04 LTS
   Instance type: t2.micro
   Key pair: healthbridge-key
   VPC: healthbridge-vpc
   Subnet: healthbridge-public-subnet-1
   Security group: healthbridge-frontend-sg
   ```
3. **Launch instance**
4. Catat **Public IP** → `FRONTEND_IP`

---

# TAHAP 6: Launch EC2 Backend

1. **Launch instances** dengan:
   ```
   Name: healthbridge-backend
   AMI: Ubuntu Server 22.04 LTS
   Instance type: t2.micro
   Key pair: healthbridge-key
   Subnet: healthbridge-public-subnet-1
   Security group: healthbridge-backend-sg
   ```
2. Catat **Public IP** → `BACKEND_IP`

---

# TAHAP 7: Setup S3 Bucket

## 7.1 Buat Bucket
1. **S3** → **Create bucket**
2. Isi:
   ```
   Bucket name: healthbridge-storage-UNIQUE-ID
   Region: ap-southeast-1
   Block Public Access: Uncheck "Block all public access"
   ```
3. **Create bucket**

## 7.2 Buat Folder
- `product_images/`
- `invoices/`
- `orders/`

## 7.3 Set Bucket Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadProductImages",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::BUCKET-NAME/product_images/*"
        }
    ]
}
```

## 7.4 Buat IAM User untuk S3
1. **IAM** → **Users** → **Create user**: `healthbridge-s3-user`
2. Attach policy: `AmazonS3FullAccess`
3. **Create access key** → Catat Access Key ID & Secret

---

# TAHAP 8: Setup Backend Server

## Pilih Opsi:
- **[OPSI A] Dengan Docker** - Lebih mudah, recommended
- **[OPSI B] Tanpa Docker** - Manual install

---

## OPSI A: Backend dengan Docker

### 8A.1 Connect SSH
```bash
ssh -i healthbridge-key.pem ubuntu@BACKEND_IP
```

### 8A.2 Install Docker & PostgreSQL Client
```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
sudo apt install -y postgresql-client
exit
```

### 8A.3 SSH Kembali & Clone
```bash
ssh -i healthbridge-key.pem ubuntu@BACKEND_IP
git clone https://github.com/subagja033010/healthbridge.git
cd healthbridge/healthbridge-backend-main
```

### 8A.4 Setup Database di RDS
```bash
psql -h RDS_ENDPOINT -U postgres -d healthbridge -W
```

Paste SQL berikut:
```sql
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Diseases
CREATE TABLE diseases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100),
    description TEXT,
    symptoms TEXT,
    treatment TEXT,
    medicines TEXT,
    image_url VARCHAR(500)
);

-- Medicines
CREATE TABLE medicines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100),
    price FLOAT DEFAULT 0,
    stock INTEGER DEFAULT 100,
    image_url VARCHAR(500)
);

-- Orders
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    items TEXT,
    total_price FLOAT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cart Items
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    medicine_id INTEGER REFERENCES medicines(id),
    quantity INTEGER DEFAULT 1
);

-- Patients
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    symptoms TEXT,
    diagnosis VARCHAR(255),
    advice TEXT,
    disease_name VARCHAR(255),
    disease_category VARCHAR(100),
    medicines TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Admin User (password: admin123)
INSERT INTO users (email, password, name, role) VALUES (
    'admin@healthbridge.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.hHBFJWjWzQz8/K',
    'Admin',
    'admin'
);

-- Sample Medicines
INSERT INTO medicines (name, description, category, price, stock) VALUES
('Paracetamol 500mg', 'Obat pereda nyeri dan penurun demam', 'Analgesik', 5000, 100),
('Amoxicillin 500mg', 'Antibiotik untuk infeksi bakteri', 'Antibiotik', 15000, 50),
('Omeprazole 20mg', 'Obat untuk asam lambung', 'Gastrointestinal', 12000, 75);

\q
```

### 8A.5 Buat File .env
```bash
nano .env
```
```env
SECRET_KEY=your-secret-key-min-32-chars
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=postgresql://postgres:YourSecurePassword123!@RDS_ENDPOINT:5432/healthbridge
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxx
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=healthbridge-storage-UNIQUE-ID
```

### 8A.6 Edit CORS
```bash
nano main.py
```
Tambahkan domain ke `allow_origins`:
```python
allow_origins=[
    "http://localhost:5173",
    "https://healthbridge.my.id",
    "http://healthbridge.my.id",
],
```

### 8A.7 Build & Run Docker
```bash
mkdir -p static/images
docker build -t healthbridge-backend .
docker run -d \
  --name backend \
  -p 8000:8000 \
  -v $(pwd)/static:/app/static \
  --env-file .env \
  --restart unless-stopped \
  healthbridge-backend
```

---

## OPSI B: Backend TANPA Docker

### 8B.1 Connect SSH
```bash
ssh -i healthbridge-key.pem ubuntu@BACKEND_IP
```

### 8B.2 Install Dependencies
```bash
sudo apt update && sudo apt upgrade -y

# Install Python 3.9+
sudo apt install -y python3 python3-pip python3-venv

# Install PostgreSQL client
sudo apt install -y postgresql-client

# Install Node.js (untuk beberapa dependencies)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### 8B.3 Clone Repository
```bash
git clone https://github.com/subagja033010/healthbridge.git
cd healthbridge/healthbridge-backend-main
```

### 8B.4 Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 8B.5 Install Python Packages
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 8B.6 Setup Database di RDS
(Sama seperti OPSI A - langkah 8A.4)

### 8B.7 Buat File .env
(Sama seperti OPSI A - langkah 8A.5)

### 8B.8 Edit CORS
(Sama seperti OPSI A - langkah 8A.6)

### 8B.9 Buat Folder Static
```bash
mkdir -p static/images
```

### 8B.10 Jalankan Backend dengan Systemd

Buat service file:
```bash
sudo nano /etc/systemd/system/healthbridge-backend.service
```

Isi:
```ini
[Unit]
Description=HealthBridge Backend API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/healthbridge/healthbridge-backend-main
Environment="PATH=/home/ubuntu/healthbridge/healthbridge-backend-main/venv/bin"
EnvironmentFile=/home/ubuntu/healthbridge/healthbridge-backend-main/.env
ExecStart=/home/ubuntu/healthbridge/healthbridge-backend-main/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable dan start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable healthbridge-backend
sudo systemctl start healthbridge-backend

# Check status
sudo systemctl status healthbridge-backend

# Lihat logs
sudo journalctl -u healthbridge-backend -f
```

---

# TAHAP 9: Setup Frontend Server

## Pilih Opsi:
- **[OPSI A] Dengan Docker**
- **[OPSI B] Tanpa Docker**

---

## OPSI A: Frontend dengan Docker

### 9A.1 Connect SSH
```bash
ssh -i healthbridge-key.pem ubuntu@FRONTEND_IP
```

### 9A.2 Install Docker
```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
exit
```

### 9A.3 Clone & Configure
```bash
ssh -i healthbridge-key.pem ubuntu@FRONTEND_IP
git clone https://github.com/subagja033010/healthbridge.git
cd healthbridge/healthbridge-frontend-main
```

### 9A.4 Edit API URL
```bash
nano src/App.jsx
```
Ganti:
```javascript
const API_URL = "https://api.healthbridge.my.id";
// atau jika belum setup subdomain:
const API_URL = "http://BACKEND_IP:8000";
```

### 9A.5 Build & Run Docker
```bash
docker build -t healthbridge-frontend .
docker run -d \
  --name frontend \
  -p 80:80 \
  --restart unless-stopped \
  healthbridge-frontend
```

---

## OPSI B: Frontend TANPA Docker

### 9B.1 Connect SSH
```bash
ssh -i healthbridge-key.pem ubuntu@FRONTEND_IP
```

### 9B.2 Install Nginx & Node.js
```bash
sudo apt update && sudo apt upgrade -y

# Install Nginx
sudo apt install -y nginx

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### 9B.3 Clone & Configure API URL
```bash
git clone https://github.com/subagja033010/healthbridge.git
cd healthbridge/healthbridge-frontend-main

# Edit API URL untuk koneksi ke Backend
nano src/App.jsx
```

**Cari baris ini** (biasanya di bagian atas file):
```javascript
const API_URL = "http://localhost:8000";
```

**Ganti menjadi:**
```javascript
// Jika sudah setup Cloudflare:
const API_URL = "https://api.healthbridge.my.id";

// Atau jika belum setup domain (gunakan IP langsung):
const API_URL = "http://BACKEND_IP:8000";  // Ganti BACKEND_IP dengan IP EC2 Backend
```

Simpan file: `Ctrl+O` → `Enter` → `Ctrl+X`

### 9B.4 Install Dependencies & Build
```bash
# Install dependencies
npm install

# Build production
npm run build
```

### 9B.5 Copy Build ke Nginx
```bash
sudo rm -rf /var/www/html/*
sudo cp -r dist/* /var/www/html/
```

### 9B.6 Konfigurasi Nginx
```bash
sudo nano /etc/nginx/sites-available/default
```

Ganti isinya:
```nginx
server {
    listen 80;
    server_name healthbridge.my.id www.healthbridge.my.id;
    root /var/www/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 9B.7 Restart Nginx
```bash
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

# TAHAP 10: Setup Cloudflare CDN

## 10.1 Buat Akun Cloudflare
1. Buka https://dash.cloudflare.com
2. Sign up (gratis)

## 10.2 Tambahkan Domain
1. Klik **Add a Site**
2. Masukkan: `healthbridge.my.id`
3. Pilih plan **Free**
4. Klik **Continue**

## 10.3 Review DNS Records
Cloudflare akan scan DNS records yang ada. Klik **Continue**.

## 10.4 Update Nameservers
1. Cloudflare akan memberikan 2 nameservers, contoh:
   ```
   ada.ns.cloudflare.com
   bob.ns.cloudflare.com
   ```
2. Login ke registrar domain Anda (tempat beli domain)
3. Ganti nameservers ke nameservers Cloudflare
4. Tunggu propagasi (5 menit - 24 jam)

## 10.5 Tambahkan DNS Records
Di Cloudflare Dashboard → **DNS** → **Records** → **Add record**:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | @ | FRONTEND_IP | ✅ Proxied |
| A | www | FRONTEND_IP | ✅ Proxied |
| A | api | BACKEND_IP | ✅ Proxied |

> 💡 **Penjelasan**:
> - `@` = `healthbridge.my.id` (frontend)
> - `www` = `www.healthbridge.my.id` (frontend)
> - `api` = `api.healthbridge.my.id` (backend)

## 10.6 Enable SSL
1. Klik **SSL/TLS** di sidebar
2. Pilih mode: **Full (strict)**

## 10.7 Enable HTTPS Redirect
1. **SSL/TLS** → **Edge Certificates**
2. Enable **Always Use HTTPS**

## 10.8 Update Backend CORS
SSH ke backend dan edit CORS:
```python
allow_origins=[
    "https://healthbridge.my.id",
    "https://www.healthbridge.my.id",
    "http://localhost:5173",
],
```

Restart backend:
```bash
# Docker:
docker restart backend

# Atau systemd:
sudo systemctl restart healthbridge-backend
```

## 10.9 Update Frontend API URL
Edit `App.jsx` dan rebuild:
```javascript
const API_URL = "https://api.healthbridge.my.id";
```

Rebuild:
```bash
# Docker:
docker stop frontend && docker rm frontend
docker build -t healthbridge-frontend .
docker run -d --name frontend -p 80:80 --restart unless-stopped healthbridge-frontend

# Atau tanpa Docker:
npm run build
sudo cp -r dist/* /var/www/html/
```

---

# TAHAP 11: Test Connection (Semua Koneksi)

Sebelum lanjut, pastikan semua koneksi berfungsi dengan baik.

---

## 11.1 Test SSH Connection ke EC2

### Test SSH Frontend
```bash
ssh -i healthbridge-key.pem ubuntu@FRONTEND_IP
# Jika berhasil, akan muncul prompt: ubuntu@ip-xxx:~$
exit
```

### Test SSH Backend
```bash
ssh -i healthbridge-key.pem ubuntu@BACKEND_IP
# Jika berhasil, akan muncul prompt: ubuntu@ip-xxx:~$
```

**✅ Expected**: Masuk ke server tanpa error

**❌ Troubleshoot**:
- `Permission denied`: Cek file .pem (`chmod 400 healthbridge-key.pem`)
- `Connection refused`: Cek Security Group port 22 terbuka untuk IP Anda
- `Connection timeout`: Cek instance running dan Public IP benar

---

## 11.2 Test Koneksi RDS PostgreSQL

### Dari Backend EC2:
```bash
# SSH ke backend dulu
ssh -i healthbridge-key.pem ubuntu@BACKEND_IP

# Test koneksi ke RDS
psql -h RDS_ENDPOINT -U postgres -d healthbridge -W
```

Masukkan password RDS. Jika berhasil:
```
healthbridge=> 
```

### Test Query:
```sql
-- Cek tables
\dt

-- Cek admin user
SELECT id, email, name, role FROM users;

-- Cek medicines
SELECT id, name, price FROM medicines LIMIT 5;

-- Keluar
\q
```

**✅ Expected**: 
- Konek berhasil
- Tables terlihat
- Data ada

**❌ Troubleshoot**:
- `Connection refused`: 
  - Cek RDS Security Group izinkan port 5432 dari `healthbridge-backend-sg`
  - Cek RDS status "Available"
- `Password authentication failed`: Password salah
- `Database does not exist`: Initial database name salah saat create RDS

---

## 11.3 Test Koneksi S3 Bucket

### Dari Backend EC2:
```bash
# Install AWS CLI (jika belum)
sudo apt install -y awscli

# Konfigurasi credentials
aws configure
# Masukkan:
# AWS Access Key ID: AKIAXXXXXXXXXX
# AWS Secret Access Key: xxxxxxxxxxxxxxxx
# Default region: ap-southeast-1
# Default output: json

# Test list bucket
aws s3 ls

# Test list isi bucket
aws s3 ls s3://healthbridge-storage-UNIQUE-ID/

# Test upload file
echo "test" > test.txt
aws s3 cp test.txt s3://healthbridge-storage-UNIQUE-ID/test.txt

# Test download file
aws s3 cp s3://healthbridge-storage-UNIQUE-ID/test.txt downloaded.txt
cat downloaded.txt

# Cleanup
aws s3 rm s3://healthbridge-storage-UNIQUE-ID/test.txt
rm test.txt downloaded.txt
```

**✅ Expected**: 
- `aws s3 ls` menampilkan bucket
- Upload dan download berhasil

**❌ Troubleshoot**:
- `Access Denied`: Cek IAM user punya policy `AmazonS3FullAccess`
- `NoSuchBucket`: Nama bucket salah
- `InvalidAccessKeyId`: Access key salah

---

## 11.4 Test Backend API

### Test dari Backend EC2 (localhost):
```bash
# Docker
curl http://localhost:8000/
curl http://localhost:8000/api/medicines

# Systemd
curl http://localhost:8000/
curl http://localhost:8000/api/medicines
```

### Test dari komputer lokal:
```bash
# Via IP
curl http://BACKEND_IP:8000/
curl http://BACKEND_IP:8000/api/medicines

# Via domain (setelah Cloudflare setup)
curl https://api.healthbridge.my.id/
curl https://api.healthbridge.my.id/api/medicines
```

**✅ Expected**:
```json
{"message":"Welcome to HealthBridge AI API"}
```
```json
[{"id":1,"name":"Paracetamol 500mg",...}]
```

**❌ Troubleshoot**:
- `Connection refused`:
  - Docker: `docker ps` - pastikan container running
  - Systemd: `sudo systemctl status healthbridge-backend`
- `502 Bad Gateway`: Backend crash, cek logs
- `Empty response`: Cek Security Group port 8000

---

## 11.5 Test Frontend

### Test dari komputer lokal:
```bash
# Via IP
curl -I http://FRONTEND_IP

# Via domain (setelah Cloudflare setup)
curl -I https://healthbridge.my.id
```

### Test via Browser:
1. Buka `http://FRONTEND_IP` atau `https://healthbridge.my.id`
2. Halaman landing harus muncul
3. Coba navigasi ke halaman lain

**✅ Expected**: 
- HTTP 200 atau 301/302
- Halaman web muncul

**❌ Troubleshoot**:
- `Connection refused`:
  - Docker: `docker ps`
  - Nginx: `sudo systemctl status nginx`
- Blank page: Cek console browser (F12) untuk error JavaScript
- API error: Cek API_URL di App.jsx sudah benar

---

## 11.6 Test DNS & Cloudflare

### Test DNS Resolution:
```bash
# Test domain utama
nslookup healthbridge.my.id
dig healthbridge.my.id

# Test subdomain API
nslookup api.healthbridge.my.id
dig api.healthbridge.my.id
```

**✅ Expected**: 
- Menampilkan Cloudflare IP (bukan EC2 IP karena proxied)

### Test SSL Certificate:
```bash
# Test HTTPS
curl -I https://healthbridge.my.id
curl -I https://api.healthbridge.my.id

# Cek certificate
openssl s_client -connect healthbridge.my.id:443 -servername healthbridge.my.id < /dev/null 2>/dev/null | openssl x509 -noout -subject -issuer
```

**✅ Expected**:
- `HTTP/2 200` atau redirect
- Issuer: Cloudflare Inc

**❌ Troubleshoot**:
- DNS tidak resolve: Tunggu propagasi (bisa sampai 24 jam)
- SSL error: 
  - Pastikan Cloudflare SSL mode: "Full (strict)"
  - Cek DNS record sudah proxied (awan oranye)

---

## 11.7 Test End-to-End

### Test Login Admin:
1. Buka `https://healthbridge.my.id`
2. Klik "Masuk"
3. Login dengan:
   ```
   Email: admin@healthbridge.com
   Password: admin123
   ```
4. Pastikan dashboard admin muncul

### Test Tambah Produk:
1. Di Admin Dashboard → Produk → Tambah Produk
2. Isi form, upload gambar
3. Simpan
4. Refresh, pastikan produk muncul

### Test Upload Gambar ke S3:
1. Edit produk → Upload gambar baru
2. SSH ke backend:
   ```bash
   aws s3 ls s3://healthbridge-storage-UNIQUE-ID/product_images/
   ```
3. Pastikan gambar ada di S3

### Test Konsultasi AI:
1. Logout dari admin
2. Klik "Konsultasi"
3. Masukkan gejala
4. Pastikan AI memberikan diagnosis

---

## 11.8 Ringkasan Test Connection

| # | Test | Command/Action | Expected |
|---|------|----------------|----------|
| 1 | SSH Frontend | `ssh -i key.pem ubuntu@FE_IP` | Login berhasil |
| 2 | SSH Backend | `ssh -i key.pem ubuntu@BE_IP` | Login berhasil |
| 3 | RDS Connection | `psql -h RDS_ENDPOINT...` | Connect & query OK |
| 4 | S3 Upload | `aws s3 cp file s3://bucket/` | Upload berhasil |
| 5 | Backend API | `curl http://BE_IP:8000/` | JSON response |
| 6 | Frontend | `curl http://FE_IP` | HTML response |
| 7 | DNS | `nslookup healthbridge.my.id` | IP resolved |
| 8 | HTTPS | `curl https://healthbridge.my.id` | HTTP 200 + SSL OK |
| 9 | Admin Login | Browser login | Dashboard muncul |
| 10 | AI Consult | Submit symptoms | Diagnosis OK |

---

# 💰 Estimasi Biaya (Per Bulan)

| Service | Spec | Biaya (USD) |
|---------|------|-------------|
| EC2 t2.micro (2x) | 730 jam | $0 (Free Tier) |
| RDS db.t3.micro | PostgreSQL | $12.41 |
| S3 Storage | 5GB | $0.12 |
| Cloudflare | Free plan | $0 |
| Domain .my.id | Per tahun | ~$3-5 |
| **TOTAL** | | **~$12-15/bulan** |

---

# 🔧 Maintenance

## View Logs
```bash
# Docker
docker logs -f backend
docker logs -f frontend

# Systemd
sudo journalctl -u healthbridge-backend -f
```

## Restart
```bash
# Docker
docker restart backend
docker restart frontend

# Systemd
sudo systemctl restart healthbridge-backend
sudo systemctl restart nginx
```

---

# 🚨 Troubleshooting

## SSL Error
- Pastikan Cloudflare SSL mode: **Full (strict)**
- Tunggu DNS propagasi selesai

## 502 Bad Gateway
- Backend tidak berjalan
- Cek: `docker ps` atau `sudo systemctl status healthbridge-backend`

## CORS Error
- Pastikan domain ada di `allow_origins`
- Restart backend setelah edit

## Database Connection Error
- Cek RDS endpoint di .env
- Cek Security Group RDS
