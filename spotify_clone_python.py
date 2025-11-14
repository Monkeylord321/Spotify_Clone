import os
import random
import threading
from pytubefix import YouTube
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.audio import SoundLoader
from kivy.clock import mainthread
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp


DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class SpotifyClone(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=10, padding=10, **kwargs)

        self.playlist = []
        self.current_index = -1
        self.current_sound = None

        # ================================================================
        # HEADER + SEARCH
        # ================================================================
        header = BoxLayout(size_hint=(1, 0.08), spacing=10)
        self.search_input = TextInput(
            hint_text="Search playlist...",
            multiline=False,
            size_hint=(1, 1),
        )
        header.add_widget(self.search_input)
        self.search_input.bind(text=self.filter_playlist)
        self.add_widget(header)

        # ================================================================
        # STATUS LABEL
        # ================================================================
        self.status_label = Label(text="Ready", size_hint=(1, 0.08))
        self.add_widget(self.status_label)

        # ================================================================
        # PLAYLIST VIEW (SCROLL)
        # ================================================================
        scroll = ScrollView(size_hint=(1, 0.55))
        self.playlist_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.playlist_box.bind(minimum_height=self.playlist_box.setter("height"))
        scroll.add_widget(self.playlist_box)
        self.add_widget(scroll)

        # ================================================================
        # PLAYER CONTROLS
        # ================================================================
        controls = BoxLayout(size_hint=(1, 0.10), spacing=10)

        controls.add_widget(Button(
            text="Previous",
            font_size=18,
            on_release=self.prev_song,
            background_normal='',
            background_color=(0.15, 0.15, 0.15, 1),
            color=(1, 1, 1, 1)
        ))

        controls.add_widget(Button(
            text="Play / Pause",
            font_size=18,
            on_release=self.play_pause,
            background_normal='',
            background_color=(0.20, 0.20, 0.20, 1),
            color=(1, 1, 1, 1)
        ))

        controls.add_widget(Button(
            text="Next",
            font_size=18,
            on_release=self.next_song,
            background_normal='',
            background_color=(0.15, 0.15, 0.15, 1),
            color=(1, 1, 1, 1)
        ))

        controls.add_widget(Button(
            text="Shuffle",
            font_size=18,
            on_release=self.shuffle_songs,
            background_normal='',
            background_color=(0.25, 0.25, 0.25, 1),
            color=(1, 1, 1, 1)
        ))

        self.add_widget(controls)

        # ================================================================
        # URL INPUT + ADD BUTTON (SMALLER)
        # ================================================================
        add_row = BoxLayout(size_hint=(1, 0.07), spacing=10)

        self.url_input = TextInput(
            hint_text="YouTube URL",
            multiline=False,
            size_hint=(0.75, 1),
            font_size=14,
        )
        add_row.add_widget(self.url_input)

        add_row.add_widget(Button(
            text="Add",
            size_hint=(0.25, 1),
            on_release=self.add_song
        ))

        self.add_widget(add_row)

        self.update_playlist_display()

    # ================================================================
    # PLAYLIST UI UPDATES
    # ================================================================
    def update_playlist_display(self, filtered=None):
        self.playlist_box.clear_widgets()
        items = filtered if filtered is not None else self.playlist

        for i, song in enumerate(items):
            btn = Button(
                text=os.path.basename(song),
                size_hint_y=None,
                height=dp(42),
                font_size=14,
                background_normal='',
                background_color=(0.2, 0.2, 0.2, 1),
                color=(1, 1, 1, 1)
            )
            btn.bind(on_release=lambda b, index=i: self.play_selected(index))
            self.playlist_box.add_widget(btn)

    def filter_playlist(self, *args):
        q = self.search_input.text.lower()
        filtered = [s for s in self.playlist if q in s.lower()]
        self.update_playlist_display(filtered)

    # ================================================================
    # DOWNLOAD & ADD
    # ================================================================
    def add_song(self, *args):
        url = self.url_input.text.strip()
        if not url:
            self.status_label.text = "Enter a URL first."
            return

        self.url_input.text = ""  # ✔ auto-clear input field
        self.status_label.text = "Downloading..."

        threading.Thread(target=self.download_thread, args=(url,), daemon=True).start()

    def download_thread(self, url):
        try:
            yt = YouTube(url)
            audio = yt.streams.filter(only_audio=True).first()
            temp_file = audio.download(output_path=DOWNLOAD_DIR, filename="temp")

            output_file = os.path.join(DOWNLOAD_DIR, f"{yt.title}.mp3")

            cmd = f'ffmpeg -y -i "{temp_file}" "{output_file}"'
            os.system(cmd)
            os.remove(temp_file)

            self.add_to_playlist(output_file)

        except Exception as e:
            self.set_status(f"Error: {e}")

    @mainthread
    def add_to_playlist(self, file):
        self.playlist.append(file)
        self.update_playlist_display()
        self.set_status("Song added!")

    @mainthread
    def set_status(self, text):
        self.status_label.text = text

    # ================================================================
    # PLAYBACK
    # ================================================================
    def play_selected(self, index):
        self.current_index = index
        self.play_song()

    def play_song(self):
        if not self.playlist:
            self.set_status("Playlist empty.")
            return

        if self.current_sound:
            self.current_sound.stop()

        file = self.playlist[self.current_index]
        self.current_sound = SoundLoader.load(file)

        if self.current_sound:
            self.current_sound.play()
            self.set_status(f"Playing: {os.path.basename(file)}")
        else:
            self.set_status("Could not play audio.")

    def play_pause(self, *args):
        if not self.current_sound:
            if self.current_index == -1 and self.playlist:
                self.current_index = 0
            self.play_song()
            return

        if self.current_sound.state == "play":
            self.current_sound.stop()
            self.set_status("Paused")
        else:
            self.current_sound.play()
            self.set_status("Playing")

    def next_song(self, *args):
        if not self.playlist:
            return
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.play_song()

    def prev_song(self, *args):
        if not self.playlist:
            return
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play_song()

    def shuffle_songs(self, *args):
        random.shuffle(self.playlist)
        self.update_playlist_display()
        self.set_status("Shuffled!")


class SpotifyCloneApp(App):
    def build(self):
        return SpotifyClone()


if __name__ == "__main__":
    SpotifyCloneApp().run()
