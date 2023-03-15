''' Azure TTS interface '''
import os
import azure.cognitiveservices.speech as speechsdk
import numpy as np
from io import BytesIO
import wave

import logging
logger = logging.getLogger(__file__)


class AzureTts:
    def __init__(self, api_key: str, api_region: str):
        self._speech_config: speechsdk.SpeechConfig = speechsdk.SpeechConfig(subscription=api_key, region=api_region)
        self._audio_config: speechsdk.AudioConfig = None
        self._synthesizer: speechsdk.SpeechSynthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self._speech_config, audio_config=self._audio_config)

    def synthesize(self, text: str) -> tuple[np.array, int]:
        result = self._synthesizer.speak_text_async(text).get()
        stream: speechsdk.AudioDataStream = speechsdk.AudioDataStream(result)
        resultData: BytesIO = BytesIO(result.audio_data)
        waveFile = wave.open(resultData)
        waveData: bytes = waveFile.readframes(waveFile.getnframes())
        waveRate: int = waveFile.getframerate()

        return np.frombuffer(waveData, dtype=np.int16), waveRate
