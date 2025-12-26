(() => {
	const barcodeInput = document.getElementById("barcode");
	const titleInput = document.getElementById("title");
	const sourceInput = document.getElementById("source");
	const form = document.getElementById("barcode-form");
	const result = document.getElementById("scan-result");

	const cameraPanel = document.getElementById("camera-panel");
	const toggleCameraBtn = document.getElementById("toggle-camera");
	const stopCameraBtn = document.getElementById("stop-camera");
	const cameraVideo = document.getElementById("camera");
	const cameraHint = document.getElementById("camera-hint");

	let cameraStream = null;
	let detector = null;
	let scanning = false;
	let scanLoopHandle = null;

	// Wedge heuristic state (keyboard-emulated scans)
	let digitKeyTimes = [];
	let lastValue = "";

	function resetWedgeHeuristic() {
		digitKeyTimes = [];
		lastValue = barcodeInput ? barcodeInput.value || "" : "";
	}

	function isLikelyWedge(value) {
		// Heuristic: rapid digit burst producing a valid-length numeric barcode.
		// Typical wedges emit keystrokes extremely quickly; humans don't.
		if (!value) return false;
		if (!/^\d{8,14}$/.test(value)) return false;
		if (digitKeyTimes.length < Math.min(8, value.length)) return false;

		const first = digitKeyTimes[0];
		const last = digitKeyTimes[digitKeyTimes.length - 1];
		const durationMs = last - first;
		const avgMs = durationMs / Math.max(1, digitKeyTimes.length - 1);

		// Conservative thresholds:
		// - average <= 35ms between digits OR total <= 400ms for 12-13 digits.
		if (avgMs <= 35) return true;
		if (value.length >= 10 && durationMs <= 400) return true;
		return false;
	}

	function focusBarcode() {
		if (!barcodeInput) return;
		const active = document.activeElement;
		// Don't steal focus from any other interactive element.
		const okToFocus =
			!active ||
			active === document.body ||
			active === document.documentElement ||
			active === barcodeInput;
		if (!okToFocus) return;
		barcodeInput.focus({ preventScroll: true });
	}

	function formatLocalTimes(root = document) {
		const nodes = root.querySelectorAll("time.batch-time[datetime]");
		if (!nodes.length) return;

		const formatter = new Intl.DateTimeFormat(undefined, {
			year: "numeric",
			month: "short",
			day: "2-digit",
			hour: "2-digit",
			minute: "2-digit",
			second: "2-digit",
		});

		nodes.forEach((node) => {
			const iso = node.getAttribute("datetime") || "";
			const d = new Date(iso);
			if (Number.isNaN(d.getTime())) return;
			node.textContent = formatter.format(d);
		});
	}

	// PWA service worker
	if ("serviceWorker" in navigator) {
		window.addEventListener("load", () => {
			navigator.serviceWorker.register("/service-worker.js").catch(() => {
				// Ignore registration errors (still works as normal web app)
			});
		});
	}

	// HTMX: keep scanner workflows fast by re-focusing input after swaps.
	document.body.addEventListener("htmx:afterSwap", (e) => {
		if (e.target && e.target.id === "scan-result") {
			focusBarcode();
			if (sourceInput) sourceInput.value = "manual";
			if (barcodeInput) barcodeInput.select();
			// Clear title only when we successfully added to batch.
			if (titleInput && e.target.querySelector(".result-ok")) titleInput.value = "";
		}

		// Batch updates are delivered out-of-band; format any newly swapped timestamps.
		formatLocalTimes(document);
	});

	// Custom confirmation modal (replaces browser confirm())
	const confirmOverlay = document.getElementById("confirm-modal");
	const confirmMessage = document.getElementById("confirm-message");
	const confirmCancel = document.getElementById("confirm-cancel");
	const confirmOk = document.getElementById("confirm-ok");

	let confirmState = null;

	function hideConfirmModal({ restoreFocus = true } = {}) {
		if (!confirmOverlay) return;
		confirmOverlay.classList.add("hidden");
		confirmOverlay.setAttribute("aria-hidden", "true");
		if (confirmOk) confirmOk.disabled = false;
		if (confirmCancel) confirmCancel.disabled = false;
		if (restoreFocus && confirmState && confirmState.previouslyFocused) {
			try {
				confirmState.previouslyFocused.focus({ preventScroll: true });
			} catch {
				// ignore
			}
		}
		confirmState = null;
	}

	function showConfirmModal({ message, okText, onConfirm }) {
		if (!confirmOverlay || !confirmMessage || !confirmCancel || !confirmOk) {
			return false;
		}

		confirmState = {
			onConfirm,
			previouslyFocused: document.activeElement,
		};

		confirmMessage.textContent = String(message || "Are you sure?");
		confirmOk.textContent = String(okText || "OK");
		confirmOverlay.classList.remove("hidden");
		confirmOverlay.setAttribute("aria-hidden", "false");
		confirmOk.focus({ preventScroll: true });
		return true;
	}

	if (confirmOverlay) {
		confirmOverlay.addEventListener("click", (e) => {
			// Clicking the dimmed overlay closes the modal; clicks inside the modal should not.
			if (e.target === confirmOverlay) hideConfirmModal();
		});
		window.addEventListener("keydown", (e) => {
			if (!confirmState) return;
			if (e.key === "Escape") {
				e.preventDefault();
				hideConfirmModal();
			}
		});
	}

	if (confirmCancel) {
		confirmCancel.addEventListener("click", () => hideConfirmModal());
	}

	if (confirmOk) {
		confirmOk.addEventListener("click", async () => {
			if (!confirmState || typeof confirmState.onConfirm !== "function") {
				hideConfirmModal();
				return;
			}
			confirmOk.disabled = true;
			confirmCancel.disabled = true;
			try {
				confirmState.onConfirm();
			} finally {
				hideConfirmModal({ restoreFocus: false });
			}
		});
	}

	// HTMX confirm override: opt-in via data-confirm-modal="1".
	const htmxConfirmHandler = (evt) => {
		let el = evt && evt.detail && evt.detail.target ? evt.detail.target : null;
		if (!el) return;
		if (el.closest) el = el.closest("[data-confirm-modal='1']") || el;
		if (!el.dataset || el.dataset.confirmModal !== "1") return;

		// Only run when HTMX is actually attempting to confirm (i.e., hx-confirm exists).
		const question = evt && evt.detail ? evt.detail.question : null;
		if (!question) return;

		// Prevent HTMX from showing window.confirm.
		evt.preventDefault();

		const message = String(question || "Are you sure?");
		const okText = (el.dataset && el.dataset.confirmOk) || "OK";
		const didShow = showConfirmModal({
			message,
			okText,
			onConfirm: () => {
				if (evt.detail && typeof evt.detail.issueRequest === "function") {
					// true => skip built-in window.confirm() and only use our modal
					evt.detail.issueRequest(true);
				}
			},
		});

		// If modal couldn't render for some reason, don't silently do nothing.
		if (!didShow) {
			// Fall back to not issuing the request (safer than accidental delete).
		}
	};
	// Capture + bubble registration for max compatibility
	document.addEventListener("htmx:confirm", htmxConfirmHandler, true);
	document.body.addEventListener("htmx:confirm", htmxConfirmHandler);

	// Deterministic modal confirm for specific buttons:
	// - Elements opt in with data-confirm-modal="1" and data-confirm-message
	// - Their htmx request is bound to hx-trigger="confirmed"
	// - On OK, we programmatically trigger the "confirmed" event
	const confirmClickHandler = (evt) => {
		const target = evt && evt.target ? evt.target : null;
		if (!target || !target.closest) return;
		const el = target.closest("[data-confirm-modal='1'][data-confirm-message]");
		if (!el) return;

		// Only intercept if the element is configured to wait for the custom event.
		const triggerSpec = el.getAttribute("hx-trigger") || "";
		if (!triggerSpec.includes("confirmed")) return;

		evt.preventDefault();
		evt.stopPropagation();
		if (typeof evt.stopImmediatePropagation === "function") evt.stopImmediatePropagation();

		const message = el.dataset.confirmMessage || "Are you sure?";
		const okText = el.dataset.confirmOk || "OK";
		showConfirmModal({
			message,
			okText,
			onConfirm: () => {
				if (window.htmx && typeof window.htmx.trigger === "function") {
					window.htmx.trigger(el, "confirmed");
				}
			},
		});
	};
	// Capture phase so we intercept even if other listeners stop propagation.
	document.addEventListener("click", confirmClickHandler, true);

	// Wedge scanner friendliness
	if (barcodeInput) {
		resetWedgeHeuristic();

		barcodeInput.addEventListener("focus", () => {
			resetWedgeHeuristic();
			if (sourceInput) sourceInput.value = "manual";
		});

		barcodeInput.addEventListener("keydown", (e) => {
			// Record timing only for digit keys (wedge emits digits rapidly)
			if (/^\d$/.test(e.key)) {
				digitKeyTimes.push(performance.now());
				// keep it bounded
				if (digitKeyTimes.length > 32) digitKeyTimes.shift();
			}

			if (e.key === "Backspace" || e.key === "Delete") {
				// user editing implies manual
				if (sourceInput) sourceInput.value = "manual";
				resetWedgeHeuristic();
			}

			if (e.key === "Enter") {
				// Let the form submit (HTMX handles it). If we already decided it's wedge, keep it.
				if (sourceInput && sourceInput.value !== "camera" && sourceInput.value !== "wedge") {
					// Many wedges send Enter suffix; require the timing heuristic to match.
					const v = (barcodeInput.value || "").trim();
					sourceInput.value = isLikelyWedge(v) ? "wedge" : "manual";
				}
			}
		});

		barcodeInput.addEventListener("input", (e) => {
			const v = (barcodeInput.value || "").trim();

			// Paste/drop should be treated as manual (not a wedge burst).
			const inputType = e && e.inputType ? String(e.inputType) : "";
			if (inputType === "insertFromPaste" || inputType === "insertFromDrop") {
				if (sourceInput && sourceInput.value !== "camera") sourceInput.value = "manual";
				resetWedgeHeuristic();
				lastValue = v;
				return;
			}

			// Any change in the barcode field should be at least considered manual unless wedge is detected.
			if (sourceInput && sourceInput.value !== "camera") {
				if (isLikelyWedge(v)) {
					sourceInput.value = "wedge";
				} else {
					// Only force manual when the user is typing/editing; don't override camera.
					sourceInput.value = "manual";
				}
			}

			// Reset the heuristic if the value was cleared or drastically changed.
			if (v.length === 0 || (lastValue && v.length < lastValue.length - 2)) {
				resetWedgeHeuristic();
			}
			lastValue = v;
		});
	}

	function setCameraPanelVisible(visible) {
		if (!cameraPanel) return;
		cameraPanel.classList.toggle("hidden", !visible);
		cameraPanel.setAttribute("aria-hidden", visible ? "false" : "true");
	}

	async function stopCamera({ resetSource = true } = {}) {
		scanning = false;
		if (scanLoopHandle) {
			cancelAnimationFrame(scanLoopHandle);
			scanLoopHandle = null;
		}
		if (cameraStream) {
			cameraStream.getTracks().forEach((t) => t.stop());
			cameraStream = null;
		}
		if (cameraVideo) {
			cameraVideo.srcObject = null;
		}
		setCameraPanelVisible(false);
		if (resetSource && sourceInput) sourceInput.value = "manual";
		focusBarcode();
	}

	async function startCamera() {
		if (!cameraPanel || !cameraVideo) return;

		if (!("BarcodeDetector" in window)) {
			cameraHint.textContent = "Camera scanning is not supported in this browser. Use manual entry or a wedge scanner.";
			setCameraPanelVisible(true);
			return;
		}

		try {
			detector = new window.BarcodeDetector({
				formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128"],
			});
		} catch {
			detector = new window.BarcodeDetector();
		}

		try {
			cameraStream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: { ideal: "environment" } },
				audio: false,
			});
			cameraVideo.srcObject = cameraStream;
			await cameraVideo.play();
			setCameraPanelVisible(true);
			scanning = true;
			if (sourceInput) sourceInput.value = "camera";
			cameraHint.textContent = "Point the camera at a barcode.";

			const scanTick = async () => {
				if (!scanning) return;
				try {
					const barcodes = await detector.detect(cameraVideo);
					if (barcodes && barcodes.length) {
						const value = (barcodes[0].rawValue || "").trim();
						if (barcodeInput) barcodeInput.value = value;

						// Auto-submit; HTMX will intercept the submit event if present.
						if (form) form.requestSubmit();
						await stopCamera({ resetSource: false });
						return;
					}
				} catch {
					// keep trying
				}
				scanLoopHandle = requestAnimationFrame(scanTick);
			};

			scanLoopHandle = requestAnimationFrame(scanTick);
		} catch {
			cameraHint.textContent = "Camera permission denied or unavailable. Use manual entry or a wedge scanner.";
			setCameraPanelVisible(true);
		}
	}

	if (toggleCameraBtn) {
		toggleCameraBtn.addEventListener("click", () => {
			startCamera();
		});
	}

	if (stopCameraBtn) {
		stopCameraBtn.addEventListener("click", () => {
			stopCamera({ resetSource: true });
		});
	}

	// Default focus for PC wedge scanners
	window.addEventListener("pageshow", () => {
		focusBarcode();
		formatLocalTimes(document);
	});
})();
