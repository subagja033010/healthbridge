// index.js
const express = require('express');
const app = express();
const pool = require('./db'); // Import file db.js tadi

app.use(express.json());

// Contoh Endpoint: Ambil semua data pasien
app.get('/pasien', async (req, res) => {
    try {
        const result = await pool.query('SELECT * FROM data_pasien');
        res.json(result.rows);
    } catch (err) {
        console.error(err.message);
        res.status(500).send('Server Error');
    }
});

// Contoh Endpoint: Tambah pasien baru
app.post('/pasien', async (req, res) => {
    try {
        const { nama, diagnosa } = req.body;
        const newPasien = await pool.query(
            'INSERT INTO data_pasien (nama_pasien, diagnosa, tanggal_masuk) VALUES ($1, $2, CURRENT_DATE) RETURNING *',
            [nama, diagnosa]
        );
        res.json(newPasien.rows[0]);
    } catch (err) {
        console.error(err.message);
        res.status(500).send('Server Error');
    }
});

app.listen(3000, () => {
    console.log('Server berjalan di port 3000');
});