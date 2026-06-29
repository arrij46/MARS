export function initContextMenu(editor, setChatInput, setChatOpen) {
  let selectedText = "";

  editor.view.dom.addEventListener("mouseup", () => {
    setTimeout(() => {
      const menu = document.getElementById("customMenu");
      if (!menu) return;

      const { from, to } = editor.state.selection;
      if (from === to) {
        menu.style.display = "none";
        return;
      }

      selectedText = editor.state.doc.textBetween(from, to, " ").trim();
      if (!selectedText) {
        menu.style.display = "none";
        return;
      }

      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) return;

      const rect = selection.getRangeAt(0).getBoundingClientRect();
      menu.style.position = "fixed";
      menu.style.top = `${rect.bottom + 6}px`;
      menu.style.left = `${rect.left}px`;
      menu.style.display = "block";

      const sendOption = document.getElementById("sendToLLM");
      if (sendOption) {
        sendOption.onclick = () => {
          setChatInput((prev) => prev ? `${prev} ${selectedText}` : selectedText);
          setChatOpen(true);
          menu.style.display = "none";
        };
      }
    }, 10);
  });

  document.addEventListener("mousedown", (event) => {
    const menu = document.getElementById("customMenu");
    if (!menu) return;
    if (!menu.contains(event.target)) {
      menu.style.display = "none";
    }
  });
}