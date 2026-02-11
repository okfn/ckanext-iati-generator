async function copyText(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) {
  }

  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "0";
    ta.style.left = "-9999px";
    ta.style.opacity = "0";
    document.body.appendChild(ta);

    ta.focus();
    ta.select();
    ta.setSelectionRange(0, ta.value.length);

    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch (e) {
    return false;
  }
}

document.addEventListener(
  "click",
  async function (e) {
    const btn = e.target.closest(".copy-link-btn");
    if (!btn) return;

    e.preventDefault();

    const url = btn.dataset.url;
    if (!url) {
      console.error("Copy failed: data-url is empty");
      return;
    }

    const ok = await copyText(url);

    const li = btn.closest("li");
    const message = li ? li.querySelector(".copy-message") : null;

    if (ok) {
      if (message) {
        message.style.display = "inline";
        setTimeout(() => {
          message.style.display = "none";
        }, 2000);
      }
    } else {
      window.prompt("Copy link:", url);
    }
  },
  true
);
