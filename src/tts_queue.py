''' Class for handling chunking TTS requests '''
from __future__ import annotations
from typing import Tuple, List, Dict
import numpy as np
from .tts import Tts
from .text_utils import TextUtils
from dataclasses import dataclass

from multiprocessing.dummy import Event
from multiprocessing.pool import ThreadPool, AsyncResult
from queue import Empty
from functools import partial
import time
import logging
logger = logging.getLogger(__file__)


class TtsQueue:
    @dataclass
    class ResultItem:
        chunk_id: int
        audio_data: np.array
        sample_rate: int
        text: str

    @dataclass
    class AudioData:
        text: str
        data: np.array
        sample_rate: int

    def __init__(self, tts: Tts, chunk_min_words: int = 32):
        # TODO: adjust min_words on the fly based on processing rate
        self._tts: Tts = tts
        self._min_chunk_words: int = chunk_min_words
        self._audio: Dict[int, TtsQueue.AudioData] = {}
        self._sampling_rate: int = 0
        self._pool: ThreadPool = ThreadPool(processes=1)
        self._pool_result: AsyncResult = None
        self._pool_cancel_event: Event = Event()
        self._read_chunk_id: int = 0
        self._new_audio_avail_event: Event = Event()

    def cancel(self):
        '''
        Cancel an on-going synthesis
        '''
        if self._pool_result:
            logger.warn("Cancelling ongoing synthesis (maybe? This probably doesn't work)")
            self._pool_cancel_event.set()
            self._pool_result.wait()
            self._pool_result = None

    def reset(self):
        ''' Resets the Queue to prepare for new audio '''
        self._read_chunk_id = 0
        self._audio.clear()

    def is_done(self) -> bool:
        ''' returns true if the Queue has no work '''
        return self._pool_result is None

    def get_new_audio(self) -> Tuple[np.array, int]:
        '''
        Returns any newly available audio since the last time this function
        was called

        Returns:
            Tuple[np.array, int]: tuple of (audio data buffer, sampling rate)
        '''
        logger.info("Returning NEW audio")
        # self._assemble_audio()
        new_buffer: np.array = np.array([], dtype=np.int16)
        while self._read_chunk_id in self._audio:
            audio_data = self._audio[self._read_chunk_id]
            new_buffer = np.append(new_buffer, audio_data.data)
            self._read_chunk_id += 1
        return (new_buffer, self._sampling_rate)

    def get_all_audio(self) -> Tuple[np.array, int]:
        '''
        Returns the entire synthesized audio buffed

        Returns:
            Tuple[np.array, int]: tuple of (audio data buffer, sampling rate)
        '''
        logger.info("Returning ALL audio")
        # self._assemble_audio()
        new_buffer: np.array = np.array([], dtype=np.int16)
        for chunk_id in sorted(self._audio.keys()):
            audio_data = self._audio[chunk_id]
            new_buffer = np.append(new_buffer, audio_data.data)
        return (new_buffer, self._sampling_rate)

    def start_synthesis(self, text: str, voice: Tts.Voice):
        '''
        Begin synthesizing a large block of text.

        Cancels any on-going synthesis.

        Args:
            text (str): text to speak
            voice (Tts.Voice): voice parameters to use
        '''
        if self._pool_result:
            self.cancel()

        self.reset()

        sentences = TextUtils.split_sentences(text)
        chunk: str = ""
        chunks: List[Tuple[int, str]] = []
        word_cnt = 0
        chunk_id = 0
        for sentence in sentences:
            words = TextUtils.split_words(sentence)
            word_cnt += len(words)
            chunk += sentence + " "
            if word_cnt >= self._min_chunk_words:
                chunks.append((chunk_id, chunk))
                chunk = ""
                chunk_id += 1
        if chunk:
            chunks.append((chunk_id, chunk))

        self._sampling_rate = voice.get_sampling_rate()
        self._pool_result = self._pool.map_async(func=partial(self._worker_func, (self._pool_cancel_event, voice)),
                                                 iterable=chunks, callback=self._result_ready)

    def wait_for_audio(self, timeout: float = None) -> bool:
        ''' Checks for any audio, optionally blocking until audio is available'''
        return len(self._audio) > 0 or self._new_audio_avail_event.wait(timeout)

    def wait_for_new_audio(self, timeout: float = None) -> bool:
        ''' Checks for unprocessed audio, optionally blocking until audio is available'''
        end_time = time.time() + timeout if timeout else None
        audio_ready = self._read_chunk_id in self._audio

        while not audio_ready:
            remaining_timeout = end_time - time.time() if end_time else None
            signaled = self._new_audio_avail_event.wait(timeout=remaining_timeout)
            if signaled:
                audio_ready = self._read_chunk_id in self._audio
            else:
                break

        return audio_ready

    def _worker_func(self, *args, **kwargs):
        '''
        Background worker function to generate chunks of TTS audio
        '''
        (cancel_event, voice), (job_id, job_text) = args
        if cancel_event.is_set():
            return None

        logger.info(f"Start work on {job_id}, {job_text}")
        try:
            audio_data, sample_rate = self._tts.synthesize(text=job_text, voice=voice)
        except Exception as e:
            import traceback
            traceback.print_exception(e)
            logger.error(f"Synthesize Error: {e}")
        self._audio[job_id] = TtsQueue.AudioData(
            text=job_text, data=audio_data, sample_rate=sample_rate)
        self._new_audio_avail_event.set()
        logger.info(f"Done working on {job_id}")

    def _result_ready(self, *args, **kwargs):
        '''
        Callback when all results are ready
        '''
        # self._assemble_audio()
        logger.info("Synthesis complete")
        self._pool_result = None
