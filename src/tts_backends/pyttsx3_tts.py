''' pyttsx3 TTS interface '''
from __future__ import annotations
import pyttsx3
import pyttsx3.voice
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from tts import Tts
from typing_extensions import override
import tempfile
import wave
import os
import time
from threading import Lock

import logging
logger = logging.getLogger(__file__)


class Pyttsx3Tts(Tts):
    BACKEND_NAME: str = "pyttsx3_tts"

    def __init__(self, language='en'):
        self._pitch: str = None
        self._rate: str = None

        tts: pyttsx3.Engine = pyttsx3.init()
        voices = tts.getProperty('voices')
        self._voices: List[Pyttsx3Tts.Voice] = [Pyttsx3Tts.Voice(tts_inst=self, voice_info=voice) for voice in voices]
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

    class Voice(Tts.Voice):
        def __init__(self, tts_inst: Pyttsx3Tts, voice_info: pyttsx3.voice.Voice):
            self._voice_info: pyttsx3.voice.Voice = voice_info
            self._pitch: str = None
            self._rate: str = None
            self._cur_style: str = self._voice_info.gender
            self._tts: Pyttsx3Tts = tts_inst
            self._lock: Lock = Lock()

        def get_language(self) -> str:
            lang = self._voice_info.languages[0]
            if lang[0] == 5:  # Weird extra byte?
                lang = lang[-2:]
            return lang.decode()

        @override
        def synthesize(self, text: str) -> Tuple[np.array, int]:
            # Enforce single threading
            with self._lock:
                tts: pyttsx3.Engine = pyttsx3.init()
                tts.setProperty('voice', self._voice_info.id)

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

        @override
        def get_backend_name(self) -> str:
            return Pyttsx3Tts.BACKEND_NAME

        @override
        def from_dict(self, info: Dict[str, Any]) -> Pyttsx3Tts.Voice:
            raise NotImplementedError()

        @override
        def as_dict(self) -> Dict[str, Any]:
            ret: Dict[str, Any] = {}
            ret[Pyttsx3Tts.Voice.JsonKeys.BACKEND] = Pyttsx3Tts.BACKEND_NAME
            ret[Pyttsx3Tts.Voice.JsonKeys.NAME] = self.get_name()
            ret[Pyttsx3Tts.Voice.JsonKeys.STYLE] = self.get_style()
            ret[Pyttsx3Tts.Voice.JsonKeys.PITCH] = self._pitch
            ret[Pyttsx3Tts.Voice.JsonKeys.RATE] = self._rate
            return ret

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
        def get_pitch(self) -> str:
            return self._pitch

        @override
        def set_rate(self, rate: str) -> None:
            self._rate = rate

        @override
        def get_rate(self) -> str:
            return self._rate

        @override
        def get_sampling_rate(self) -> int:
            return 22050
