function set_theme(theme) {
    gradioURL = window.location.href
    if (!gradioURL.includes('?__theme=')) {
        window.location.replace(gradioURL + '?__theme=' + theme);
    }
}

function check_for_audio(audio_data) {
    audio_player = gradioApp()?.getElementById('audioplayer')?.getElementsByTagName("AUDIO");
    if( audio_player && audio_player.length > 0 ) {
        audio_player[0].play()
    }
}

function gradioApp() {
    const elems = document.getElementsByTagName('gradio-app')
    const gradioShadowRoot = elems.length == 0 ? null : elems[0].shadowRoot
    return !!gradioShadowRoot ? gradioShadowRoot : document;
}