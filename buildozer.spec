[app]
# (1) Nombre de la app en Android
title = BUENAS
package.name = buenas
package.domain = org.buenas

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = banderas/*

# (2) Aquí le indicamos dónde está el logo
icon.filename = %(source.dir)s/logo.png

version = 1.0
requirements = python3,kivy==2.3.0,plyer,android

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, RECORD_AUDIO, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1