import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

// Displays input text on a node

app.registerExtension({
	name: "Comfyui_MiniCPM-V-2_6-int4.MiniCPM_Chat",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "MiniCPM_Chat") {
			const onExecuted = nodeType.prototype.onExecuted;
			nodeType.prototype.onExecuted = function (message) {
				onExecuted?.apply(this, arguments);

				if (this.widgets) {
					const pos = this.widgets.findIndex((w) => w.name === "result");
					if (pos !== -1) {
						for (let i = pos; i < this.widgets.length; i++) {
							this.widgets[i].onRemove?.();
						}
						this.widgets.length = pos;
					}
				}

				const w = ComfyWidgets["STRING"](this, "result", ["STRING", { multiline: true }], app).widget;
				w.inputEl.readOnly = true;
				w.inputEl.style.opacity = 0.6;
				w.value = message.text;

				this.onResize?.(this.size);
			};
		}
	},
});
