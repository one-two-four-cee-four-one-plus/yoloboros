COMPONENT_IDENTIFIER = '__yolo__identifier'
COMPONENT_ACTIONS = '__yolo__actions'
COMPONENT_INIT = '__yolo__init'
COMPONENT_RENDER = '__yolo__render'
COMPONENT_WRAP = '__yolo__wrap'
COMPONENT_NODE_CREATE = '__yolo__create_element'
COMPONENT_TEXT = '__yolo__text'
COMPONENT_MAKE = '__yolo__make_component'
COMPONENT_FETCH = '__yolo__fetch'
COMPONENT_MAKE_FULL = f'{COMPONENT_MAKE}({COMPONENT_IDENTIFIER}, {COMPONENT_INIT}, {COMPONENT_RENDER}, {COMPONENT_ACTIONS}, {{is_root}})'
COMPONENT_ADD_EVENT_LISTENER = '__yolo__add_event_listener'
COMPONENT_LOCALS = '__yolo_locals'
