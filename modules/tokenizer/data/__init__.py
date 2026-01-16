import json
import os

BASE_PATH = os.path.dirname(__file__)

def load_json(filename):
    """Memuat file JSON dari folder dictionary dengan penanganan error."""
    filepath = os.path.join(BASE_PATH, filename)
    
    if not os.path.exists(filepath):
        print(f"⚠️  Peringatan: File {filename} tidak ditemukan di {BASE_PATH}.")
        return {}  # Kembalikan dictionary kosong agar tidak menyebabkan error

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: File {filename} mengandung JSON yang tidak valid!")
        return {}

kada = load_json("kada.json")

__all__ = ["kada"]