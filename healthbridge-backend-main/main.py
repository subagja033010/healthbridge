from fastapi import FastAPI, Depends, Query, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, List
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
import requests 
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# JWT Configuration (from .env)
SECRET_KEY = os.getenv("SECRET_KEY", "healthbridge-secret-key-2024-default")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Security
security = HTTPBearer()

# ==========================================
# 1. KONFIGURASI GEMINI (HYBRID)
# ==========================================
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"

# ==========================================
# 2. DATABASE SETUP
# ==========================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./healthbridge.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PatientRecord(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    symptoms = Column(Text)
    diagnosis = Column(String)
    advice = Column(Text)
    disease_name = Column(String, nullable=True)  # Nama penyakit yang terdeteksi
    disease_category = Column(String, nullable=True)  # Kategori penyakit
    medicines = Column(Text, nullable=True)  # Obat yang direkomendasikan
    created_at = Column(String, nullable=True)  # Waktu konsultasi

class Disease(Base):
    __tablename__ = "diseases"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    category = Column(String)
    description = Column(Text)
    symptoms = Column(Text)
    treatment = Column(Text)
    medicines = Column(Text)  # Rekomendasi obat
    image_url = Column(String)

# ==========================================
# 2.1 TABEL TOKO OBAT (BARU)
# ==========================================
class Medicine(Base):
    __tablename__ = "medicines"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    description = Column(Text)
    category = Column(String)
    price = Column(Float)
    stock = Column(Integer, default=100)
    image_url = Column(String, nullable=True)

class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    medicine_id = Column(Integer)
    quantity = Column(Integer, default=1)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String)
    phone = Column(String)
    address = Column(Text)
    items = Column(Text)  # JSON string of items
    total_price = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(String)

# ==========================================
# 2.2 TABEL USER (AUTENTIKASI)
# ==========================================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)  # Hashed password
    name = Column(String)
    role = Column(String, default="user")  # user or admin
    created_at = Column(String)

Base.metadata.create_all(bind=engine)

# ==========================================
# 3. SEED DATA PENYAKIT
# ==========================================
def seed_diseases(db: Session):
    if db.query(Disease).count() == 0:
        diseases_data = [
            {
                "name": "Demam",
                "category": "Infeksi",
                "description": "Demam adalah kondisi ketika suhu tubuh naik di atas normal (di atas 37.5°C). Demam merupakan respons alami tubuh terhadap infeksi virus atau bakteri.",
                "symptoms": "Suhu tubuh tinggi, menggigil, berkeringat, sakit kepala, nyeri otot, lemas, kehilangan nafsu makan",
                "treatment": "Istirahat yang cukup, minum banyak cairan, kompres hangat, konsumsi obat penurun panas seperti Paracetamol",
                "medicines": "Paracetamol 500mg, Ibuprofen 400mg, Sanmol, Tempra",
                "image_url": "/static/images/demam.png"
            },
            {
                "name": "Flu (Influenza)",
                "category": "Infeksi Virus",
                "description": "Flu adalah infeksi virus yang menyerang sistem pernapasan. Virus influenza menyebar melalui droplet saat batuk atau bersin.",
                "symptoms": "Hidung tersumbat, pilek, batuk, sakit tenggorokan, demam, nyeri tubuh, kelelahan",
                "treatment": "Istirahat total, minum air hangat, konsumsi vitamin C, gunakan masker, obat flu jika diperlukan",
                "medicines": "Decolgen, Bodrex Flu & Batuk, Neozep Forte, Panadol Cold & Flu, Vitamin C 1000mg",
                "image_url": "/static/images/flu.png"
            },
            {
                "name": "Maag (Gastritis)",
                "category": "Pencernaan",
                "description": "Maag adalah peradangan pada lapisan lambung yang menyebabkan nyeri dan ketidaknyamanan di perut bagian atas.",
                "symptoms": "Nyeri ulu hati, mual, muntah, kembung, perut terasa penuh, sendawa berlebihan",
                "treatment": "Makan teratur dan porsi kecil, hindari makanan pedas dan asam, kurangi kafein, konsumsi antasida",
                "medicines": "Promag, Mylanta, Polysilane, Omeprazole 20mg, Lansoprazole, Antasida DOEN",
                "image_url": "/static/images/maag.png"
            },
            {
                "name": "Migrain",
                "category": "Neurologis",
                "description": "Migrain adalah sakit kepala berdenyut yang intense, biasanya di satu sisi kepala. Dapat disertai mual dan sensitivitas terhadap cahaya.",
                "symptoms": "Sakit kepala berdenyut, mual, muntah, sensitif terhadap cahaya dan suara, gangguan penglihatan",
                "treatment": "Istirahat di ruangan gelap dan tenang, kompres dingin, obat pereda nyeri, hindari pemicu migrain",
                "medicines": "Panadol Extra, Saridon, Bodrexin, Paramex, Antalgin",
                "image_url": "/static/images/migrain.png"
            },
            {
                "name": "Dermatitis Alergi",
                "category": "Kulit",
                "description": "Dermatitis alergi adalah reaksi kulit terhadap alergen yang menyebabkan ruam, gatal, dan kemerahan.",
                "symptoms": "Kulit gatal, kemerahan, ruam, bengkak, kulit kering dan bersisik, lepuhan kecil",
                "treatment": "Hindari alergen, gunakan krim kortikosteroid, lotion pelembab, antihistamin oral jika gatal parah",
                "medicines": "Cetirizine 10mg, Loratadine, CTM (Chlorpheniramine), Hydrocortisone Cream, Calamine Lotion",
                "image_url": "/static/images/dermatitis.png"
            },
            {
                "name": "Hipertensi",
                "category": "Kardiovaskular",
                "description": "Hipertensi atau tekanan darah tinggi adalah kondisi ketika tekanan darah dalam arteri meningkat secara persisten di atas 140/90 mmHg.",
                "symptoms": "Sering tanpa gejala, sakit kepala, sesak napas, mimisan, pusing, nyeri dada",
                "treatment": "Diet rendah garam, olahraga teratur, kelola stres, hindari alkohol dan rokok, obat antihipertensi",
                "medicines": "Amlodipine 5mg, Captopril, Lisinopril, Bisoprolol (dengan resep dokter)",
                "image_url": "/static/images/hipertensi.png"
            },
            {
                "name": "Diabetes Mellitus",
                "category": "Metabolik",
                "description": "Diabetes adalah penyakit metabolik kronis yang ditandai dengan kadar gula darah tinggi karena tubuh tidak dapat memproduksi atau menggunakan insulin dengan baik.",
                "symptoms": "Sering buang air kecil, haus berlebihan, lapar terus-menerus, penurunan berat badan, luka sulit sembuh",
                "treatment": "Diet seimbang rendah gula, olahraga teratur, monitor gula darah, obat diabetes atau insulin",
                "medicines": "Metformin 500mg, Glibenclamide, Glimepiride (dengan resep dokter), Glucometer",
                "image_url": "/static/images/diabetes.png"
            },
            {
                "name": "Vertigo",
                "category": "Neurologis",
                "description": "Vertigo adalah sensasi pusing berputar yang membuat penderita merasa dirinya atau lingkungan sekitar berputar.",
                "symptoms": "Pusing berputar, mual, muntah, kehilangan keseimbangan, nistagmus (gerakan mata abnormal)",
                "treatment": "Istirahat, hindari gerakan kepala mendadak, manuver Epley, obat antivertigo jika diperlukan",
                "medicines": "Betahistine (Mertigo), Dimenhidrinat (Antimo), Flunarizine, Cinnarizine",
                "image_url": "/static/images/vertigo.png"
            },
            {
                "name": "Asma",
                "category": "Pernapasan",
                "description": "Asma adalah penyakit kronis pada saluran pernapasan yang menyebabkan peradangan dan penyempitan bronkus.",
                "symptoms": "Sesak napas, mengi (napas berbunyi), batuk terutama malam hari, dada terasa berat",
                "treatment": "Hindari pemicu asma, gunakan inhaler, obat pengontrol asma, jaga kebersihan lingkungan",
                "medicines": "Salbutamol Inhaler (Ventolin), Budesonide Inhaler, Aminofilin, Theophylline",
                "image_url": "/static/images/asma.png"
            },
            {
                "name": "Tifus (Demam Tifoid)",
                "category": "Infeksi Bakteri",
                "description": "Tifus adalah infeksi bakteri Salmonella typhi yang menyerang usus dan menyebar ke seluruh tubuh melalui aliran darah.",
                "symptoms": "Demam tinggi bertahap, sakit kepala, nyeri perut, diare atau sembelit, ruam merah muda, lemas",
                "treatment": "Antibiotik sesuai resep dokter, istirahat total, makan makanan lunak, minum banyak cairan",
                "medicines": "Ciprofloxacin, Chloramphenicol, Amoxicillin (dengan resep dokter), Oralit",
                "image_url": "/static/images/tifus.png"
            },
            {
                "name": "Sakit Gigi",
                "category": "Gigi & Mulut",
                "description": "Sakit gigi adalah nyeri pada gigi atau sekitar rahang yang dapat disebabkan oleh gigi berlubang, infeksi gusi, atau kerusakan gigi.",
                "symptoms": "Nyeri gigi, gigi ngilu, bengkak gusi, sakit saat mengunyah, sensitif panas dingin, bau mulut",
                "treatment": "Kumur air garam hangat, kompres dingin, minum obat pereda nyeri, hindari makanan manis, segera ke dokter gigi",
                "medicines": "Asam Mefenamat 500mg, Ibuprofen, Paracetamol, Minyak Cengkeh, Betadine Kumur",
                "image_url": "/static/images/sakit_gigi.png"
            },
            {
                "name": "Diare",
                "category": "Pencernaan",
                "description": "Diare adalah kondisi buang air besar dengan feses encer lebih dari 3 kali sehari, sering disertai kram perut.",
                "symptoms": "BAB encer, sering ke toilet, kram perut, mual, dehidrasi, lemas",
                "treatment": "Minum oralit, hindari makanan berminyak, makan pisang dan bubur, banyak minum air putih",
                "medicines": "Oralit, Loperamide (Imodium), Entrostop, Diapet, Zinc Tablet",
                "image_url": "/static/images/diare.png"
            },
            {
                "name": "Sariawan",
                "category": "Gigi & Mulut",
                "description": "Sariawan adalah luka kecil di dalam mulut yang menyebabkan rasa perih terutama saat makan atau minum.",
                "symptoms": "Luka di mulut, perih, sulit makan, bengkak bibir bagian dalam",
                "treatment": "Oleskan obat sariawan, kumur antiseptik, makan makanan lembut, konsumsi vitamin C",
                "medicines": "Aloclair Gel, Kenalog in Orabase, Albothyl, Enkasari, Vitamin C 500mg, Vitamin B Complex",
                "image_url": "/static/images/sariawan.png"
            },
            {
                "name": "Sakit Mata (Konjungtivitis)",
                "category": "Mata",
                "description": "Konjungtivitis adalah peradangan pada selaput mata yang menyebabkan mata merah, gatal, dan berair.",
                "symptoms": "Mata merah, gatal, berair, belekan, sensitif cahaya, pandangan kabur",
                "treatment": "Kompres dingin, tetes mata, jangan mengucek mata, cuci tangan sering, hindari kontak mata",
                "medicines": "Cendo Xitrol, Tetes Mata Insto, Cendo Fenicol, Rohto Eye Drops, Visine",
                "image_url": "/static/images/sakit_mata.png"
            },
            {
                "name": "Sakit Telinga (Otitis)",
                "category": "THT",
                "description": "Otitis adalah infeksi atau peradangan pada telinga yang menyebabkan nyeri dan gangguan pendengaran.",
                "symptoms": "Nyeri telinga, pendengaran berkurang, telinga berdengung, keluar cairan, demam",
                "treatment": "Kompres hangat, obat tetes telinga, jangan mengorek telinga, segera ke dokter THT",
                "medicines": "Otopain Ear Drops, Tarivid Otic, Paracetamol, Amoxicillin (dengan resep dokter)",
                "image_url": "/static/images/sakit_telinga.png"
            },
            # === PENYAKIT PERNAPASAN ===
            {
                "name": "Bronkitis",
                "category": "Pernapasan",
                "description": "Bronkitis adalah peradangan pada saluran bronkus yang menyebabkan batuk berdahak.",
                "symptoms": "Batuk berdahak, sesak napas ringan, dada tidak nyaman, kelelahan, demam ringan",
                "treatment": "Istirahat, minum banyak air hangat, hindari asap rokok, gunakan pelembab udara",
                "medicines": "Ambroxol, OBH Combi, Woods Peppermint, Bisolvon, Vicks Formula 44",
                "image_url": "/static/images/bronkitis.png"
            },
            {
                "name": "Pneumonia",
                "category": "Pernapasan",
                "description": "Pneumonia adalah infeksi paru-paru yang menyebabkan kantung udara terisi cairan atau nanah.",
                "symptoms": "Demam tinggi, batuk berdahak, sesak napas berat, nyeri dada, menggigil",
                "treatment": "Segera ke dokter, antibiotik sesuai resep, istirahat total, oksigen jika perlu",
                "medicines": "Antibiotik (Amoxicillin, Azithromycin - HARUS resep dokter), Paracetamol",
                "image_url": "/static/images/pneumonia.png"
            },
            {
                "name": "TBC (Tuberkulosis)",
                "category": "Pernapasan",
                "description": "TBC adalah infeksi bakteri pada paru-paru yang menular melalui udara.",
                "symptoms": "Batuk lebih dari 2 minggu, batuk berdarah, keringat malam, penurunan berat badan, demam",
                "treatment": "Pengobatan 6 bulan dengan obat TBC, HARUS ke dokter dan rutin kontrol",
                "medicines": "Obat TBC (Rifampicin, Isoniazid, Ethambutol - HARUS resep dokter dan kontrol rutin)",
                "image_url": "/static/images/tbc.png"
            },
            {
                "name": "Sinusitis",
                "category": "THT",
                "description": "Sinusitis adalah peradangan pada rongga sinus yang menyebabkan hidung tersumbat dan nyeri wajah.",
                "symptoms": "Hidung tersumbat, nyeri wajah, sakit kepala, ingus kental, bau mulut",
                "treatment": "Uap air hangat, irigasi hidung dengan air garam, kompres hangat pada wajah",
                "medicines": "Pseudoephedrine (Rhinos), Nasonex Spray, Paracetamol, Amoxicillin (resep dokter)",
                "image_url": "/static/images/sinusitis.png"
            },
            {
                "name": "Radang Tenggorokan",
                "category": "THT",
                "description": "Radang tenggorokan adalah peradangan pada tenggorokan yang menyebabkan nyeri saat menelan.",
                "symptoms": "Sakit tenggorokan, sulit menelan, suara serak, demam, pembengkakan kelenjar",
                "treatment": "Kumur air garam, minum air hangat dengan madu, istirahat bicara",
                "medicines": "FG Troches, Hexadol, Betadine Gargle, Strepsils, Degirol",
                "image_url": "/static/images/radang_tenggorokan.png"
            },
            # === PENYAKIT PENCERNAAN ===
            {
                "name": "Wasir (Hemoroid)",
                "category": "Pencernaan",
                "description": "Wasir adalah pembengkakan pembuluh darah di area anus yang menyebabkan nyeri dan pendarahan.",
                "symptoms": "Nyeri saat BAB, pendarahan saat BAB, benjolan di anus, gatal, tidak nyaman duduk",
                "treatment": "Makan serat tinggi, banyak minum air, jangan terlalu lama duduk, hindari mengejan",
                "medicines": "Faktu Suppositoria, Ultraproct, Ardium, Anusol, Preparation H",
                "image_url": "/static/images/wasir.png"
            },
            {
                "name": "Sembelit (Konstipasi)",
                "category": "Pencernaan",
                "description": "Sembelit adalah kondisi sulit buang air besar dengan feses keras.",
                "symptoms": "Sulit BAB, feses keras, perut kembung, rasa tidak tuntas, kurang dari 3x BAB seminggu",
                "treatment": "Makan sayur dan buah, minum banyak air, olahraga rutin, jangan menahan BAB",
                "medicines": "Dulcolax, Microlax, Lactulax, Vegeta, Psyllium Husk",
                "image_url": "/static/images/sembelit.png"
            },
            {
                "name": "GERD (Asam Lambung)",
                "category": "Pencernaan",
                "description": "GERD adalah naiknya asam lambung ke kerongkongan yang menyebabkan rasa terbakar.",
                "symptoms": "Nyeri ulu hati, rasa terbakar di dada, mual, mulut asam, sulit menelan",
                "treatment": "Makan porsi kecil, hindari makanan pedas dan asam, jangan langsung tidur setelah makan",
                "medicines": "Omeprazole, Lansoprazole, Antasida, Sucralfate, Domperidone",
                "image_url": "/static/images/gerd.png"
            },
            {
                "name": "Hepatitis",
                "category": "Pencernaan",
                "description": "Hepatitis adalah peradangan hati yang dapat disebabkan oleh virus, alkohol, atau obat.",
                "symptoms": "Kulit dan mata menguning, urin gelap, lemas, mual, nyeri perut kanan atas",
                "treatment": "SEGERA ke dokter, istirahat total, hindari alkohol, makan bergizi",
                "medicines": "Harus konsultasi dokter - pengobatan tergantung jenis hepatitis",
                "image_url": "/static/images/hepatitis.png"
            },
            {
                "name": "Cacingan",
                "category": "Pencernaan",
                "description": "Cacingan adalah infeksi parasit cacing di usus yang sering terjadi pada anak-anak.",
                "symptoms": "Gatal di anus terutama malam, perut buncit, nafsu makan menurun, lemas",
                "treatment": "Minum obat cacing, cuci tangan sebelum makan, potong kuku, jaga kebersihan",
                "medicines": "Combantrin, Vermox, Zentel, Albendazole, Pirantel Pamoat",
                "image_url": "/static/images/cacingan.png"
            },
            # === PENYAKIT KULIT ===
            {
                "name": "Jerawat",
                "category": "Kulit",
                "description": "Jerawat adalah kondisi kulit dimana pori-pori tersumbat minyak dan sel kulit mati.",
                "symptoms": "Bintik merah, komedo, pustula bernanah, kulit berminyak, bekas hitam",
                "treatment": "Cuci muka 2x sehari, hindari pegang wajah, gunakan produk non-komedogenik",
                "medicines": "Acnes, Oxy, Vitacid Gel, Erythromycin Gel, Benzoyl Peroxide",
                "image_url": "/static/images/jerawat.png"
            },
            {
                "name": "Kudis (Scabies)",
                "category": "Kulit",
                "description": "Kudis adalah infeksi kulit oleh tungau yang menyebabkan gatal hebat terutama malam hari.",
                "symptoms": "Gatal hebat malam hari, ruam merah, lesi kulit, menyebar ke orang lain",
                "treatment": "Oleskan obat kudis, cuci semua pakaian dan sprei, obati seluruh anggota keluarga",
                "medicines": "Scabimite Cream, Permethrin 5%, Sulfur 10%, Antihistamin (CTM)",
                "image_url": "/static/images/kudis.png"
            },
            {
                "name": "Panu",
                "category": "Kulit",
                "description": "Panu adalah infeksi jamur kulit yang menyebabkan bercak putih atau coklat.",
                "symptoms": "Bercak putih/coklat, gatal ringan, kulit bersisik halus, menyebar perlahan",
                "treatment": "Jaga kulit tetap kering, gunakan obat antijamur, ganti pakaian jika berkeringat",
                "medicines": "Miconazole Cream, Ketoconazole Cream, Kalpanax, Daktarin, Canesten",
                "image_url": "/static/images/panu.png"
            },
            {
                "name": "Kurap (Tinea)",
                "category": "Kulit",
                "description": "Kurap adalah infeksi jamur kulit yang membentuk ruam melingkar bersisik.",
                "symptoms": "Ruam melingkar merah, bersisik, gatal, menyebar, tepi aktif",
                "treatment": "Jaga kebersihan kulit, keringkan dengan baik, gunakan obat antijamur rutin",
                "medicines": "Terbinafine Cream, Clotrimazole, Miconazole, Griseofulvin (resep dokter)",
                "image_url": "/static/images/kurap.png"
            },
            {
                "name": "Eksim",
                "category": "Kulit",
                "description": "Eksim adalah peradangan kulit kronis yang menyebabkan kulit kering, gatal, dan kemerahan.",
                "symptoms": "Kulit kering, gatal, kemerahan, bersisik, pecah-pecah, lepuhan kecil",
                "treatment": "Gunakan pelembab rutin, hindari sabun keras, jangan garuk, kendalikan alergen",
                "medicines": "Hidrokortison Cream, Mometason, Pelembab Cetaphil, Antihistamin",
                "image_url": "/static/images/eksim.png"
            },
            {
                "name": "Biduran (Urtikaria)",
                "category": "Kulit",
                "description": "Biduran adalah reaksi alergi kulit yang menyebabkan bentol merah gatal.",
                "symptoms": "Bentol merah, gatal hebat, bengkak tiba-tiba, berpindah lokasi",
                "treatment": "Hindari pemicu alergi, kompres dingin, minum antihistamin",
                "medicines": "Loratadine, Cetirizine, CTM, Diphenhydramine, Calamine Lotion",
                "image_url": "/static/images/biduran.png"
            },
            {
                "name": "Herpes",
                "category": "Kulit",
                "description": "Herpes adalah infeksi virus yang menyebabkan lepuhan berisi cairan pada kulit atau mulut.",
                "symptoms": "Lepuhan berkelompok, nyeri, gatal, demam, lelah",
                "treatment": "SEGERA ke dokter, jangan sentuh lesi, istirahat, hindari kontak langsung",
                "medicines": "Acyclovir (HARUS resep dokter), Paracetamol untuk demam",
                "image_url": "/static/images/herpes.png"
            },
            {
                "name": "Cacar Air",
                "category": "Kulit",
                "description": "Cacar air adalah infeksi virus varicella yang menyebabkan ruam melepuh di seluruh tubuh.",
                "symptoms": "Ruam merah berisi cairan, gatal, demam, lelah, ruam menyebar ke seluruh tubuh",
                "treatment": "Istirahat, jangan garuk, mandikan dengan air hangat, potong kuku pendek",
                "medicines": "Acyclovir (resep dokter), Calamine Lotion, Paracetamol, Bedak Salisil",
                "image_url": "/static/images/cacar_air.png"
            },
            # === PENYAKIT TULANG & OTOT ===
            {
                "name": "Rematik (Arthritis)",
                "category": "Tulang & Otot",
                "description": "Rematik adalah peradangan sendi yang menyebabkan nyeri dan kaku pada persendian.",
                "symptoms": "Nyeri sendi, kaku pagi hari, bengkak sendi, sulit bergerak, demam ringan",
                "treatment": "Kompres hangat, olahraga ringan, istirahat cukup, kurangi aktivitas berat",
                "medicines": "Piroxicam, Ibuprofen, Natrium Diklofenak, Glucosamine, Chondroitin",
                "image_url": "/static/images/rematik.png"
            },
            {
                "name": "Asam Urat (Gout)",
                "category": "Tulang & Otot",
                "description": "Asam urat adalah kondisi dimana kristal urat menumpuk di sendi menyebabkan nyeri hebat.",
                "symptoms": "Nyeri sendi mendadak, bengkak merah, biasanya di jempol kaki, nyeri malam hari",
                "treatment": "Hindari makanan tinggi purin (jeroan, seafood), minum banyak air, batasi alkohol",
                "medicines": "Allopurinol, Colchicine, Piroxicam, Ibuprofen (HARUS konsultasi dokter)",
                "image_url": "/static/images/asam_urat.png"
            },
            {
                "name": "Encok (Lumbago)",
                "category": "Tulang & Otot",
                "description": "Encok adalah nyeri pada punggung bawah yang dapat menjalar ke kaki.",
                "symptoms": "Nyeri punggung bawah, kaku, sulit berdiri, nyeri menjalar ke bokong/kaki",
                "treatment": "Istirahat, kompres hangat, tidur di kasur keras, hindari angkat berat",
                "medicines": "Paracetamol, Ibuprofen, Counterpain, Salonpas, Neurobion",
                "image_url": "/static/images/encok.png"
            },
            {
                "name": "Osteoporosis",
                "category": "Tulang & Otot",
                "description": "Osteoporosis adalah kondisi tulang menjadi rapuh dan mudah patah.",
                "symptoms": "Nyeri tulang, postur bungkuk, tulang mudah patah, tinggi badan berkurang",
                "treatment": "Konsumsi kalsium cukup, vitamin D, olahraga teratur, hindari jatuh",
                "medicines": "Suplemen Kalsium, Vitamin D3, Alendronate (resep dokter), CDR",
                "image_url": "/static/images/osteoporosis.png"
            },
            # === PENYAKIT JANTUNG & PEMBULUH DARAH ===
            {
                "name": "Kolesterol Tinggi",
                "category": "Kardiovaskular",
                "description": "Kolesterol tinggi adalah kondisi kadar lemak jahat tinggi dalam darah.",
                "symptoms": "Sering tanpa gejala, nyeri dada, sesak napas, kelelahan, xanthoma (benjolan kulit)",
                "treatment": "Diet rendah lemak, olahraga rutin, hindari gorengan, berhenti merokok",
                "medicines": "Simvastatin, Atorvastatin (HARUS resep dokter), Omega-3",
                "image_url": "/static/images/kolesterol.png"
            },
            {
                "name": "Anemia",
                "category": "Darah",
                "description": "Anemia adalah kondisi kekurangan sel darah merah atau hemoglobin.",
                "symptoms": "Pucat, lemas, pusing, jantung berdebar, sesak napas, mudah lelah",
                "treatment": "Makan makanan kaya zat besi (daging, sayur hijau), vitamin C untuk penyerapan",
                "medicines": "Sangobion, Ferrous Sulfate, Vitamin B12, Asam Folat",
                "image_url": "/static/images/anemia.png"
            },
            {
                "name": "Stroke Ringan (TIA)",
                "category": "Kardiovaskular",
                "description": "TIA adalah gangguan aliran darah ke otak yang bersifat sementara - TANDA BAHAYA STROKE.",
                "symptoms": "Lemah separuh badan, bicara pelo, wajah mencong, pandangan kabur",
                "treatment": "SEGERA ke IGD rumah sakit! Ini kondisi darurat!",
                "medicines": "HARUS penanganan dokter SEGERA - Hubungi 119 atau IGD terdekat!",
                "image_url": "/static/images/stroke.png"
            },
            # === PENYAKIT GINJAL & SALURAN KEMIH ===
            {
                "name": "ISK (Infeksi Saluran Kemih)",
                "category": "Urologi",
                "description": "ISK adalah infeksi bakteri pada saluran kemih termasuk kandung kemih.",
                "symptoms": "Nyeri saat buang air kecil, sering BAK, urin keruh atau berbau, nyeri perut bawah",
                "treatment": "Minum banyak air, jangan menahan BAK, jaga kebersihan, ke dokter untuk antibiotik",
                "medicines": "Antibiotik (Ciprofloxacin, Amoxicillin - HARUS resep dokter), Ural",
                "image_url": "/static/images/isk.png"
            },
            {
                "name": "Batu Ginjal",
                "category": "Urologi",
                "description": "Batu ginjal adalah endapan mineral keras di ginjal atau saluran kemih.",
                "symptoms": "Nyeri pinggang hebat, nyeri menjalar ke selangkangan, mual, darah di urin",
                "treatment": "Minum banyak air (2-3 liter/hari), SEGERA ke dokter untuk evaluasi",
                "medicines": "Perlu evaluasi dokter - tergantung ukuran batu (obat atau operasi)",
                "image_url": "/static/images/batu_ginjal.png"
            },
            # === PENYAKIT SARAF ===
            {
                "name": "Epilepsi (Ayan)",
                "category": "Neurologis",
                "description": "Epilepsi adalah gangguan sistem saraf yang menyebabkan kejang berulang.",
                "symptoms": "Kejang, kehilangan kesadaran, gerakan tidak terkontrol, bingung setelah kejang",
                "treatment": "Minum obat teratur, hindari pemicu, tidur cukup, HARUS kontrol rutin ke dokter saraf",
                "medicines": "Phenytoin, Carbamazepine, Asam Valproat (HARUS resep dokter saraf)",
                "image_url": "/static/images/epilepsi.png"
            },
            {
                "name": "Bell's Palsy",
                "category": "Neurologis",
                "description": "Bell's Palsy adalah kelumpuhan wajah sementara akibat peradangan saraf wajah.",
                "symptoms": "Wajah mencong sebelah, tidak bisa menutup mata, mulut tertarik, sulit bicara",
                "treatment": "SEGERA ke dokter saraf dalam 72 jam pertama untuk hasil terbaik",
                "medicines": "Kortikosteroid, Acyclovir (HARUS resep dokter, makin cepat makin baik)",
                "image_url": "/static/images/bells_palsy.png"
            },
            # === PENYAKIT MENTAL ===
            {
                "name": "Kecemasan (Anxiety)",
                "category": "Mental",
                "description": "Anxiety adalah gangguan kecemasan berlebihan yang mengganggu aktivitas sehari-hari.",
                "symptoms": "Cemas berlebihan, jantung berdebar, sulit tidur, gelisah, tegang otot",
                "treatment": "Latihan pernapasan, olahraga, kurangi kafein, konsultasi psikolog/psikiater",
                "medicines": "Konsultasi dokter jiwa/psikiater untuk penanganan yang tepat",
                "image_url": "/static/images/anxiety.png"
            },
            {
                "name": "Depresi",
                "category": "Mental",
                "description": "Depresi adalah gangguan mood yang menyebabkan perasaan sedih berkepanjangan.",
                "symptoms": "Sedih berkepanjangan, kehilangan minat, gangguan tidur, lelah, pikiran negatif",
                "treatment": "Jangan dipendam sendiri - bicara dengan orang terdekat, konsultasi psikolog/psikiater",
                "medicines": "HARUS konsultasi psikiater - butuh penanganan profesional",
                "image_url": "/static/images/depresi.png"
            },
            {
                "name": "Insomnia",
                "category": "Mental",
                "description": "Insomnia adalah gangguan tidur berupa sulit tidur atau tidak bisa tidur nyenyak.",
                "symptoms": "Sulit tidur, bangun tengah malam, tidak segar saat bangun, mengantuk siang",
                "treatment": "Atur jadwal tidur, hindari gadget sebelum tidur, ruangan gelap dan sejuk",
                "medicines": "Lelap, Melatonin (jangka pendek), konsultasi dokter jika berlanjut",
                "image_url": "/static/images/insomnia.png"
            },
            # === PENYAKIT LAINNYA ===
            {
                "name": "Alergi Makanan",
                "category": "Alergi",
                "description": "Alergi makanan adalah reaksi sistem imun berlebihan terhadap makanan tertentu.",
                "symptoms": "Gatal kulit, bengkak bibir/lidah, mual, diare, sesak napas (berat)",
                "treatment": "Hindari makanan pemicu, bawa obat alergi, segera ke IGD jika sesak napas",
                "medicines": "Loratadine, Cetirizine, CTM, Epinefrin (untuk reaksi berat - IGD)",
                "image_url": "/static/images/alergi_makanan.png"
            },
            {
                "name": "DBD (Demam Berdarah)",
                "category": "Infeksi Virus",
                "description": "DBD adalah infeksi virus dengue melalui gigitan nyamuk Aedes aegypti.",
                "symptoms": "Demam tinggi mendadak, nyeri belakang mata, nyeri otot, bintik merah, mimisan",
                "treatment": "SEGERA ke dokter untuk cek trombosit, banyak minum, istirahat total",
                "medicines": "Paracetamol saja (JANGAN Ibuprofen/Aspirin), oralit, HARUS kontrol dokter",
                "image_url": "/static/images/dbd.png"
            },
            {
                "name": "Malaria",
                "category": "Infeksi Parasit",
                "description": "Malaria adalah infeksi parasit melalui gigitan nyamuk Anopheles.",
                "symptoms": "Demam tinggi berulang, menggigil, keringat, sakit kepala, lemas",
                "treatment": "SEGERA ke dokter untuk pemeriksaan darah dan pengobatan malaria",
                "medicines": "Obat antimalaria (HARUS resep dokter setelah konfirmasi lab)",
                "image_url": "/static/images/malaria.png"
            },
            {
                "name": "Chikungunya",
                "category": "Infeksi Virus",
                "description": "Chikungunya adalah infeksi virus melalui gigitan nyamuk yang menyebabkan nyeri sendi hebat.",
                "symptoms": "Demam tinggi, nyeri sendi hebat, ruam kulit, sakit kepala, lemas",
                "treatment": "Istirahat total, banyak minum, obat pereda nyeri, kompres hangat pada sendi",
                "medicines": "Paracetamol, Ibuprofen untuk nyeri sendi, tidak ada antivirus khusus",
                "image_url": "/static/images/chikungunya.png"
            },
            {
                "name": "Gondok (Mumps)",
                "category": "Infeksi Virus",
                "description": "Gondok adalah infeksi virus yang menyebabkan pembengkakan kelenjar liur.",
                "symptoms": "Bengkak di bawah telinga/rahang, nyeri saat mengunyah, demam, lemas",
                "treatment": "Istirahat, kompres dingin, makan makanan lembut, hindari asam",
                "medicines": "Paracetamol untuk nyeri dan demam, banyak minum",
                "image_url": "/static/images/gondok.png"
            },
            {
                "name": "Campak",
                "category": "Infeksi Virus",
                "description": "Campak adalah infeksi virus yang sangat menular dengan ruam khas di seluruh tubuh.",
                "symptoms": "Demam tinggi, ruam merah menyebar, batuk, pilek, mata merah, bercak Koplik",
                "treatment": "Istirahat total, banyak minum, vitamin A, isolasi untuk cegah penularan",
                "medicines": "Paracetamol, Vitamin A dosis tinggi, tidak ada antivirus khusus",
                "image_url": "/static/images/campak.png"
            },
            {
                "name": "Keracunan Makanan",
                "category": "Pencernaan",
                "description": "Keracunan makanan adalah penyakit akibat mengonsumsi makanan terkontaminasi.",
                "symptoms": "Mual, muntah, diare, kram perut, demam, lemas",
                "treatment": "Banyak minum oralit, istirahat, makan bertahap, ke dokter jika parah",
                "medicines": "Oralit, Norit (karbon aktif), Attapulgite, ke IGD jika dehidrasi berat",
                "image_url": "/static/images/keracunan.png"
            },
            {
                "name": "Kolik (Bayi Menangis)",
                "category": "Pediatrik",
                "description": "Kolik adalah kondisi bayi menangis berlebihan tanpa penyebab jelas.",
                "symptoms": "Bayi menangis lebih dari 3 jam sehari, wajah merah, kaki ditekuk ke perut",
                "treatment": "Gendong dan ayun pelan, pijat perut, suara white noise, posisi tegak setelah menyusu",
                "medicines": "Simethicone drops (Mylicon), konsultasi dokter anak jika berlanjut",
                "image_url": "/static/images/kolik.png"
            },
            {
                "name": "Ruam Popok",
                "category": "Pediatrik",
                "description": "Ruam popok adalah iritasi kulit bayi di area popok akibat kelembaban.",
                "symptoms": "Kulit merah di area popok, bintik merah, bayi rewel saat diganti popok",
                "treatment": "Ganti popok sering, biarkan kulit terpapar udara, gunakan krim barrier",
                "medicines": "Bepanthen, Zwitsal Baby Cream, Desitin, tepung maizena",
                "image_url": "/static/images/ruam_popok.png"
            },
            # === PENYAKIT INFEKSI VIRUS BARU ===
            {
                "name": "COVID-19",
                "category": "Infeksi Virus",
                "description": "COVID-19 adalah penyakit pernapasan yang disebabkan oleh virus SARS-CoV-2.",
                "symptoms": "Demam, batuk kering, kelelahan, kehilangan penciuman/pengecapan, sesak napas, nyeri otot",
                "treatment": "Isolasi mandiri, istirahat, minum banyak cairan, pantau saturasi oksigen, segera ke RS jika sesak berat",
                "medicines": "Paracetamol, Vitamin C, D, Zinc, Antivirus (jika diresepkan dokter)",
                "image_url": "/static/images/covid19.png"
            },
            {
                "name": "Rubella (Campak Jerman)",
                "category": "Infeksi Virus",
                "description": "Rubella adalah infeksi virus yang menyebabkan ruam merah dan berbahaya bagi ibu hamil.",
                "symptoms": "Ruam merah mulai dari wajah, demam ringan, pembengkakan kelenjar getah bening, nyeri sendi",
                "treatment": "Istirahat, obat pereda demam, SANGAT BERBAHAYA untuk ibu hamil - segera ke dokter",
                "medicines": "Paracetamol untuk demam, pencegahan dengan vaksin MMR",
                "image_url": "/static/images/rubella.png"
            },
            {
                "name": "Herpes Zoster (Cacar Ular)",
                "category": "Infeksi Virus",
                "description": "Herpes zoster adalah reaktivasi virus varicella yang menyebabkan ruam nyeri di satu sisi tubuh.",
                "symptoms": "Nyeri terbakar pada kulit, ruam melepuh mengikuti saraf, gatal, demam, sensitif sentuhan",
                "treatment": "Segera ke dokter dalam 72 jam untuk antivirus, kompres dingin, jaga kebersihan lesi",
                "medicines": "Acyclovir/Valacyclovir (HARUS resep dokter), Gabapentin untuk nyeri saraf",
                "image_url": "/static/images/herpes_zoster.png"
            },
            {
                "name": "Mononukleosis (Kissing Disease)",
                "category": "Infeksi Virus",
                "description": "Mononukleosis adalah infeksi virus Epstein-Barr yang menyebabkan kelelahan ekstrem.",
                "symptoms": "Kelelahan ekstrem, demam, sakit tenggorokan parah, pembengkakan kelenjar, pembesaran limpa",
                "treatment": "Istirahat total (bisa berminggu-minggu), hindari olahraga berat, minum banyak cairan",
                "medicines": "Paracetamol/Ibuprofen untuk demam dan nyeri, tidak ada antivirus khusus",
                "image_url": "/static/images/mono.png"
            },
            # === PENYAKIT KARDIOVASKULAR BARU ===
            {
                "name": "Aritmia (Gangguan Irama Jantung)",
                "category": "Kardiovaskular",
                "description": "Aritmia adalah kondisi dimana jantung berdetak tidak teratur, terlalu cepat, atau terlalu lambat.",
                "symptoms": "Jantung berdebar kencang, detak jantung tidak teratur, pusing, sesak napas, nyeri dada",
                "treatment": "Segera ke dokter jantung, hindari kafein dan alkohol, kelola stres",
                "medicines": "Beta blocker, Antiaritmia (HARUS resep dokter spesialis jantung)",
                "image_url": "/static/images/aritmia.png"
            },
            {
                "name": "Gagal Jantung",
                "category": "Kardiovaskular",
                "description": "Gagal jantung adalah kondisi dimana jantung tidak dapat memompa darah dengan efektif.",
                "symptoms": "Sesak napas saat aktivitas/berbaring, kaki bengkak, kelelahan, batuk malam hari",
                "treatment": "HARUS kontrol rutin ke dokter jantung, batasi garam dan cairan, minum obat teratur",
                "medicines": "ACE inhibitor, Diuretik, Beta blocker (HARUS resep dan kontrol dokter spesialis)",
                "image_url": "/static/images/gagal_jantung.png"
            },
            {
                "name": "Penyakit Jantung Koroner",
                "category": "Kardiovaskular",
                "description": "Penyakit jantung koroner adalah penyempitan pembuluh darah jantung akibat plak.",
                "symptoms": "Nyeri dada saat aktivitas (angina), sesak napas, kelelahan, nyeri menjalar ke lengan/rahang",
                "treatment": "Segera ke dokter jantung, diet rendah lemak, olahraga teratur, berhenti merokok",
                "medicines": "Aspirin, Statin, Nitrat (HARUS resep dan pemantauan dokter)",
                "image_url": "/static/images/jantung_koroner.png"
            },
            {
                "name": "Serangan Jantung (DARURAT)",
                "category": "Darurat",
                "description": "Serangan jantung adalah kondisi darurat dimana aliran darah ke jantung terhenti mendadak.",
                "symptoms": "Nyeri dada hebat seperti ditekan, menjalar ke lengan kiri/rahang, keringat dingin, mual, sesak",
                "treatment": "SEGERA HUBUNGI 119! Kunyah Aspirin jika tersedia, jangan beraktivitas, tunggu ambulans",
                "medicines": "DARURAT - Butuh penanganan IGD segera! Hubungi 119 atau bawa ke IGD terdekat!",
                "image_url": "/static/images/serangan_jantung.png"
            },
            # === PENYAKIT NEUROLOGIS BARU ===
            {
                "name": "Parkinson",
                "category": "Neurologis",
                "description": "Parkinson adalah gangguan saraf progresif yang mempengaruhi gerakan tubuh.",
                "symptoms": "Tremor/gemetar tangan, kekakuan otot, gerakan lambat, gangguan keseimbangan, wajah datar",
                "treatment": "Kontrol rutin ke dokter saraf, fisioterapi, olahraga teratur, dukungan keluarga",
                "medicines": "Levodopa, Dopamine agonist (HARUS resep dokter saraf)",
                "image_url": "/static/images/parkinson.png"
            },
            {
                "name": "Alzheimer",
                "category": "Neurologis",
                "description": "Alzheimer adalah penyakit otak progresif yang menyebabkan penurunan daya ingat dan fungsi kognitif.",
                "symptoms": "Lupa kejadian baru, kesulitan menyelesaikan tugas familiar, bingung waktu/tempat, perubahan mood",
                "treatment": "Konsultasi dokter saraf, stimulasi mental, dukungan keluarga, lingkungan aman",
                "medicines": "Donepezil, Memantine (HARUS resep dokter saraf, tidak menyembuhkan tapi memperlambat)",
                "image_url": "/static/images/alzheimer.png"
            },
            {
                "name": "Meningitis",
                "category": "Neurologis",
                "description": "Meningitis adalah peradangan selaput otak dan sumsum tulang belakang yang mengancam jiwa.",
                "symptoms": "Demam tinggi, sakit kepala hebat, leher kaku, mual muntah, sensitif cahaya, kebingungan",
                "treatment": "DARURAT! Segera ke IGD, butuh antibiotik/antivirus IV, rawat inap intensif",
                "medicines": "DARURAT - Antibiotik IV di rumah sakit (Ceftriaxone, Vancomycin)",
                "image_url": "/static/images/meningitis.png"
            },
            {
                "name": "Neuropati (Kerusakan Saraf)",
                "category": "Neurologis",
                "description": "Neuropati adalah kerusakan saraf tepi yang menyebabkan nyeri, kesemutan, atau mati rasa.",
                "symptoms": "Kesemutan, mati rasa, nyeri seperti terbakar, lemah otot, sensitivitas berlebihan",
                "treatment": "Konsultasi dokter saraf, kontrol penyebab (diabetes), terapi fisik",
                "medicines": "Gabapentin, Pregabalin, Vitamin B kompleks (resep dokter)",
                "image_url": "/static/images/neuropati.png"
            },
            # === PENYAKIT MATA BARU ===
            {
                "name": "Katarak",
                "category": "Mata",
                "description": "Katarak adalah kekeruhan lensa mata yang menyebabkan penglihatan kabur.",
                "symptoms": "Penglihatan kabur seperti berkabut, sensitif silau, warna memudar, sulit melihat malam",
                "treatment": "Konsultasi dokter mata, operasi katarak jika sudah mengganggu aktivitas",
                "medicines": "Tidak ada obat - pengobatan dengan operasi penggantian lensa",
                "image_url": "/static/images/katarak.png"
            },
            {
                "name": "Glaukoma",
                "category": "Mata",
                "description": "Glaukoma adalah kerusakan saraf mata akibat tekanan tinggi yang dapat menyebabkan kebutaan.",
                "symptoms": "Penglihatan tepi menyempit, nyeri mata, mual, melihat lingkaran cahaya, mata merah",
                "treatment": "Segera ke dokter mata! Kontrol rutin, tetes mata penurun tekanan, mungkin perlu operasi",
                "medicines": "Tetes mata Timolol, Latanoprost (HARUS resep dokter mata)",
                "image_url": "/static/images/glaukoma.png"
            },
            {
                "name": "Rabun Jauh (Miopia)",
                "category": "Mata",
                "description": "Rabun jauh adalah kondisi dimana objek jauh terlihat buram tetapi objek dekat terlihat jelas.",
                "symptoms": "Sulit melihat jauh, sering memicingkan mata, sakit kepala, mata lelah",
                "treatment": "Periksa ke dokter mata, gunakan kacamata/lensa kontak, batasi screen time",
                "medicines": "Kacamata koreksi, Lensa kontak, LASIK (untuk kasus tertentu)",
                "image_url": "/static/images/miopia.png"
            },
            {
                "name": "Rabun Dekat (Hipermetropia)",
                "category": "Mata",
                "description": "Rabun dekat adalah kondisi dimana objek dekat terlihat buram tetapi objek jauh terlihat jelas.",
                "symptoms": "Sulit melihat dekat/membaca, mata cepat lelah saat membaca, sakit kepala",
                "treatment": "Periksa ke dokter mata, gunakan kacamata baca",
                "medicines": "Kacamata koreksi plus, Lensa kontak",
                "image_url": "/static/images/hipermetropia.png"
            },
            {
                "name": "Mata Kering",
                "category": "Mata",
                "description": "Mata kering adalah kondisi dimana mata tidak memproduksi cukup air mata.",
                "symptoms": "Mata terasa kering, perih, gatal, merah, sensitif cahaya, penglihatan kabur sesaat",
                "treatment": "Gunakan tetes mata pelembab, istirahatkan mata dari layar, gunakan pelembab udara",
                "medicines": "Insto Dry Eyes, Cendo Lyteers, Refresh Tears, Systane",
                "image_url": "/static/images/mata_kering.png"
            },
            # === PENYAKIT GIZI & METABOLIK BARU ===
            {
                "name": "Obesitas",
                "category": "Metabolik",
                "description": "Obesitas adalah kondisi kelebihan berat badan dengan BMI di atas 30.",
                "symptoms": "Berat badan berlebih, sulit beraktivitas, sesak napas, nyeri sendi, gangguan tidur",
                "treatment": "Diet seimbang, olahraga teratur, konsultasi ahli gizi, evaluasi penyebab",
                "medicines": "Konsultasi dokter - program diet, Orlistat (resep dokter), evaluasi hormonal",
                "image_url": "/static/images/obesitas.png"
            },
            {
                "name": "Malnutrisi (Kurang Gizi)",
                "category": "Gizi",
                "description": "Malnutrisi adalah kondisi kekurangan nutrisi penting yang dibutuhkan tubuh.",
                "symptoms": "Berat badan rendah, lemas, mudah sakit, pertumbuhan terhambat (anak), rambut rontok",
                "treatment": "Konsultasi ahli gizi, makan makanan bergizi seimbang, suplemen jika perlu",
                "medicines": "Multivitamin, Suplemen zat besi, Vitamin A, program PMT (Pemberian Makanan Tambahan)",
                "image_url": "/static/images/malnutrisi.png"
            },
            {
                "name": "Hipotiroid",
                "category": "Metabolik",
                "description": "Hipotiroid adalah kondisi kelenjar tiroid tidak memproduksi cukup hormon tiroid.",
                "symptoms": "Kelelahan, berat badan naik, sensitif dingin, kulit kering, sembelit, depresi",
                "treatment": "Konsultasi dokter endokrin, terapi hormon tiroid seumur hidup",
                "medicines": "Levothyroxine/Euthyrox (HARUS resep dokter, dosis disesuaikan)",
                "image_url": "/static/images/hipotiroid.png"
            },
            {
                "name": "Hipertiroid",
                "category": "Metabolik",
                "description": "Hipertiroid adalah kondisi kelenjar tiroid memproduksi hormon berlebihan.",
                "symptoms": "Penurunan berat badan, jantung berdebar, gelisah, tremor tangan, sensitif panas, diare",
                "treatment": "Konsultasi dokter endokrin, obat antitiroid, terapi radioiodine atau operasi",
                "medicines": "PTU, Methimazole (HARUS resep dokter spesialis)",
                "image_url": "/static/images/hipertiroid.png"
            },
            # === PENYAKIT PEDIATRIK BARU ===
            {
                "name": "Hand Foot Mouth Disease (HFMD)",
                "category": "Pediatrik",
                "description": "HFMD adalah infeksi virus pada anak yang menyebabkan luka di mulut, tangan, dan kaki.",
                "symptoms": "Demam, luka di mulut, ruam merah di telapak tangan/kaki, tidak mau makan, rewel",
                "treatment": "Istirahat, banyak minum, makanan lembut, obat pereda nyeri, isolasi untuk cegah penularan",
                "medicines": "Paracetamol untuk demam, gel mulut untuk sariawan, banyak cairan",
                "image_url": "/static/images/hfmd.png"
            },
            {
                "name": "Batuk Rejan (Pertusis)",
                "category": "Pediatrik",
                "description": "Batuk rejan adalah infeksi bakteri yang menyebabkan batuk parah berkepanjangan.",
                "symptoms": "Batuk keras beruntun dengan whoop, muntah setelah batuk, wajah merah/biru saat batuk",
                "treatment": "Segera ke dokter untuk antibiotik, isolasi, rawat inap jika bayi",
                "medicines": "Azithromycin, Erythromycin (HARUS resep dokter, makin cepat makin baik)",
                "image_url": "/static/images/batuk_rejan.png"
            },
            {
                "name": "Demam Scarlet",
                "category": "Pediatrik",
                "description": "Demam scarlet adalah infeksi bakteri streptokokus yang menyebabkan ruam merah.",
                "symptoms": "Demam tinggi, ruam merah seperti amplas, lidah stroberi, sakit tenggorokan",
                "treatment": "Segera ke dokter untuk antibiotik, istirahat, banyak minum",
                "medicines": "Penisilin atau Amoxicillin (HARUS resep dokter)",
                "image_url": "/static/images/scarlet_fever.png"
            },
            # === PENYAKIT KESEHATAN WANITA ===
            {
                "name": "PCOS (Polycystic Ovary Syndrome)",
                "category": "Kesehatan Wanita",
                "description": "PCOS adalah gangguan hormonal pada wanita yang mempengaruhi ovarium.",
                "symptoms": "Haid tidak teratur, jerawat berlebihan, berat badan naik, sulit hamil, rambut tumbuh berlebihan",
                "treatment": "Konsultasi dokter kandungan, diet sehat, olahraga teratur, kelola stres",
                "medicines": "Pil KB untuk mengatur haid, Metformin (HARUS resep dokter SpOG)",
                "image_url": "/static/images/pcos.png"
            },
            {
                "name": "Endometriosis",
                "category": "Kesehatan Wanita",
                "description": "Endometriosis adalah kondisi dimana jaringan rahim tumbuh di luar rahim.",
                "symptoms": "Nyeri haid hebat, nyeri saat berhubungan, nyeri panggul kronis, sulit hamil",
                "treatment": "Konsultasi dokter kandungan, terapi hormonal, operasi jika perlu",
                "medicines": "Obat anti nyeri, Pil KB, GnRH agonist (HARUS resep SpOG)",
                "image_url": "/static/images/endometriosis.png"
            },
            {
                "name": "Mastitis",
                "category": "Kesehatan Wanita",
                "description": "Mastitis adalah infeksi payudara yang sering terjadi pada ibu menyusui.",
                "symptoms": "Payudara bengkak, merah, nyeri, demam, menggigil, seperti flu",
                "treatment": "Tetap menyusui/pompa ASI, kompres hangat, istirahat, ke dokter untuk antibiotik",
                "medicines": "Paracetamol, Ibuprofen, Antibiotik (resep dokter jika infeksi berat)",
                "image_url": "/static/images/mastitis.png"
            },
            {
                "name": "Pre-eklampsia (Kehamilan)",
                "category": "Darurat",
                "description": "Pre-eklampsia adalah tekanan darah tinggi pada kehamilan yang mengancam ibu dan janin.",
                "symptoms": "Tekanan darah tinggi, protein di urin, bengkak wajah/tangan, sakit kepala hebat, pandangan kabur",
                "treatment": "SEGERA ke dokter kandungan/IGD! Butuh pemantauan ketat, mungkin perlu melahirkan dini",
                "medicines": "DARURAT KEHAMILAN - Butuh penanganan dokter SpOG segera!",
                "image_url": "/static/images/preeklampsia.png"
            },
            # === PENYAKIT UROLOGI BARU ===
            {
                "name": "Pembesaran Prostat (BPH)",
                "category": "Urologi",
                "description": "BPH adalah pembesaran kelenjar prostat yang umum pada pria lanjut usia.",
                "symptoms": "Sulit mulai buang air kecil, aliran lemah, sering BAK malam, rasa tidak tuntas",
                "treatment": "Konsultasi dokter urologi, kurangi kafein dan alkohol, jangan menahan BAK",
                "medicines": "Tamsulosin, Finasteride (HARUS resep dokter urologi)",
                "image_url": "/static/images/bph.png"
            },
            {
                "name": "Inkontinensia Urin",
                "category": "Urologi",
                "description": "Inkontinensia adalah ketidakmampuan menahan buang air kecil.",
                "symptoms": "Tidak bisa menahan BAK, BAK saat batuk/bersin, sering BAK, BAK mendesak",
                "treatment": "Latihan otot panggul (Kegel), konsultasi dokter urologi, terapi perilaku",
                "medicines": "Konsultasi dokter - perlu evaluasi penyebab, mungkin perlu obat atau fisioterapi",
                "image_url": "/static/images/inkontinensia.png"
            },
            # === PENYAKIT LAINNYA ===
            {
                "name": "Batu Empedu",
                "category": "Pencernaan",
                "description": "Batu empedu adalah endapan keras di kantung empedu yang menyebabkan nyeri perut.",
                "symptoms": "Nyeri perut kanan atas mendadak, mual muntah, nyeri setelah makan berlemak, demam",
                "treatment": "Konsultasi dokter bedah, diet rendah lemak, mungkin perlu operasi",
                "medicines": "Obat pereda nyeri, operasi pengangkatan kantung empedu (laparoskopi)",
                "image_url": "/static/images/batu_empedu.png"
            },
            {
                "name": "Hernia",
                "category": "Bedah",
                "description": "Hernia adalah kondisi organ tubuh menonjol melalui dinding otot yang melemah.",
                "symptoms": "Benjolan di perut/selangkangan, nyeri saat angkat beban, rasa berat, benjolan membesar",
                "treatment": "Konsultasi dokter bedah, hindari angkat berat, operasi untuk perbaikan",
                "medicines": "Pengobatan utama adalah operasi - konsultasi dokter bedah",
                "image_url": "/static/images/hernia.png"
            },
            {
                "name": "Varises",
                "category": "Kardiovaskular",
                "description": "Varises adalah pembengkakan dan pelebaran pembuluh darah vena, biasanya di kaki.",
                "symptoms": "Vena menonjol kebiru-biruan, kaki berat/pegal, gatal, kram malam hari",
                "treatment": "Elevasi kaki, kompresi stocking, jangan berdiri lama, olahraga ringan",
                "medicines": "Diosmin/Hesperidin (Ardium), Stoking kompresi, skleroterapi jika parah",
                "image_url": "/static/images/varises.png"
            },
            {
                "name": "Fibromialgia",
                "category": "Tulang & Otot",
                "description": "Fibromialgia adalah kondisi nyeri kronis di seluruh tubuh dengan kelelahan.",
                "symptoms": "Nyeri seluruh tubuh, kelelahan ekstrem, gangguan tidur, kabut otak, nyeri titik tender",
                "treatment": "Konsultasi dokter, olahraga teratur, manajemen stres, terapi kognitif",
                "medicines": "Pregabalin, Duloxetine (HARUS resep dokter)",
                "image_url": "/static/images/fibromialgia.png"
            },
            {
                "name": "Syok Anafilaksis (DARURAT)",
                "category": "Darurat",
                "description": "Anafilaksis adalah reaksi alergi berat yang mengancam jiwa.",
                "symptoms": "Sesak napas mendadak, bengkak wajah/tenggorokan, tekanan darah turun, gatal hebat, pingsan",
                "treatment": "DARURAT! Hubungi 119, suntik Epinefrin jika tersedia, baringkan dengan kaki diangkat",
                "medicines": "Epinefrin/Adrenalin injeksi (EpiPen) - SEGERA ke IGD!",
                "image_url": "/static/images/anafilaksis.png"
            },
            {
                "name": "Ketoasidosis Diabetik (DARURAT)",
                "category": "Darurat",
                "description": "Ketoasidosis adalah komplikasi diabetes berat yang mengancam jiwa.",
                "symptoms": "Mual muntah, nyeri perut, napas bau buah, lemas berat, bingung, dehidrasi berat",
                "treatment": "SEGERA ke IGD! Butuh cairan IV dan insulin, rawat ICU",
                "medicines": "DARURAT - Butuh penanganan IGD dengan insulin IV dan cairan!",
                "image_url": "/static/images/ketoasidosis.png"
            },
            {
                "name": "Apendiksitis (Usus Buntu)",
                "category": "Darurat",
                "description": "Apendiksitis adalah peradangan usus buntu yang memerlukan operasi darurat.",
                "symptoms": "Nyeri perut kanan bawah, mual muntah, demam, nyeri makin berat saat bergerak",
                "treatment": "SEGERA ke IGD! Butuh operasi pengangkatan usus buntu",
                "medicines": "DARURAT BEDAH - Butuh operasi segera, jangan minum obat pereda nyeri dulu!",
                "image_url": "/static/images/apendiksitis.png"
            },
            {
                "name": "Psoriasis",
                "category": "Kulit",
                "description": "Psoriasis adalah penyakit autoimun kulit yang menyebabkan plak bersisik.",
                "symptoms": "Plak merah bersisik putih, gatal, kulit kering pecah, nyeri, kuku berlubang",
                "treatment": "Konsultasi dokter kulit, pelembab rutin, terapi cahaya, kelola stres",
                "medicines": "Krim kortikosteroid, Calcipotriol, Methotrexate (HARUS resep dokter kulit)",
                "image_url": "/static/images/psoriasis.png"
            },
            {
                "name": "Lupus (SLE)",
                "category": "Autoimun",
                "description": "Lupus adalah penyakit autoimun yang dapat menyerang berbagai organ tubuh.",
                "symptoms": "Ruam kupu-kupu di wajah, nyeri sendi, kelelahan, demam, sensitif matahari",
                "treatment": "Konsultasi dokter reumatologi, hindari sinar matahari, kontrol rutin",
                "medicines": "Hydroxychloroquine, Kortikosteroid, Imunosupresan (HARUS resep dokter spesialis)",
                "image_url": "/static/images/lupus.png"
            },
            {
                "name": "Alergi Musiman (Rhinitis Alergi)",
                "category": "Alergi",
                "description": "Rhinitis alergi adalah reaksi alergi pada hidung terhadap serbuk sari atau alergen lain.",
                "symptoms": "Bersin-bersin, hidung gatal dan berair, mata gatal, hidung tersumbat",
                "treatment": "Hindari alergen, gunakan masker, bersihkan rumah, antihistamin",
                "medicines": "Cetirizine, Loratadine, Flixonase Nasal Spray, Tetes mata antihistamin",
                "image_url": "/static/images/rhinitis_alergi.png"
            },
            {
                "name": "Gangguan Panik",
                "category": "Mental",
                "description": "Gangguan panik adalah serangan kecemasan intens yang terjadi mendadak.",
                "symptoms": "Jantung berdebar kencang, sesak napas, gemetar, keringat, takut mati, pusing",
                "treatment": "Latihan pernapasan, terapi kognitif perilaku, konsultasi psikiater",
                "medicines": "SSRI, Benzodiazepin (HARUS resep psikiater)",
                "image_url": "/static/images/panik.png"
            },
            {
                "name": "Gangguan Bipolar",
                "category": "Mental",
                "description": "Bipolar adalah gangguan mood dengan episode mania dan depresi bergantian.",
                "symptoms": "Episode sangat bersemangat (mania), episode sangat sedih (depresi), perubahan tidur dan energi",
                "treatment": "HARUS konsultasi psikiater, terapi rutin, dukungan keluarga",
                "medicines": "Mood stabilizer, Antipsikotik (HARUS resep dan kontrol psikiater)",
                "image_url": "/static/images/bipolar.png"
            }
        ]
        
        for disease_data in diseases_data:
            disease = Disease(**disease_data)
            db.add(disease)
        db.commit()

# ==========================================
# 3.1 SEED DATA OBAT (BARU)
# ==========================================
def seed_medicines(db: Session):
    if db.query(Medicine).count() == 0:
        medicines_data = [
            # Obat Demam & Flu
            {"name": "Paracetamol 500mg", "description": "Obat penurun demam dan pereda nyeri", "category": "Analgesik", "price": 5000, "stock": 200},
            {"name": "Ibuprofen 400mg", "description": "Anti-inflamasi dan pereda nyeri", "category": "Anti-inflamasi", "price": 8000, "stock": 150},
            {"name": "Sanmol Tablet", "description": "Paracetamol untuk dewasa", "category": "Analgesik", "price": 12000, "stock": 100},
            {"name": "Tempra Syrup", "description": "Paracetamol sirup untuk anak", "category": "Analgesik", "price": 35000, "stock": 80},
            {"name": "Decolgen", "description": "Obat flu dan pilek", "category": "Flu", "price": 15000, "stock": 120},
            {"name": "Bodrex Flu & Batuk", "description": "Meredakan gejala flu dan batuk", "category": "Flu", "price": 18000, "stock": 100},
            {"name": "Neozep Forte", "description": "Obat flu dan hidung tersumbat", "category": "Flu", "price": 20000, "stock": 90},
            {"name": "Panadol Cold & Flu", "description": "Meredakan demam dan gejala flu", "category": "Flu", "price": 25000, "stock": 85},
            
            # Obat Pencernaan
            {"name": "Promag Tablet", "description": "Obat maag dan asam lambung", "category": "Pencernaan", "price": 8000, "stock": 200},
            {"name": "Mylanta Syrup", "description": "Antasida cair untuk maag", "category": "Pencernaan", "price": 35000, "stock": 100},
            {"name": "Polysilane", "description": "Obat kembung dan maag", "category": "Pencernaan", "price": 28000, "stock": 90},
            {"name": "Omeprazole 20mg", "description": "Menurunkan produksi asam lambung", "category": "Pencernaan", "price": 15000, "stock": 120},
            {"name": "Oralit", "description": "Larutan rehidrasi untuk diare", "category": "Pencernaan", "price": 3000, "stock": 300},
            {"name": "Entrostop", "description": "Obat diare untuk dewasa", "category": "Pencernaan", "price": 12000, "stock": 150},
            {"name": "Diapet", "description": "Obat diare herbal", "category": "Pencernaan", "price": 10000, "stock": 130},
            
            # Obat Sakit Kepala
            {"name": "Panadol Extra", "description": "Pereda sakit kepala ekstra kuat", "category": "Analgesik", "price": 18000, "stock": 100},
            {"name": "Saridon", "description": "Obat sakit kepala triple action", "category": "Analgesik", "price": 15000, "stock": 110},
            {"name": "Bodrexin", "description": "Pereda nyeri dan demam", "category": "Analgesik", "price": 8000, "stock": 150},
            {"name": "Paramex", "description": "Obat sakit kepala", "category": "Analgesik", "price": 10000, "stock": 140},
            
            # Obat Alergi & Kulit
            {"name": "Cetirizine 10mg", "description": "Antihistamin untuk alergi", "category": "Alergi", "price": 5000, "stock": 180},
            {"name": "Loratadine 10mg", "description": "Antihistamin non-kantuk", "category": "Alergi", "price": 8000, "stock": 160},
            {"name": "CTM 4mg", "description": "Chlorpheniramine antihistamin", "category": "Alergi", "price": 3000, "stock": 200},
            {"name": "Hydrocortisone Cream", "description": "Krim anti gatal dan radang", "category": "Kulit", "price": 25000, "stock": 80},
            {"name": "Calamine Lotion", "description": "Mengurangi gatal dan iritasi kulit", "category": "Kulit", "price": 20000, "stock": 90},
            
            # Obat Batuk
            {"name": "OBH Combi", "description": "Obat batuk berdahak", "category": "Batuk", "price": 22000, "stock": 100},
            {"name": "Woods Peppermint", "description": "Obat batuk dan pelega tenggorokan", "category": "Batuk", "price": 18000, "stock": 110},
            {"name": "Bisolvon", "description": "Pengencer dahak", "category": "Batuk", "price": 35000, "stock": 80},
            {"name": "Vicks Formula 44", "description": "Obat batuk kering dan berdahak", "category": "Batuk", "price": 30000, "stock": 85},
            
            # Obat Tenggorokan & Mulut
            {"name": "FG Troches", "description": "Tablet hisap radang tenggorokan", "category": "THT", "price": 25000, "stock": 90},
            {"name": "Strepsils", "description": "Lozenges untuk sakit tenggorokan", "category": "THT", "price": 18000, "stock": 120},
            {"name": "Betadine Gargle", "description": "Obat kumur antiseptik", "category": "THT", "price": 35000, "stock": 70},
            {"name": "Aloclair Gel", "description": "Gel obat sariawan", "category": "Mulut", "price": 45000, "stock": 60},
            
            # Vitamin & Suplemen
            {"name": "Vitamin C 1000mg", "description": "Meningkatkan daya tahan tubuh", "category": "Vitamin", "price": 50000, "stock": 150},
            {"name": "Vitamin B Complex", "description": "Menjaga kesehatan saraf", "category": "Vitamin", "price": 35000, "stock": 120},
            {"name": "Sangobion", "description": "Suplemen zat besi untuk anemia", "category": "Vitamin", "price": 45000, "stock": 100},
            {"name": "CDR", "description": "Kalsium untuk tulang", "category": "Vitamin", "price": 55000, "stock": 90},
            {"name": "Neurobion", "description": "Vitamin B1, B6, B12", "category": "Vitamin", "price": 65000, "stock": 80},
            
            # Obat Mata
            {"name": "Insto Regular", "description": "Tetes mata untuk mata merah", "category": "Mata", "price": 18000, "stock": 100},
            {"name": "Cendo Xitrol", "description": "Tetes mata antibiotik", "category": "Mata", "price": 35000, "stock": 70},
            {"name": "Visine", "description": "Tetes mata pelembab", "category": "Mata", "price": 45000, "stock": 60},
            
            # Obat Nyeri Otot
            {"name": "Counterpain", "description": "Krim pereda nyeri otot", "category": "Otot", "price": 35000, "stock": 100},
            {"name": "Salonpas", "description": "Koyo pereda nyeri", "category": "Otot", "price": 25000, "stock": 120},
            {"name": "Hot In Cream", "description": "Krim penghangat otot", "category": "Otot", "price": 20000, "stock": 110},
            
            # Obat Kulit Jamur
            {"name": "Miconazole Cream", "description": "Antijamur untuk kulit", "category": "Kulit", "price": 25000, "stock": 80},
            {"name": "Kalpanax", "description": "Obat panu dan kurap", "category": "Kulit", "price": 15000, "stock": 100},
            {"name": "Canesten Cream", "description": "Krim antijamur", "category": "Kulit", "price": 55000, "stock": 60},
        ]
        
        for med_data in medicines_data:
            medicine = Medicine(**med_data)
            db.add(medicine)
        db.commit()

# ==========================================
# 4. SETUP APLIKASI
# ==========================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Buat folder static jika belum ada
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        # Seed data on first connection
        seed_diseases(db)
        seed_medicines(db)
        yield db
    finally:
        db.close()

class SymptomCheck(BaseModel):
    patient_name: str
    symptoms: str

class DiseaseResponse(BaseModel):
    id: int
    name: str
    category: str
    description: str
    symptoms: str
    treatment: str
    medicines: str
    image_url: str

class PatientRecordResponse(BaseModel):
    id: int
    name: str
    symptoms: str
    diagnosis: str
    advice: str
    disease_name: Optional[str] = None
    disease_category: Optional[str] = None
    medicines: Optional[str] = None
    created_at: Optional[str] = None

# Pydantic models untuk Toko Obat
class MedicineResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    price: float
    stock: int
    image_url: Optional[str] = None

class CartAddRequest(BaseModel):
    session_id: str
    medicine_id: int
    quantity: int = 1

class CartItemResponse(BaseModel):
    id: int
    session_id: str
    medicine_id: int
    medicine_name: str
    medicine_price: float
    quantity: int
    subtotal: float

class CheckoutRequest(BaseModel):
    session_id: str
    customer_name: str
    phone: str
    address: str

class OrderResponse(BaseModel):
    id: int
    customer_name: str
    phone: str
    address: str
    items: str
    total_price: float
    status: str
    created_at: str

# ==========================================
# AUTH PYDANTIC MODELS
# ==========================================
class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    created_at: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# ==========================================
# AUTH HELPER FUNCTIONS
# ==========================================
def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token tidak valid")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")
    return user

def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak. Hanya admin yang bisa mengakses.")
    return current_user

# ==========================================
# AUTH ENDPOINTS
# ==========================================
@app.post("/api/auth/register")
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Registrasi user baru"""
    # Cek apakah email sudah terdaftar
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    
    # Buat user baru
    new_user = User(
        email=data.email,
        password=hash_password(data.password),
        name=data.name,
        role="user",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "status": "success",
        "message": "Registrasi berhasil! Silakan login.",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "role": new_user.role
        }
    }

@app.post("/api/auth/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Login dan dapatkan JWT token"""
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    
    # Buat access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "created_at": user.created_at
        }
    }

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Mendapatkan info user yang sedang login"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "created_at": current_user.created_at
    }

@app.get("/")
def read_root():
    return {"message": "HealthBridge AI is Running!"}

# ==========================================
# 5. API PENYAKIT (BARU)
# ==========================================
@app.get("/api/diseases", response_model=List[DiseaseResponse])
def get_all_diseases(db: Session = Depends(get_db)):
    """Mengambil semua data penyakit"""
    diseases = db.query(Disease).all()
    return diseases

@app.get("/api/diseases/search")
def search_diseases(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Mencari penyakit berdasarkan keyword"""
    diseases = db.query(Disease).filter(
        Disease.name.ilike(f"%{q}%") | 
        Disease.symptoms.ilike(f"%{q}%") |
        Disease.category.ilike(f"%{q}%")
    ).all()
    return diseases

@app.get("/api/diseases/{disease_id}", response_model=DiseaseResponse)
def get_disease_by_id(disease_id: int, db: Session = Depends(get_db)):
    """Mengambil detail penyakit berdasarkan ID"""
    disease = db.query(Disease).filter(Disease.id == disease_id).first()
    if not disease:
        return {"error": "Penyakit tidak ditemukan"}
    return disease

# ==========================================
# 6. API RIWAYAT PASIEN (BARU)
# ==========================================
@app.get("/api/patients", response_model=List[PatientRecordResponse])
def get_all_patients(db: Session = Depends(get_db)):
    """Mengambil semua riwayat konsultasi pasien"""
    patients = db.query(PatientRecord).order_by(PatientRecord.id.desc()).all()
    return patients

@app.get("/api/patients/search")
def search_patients(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Mencari riwayat pasien berdasarkan nama atau diagnosa"""
    patients = db.query(PatientRecord).filter(
        PatientRecord.name.ilike(f"%{q}%") | 
        PatientRecord.diagnosis.ilike(f"%{q}%") |
        PatientRecord.disease_name.ilike(f"%{q}%")
    ).order_by(PatientRecord.id.desc()).all()
    return patients

@app.get("/api/patients/{patient_id}", response_model=PatientRecordResponse)
def get_patient_by_id(patient_id: int, db: Session = Depends(get_db)):
    """Mengambil detail riwayat konsultasi berdasarkan ID"""
    patient = db.query(PatientRecord).filter(PatientRecord.id == patient_id).first()
    if not patient:
        return {"error": "Data pasien tidak ditemukan"}
    return patient

# ==========================================
# 7. API DIAGNOSA (UPGRADED)
# ==========================================
@app.post("/api/diagnose")
def diagnose_symptoms(data: SymptomCheck, db: Session = Depends(get_db)):
    
    diagnosis_clean = "Analisa Umum"
    advice_clean = "Istirahat yang cukup dan perbanyak minum air putih."
    matched_disease = None

    # --- OTAK 1: REAL AI (GEMINI) ---
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": f"Kamu adalah dokter AI profesional. Pasien bernama {data.patient_name} memiliki keluhan: '{data.symptoms}'. Berikan diagnosa medis kemungkinan (nama penyakit) dan saran pengobatan praktis. Jawab singkat padat."}]
            }]
        }
        
        response = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result:
                full_text = result['candidates'][0]['content']['parts'][0]['text']
                sentences = full_text.split('.')
                diagnosis_clean = sentences[0]
                advice_clean = " ".join(sentences[1:]).strip()
                if len(advice_clean) < 5: advice_clean = full_text
            else:
                raise Exception("Google menolak menjawab (Safety Filter)")
        else:
            raise Exception(f"Koneksi Gagal: {response.status_code}")

    except Exception as e:
        # --- OTAK 2: MODE SIMULASI (AUTO-DETECT) ---
        print(f"[WARNING] Pindah ke Mode Simulasi karena: {e}")
        
        s_lower = data.symptoms.lower()
        
        if "demam" in s_lower or "panas" in s_lower:
            diagnosis_clean = "Demam (Viral Infection)"
            advice_clean = "Minum Paracetamol, kompres hangat, cek suhu berkala."
        elif "perut" in s_lower or "mual" in s_lower or "lambung" in s_lower:
            diagnosis_clean = "Dispepsia / Maag"
            advice_clean = "Hindari makanan pedas/asam, makan teratur, minum obat lambung."
        elif "kepala" in s_lower or "pusing" in s_lower or "migrain" in s_lower:
            diagnosis_clean = "Cephalgia (Sakit Kepala)"
            advice_clean = "Istirahat di ruang gelap, hindari layar HP, minum obat pereda nyeri."
        elif "gatal" in s_lower or "kulit" in s_lower or "merah" in s_lower:
            diagnosis_clean = "Dermatitis / Alergi Kulit"
            advice_clean = "Jangan digaruk, gunakan bedak salisil atau salep gatal."
        elif "batuk" in s_lower or "pilek" in s_lower or "flu" in s_lower:
            diagnosis_clean = "Common Cold (ISPA Ringan)"
            advice_clean = "Istirahat total, minum vitamin C, gunakan masker."
        elif "tulang" in s_lower or "nyeri" in s_lower or "pegal" in s_lower:
            diagnosis_clean = "Myalgia (Nyeri Otot)"
            advice_clean = "Pijat ringan, gunakan krim otot panas, istirahat."
        elif "sesak" in s_lower or "napas" in s_lower or "mengi" in s_lower:
            diagnosis_clean = "Asma / Gangguan Pernapasan"
            advice_clean = "Hindari pemicu, gunakan inhaler jika tersedia, segera ke dokter jika parah."
        elif "gula" in s_lower or "kencing" in s_lower or "haus" in s_lower:
            diagnosis_clean = "Suspek Diabetes Mellitus"
            advice_clean = "Cek gula darah, kurangi konsumsi gula, konsultasi dokter."
        elif "darah tinggi" in s_lower or "hipertensi" in s_lower:
            diagnosis_clean = "Hipertensi (Tekanan Darah Tinggi)"
            advice_clean = "Kurangi garam, olahraga ringan, hindari stres, cek tekanan darah rutin."
        elif "berputar" in s_lower or "vertigo" in s_lower:
            diagnosis_clean = "Vertigo"
            advice_clean = "Istirahat, hindari gerakan mendadak, minum obat antivertigo."
        elif "gigi" in s_lower or "ngilu" in s_lower or "gusi" in s_lower:
            diagnosis_clean = "Sakit Gigi"
            advice_clean = "Kumur air garam hangat, minum obat pereda nyeri, segera ke dokter gigi."
        elif "diare" in s_lower or "mencret" in s_lower or "bab encer" in s_lower:
            diagnosis_clean = "Diare"
            advice_clean = "Minum oralit, hindari makanan berminyak, banyak minum air putih."
        elif "sariawan" in s_lower or "luka mulut" in s_lower:
            diagnosis_clean = "Sariawan"
            advice_clean = "Oleskan obat sariawan, kumur antiseptik, konsumsi vitamin C."
        elif "mata" in s_lower or "belekan" in s_lower:
            diagnosis_clean = "Sakit Mata (Konjungtivitis)"
            advice_clean = "Kompres dingin, gunakan tetes mata, jangan mengucek mata."
        elif "telinga" in s_lower or "pendengaran" in s_lower:
            diagnosis_clean = "Sakit Telinga (Otitis)"
            advice_clean = "Kompres hangat, jangan mengorek telinga, segera ke dokter THT."
        else:
            diagnosis_clean = "Gejala Umum / Kelelahan"
            advice_clean = f"Keluhan '{data.symptoms}' membutuhkan observasi lebih lanjut. Sarankan istirahat total dan kunjungi dokter jika berlanjut 3 hari."

    # Cari penyakit yang cocok di database dengan scoring system
    diseases = db.query(Disease).all()
    best_match = None
    best_score = 0
    
    for disease in diseases:
        score = 0
        
        # Check if disease name matches diagnosis
        if disease.name.lower() in diagnosis_clean.lower() or diagnosis_clean.lower() in disease.name.lower():
            score += 10
            
        # Check keywords match with symptoms
        disease_keywords = [k.strip().lower() for k in disease.symptoms.split(',')]
        symptom_words = [w.strip().lower() for w in data.symptoms.lower().split()]
        
        for keyword in disease_keywords:
            for word in symptom_words:
                if len(word) > 3:  # Avoid matching short words
                    if word in keyword or keyword in word:
                        score += 2
                    elif word[:4] == keyword[:4]:  # Prefix match
                        score += 1
        
        if score > best_score:
            best_score = score
            best_match = disease
    
    # Hanya assign jika score cukup tinggi (minimal ada 2 keyword match)
    matched_disease = best_match if best_score >= 4 else None
    
    # Deteksi kondisi DARURAT
    is_emergency = False
    emergency_keywords = ["nyeri dada hebat", "sesak napas berat", "pingsan", "kejang", "tidak sadar", 
                          "pendarahan", "kecelakaan", "lumpuh", "stroke", "serangan jantung"]
    s_lower = data.symptoms.lower()
    for keyword in emergency_keywords:
        if keyword in s_lower:
            is_emergency = True
            break
    
    # Jika matched disease adalah kategori Darurat
    if matched_disease and matched_disease.category == "Darurat":
        is_emergency = True

    # Simpan dengan data lengkap
    from datetime import datetime
    new_record = PatientRecord(
        name=data.patient_name,
        symptoms=data.symptoms,
        diagnosis=diagnosis_clean,
        advice=advice_clean,
        disease_name=matched_disease.name if matched_disease else None,
        disease_category=matched_disease.category if matched_disease else None,
        medicines=matched_disease.medicines if matched_disease else None,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    response_data = {
        "status": "success",
        "id": new_record.id,
        "patient": new_record.name,
        "ai_diagnosis": new_record.diagnosis,
        "suggestion": new_record.advice,
        "is_emergency": is_emergency
    }
    
    # Tambahkan peringatan darurat jika diperlukan
    if is_emergency:
        response_data["emergency_warning"] = "⚠️ PERHATIAN: Gejala Anda mungkin memerlukan penanganan DARURAT! Segera hubungi 119 atau pergi ke IGD rumah sakit terdekat!"
    
    # Tambahkan info penyakit jika ditemukan
    if matched_disease:
        response_data["disease"] = {
            "id": matched_disease.id,
            "name": matched_disease.name,
            "category": matched_disease.category,
            "description": matched_disease.description,
            "symptoms": matched_disease.symptoms,
            "treatment": matched_disease.treatment,
            "medicines": matched_disease.medicines,
            "image_url": matched_disease.image_url
        }
    else:
        # FALLBACK: Jika tidak ada penyakit yang cocok, sarankan ke dokter
        response_data["doctor_recommendation"] = {
            "message": "Berdasarkan gejala yang Anda sampaikan, kami tidak dapat memberikan diagnosa yang akurat. Untuk keamanan Anda, silakan konsultasi dengan dokter profesional.",
            "advice": [
                "Kunjungi dokter umum atau klinik terdekat untuk pemeriksaan lebih lanjut",
                "Catat semua gejala yang Anda rasakan untuk disampaikan ke dokter",
                "Jika gejala memburuk, segera ke IGD rumah sakit",
                "Anda juga dapat menghubungi hotline kesehatan: 119 ext 8"
            ],
            "specialist_options": [
                {"specialist": "Dokter Umum", "for": "Pemeriksaan awal dan rujukan"},
                {"specialist": "Dokter Spesialis Penyakit Dalam", "for": "Keluhan organ dalam"},
                {"specialist": "Dokter Spesialis Saraf", "for": "Keluhan neurologis"},
                {"specialist": "Dokter Spesialis Kulit", "for": "Keluhan kulit"},
                {"specialist": "Dokter Spesialis THT", "for": "Keluhan telinga, hidung, tenggorokan"},
                {"specialist": "Dokter Spesialis Mata", "for": "Keluhan penglihatan"}
            ]
        }
    
    return response_data

# ==========================================
# 8. API TOKO OBAT (BARU)
# ==========================================
@app.get("/api/medicines", response_model=List[MedicineResponse])
def get_all_medicines(db: Session = Depends(get_db)):
    """Mengambil semua data obat"""
    medicines = db.query(Medicine).all()
    return medicines

@app.get("/api/medicines/search")
def search_medicines(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Mencari obat berdasarkan keyword"""
    medicines = db.query(Medicine).filter(
        Medicine.name.ilike(f"%{q}%") | 
        Medicine.description.ilike(f"%{q}%") |
        Medicine.category.ilike(f"%{q}%")
    ).all()
    return medicines

@app.get("/api/medicines/category/{category}")
def get_medicines_by_category(category: str, db: Session = Depends(get_db)):
    """Mengambil obat berdasarkan kategori"""
    medicines = db.query(Medicine).filter(Medicine.category.ilike(f"%{category}%")).all()
    return medicines

@app.get("/api/medicines/{medicine_id}", response_model=MedicineResponse)
def get_medicine_by_id(medicine_id: int, db: Session = Depends(get_db)):
    """Mengambil detail obat berdasarkan ID"""
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        return {"error": "Obat tidak ditemukan"}
    return medicine

# ==========================================
# 9. API KERANJANG BELANJA (BARU)
# ==========================================
@app.post("/api/cart/add")
def add_to_cart(data: CartAddRequest, db: Session = Depends(get_db)):
    """Menambahkan obat ke keranjang"""
    # Cek apakah obat ada
    medicine = db.query(Medicine).filter(Medicine.id == data.medicine_id).first()
    if not medicine:
        return {"status": "error", "message": "Obat tidak ditemukan"}
    
    # Cek apakah item sudah ada di keranjang
    existing_item = db.query(CartItem).filter(
        CartItem.session_id == data.session_id,
        CartItem.medicine_id == data.medicine_id
    ).first()
    
    if existing_item:
        existing_item.quantity += data.quantity
    else:
        new_item = CartItem(
            session_id=data.session_id,
            medicine_id=data.medicine_id,
            quantity=data.quantity
        )
        db.add(new_item)
    
    db.commit()
    
    # Hitung total items di keranjang
    total_items = db.query(CartItem).filter(CartItem.session_id == data.session_id).count()
    
    return {
        "status": "success",
        "message": f"{medicine.name} ditambahkan ke keranjang",
        "cart_count": total_items
    }

@app.get("/api/cart/{session_id}")
def get_cart(session_id: str, db: Session = Depends(get_db)):
    """Mengambil isi keranjang berdasarkan session"""
    cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    
    items = []
    total_price = 0
    
    for item in cart_items:
        medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
        if medicine:
            subtotal = medicine.price * item.quantity
            total_price += subtotal
            items.append({
                "id": item.id,
                "medicine_id": medicine.id,
                "medicine_name": medicine.name,
                "medicine_price": medicine.price,
                "quantity": item.quantity,
                "subtotal": subtotal
            })
    
    return {
        "items": items,
        "total_items": len(items),
        "total_price": total_price
    }

@app.put("/api/cart/update/{item_id}")
def update_cart_item(item_id: int, quantity: int = Query(..., ge=1), db: Session = Depends(get_db)):
    """Update jumlah item di keranjang"""
    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not item:
        return {"status": "error", "message": "Item tidak ditemukan"}
    
    item.quantity = quantity
    db.commit()
    
    return {"status": "success", "message": "Keranjang diupdate"}

@app.delete("/api/cart/remove/{item_id}")
def remove_from_cart(item_id: int, db: Session = Depends(get_db)):
    """Menghapus item dari keranjang"""
    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not item:
        return {"status": "error", "message": "Item tidak ditemukan"}
    
    db.delete(item)
    db.commit()
    
    return {"status": "success", "message": "Item dihapus dari keranjang"}

@app.delete("/api/cart/clear/{session_id}")
def clear_cart(session_id: str, db: Session = Depends(get_db)):
    """Mengosongkan keranjang"""
    db.query(CartItem).filter(CartItem.session_id == session_id).delete()
    db.commit()
    
    return {"status": "success", "message": "Keranjang dikosongkan"}

# ==========================================
# 10. API CHECKOUT & ORDER (BARU)
# ==========================================
@app.post("/api/order/checkout")
def checkout(data: CheckoutRequest, db: Session = Depends(get_db)):
    """Proses checkout dan buat pesanan + backup ke AWS S3"""
    from datetime import datetime
    from aws_service import s3_manager
    
    # Ambil isi keranjang
    cart_items = db.query(CartItem).filter(CartItem.session_id == data.session_id).all()
    
    if not cart_items:
        return {"status": "error", "message": "Keranjang kosong"}
    
    # Hitung total dan buat list items
    items_list = []
    total_price = 0
    
    for item in cart_items:
        medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
        if medicine:
            subtotal = medicine.price * item.quantity
            total_price += subtotal
            items_list.append({
                "medicine_id": medicine.id,
                "name": medicine.name,
                "price": medicine.price,
                "quantity": item.quantity,
                "subtotal": subtotal
            })
    
    # Buat order baru
    new_order = Order(
        customer_name=data.customer_name,
        phone=data.phone,
        address=data.address,
        items=json.dumps(items_list),
        total_price=total_price,
        status="pending",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(new_order)
    
    # Kosongkan keranjang
    db.query(CartItem).filter(CartItem.session_id == data.session_id).delete()
    
    db.commit()
    db.refresh(new_order)
    
    # Upload ke AWS S3 (jika tersedia)
    order_data = {
        "order_id": new_order.id,
        "customer_name": new_order.customer_name,
        "email": data.email if hasattr(data, 'email') else "N/A",
        "phone": new_order.phone,
        "address": new_order.address,
        "items": items_list,
        "total_price": new_order.total_price,
        "status": new_order.status,
        "created_at": new_order.created_at
    }
    
    # Backup data order ke S3 JSON
    s3_manager.upload_order_json(order_data, new_order.id)
    
    # Generate dan upload invoice PDF
    s3_manager.generate_and_upload_invoice(order_data, new_order.id)
    
    return {
        "status": "success",
        "message": "Pesanan berhasil dibuat! Data di-backup ke AWS S3.",
        "order": {
            "id": new_order.id,
            "customer_name": new_order.customer_name,
            "phone": new_order.phone,
            "address": new_order.address,
            "items": items_list,
            "total_price": new_order.total_price,
            "status": new_order.status,
            "created_at": new_order.created_at
        }
    }

@app.get("/api/orders/{phone}")
def get_orders_by_phone(phone: str, db: Session = Depends(get_db)):
    """Mengambil riwayat pesanan berdasarkan nomor telepon"""
    orders = db.query(Order).filter(Order.phone == phone).order_by(Order.id.desc()).all()
    
    result = []
    for order in orders:
        result.append({
            "id": order.id,
            "customer_name": order.customer_name,
            "phone": order.phone,
            "address": order.address,
            "items": json.loads(order.items),
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at
        })
    
    return {"orders": result}

# ==========================================
# 11. ADMIN ENDPOINTS (PROTECTED)
# ==========================================
@app.get("/api/admin/dashboard")
def admin_dashboard(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Dashboard admin dengan statistik"""
    total_users = db.query(User).count()
    total_orders = db.query(Order).count()
    total_medicines = db.query(Medicine).count()
    
    # Hitung total revenue
    orders = db.query(Order).all()
    total_revenue = sum([order.total_price for order in orders])
    
    # Order pending
    pending_orders = db.query(Order).filter(Order.status == "pending").count()
    
    # Order terbaru
    recent_orders = db.query(Order).order_by(Order.id.desc()).limit(5).all()
    recent_list = []
    for order in recent_orders:
        recent_list.append({
            "id": order.id,
            "customer_name": order.customer_name,
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at
        })
    
    return {
        "stats": {
            "total_users": total_users,
            "total_orders": total_orders,
            "total_medicines": total_medicines,
            "total_revenue": total_revenue,
            "pending_orders": pending_orders
        },
        "recent_orders": recent_list
    }

@app.get("/api/admin/users")
def admin_get_users(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Mendapatkan semua user"""
    users = db.query(User).all()
    return [{
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "created_at": u.created_at
    } for u in users]

@app.get("/api/admin/orders")
def admin_get_orders(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Mendapatkan semua order"""
    orders = db.query(Order).order_by(Order.id.desc()).all()
    result = []
    for order in orders:
        result.append({
            "id": order.id,
            "customer_name": order.customer_name,
            "phone": order.phone,
            "address": order.address,
            "items": json.loads(order.items),
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at
        })
    return result

class UpdateOrderStatus(BaseModel):
    status: str

@app.put("/api/admin/orders/{order_id}")
def admin_update_order(order_id: int, data: UpdateOrderStatus, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Update status order"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    
    order.status = data.status
    db.commit()
    
    return {"status": "success", "message": f"Status order diubah ke {data.status}"}

class MedicineCreate(BaseModel):
    name: str
    description: str
    category: str
    price: float
    stock: int = 100
    image_url: Optional[str] = None

@app.post("/api/admin/medicines")
def admin_add_medicine(data: MedicineCreate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Tambah obat baru"""
    existing = db.query(Medicine).filter(Medicine.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Obat dengan nama ini sudah ada")
    
    new_medicine = Medicine(
        name=data.name,
        description=data.description,
        category=data.category,
        price=data.price,
        stock=data.stock,
        image_url=data.image_url
    )
    db.add(new_medicine)
    db.commit()
    db.refresh(new_medicine)
    
    return {"status": "success", "message": "Obat berhasil ditambahkan", "medicine_id": new_medicine.id}

@app.put("/api/admin/medicines/{medicine_id}")
def admin_update_medicine(medicine_id: int, data: MedicineCreate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Update obat"""
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Obat tidak ditemukan")
    
    medicine.name = data.name
    medicine.description = data.description
    medicine.category = data.category
    medicine.price = data.price
    medicine.stock = data.stock
    if data.image_url:
        medicine.image_url = data.image_url
    
    db.commit()
    
    return {"status": "success", "message": "Obat berhasil diupdate"}

@app.delete("/api/admin/medicines/{medicine_id}")
def admin_delete_medicine(medicine_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Hapus obat"""
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Obat tidak ditemukan")
    
    db.delete(medicine)
    db.commit()
    
    return {"status": "success", "message": "Obat berhasil dihapus"}

@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...), product_name: str = Form(None)):
    """Upload gambar produk ke local storage dan S3"""
    import uuid
    import shutil
    import re
    from aws_service import s3_manager
    
    # Validasi tipe file
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipe file tidak didukung. Gunakan JPG, PNG, GIF, atau WEBP")
    
    # Generate nama file
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    
    # Jika ada product_name, gunakan sebagai nama file (sanitize untuk keamanan)
    if product_name:
        # Sanitize: hanya huruf, angka, spasi, dan dash yang diperbolehkan
        safe_name = re.sub(r'[^a-zA-Z0-9\s\-]', '', product_name)
        safe_name = safe_name.replace(' ', '_').lower()[:50]  # Max 50 karakter
        unique_filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.{file_extension}"
    else:
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
    
    file_path = f"static/images/{unique_filename}"
    
    # Simpan file ke local storage
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan file: {str(e)}")
    
    # Upload ke S3 untuk backup (jika tersedia)
    s3_url = None
    if s3_manager.enabled:
        try:
            with open(file_path, "rb") as f:
                s3_key = f"product_images/{unique_filename}"
                s3_manager.s3_client.put_object(
                    Bucket=s3_manager.bucket,
                    Key=s3_key,
                    Body=f.read(),
                    ContentType=file.content_type
                )
                s3_url = f"https://{s3_manager.bucket}.s3.{s3_manager.region}.amazonaws.com/{s3_key}"
                print(f"✅ Image uploaded to S3: {s3_url}")
        except Exception as e:
            print(f"⚠️ S3 upload failed (local save successful): {str(e)}")
    
    # Return URL gambar
    image_url = f"/static/images/{unique_filename}"
    return {
        "status": "success", 
        "image_url": image_url, 
        "s3_url": s3_url,
        "filename": unique_filename
    }

@app.get("/api/images")
def list_available_images():
    """List semua gambar yang tersedia di folder static/images"""
    import os
    images_dir = "static/images"
    
    if not os.path.exists(images_dir):
        return {"images": []}
    
    images = []
    for filename in os.listdir(images_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.jfif')):
            images.append({
                "filename": filename,
                "url": f"/static/images/{filename}",
                "size": os.path.getsize(os.path.join(images_dir, filename))
            })
    
    return {"images": images, "total": len(images)}

@app.get("/api/admin/images-usage")
def get_images_usage(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Get mapping of images to products for admin"""
    import os
    images_dir = "static/images"
    
    # Get all medicines with images
    medicines = db.query(Medicine).filter(Medicine.image_url != None, Medicine.image_url != "").all()
    
    # Create mapping
    used_images = {}
    for med in medicines:
        if med.image_url:
            filename = med.image_url.split("/")[-1]
            used_images[filename] = {
                "medicine_id": med.id,
                "medicine_name": med.name,
                "image_url": med.image_url
            }
    
    # List all images
    all_images = []
    if os.path.exists(images_dir):
        for filename in os.listdir(images_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.jfif')):
                all_images.append({
                    "filename": filename,
                    "url": f"/static/images/{filename}",
                    "assigned_to": used_images.get(filename)
                })
    
    return {
        "images": all_images, 
        "total": len(all_images),
        "assigned": len(used_images),
        "unassigned": len(all_images) - len(used_images)
    }

# 12. SEED DEFAULT ADMIN
# ==========================================
def seed_admin(db: Session):
    """Buat akun admin default jika belum ada"""
    admin = db.query(User).filter(User.email == "admin@healthbridge.com").first()
    if not admin:
        admin_user = User(
            email="admin@healthbridge.com",
            password=hash_password("admin123"),
            name="Administrator",
            role="admin",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(admin_user)
        db.commit()
        print("✅ Admin default dibuat: admin@healthbridge.com / admin123")

# Jalankan seed saat startup
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        seed_diseases(db)
        seed_medicines(db)
        seed_admin(db)
    finally:
        db.close()