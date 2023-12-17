var YOLO_ROOT = null;
var YOLO_REGISTRY = {};
var YOLO_COMPONENTS = {};
var YOLO_RENDER_STACK = [];
var YOLO_ANCHOR_COUNTER = {};

class YoloWrapper {
    constructor(element) {
        this.element = element;
    }

    get id() {
        return this.getAttribute('id')
    }

    get y() {
        return yolo(this.id)
    }

    get state() {
        return yolo(this.id).state
    }

    set state(value) {
        yolo(this.id).state = value
    }

    render() {
        yolo(this.id).render()
    }

    get e() {
        return this.element
    }

    setAttribute(name, value) {
        this.element.setAttribute(name, value);
    }

    getAttribute(name) {
        return this.element.getAttribute(name);
    }

    setAction(component, event, name, ...args) {
        this.element.addEventListener(event, () => {
            component.actions[name](component, ...args);
        });
    }

    setCall(component, event, name, ...args) {
        this.element.addEventListener(event, () => {
            component.namespace[name](...args);
        });
    }
}

const __yolo__wrap = (element) => {
    if (!element.getAttribute('id'))
        element.setAttribute('id', crypto.randomUUID());
    return new YoloWrapper(element);
};


const __yolo__before_root_render = () => {
    YOLO_ANCHOR_COUNTER = {};
};

const __yolo__after_root_render = () => {
};

const __yolo__create_element = (tag, anchor, attrs=null, parent=null, cb=null) => {
    let element = null
    let yolo_elem = tag.startsWith('yolo:');
    let yolo_instance = null;
    if (yolo_elem) {
        element = document.createElement('div');
        element.setAttribute('yolo_for', tag.substring(5));
    } else {
        element = document.createElement(tag);
    }
    YOLO_RENDER_STACK.push(element);
    if (attrs) {
        for (let key in attrs) {
            if ('style' === key) {
                for (let style_key in attrs[key]) {
                    element.style[style_key] = attrs[key][style_key];
                }
            } else if ('class' === key) {
                element.className = attrs[key];
            } else if ('html' === key) {
                element.innerHTML = attrs[key];
            } else {
                element.setAttribute(key, attrs[key]);
            }
        }
    }
    if (yolo_elem) {
        if (!YOLO_ANCHOR_COUNTER[anchor]) {
            YOLO_ANCHOR_COUNTER[anchor] = 0;
        }
        anchor = `${anchor}-${YOLO_ANCHOR_COUNTER[anchor]++}`;
        if (!(yolo_instance = YOLO_REGISTRY[anchor])) {
            yolo_instance = YOLO_REGISTRY[anchor] = YOLO_COMPONENTS[tag.substring(5)].make(anchor);
        }
        element.setAttribute('id', anchor);
        element = yolo_instance.render(element);
    }
    if (cb) {
        cb(element);
    }
    if (parent) {
        parent.appendChild(element);
    }
    YOLO_RENDER_STACK.pop();
    return element;
};

const __yolo__text = (element, text) => {
    if (element instanceof YoloWrapper) {
        element = element.element;
    }

    if (!element.innerHTML) {
        element.innerHTML = '';
    }

    element.innerHTML += text;
};


class YoloInstance {
    constructor(component, anchor=null) {
        this.component = component;
        this.namespace = {};
        this.state = null;
        let val = component.init(this);
        if (val) { this.state = val; }
        this.cid = anchor ? anchor : crypto.randomUUID();
    }

    render(domid_or_element=null) {
        let element = null;
        if (this.component.is_root) {
            __yolo__before_root_render();
        }
        if (typeof domid_or_element == 'string') {
            element = document.getElementById(domid_or_element);
        } else if (domid_or_element instanceof Node) {
            element = domid_or_element;
        } else {
            element = document.getElementById(this.cid);
        }
        element.innerHTML = '';
        this.namespace = {};
        element.setAttribute('id', this.cid);
        this.component._render(this, element);
        if (this.component.is_root) {
            __yolo__after_root_render();
        }
        return element;
    }
}

class YoloComponent {
    constructor(identifier, init, render, actions, is_root=false) {
        this.identifier = identifier;
        this.init = init;
        this._render = render;
        this.actions = actions;
        this.is_root = is_root;
    }

    make(anchor=null) {
        return new YoloInstance(this, anchor);
    }
}

const __yolo__make_component = (identifier, init, render, actions, is_root) => {
    return new YoloComponent(identifier, init, render, actions, is_root);
};


const __yolo__fetch = (identifier, action, request_json, callback, ...args) => {
    const request = new XMLHttpRequest();
    request.open('POST', `/`, false);  // TODO: fix race between fetch and render
    request.setRequestHeader('Content-Type', 'application/json');
    request_data = request_json();
    if (args.length > 0) {
        request_data['args'] = args;
    }
    request.onload = () => {
        if (request.status >= 200 && request.status < 400) {
            callback(request_data, JSON.parse(request.responseText));
        } else {
            console.log('error');
        }
    };
    request.send(JSON.stringify({
        'identifier': identifier,
        'action': action,
        'request': request_data,
    }));
};

const __yolo__add_event_listener = (wrapper, event, callback) => {
    wrapper.element.addEventListener(event, callback);
};

const yolo = (id) => YOLO_REGISTRY[id];


const range = (start, end=null) => {
    if (end === null) {
        end = start;
        start = 0;
    }

    let result = [];
    for (let i = start; i < end; i++) {
        result.push(i);
    }
    return result;
};
