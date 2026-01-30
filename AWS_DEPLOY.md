# HealthBridge AI - AWS Deployment Guide

Panduan lengkap untuk deploy HealthBridge ke AWS menggunakan 2 EC2 instances + RDS PostgreSQL.

---

## 📋 Prerequisites

Sebelum memulai, pastikan Anda memiliki:
- ✅ AWS Account dengan akses ke Console
- ✅ Credit card terdaftar di AWS (untuk billing)
- ✅ SSH key pair (akan dibuat di panduan ini)
- ✅ Domain name (opsional, untuk production)

---

## 🏗️ Architecture Overview

```mermaid
flowchart LR
    CF["CloudFront"] --> FE["EC2 Frontend :80"]
    FE --> BE["EC2 Backend :8000"]
    BE --> RDS["RDS PostgreSQL :5432"]
    BE --> S3["S3 Bucket"]
```

---

# TAHAP 1: Setup VPC & Network

## 1.1 Create VPC

1. **Buka AWS Console** → Services → **VPC**
2. Klik **Create VPC**
3. Isi form:
   - Name: `healthbridge-vpc`
   - IPv4 CIDR: `10.0.0.0/16`
   - Tenancy: Default
4. Klik **Create VPC**

## 1.2 Create Public Subnet (untuk EC2)

1. Di VPC Dashboard → **Subnets** → **Create subnet**
2. Isi form:
   - VPC: `healthbridge-vpc`
   - Subnet name: `healthbridge-public-subnet-1`
   - Availability Zone: `ap-southeast-1a`
   - IPv4 CIDR: `10.0.1.0/24`
3. Klik **Create subnet**

## 1.3 Create Private Subnets (untuk RDS)

> ⚠️ **PENTING:** RDS memerlukan minimal 2 subnet di 2 Availability Zone berbeda.

**Subnet 1:**
1. **Create subnet**
2. Isi:
   - VPC: `healthbridge-vpc`
   - Subnet name: `healthbridge-private-subnet-1`
   - Availability Zone: `ap-southeast-1a`
   - IPv4 CIDR: `10.0.2.0/24`

**Subnet 2:**
1. **Create subnet**
2. Isi:
   - VPC: `healthbridge-vpc`
   - Subnet name: `healthbridge-private-subnet-2`
   - Availability Zone: `ap-southeast-1b`
   - IPv4 CIDR: `10.0.3.0/24`

## 1.4 Create Internet Gateway

1. **Internet Gateways** → **Create internet gateway**
2. Name: `healthbridge-igw`
3. Klik **Create**
4. Pilih gateway → **Actions** → **Attach to VPC**
5. Pilih `healthbridge-vpc` → **Attach**

## 1.5 Configure Route Table untuk Public Subnet

1. **Route Tables** → Pilih route table untuk `healthbridge-vpc`
2. Tab **Routes** → **Edit routes**
3. **Add route**:
   - Destination: `0.0.0.0/0`
   - Target: `healthbridge-igw`
4. **Save routes**
5. Tab **Subnet associations** → **Edit subnet associations**
6. Pilih `healthbridge-public-subnet-1` → **Save**

## 1.6 Enable Auto-assign Public IP

1. **Subnets** → Pilih `healthbridge-public-subnet-1`
2. **Actions** → **Edit subnet settings**
3. ✅ Enable **Auto-assign public IPv4 address**
4. **Save**

---

# TAHAP 2: Create Security Groups

## 2.1 Security Group untuk Frontend

1. **EC2** → **Security Groups** → **Create security group**
2. Isi:
   - Name: `healthbridge-frontend-sg`
   - Description: Frontend security group
   - VPC: `healthbridge-vpc`

3. **Inbound rules** (Add rule):

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | HTTP | 80 | 0.0.0.0/0 | Web traffic |
   | HTTPS | 443 | 0.0.0.0/0 | Secure web |
   | SSH | 22 | My IP | Admin access |

4. **Create security group**

## 2.2 Security Group untuk Backend

1. **Create security group**
2. Isi:
   - Name: `healthbridge-backend-sg`
   - Description: Backend security group
   - VPC: `healthbridge-vpc`

3. **Inbound rules**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | Custom TCP | 8000 | 0.0.0.0/0 | API access |
   | SSH | 22 | My IP | Admin access |

4. **Create security group**

## 2.3 Security Group untuk RDS

1. **Create security group**
2. Isi:
   - Name: `healthbridge-rds-sg`
   - Description: RDS PostgreSQL security group
   - VPC: `healthbridge-vpc`

3. **Inbound rules**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | PostgreSQL | 5432 | healthbridge-backend-sg | Backend only |

   > 💡 Di field Source, ketik nama security group backend untuk referensi.

4. **Create security group**

---

# TAHAP 3: Setup RDS PostgreSQL

## 3.1 Create DB Subnet Group

1. **RDS** → **Subnet groups** → **Create DB subnet group**
2. Isi:
   - Name: `healthbridge-db-subnet-group`
   - Description: Subnet group for HealthBridge RDS
   - VPC: `healthbridge-vpc`
3. **Add subnets:**
   - Availability Zones: `ap-southeast-1a`, `ap-southeast-1b`
   - Subnets: Pilih `healthbridge-private-subnet-1` dan `healthbridge-private-subnet-2`
4. **Create**

## 3.2 Create RDS Instance

1. **RDS** → **Databases** → **Create database**
2. Isi form:

   **Engine options:**
   - Engine: PostgreSQL
   - Version: PostgreSQL 15.x

   **Templates:**
   - Free tier (untuk development) ATAU
   - Production (untuk production)

   **Settings:**
   - DB instance identifier: `healthbridge-db`
   - Master username: `admin`
   - Master password: `YourSecurePassword123!` (catat ini!)

   **Instance configuration:**
   - DB instance class: `db.t3.micro` (Free tier eligible)

   **Storage:**
   - Storage type: gp2
   - Allocated storage: 20 GiB
   - ❌ Enable storage autoscaling (disable untuk hemat biaya)

   **Connectivity:**
   - VPC: `healthbridge-vpc`
   - DB subnet group: `healthbridge-db-subnet-group`
   - Public access: **No** ⚠️ (penting untuk keamanan!)
   - VPC security group: Pilih `healthbridge-rds-sg`
   - Availability Zone: No preference

   **Database authentication:**
   - Password authentication

   **Additional configuration:**
   - Initial database name: `healthbridge`
   - ❌ Enable automated backups (disable untuk dev, enable untuk prod)
   - ❌ Enable Enhanced monitoring (disable untuk hemat biaya)

3. **Create database**

## 3.3 Tunggu RDS Available

Tunggu status RDS berubah dari "Creating" ke "Available" (5-10 menit).

## 3.4 Catat RDS Endpoint

1. Klik database `healthbridge-db`
2. Di tab **Connectivity & security**, catat:
   - **Endpoint**: `healthbridge-db.xxxxx.ap-southeast-1.rds.amazonaws.com`
   - **Port**: `5432`

---

# TAHAP 4: Create EC2 Instances

## 4.1 Create Key Pair

1. **EC2** → **Key Pairs** → **Create key pair**
2. Isi:
   - Name: `healthbridge-key`
   - Type: RSA
   - Format: `.pem` (untuk Linux/Mac) atau `.ppk` (untuk Windows PuTTY)
3. **Create** → File akan terdownload otomatis
4. **PENTING**: Simpan file ini dengan aman!

## 4.2 Launch Frontend EC2

1. **EC2** → **Instances** → **Launch instances**
2. Isi form:

   **Name and tags:**
   - Name: `healthbridge-frontend`

   **Application and OS Images:**
   - AMI: Ubuntu Server 22.04 LTS (Free tier eligible)

   **Instance type:**
   - t2.micro (Free tier) atau t3.micro

   **Key pair:**
   - Select: `healthbridge-key`

   **Network settings:** (Edit)
   - VPC: `healthbridge-vpc`
   - Subnet: `healthbridge-public-subnet-1`
   - Auto-assign public IP: Enable
   - Security group: `healthbridge-frontend-sg`

   **Configure storage:**
   - 8 GiB gp2 (default)

3. **Launch instance**

## 4.3 Launch Backend EC2

Ulangi langkah yang sama dengan perbedaan:
- Name: `healthbridge-backend`
- Security group: `healthbridge-backend-sg`

---

# TAHAP 5: Setup Frontend Server

## 5.1 Connect via SSH

**Linux/Mac:**
```bash
chmod 400 healthbridge-key.pem
ssh -i healthbridge-key.pem ubuntu@<FRONTEND_PUBLIC_IP>
```

**Windows (PowerShell):**
```powershell
ssh -i healthbridge-key.pem ubuntu@<FRONTEND_PUBLIC_IP>
```

## 5.2 Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Logout dan login kembali
exit
```

SSH kembali:
```bash
ssh -i healthbridge-key.pem ubuntu@<FRONTEND_PUBLIC_IP>
```

## 5.3 Clone & Build Frontend

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/healthbridge-frontend-main.git
cd healthbridge-frontend-main

# PENTING: Update API URL sebelum build
nano src/App.jsx
```

**Edit baris berikut:**
```javascript
// Ganti ini:
const API_URL = "http://127.0.0.1:8000";

// Menjadi (gunakan IP backend):
const API_URL = "http://<BACKEND_PUBLIC_IP>:8000";
```

Simpan dengan `Ctrl+X`, `Y`, `Enter`

## 5.4 Build & Run Docker

```bash
# Build image
docker build -t healthbridge-frontend .

# Run container
docker run -d \
  --name frontend \
  -p 80:80 \
  --restart unless-stopped \
  healthbridge-frontend

# Verify
docker ps
```

## 5.5 Verify Frontend

Buka browser: `http://<FRONTEND_PUBLIC_IP>`

---

# TAHAP 6: Setup Backend Server

## 6.1 Connect via SSH

```bash
ssh -i healthbridge-key.pem ubuntu@<BACKEND_PUBLIC_IP>
```

## 6.2 Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Logout dan login kembali
exit
```

SSH kembali:
```bash
ssh -i healthbridge-key.pem ubuntu@<BACKEND_PUBLIC_IP>
```

## 6.3 Clone & Configure Backend

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/healthbridge-backend-main.git
cd healthbridge-backend-main

# Create .env file
nano .env
```

**Isi .env (dengan RDS PostgreSQL):**
```env
# JWT Authentication
SECRET_KEY=your-super-secret-key-change-this-in-production

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Database - RDS PostgreSQL
DATABASE_URL=postgresql://admin:YourSecurePassword123!@healthbridge-db.xxxxx.ap-southeast-1.rds.amazonaws.com:5432/healthbridge

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=healthbridge-storage
```

> ⚠️ **PENTING:** Ganti `healthbridge-db.xxxxx.ap-southeast-1.rds.amazonaws.com` dengan RDS endpoint Anda!

Simpan dengan `Ctrl+X`, `Y`, `Enter`

## 6.4 Update CORS Settings

```bash
nano main.py
```

Cari bagian CORS dan tambahkan frontend IP:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://<FRONTEND_PUBLIC_IP>",  # Add this
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 6.5 Install PostgreSQL Dependencies

Tambahkan ke `requirements.txt`:
```bash
echo "psycopg2-binary" >> requirements.txt
```

## 6.6 Build & Run Docker

```bash
# Create directories for persistence
mkdir -p static/images

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

## 6.7 Verify Backend & Database Connection

```bash
# Check logs untuk koneksi database
docker logs backend | grep -i database

# Test API
curl http://localhost:8000/
# Output: {"message":"Welcome to HealthBridge AI API"}
```

---

# TAHAP 7: Setup S3 Bucket

## 7.1 Create S3 Bucket

1. **AWS Console** → **S3** → **Create bucket**
2. Isi:
   - Bucket name: `healthbridge-storage-YOUR-UNIQUE-ID`
   - Region: `ap-southeast-1`
   - Object Ownership: ACLs disabled
   - Block Public Access: Uncheck "Block all public access" (untuk gambar produk)
3. **Create bucket**

## 7.2 Configure Bucket Policy

1. Pilih bucket → **Permissions** → **Bucket policy**
2. Paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadProductImages",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::healthbridge-storage-YOUR-UNIQUE-ID/product_images/*"
        }
    ]
}
```

3. **Save changes**

## 7.3 Create IAM User for S3 Access

1. **IAM** → **Users** → **Create user**
2. User name: `healthbridge-s3-user`
3. **Attach policies directly** → Search: `AmazonS3FullAccess`
4. **Create user**
5. Pilih user → **Security credentials** → **Create access key**
6. Use case: **Application running outside AWS**
7. **Create** → Download CSV (simpan dengan aman!)

## 7.4 Update Backend .env

```bash
ssh -i healthbridge-key.pem ubuntu@<BACKEND_PUBLIC_IP>
cd healthbridge-backend-main
nano .env
```

Update AWS credentials:
```env
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_S3_BUCKET=healthbridge-storage-YOUR-UNIQUE-ID
```

Restart container:
```bash
docker restart backend
```

---

# TAHAP 8: Setup CloudFront (CDN)

## 8.1 Create Distribution

1. **CloudFront** → **Create distribution**
2. **Origin:**
   - Origin domain: `<FRONTEND_PUBLIC_IP>` atau S3 bucket
   - Protocol: HTTP only
   - Origin path: (kosong)

3. **Default cache behavior:**
   - Viewer protocol policy: Redirect HTTP to HTTPS
   - Allowed HTTP methods: GET, HEAD
   - Cache policy: CachingOptimized

4. **Settings:**
   - Price class: Use only North America and Europe (lebih murah)
   - Alternate domain name (CNAME): (opsional, jika punya domain)
   - SSL certificate: Default CloudFront certificate

5. **Create distribution**

## 8.2 Wait for Deployment

Tunggu status berubah dari "Deploying" ke "Enabled" (5-15 menit)

## 8.3 Access via CloudFront

Setelah deployed, akses via:
```
https://d1234567890abc.cloudfront.net
```

---

# TAHAP 9: Verification & Testing

## 9.1 Test Frontend

1. Buka `http://<FRONTEND_PUBLIC_IP>`
2. Pastikan halaman landing muncul
3. Coba navigasi ke berbagai halaman

## 9.2 Test Backend API

```bash
# Test dari local
curl http://<BACKEND_PUBLIC_IP>:8000/api/medicines

# Test dari frontend EC2
ssh -i healthbridge-key.pem ubuntu@<FRONTEND_PUBLIC_IP>
curl http://<BACKEND_PUBLIC_IP>:8000/api/medicines
```

## 9.3 Test Database Connection

```bash
# Di backend server
docker logs backend | grep -i "database\|postgres\|connected"
```

## 9.4 Test Admin Login

1. Buka `http://<FRONTEND_PUBLIC_IP>`
2. Login dengan:
   - Email: `admin@healthbridge.com`
   - Password: `admin123`
3. Verifikasi dashboard admin muncul

## 9.5 Test Image Upload

1. Login sebagai admin
2. Kelola Produk → Edit produk
3. Upload gambar baru
4. Verifikasi gambar muncul dan tersimpan ke S3

---

# 💰 Cost Estimation (Per Month)

| Service | Specification | Cost (USD) |
|---------|---------------|------------|
| EC2 t2.micro (2x) | 730 hours | $0-18.70 |
| RDS db.t3.micro | Single-AZ | $12.41 |
| S3 Storage | 5GB | $0.12 |
| CloudFront | 50GB transfer | $4.25 |
| Data Transfer | 10GB | $0.90 |
| **TOTAL** | | **~$18-37/month** |

> 💡 **Free Tier:** EC2 dan RDS gratis 12 bulan pertama (dengan batasan).

---

# 🔧 Maintenance Commands

## View Logs
```bash
# Frontend
docker logs -f frontend

# Backend
docker logs -f backend
```

## Restart Containers
```bash
docker restart frontend
docker restart backend
```

## Update Application
```bash
# Frontend
cd healthbridge-frontend-main
git pull
docker build -t healthbridge-frontend .
docker stop frontend && docker rm frontend
docker run -d --name frontend -p 80:80 --restart unless-stopped healthbridge-frontend

# Backend
cd healthbridge-backend-main
git pull
docker build -t healthbridge-backend .
docker stop backend && docker rm backend
docker run -d --name backend -p 8000:8000 -v $(pwd)/static:/app/static --env-file .env --restart unless-stopped healthbridge-backend
```

## Backup Database (RDS)
```bash
# RDS otomatis backup jika enabled
# Manual snapshot via Console:
# RDS → Databases → healthbridge-db → Actions → Take snapshot
```

---

# 🚨 Troubleshooting

## Container tidak jalan
```bash
docker logs backend
docker logs frontend
```

## Database Connection Error
```bash
# Check RDS endpoint benar
# Check security group RDS mengizinkan backend
# Check username/password benar
docker logs backend | grep -i "database\|error\|connection"
```

## CORS Error
Pastikan frontend IP ada di allow_origins di main.py

## Cannot connect to backend
- Check security group port 8000 open
- Check backend container running: `docker ps`

## Images not loading
- Check S3 bucket policy
- Check AWS credentials in .env
