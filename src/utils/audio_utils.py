''' Utilities for audiol '''

from typing import Tuple
import numpy as np
from pathlib import Path
import wave


def save_audio_to_file(sampling_rate: int, audio_data: np.ndarray, output_path: str):
    with wave.open(output_path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sampling_rate)
        wav.writeframesraw(audio_data)
