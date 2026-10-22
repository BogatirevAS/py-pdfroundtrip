import json
from typing import Any
from pymupdf import Rect

from pdfroundtrip.domain.enums import JsonKey, StyleSwitch


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Rect):
            return {
                '__type__': 'Rect',
                'coords': [obj.x0, obj.y0, obj.x1, obj.y1]
            }
        return super().default(obj)


def decoder_hook(dct):
    if dct.get('__type__') == 'Rect':
        return Rect(*dct['coords'])
    return dct


def save_json(data, filepath, **kwargs):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, cls=CustomEncoder, **kwargs)


def load_json(filepath, **kwargs):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f, object_hook=decoder_hook, **kwargs)


def get_json_param(name: JsonKey, data: dict, default) -> Any:
    if default is None:
        default = StyleSwitch.ENABLE
    if isinstance(default, StyleSwitch):
        if (default == StyleSwitch.ENABLE) and isinstance(data, dict):
            return data.get(name.value, None)
        return None
    return default
