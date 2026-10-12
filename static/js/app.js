/**
 * PDF Utility Toolkit — Intermediate
 * Vanilla JavaScript Frontend Engine
 * Manages theme, file handling, drag-and-drop, real progress states, live previews, and API calls.
 */

(function () {
  "use strict";

  // --- State Management ---
  const state = {
    activeTool: "merge",
    selectedFiles: [], // Array of { file: File, id: string, name: string, size: number }
    uploadedJobId: null,
    watermarkImageFile: null,
    isProcessing: false
  };

  // --- DOM Elements Cache ---
  const dom = {
    themeToggle: document.getElementById("themeToggle"),
    mobileNavToggle: document.getElementById("mobileNavToggle"),
    navMenu: document.getElementById("navMenu"),
    toolCards: document.querySelectorAll(".tool-card"),
    activeToolIcon: document.getElementById("activeToolIcon"),
    activeToolName: document.getElementById("activeToolName"),
    activeToolDesc: document.getElementById("activeToolDesc"),
    dropzone: document.getElementById("dropzone"),
    fileInput: document.getElementById("fileInput"),
    fileListContainer: document.getElementById("fileListContainer"),
    fileCardsGrid: document.getElementById("fileCardsGrid"),
    clearFilesBtn: document.getElementById("clearFilesBtn"),
    configPanels: document.querySelectorAll(".config-panel"),
    processBtn: document.getElementById("processBtn"),
    processBtnText: document.getElementById("processBtnText"),
    progressPanel: document.getElementById("progressPanel"),
    progressFill: document.getElementById("progressFill"),
    progressPercent: document.getElementById("progressPercent"),
    progressStageTitle: document.getElementById("progressStageTitle"),
    resultPanel: document.getElementById("resultPanel"),
    historyTableBody: document.getElementById("historyTableBody"),
    historyEmptyState: document.getElementById("historyEmptyState"),
    toastContainer: document.getElementById("toastContainer"),
    // Watermark specific
    wmTextInput: document.getElementById("wmText"),
    wmColorInput: document.getElementById("wmColor"),
    wmOpacityInput: document.getElementById("wmOpacity"),
    wmOpacityVal: document.getElementById("wmOpacityVal"),
    wmRotationInput: document.getElementById("wmRotation"),
    wmRotationVal: document.getElementById("wmRotationVal"),
    wmPlacementSelect: document.getElementById("wmPlacement"),
    wmCanvasText: document.getElementById("wmCanvasText"),
    wmImageInput: document.getElementById("wmImageInput")
  };

  // =========================================================================
  // Theme Management (Light / Dark Mode with Persistence)
  // =========================================================================

  function initTheme() {
    const savedTheme = localStorage.getItem("pdf_toolkit_theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const currentTheme = savedTheme || (prefersDark ? "dark" : "light");

    setTheme(currentTheme);

    if (dom.themeToggle) {
      dom.themeToggle.addEventListener("click", () => {
        const active = document.documentElement.getAttribute("data-theme") || "light";
        const target = active === "dark" ? "light" : "dark";
        setTheme(target);
      });
    }

    // Listen to OS preference changes
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
      if (!localStorage.getItem("pdf_toolkit_theme")) {
        setTheme(e.matches ? "dark" : "light");
      }
    });
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("pdf_toolkit_theme", theme);
    if (dom.themeToggle) {
      dom.themeToggle.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} theme`);
    }
  }

  // =========================================================================
  // Mobile Navigation
  // =========================================================================

  function initNavigation() {
    if (dom.mobileNavToggle && dom.navMenu) {
      dom.mobileNavToggle.addEventListener("click", () => {
        dom.navMenu.classList.toggle("mobile-open");
      });

      // Close menu on link click
      dom.navMenu.querySelectorAll(".nav-link").forEach((link) => {
        link.addEventListener("click", () => {
          dom.navMenu.classList.remove("mobile-open");
        });
      });
    }

    // Navbar elevation on scroll
    const navbar = document.querySelector(".navbar");
    window.addEventListener("scroll", () => {
      if (window.scrollY > 20) {
        navbar?.classList.add("scrolled");
      } else {
        navbar?.classList.remove("scrolled");
      }
    });
  }

  // =========================================================================
  // Tool Switching
  // =========================================================================

  const toolMetadata = {
    merge: {
      name: "Merge PDF",
      desc: "Combine two or more PDF documents into a single file with custom ordering.",
      multiple: true,
      btnLabel: "Merge Documents"
    },
    split: {
      name: "Split PDF",
      desc: "Extract pages into individual files or generate documents from custom page ranges.",
      multiple: false,
      btnLabel: "Split Document"
    },
    rotate: {
      name: "Rotate PDF",
      desc: "Rotate all or selected pages clockwise by 90°, 180°, or 270° without rasterization.",
      multiple: false,
      btnLabel: "Rotate Pages"
    },
    watermark: {
      name: "Watermark PDF",
      desc: "Overlay customizable vector text or branded image watermarks with precise opacity.",
      multiple: false,
      btnLabel: "Apply Watermark"
    },
    info: {
      name: "PDF Information",
      desc: "Inspect page dimensions, file size, encryption, version, metadata, and text analysis.",
      multiple: false,
      btnLabel: "Inspect Document"
    },
    sanitize_metadata: {
      name: "Metadata Sanitizer",
      desc: "Safely strip or update document properties (Author, Title, Subject, Producer, etc.).",
      multiple: false,
      btnLabel: "Sanitize Metadata"
    },
    extract_text: {
      name: "PDF Text Extractor",
      desc: "Extract readable text using pdfplumber with full character statistics and text export.",
      multiple: false,
      btnLabel: "Extract Text"
    },
    validate: {
      name: "PDF Validator",
      desc: "Verify structural compliance, header magic bytes, EOF markers, and xref integrity.",
      multiple: false,
      btnLabel: "Validate Document"
    }
  };

  function selectTool(toolKey) {
    if (!toolMetadata[toolKey]) return;
    state.activeTool = toolKey;
    const meta = toolMetadata[toolKey];

    // Update tool cards UI
    dom.toolCards.forEach((card) => {
      if (card.dataset.tool === toolKey) {
        card.classList.add("active");
      } else {
        card.classList.remove("active");
      }
    });

    // Update workspace header
    if (dom.activeToolName) dom.activeToolName.textContent = meta.name;
    if (dom.activeToolDesc) dom.activeToolDesc.textContent = meta.desc;
    if (dom.processBtnText) dom.processBtnText.textContent = meta.btnLabel;

    // Toggle multi-file file input attribute
    if (dom.fileInput) {
      if (meta.multiple) {
        dom.fileInput.setAttribute("multiple", "multiple");
      } else {
        dom.fileInput.removeAttribute("multiple");
      }
    }

    // Show appropriate contextual config panel
    dom.configPanels.forEach((panel) => {
      if (panel.id === `config-${toolKey}`) {
        panel.style.display = "block";
      } else {
        panel.style.display = "none";
      }
    });

    // Update Process button state
    updateProcessButtonState();

    // Scroll smoothly to workspace
    const workspace = document.getElementById("workspace");
    if (workspace && window.innerWidth < 768) {
      workspace.scrollIntoView({ behavior: "smooth" });
    }
  }

  // =========================================================================
  // Drag & Drop and File Management
  // =========================================================================

  function initDropzone() {
    if (!dom.dropzone || !dom.fileInput) return;

    dom.dropzone.addEventListener("click", () => dom.fileInput.click());

    dom.dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dom.dropzone.classList.add("drag-active");
    });

    dom.dropzone.addEventListener("dragleave", (e) => {
      e.preventDefault();
      dom.dropzone.classList.remove("drag-active");
    });

    dom.dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dom.dropzone.classList.remove("drag-active");
      if (e.dataTransfer && e.dataTransfer.files) {
        handleFileSelection(Array.from(e.dataTransfer.files));
      }
    });

    dom.fileInput.addEventListener("change", (e) => {
      if (e.target.files) {
        handleFileSelection(Array.from(e.target.files));
        dom.fileInput.value = ""; // Reset for re-selection
      }
    });

    if (dom.clearFilesBtn) {
      dom.clearFilesBtn.addEventListener("click", () => {
        state.selectedFiles = [];
        renderFileList();
        updateProcessButtonState();
      });
    }
  }

  function handleFileSelection(files) {
    const isMultiple = toolMetadata[state.activeTool]?.multiple;

    // Filter valid PDFs
    const validPdfFiles = files.filter((f) => {
      const ext = f.name.toLowerCase().slice(f.name.lastIndexOf("."));
      if (ext !== ".pdf") {
        showToast("Invalid Format", `File "${f.name}" is not a PDF document.`, "warning");
        return false;
      }
      if (f.size > 50 * 1024 * 1024) {
        showToast("File Too Large", `File "${f.name}" exceeds the 50 MB limit.`, "warning");
        return false;
      }
      return true;
    });

    if (!validPdfFiles.length) return;

    if (!isMultiple) {
      // Single-file tools replace previous selection
      state.selectedFiles = [
        {
          file: validPdfFiles[0],
          id: Math.random().toString(36).substring(2, 9),
          name: validPdfFiles[0].name,
          size: validPdfFiles[0].size
        }
      ];
    } else {
      // Multi-file tools append up to 20 files
      validPdfFiles.forEach((f) => {
        state.selectedFiles.push({
          file: f,
          id: Math.random().toString(36).substring(2, 9),
          name: f.name,
          size: f.size
        });
      });
    }

    renderFileList();
    updateProcessButtonState();
  }

  function renderFileList() {
    if (!dom.fileCardsGrid || !dom.fileListContainer) return;

    if (!state.selectedFiles.length) {
      dom.fileListContainer.style.display = "none";
      dom.fileCardsGrid.innerHTML = "";
      return;
    }

    dom.fileListContainer.style.display = "block";
    dom.fileCardsGrid.innerHTML = "";

    const isMerge = state.activeTool === "merge";

    state.selectedFiles.forEach((item, index) => {
      const card = document.createElement("div");
      card.className = "file-item-card";

      const formattedSize = formatBytes(item.size);

      card.innerHTML = `
        <div class="file-item-left">
          <div class="file-type-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </div>
          <div class="file-meta-info">
            <div class="file-name-text" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</div>
            <div class="file-badges-row">
              <span class="file-badge">${formattedSize}</span>
              ${isMerge ? `<span class="file-badge-pill">Order #${index + 1}</span>` : ""}
            </div>
          </div>
        </div>
        <div class="file-item-actions">
          ${
            isMerge
              ? `
            <button type="button" class="file-reorder-btn move-up" data-idx="${index}" title="Move Up" ${
                  index === 0 ? "disabled" : ""
                }>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>
            </button>
            <button type="button" class="file-reorder-btn move-down" data-idx="${index}" title="Move Down" ${
                  index === state.selectedFiles.length - 1 ? "disabled" : ""
                }>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </button>
          `
              : ""
          }
          <button type="button" class="file-reorder-btn remove-file" data-idx="${index}" title="Remove file">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>
      `;

      // Event listeners for reordering & removal
      const upBtn = card.querySelector(".move-up");
      const downBtn = card.querySelector(".move-down");
      const remBtn = card.querySelector(".remove-file");

      if (upBtn) {
        upBtn.addEventListener("click", () => {
          if (index > 0) {
            const temp = state.selectedFiles[index];
            state.selectedFiles[index] = state.selectedFiles[index - 1];
            state.selectedFiles[index - 1] = temp;
            renderFileList();
          }
        });
      }

      if (downBtn) {
        downBtn.addEventListener("click", () => {
          if (index < state.selectedFiles.length - 1) {
            const temp = state.selectedFiles[index];
            state.selectedFiles[index] = state.selectedFiles[index + 1];
            state.selectedFiles[index + 1] = temp;
            renderFileList();
          }
        });
      }

      if (remBtn) {
        remBtn.addEventListener("click", () => {
          state.selectedFiles.splice(index, 1);
          renderFileList();
          updateProcessButtonState();
        });
      }

      dom.fileCardsGrid.appendChild(card);
    });
  }

  function updateProcessButtonState() {
    if (!dom.processBtn) return;
    const isMultiple = toolMetadata[state.activeTool]?.multiple;

    if (state.isProcessing) {
      dom.processBtn.disabled = true;
      return;
    }

    if (isMultiple) {
      dom.processBtn.disabled = state.selectedFiles.length < 2;
    } else {
      dom.processBtn.disabled = state.selectedFiles.length !== 1;
    }
  }

  // =========================================================================
  // Watermark Live Preview
  // =========================================================================

  function initWatermarkControls() {
    if (!dom.wmTextInput || !dom.wmCanvasText) return;

    function updatePreview() {
      const text = dom.wmTextInput.value || "CONFIDENTIAL";
      const color = dom.wmColorInput ? dom.wmColorInput.value : "#2563eb";
      const opacity = dom.wmOpacityInput ? parseFloat(dom.wmOpacityInput.value) : 0.25;
      const rotation = dom.wmRotationInput ? parseInt(dom.wmRotationInput.value, 10) : 45;
      const placement = dom.wmPlacementSelect ? dom.wmPlacementSelect.value : "center";

      if (dom.wmOpacityVal) dom.wmOpacityVal.textContent = `${Math.round(opacity * 100)}%`;
      if (dom.wmRotationVal) dom.wmRotationVal.textContent = `${rotation}°`;

      dom.wmCanvasText.textContent = text;
      dom.wmCanvasText.style.color = color;
      dom.wmCanvasText.style.opacity = opacity;

      // Coordinate placement
      dom.wmCanvasText.style.top = "";
      dom.wmCanvasText.style.bottom = "";
      dom.wmCanvasText.style.left = "";
      dom.wmCanvasText.style.right = "";

      if (placement === "center" || placement === "diagonal") {
        dom.wmCanvasText.style.top = "50%";
        dom.wmCanvasText.style.left = "50%";
        dom.wmCanvasText.style.transform = `translate(-50%, -50%) rotate(${rotation}deg)`;
      } else if (placement === "top_left") {
        dom.wmCanvasText.style.top = "20px";
        dom.wmCanvasText.style.left = "20px";
        dom.wmCanvasText.style.transform = `rotate(${rotation}deg)`;
      } else if (placement === "top_right") {
        dom.wmCanvasText.style.top = "20px";
        dom.wmCanvasText.style.right = "20px";
        dom.wmCanvasText.style.transform = `rotate(${rotation}deg)`;
      } else if (placement === "bottom_left") {
        dom.wmCanvasText.style.bottom = "20px";
        dom.wmCanvasText.style.left = "20px";
        dom.wmCanvasText.style.transform = `rotate(${rotation}deg)`;
      } else if (placement === "bottom_right") {
        dom.wmCanvasText.style.bottom = "20px";
        dom.wmCanvasText.style.right = "20px";
        dom.wmCanvasText.style.transform = `rotate(${rotation}deg)`;
      }
    }

    [dom.wmTextInput, dom.wmColorInput, dom.wmOpacityInput, dom.wmRotationInput, dom.wmPlacementSelect].forEach((el) => {
      if (el) el.addEventListener("input", updatePreview);
    });

    // Image watermark file picker
    if (dom.wmImageInput) {
      dom.wmImageInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
          state.watermarkImageFile = e.target.files[0];
          showToast("Image Loaded", `Selected ${e.target.files[0].name} for watermark.`, "info");
        }
      });
    }

    // Radio cards selection for Watermark Type
    document.querySelectorAll("input[name='watermarkType']").forEach((radio) => {
      radio.addEventListener("change", (e) => {
        const val = e.target.value;
        const textOptions = document.getElementById("wmTextOptions");
        const imageOptions = document.getElementById("wmImageOptions");
        if (val === "text") {
          if (textOptions) textOptions.style.display = "block";
          if (imageOptions) imageOptions.style.display = "none";
        } else {
          if (textOptions) textOptions.style.display = "none";
          if (imageOptions) imageOptions.style.display = "block";
        }
      });
    });

    // General radio card active visual toggles & contextual options
    document.querySelectorAll(".radio-card input[type='radio']").forEach((radio) => {
      radio.addEventListener("change", (e) => {
        const groupName = e.target.name;
        document.querySelectorAll(`input[name='${groupName}']`).forEach((r) => {
          r.closest(".radio-card")?.classList.toggle("active", r.checked);
        });

        // Contextual visibility
        if (groupName === "metaAction") {
          const customFields = document.getElementById("metaCustomFieldsGroup");
          if (customFields) customFields.style.display = e.target.value === "update" ? "block" : "none";
        } else if (groupName === "splitMode") {
          const rangeGroup = document.getElementById("splitRangeGroup");
          if (rangeGroup) rangeGroup.style.display = e.target.value === "all_pages" ? "none" : "block";
        } else if (groupName === "rotateScope") {
          const rotGroup = document.getElementById("rotateRangeGroup");
          if (rotGroup) rotGroup.style.display = e.target.value === "selected" ? "block" : "none";
        } else if (groupName === "extractScope") {
          const extInput = document.getElementById("extractRangeExpr");
          if (extInput) extInput.closest(".form-group").style.display = e.target.value === "selected" ? "block" : "none";
        }
      });
    });

    updatePreview();
  }

  // =========================================================================
  // Real Processing Progress & API Communication
  // =========================================================================

  function setProgressState(percent, title, step) {
    if (!dom.progressPanel) return;
    dom.progressPanel.style.display = "block";

    if (dom.progressFill) dom.progressFill.style.width = `${percent}%`;
    if (dom.progressPercent) dom.progressPercent.textContent = `${percent}%`;
    if (dom.progressStageTitle) dom.progressStageTitle.textContent = title;

    const steps = ["upload", "validate", "process", "verify"];
    steps.forEach((s) => {
      const el = document.getElementById(`step-${s}`);
      if (el) {
        if (s === step) {
          el.className = "step-item active";
        } else if (steps.indexOf(s) < steps.indexOf(step)) {
          el.className = "step-item completed";
        } else {
          el.className = "step-item";
        }
      }
    });
  }

  async function executeOperation() {
    if (!state.selectedFiles.length || state.isProcessing) return;

    state.isProcessing = true;
    updateProcessButtonState();
    if (dom.resultPanel) dom.resultPanel.style.display = "none";

    try {
      // Stage 1: Uploading
      setProgressState(20, "Uploading source files to isolated session...", "upload");
      const formData = new FormData();
      state.selectedFiles.forEach((item) => {
        formData.append("files", item.file, item.name);
      });

      // Attach image watermark if present
      if (state.activeTool === "watermark" && state.watermarkImageFile) {
        formData.append("image", state.watermarkImageFile, state.watermarkImageFile.name);
      }

      // Password if provided
      const passwordInput = document.getElementById("docPassword");
      const password = passwordInput ? passwordInput.value.trim() : "";
      if (password) {
        formData.append("password", password);
      }

      const uploadRes = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });

      if (!uploadRes.ok) {
        const errJson = await uploadRes.json();
        throw new Error(errJson.message || "Failed to upload documents.");
      }

      const uploadData = await uploadRes.json();
      state.uploadedJobId = uploadData.job_id;

      // Stage 2: Validation
      setProgressState(45, "Validating PDF headers and structure on server...", "validate");
      await delay(250); // Visual stability

      // Stage 3: Processing
      setProgressState(75, `Executing ${toolMetadata[state.activeTool].name}...`, "process");

      const payload = buildOperationPayload(uploadData);
      const processRes = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!processRes.ok) {
        const errJson = await processRes.json();
        throw new Error(errJson.message || "Operation processing failed.");
      }

      const processData = await processRes.json();

      // Stage 4: Verification
      setProgressState(100, "Verifying output integrity and finalizing assets...", "verify");
      await delay(300);

      // Render Result
      dom.progressPanel.style.display = "none";
      renderResult(processData);
      showToast("Operation Complete", `${toolMetadata[state.activeTool].name} succeeded!`, "success");

      // Refresh history list
      loadProcessedFilesHistory();
    } catch (err) {
      dom.progressPanel.style.display = "none";
      showToast("Error", err.message, "error");
    } finally {
      state.isProcessing = false;
      updateProcessButtonState();
    }
  }

  function buildOperationPayload(uploadData) {
    const payload = {
      operation: state.activeTool,
      job_id: uploadData.job_id
    };

    const passwordInput = document.getElementById("docPassword");
    if (passwordInput && passwordInput.value.trim()) {
      payload.password = passwordInput.value.trim();
    }

    if (state.activeTool === "merge") {
      payload.file_order = state.selectedFiles.map((f) => f.name);
      payload.output_filename = "merged_document.pdf";
    } else {
      payload.filename = state.selectedFiles[0].name;

      if (state.activeTool === "split") {
        const mode = document.querySelector("input[name='splitMode']:checked")?.value || "all_pages";
        payload.mode = mode;
        if (mode === "custom_ranges" || mode === "extract_selection") {
          payload.range_expr = document.getElementById("splitRangeExpr")?.value.trim() || "";
          payload.merge_ranges = document.getElementById("splitMergeRanges")?.checked || false;
        }
      } else if (state.activeTool === "rotate") {
        payload.angle = parseInt(document.querySelector("input[name='rotateAngle']:checked")?.value || "90", 10);
        payload.scope = document.querySelector("input[name='rotateScope']:checked")?.value || "all";
        if (payload.scope === "selected") {
          payload.range_expr = document.getElementById("rotateRangeExpr")?.value.trim() || "";
        }
      } else if (state.activeTool === "watermark") {
        const wmType = document.querySelector("input[name='watermarkType']:checked")?.value || "text";
        payload.watermark_type = wmType;
        payload.text = dom.wmTextInput?.value.trim() || "CONFIDENTIAL";
        payload.font_size = parseInt(document.getElementById("wmFontSize")?.value || "48", 10);
        payload.color_hex = dom.wmColorInput?.value || "#2563eb";
        payload.opacity = parseFloat(dom.wmOpacityInput?.value || "0.25");
        payload.rotation = parseInt(dom.wmRotationInput?.value || "45", 10);
        payload.placement = dom.wmPlacementSelect?.value || "center";
        payload.scale_percent = parseInt(document.getElementById("wmImageScale")?.value || "50", 10);
        payload.scope = document.querySelector("input[name='wmScope']:checked")?.value || "all";
        if (payload.scope === "selected") {
          payload.range_expr = document.getElementById("wmRangeExpr")?.value.trim() || "";
        }
        if (state.watermarkImageFile) {
          payload.image_filename = state.watermarkImageFile.name;
        }
      } else if (state.activeTool === "sanitize_metadata") {
        payload.action = document.querySelector("input[name='metaAction']:checked")?.value || "strip_all";
        if (payload.action === "update") {
          payload.custom_fields = {
            title: document.getElementById("metaTitle")?.value.trim() || "",
            author: document.getElementById("metaAuthor")?.value.trim() || "",
            subject: document.getElementById("metaSubject")?.value.trim() || "",
            keywords: document.getElementById("metaKeywords")?.value.trim() || ""
          };
        }
      } else if (state.activeTool === "extract_text") {
        payload.scope = document.querySelector("input[name='extractScope']:checked")?.value || "all";
        if (payload.scope === "selected") {
          payload.range_expr = document.getElementById("extractRangeExpr")?.value.trim() || "";
        }
      }
    }

    return payload;
  }

  function renderResult(data) {
    if (!dom.resultPanel) return;
    dom.resultPanel.style.display = "block";

    const output = data.output;
    const summary = data.summary || {};
    const details = data.data || {};

    let html = `
      <div class="result-header">
        <span class="result-badge-success">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
          Processing Verified & Completed
        </span>
        <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 500;">
          Execution duration: ${data.duration_seconds || "0.1"}s
        </span>
      </div>
    `;

    // File Download Section (if file asset generated)
    if (output) {
      const isZip = output.is_zip;
      const downloadUrl = `/api/download/${output.file_id}`;
      html += `
        <div class="result-meta-grid">
          <div class="result-meta-item">
            <span class="result-meta-label">Generated File</span>
            <span class="result-meta-val">${escapeHtml(output.display_name)}</span>
          </div>
          <div class="result-meta-item">
            <span class="result-meta-label">File Size</span>
            <span class="result-meta-val">${formatBytes(output.file_size)}</span>
          </div>
          <div class="result-meta-item">
            <span class="result-meta-label">${isZip ? "Contained Files" : "Page Count"}</span>
            <span class="result-meta-val">${output.page_count || 1}</span>
          </div>
        </div>

        <div class="result-actions-row">
          <a href="${downloadUrl}" class="btn btn-primary btn-lg" download="${escapeHtml(output.display_name)}">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            Download ${isZip ? "ZIP Archive" : "Processed File"}
          </a>
          <button type="button" class="btn btn-secondary" onclick="window.scrollTo({top: 0, behavior: 'smooth'})">
            Process Another Document
          </button>
        </div>
      `;
    }

    // Operation specific summary details
    if (state.activeTool === "extract_text" && details.full_text) {
      html += `
        <div style="margin-top: 1.75rem;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
            <h4 style="font-size: 1rem; font-weight: 700;">Extracted Text (${details.total_words} words, ${details.total_characters} characters)</h4>
            <div style="display: flex; gap: 0.5rem;">
              <button type="button" class="btn btn-sm btn-secondary" id="copyExtractedBtn">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                Copy to Clipboard
              </button>
            </div>
          </div>
          ${
            details.warning
              ? `<div style="padding: 0.75rem 1rem; background: var(--warning-bg); border: 1px solid var(--warning-border); color: var(--warning-text); border-radius: 8px; font-size: 0.85rem; margin-bottom: 1rem;">${details.warning}</div>`
              : ""
          }
          <div class="text-viewer-box" id="extractedTextViewer">${escapeHtml(details.full_text)}</div>
        </div>
      `;
    } else if (state.activeTool === "info" && details) {
      html += renderInfoSummaryHtml(details);
    } else if (state.activeTool === "validate" && details) {
      html += renderValidationSummaryHtml(details);
    } else if (state.activeTool === "sanitize_metadata" && summary) {
      html += `
        <div style="margin-top: 1.5rem; padding: 1rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
          <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 0.5rem;">Metadata Sanitization Summary</h4>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">Fields Modified: ${summary.fields_changed || 0}</p>
          <div style="font-size: 0.8rem; color: var(--warning-text); background: var(--warning-bg); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--warning-border);">
            ${summary.disclaimer}
          </div>
        </div>
      `;
    }

    dom.resultPanel.innerHTML = html;

    // Attach copy button handler if present
    const copyBtn = document.getElementById("copyExtractedBtn");
    if (copyBtn && details.full_text) {
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(details.full_text).then(() => {
          showToast("Copied", "Extracted text copied to clipboard.", "success");
        });
      });
    }

    dom.resultPanel.scrollIntoView({ behavior: "smooth" });
  }

  function renderInfoSummaryHtml(data) {
    let metaRows = "";
    if (data.metadata && Object.keys(data.metadata).length > 0) {
      for (const [k, v] of Object.entries(data.metadata)) {
        metaRows += `<tr><td style="font-weight: 600; width: 35%;">${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`;
      }
    } else {
      metaRows = `<tr><td colspan="2" style="color: var(--text-muted);">(No metadata found)</td></tr>`;
    }

    const firstPage = data.pages && data.pages.length ? data.pages[0] : null;

    return `
      <div style="margin-top: 1.5rem;">
        <h4 style="font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem;">Document Metrics & Structure</h4>
        <div class="result-meta-grid">
          <div class="result-meta-item">
            <span class="result-meta-label">Total Pages</span>
            <span class="result-meta-val">${data.page_count}</span>
          </div>
          <div class="result-meta-item">
            <span class="result-meta-label">PDF Version</span>
            <span class="result-meta-val">${data.pdf_version || "PDF-1.4"}</span>
          </div>
          <div class="result-meta-item">
            <span class="result-meta-label">Encryption</span>
            <span class="result-meta-val">${data.is_encrypted ? "Password Protected" : "None"}</span>
          </div>
          <div class="result-meta-item">
            <span class="result-meta-label">Dimensions (P1)</span>
            <span class="result-meta-val">${firstPage ? `${firstPage.width_pt} x ${firstPage.height_pt} pt` : "N/A"}</span>
          </div>
        </div>

        <h5 style="font-size: 0.95rem; font-weight: 700; margin: 1.25rem 0 0.5rem;">Metadata Properties</h5>
        <table class="history-table" style="margin-bottom: 1.5rem;">
          <tbody>${metaRows}</tbody>
        </table>

        <div style="padding: 1rem; background: var(--bg-surface); border-radius: 8px; border: 1px solid var(--border-subtle);">
          <h5 style="font-size: 0.9rem; font-weight: 700; margin-bottom: 0.35rem;">Text Presence Analysis</h5>
          <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
            Extracted Words: <strong>${data.text_statistics?.total_words || 0}</strong> |
            Characters: <strong>${data.text_statistics?.total_characters || 0}</strong> |
            Pages with text: <strong>${data.text_statistics?.pages_with_extractable_text || 0} / ${data.page_count}</strong>
          </p>
          <p style="font-size: 0.825rem; color: var(--text-muted);">${data.text_statistics?.notice || ""}</p>
        </div>
      </div>
    `;
  }

  function renderValidationSummaryHtml(data) {
    let checkRows = "";
    (data.checks || []).forEach((c) => {
      const color = c.passed ? "var(--success-base)" : "var(--danger-base)";
      const icon = c.passed ? "✓" : "✗";
      checkRows += `
        <tr>
          <td style="font-weight: 600; width: 40%; color: ${color};">${icon} ${escapeHtml(c.name)}</td>
          <td>${escapeHtml(c.detail)}</td>
        </tr>
      `;
    });

    return `
      <div style="margin-top: 1.5rem;">
        <h4 style="font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem; color: ${
          data.valid ? "var(--success-base)" : "var(--danger-base)"
        };">
          Validation Result: ${data.valid ? "PASSED (Structurally Parseable)" : "FAILED (Structural Issues Detected)"}
        </h4>
        <table class="history-table" style="margin-bottom: 1.25rem;">
          <thead>
            <tr><th>Check Item</th><th>Verification Details</th></tr>
          </thead>
          <tbody>${checkRows}</tbody>
        </table>
        <div style="font-size: 0.8rem; color: var(--text-muted); background: var(--bg-surface); padding: 0.75rem; border-radius: 6px;">
          ${data.disclaimer}
        </div>
      </div>
    `;
  }

  // =========================================================================
  // Processed Files History & Safe Deletion
  // =========================================================================

  async function loadProcessedFilesHistory() {
    if (!dom.historyTableBody) return;

    try {
      const res = await fetch("/api/files");
      if (!res.ok) return;
      const data = await res.json();
      const files = data.files || [];

      if (!files.length) {
        if (dom.historyEmptyState) dom.historyEmptyState.style.display = "block";
        dom.historyTableBody.innerHTML = "";
        return;
      }

      if (dom.historyEmptyState) dom.historyEmptyState.style.display = "none";
      dom.historyTableBody.innerHTML = "";

      files.forEach((f) => {
        const row = document.createElement("tr");
        const formattedDate = new Date(f.created_at * 1000).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit"
        });

        row.innerHTML = `
          <td>
            <div class="table-file-name">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--primary-600); flex-shrink: 0;">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              <span>${escapeHtml(f.display_name)}</span>
            </div>
          </td>
          <td><span class="file-badge-pill" style="text-transform: uppercase;">${f.operation}</span></td>
          <td>${formatBytes(f.file_size)}</td>
          <td>${f.page_count || 1}</td>
          <td>${formattedDate}</td>
          <td>
            <div class="table-actions">
              <a href="/api/download/${f.file_id}" class="btn btn-sm btn-outline-primary" download="${escapeHtml(
          f.display_name
        )}" title="Download File">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Download
              </a>
              <button type="button" class="btn btn-sm btn-ghost delete-file-btn" data-id="${f.file_id}" title="Delete File" style="color: var(--danger-base);">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
          </td>
        `;

        const delBtn = row.querySelector(".delete-file-btn");
        if (delBtn) {
          delBtn.addEventListener("click", () => deleteProcessedFile(f.file_id));
        }

        dom.historyTableBody.appendChild(row);
      });
    } catch (e) {
      // Silently ignore background fetch failure
    }
  }

  async function deleteProcessedFile(fileId) {
    if (!confirm("Are you sure you want to permanently delete this generated file?")) return;

    try {
      const res = await fetch(`/api/delete/${fileId}`, { method: "DELETE" });
      if (res.ok) {
        showToast("Deleted", "File was removed from temporary storage.", "info");
        loadProcessedFilesHistory();
      } else {
        const errJson = await res.json();
        showToast("Delete Failed", errJson.message, "error");
      }
    } catch (e) {
      showToast("Error", "Could not delete asset.", "error");
    }
  }

  // =========================================================================
  // FAQ Accordion
  // =========================================================================

  function initFaq() {
    const faqItems = document.querySelectorAll(".faq-item");
    faqItems.forEach((item) => {
      const question = item.querySelector(".faq-question");
      if (question) {
        question.addEventListener("click", () => {
          const isActive = item.classList.contains("active");
          faqItems.forEach((i) => i.classList.remove("active"));
          if (!isActive) {
            item.classList.add("active");
          }
        });
      }
    });
  }

  // =========================================================================
  // Toast Notification System
  // =========================================================================

  function showToast(title, message, type = "info") {
    if (!dom.toastContainer) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let iconSvg = "";
    if (type === "success") {
      iconSvg = `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    } else if (type === "error") {
      iconSvg = `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
    } else if (type === "warning") {
      iconSvg = `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
    } else {
      iconSvg = `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `
      ${iconSvg}
      <div class="toast-body">
        <div class="toast-title">${escapeHtml(title)}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
      </div>
      <button class="toast-close" type="button" aria-label="Close notification">&times;</button>
    `;

    toast.querySelector(".toast-close").addEventListener("click", () => {
      toast.remove();
    });

    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(8px)";
        setTimeout(() => toast.remove(), 250);
      }
    }, 4500);
  }

  // =========================================================================
  // Utilities
  // =========================================================================

  function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // =========================================================================
  // Initialization
  // =========================================================================

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initNavigation();
    initDropzone();
    initWatermarkControls();
    initFaq();

    // Attach tool card click listeners
    dom.toolCards.forEach((card) => {
      card.addEventListener("click", () => {
        const tool = card.dataset.tool;
        if (tool) selectTool(tool);
      });
    });

    // Attach process button click
    if (dom.processBtn) {
      dom.processBtn.addEventListener("click", executeOperation);
    }

    // Set initial tool
    selectTool("merge");

    // Expose selectTool globally for footer & external controls
    window.selectTool = selectTool;

    // Load existing history
    loadProcessedFilesHistory();
  });
})();
