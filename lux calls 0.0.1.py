import customtkinter as ctk
import socket
import threading
import json
import pyaudio

class P2PCommunicationApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Comunicación P2P")
        self.root.geometry("400x600")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.user_id = socket.gethostbyname(socket.gethostname())
        self.current_call = None
        self.is_muted = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.user_id, 0))
        self.port = self.socket.getsockname()[1]

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
        main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(main_frame, text=f"Tu ID: {self.user_id}:{self.port}").pack(pady=10)

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
        other_id, port = self.other_id_entry.get().split(':')
        port = int(port)
        self.current_call = (other_id, port)
        try:
            self.socket.connect(self.current_call)
            self.other_user_label.configure(text=f"Llamada con: {other_id}")
            self.call_frame.pack(pady=20, fill="both", expand=True)
            threading.Thread(target=self.handle_call, args=(self.socket,), daemon=True).start()
        except Exception as e:
            print(f"Error al conectar: {e}")

    def listen_for_connections(self):
        self.socket.listen(1)
        while True:
            conn, addr = self.socket.accept()
            self.current_call = addr
            self.root.after(0, self.update_ui_for_incoming_call, addr[0])
            threading.Thread(target=self.handle_call, args=(conn,), daemon=True).start()

    def update_ui_for_incoming_call(self, addr):
        self.other_user_label.configure(text=f"Llamada con: {addr}")
        self.call_frame.pack(pady=20, fill="both", expand=True)

    def handle_call(self, conn):
        while self.current_call:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                if not self.is_muted:
                    self.stream.write(data)
            except:
                break
        conn.close()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.mute_button.configure(text="Activar" if self.is_muted else "Silenciar")

    def end_call(self):
        if self.current_call:
            self.socket.close()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind((self.user_id, self.port))
            threading.Thread(target=self.listen_for_connections, daemon=True).start()
        self.current_call = None
        self.call_frame.pack_forget()

    def send_audio(self):
        while self.current_call and not self.is_muted:
            try:
                data = self.stream.read(1024)
                self.socket.sendall(data)
            except:
                break

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = P2PCommunicationApp()
    app.run()
