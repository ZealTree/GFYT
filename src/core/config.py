import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from .constants import USER_AGENT, YTDLP_DOWNLOAD_URL, FFMPEG_RELEASES_URL

class ConfigManager:
    CONFIG_FILE = "yt-dlp.conf"
    LOG_FILE = "yt-dlp-gui.log"
    USER_AGENT = USER_AGENT
    YTDLP_DOWNLOAD_URL = YTDLP_DOWNLOAD_URL
    FFMPEG_RELEASES_URL = FFMPEG_RELEASES_URL

    DEFAULT_CONFIG = """# yt-dlp Configuration File
--output "%(title)s.%(ext)s"
--paths "{}/Videos"
--merge-output-format mp4
--no-overwrites
""".format(str(Path.home()))

    @classmethod
    def init_config(cls):
        if not os.path.exists(cls.CONFIG_FILE):
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(cls.DEFAULT_CONFIG)

        if not os.path.exists(cls.LOG_FILE):
            with open(cls.LOG_FILE, 'w', encoding='utf-8') as f:
                f.write(f"YT-DLP GUI Log - Created {datetime.now()}\n")

    @classmethod
    def save_config(cls, config_text):
        try:
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(config_text)
            return True
        except Exception as e:
            return False

    @classmethod
    def load_config(cls):
        try:
            with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    @classmethod
    def parse_config(cls, config_text):
        params = {
            'output': '%(title)s.%(ext)s',
            'paths': str(Path.home() / "Videos"),
            'merge_format': 'mp4',
            'proxy': None,
            'cookies': None,
            'cookies_from_browser': None,
            'no_overwrites': False,
            'sponsorblock_remove': False,
            'add_metadata': False,
            'embed_thumbnail': False,
            'ffmpeg_location': None
        }

        lines = [line.strip() for line in config_text.split('\n') if line.strip() and not line.strip().startswith('#')]

        for line in lines:
            if line.startswith('--output'):
                params['output'] = line.split('"')[1]
            elif line.startswith('--paths'):
                params['paths'] = line.split('"')[1]
            elif line.startswith('--merge-output-format'):
                params['merge_format'] = line.split()[-1]
            elif line.startswith('--proxy'):
                params['proxy'] = line.split()[-1]
            elif line.startswith('--cookies'):
                match = re.search(r'--cookies\s+"(.+?)"', line)
                if match:
                    params['cookies'] = match.group(1)
            elif line.startswith('--cookies-from-browser'):
                params['cookies_from_browser'] = ' '.join(line.split()[1:])
            elif line.startswith('--ffmpeg-location'):
                params['ffmpeg_location'] = line.split('"')[1]
            elif line == '--no-overwrites':
                params['no_overwrites'] = True
            elif line == '--sponsorblock-remove all':
                params['sponsorblock_remove'] = True
            elif line == '--add-metadata':
                params['add_metadata'] = True
            elif line == '--embed-thumbnail':
                params['embed_thumbnail'] = True

        return params

    @classmethod
    def log_download(cls, message, success=True):
        with open(cls.LOG_FILE, 'a', encoding='utf-8') as f:
            status = "INFO" if success else "ERROR"
            f.write(f"[{datetime.now()}] [{status}] {message}\n")

    @classmethod
    def get_ytdlp_path(cls):
        if os.name == 'nt':
            return "yt-dlp.exe"
        return "./yt-dlp"

    @classmethod
    def check_ytdlp_exists(cls):
        return os.path.exists(cls.get_ytdlp_path())

    @classmethod
    def get_ytdlp_version(cls):
        if not cls.check_ytdlp_exists():
            return None

        try:
            result = subprocess.run(
                [cls.get_ytdlp_path(), "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.stdout.strip()
        except Exception:
            return None

    @classmethod
    def get_ffmpeg_path(cls):
        config_text = cls.load_config()
        if config_text:
            params = cls.parse_config(config_text)
            if params['ffmpeg_location'] and os.path.isdir(params['ffmpeg_location']):
                ffmpeg_bin = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
                ffmpeg_path = os.path.join(params['ffmpeg_location'], ffmpeg_bin)
                if os.path.isfile(ffmpeg_path):
                    return ffmpeg_path
        return "ffmpeg"

    @classmethod
    def check_ffmpeg_exists(cls):
        ffmpeg_path = cls.get_ffmpeg_path()
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def get_ffmpeg_version(cls):
        ffmpeg_path = cls.get_ffmpeg_path()
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode != 0:
                return None
            version_line = result.stdout.split('\n')[0]
            match = re.search(r'ffmpeg version (\S+)', version_line)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None