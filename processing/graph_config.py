# graph_config.py

GRAPH_PROCESSING_CONFIG = {
    'num_floors': 1,  # fallback default
    'top_n_heuristic_entrances': 5,
    'primary_positive_indicator': "ACCESS GRANTED",
    'invalid_phrases_exact': ["INVALID ACCESS LEVEL"],
    'invalid_phrases_contain': ["NO ENTRY MADE"],
    'same_door_scan_threshold_seconds': 10,
    'ping_pong_threshold_minutes': 1
}

# graph_config.py

GRAPH_PROCESSING_CONFIG = {
    'num_floors': 1,
    'top_n_heuristic_entrances': 5,
    'primary_positive_indicator': "ACCESS GRANTED",
    'invalid_phrases_exact': ["INVALID ACCESS LEVEL"],
    'invalid_phrases_contain': ["NO ENTRY MADE"],
    'same_door_scan_threshold_seconds': 10,
    'ping_pong_threshold_minutes': 1
}

# ✅ Add UI display constants here:
UI_STYLES = {
    'hide': {'display': 'none'},
    'show_block': {'display': 'block'},
    'show_flex_stats': {
        'display': 'flex',
        'flexDirection': 'row',
        'justifyContent': 'space-around',
        'marginBottom': '30px'
    }
}
