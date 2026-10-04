import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
import os
import threading
import queue
import json
import platform
import subprocess
import sys

# Solicitar permisos nativos en Android al iniciar
def solicitar_permisos_android():
    if platform.system() == 'Android':
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.RECORD_AUDIO, Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE])
        except Exception as e:
            print(f"Error al solicitar permisos: {e}")

Window.softinput_mode = 'below_target'

class TecladoCirilico(GridLayout):
    def __init__(self, entrada_texto, **kwargs):
        super().__init__(**kwargs)
        self.cols = 7
        self.size_hint_y = 0.35
        self.spacing = 3
        self.entrada = entrada_texto
        
        teclas = [
            'Й', 'Ц', 'У', 'К', 'Е', 'Н', 'Г',
            'Ш', 'Щ', 'З', 'Х', 'Ъ', 'Ф', 'Ы',
            'В', 'А', 'П', 'Р', 'О', 'Л', 'Д',
            'Ж', 'Э', 'Я', 'Ч', 'С', 'М', 'И',
            'Т', 'Ь', 'Б', 'Ю', 'Ё', 'ESP', 'DEL'
        ]
        
        for t in teclas:
            color = (0.3, 0.3, 0.3, 1) if t not in ['ESP', 'DEL'] else (0.7, 0.3, 0.3, 1)
            btn = Button(text=t, background_color=color, font_size=16, bold=True)
            btn.bind(on_press=self.teclear)
            self.add_widget(btn)
            
    def teclear(self, instancia):
        if instancia.text == 'ESP':
            self.entrada.text += ' '
        elif instancia.text == 'DEL':
            self.entrada.text = self.entrada.text[:-1]
        else:
            self.entrada.text += instancia.text

    def actualizar_colores(self, tema_oscuro):
        for btn in self.children:
            if btn.text not in ['ESP', 'DEL']:
                btn.background_color = (0.15, 0.15, 0.15, 1) if tema_oscuro else (0.3, 0.3, 0.3, 1)

class BuenasApp(App):
    def build(self):
        # APLICAR NOMBRE Y LOGO DE LA APP EN PC
        self.title = 'BUENAS'
        self.icon = 'logo.png'
        
        solicitar_permisos_android()
        
        self.tema_oscuro = False
        self.grabando = False
        self.cola_audio = queue.Queue()
        
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        
        # --- FILA 1 ---
        caja_top = BoxLayout(size_hint_y=0.08, spacing=10)
        self.btn_tema = Button(text="MODO OSCURO", size_hint_x=0.5, font_size=14, bold=True)
        self.btn_tema.bind(on_press=self.alternar_tema)
        
        btn_limpiar = Button(text="BORRAR", size_hint_x=0.5, font_size=14, bold=True, background_color=(0.8, 0.2, 0.2, 1))
        btn_limpiar.bind(on_press=self.limpiar_textos)
        
        caja_top.add_widget(self.btn_tema)
        caja_top.add_widget(btn_limpiar)
        self.layout.add_widget(caja_top)
        
        # --- FILA 2 ---
        caja_idiomas = BoxLayout(size_hint_y=0.1, spacing=5)
        
        self.img_origen = Image(source=self.obtener_ruta_bandera('es'), size_hint_x=0.2)
        self.origen = Spinner(text='es', values=('es', 'en', 'ru'), font_size=16, bold=True, size_hint_x=0.3)
        
        btn_invertir = Button(text="<->", font_size=18, bold=True, size_hint_x=0.2, background_color=(0.4, 0.4, 0.4, 1))
        btn_invertir.bind(on_press=self.invertir_idiomas)
        
        self.destino = Spinner(text='ru', values=('es', 'en', 'ru'), font_size=16, bold=True, size_hint_x=0.3)
        self.img_destino = Image(source=self.obtener_ruta_bandera('ru'), size_hint_x=0.2)
        
        caja_idiomas.add_widget(self.img_origen)
        caja_idiomas.add_widget(self.origen)
        caja_idiomas.add_widget(btn_invertir)
        caja_idiomas.add_widget(self.destino)
        caja_idiomas.add_widget(self.img_destino)
        self.layout.add_widget(caja_idiomas)
        
        # --- FILA 3 ---
        self.entrada = TextInput(hint_text="Escribe o dicta aqui...", size_hint_y=0.23, font_size=20)
        self.salida = TextInput(hint_text="Traduccion...", size_hint_y=0.23, readonly=True, font_size=20)
        self.layout.add_widget(self.entrada)
        self.layout.add_widget(self.salida)
        
        # --- FILA 4 ---
        caja_acciones = BoxLayout(size_hint_y=0.1, spacing=5)
        
        btn_copiar = Button(text="COPIAR", size_hint_x=0.2, font_size=13, bold=True, background_color=(0.2, 0.5, 0.8, 1))
        btn_copiar.bind(on_press=self.copiar_texto)
        
        self.btn_mic = Button(text="DICTAR", size_hint_x=0.25, font_size=13, bold=True, background_color=(0.3, 0.3, 0.3, 1))
        self.btn_mic.bind(on_press=self.toggle_grabacion)
        
        btn_hablar = Button(text="LEER", size_hint_x=0.25, font_size=13, bold=True, background_color=(0.8, 0.5, 0.1, 1))
        btn_hablar.bind(on_press=self.hablar_traduccion)
        
        btn_traducir = Button(text="TRADUCIR", size_hint_x=0.3, font_size=15, bold=True, background_color=(0.1, 0.7, 0.3, 1))
        btn_traducir.bind(on_press=self.traducir)
        
        caja_acciones.add_widget(btn_copiar)
        caja_acciones.add_widget(self.btn_mic)
        caja_acciones.add_widget(btn_hablar)
        caja_acciones.add_widget(btn_traducir)
        self.layout.add_widget(caja_acciones)
        
        # --- FILA 5 ---
        self.teclado_ruso = TecladoCirilico(self.entrada)
        self.layout.add_widget(self.teclado_ruso)
        
        self.aplicar_tema()
        self.origen.bind(text=self.al_cambiar_origen)
        self.destino.bind(text=self.al_cambiar_destino)
        self.al_cambiar_origen(self.origen, self.origen.text)

        return self.layout

    # ==========================================
    # UTILIDADES DE INTERFAZ
    # ==========================================
    def alternar_tema(self, instancia):
        self.tema_oscuro = not self.tema_oscuro
        self.aplicar_tema()

    def aplicar_tema(self):
        if self.tema_oscuro:
            Window.clearcolor = (0.15, 0.15, 0.15, 1)
            self.btn_tema.text = "MODO CLARO"
            color_bg_texto = (0.25, 0.25, 0.25, 1)
            color_fuente = (1, 1, 1, 1)
        else:
            Window.clearcolor = (0.9, 0.9, 0.9, 1)
            self.btn_tema.text = "MODO OSCURO"
            color_bg_texto = (1, 1, 1, 1)
            color_fuente = (0, 0, 0, 1)
            
        self.entrada.background_color = color_bg_texto
        self.entrada.foreground_color = color_fuente
        self.salida.background_color = color_bg_texto
        self.salida.foreground_color = color_fuente
        self.teclado_ruso.actualizar_colores(self.tema_oscuro)

    def limpiar_textos(self, instancia):
        self.entrada.text = ""
        self.salida.text = ""

    def copiar_texto(self, instancia):
        if self.salida.text:
            Clipboard.copy(self.salida.text)

    def invertir_idiomas(self, instancia):
        if "Traduciendo..." in self.salida.text or "Error" in self.salida.text:
            return
            
        nuevo_origen = self.destino.text
        nuevo_destino = self.origen.text
        nuevo_texto_entrada = self.salida.text
        nuevo_texto_salida = self.entrada.text
        
        self.origen.text = nuevo_origen
        self.destino.text = nuevo_destino
        self.entrada.text = nuevo_texto_entrada
        self.salida.text = nuevo_texto_salida

    def obtener_ruta_bandera(self, cod_idioma):
        ruta = os.path.join("banderas", f"{cod_idioma}.png")
        return ruta if os.path.exists(ruta) else ""

    def al_cambiar_origen(self, spinner, texto):
        self.img_origen.source = self.obtener_ruta_bandera(texto)
        if texto == 'ru':
            self.teclado_ruso.disabled = False
            self.teclado_ruso.opacity = 1
        else:
            self.teclado_ruso.disabled = True
            self.teclado_ruso.opacity = 0.4

    def al_cambiar_destino(self, spinner, texto):
        self.img_destino.source = self.obtener_ruta_bandera(texto)

    # ==========================================
    # TRADUCCIÓN
    # ==========================================
    def traducir(self, instancia):
        texto = self.entrada.text.strip()
        if not texto: return
        
        self.salida.text = "Traduciendo..."
        t = threading.Thread(target=self._hilo_traduccion, args=(texto, self.origen.text, self.destino.text))
        t.daemon = True
        t.start()

    def _hilo_traduccion(self, texto, origen, destino):
        import argostranslate.translate
        try:
            trad = argostranslate.translate.translate(texto, origen, destino)
            Clock.schedule_once(lambda dt: self._actualizar_salida(trad), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._actualizar_salida(f"Error: {str(e)}"), 0)

    def _actualizar_salida(self, texto):
        self.salida.text = texto

    # ==========================================
    # TTS MULTIPLATAFORMA (UNIVERSAL)
    # ==========================================
    def hablar_traduccion(self, instancia):
        texto = self.salida.text.strip()
        idioma = self.destino.text
        
        if not texto or texto.startswith("Error") or texto == "Traduciendo...":
            return

        if platform.system() in ("Windows", "Linux", "Darwin"):
            # MODO PC: Escudo blindado contra desbordamientos de memoria
            script_aislado = """
import sys
try:
    import pyttsx3
    texto = sys.argv[1]
    idioma = sys.argv[2]
    
    engine = pyttsx3.init()
    claves = {
        'en': ['english', 'en-us', 'en-gb', 'zira', 'david', 'mark', 'hazel'],
        'es': ['spanish', 'es-es', 'es-mx', 'helena', 'sabina', 'laura', 'pablo'],
        'ru': ['russian', 'ru-ru', 'irina']
    }
    voces = engine.getProperty('voices')
    palabras_clave = claves.get(idioma, [])
    
    for v in voces:
        nombre = str(v.name).lower()
        id_voz = str(v.id).lower()
        if any(c in nombre or c in id_voz for c in palabras_clave):
            engine.setProperty('voice', v.id)
            break
            
    engine.say(texto)
    engine.runAndWait()
except Exception:
    sys.exit(1)
"""
            if hasattr(self, 'proceso_tts') and self.proceso_tts.poll() is None:
                try: self.proceso_tts.terminate()
                except: pass
            
            self.proceso_tts = subprocess.Popen([sys.executable, '-c', script_aislado, texto, idioma])
        else:
            # MODO ANDROID/iOS: Llamada nativa con Plyer
            try:
                from plyer import tts
                tts.speak(texto)
            except Exception as e:
                print(f"Error de TTS móvil: {e}")

    # ==========================================
    # STT (Vosk)
    # ==========================================
    def toggle_grabacion(self, instancia):
        if not self.grabando:
            self.btn_mic.background_color = (0.8, 0.2, 0.2, 1)
            self.btn_mic.text = "GRABANDO..."
            self.grabando = True
            t = threading.Thread(target=self.hilo_reconocimiento)
            t.daemon = True
            t.start()
        else:
            self.detener_grabacion()

    def detener_grabacion(self):
        self.grabando = False
        self.btn_mic.background_color = (0.3, 0.3, 0.3, 1)
        self.btn_mic.text = "DICTAR"

    def hilo_reconocimiento(self):
        try:
            import sounddevice as sd
            from vosk import Model, KaldiRecognizer
        except ImportError:
            Clock.schedule_once(lambda dt: self.mostrar_error("Faltan librerias STT"), 0)
            return

        mapa_idiomas = {'es': 'es', 'en': 'en-us', 'ru': 'ru'}
        idioma_actual = mapa_idiomas.get(self.origen.text, 'es')
        
        while not self.cola_audio.empty():
            try: self.cola_audio.get_nowait()
            except queue.Empty: break

        try:
            modelo = Model(lang=idioma_actual)
            rec = KaldiRecognizer(modelo, 16000)
            
            def callback(indata, frames, time, status):
                if self.grabando:
                    self.cola_audio.put(bytes(indata))

            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                                   channels=1, callback=callback):
                while self.grabando:
                    try:
                        data = self.cola_audio.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    
                    try:
                        if rec.AcceptWaveform(data):
                            resultado = json.loads(rec.Result())
                            texto = resultado.get("text", "").strip()
                            if texto:
                                Clock.schedule_once(lambda dt, t=texto: self.agregar_texto_dictado(t), 0)
                    except Exception:
                        pass

                try:
                    resultado_final = json.loads(rec.FinalResult())
                    texto_final = resultado_final.get("text", "").strip()
                    if texto_final:
                        Clock.schedule_once(lambda dt, t=texto_final: self.agregar_texto_dictado(t), 0)
                except Exception:
                    pass

        except Exception as e:
            print(f"Fallo STT: {e}")
        finally:
            Clock.schedule_once(lambda dt: self.detener_grabacion(), 0)

    def agregar_texto_dictado(self, texto):
        if self.entrada.text and not self.entrada.text.endswith(" "):
            self.entrada.text += " "
        self.entrada.text += texto

    def mostrar_error(self, mensaje):
        self.entrada.text = f"Error: {mensaje}"
        self.detener_grabacion()

    def on_stop(self):
        self.grabando = False
        if hasattr(self, 'proceso_tts') and self.proceso_tts.poll() is None:
            try:
                self.proceso_tts.terminate()
            except:
                pass

if __name__ == "__main__":
    BuenasApp().run()