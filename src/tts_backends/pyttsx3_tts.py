''' pyttsx3 TTS interface '''
from __future__ import annotations
import pyttsx3
import pyttsx3.voice
import numpy as np
from typing import List, Optional, Tuple
from tts import Tts
from typing_extensions import override
import tempfile
import wave
import os
import time

import logging
logger = logging.getLogger(__file__)


class Pyttsx3Tts(Tts):
    def __init__(self, language='en'):
        self._pitch: str = None
        self._rate: str = None

        tts: pyttsx3.Engine = pyttsx3.init()
        voices = tts.getProperty('voices')
        self._voices: List[Pyttsx3Tts.Voice] = [Pyttsx3Tts.Voice(voice_info=voice) for voice in voices]
        self._voices = [voice for voice in self._voices if voice.get_language() == language]

    @override
    def get_voice_list(self) -> List[Tts.Voice]:
        return self._voices.copy()

    @override
    def get_voice(self, name: str) -> Optional[Tts.Voice]:
        matches = [voice for voice in self._voices if voice.get_name() == name]
        if matches:
            return matches[0]
        return None

    @override
    def synthesize(self, text: str, voice: Pyttsx3Tts.Voice) -> Tuple[np.array, int]:
        tts: pyttsx3.Engine = pyttsx3.init()
        tts.setProperty('voice', voice._voice_info.id)

        # Really would be nice if this could output to a buffer...
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "audio_out.wav")
            tts.save_to_file(text, filename)
            logger.info(f"Saving file to {filename}")
            tts.runAndWait()

            # runAndWait() doesn't seem to actually wait for the file to write...
            for retry in range(20):
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    break
                logger.info(f"Waiting for tts to finish: {retry}")
                time.sleep(0.1)

            try:
                waveFile: wave.Wave_read = wave.open(filename)
            except Exception as e:
                logger.error(e)
            waveData: bytes = waveFile.readframes(waveFile.getnframes())
            waveRate: int = waveFile.getframerate()
            waveFile.close()

        return np.frombuffer(waveData, dtype=np.int16), waveRate

    class Voice(Tts.Voice):
        def __init__(self, voice_info: pyttsx3.voice.Voice):
            self._voice_info: pyttsx3.voice.Voice = voice_info
            self._pitch: str = None
            self._rate: str = None
            self._cur_style: str = self._voice_info.gender

        def get_language(self) -> str:
            lang = self._voice_info.languages[0]
            if lang[0] == 5:  # Weird extra byte?
                lang = lang[-2:]
            return lang.decode()

        @override
        def get_name(self) -> str:
            return self._voice_info.name

        @override
        def get_styles_available(self) -> List[str]:
            return [self._cur_style]

        @override
        def get_style(self) -> str:
            return self._cur_style

        @override
        def set_style(self, style: str) -> None:
            if style in self.get_styles_available():
                self._cur_style = style
            else:
                logger.warn(f"Invalid style for voice [{self.get_name()}]: {style}")

        @override
        def set_pitch(self, pitch: str) -> None:
            self._pitch = pitch

        @override
        def set_rate(self, rate: str) -> None:
            self._rate = rate

        @override
        def get_sampling_rate(self) -> int:
            return 22050
