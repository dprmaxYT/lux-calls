import customtkinter as ctk
import socket
import threading
import json
import pyaudio
import ssl
import requests
import random

STUN_SERVER = 'stun.l.google.com'
STUN_PORT = 19302

class P2PCommunicationApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Comunicación P2P")
        self.root.geometry("400x600")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.public_ip, self.public_port = self.get_public_address()
        self.current_call = None
        self.is_muted = False
        
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('0.0.0.0', 0))
        self.local_port = self.udp_socket.getsockname()[1]

        self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        self.setup_audio()
        self.setup_ui()

    def get_public_address(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b'', (STUN_SERVER, STUN_PORT))
        data, _ = sock.recvfrom(1024)
        ip = '.'.join([str(int(data[i])) for i in range(4, 8)])
        port = int.from_bytes(data[8:10], byteorder='big')
        return ip, port

    def setup_audio(self):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      output=True,
                                      frames_per_buffer=1024)

    def setup_ui(self):
        main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(main_frame, text=f"Tu ID: {self.public_ip}:{self.public_port}").pack(pady=10)

        self.other_id_entry = ctk.CTkEntry(main_frame, placeholder_text="ID:Puerto del otro usuario")
        self.other_id_entry.pack(pady=10)

        call_button = ctk.CTkButton(main_frame, text="Llamar", command=self.start_call)
        call_button.pack(pady=10)

        self.call_frame = ctk.CTkFrame(main_frame, corner_radius=10)

        self.other_user_label = ctk.CTkLabel(self.call_frame, text="", fg_color="black")
        self.other_user_label.pack(pady=10, fill="x")

        button_frame = ctk.CTkFrame(self.call_frame)
        button_frame.pack(pady=10)

        self.mute_button = ctk.CTkButton(button_frame, text="Silenciar", command=self.toggle_mute)
        self.mute_button.pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Colgar", command=self.end_call).pack(side="left", padx=5)

    def start_call(self):
        other_ip, other_port = self.other_id_entry.get().split(':')
        other_port = int(other_port)
        self.current_call = (other_ip, other_port)
        
        # Iniciar el proceso de hole punching
        threading.Thread(target=self.hole_punching, args=(other_ip, other_port), daemon=True).start()

    def hole_punching(self, other_ip, other_port):
        # Enviar paquetes al otro usuario para abrir el NAT
        for _ in range(5):
            self.udp_socket.sendto(b'hole_punch', (other_ip, other_port))
        
        # Esperar respuesta
        self.udp_socket.settimeout(10)
        try:
            data, addr = self.udp_socket.recvfrom(1024)
            if data == b'hole_punch':
                self.establish_connection(addr)
        except socket.timeout:
            print("No se pudo establecer la conexión")
        finally:
            self.udp_socket.settimeout(None)

    def establish_connection(self, addr):
        self.other_user_label.configure(text=f"Llamada con: {addr[0]}:{addr[1]}")
        self.call_frame.pack(pady=20, fill="both", expand=True)
        threading.Thread(target=self.handle_call, args=(addr,), daemon=True).start()
        threading.Thread(target=self.send_audio, args=(addr,), daemon=True).start()

    def handle_call(self, addr):
        while self.current_call:
            try:
                data, _ = self.udp_socket.recvfrom(1024)
                if not data:
                    break
                if not self.is_muted:
                    self.stream.write(data)
            except Exception as e:
                print(f"Error en la llamada: {e}")
                break
        self.end_call()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.mute_button.configure(text="Activar" if self.is_muted else "Silenciar")

    def end_call(self):
        self.current_call = None
        self.call_frame.pack_forget()

    def send_audio(self, addr):
        while self.current_call:
            if not self.is_muted:
                try:
                    data = self.stream.read(1024)
                    self.udp_socket.sendto(data, addr)
                except Exception as e:
                    print(f"Error enviando audio: {e}")
                    break

    def run(self):
        threading.Thread(target=self.listen_for_connections, daemon=True).start()
        self.root.mainloop()

    def listen_for_connections(self):
        while True:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                if data == b'hole_punch' and not self.current_call:
                    self.udp_socket.sendto(b'hole_punch', addr)
                    self.root.after(0, self.establish_connection, addr)
            except Exception as e:
                print(f"Error al escuchar conexiones: {e}")

if __name__ == "__main__":
    app = P2PCommunicationApp()
    app.run()
