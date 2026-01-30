// db.js
require('dotenv').config(); // Membaca file .env
const { Pool } = require('pg');

// Membuat pool koneksi menggunakan data dari .env
const pool = new Pool({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASS,
    database: process.env.DB_NAME,
    port: process.env.DB_PORT,
    ssl: {
        rejectUnauthorized: false // Wajib untuk koneksi ke AWS RDS agar tidak error SSL
    }
});

// Tes koneksi saat file ini dijalankan
pool.connect((err, client, release) => {
    if (err) {
        return console.error('Gagal terhubung ke database:', err.stack);
    }
    console.log('Berhasil terhubung ke Database AWS!');
    release();
});

module.exports = pool;