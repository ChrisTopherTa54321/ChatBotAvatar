''' coqui TTS interface '''
from __future__ import annotations
from TTS.api import TTS as cTTS
import numpy as np
from typing import List, Optional, Tuple
from src.tts import Tts
from typing_extensions import override

import logging
logger = logging.getLogger(__file__)


class CoquiTts(Tts):
    def __init__(self, language='en', use_gpu=False):
        self._pitch: str = None
        self._rate: str = None
        self._use_gpu = use_gpu

        model_list = cTTS.list_models()
        self._voices: List[CoquiTts.Voice] = [CoquiTts.Voice(
            model_path=model, language=language) for model in model_list]
        self._voices = [voice for voice in self._voices
                        if voice.get_language() == language or voice.get_language() == "multilingual"]

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
    def synthesize(self, text: str, voice: CoquiTts.Voice) -> Tuple[np.array, int]:
        tts = cTTS(voice.get_path(), gpu=self._use_gpu)
        language = voice.get_language() if voice.is_multilingual() else None
        speaker = voice.get_style() if tts.speakers else None
        pcm_data_float = np.array(tts.tts(text, speaker=speaker, language=language))
        pcm_data_float /= 1.414
        pcm_data_float *= 32767
        pcm_data = pcm_data_float.astype(np.int16)
        return np.frombuffer(pcm_data, dtype=np.int16), voice.get_sampling_rate()

    class Voice(Tts.Voice):
        def __init__(self, model_path: str, language: str):
            _, lang, dataset, name = model_path.split('/')
            self._model_path = model_path
            self._lang = lang
            self._dataset = dataset
            self._name = f"{dataset}_{name}"
            self._cur_style = None
            self._style_list = None
            self._sampling_rate = None
            self._default_lang = language
            self._loaded = False

        def _fill_model_info(self) -> None:
            if not self._loaded:
                tts = cTTS(self._model_path)
                self._style_list = tts.speakers
                if self._style_list:
                    # Remove duplicates
                    unique_list: List[str] = []
                    for style in self._style_list:
                        if not style.strip() in unique_list:
                            unique_list.append(style)
                    self._style_list = unique_list
                    self._cur_style = self._style_list[0]
                else:
                    self._style_list = ["general"]

                self._sampling_rate = tts.synthesizer.output_sample_rate
                del tts
                self._loaded = True

        def _get_style_list(self):
            if not self._style_list:
                self._fill_model_info()
            return self._style_list

        def is_multilingual(self) -> bool:
            return self._lang == "multilingual"

        def get_language(self) -> str:
            if self.is_multilingual():
                return self._default_lang
            return self._lang

        def get_path(self) -> str:
            return self._model_path

        @override
        def get_name(self) -> str:
            return self._name

        @override
        def get_styles_available(self) -> List[str]:
            return self._get_style_list()

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
            if not self._sampling_rate:
                self._fill_model_info()
            return self._sampling_rate
