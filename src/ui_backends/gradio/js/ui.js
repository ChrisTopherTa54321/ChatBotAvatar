var tts_audio_observer = new MutationObserver(audio_player_dom_changed);

function start_listen_for_audio_component_updates() {
    stop_listen_for_audio_component_updates();
    tts_audio_observer.observe(get_audio_player_container(), { childList: true });
    console.log("Started watching for audio changes");
}

function stop_listen_for_audio_component_updates() {
    tts_audio_observer.disconnect();
    console.log("Stopped watching for audio changes");
}

function audio_player_dom_changed(dom_changes, observer) {
    console.log("Dom Change");
    dom_changes.forEach(function (change) {
        change.addedNodes.forEach(function (new_node) {
            if ("audio" == new_node.tagName.toLowerCase()) {
                console.log("Dom change, audio found, play!");
                stop_listen_for_audio_component_updates();
                audio_player = get_audio_player();
                audio_player?.addEventListener('ended', audio_player_done_playing);
                audio_player?.play()
            }
        });
    });
}

function audio_player_done_playing() {
    console.log("Audio Done Playing")
    trigger_audio_update();
}

function trigger_audio_update(...theArgs) {
    console.log("Trigger audio update!");
    start_listen_for_audio_component_updates()
    get_audio_trigger_checkbox().click();
}

function get_audio_trigger_checkbox() {
    return gradioApp()?.getElementById('audio_trigger_relay')?.querySelectorAll('input[type=checkbox')[0];
}

function get_audio_player() {
    return get_audio_player_container()?.getElementsByTagName("AUDIO")[0];
}

function get_audio_player_container() {
    return gradioApp()?.getElementById('tts_streaming_audio_player');
}


// Copied from AUTOMATIC1111 stable-diffusion-webui
function gradioApp() {
    const elems = document.getElementsByTagName('gradio-app');
    const gradioShadowRoot = elems.length == 0 ? null : elems[0].shadowRoot;
    return !!gradioShadowRoot ? gradioShadowRoot : document;
}

function set_theme(theme) {
    gradioURL = window.location.href;
    if (!gradioURL.includes('?__theme=')) {
        window.location.replace(gradioURL + '?__theme=' + theme);
    }
}
