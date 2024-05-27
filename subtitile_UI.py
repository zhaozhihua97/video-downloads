import pytube.helpers
import whisper
import json
import time
import os
import re
from pytube import YouTube
import os
import re
from gpt import text_generation
import translator
from tqdm import tqdm
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter.ttk import Progressbar
import threading
import sys

def YoutubeVideoDownload(video_url):
    yt = YouTube(video_url)
    # for e in yt.streams:
    #     print(e)
    # video = video.streams.get_highest_resolution()
    video = yt.streams.filter(only_video=True, file_extension='mp4').first()
    audio = yt.streams.filter(only_audio=True).first()
    # video_dir = re.sub(r'\W', '_', video.title)
    video_dir = pytube.helpers.safe_filename(video.title)
    video_title = pytube.helpers.safe_filename(video.title)
    URL_DOWNLOAD_DIR = os.path.join(save_directory.get(), video_dir)
    os.makedirs(URL_DOWNLOAD_DIR, exist_ok=True)
    with open(os.path.join(URL_DOWNLOAD_DIR, 'info.txt'), 'w') as f:
        f.writelines(f'{video_url}\n')

    video_path = os.path.join(URL_DOWNLOAD_DIR, f'video_{video.resolution}_{video_title}.{video.mime_type.split("/")[1]}')
    audio_path = os.path.join(URL_DOWNLOAD_DIR, f'audio_{audio.abr}_{video_title}.{audio.mime_type.split("/")[1]}')
    if not os.path.exists(video_path):
        try:
            video_path = video.download(URL_DOWNLOAD_DIR, filename_prefix=f'video_{video.resolution}_')
        except Exception as e:
            print(f"Unable to download video at this time! {e}")
        print("Video downloaded!")
    else:
        print("video existed")
    if not os.path.exists(audio_path):
        try:
            audio_path = audio.download(URL_DOWNLOAD_DIR, filename_prefix=f'audio_{audio.abr}_')
        except Exception as e:
            print(f"Failed to download audio, {e}")
        print("audio was downloaded successfully")
    else:
        print('audio existed')

    return URL_DOWNLOAD_DIR, video_path, audio_path


def model_parm(model):
    param_count = sum(p.numel() for p in model.parameters())
    print("参数数量:", param_count)


def transcribe(url_path, audio_path, model_size, target_lang='en'):
    def convert_json_to_srt(data, srt_file):
        # Open the SRT file to write
        with open(srt_file, 'w') as file:
            for i, entry in enumerate(data['segments'], start=1):
                start = convert_to_srt_time(entry['start'])
                end = convert_to_srt_time(entry['end'])
                text = entry['text']

                # Write each subtitle entry
                file.write(f"{i}\n")
                file.write(f"{start} --> {end}\n")
                file.write(f"{text}\n\n")

    def convert_to_srt_time(seconds):
        """Converts time in seconds to SRT format HH:MM:SS,MS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int(seconds % 1 * 1000)
        return f"{hours:02}:{minutes:02}:{int(seconds):02},{milliseconds:03}"

    root_path = os.path.split(audio_path)
    audio_name = root_path[1].split('.')[0]
    transcribed_text_path = os.path.join(root_path[0], f'{audio_name}_transcribed_text.json')
    srt_path = os.path.join(root_path[0], f'{audio_name}_subtitles.srt')

    start_time = time.time()
    if not os.path.exists(transcribed_text_path):
        # print(whisper.available_models())
        model = whisper.load_model(model_size)
        print(f'model is loaded, the loaded time:{time.time() - start_time}')
        transcribe_time = time.time()
        result = model.transcribe(audio_path)
        with open(transcribed_text_path, 'w') as file:
            json.dump(result, file)
        print(f'the audio completed transcription. the transcription time:{time.time() - transcribe_time}')
    else:
        with open(transcribed_text_path, 'r') as file:
            result = json.load(file)
        print(f'the transcription file already exists, the transcription time:{time.time() - start_time}')


    video_info = open(os.path.join(url_path, 'info.txt'), 'r')
    video_url = video_info.readline()
    video_detail_path = os.path.join(save_directory.get(), f'video_detail.txt')
    text = result['text']
    if os.path.exists(video_detail_path):
        video_detail = open(video_detail_path, 'r', encoding='utf-8').readlines()
        if video_url not in video_detail:
            answer = text_generation(result['text'])
            with open(video_detail_path, 'a', encoding='utf-8') as f:
                f.write(video_url)
                f.write(f'============={audio_name}==============\n')
                f.write(f'{text}\n')
                f.write(f'{answer}\n')
                f.write('----------------------------------------\n')
    else:
        answer = text_generation(result['text'])
        with open(video_detail_path, 'a', encoding='utf-8') as f:
            f.write(video_url)
            f.write(f'============={audio_name}==============\n')
            f.write(f'{text}\n')
            f.write(f'{answer}\n')
            f.write('----------------------------------------\n')

    # Usage
    if not os.path.exists(srt_path):
        convert_json_to_srt(result, srt_path)
        print(f'successfully converted to srt file-{srt_path}')
    else:
        print(f'the SRT file, {srt_path}, already exists.')
    return srt_path


def swap_language(file_path, output_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    new_lines = []
    pattern = re.compile(r'^\d+$')  # Matches the subtitle number lines
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if pattern.match(line):  # Check if the line is a subtitle number
            new_lines.append(line + '\n')  # Subtitle number
            new_lines.append(lines[i + 1])  # Time codes
            # Assume the next two lines are the languages in the wrong order
            chinese = lines[i + 3].strip()
            english = lines[i + 2].strip()
            new_lines.append(chinese + '\n')
            new_lines.append(english + '\n')
            i += 4  # Move past this block
        else:
            i += 1  # Continue to next line

    with open(output_path, 'w', encoding='utf-8') as file:
        file.writelines(new_lines)


def translation4srt(srt_file, config, api_name='tencent', target_lang='zh'):

    trans = translator.Translator(**config)

    subtitles = []
    start_time = time.time()
    with open(srt_file, 'r', encoding='utf-8') as file:
        subtitle = {}
        lines = file.readlines()
        # bar = TqdmToLabel(progress_label, total=len(lines), desc='Translating subtitles', unit='lines')
        bar = tqdm(lines, desc='Translating subtitles', unit='lines')
        for line in bar:
            line = line.strip()
            if line.isdigit():
                if subtitle:
                    subtitles.append(subtitle)
                    subtitle = {}
                subtitle['index'] = line
            elif '-->' in line:
                subtitle['time'] = line
            elif line:
                if 'text' in subtitle:
                    subtitle['text'] += ' ' + line
                else:
                    subtitle['text'] = line
                    target_text = trans.translate(api_name, line, target_lang)
                    subtitle['target_text'] = target_text
        if subtitle:
            subtitles.append(subtitle)
    print(f'the {api_name} translation time:{time.time() - start_time}')
    new_srt_file = srt_file.replace('.srt', f'_{api_name}_{target_lang}.srt')
    with open(new_srt_file, 'w', encoding='utf-8') as file:
        pbar = tqdm(subtitles, desc='Writing translated subtitles', unit='subtitles')
        for subtitle in pbar:
            file.write(f"{subtitle['index']}\n")
            file.write(f"{subtitle['time']}\n")
            file.write(f"{subtitle['target_text']}\n")
            file.write(f"{subtitle['text']}\n\n")


def include_video(video_url, config, api_name='tencent', target_lang='zh'):
    url_path, video_path, audio_path = YoutubeVideoDownload(video_url)
    root_path = os.path.split(audio_path)
    audio_name = root_path[1].split('.')[0]
    srt_file = os.path.join(url_path, f'{audio_name}_subtitles.srt')
    translation_file = os.path.join(url_path, f'{audio_name}_subtitles_{api_name}_{target_lang}.srt')
    if not os.path.exists(srt_file):
        model_size = "large"
        srt_file = transcribe(url_path, audio_path, model_size)
        # srt_file = "E:\Englist NBA Video\The Richard Jefferson_Larry Show  Ep. 1\The Richard Jefferson_Larry Show Ep. 1.srt"
    if not os.path.exists(translation_file):
        translation4srt(srt_file, config, api_name=api_name, target_lang=target_lang)

def download_and_process_video(url, config):
    api_name = api_name_var.get()
    target_lang = target_lang_var.get()
    model_size = model_size_var.get()
    if not url:
        messagebox.showerror("Error", "Please enter a video URL")
        return
    # 假设以下函数调用您已经定义的逻辑
    url_path, video_path, audio_path = YoutubeVideoDownload(url)
    srt_file = transcribe(url_path, audio_path, model_size)
    translation4srt(srt_file, config, api_name, target_lang)
    messagebox.showinfo("Success", "Video processed successfully")

def process_audio(config):
    file_path = audio_entry.get()
    # file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.m4a *.mp4")])
    api_name = api_name_var.get()
    target_lang = target_lang_var.get()
    model_size = model_size_var.get()
    if not file_path:
        messagebox.showerror("Error", "Please select an audio file")
        return
    # 假设以下函数调用您已经定义的逻辑
    try:
        # 假设 audio_path, url_path 需要你手动设置或获取
        url_path = os.path.split(file_path)[0]
        srt_file = transcribe(url_path, file_path, model_size)
        srt_entry.config(state='normal')  # 允许编辑以更新路径
        srt_entry.delete(0, tk.END)
        srt_entry.insert(0, srt_file)
        srt_entry.config(state='readonly')  # 重新设置为只读
        translation4srt(srt_file, config, api_name, target_lang)
        messagebox.showinfo("Success", "Audio processed successfully")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to process audio: {str(e)}")

def translate_subtitles(config):
    file_path = srt_entry.get()
    # file_path = filedialog.askopenfilename(filetypes=[("Subtitle Files", "*.srt *.txt")])
    api_name = api_name_var.get()
    target_lang = target_lang_var.get()
    if not file_path:
        messagebox.showerror("Error", "Please select a subtitle file")
        return
    # 假设以下函数调用您已经定义的逻辑
    translation4srt(file_path, config, api_name, target_lang)
    messagebox.showinfo("Success", "Subtitles translated successfully")
    # try:
    #     translation4srt(file_path, config, api_name, target_lang)
    #     messagebox.showinfo("Success", "Subtitles translated successfully")
    # except Exception as e:
    #     messagebox.showerror("Error", f"Failed to translate subtitles: {str(e)}")


def generate_paths(event):
    video_url = url_entry.get()
    if video_url.strip():  # 确保视频URL不为空
        try:
            yt = YouTube(video_url)
            video_title = yt.title  # 获取视频标题用于生成文件名
            video_title_safe = "".join([c for c in video_title if c.isalpha() or c.isdigit() or c == ' ']).rstrip()

            # 设定下载目录
            URL_DOWNLOAD_DIR = os.path.join(save_directory.get(), video_title_safe)

            # 假设视频和音频文件命名规则
            video_mime_type = 'mp4'  # 示例中假设视频为MP4格式
            audio_mime_type = 'mp3'  # 示例中假设音频为MP3格式
            video_path = os.path.join(URL_DOWNLOAD_DIR, f'video_{video_title_safe}.{video_mime_type}')
            audio_path = os.path.join(URL_DOWNLOAD_DIR, f'audio_{video_title_safe}.{audio_mime_type}')

            # 更新界面中的音频和字幕路径
            audio_entry.config(state='normal')  # 允许编辑以更新路径
            audio_entry.delete(0, tk.END)
            audio_entry.insert(0, audio_path)
            audio_entry.config(state='readonly')  # 重新设置为只读

            srt_path = os.path.join(URL_DOWNLOAD_DIR, f'{video_title_safe}_subtitles.srt')
            srt_entry.config(state='normal')  # 允许编辑以更新路径
            srt_entry.delete(0, tk.END)
            srt_entry.insert(0, srt_path)
            srt_entry.config(state='readonly')  # 重新设置为只读
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch video info: {str(e)}")
    else:
        # 清空路径，因为URL为空
        audio_entry.config(state='normal')
        audio_entry.delete(0, tk.END)
        # audio_entry.config(state='readonly')
        srt_entry.config(state='normal')
        srt_entry.delete(0, tk.END)
        # srt_entry.config(state='readonly')

def choose_file(entry, filetypes, initialdir):
    filename = filedialog.askopenfilename(initialdir=initialdir, filetypes=filetypes)
    if filename:
        entry.config(state='normal')
        entry.delete(0, tk.END)
        entry.insert(0, filename)
        entry.config(state='readonly')

def choose_audio_file():
    initial_dir = save_directory.get()
    choose_file(audio_entry, [("Audio files", "*.mp3 *.wav *.m4a *.mp4")], initial_dir)

def choose_srt_file():
    initial_dir = save_directory.get()
    choose_file(srt_entry, [("Subtitle files", "*.srt *.txt")], initial_dir)

def choose_directory():
    global save_directory  # 使用全局变量来存储目录路径
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        save_directory.set(folder_selected)

class TqdmToLabel(tqdm):
    def __init__(self, label, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def display(self, msg=None, pos=None):
        if msg:
            self.label.config(text=msg)

class RedirectOutput:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

def save_config():
    config = {
        "tencent": {"key": tencent_key_var.get(), "secret": tencent_secret_var.get(), "url": tencent_url_var.get()},
        "youdao": {"key": youdao_key_var.get(), "secret": youdao_secret_var.get(), "url": youdao_url_var.get()},
        "huoshan": {"key": huoshan_key_var.get(), "secret": huoshan_secret_var.get(), "url": huoshan_url_var.get()},
        "openai": {"url": openai_url_var.get(), "access": openai_access_var.get()},
        "claude": {"url": claude_url_var.get(), "access": claude_access_var.get()}
    }
    with open("config.json", "w") as f:
        json.dump(config, f)
    print("Configuration saved successfully.")

def load_config():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            tencent_key_var.set(config.get("tencent", {}).get("key", ""))
            tencent_secret_var.set(config.get("tencent", {}).get("secret", ""))
            tencent_url_var.set(config.get("tencent", {}).get("url", ""))
            youdao_key_var.set(config.get("youdao", {}).get("key", ""))
            youdao_secret_var.set(config.get("youdao", {}).get("secret", ""))
            youdao_url_var.set(config.get("youdao", {}).get("url", ""))
            huoshan_key_var.set(config.get("huoshan", {}).get("key", ""))
            huoshan_secret_var.set(config.get("huoshan", {}).get("secret", ""))
            huoshan_url_var.set(config.get("huoshan", {}).get("url", ""))
            openai_url_var.set(config.get("openai", {}).get("url", ""))
            openai_access_var.set(config.get("openai", {}).get("access", ""))
            claude_url_var.set(config.get("claude", {}).get("url", ""))
            claude_access_var.set(config.get("claude", {}).get("access", ""))
        print("Configuration loaded successfully.")
    except FileNotFoundError:
        print("No configuration file found. Please save a configuration first.")

def get_config_from_entries():
    config = {
        "tencent_secret_id": tencent_key_var.get(),
        "tencent_secret_key": tencent_secret_var.get(),
        "tencent_endpoint": tencent_url_var.get(),
        "youdao_APP_KEY": youdao_key_var.get(),
        "youdao_APP_SECRET": youdao_secret_var.get(),
        "youdao_url": youdao_url_var.get(),
        "volcengine_access_key": huoshan_key_var.get(),
        "volcengine_secret_key": huoshan_secret_var.get(),
        "volcengine_url": huoshan_url_var.get(),
        "openai_base_url": openai_url_var.get(),
        "openai_api_key": openai_access_var.get(),
        "claude_base_url": claude_url_var.get(),
        "claude_api_key": claude_access_var.get(),
        "api_usage": "./api_character_count.json",
    }
    return config

if __name__ == "__main__":
    # 创建主窗口
    app = tk.Tk()
    app.title("Media Processing Tool")
    app.geometry("600x600")

    # 设置全局变量来存储目录
    save_directory = tk.StringVar(app)
    # 尝试设置默认目录为用户的"视频"文件夹
    default_dir = os.path.expanduser(os.path.join("~", "Videos"))
    if not os.path.exists(default_dir):
        default_dir = os.path.expanduser("~")
    save_directory.set(default_dir)

    # 创建一个 Notebook 容器
    notebook = ttk.Notebook(app)
    notebook.pack(expand=True, fill='both')

    # 创建媒体处理页面
    media_page = ttk.Frame(notebook)
    notebook.add(media_page, text="Media Processing")

    # 创建配置页面
    config_page = ttk.Frame(notebook)
    notebook.add(config_page, text="Configuration")

    # 在配置页面中添加控件
    tk.Label(config_page, text="Configuration Settings").pack(pady=(10, 0))

    config_frame = tk.Frame(config_page)
    config_frame.pack(pady=(10, 0))

    # 腾讯配置
    tk.Label(config_frame, text="Tencent Key:").grid(row=0, column=0, padx=5, pady=5)
    tencent_key_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=tencent_key_var, width=30).grid(row=0, column=1, padx=5, pady=5)

    tk.Label(config_frame, text="Tencent Secret:").grid(row=1, column=0, padx=5, pady=5)
    tencent_secret_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=tencent_secret_var, width=30).grid(row=1, column=1, padx=5, pady=5)

    tk.Label(config_frame, text="Tencent URL:").grid(row=2, column=0, padx=5, pady=5)
    tencent_url_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=tencent_url_var, width=30).grid(row=2, column=1, padx=5, pady=5)

    # 有道配置
    tk.Label(config_frame, text="Youdao Key:").grid(row=3, column=0, padx=5, pady=5)
    youdao_key_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=youdao_key_var, width=30).grid(row=3, column=1, padx=5, pady=5)

    tk.Label(config_frame, text="Youdao Secret:").grid(row=4, column=0, padx=5, pady=5)
    youdao_secret_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=youdao_secret_var, width=30).grid(row=4, column=1, padx=5, pady=5)

    tk.Label(config_frame, text="Youdao URL:").grid(row=5, column=0, padx=5, pady=5)
    youdao_url_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=youdao_url_var, width=30).grid(row=5, column=1, padx=5, pady=5)

    # 火山配置
    tk.Label(config_frame, text="Huoshan Key:").grid(row=6, column=0, padx=5, pady=5)
    huoshan_key_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=huoshan_key_var, width=30).grid(row=6, column=1, padx=5, pady=5)

    tk.Label(config_frame, text="Huoshan Secret:").grid(row=7, column=0, padx=5, pady=5)
    huoshan_secret_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=huoshan_secret_var, width=30).grid(row=7, column=1, padx=5, pady=5)

    tk.Label(config_frame, text="Huoshan URL:").grid(row=8, column=0, padx=5, pady=5)
    huoshan_url_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=huoshan_url_var, width=30).grid(row=8, column=1, padx=5, pady=5)

    # OpenAI 配置
    tk.Label(config_frame, text="OpenAI URL:").grid(row=9, column=0, padx=5, pady=5)
    openai_url_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=openai_url_var, width=30).grid(row=9, column=1, padx=5, pady=5)

    tk.Label(config_frame, text="OpenAI Access:").grid(row=10, column=0, padx=5, pady=5)
    openai_access_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=openai_access_var, width=30).grid(row=10, column=1, padx=5, pady=5)

    # Claude 配置
    tk.Label(config_frame, text="Claude URL:").grid(row=11, column=0, padx=5, pady=5)
    claude_url_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=claude_url_var, width=30).grid(row=11, column=1, padx=5, pady=5)

    tk.Label(config_frame, text="Claude Access:").grid(row=12, column=0, padx=5, pady=5)
    claude_access_var = tk.StringVar()
    tk.Entry(config_frame, textvariable=claude_access_var, width=30).grid(row=12, column=1, padx=5, pady=5)
    load_config()
    # 保存和加载配置的按钮
    save_button = tk.Button(config_frame, text="Save Configuration", command=save_config)
    save_button.grid(row=13, column=0, pady=10, padx=5)

    load_button = tk.Button(config_frame, text="Load Configuration", command=load_config)
    load_button.grid(row=13, column=1, pady=10, padx=5)

    # 在媒体处理页面中添加控件
    tk.Label(media_page, text="Enter Video URL:").pack(pady=(10, 0))
    video_frame = tk.Frame(media_page)
    video_frame.pack(pady=(0, 10))
    url_entry = tk.Entry(video_frame, width=50)
    url_entry.pack(side=tk.LEFT)
    url_entry.bind("<KeyRelease>", generate_paths)
    video_button = tk.Button(video_frame, text="Download",
                             command=lambda: download_and_process_video(url_entry.get(), get_config_from_entries()))
    video_button.pack(side=tk.LEFT)

    # Audio file Entry and Button# Audio file Entry
    tk.Label(media_page, text="Audio File Path (Auto-filled or select):").pack(pady=(10, 0))
    audio_frame = tk.Frame(media_page)
    audio_frame.pack(pady=(0, 10))
    audio_entry = tk.Entry(audio_frame, width=50, state='readonly')
    audio_entry.pack(side=tk.LEFT, padx=(5, 5))
    audio_button = tk.Button(audio_frame, text="...", command=choose_audio_file)
    audio_button.pack(side=tk.LEFT, padx=(5, 5))
    # Audio Model Size OptionMenu
    audio_options_frame = tk.Frame(media_page)
    audio_options_frame.pack(pady=(0, 10))
    tk.Label(audio_options_frame, text="Model Size:").pack(side=tk.LEFT, padx=(5, 5))
    model_size_var = tk.StringVar(media_page)
    model_size_var.set("large")  # 默认值
    model_size_menu = tk.OptionMenu(audio_options_frame, model_size_var, "tiny", "medium", "large")
    model_size_menu.pack(side=tk.LEFT, padx=(0, 5))
    # Audio File Button
    audio_button = tk.Button(audio_options_frame, text="Process Audio File", command=lambda: process_audio(get_config_from_entries()))
    audio_button.pack(side=tk.LEFT, padx=(5, 5))

    # SRT file Entry and Button
    tk.Label(media_page, text="Subtitle File Path (Auto-filled or select):").pack(pady=(10, 0))
    srt_frame = tk.Frame(media_page)
    srt_frame.pack(pady=(0, 10))
    srt_entry = tk.Entry(srt_frame, width=50, state='readonly')
    srt_entry.pack(side=tk.LEFT, padx=(5, 5))
    srt_button = tk.Button(srt_frame, text="...", command=choose_srt_file)
    srt_button.pack(side=tk.LEFT, padx=(5, 5))
    # API Name and Target Language OptionMenu
    subtitle_options_frame = tk.Frame(media_page)
    subtitle_options_frame.pack(pady=(0, 10))
    tk.Label(subtitle_options_frame, text="API Name:").pack(side=tk.LEFT, padx=(5, 5))
    api_name_var = tk.StringVar(media_page)
    api_name_var.set("tencent")  # 默认值
    api_name_menu = tk.OptionMenu(subtitle_options_frame, api_name_var, "tencent", "volcengine", "youdao", 'gpt3', 'gpt4', 'gpt4o', 'sonnet', "opus")
    api_name_menu.pack(side=tk.LEFT, padx=(0, 5))
    tk.Label(subtitle_options_frame, text="Target Lang:").pack(side=tk.LEFT, padx=(5, 5))
    target_lang_var = tk.StringVar(media_page)
    target_lang_var.set("zh")  # 默认值
    target_lang_menu = tk.OptionMenu(subtitle_options_frame, target_lang_var, "zh", "en", "es")
    target_lang_menu.pack(side=tk.LEFT, padx=(0, 5))
    # Subtitle File Button
    subtitle_button = tk.Button(subtitle_options_frame, text="Translate Subtitles", command=lambda: translate_subtitles(get_config_from_entries()))
    subtitle_button.pack(side=tk.LEFT, padx=(5, 5))

    # Directory Entry and Button
    tk.Label(media_page, text="Save Directory:").pack(pady=(10, 0))
    dir_frame = tk.Frame(media_page)
    dir_frame.pack(pady=(0, 10))
    dir_entry = tk.Entry(dir_frame, textvariable=save_directory, width=50, state='readonly')
    dir_entry.pack(side=tk.LEFT)
    dir_button = tk.Button(dir_frame, text="...", command=choose_directory)
    dir_button.pack(side=tk.LEFT, padx=(5, 0))

    # Text widget to display the output
    output_text = scrolledtext.ScrolledText(media_page, wrap=tk.WORD, width=50, height=20)
    output_text.pack(pady=(10, 10), padx=(10, 10))

    # Redirect standard output to the text widget# Redirect standard
    sys.stdout = RedirectOutput(output_text)


    # 运行主事件循环
    app.mainloop()