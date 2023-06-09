from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
from gradio.components import Component
from functools import partial

from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from utils.tts_chunker import TtsChunker

logger = logging.getLogger(__file__)


class TtsSpeaker(GradioComponent):
    @dataclass
    class StateData:
        chunker: TtsChunker = None

    def __init__(self, tts_settings: Optional[TtsSettings] = None):
        self._ui_state: gr.State = None
        self._ui_prompt_textbox: gr.Textbox = None
        self._ui_submit_btn: gr.Button = None
        self._ui_cancel_btn: gr.Button = None
        self._ui_stream_checkbox: gr.Checkbox = None
        self._ui_tts_settings: TtsSettings = tts_settings

        self._ui_start_streaming_relay: Component = None
        self._ui_full_audio_relay: Component = None
        self._ui_stream_audio_relay: Component = None
        self._ui_play_streaming_relay: Component = None
        self._ui_instance_id: gr.Textbox = None
        self._ui_full_audio: gr.Audio = None
        self._ui_streaming_audio: gr.Audio = None
        self._build_component()

    def _build_component(self):
        self._ui_state = gr.State(value=TtsSpeaker.StateData)
        with gr.Row():
            with gr.Column(scale=2):
                self._ui_prompt_textbox = gr.Textbox(show_label=False, placeholder="Text to speak")
            with gr.Column(scale=1):
                self._ui_submit_btn = gr.Button("Generate Speech", variant="primary")
                self._ui_cancel_btn = gr.Button("Cancel Synthesis", visible=False)
                self._ui_stream_checkbox = gr.Checkbox(value=True, label="Auto-Play/Stream")
                if not self._ui_tts_settings:
                    with gr.Box():
                        self._ui_tts_settings = TtsSettings()
        with gr.Row():
            self._ui_streaming_audio = gr.Audio(label="Streaming Audio", elem_id="streaming_audio", visible=False)
        with gr.Row():
            self._ui_full_audio = gr.Audio(label="Full Audio", elem_id="full_audio", visible=False)
        self._ui_instance_id = gr.Markdown(
            value=lambda: f"<div id='{uuid.uuid4().hex}'>Search Target!</div>", visible=False)

        # When this event is *output to* it will run its function and then output to its outputs
        self._ui_play_streaming_relay = EventWrapper.create_wrapper(fn_delay=1, _js="start_audio_streamer_drop2", inputs=[
                                                                    self._ui_instance_id], name="Autoplayer Relay")
        self._ui_full_audio_relay = EventRelay.create_relay(
            fn=self._full_audio_handler, inputs=[self.instance_data], outputs=[self._ui_full_audio, self._ui_cancel_btn, self._ui_submit_btn], name="Full Audio Relay")
        self._ui_stream_audio_relay = EventRelay.create_relay(
            fn=self._streaming_audio_handler, inputs=[self.instance_data, self._ui_play_streaming_relay],
            outputs=[self._ui_streaming_audio, self._ui_play_streaming_relay], elem_id="refresh_streaming",
            name="Stream Audio Relay")

        def set_button_states(synthesizing: bool):
            return (gr.Button.update(visible=not synthesizing), gr.Button.update(visible=synthesizing))

        submit_prompt_wrapper = EventWrapper.create_wrapper_list(
            wrapped_func_list=[
                EventWrapper.WrappedFunc(fn=partial(set_button_states, synthesizing=True),
                                         outputs=[self._ui_submit_btn, self._ui_cancel_btn]),
                EventWrapper.WrappedFunc(fn=self._handle_submit_click,
                                         inputs=[self.instance_data, self._ui_tts_settings.instance_data,
                                                 self._ui_prompt_textbox, self._ui_stream_audio_relay, self._ui_full_audio_relay, self._ui_stream_checkbox],
                                         outputs=[self._ui_stream_audio_relay,
                                                  self._ui_full_audio_relay]
                                         )],
            finally_func=EventWrapper.WrappedFunc(fn=partial(set_button_states, synthesizing=False), outputs=[
                                                  self._ui_submit_btn, self._ui_cancel_btn])
        )

        self._ui_submit_btn.click(**EventWrapper.get_event_args(submit_prompt_wrapper))
        self._ui_cancel_btn.click(fn=self._handle_cancel_tts, inputs=[self.instance_data])

    def _handle_cancel_tts(self, inst_data: TtsSpeaker.StateData):
        inst_data.chunker.cancel()

    def _handle_submit_click(self, inst_data: TtsSpeaker.StateData, tts_settings: TtsSettings.StateData, prompt: str, streaming_relay: bool, full_audio_relay: bool, streaming_enabled: bool) -> Tuple[EventRelay, EventRelay]:
        '''
        Starts process TTS when the Submit button is pressed

        Args:
            inst_data (TtsSpeaker.StateData): tts instance data
            tts_settings (TtsSettings.StateData): tts settings instance data
            prompt (str): prompt to speak
            streaming_relay (bool): relay to toggle in order to trigger streaming audio
        '''
        if inst_data.chunker and not inst_data.chunker.is_done():
            logger.warn("Already a TTS chunker!")
            return (streaming_relay, full_audio_relay)

        if tts_settings.voice is None:
            logger.warn("No voice selected!")
            return (streaming_relay, full_audio_relay)

        inst_data.chunker = TtsChunker()
        inst_data.chunker.start_synthesis(prompt, tts_settings.voice)
        logger.info("Waiting for first samples...")
        success = inst_data.chunker.wait_for_audio(timeout=240)

        if success:
            logger.info("First samples received! Triggering audio")
            if streaming_enabled:
                streaming_relay = not streaming_relay
            return (streaming_relay, not full_audio_relay)
        logger.info("No samples received before timeout")
        return (streaming_relay, full_audio_relay)

    def _full_audio_handler(self, inst_data: TtsSpeaker.StateData):
        success = inst_data.chunker.wait_for_audio_complete()
        if success:
            all_audio_buffer, sampling_rate = inst_data.chunker.get_all_audio()
            all_audio = (sampling_rate, all_audio_buffer)
        else:
            all_audio = (None, None)
        return [gr.Audio.update(visible=True, value=all_audio), gr.update(visible=False), gr.update(visible=True)]

    def _streaming_audio_handler(self, inst_data: TtsSpeaker.StateData, play_streaming_relay: bool):
        success = inst_data.chunker.wait_for_new_audio()
        if success:
            audio_buffer, sampling_rate = inst_data.chunker.get_new_audio()
            return [gr.Audio.update(visible=True, value=(sampling_rate, audio_buffer)), not play_streaming_relay]
        else:
            return [gr.Audio.update(visible=False), play_streaming_relay]

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state

    @property
    def output_audio(self) -> gr.Audio:
        return self._ui_full_audio

    @property
    def prompt(self) -> gr.Textbox:
        return self._ui_prompt_textbox

    @property
    def tts_settings(self) -> TtsSettings:
        return self._ui_tts_settings
