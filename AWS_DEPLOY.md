# HealthBridge AI - AWS Deployment Guide

Panduan lengkap deploy HealthBridge ke AWS dengan **2 EC2 instances** + **RDS PostgreSQL**.

---

## 📋 Prerequisites

Sebelum memulai, pastikan Anda memiliki:
- ✅ AWS Account aktif
- ✅ Credit card terdaftar di AWS
- ✅ Repository GitHub sudah di-clone

---

## 🏗️ Architecture Overview

```mermaid
flowchart TB
    subgraph Internet
        User["👤 User"]
    end

    subgraph AWS["AWS Cloud"]
        subgraph VPC["VPC 10.0.0.0/16"]
            subgraph PublicSubnet1["Public Subnet 1<br/>10.0.1.0/24<br/>ap-southeast-1a"]
                EC2_FE["🖥️ EC2 Frontend<br/>Nginx + React<br/>Port 80"]
                EC2_BE["🖥️ EC2 Backend<br/>FastAPI<br/>Port 8000"]
            end
            
            subgraph PublicSubnet2["Public Subnet 2<br/>10.0.2.0/24<br/>ap-southeast-1b"]
                RDS["🗄️ RDS PostgreSQL<br/>Port 5432"]
            end
        end

        S3["📦 S3 Bucket<br/>Product Images"]
        CF["🌐 CloudFront CDN"]
    end

    User --> CF --> EC2_FE --> EC2_BE
    EC2_BE --> RDS
    EC2_BE --> S3
```

### Komponen:
| Komponen | Lokasi | Fungsi |
|----------|--------|--------|
| Frontend EC2 | Public Subnet 1 | Serve React app via Nginx |
| Backend EC2 | Public Subnet 1 | FastAPI API Server |
| RDS PostgreSQL | Public Subnet 2 | Database (production) |
| S3 Bucket | AWS S3 | Penyimpanan gambar (production) |
| CloudFront | CDN | Cache & HTTPS |

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
   - Klik dropdown region di pojok kanan atas
   - Pilih **Asia Pacific (Singapore)**

## 1.2 Buat VPC Baru
1. Ketik **VPC** di search bar → Klik **VPC**
2. Klik tombol **Create VPC** (tombol oranye)
3. Pilih **VPC only** (bukan "VPC and more")
4. Isi form:
   ```
   Name tag: healthbridge-vpc
   IPv4 CIDR block: 10.0.0.0/16
   IPv6 CIDR block: No IPv6 CIDR block
   Tenancy: Default
   ```
5. Klik **Create VPC**
6. ✅ VPC berhasil dibuat! Catat **VPC ID** (vpc-xxxxxxxx)

## 1.3 Buat Subnet 1 (untuk EC2)
1. Di sidebar kiri, klik **Subnets**
2. Klik **Create subnet**
3. Isi form:
   ```
   VPC ID: Pilih healthbridge-vpc
   Subnet name: healthbridge-public-subnet-1
   Availability Zone: ap-southeast-1a
   IPv4 CIDR block: 10.0.1.0/24
   ```
4. Klik **Create subnet**

## 1.4 Buat Subnet 2 (untuk RDS)
1. Klik **Create subnet** lagi
2. Isi form:
   ```
   VPC ID: Pilih healthbridge-vpc
   Subnet name: healthbridge-public-subnet-2
   Availability Zone: ap-southeast-1b
   IPv4 CIDR block: 10.0.2.0/24
   ```
3. Klik **Create subnet**

> ⚠️ **PENTING**: RDS memerlukan minimal 2 subnet di 2 Availability Zone berbeda!

## 1.5 Buat Internet Gateway
1. Di sidebar kiri, klik **Internet Gateways**
2. Klik **Create internet gateway**
3. Isi form:
   ```
   Name tag: healthbridge-igw
   ```
4. Klik **Create internet gateway**
5. Klik tombol **Actions** → **Attach to VPC**
6. Pilih **healthbridge-vpc** → Klik **Attach internet gateway**

## 1.6 Konfigurasi Route Table
1. Di sidebar kiri, klik **Route Tables**
2. Cari route table yang VPC-nya `healthbridge-vpc` → Klik ID-nya
3. Klik tab **Routes** → **Edit routes**
4. Klik **Add route**:
   ```
   Destination: 0.0.0.0/0
   Target: Internet Gateway → pilih healthbridge-igw
   ```
5. Klik **Save changes**
6. Klik tab **Subnet associations** → **Edit subnet associations**
7. Centang ✅ `healthbridge-public-subnet-1` DAN `healthbridge-public-subnet-2`
8. Klik **Save associations**

## 1.7 Enable Auto-assign Public IP
Lakukan untuk **KEDUA** subnet:

**Subnet 1:**
1. Klik `healthbridge-public-subnet-1`
2. Klik **Actions** → **Edit subnet settings**
3. Centang ✅ **Enable auto-assign public IPv4 address**
4. Klik **Save**

**Subnet 2:**
1. Klik `healthbridge-public-subnet-2`
2. Klik **Actions** → **Edit subnet settings**
3. Centang ✅ **Enable auto-assign public IPv4 address**
4. Klik **Save**

---

# TAHAP 2: Buat Security Groups

## 2.1 Security Group Frontend
1. Buka **EC2** (ketik di search bar)
2. Di sidebar kiri, klik **Security Groups**
3. Klik **Create security group**
4. Isi form:
   ```
   Security group name: healthbridge-frontend-sg
   Description: Security group for frontend
   VPC: healthbridge-vpc
   ```
5. **Inbound rules** → Klik **Add rule** 3x:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | HTTP | 80 | 0.0.0.0/0 | Web access |
   | HTTPS | 443 | 0.0.0.0/0 | Secure web |
   | SSH | 22 | My IP | Admin SSH |

6. Klik **Create security group**

## 2.2 Security Group Backend
1. Klik **Create security group** lagi
2. Isi form:
   ```
   Security group name: healthbridge-backend-sg
   Description: Security group for backend
   VPC: healthbridge-vpc
   ```
3. **Inbound rules** → Klik **Add rule** 2x:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | Custom TCP | 8000 | 0.0.0.0/0 | API access |
   | SSH | 22 | My IP | Admin SSH |

4. Klik **Create security group**

## 2.3 Security Group RDS
1. Klik **Create security group** lagi
2. Isi form:
   ```
   Security group name: healthbridge-rds-sg
   Description: Security group for RDS PostgreSQL
   VPC: healthbridge-vpc
   ```
3. **Inbound rules** → Klik **Add rule**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | PostgreSQL | 5432 | healthbridge-backend-sg | Backend only |

   > 💡 Di field Source, ketik `healthbridge-backend-sg` untuk referensi Security Group

4. Klik **Create security group**

---

# TAHAP 3: Buat RDS PostgreSQL

## 3.1 Buat DB Subnet Group
1. Ketik **RDS** di search bar → Klik **RDS**
2. Di sidebar kiri, klik **Subnet groups**
3. Klik **Create DB subnet group**
4. Isi form:
   ```
   Name: healthbridge-db-subnet-group
   Description: Subnet group for HealthBridge RDS
   VPC: healthbridge-vpc
   ```
5. **Add subnets:**
   - Availability Zones: Pilih `ap-southeast-1a` dan `ap-southeast-1b`
   - Subnets: Pilih kedua subnet (10.0.1.0/24 dan 10.0.2.0/24)
6. Klik **Create**

## 3.2 Buat RDS Instance
1. Di sidebar kiri, klik **Databases**
2. Klik **Create database**
3. Isi form dengan SANGAT HATI-HATI:

   **Choose a database creation method:**
   ```
   ✅ Standard create
   ```

   **Engine options:**
   ```
   Engine type: PostgreSQL
   Version: PostgreSQL 15.x (pilih yang terbaru)
   ```

   **Templates:**
   ```
   ✅ Free tier
   ```

   **Settings:**
   ```
   DB instance identifier: healthbridge-db
   Master username: postgres
   Master password: YourSecurePassword123!
   Confirm password: YourSecurePassword123!
   ```
   > ⚠️ **CATAT PASSWORD INI!** Tidak bisa dilihat lagi setelah create.

   **Instance configuration:**
   ```
   DB instance class: db.t3.micro (atau db.t4g.micro)
   ```

   **Storage:**
   ```
   Storage type: gp2
   Allocated storage: 20 GiB
   ❌ Enable storage autoscaling: UNCHECK
   ```

   **Connectivity:**
   ```
   Compute resource: Don't connect to an EC2
   Network type: IPv4
   VPC: healthbridge-vpc
   DB subnet group: healthbridge-db-subnet-group
   Public access: Yes
   VPC security group: Choose existing
   Existing VPC security groups: healthbridge-rds-sg
   Availability Zone: No preference
   ```

   **Database authentication:**
   ```
   ✅ Password authentication
   ```

   **Additional configuration:** (klik untuk expand)
   ```
   Initial database name: healthbridge
   ❌ Enable automated backups: UNCHECK (untuk hemat biaya)
   ❌ Enable Enhanced monitoring: UNCHECK
   ❌ Enable auto minor version upgrade: UNCHECK
   ❌ Enable deletion protection: UNCHECK
   ```

4. Klik **Create database**
5. ⏳ Tunggu status berubah dari "Creating" ke "Available" (5-10 menit)

## 3.3 Catat RDS Endpoint
1. Setelah status "Available", klik `healthbridge-db`
2. Di tab **Connectivity & security**, catat:
   ```
   Endpoint: healthbridge-db.xxxxxxxxx.ap-southeast-1.rds.amazonaws.com
   Port: 5432
   ```

---

# TAHAP 4: Buat Key Pair

1. Di sidebar EC2, klik **Key Pairs**
2. Klik **Create key pair**
3. Isi form:
   ```
   Name: healthbridge-key
   Key pair type: RSA
   Private key file format: .pem
   ```
4. Klik **Create key pair**
5. ⚠️ **PENTING**: File `healthbridge-key.pem` akan terdownload otomatis
6. Simpan file ini di tempat aman! Tidak bisa didownload ulang!

---

# TAHAP 5: Launch EC2 Frontend

## 5.1 Buat Instance
1. Di sidebar EC2, klik **Instances**
2. Klik **Launch instances**
3. Isi form:

   **Name:**
   ```
   healthbridge-frontend
   ```

   **Application and OS Images:**
   - Klik **Ubuntu**
   - Pilih **Ubuntu Server 22.04 LTS (Free tier eligible)**

   **Instance type:**
   - Pilih **t2.micro** (Free tier eligible)

   **Key pair:**
   - Pilih **healthbridge-key**

   **Network settings:** Klik **Edit**
   ```
   VPC: healthbridge-vpc
   Subnet: healthbridge-public-subnet-1
   Auto-assign public IP: Enable
   Firewall: Select existing security group
   Security groups: healthbridge-frontend-sg
   ```

4. Klik **Launch instance**

## 5.2 Catat Public IP
1. Tunggu instance berstatus **Running**
2. Klik instance → Catat **Public IPv4 address**
   ```
   Contoh: 54.123.45.67 (FRONTEND_IP)
   ```

---

# TAHAP 6: Launch EC2 Backend

Ulangi langkah TAHAP 5 dengan perbedaan:

```
Name: healthbridge-backend
Security group: healthbridge-backend-sg
```

Catat **Public IPv4 address** backend:
```
Contoh: 54.234.56.78 (BACKEND_IP)
```

---

# TAHAP 7: Setup S3 Bucket

## 7.1 Buat Bucket
1. Ketik **S3** di search bar → Klik **S3**
2. Klik **Create bucket**
3. Isi form:
   ```
   Bucket name: healthbridge-storage-UNIQUE-ID
   (Ganti UNIQUE-ID dengan angka random, misal: healthbridge-storage-12345)
   
   AWS Region: Asia Pacific (Singapore) ap-southeast-1
   ```
4. **Object Ownership**: ACLs disabled (recommended)
5. **Block Public Access**: 
   - ❌ Uncheck "Block all public access"
   - ✅ Centang "I acknowledge..."
6. Klik **Create bucket**

## 7.2 Buat Folder di Bucket
1. Klik bucket yang baru dibuat
2. Klik **Create folder**
3. Buat folder:
   - `product_images/`
   - `invoices/`
   - `orders/`

## 7.3 Set Bucket Policy
1. Klik tab **Permissions**
2. Scroll ke **Bucket policy** → Klik **Edit**
3. Paste policy ini (ganti BUCKET-NAME dengan nama bucket Anda):
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
4. Klik **Save changes**

## 7.4 Buat IAM User untuk S3
1. Ketik **IAM** di search bar → Klik **IAM**
2. Klik **Users** → **Create user**
3. Isi:
   ```
   User name: healthbridge-s3-user
   ```
4. Klik **Next**
5. Pilih **Attach policies directly**
6. Cari dan centang: **AmazonS3FullAccess**
7. Klik **Next** → **Create user**
8. Klik user yang baru dibuat → tab **Security credentials**
9. Scroll ke **Access keys** → **Create access key**
10. Pilih **Application running outside AWS** → **Next**
11. Klik **Create access key**
12. ⚠️ **CATAT atau DOWNLOAD**:
    ```
    Access key ID: AKIAXXXXXXXXXXXXXXXXX
    Secret access key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    ```

---

# TAHAP 8: Setup Backend Server

## 8.1 Connect SSH
```bash
# Linux/Mac:
chmod 400 healthbridge-key.pem
ssh -i healthbridge-key.pem ubuntu@BACKEND_IP

# Windows PowerShell:
ssh -i healthbridge-key.pem ubuntu@BACKEND_IP
```

## 8.2 Install Docker & PostgreSQL Client
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install PostgreSQL client (untuk setup database)
sudo apt install -y postgresql-client

# Logout dan login kembali
exit
```

## 8.3 SSH Kembali
```bash
ssh -i healthbridge-key.pem ubuntu@BACKEND_IP
```

## 8.4 Clone Repository
```bash
git clone https://github.com/subagja033010/healthbridge.git
cd healthbridge/healthbridge-backend-main
```

## 8.5 Setup Database Tables di RDS

### 8.5.1 Test Koneksi ke RDS
```bash
psql -h RDS_ENDPOINT -U postgres -d healthbridge -W
```
Ganti `RDS_ENDPOINT` dengan endpoint RDS Anda.
Masukkan password yang Anda buat sebelumnya.

Jika berhasil connect, Anda akan melihat prompt:
```
healthbridge=>
```

### 8.5.2 Buat Tables

Copy dan paste SQL berikut di prompt PostgreSQL:

```sql
-- Table Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table Diseases
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

-- Table Medicines
CREATE TABLE medicines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100),
    price FLOAT DEFAULT 0,
    stock INTEGER DEFAULT 100,
    image_url VARCHAR(500)
);

-- Table Orders
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

-- Table Cart Items
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    medicine_id INTEGER REFERENCES medicines(id),
    quantity INTEGER DEFAULT 1
);

-- Table Patients (untuk history konsultasi)
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

-- Insert Admin User (password: admin123)
INSERT INTO users (email, password, name, role) VALUES (
    'admin@healthbridge.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.hHBFJWjWzQz8/K',
    'Admin',
    'admin'
);

-- Insert Sample Medicines
INSERT INTO medicines (name, description, category, price, stock) VALUES
('Paracetamol 500mg', 'Obat pereda nyeri dan penurun demam', 'Analgesik', 5000, 100),
('Amoxicillin 500mg', 'Antibiotik untuk infeksi bakteri', 'Antibiotik', 15000, 50),
('Omeprazole 20mg', 'Obat untuk asam lambung dan maag', 'Gastrointestinal', 12000, 75),
('Cetirizine 10mg', 'Antihistamin untuk alergi', 'Antihistamin', 8000, 80),
('Vitamin C 500mg', 'Suplemen untuk daya tahan tubuh', 'Vitamin', 10000, 100);

-- Insert Sample Diseases
INSERT INTO diseases (name, category, description, symptoms, treatment, medicines) VALUES
('Flu', 'Infeksi Virus', 'Infeksi virus yang menyerang saluran pernapasan', 'Demam, batuk, pilek, nyeri otot, sakit kepala', 'Istirahat cukup, minum banyak cairan, obat pereda gejala', 'Paracetamol, Vitamin C'),
('Maag', 'Gastrointestinal', 'Gangguan pada lambung akibat asam lambung berlebih', 'Nyeri ulu hati, mual, kembung, perut terasa panas', 'Makan teratur, hindari makanan pedas dan asam', 'Omeprazole, Antasida'),
('Alergi', 'Imunologi', 'Reaksi sistem imun terhadap zat tertentu', 'Gatal, ruam kulit, bersin, mata berair', 'Hindari alergen, antihistamin', 'Cetirizine, Loratadine');
```

### 8.5.3 Verifikasi Tables
```sql
-- Lihat semua tables
\dt

-- Lihat isi table users
SELECT * FROM users;

-- Lihat isi table medicines
SELECT * FROM medicines;

-- Keluar dari PostgreSQL
\q
```

## 8.6 Buat File .env
```bash
nano .env
```

Isi dengan kredensial Anda:
```env
# JWT Authentication
SECRET_KEY=ganti-dengan-random-string-yang-panjang-dan-aman-minimal-32-karakter

# Google Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Database - RDS PostgreSQL
DATABASE_URL=postgresql://postgres:YourSecurePassword123!@RDS_ENDPOINT:5432/healthbridge

# AWS S3
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=healthbridge-storage-UNIQUE-ID
```

> ⚠️ Ganti:
> - `RDS_ENDPOINT` dengan endpoint RDS Anda
> - `YourSecurePassword123!` dengan password RDS
> - AWS credentials dengan yang Anda catat

Simpan: `Ctrl+X` → `Y` → `Enter`

## 8.7 Edit CORS di main.py
```bash
nano main.py
```

Cari bagian `allow_origins` dan tambahkan IP frontend:
```python
allow_origins=[
    "http://localhost:5173",
    "http://localhost:3000",
    "http://FRONTEND_IP",  # Tambahkan ini
],
```

Simpan: `Ctrl+X` → `Y` → `Enter`

## 8.8 Buat Folder Static
```bash
mkdir -p static/images
```

## 8.9 Build & Run Docker
```bash
# Build image
docker build -t healthbridge-backend .

# Run container
docker run -d \
  --name backend \
  -p 8000:8000 \
  -v $(pwd)/static:/app/static \
  --env-file .env \
  --restart unless-stopped \
  healthbridge-backend

# Verify
docker ps
docker logs backend
```

## 8.10 Test API & Database Connection
```bash
# Test API
curl http://localhost:8000/

# Check database connection di logs
docker logs backend | grep -i "database\|postgres"
```

---

# TAHAP 9: Setup Frontend Server

## 9.1 Connect SSH
```bash
ssh -i healthbridge-key.pem ubuntu@FRONTEND_IP
```

## 9.2 Install Docker
```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
exit
```

## 9.3 SSH Kembali
```bash
ssh -i healthbridge-key.pem ubuntu@FRONTEND_IP
```

## 9.4 Clone & Configure
```bash
git clone https://github.com/subagja033010/healthbridge.git
cd healthbridge/healthbridge-frontend-main
```

## 9.5 Edit API URL
```bash
nano src/App.jsx
```

Cari dan ganti:
```javascript
const API_URL = "http://127.0.0.1:8000";
// Menjadi:
const API_URL = "http://BACKEND_IP:8000";
```

Simpan: `Ctrl+X` → `Y` → `Enter`

## 9.6 Build & Run
```bash
docker build -t healthbridge-frontend .
docker run -d \
  --name frontend \
  -p 80:80 \
  --restart unless-stopped \
  healthbridge-frontend

docker ps
```

---

# TAHAP 10: Setup CloudFront (Opsional)

1. Ketik **CloudFront** di search bar
2. Klik **Create distribution**
3. **Origin domain**: `FRONTEND_IP`
4. **Protocol**: HTTP only
5. **Viewer protocol policy**: Redirect HTTP to HTTPS
6. Klik **Create distribution**
7. Tunggu status **Deployed**

---

# TAHAP 11: Verifikasi

## 11.1 Test Frontend
Buka browser: `http://FRONTEND_IP`

## 11.2 Test Login Admin
```
Email: admin@healthbridge.com
Password: admin123
```

## 11.3 Test Database
1. Login sebagai admin
2. Tambah produk baru
3. Pastikan tersimpan (refresh halaman)

## 11.4 Test Upload Gambar
1. Edit produk → Upload gambar
2. Cek S3 bucket → folder `product_images/`

---

# 💰 Estimasi Biaya (Per Bulan)

| Service | Spec | Biaya (USD) |
|---------|------|-------------|
| EC2 t2.micro (2x) | 730 jam | $0 (Free Tier) |
| RDS db.t3.micro | PostgreSQL | $12.41 |
| S3 Storage | 5GB | $0.12 |
| CloudFront | 50GB | $4.25 |
| **TOTAL** | | **~$17-20/bulan** |

> 💡 **Free Tier**: EC2 & RDS gratis 12 bulan pertama (dengan batasan)

---

# 🔧 Maintenance

## View Logs
```bash
docker logs -f backend
docker logs -f frontend
```

## Restart
```bash
docker restart backend
docker restart frontend
```

## Backup Database (RDS)
```bash
# Export database
pg_dump -h RDS_ENDPOINT -U postgres -d healthbridge > backup.sql

# Import ke RDS baru
psql -h NEW_RDS_ENDPOINT -U postgres -d healthbridge < backup.sql
```

---

# 🚨 Troubleshooting

## Database Connection Error
```bash
# Test koneksi manual
psql -h RDS_ENDPOINT -U postgres -d healthbridge -W

# Check RDS Security Group mengizinkan port 5432 dari backend
# Check endpoint dan password di .env benar
```

## Tables Tidak Ada
```bash
# Connect ke RDS dan jalankan SQL di TAHAP 8.5.2
psql -h RDS_ENDPOINT -U postgres -d healthbridge -W
```

## CORS Error
Pastikan IP frontend ada di `allow_origins` di `main.py`

## Container Tidak Jalan
```bash
docker logs backend
docker logs frontend
```
