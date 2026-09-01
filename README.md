# Sub-auto

<img width="1500" height="1000" alt="Image" src="https://github.com/user-attachments/assets/83e52e05-1795-41ee-8e92-ecb068a34dca" />

[![CI](https://github.com/msyamsudin/Sub-auto/actions/workflows/ci.yml/badge.svg)](https://github.com/msyamsudin/Sub-auto/actions/workflows/ci.yml)

Alat otomatisasi untuk mengekstrak, menerjemahkan, dan menggabungkan subtitle pada file video MKV menggunakan LLM.

## Fitur

- **Multi-Provider LLM**:
  - **OpenRouter**: Akses ke ratusan model performa tinggi (termasuk Gemini, Llama, Mistral).
  - **Groq**: Pemrosesan cepat dengan inference hardware (LPU).
  - **Ollama**: Jalankan model secara lokal, gratis dan tanpa API key.
- **Smart Fallback**: Sistem otomatis beralih ke model cadangan jika terjadi error API atau policy violation.
- **Token Manager**: Statistik token akurat — menggunakan data `usage` asli dari respons API (dengan estimasi sebagai cadangan), plus estimasi biaya dan perkiraan token sebelum terjemahan dimulai.
- **Prompt Manager**: Atur prompt terjemahan (Standard/Anime/Formal), buat prompt kustom, uji prompt langsung dari aplikasi, dan pilih prompt aktif.
- **Built-in Editor**: Tinjau, edit, dan validasi hasil terjemahan sebelum digabungkan ke video.
- **Subtitle Eksternal**: Gunakan file SRT/ASS/SSA eksternal sebagai sumber terjemahan selain track bawaan MKV.
- **Otomatisasi Penuh**:
  - Ekstrak subtitle dari MKV.
  - Terjemahkan baris demi baris dengan pemulihan otomatis (batch yang gagal di-retry dengan ukuran lebih kecil).
  - Mempertahankan gaya subtitle (tag ASS/SSA).
  - Gabung kembali (mux) ke file video asli tanpa re-encoding.
- **Batch Processing**: Proses per-batch dengan **Pause / Resume / Auto-Resume** (progres tersimpan ke disk, aman dari crash).
- **Pengaturan Fleksibel**: Delay antar-batch dapat dikonfigurasi (`batch_delay_seconds` — set 0 untuk Ollama lokal).

## Prerequisites

- Python 3.10+
- MKVToolNix ([download](https://mkvtoolnix.download/))

## Instalasi & Penggunaan

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

> **Catatan**: Untuk pengembangan (menjalankan suite test), gunakan `pip install -r requirements-dev.txt`.

## Cara Menggunakan

1. **Pilih file MKV** - Klik tombol untuk memilih file video
2. **Pilih track subtitle** - Pilih subtitle yang ingin diterjemahkan (atau pilih file subtitle eksternal)
3. **Konfigurasi AI**:
   - Pilih provider LLM (OpenRouter/Groq/Ollama) di Settings
   - Masukkan API key (untuk OpenRouter/Groq) dan klik **Test**
   - Pilih model yang tersedia
   - Pilih bahasa tujuan terjemahan
4. **Mulai terjemahan** - Klik "Start Translation" dan konfirmasi judul anime (untuk konteks)
5. **Tunggu proses selesai** - Anda bisa Pause dan lanjutkan lagi kapan saja; progres tersimpan otomatis
6. **Tinjau hasil** - Edit subtitle jika perlu, lalu klik Approve untuk menggabungkan ke file MKV

**Settings**: Atur API key, path MKVToolNix, dan kelola prompt terjemahan.

## Konfigurasi

Semua pengaturan disimpan di `config.json` (tidak di-commit ke git):

| Key | Deskripsi | Default |
|---|---|---|
| `provider` | Provider aktif: `openrouter`, `groq`, `ollama` | `openrouter` |
| `openrouter_api_key` / `groq_api_key` | API key (disarankan lewat env var/keyring) | `""` |
| `ollama_base_url` | URL instance Ollama lokal | `http://localhost:11434` |
| `default_target_lang` | Bahasa tujuan default | `Indonesian` |
| `default_output_dir` | Direktori output (kosong = folder file sumber) | `""` |
| `output_mode` | Mode output (`new_file`) | `new_file` |
| `batch_size` | Jumlah baris per permintaan (saat ini tetap 25) | `25` |
| `batch_delay_seconds` | Jeda antar-batch (rate-limit guard; 0 untuk Ollama) | `1.5` |
| `fallback_model` | Model cadangan saat policy violation (kosong = otomatis) | `""` |

## Pengembangan

- **Menjalankan test**:
  ```bash
  pip install -r requirements-dev.txt
  python -m pytest tests
  ```
- **CI**: Workflow GitHub Actions (`.github/workflows/ci.yml`) menjalankan suite test (67 test) di Python 3.10–3.13 untuk setiap push/PR.
- **Paket**: Metadata proyek ada di `pyproject.toml` (versi dibaca dari `core/version.py`).

## Troubleshooting

- **Ollama 403**: Pastikan `ollama serve` berjalan di background
- **MKVToolNix not found**: Atur path manual di Settings atau install dari [mkvtoolnix.download](https://mkvtoolnix.download/)
- **Import Error**: Pastikan semua dependencies terinstall dengan menjalankan `pip install -r requirements.txt`
- **Virtual environment tidak aktif**: Gunakan `start.bat` (Windows) atau aktifkan manual dengan `.venv\Scripts\activate`
- **CI gagal di Python 3.10**: Sudah ditangani — `tomli` dipakai sebagai backport `tomllib` untuk validasi `pyproject.toml`

## Struktur

```
Sub-auto/
├── core/                      # Modul inti
│   ├── batch_processor.py     # Logika batch: parser respons, recovery, model token
│   ├── translator.py          # Orkestrator terjemahan (delegasi ke batch_processor)
│   ├── llm_provider.py        # Provider LLM (OpenRouter, Groq, Ollama)
│   ├── retry_handler.py       # Retry dengan exponential backoff
│   ├── state_manager.py       # Pause/resume state
│   ├── prompt_manager.py      # Manajemen prompt terjemahan
│   └── ...                    # mkv_handler, subtitle_parser, dll.
├── gui/
│   ├── app/                   # Jendela utama (app.py, ui_setup, translation_flow, ...)
│   ├── settings/              # Dialog pengaturan (per-provider frames)
│   ├── prompt_settings/       # Tab pengelolaan prompt
│   ├── components/            # Widget UI yang dapat digunakan ulang
│   ├── controllers/           # Logika controller (API, translation, step, view)
│   ├── services/              # Layanan sesi terjemahan & track subtitle
│   ├── views/                 # View per-langkah wizard
│   └── ...
├── tests/                     # Suite test (67 test)
├── .github/workflows/ci.yml   # CI GitHub Actions (Python 3.10–3.13)
├── main.py                    # Entry point aplikasi
├── pyproject.toml             # Metadata paket
├── requirements.txt           # Dependencies runtime
├── requirements-dev.txt       # Dependencies pengembangan (termasuk pytest)
├── install.bat                # Script instalasi (Windows)
└── start.bat                  # Script untuk menjalankan aplikasi (Windows)
```

## Lisensi

[MIT License](LICENSE)
