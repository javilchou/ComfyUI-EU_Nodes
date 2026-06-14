import { app } from "../../../scripts/app.js";

const NODE_TYPE = "EU_TextConcatenatorPlus";
const TEXT_PREFIX = "text";
const MIN_VISIBLE = 4;
const MAX_TEXTS = 20;

function getWidget(node, name) {
    return node.widgets?.find((widget) => widget.name === name);
}

function getInputIndex(node, name) {
    return node.inputs?.findIndex((input) => input.name === name || input.widget?.name === name) ?? -1;
}

function hasLinkedInput(node, name) {
    const index = getInputIndex(node, name);
    return index >= 0 && node.inputs?.[index]?.link != null;
}

function ensureTextInput(node, name) {
    if (getInputIndex(node, name) !== -1) return;
    node.addInput(name, "STRING", { widget: { name } });
}

function removeTextInput(node, name) {
    const index = getInputIndex(node, name);
    if (index !== -1) {
        node.removeInput(index);
    }
}

function hasTextValue(node, index) {
    const name = `${TEXT_PREFIX}${index}`;
    const widget = getWidget(node, name);
    const value = widget?.value ?? "";
    return String(value) !== "" || hasLinkedInput(node, name);
}

function stashWidget(widget) {
    if (!widget || widget.euConcatOrig) return;
    widget.euConcatOrig = {
        type: widget.type,
        computeSize: widget.computeSize,
        serialize: widget.serialize,
    };
}

function setWidgetVisible(widget, visible) {
    if (!widget) return;
    stashWidget(widget);

    widget.hidden = !visible;
    widget.serialize = visible ? widget.euConcatOrig.serialize : false;

    if (visible) {
        widget.type = widget.euConcatOrig.type;
        widget.computeSize = widget.euConcatOrig.computeSize;
    } else {
        widget.type = "hidden";
        widget.computeSize = () => [0, -4];
    }
}

function calculateVisibleCount(node) {
    let visible = MIN_VISIBLE;

    for (let i = MIN_VISIBLE; i < MAX_TEXTS; i += 1) {
        if (!hasTextValue(node, i)) break;
        visible = i + 1;
    }

    return visible;
}

function updateTextWidgets(node) {
    const visibleCount = calculateVisibleCount(node);

    for (let i = 1; i <= MAX_TEXTS; i += 1) {
        const name = `${TEXT_PREFIX}${i}`;
        const widget = getWidget(node, name);
        const visible = i <= visibleCount;

        setWidgetVisible(widget, visible);

        if (visible) {
            ensureTextInput(node, name);
        } else {
            removeTextInput(node, name);
            if (widget) widget.value = "";
        }
    }

    node.setSize(node.computeSize());
    app.graph.setDirtyCanvas(true, true);
}

function wrapWidgetCallback(node, widget) {
    if (!widget || widget.euConcatWrapped) return;

    const originalCallback = widget.callback;
    widget.callback = function (...args) {
        const result = originalCallback?.apply(this, args);
        updateTextWidgets(node);
        return result;
    };

    widget.euConcatWrapped = true;
}

app.registerExtension({
    name: "EU.TextConcatenatorPlus",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_TYPE) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = onNodeCreated?.apply(this, args);

            for (const widget of this.widgets || []) {
                if (
                    widget.name?.startsWith(TEXT_PREFIX)
                    || widget.name === "separator"
                    || widget.name === "换行"
                    || widget.name === "跳过空行"
                ) {
                    wrapWidgetCallback(this, widget);
                }
            }

            setTimeout(() => updateTextWidgets(this), 0);
            return result;
        };

        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (...args) {
            const result = onConnectionsChange?.apply(this, args);
            setTimeout(() => updateTextWidgets(this), 0);
            return result;
        };
    },
});
