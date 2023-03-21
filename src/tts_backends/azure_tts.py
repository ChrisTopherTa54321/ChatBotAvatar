''' Azure TTS interface '''
from __future__ import annotations
import os
import azure.cognitiveservices.speech as speechsdk
import numpy as np
from io import BytesIO
from typing import List, Optional, Tuple
import wave
import re
from tts import Tts
from typing_extensions import override

import logging
logger = logging.getLogger(__file__)


class AzureTts(Tts):
    DEFAULT_STYLE = "general"

    def __init__(self, api_key: str, api_region: str, voice_locale: str = "en-US"):
        # Create configuration
        self._speech_config: speechsdk.SpeechConfig = speechsdk.SpeechConfig(subscription=api_key, region=api_region)
        self._speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff44100Hz16BitMonoPcm)

        self._locale: str = voice_locale
        self._pitch: str = None
        self._rate: str = None

        synthesizer = self._get_synthesizer()
        voices = synthesizer.get_voices_async(locale=voice_locale).get().voices
        self._voices: List[AzureTts.Voice] = [AzureTts.Voice(voice_info=voice) for voice in voices]

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
    def synthesize(self, text: str, voice: AzureTts.Voice) -> Tuple[np.array, int]:
        ssml = voice._buildSsml(text)
        synthesizer: speechsdk.SpeechSynthesizer = self._get_synthesizer()
        result = synthesizer.speak_ssml_async(ssml).get()
        if not result.audio_data:
            logger.warn(f"Failed to synthesize audio: {result.cancellation_details.error_details}")
            return np.array([]), 0
        resultData: BytesIO = BytesIO(result.audio_data)
        waveFile = wave.open(resultData)
        waveData: bytes = waveFile.readframes(waveFile.getnframes())
        waveRate: int = waveFile.getframerate()

        return np.frombuffer(waveData, dtype=np.int16), waveRate

    def _get_synthesizer(self) -> speechsdk.SpeechSynthesizer:
        '''
        Create a SpeechSynthesizer with the current configuration

        Returns:
            speechsdk.SpeechSynthesizer: new speechsdk.SpeechSynthesizer
        '''
        return speechsdk.SpeechSynthesizer(speech_config=self._speech_config)

    class Voice(Tts.Voice):
        def __init__(self, voice_info: speechsdk.VoiceInfo):
            self._voice_info: speechsdk.VoiceInfo = voice_info
            self._cur_style: str = self.get_styles_available()[0]
            self._pitch: str = None
            self._rate: str = None

        @override
        def get_name(self) -> str:
            return self._voice_info.local_name

        @override
        def get_styles_available(self) -> List[str]:
            return [AzureTts.DEFAULT_STYLE] + self._voice_info.style_list

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
            return 44100

        def _buildSsml(self, text: str) -> str:
            style = self._cur_style if self._cur_style else AzureTts.DEFAULT_STYLE
            pitch = self._pitch if self._pitch else "+0%"
            rate = self._rate if self._rate else "+0%"
            if style == AzureTts.DEFAULT_STYLE:
                express_open = ""
                express_close = ""
            else:
                express_open = f'<mstts:express-as style="{style}">'
                express_close = '</mstts:express-as>'
            ssml: str = f"""
                <speak version="1.0"
                xmlns="http://www.w3.org/2001/10/synthesis"
                xmlns:mstts="http://www.w3.org/2001/mstts"
                xml:lang="{self._voice_info.locale}">
                    <voice name="{self._voice_info.short_name}">
                        <prosody pitch="{pitch}" rate="{rate}">
                            {express_open}
                                {text}
                            {express_close}
                        </prosody>
                    </voice>
                </speak>
            """
            ssml = ssml.replace('\n', ' ')
            whitespace_re = re.compile('[ \n]+([ \n])')
            ssml = whitespace_re.sub(' ', ssml).strip()
            ssml = ssml.replace("> <", "><")
            return ssml
