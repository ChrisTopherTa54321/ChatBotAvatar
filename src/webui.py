import gradio as gr
import logging
logger = logging.getLogger(__file__)


class WebUI:
    def __init__(self, args):
        self._uiChatbot: gr.Chatbot = None
        self._uiState: gr.State = None

    def buildInterface(self):

        with gr.Blocks(analytics_enabled=False) as interface:
            self._uiChatbot = gr.Chatbot()
            self._uiState = gr.State([])
            with gr.Row():
                with gr.Column(scale=4):
                    txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter").style(container=False)
                with gr.Column(scale=1):
                    submit_btn = gr.Button("Submit", width="1%")

        txt.submit(self.submitText, [txt, self._uiState], [self._uiChatbot, self._uiState])
        submit_btn.click(self.submitText, [txt, self._uiState], [self._uiChatbot, self._uiState])

    def submitText(self, *args, **kwargs):
        inputText, state = args
        response = state.append((f"{inputText}", f"Resposne to [{inputText}]!"))
        logger.info(f"Prediction!")
        return state, state


if __name__ == "__main__":
    demo.launch()
