function set_theme(theme) {
    gradioURL = window.location.href
    if (!gradioURL.includes('?__theme=')) {
        window.location.replace(gradioURL + '?__theme=' + theme);
    }
}

function check_for_audio() {
    audio_player = gradioApp().getElementById('audioplayer');
    audio_player.click()
}

function play_audio_file() {
    audio_player = gradioApp().getElementById('audioplayer');
}

function gradioApp() {
    const elems = document.getElementsByTagName('gradio-app')
    const gradioShadowRoot = elems.length == 0 ? null : elems[0].shadowRoot
    return !!gradioShadowRoot ? gradioShadowRoot : document;
}