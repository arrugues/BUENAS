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

# ==========================================
# TRADUCCIÓN OFFLINE CON MODELS LOCALES
# ==========================================
class TranslatorOffline:
    """Traductor offline usando modelos locales"""
    
    def __init__(self):
        self.loaded = False
        self.translator = None
        self.init_translator()
    
    def init_translator(self):
        try:
            import argos_translate_offline as ato
            self.translator = ato
            self.loaded = True
        except ImportError:
            try:
                # Fallback: usar una versión mínima de traducción
                import argostranslate.package
                argostranslate.package.update_package_index()
                self.loaded = True
            except ImportError:
                self.loaded = False
    
    def translate(self, texto, origen, destino):
        """Traduce texto offline"""
        if not self.loaded:
            return f"Error: Módulo de traducción no disponible"
        
        try:
            # Mapeo de códigos de idioma
            lang_map = {
                'es': 'es',
                'en': 'en',
                'ru': 'ru'
            }
            
            from_lang = lang_map.get(origen, origen)
            to_lang = lang_map.get(destino, destino)
            
            # Intentar traducir
            try:
                import argostranslate.translate
                resultado = argostranslate.translate.translate(texto, from_lang, to_lang)
                return resultado
            except Exception as e:
                # Si falla, retornar texto original
                return texto
        except Exception as e:
            return f"Error: {str(e)}"


# ==========================================
# TTS OFFLINE MULTIPLATAFORMA
# ==========================================
class TTSOffline:
    """Sistema de síntesis de voz offline"""
    
    def __init__(self):
        self.proceso_tts = None
    
    def speak(self, texto, idioma='es'):
        """Habla el texto en el idioma especificado"""
        
        if platform.system() in ("Windows", "Linux", "Darwin"):
            self._speak_desktop(texto, idioma)
        else:
            # Android: usar Plyer
            self._speak_android(texto, idioma)
    
    def _speak_desktop(self, texto, idioma):
        """TTS para desktop usando pyttsx3"""
        script = f"""
import sys
try:
    import pyttsx3
    texto = sys.argv[1]
    idioma = sys.argv[2]
    
    engine = pyttsx3.init()
    claves = {{
        'en': ['english', 'en-us', 'en-gb', 'zira', 'david', 'mark', 'hazel'],
        'es': ['spanish', 'es-es', 'es-mx', 'helena', 'sabina', 'laura', 'pablo'],
        'ru': ['russian', 'ru-ru', 'irina']
    }}
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
except Exception as e:
    print(f"Error TTS: {{e}}")
    sys.exit(1)
"""
        try:
            if hasattr(self, 'proceso_tts') and self.proceso_tts and self.proceso_tts.poll() is None:
                self.proceso_tts.terminate()
            self.proceso_tts = subprocess.Popen([sys.executable, '-c', script, texto, idioma])
        except Exception as e:
            print(f"Error en TTS desktop: {e}")
    
    def _speak_android(self, texto, idioma):
        """TTS para Android usando Plyer"""
        try:
            from plyer import tts
            tts.speak(text=texto)
        except Exception as e:
            print(f"Error TTS Android: {e}")
    
    def stop(self):
        """Detiene la reproducción"""
        if self.proceso_tts and self.proceso_tts.poll() is None:
            try:
                self.proceso_tts.terminate()
            except:
                pass


# ==========================================
# STT OFFLINE (DICTADO)
# ==========================================
class STTOffline:
    """Sistema de reconocimiento de voz offline usando Vosk"""
    
    def __init__(self):
        self.grabando = False
        self.cola_audio = queue.Queue()
        self.recognizer = None
        self.init_recognizer()
    
    def init_recognizer(self):
        try:
            from vosk import Model, KaldiRecognizer
            self.KaldiRecognizer = KaldiRecognizer
            self.Model = Model
        except ImportError:
            self.recognizer = None
    
    def recognise(self, idioma='es', callback=None):
        """Inicia el reconocimiento de voz"""
        try:
            import sounddevice as sd
        except ImportError:
            if callback:
                callback("error", "Faltan librerías de audio")
            return
        
        threading.Thread(target=self._thread_recognize, args=(idioma, callback), daemon=True).start()
    
    def _thread_recognize(self, idioma, callback):
        """Thread de reconocimiento"""
        try:
            import sounddevice as sd
            from vosk import Model, KaldiRecognizer
            
            mapa_idiomas = {'es': 'es', 'en': 'en-us', 'ru': 'ru'}
            idioma_actual = mapa_idiomas.get(idioma, 'es')
            
            # Limpiar cola
            while not self.cola_audio.empty():
                try:
                    self.cola_audio.get_nowait()
                except queue.Empty:
                    break
            
            # Cargar modelo
            try:
                modelo = Model(lang=idioma_actual)
                rec = KaldiRecognizer(modelo, 16000)
            except Exception as e:
                if callback:
                    callback("error", f"Modelo no disponible: {idioma_actual}")
                return
            
            def callback_audio(indata, frames, time, status):
                if self.grabando:
                    self.cola_audio.put(bytes(indata))
            
            # Capturar audio
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                                   channels=1, callback=callback_audio):
                while self.grabando:
                    try:
                        data = self.cola_audio.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    
                    try:
                        if rec.AcceptWaveform(data):
                            resultado = json.loads(rec.Result())
                            texto = resultado.get("text", "").strip()
                            if texto and callback:
                                callback("text", texto)
                    except Exception:
                        pass
            
            # Resultado final
            try:
                resultado_final = json.loads(rec.FinalResult())
                texto_final = resultado_final.get("text", "").strip()
                if texto_final and callback:
                    callback("final", texto_final)
            except Exception:
                pass
        
        except Exception as e:
            print(f"Error STT: {e}")
            if callback:
                callback("error", str(e))


# ==========================================
# SOLICITAR PERMISOS ANDROID
# ==========================================
def solicitar_permisos_android():
    if platform.system() == 'Android':
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.RECORD_AUDIO,
                Permission.INTERNET,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ])
        except Exception as e:
            print(f"Error al solicitar permisos: {e}")


Window.softinput_mode = 'below_target'


# ==========================================
# INTERFAZ GRÁFICA
# ==========================================
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
        self.title = 'BUENAS'
        self.icon = 'logo.png'
        
        solicitar_permisos_android()
        
        # Inicializar componentes offline
        self.translator = TranslatorOffline()
        self.tts = TTSOffline()
        self.stt = STTOffline()
        
        self.tema_oscuro = False
        self.grabando = False
        
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
    # TRADUCCIÓN OFFLINE
    # ==========================================
    def traducir(self, instancia):
        texto = self.entrada.text.strip()
        if not texto:
            return
        
        self.salida.text = "Traduciendo..."
        t = threading.Thread(target=self._hilo_traduccion, args=(texto, self.origen.text, self.destino.text))
        t.daemon = True
        t.start()
    
    def _hilo_traduccion(self, texto, origen, destino):
        try:
            resultado = self.translator.translate(texto, origen, destino)
            Clock.schedule_once(lambda dt: self._actualizar_salida(resultado), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._actualizar_salida(f"Error: {str(e)}"), 0)
    
    def _actualizar_salida(self, texto):
        self.salida.text = texto
    
    # ==========================================
    # TTS OFFLINE
    # ==========================================
    def hablar_traduccion(self, instancia):
        texto = self.salida.text.strip()
        idioma = self.destino.text
        
        if not texto or texto.startswith("Error") or texto == "Traduciendo...":
            return
        
        threading.Thread(target=lambda: self.tts.speak(texto, idioma), daemon=True).start()
    
    # ==========================================
    # STT OFFLINE (DICTADO)
    # ==========================================
    def toggle_grabacion(self, instancia):
        if not self.grabando:
            self.btn_mic.background_color = (0.8, 0.2, 0.2, 1)
            self.btn_mic.text = "GRABANDO..."
            self.grabando = True
            self.stt.grabando = True
            self.stt.recognise(self.origen.text, self._callback_stt)
        else:
            self.detener_grabacion()
    
    def detener_grabacion(self):
        self.grabando = False
        self.stt.grabando = False
        self.btn_mic.background_color = (0.3, 0.3, 0.3, 1)
        self.btn_mic.text = "DICTAR"
    
    def _callback_stt(self, tipo, texto):
        """Callback para el reconocimiento de voz"""
        if tipo == "text":
            Clock.schedule_once(lambda dt: self._agregar_texto_dictado_parcial(texto), 0)
        elif tipo == "final":
            Clock.schedule_once(lambda dt: self._agregar_texto_dictado_final(texto), 0)
        elif tipo == "error":
            Clock.schedule_once(lambda dt: self._mostrar_error(texto), 0)
    
    def _agregar_texto_dictado_parcial(self, texto):
        """Agrega texto parcial del reconocimiento"""
        if self.entrada.text and not self.entrada.text.endswith(" "):
            self.entrada.text += " "
        self.entrada.text += texto
    
    def _agregar_texto_dictado_final(self, texto):
        """Agrega texto final del reconocimiento"""
        if self.entrada.text and not self.entrada.text.endswith(" "):
            self.entrada.text += " "
        self.entrada.text += texto
        self.detener_grabacion()
    
    def _mostrar_error(self, mensaje):
        self.salida.text = f"Error: {mensaje}"
        self.detener_grabacion()
    
    def on_stop(self):
        self.grabando = False
        self.stt.grabando = False
        if self.tts.proceso_tts and self.tts.proceso_tts.poll() is None:
            try:
                self.tts.proceso_tts.terminate()
            except:
                pass


if __name__ == "__main__":
    BuenasApp().run()
