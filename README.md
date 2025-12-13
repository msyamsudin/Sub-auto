# Sub-auto 🎬

Alat otomatisasi untuk mengekstrak, menerjemahkan, dan menggabungkan subtitle pada file video MKV menggunakan LLM.

## Fitur

- **Multi-Provider LLM**: Ollama (lokal), OpenRouter (cloud), Gemini
- **Otomatis end-to-end**: Ekstrak → Terjemahkan → Gabung kembali ke MKV
- **Batch processing**: Terjemahan dalam batch dengan kemampuan resume
- **Estimasi token**: Prakiraan penggunaan token sebelum mulai

## Prerequisites

- Python 3.10+
- MKVToolNix ([download](https://mkvtoolnix.download/))

## Instalasi

```bash
git clone https://github.com/msyamsudin/Sub-auto.git
cd Sub-auto
python -m venv .venv
source .venv/bin/activate  # Linux/Mac: .venv\Scripts\activate di Windows
pip install -r requirements.txt
```

## Penggunaan

```bash
python main.py
```

1. Pilih file MKV
2. Pilih track subtitle
3. Pilih model AI dan bahasa tujuan
4. Klik Start Translation

**Settings (⚙️)**: Atur API key atau path MKVToolNix jika diperlukan.

## Troubleshooting

- **Ollama 403**: Pastikan `ollama serve` berjalan
- **MKVToolNix not found**: Atur path manual di Settings

## Lisensi

[MIT License](LICENSE)