import { Plugin, PluginKey } from "prosemirror-state";
import { Decoration, DecorationSet } from "prosemirror-view";
import { authFetch } from "../../utils/api";

export const autocompletePluginKey = new PluginKey("autocomplete");

/**
 * TipTap plugin for showing inline grey suggestion.
 */
export function autocompletePlugin() {
  return new Plugin({
    key: autocompletePluginKey,

    state: {
      init() {
        return { suggestion: "", pos: null };
      },
      apply(tr, prev) {
        const meta = tr.getMeta(autocompletePluginKey);
        if (meta !== undefined) return meta;

        if (tr.docChanged && !tr.getMeta("autocomplete-insert")) {
          return { suggestion: "", pos: null };
        }

        if (prev.pos !== null) {
          return { ...prev, pos: tr.mapping.map(prev.pos) };
        }

        return prev;
      },
    },

    props: {
      decorations(state) {
        const pluginState = autocompletePluginKey.getState(state);
        if (!pluginState) return DecorationSet.empty;

        const { suggestion, pos } = pluginState;
        if (!suggestion || pos == null) return DecorationSet.empty;

        const widget = Decoration.widget(
          pos,
          () => {
            const span = document.createElement("span");
            span.textContent = suggestion;
            span.style.cssText =
              "color: grey; pointer-events: none; user-select: none;";
            return span;
          },
          { side: 1 }
        );

        return DecorationSet.create(state.doc, [widget]);
      },

      // ── Key handling lives HERE — runs before TipTap/ProseMirror sees it
      handleKeyDown(view, event) {
        const pluginState = autocompletePluginKey.getState(view.state);
        if (!pluginState?.suggestion) return false;

        const { suggestion } = pluginState;

        // Accept with ArrowRight — safe, nothing else uses it for editing
        if (event.key === "ArrowRight") {
          event.preventDefault();

          const { from } = view.state.selection;

          const charBefore = view.state.doc.textBetween(
            Math.max(0, from - 1),
            from,
            "\n"
          );

          const needsSpace =
            charBefore !== "" &&
            charBefore !== " " &&
            charBefore !== "\n";

          const textToInsert = needsSpace ? " " + suggestion : suggestion;

          // Clear suggestion first
          view.dispatch(
            view.state.tr.setMeta(autocompletePluginKey, {
              suggestion: "",
              pos: null,
            })
          );

          // Insert text
          view.dispatch(
            view.state.tr
              .insertText(textToInsert)
              .setMeta("autocomplete-insert", true)
          );

          return true; // event consumed — nothing else runs
        }

        // Any other key — clear suggestion, let the key behave normally
        view.dispatch(
          view.state.tr.setMeta(autocompletePluginKey, {
            suggestion: "",
            pos: null,
          })
        );
        return false;
      },

      handleDOMEvents: {
        mousedown(view) {
          const pluginState = autocompletePluginKey.getState(view.state);
          if (pluginState?.suggestion) {
            view.dispatch(
              view.state.tr.setMeta(autocompletePluginKey, {
                suggestion: "",
                pos: null,
              })
            );
          }
          return false;
        },
      },
    },
  });
}

/**
 * Helper to set or clear suggestion
 */
function setSuggestion(editor, suggestion, pos) {
  const tr = editor.state.tr.setMeta(autocompletePluginKey, {
    suggestion: suggestion || "",
    pos: suggestion ? pos : null,
  });
  editor.view.dispatch(tr);
}

/**
 * Send last words to backend
 */
export async function sendToBackend(lastWords, editor, setSuggestionState) {
  try {
    const response = await authFetch("/api/projects/srs/autocomplete", {
      method: "POST",
      body: JSON.stringify({ text: lastWords }),
    });

    const data = await response.json();

    const suggestion = data.suggestion || "";
    const pos = editor.state.selection.from;

    setSuggestion(editor, suggestion, pos);
    if (setSuggestionState) setSuggestionState(suggestion);

    console.log("Autocomplete suggestion:", suggestion);
  } catch (err) {
    console.error("Autocomplete error:", err);
    setSuggestion(editor, "", null);
  }
}

/**
 * Trigger autocomplete (only in valid positions)
 */
export function triggerAutocomplete(editor, setSuggestionState) {
  if (!editor) return;

  const { from } = editor.state.selection;
  const docSize = editor.state.doc.content.size;

  const textAfterCursor = editor.state.doc.textBetween(from, docSize, "\n");
  const textAfterOnSameLine = textAfterCursor.split("\n")[0];
  if (/\S/.test(textAfterOnSameLine)) return;

  const charBefore = editor.state.doc.textBetween(
    Math.max(0, from - 1),
    from,
    "\n"
  );
  const charAfter = editor.state.doc.textBetween(from, from + 1, "\n");
  if (/\w/.test(charBefore) && /\w/.test(charAfter)) return;

  const textBeforeCursor = editor.state.doc.textBetween(
    Math.max(0, from - 200),
    from,
    "\n"
  );

  const words = textBeforeCursor.trim().split(/\s+/);
  const lastWords = words.slice(-5).join(" ");

  sendToBackend(lastWords, editor, setSuggestionState);
}

// No longer needed — remove any calls to this from your components.
export function handleAutocompleteKeydown() {}


// // autocomplete.js
// import { Plugin, PluginKey } from "prosemirror-state";
// import { Decoration, DecorationSet } from "prosemirror-view";
// import { authFetch } from "../../utils/api";
// export const autocompletePluginKey = new PluginKey("autocomplete");

// /**
//  * TipTap plugin for showing inline grey suggestion.
//  * The suggestion is stored IN plugin state so that setting it via a
//  * transaction correctly triggers a re-render of decorations.
//  */
// export function autocompletePlugin() {
//   return new Plugin({
//     key: autocompletePluginKey,

//     // Plugin state: { suggestion: string, pos: number | null }
//     state: {
//       init() {
//         return { suggestion: "", pos: null };
//       },
//       apply(tr, prev) {
//         // Check if this transaction carries a suggestion update
//         const meta = tr.getMeta(autocompletePluginKey);
//         if (meta !== undefined) return meta;

//         // If the doc changed (user typed), clear the suggestion
//         if (tr.docChanged) return { suggestion: "", pos: null };

//         // Map the stored position forward through any changes
//         if (prev.pos !== null) {
//           return { ...prev, pos: tr.mapping.map(prev.pos) };
//         }

//         return prev;
//       },
//     },

//     props: {
//       decorations(state) {
//         const pluginState = autocompletePluginKey.getState(state);
//         if (!pluginState) return DecorationSet.empty;
//         const { suggestion, pos } = pluginState;
//         if (!suggestion || pos == null) return DecorationSet.empty;

//         const widget = Decoration.widget(
//           pos,
//           () => {
//             const span = document.createElement("span");
//             span.textContent = suggestion;
//             span.style.cssText =
//               "color: grey; pointer-events: none; user-select: none;";
//             return span;
//           },
//           { side: 1 }
//         );

//         return DecorationSet.create(state.doc, [widget]);
//       },
//     },
//   });
// }

// /**
//  * Helper to set or clear the suggestion via a proper transaction.
//  */
// function setSuggestion(editor, suggestion, pos) {
//   const tr = editor.state.tr.setMeta(autocompletePluginKey, {
//     suggestion: suggestion || "",
//     pos: suggestion ? pos : null,
//   });
//   editor.view.dispatch(tr);
// }

// /**
//  * Send last words to backend and handle suggestion
//  */
// export async function sendToBackend(lastWords, editor, setSuggestionState) {
//   try {
//     const response = await authFetch(
//       "/api/projects/srs/autocomplete",
//       {
//         method: "POST",
//         body: JSON.stringify({ text: lastWords }),
//       }
//     );
//     const data = await response.json();

//     const suggestion = data.suggestion || "";
//     const pos = editor.state.selection.from;

//     setSuggestion(editor, suggestion, pos);

//     if (setSuggestionState) setSuggestionState(suggestion);
//     console.log("Autocomplete suggestion:", suggestion);
//   } catch (err) {
//     console.error("Autocomplete error:", err);
//     setSuggestion(editor, "", null);
//   }
// }

// /**
//  * Trigger autocomplete (call when idle typing)
//  */
// // AFTER
// export function triggerAutocomplete(editor, setSuggestionState) {
//   if (!editor) return;

//   const { from } = editor.state.selection;
//   const docSize = editor.state.doc.content.size;

//   // Don't trigger if there's any non-whitespace text ahead of the cursor
// const textAfterCursor = editor.state.doc.textBetween(from, docSize, "\n");
// const textAfterOnSameLine = textAfterCursor.split("\n")[0];
// if (textAfterOnSameLine.trim().length > 0) return;

//   const textBeforeCursor = editor.state.doc.textBetween(
//     Math.max(0, from - 200),
//     from,
//     "\n"
//   );

//   const words = textBeforeCursor.trim().split(/\s+/);
//   const lastWords = words.slice(-5).join(" ");

//   sendToBackend(lastWords, editor, setSuggestionState);
// }

// /**
//  * Handle key events for autocomplete
//  */
// export function handleAutocompleteKeydown(event, editor) {
//   if (!editor) return;

//   const pluginState = autocompletePluginKey.getState(editor.state);
//   if (!pluginState) return;
//   const { suggestion } = pluginState;
//   if (!suggestion) return;

//   if (event.key === "Tab") {
//     event.preventDefault();

//     const { from } = editor.state.selection;

//     // Prepend a space if the character before the cursor isn't one
//     const charBeforeCursor = editor.state.doc.textBetween(
//       Math.max(0, from - 1),
//       from,
//       "\n"
//     );
//     const needsSpace = charBeforeCursor !== "" && charBeforeCursor !== " ";
//     const textToInsert = needsSpace ? " " + suggestion : suggestion;

//     // Clear first, then insert — avoids the doc-changed watcher
//     // clobbering the insert
//     setSuggestion(editor, "", null);
//     editor.commands.insertContent(textToInsert);
//   } else {
//     // Any other key: clear the suggestion
//     setSuggestion(editor, "", null);
//   }
// }