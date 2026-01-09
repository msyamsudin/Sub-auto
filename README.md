# Sub-auto 🎬

Alat otomatisasi untuk mengekstrak, menerjemahkan, dan menggabungkan subtitle pada file video MKV menggunakan LLM.

## ✨ Fitur

- **Multi-Provider LLM**: Ollama (lokal), OpenRouter (cloud), Gemini
- **Otomatis end-to-end**: Ekstrak → Terjemahkan → Gabung kembali ke MKV
- **Batch processing**: Terjemahan dalam batch dengan kemampuan resume
- **Estimasi token**: Prakiraan penggunaan token sebelum mulai
- **GUI intuitif**: Antarmuka grafis yang mudah digunakan

## 📋 Prerequisites

- Python 3.10+
- MKVToolNix ([download](https://mkvtoolnix.download/))

## 🚀 Instalasi & Penggunaan

### Windows (Recommended - Menggunakan Batch Files)

1. **Clone repository**
   ```bash
   git clone https://github.com/msyamsudin/Sub-auto.git
   cd Sub-auto
   ```

2. **Instalasi dependencies**
   - Double-click `install.bat`
   - Tunggu hingga proses instalasi selesai

3. **Jalankan aplikasi**
   - Double-click `start.bat`
   - Aplikasi GUI akan terbuka secara otomatis

### Linux/Mac atau Manual Installation

1. **Clone repository**
   ```bash
   git clone https://github.com/msyamsudin/Sub-auto.git
   cd Sub-auto
   ```

2. **Setup virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Jalankan aplikasi**
   ```bash
   python main.py
   ```

## 📖 Cara Menggunakan

1. **Pilih file MKV** - Klik tombol untuk memilih file video
2. **Pilih track subtitle** - Pilih subtitle yang ingin diterjemahkan
3. **Konfigurasi AI**:
   - Pilih provider LLM (Ollama/OpenRouter/Gemini)
   - Pilih model yang tersedia
   - Pilih bahasa tujuan terjemahan
4. **Mulai terjemahan** - Klik "Start Translation"
5. **Tunggu proses selesai** - Subtitle akan otomatis digabungkan ke file MKV

**Settings (⚙️)**: Atur API key atau path MKVToolNix jika diperlukan.

## 🔧 Troubleshooting

- **Ollama 403**: Pastikan `ollama serve` berjalan di background
- **MKVToolNix not found**: Atur path manual di Settings atau install dari [mkvtoolnix.download](https://mkvtoolnix.download/)
- **Import Error**: Pastikan semua dependencies terinstall dengan menjalankan `pip install -r requirements.txt`
- **Virtual environment tidak aktif**: Gunakan `start.bat` (Windows) atau aktifkan manual dengan `.venv\Scripts\activate`

## 📁 Struktur Proyek

```
Sub-auto/
├── core/              # Modul inti (translator, parser, handler)
├── gui/               # Komponen antarmuka pengguna
├── main.py            # Entry point aplikasi
├── config.json        # Konfigurasi aplikasi
├── requirements.txt   # Dependencies Python
├── install.bat        # Script instalasi (Windows)
└── start.bat          # Script untuk menjalankan aplikasi (Windows)
```

## 📄 Lisensi

[MIT License](LICENSE)