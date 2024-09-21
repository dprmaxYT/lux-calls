import customtkinter as ctk
import socket
import threading
import pyaudio
import pickle
import nacl.utils
from nacl.public import PrivateKey, Box

class P2PCommunicationApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Comunicación P2P Mejorada")
        self.root.geometry("400x600")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.user_id = socket.gethostbyname(socket.gethostname())
        self.current_call = None
        self.is_muted = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Cambiado a UDP
        self.socket.bind((self.user_id, 0))
        self.port = self.socket.getsockname()[1]

        # Generación de claves para cifrado
        self.private_key = PrivateKey.generate()
        self.public_key = self.private_key.public_key

        self.setup_audio()
        self.setup_ui()

        threading.Thread(target=self.listen_for_connections, daemon=True).start()

    def setup_audio(self):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      output=True,
                                      frames_per_buffer=1024)

    def setup_ui(self):
        # ... (el resto del setup_ui permanece igual)
        pass

    def start_call(self):
        other_id, port = self.other_id_entry.get().split(':')
        port = int(port)
        self.current_call = (other_id, port)
        self.other_user_label.configure(text=f"Llamada con: {other_id}")
        self.call_frame.pack(pady=20, fill="both", expand=True)
        
        # Enviar clave pública
        self.socket.sendto(pickle.dumps(self.public_key), self.current_call)
        
        threading.Thread(target=self.handle_call, daemon=True).start()
        threading.Thread(target=self.send_audio, daemon=True).start()

    def listen_for_connections(self):
        while True:
            data, addr = self.socket.recvfrom(1024)
            if not self.current_call:
                self.current_call = addr
                self.root.after(0, self.update_ui_for_incoming_call, addr[0])
                
                # Recibir clave pública
                self.other_public_key = pickle.loads(data)
                
                # Enviar nuestra clave pública
                self.socket.sendto(pickle.dumps(self.public_key), addr)
                
                threading.Thread(target=self.handle_call, daemon=True).start()
                threading.Thread(target=self.send_audio, daemon=True).start()

    def update_ui_for_incoming_call(self, addr):
        self.other_user_label.configure(text=f"Llamada con: {addr}")
        self.call_frame.pack(pady=20, fill="both", expand=True)

    def handle_call(self):
        while self.current_call:
            try:
                data, addr = self.socket.recvfrom(1024)
                if addr == self.current_call:
                    decrypted_data = Box(self.private_key, self.other_public_key).decrypt(data)
                    if not self.is_muted:
                        self.stream.write(decrypted_data)
            except Exception as e:
                print(f"Error en handle_call: {e}")
                break

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.mute_button.configure(text="Activar" if self.is_muted else "Silenciar")

    def end_call(self):
        self.current_call = None
        self.call_frame.pack_forget()

    def send_audio(self):
        while self.current_call and not self.is_muted:
            try:
                data = self.stream.read(1024)
                encrypted_data = Box(self.private_key, self.other_public_key).encrypt(data)
                self.socket.sendto(encrypted_data, self.current_call)
            except Exception as e:
                print(f"Error en send_audio: {e}")
                break

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = P2PCommunicationApp()
    app.run()
