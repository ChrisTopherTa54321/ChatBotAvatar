function prompt_for_name(...theArgs) {
    var ret = [prompt("Enter name")].concat(theArgs);
    console.log(ret);
    return ret;
}

function relay_confirm_prompt(relay_value, ...theArgs) {
    if (confirm("Are you sure?")) {
        return !relay_value;
    }
    return relay_value;
}

function find_relation(search_value, target_query, max_levels = 10) {
    /* Finds a node by search_value, then finds the nearest related node matching target_query */
    search_target = gradioApp()?.getElementById(search_value);
    result = null
    while (search_target && max_levels > 0) {
        result = search_target.querySelectorAll(target_query)
        if (result.length > 0) {
            break;
        }
        search_target = search_target.parentNode
        max_levels--;
    }
    return result
}

function start_audio_streamer(search_value, ...theArgs) {
    search_uuid = search_value.match(/id='(.*)'/)[1]
    streaming_audio = find_relation(search_uuid, "#streaming_audio")?.[0]?.getElementsByTagName("AUDIO")?.[0];
    if (streaming_audio) {
        refresh_toggle = find_relation(search_uuid, "#refresh_streaming")?.[0]?.querySelectorAll('input[type=checkbox')?.[0];
        streaming_audio.addEventListener('ended', function () { refresh_toggle.click(); });
        streaming_audio.addEventListener('canplay', function () { streaming_audio.play(); });
    }
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
