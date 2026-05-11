import json, time, requests
import os
from datetime import datetime
from PIL import Image
from io import BytesIO

import pyttsx3, pyaudio
from vosk import Model, KaldiRecognizer

class RickMortyAssistant:
    def __init__(self, model_path="model"):
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 180)
        self.tts.setProperty('volume', 0.9)

        # выбор русского языка
        voices = self.tts.getProperty('voices')
        for voice in voices:
            if 'russian' in voice.name.lower() or 'ru' in str(voice.languages).lower():
                self.tts.setProperty('voice', voice.id)
                print(f"Используется голос: {voice.name}")
                break

        # распознавание речи
        print(f"Загрузка модели Vosk...")
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)

        # настройка микрофона
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )

        self.current_character = None
        self.current_image = None

        self.images_dir = "rickandmorty_images"
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)

        self.commands = {
            "случайный": self.get_random_character,
            "сохранить": self.save_image,
            "эпизод": self.get_first_episode,
            "показать": self.show_image,
            "разрешение": self.get_image_resolution,
            "выход": self.exit_assistant,
            "стоп": self.exit_assistant
        }

    def speak(self, text):
        print(f"Ассистент: {text}")
        self.tts.say(text)
        self.tts.runAndWait()

    def listen(self):
        print("Слушаю...")
        audio_data = b''

        # запись аудио
        for i in range(int(16000 / 4000 * 3)):
            data = self.stream.read(4000, exception_on_overflow=False)
            audio_data += data

        if self.recognizer.AcceptWaveform(audio_data):
            result = json.loads(self.recognizer.Result())
            text = result.get('text', '')
            if text:
                print(f"Распознано: {text}")
                return text.lower()
        return ""
    def recognize_command(self, text):
        for cmdName in self.commands:
            if cmdName in text:
                return cmdName
        return None

    def get_character(self, character_id):
        try:
            url = f"https://rickandmortyapi.com/api/character/{character_id}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"Ошибка API: {e}")
            return None

    def download_image(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                return img
            return None
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            return None

    def get_random_character(self):
        import random
        random_id = random.randint(1, 826)
        character = self.get_character(random_id)

        if character:
            self.current_character = character
            name = character.get('name', 'неизвестно')
            status = character.get('status', 'неизвестно')
            species = character.get('species', 'неизвестно')

            # скачиваем изображение
            img_url = character.get('image', 'неизвестно')
            if img_url:
                self.current_image = self.download_image(img_url)

            self.speak(f"Персонаж {name}. Статус: {status}. Вид: {species}")
        else:
            self.speak("Не удалось получить данные о персонаже")

    def save_image(self):
        if self.current_image:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if self.current_character:
                name = self.current_character.get('name', 'неизвестно')
                filename = f"{self.images_dir}/{name}_{timestamp}.png"
            else:
                filename = f"{self.images_dir}/Персонаж_{timestamp}.png"

            self.current_image.save(filename)
            self.speak(f"Изображение сохранено в папку {self.images_dir}")
            print(f"Сохранено: {filename}")
        else:
            self.speak("Нет загруженного изображения. Сначала получите случайного персонажа")

    def get_first_episode(self):
        if self.current_character:
            episode_url = self.current_character.get('episode', [])
            if episode_url:
                first_episode_url = episode_url[0]
                try:
                    response = requests.get(first_episode_url)
                    if response.status_code == 200:
                        episode_data = response.json()
                        episode_name = episode_data.get('name', 'неизвестно')
                        episode_code = episode_data.get('episode', 'неизвестно')
                        self.speak(f"Первое появление в эпизоде {episode_code}: {episode_name}")
                    else:
                        self.speak("Не удалось получить данные об эпизоде")
                except Exception as e:
                    self.speak("Ошибка при получении эпизода")
            else:
                self.speak("Нет информации об эпизодах")
        else:
            self.speak("Нет текущего персонажа. Сначала получите случайного")

    def show_image(self):
        if self.current_image:
            temp_filename = "temp_character.png"
            self.current_image.save(temp_filename)
            os.startfile(temp_filename)
            self.speak("Изображение открыто")
            time.sleep(4)

            # удаляем временный файл
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
                self.speak("Изображение закрыто")
        else:
            self.speak("Нет загруженного изображения. Сначала получите случайного персонажа")

    def get_image_resolution(self):
        if self.current_image:
            width, height = self.current_image.size
            self.speak(f"Разрешение изображения: {width} на {height} пикселей")
        else:
            self.speak("Нет загруженного изображения. Сначала получите случайного персонажа")

    def exit_assistant(self):
        self.speak("До свидания!")
        self.cleanup()
        exit(0)

    def cleanup(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

    def run(self):
        self.speak(
            "Ассистент по вселенной Рика и Морти запущен. Доступные команды: "
            "случайный персонаж, сохранить изображение, "
            "эпизод первого появления, показать картинку, разрешение изображения")

        while True:
            try:
                text = self.listen()
                if text:
                    command = self.recognize_command(text)
                    if command:
                        self.commands[command]()
                    else:
                        self.speak(
                            "Команда не распознана. Доступные команды: случайный, "
                            "сохранить, эпизод, показать, разрешение")
                time.sleep(0.7)
            except KeyboardInterrupt:
                self.exit_assistant()
            except Exception as e:
                print(f"Ошибка: {e}")
                self.speak("Произошла ошибка")
                self.cleanup()
                break


if __name__ == "__main__":
    assistant = RickMortyAssistant()
    assistant.run()