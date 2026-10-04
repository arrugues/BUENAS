[app]
# (1) Nombre de la app en Android
title = BUENAS
package.name = buenas
package.domain = org.buenas

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = banderas/*,models/*

# (2) Aquí le indicamos dónde está el logo
icon.filename = %(source.dir)s/logo.png

version = 1.0

# Dependencias compatibles con Android sin conexión
requirements = python3,kivy==2.3.0,plyer,pyjnius

# Orientación y pantalla completa
orientation = portrait
fullscreen = 0

# Permisos necesarios
android.permissions = INTERNET,RECORD_AUDIO,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Configuración de Android
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

# Características
android.features = android.hardware.microphone

# Librerías nativas de Android
android.gradle_dependencies = 

# Usar la API de Android para funciones nativas
android.add_src = 

[buildozer]
log_level = 2
warn_on_root = 1
