def init_json():
    import json
    import os

    #json state initialization
    default_state = {
        'ragged_proto': False, #if we've already ragged against the network docs, we never need to again so need to keep track
        'proto_store': {},
        'already_printed': False #if the chat_history and init_qa have already been printed on screen in main.py, we don't want it to print over and over and over again
    }
    state_file = 'src/app_state.json'
    if os.path.exists(state_file) and os.path.getsize(state_file) == 0:
        with open(state_file, 'w') as f:
            json.dump(default_state, f, indent=4)

    return default_state
    
def load_state(state_file):
    import json
    import os
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    else:
        return { #We want to load all these pieces of state so that when we just want to answer a question about a pcap that has already been ragged
                #we don't have to go through the entire rag process again, we already have the necessary info about THAT pcap
            'ragged_proto': False, #if we've already ragged against the network docs, we never need to again so need to keep track
            'proto_store': {}
        }   
    
def save_state(state_file, state):
    import json
    with open(state_file, 'w') as f:
        json.dump(state, f)