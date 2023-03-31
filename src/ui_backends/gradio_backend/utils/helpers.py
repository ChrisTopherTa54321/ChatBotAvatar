''' Misc Gradio helper functions'''

from utils.audio_utils import save_audio_to_file
from utils.shared import Shared
import shutil
from typing import Tuple
from tempfile import NamedTemporaryFile
import numpy as np
import os


def persist_file_event(file_name: NamedTemporaryFile) -> str:
    ''' Copies a gradio temporary file to an app temporary file and return the path'''
    if not file_name:
        return None
    name, ext = os.path.splitext(file_name.name)
    output_file = f"{Shared.getInstance().unique_file_prefix}{ext}"
    shutil.copy(file_name.name, output_file)
    return output_file


def audio_to_file_event(audio: Tuple[int, np.ndarray]) -> str:
    sampling_rate, audio_data = audio
    output_file = f"{Shared.getInstance().unique_file_prefix}_audio.wav"
    save_audio_to_file(audio_data=audio_data, sampling_rate=sampling_rate, output_path=output_file)
    return output_file
