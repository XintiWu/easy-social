(function () {
  function mediaKind(file) {
    if (file.type.startsWith("image/")) {
      return "image";
    }
    if (file.type.startsWith("video/")) {
      return "video";
    }

    const extension = file.name.split(".").pop().toLowerCase();
    if (["gif", "jpg", "jpeg", "png", "webp"].includes(extension)) {
      return "image";
    }
    if (["mov", "mp4", "ogg", "webm"].includes(extension)) {
      return "video";
    }
    return "";
  }

  function clearPreview(preview, frame, name, input, state) {
    if (state.objectUrl) {
      URL.revokeObjectURL(state.objectUrl);
      state.objectUrl = "";
    }
    frame.replaceChildren();
    name.textContent = "";
    preview.hidden = true;
    if (input) {
      input.value = "";
    }
  }

  function setupComposerKind(composer) {
    const kindInputs = composer.querySelectorAll("[data-post-kind-input]");
    const pollOptions = composer.querySelector("[data-poll-options]");
    const mediaPicker = composer.querySelector("[data-composer-media-picker]");
    const body = composer.querySelector("[data-composer-body]");

    if (!kindInputs.length || !pollOptions || !mediaPicker || !body) {
      return;
    }

    function syncKind() {
      const isPoll = composer.querySelector('[data-post-kind-input][value="poll"]').checked;
      pollOptions.hidden = !isPoll;
      mediaPicker.hidden = isPoll;
      body.placeholder = isPoll ? "Ask a question (optional)" : "What is happening?";
    }

    kindInputs.forEach(function (input) {
      input.addEventListener("change", syncKind);
    });
    syncKind();
  }

  function setupComposer(composer) {
    setupComposerKind(composer);

    const input = composer.querySelector("[data-media-input]");
    const preview = composer.querySelector("[data-media-preview]");
    const frame = composer.querySelector("[data-media-preview-frame]");
    const name = composer.querySelector("[data-media-preview-name]");
    const clear = composer.querySelector("[data-media-preview-clear]");

    if (!input || !preview || !frame || !name || !clear) {
      return;
    }

    const state = { objectUrl: "" };

    input.addEventListener("change", function () {
      const file = input.files && input.files[0];
      clearPreview(preview, frame, name, null, state);

      if (!file) {
        return;
      }

      const kind = mediaKind(file);
      if (!kind) {
        return;
      }

      state.objectUrl = URL.createObjectURL(file);
      const element = document.createElement(kind === "image" ? "img" : "video");
      element.className = "composer-preview-media";
      element.src = state.objectUrl;

      if (kind === "image") {
        element.alt = "Selected image preview";
      } else {
        element.controls = true;
        element.muted = true;
        element.preload = "metadata";
      }

      frame.replaceChildren(element);
      name.textContent = file.name;
      preview.hidden = false;
    });

    clear.addEventListener("click", function () {
      clearPreview(preview, frame, name, input, state);
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  function setupCaptchaRefresh() {
    const image = document.getElementById("captcha-image");
    const refresh = document.getElementById("captcha-refresh");
    if (!image || !refresh) {
      return;
    }

    refresh.addEventListener("click", function () {
      const baseUrl = image.getAttribute("src").split("?")[0];
      image.src = `${baseUrl}?t=${Date.now()}`;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form.composer").forEach(setupComposer);
    setupCaptchaRefresh();
  });
})();
