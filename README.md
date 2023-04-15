## AvatarChatBot
An collection of tools for chat bots and lip syncing videos

This is currently Alpha quality.

### Pre-Reqs
* To generate videos requires FFMPEG be installed on your system and available in your path (eg, typing 'ffmpeg' by itself on the command line should work)
* To use the ChatGPT integration requires an OpenAI API key: https://platform.openai.com/account/api-keys
* To use the AzureTTS voices requires an Azure Cognitive Services 'Speech service' API key: https://azure.microsoft.com/en-us/products/cognitive-services/speech-services/
* To generate images, you must have access to an https://github.com/AUTOMATIC1111/stable-diffusion-webui server with the --api flag enabled. The server should have ControlNet installed.
* This was developed with Python 3.10. Other versions may work.

### Installation
1. Clone the repo
2. Edit 'webui-user.bat' or 'webui-user.sh' to adjust command line parameters, such as Stable Diffusion webui host (run 'python main.py --help' for help)
4. Run 'webui.bat' or 'webui.sh'
