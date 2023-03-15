''' Azure TTS interface '''
import os
import azure.cognitiveservices.speech as speechsdk
import numpy as np
from io import BytesIO
from typing import List
import wave

import logging
logger = logging.getLogger(__file__)


class AzureTts:
    def __init__(self, api_key: str, api_region: str, voice_locale: str = "en-US"):
        self._speech_config: speechsdk.SpeechConfig = speechsdk.SpeechConfig(subscription=api_key, region=api_region)
        
        self._synthesizer: speechsdk.SpeechSynthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self._speech_config)
        self._activeVoice: speechsdk.speech.VoiceInfo = None
        self._locale = voice_locale
        self._voices = self._synthesizer.get_voices_async(locale=voice_locale).get().voices
        self._activeStyle: str = None
        self.setVoice(self._voices[0].local_name)

    def setVoice(self, name: str):
        voiceMatches = [ voice for voice in self._voices if voice.local_name == name]
        if len(voiceMatches) == 1:
            self._activeVoice = voiceMatches[0]
        else:
            raise Exception(f"Failed to set voice name to {name}")


    def getVoices(self) -> List[str]:
        return [voice.local_name for voice in self._voices]


    def getStyles(self) -> List[str]:
        if self._activeVoice:
            styles = self._activeVoice.style_list.copy()
        else:
            styles = []
        return styles


    def setStyle(self, style: str):
        styleList = self._activeVoice.style_list
        if style in styleList:
            self._activeStyle = style
        else:
            raise Exception("Failed to set style to {style}")
        

    def synthesize(self, text: str) -> tuple[np.array, int]:
        text = self._buildSsml(text)
        result = self._synthesizer.speak_ssml_async(text).get()
        if not result.audio_data:
            logger.warn(f"Failed to synthesize audio: {result.cancellation_details.error_details}")
            return np.array(), 0
        resultData: BytesIO = BytesIO(result.audio_data)
        waveFile = wave.open(resultData)
        waveData: bytes = waveFile.readframes(waveFile.getnframes())
        waveRate: int = waveFile.getframerate()

        return np.frombuffer(waveData, dtype=np.int16), waveRate


    def _buildSsml(self, text: str) -> str:
        activeStyle = self._activeStyle if self._activeStyle else "neutral"
        ssml: str = f"""
            <speak version="1.0"
             xmlns="http://www.w3.org/2001/10/synthesis"
             xmlns:mstts="http://www.w3.org/2001/mstts"
             xml:lang="{self._locale}">
                <voice name="{self._activeVoice.name}">
                    <mstts:express-as style="{activeStyle}">
                        {text}
                    </mstts:express-as>
                </voice>
            </speak>
        """
        return ssml