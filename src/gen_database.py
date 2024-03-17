import os
import json
from mutagen.flac import FLAC

# Directorio que contiene tus archivos FLAC
directory = r"C:\Users\palgato\Music\FLAC"
data_folder = "data"  # Nombre de la carpeta donde se guardará el archivo JSON

# Asegúrate de que la carpeta "data" exista, si no, créala
if not os.path.exists(data_folder):
    os.makedirs(data_folder)

# Lista para almacenar la información de las canciones
song_database = []

# Recorre todos los directorios y subdirectorios de manera recursiva
for root, dirs, files in os.walk(directory):
    for filename in files:
        if filename.endswith(".flac"):
            filepath = os.path.join(root, filename)  # Construye la ruta completa del archivo
            try:
                audio = FLAC(filepath)
                artist = audio["artist"][0] if "artist" in audio else "Desconocido"
                title = audio["title"][0] if "title" in audio else "Desconocido"
                album = audio["album"][0] if "album" in audio else "Desconocido"

                # Agrega la información de la canción a la lista
                song_info = {
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "filename": filename,
                    "filepath": os.path.normpath(filepath)  # Normaliza la ruta del archivo FLAC
                }
                song_database.append(song_info)
            except Exception as e:
                print(f"Error al procesar el archivo {filepath}: {e}")

# Guarda la lista de canciones en un archivo JSON dentro de la carpeta "data"
output_path = os.path.join(data_folder, "song_database.json")
with open(output_path, "w") as f:
    json.dump(song_database, f, indent=4)
