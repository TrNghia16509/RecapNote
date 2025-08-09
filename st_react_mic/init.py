import os
import streamlit.components.v1 as components

_component_func = components.declare_component(
    "st_react_mic",
    path=os.path.join(os.path.dirname(__file__), "frontend/build")
)

def st_react_mic(key=None):
    data = _component_func(key=key, default=None)
    if data:
        return bytes(bytearray(data))
    return None
