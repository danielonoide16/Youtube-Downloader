# YouTube Downloader

Aplicación multiplataforma desarrollada con **Python + Kivy** que permite descargar videos y audios de YouTube usando `yt-dlp`.

Actualmente soporta:

- ✅ Descarga de videos
- ✅ Descarga de audio en formato M4A
- ✅ Selección de calidad de video
- ✅ Descarga en carpeta elegida por el usuario en Android
- ✅ Integración con FFmpeg para Android
- ✅ Empaquetado como APK usando Buildozer

---

# Requisitos

## Desarrollo general

- Python 3.10+
- pip
- Kivy 2.3+
- yt-dlp
- requests

Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

# Ejecutar en escritorio (Windows / macOS / Linux)

Ejecutar:

```bash
python main.py
```

En escritorio:

- Las descargas se guardan en la carpeta seleccionada por el usuario.
- Si no existe una carpeta seleccionada, se usa la carpeta Downloads del sistema.

---

# Estructura del proyecto

```
YouTubeDownloader/
│
├── main.py
├── downloader.py
├── android_storage.py
├── desktop_storage.py
├── utils.py
├── ui.kv
│
├── assets/
│   └── (recursos de la aplicación)
│
├── libs/
│   └── (librerías nativas)
│
├── downloads/
│   └── (archivos descargados temporalmente)
│
├── buildozer.spec
│
└── README.md
```

---

# Android

La aplicación utiliza:

- Kivy
- python-for-android
- Buildozer
- PyJNIus
- FFmpeg compilado para Android

---

# Instalar Buildozer

Se recomienda usar Linux o Docker.

En Linux:

```bash
pip install buildozer
```

Dependencias:

```bash
sudo apt update

sudo apt install \
git \
zip \
unzip \
openjdk-17-jdk \
python3-pip \
build-essential \
autoconf \
libtool \
pkg-config
```

---

# Compilar APK

Desde la raíz del proyecto:

```bash
buildozer android debug
```

El APK aparecerá en:

```
bin/
```

Para instalar directamente:

```bash
buildozer android deploy run
```

Para ver logs:

```bash
buildozer android logcat
```

---

# Configuración Buildozer

El proyecto requiere:

```ini
requirements = python3,kivy,yt-dlp,requests,pyjnius

android.api = 34
android.minapi = 24

android.permissions = INTERNET
```

---

# FFmpeg para Android

Android no puede ejecutar directamente el FFmpeg del sistema.

Se utiliza:

```
ffmpeg-android-maker
```

Repositorio:

https://github.com/Javernaut/ffmpeg-android-maker

---

## Compilar FFmpeg

Ejecutar:

```bash
docker run --rm \
  -v $(pwd):/mnt/ffmpeg-android-maker \
  -e FAM_ARGS="--abis=arm64-v8a" \
  javernaut/ffmpeg-android-maker
```

Esto genera:

```
build/
└── ffmpeg/
    └── arm64-v8a/
        ├── bin/
        │   ├── ffmpeg
        │   └── ffprobe
        │
        └── lib/
            ├── libavcodec.so
            ├── libavformat.so
            ├── libavutil.so
            ├── libavfilter.so
            ├── libswscale.so
            └── libswresample.so
```

---

# Librerías FFmpeg (.so)

Las librerías necesarias deben copiarse a:

```
libs/
```

Ejemplo:

```
libs/
└── arm64-v8a/
    ├── libavcodec.so
    ├── libavformat.so
    ├── libavutil.so
    ├── libavfilter.so
    ├── libswscale.so
    └── libswresample.so
```

Estas librerías son empaquetadas dentro del APK.

---

# Assets

La carpeta:

```
assets/
```

contiene recursos usados por la aplicación.

Ejemplo:

```
assets/
├── icon.png
├── logo.png
└── images/
```

Si agregas nuevos archivos aquí, vuelve a compilar:

```bash
buildozer android clean
buildozer android debug
```

---

# Limpiar compilaciones

Si hay problemas con Buildozer:

```bash
buildozer android clean
```

Si continúa:

```bash
rm -rf .buildozer
rm -rf bin
```

Después:

```bash
buildozer android debug
```

---

# Problemas comunes

## FFmpeg no encontrado

Verificar que el APK contiene las librerías:

```bash
unzip -l bin/*.apk | grep ffmpeg
```

---

## Encoder MP3 no disponible

El FFmpeg usado en Android no incluye todos los encoders.

La aplicación usa:

```
bestaudio[ext=m4a]
```

para evitar conversiones innecesarias.

---

## Error de permisos Android

Android moderno usa Storage Access Framework.

La aplicación no escribe directamente en:

```
/storage/emulated/0/
```

El usuario debe seleccionar una carpeta mediante el selector del sistema.

---

# Desarrollo recomendado

Durante desarrollo:

```bash
python main.py
```

Para probar Android:

```bash
buildozer android debug deploy run
```

Para revisar errores:

```bash
buildozer android logcat
```

---

# Tecnologías usadas

- Python
- Kivy
- yt-dlp
- FFmpeg
- Buildozer
- python-for-android
- PyJNIus
