import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
// for authentication fetches
import { authFetch } from "../utils/api";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import TextAlign from "@tiptap/extension-text-align";
import Highlight from "@tiptap/extension-highlight";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import { TextStyle } from "@tiptap/extension-text-style";
import { Color } from "@tiptap/extension-color";
import FontFamily from "@tiptap/extension-font-family";
import { Extension } from "@tiptap/core";
import "../style/editorPage.css";

import ChatbotPopup from "../components/editor-page/chatbotPopup";
import {
  triggerAutocomplete,
  handleAutocompleteKeydown,
  autocompletePlugin,
} from "../components/editor-page/autocomplete";
import buildSRSHtml from "../components/editor-page/buildSrsHelper";
import { initContextMenu } from "../components/editor-page/copyToLLM";
import IeeeTitlePage from "../components/editor-page/documentTitlePage";

import { BsDownload } from "react-icons/bs";
import { IoIosSave } from "react-icons/io";
import { FaRegFileAlt } from "react-icons/fa";
import { FiEdit3 } from "react-icons/fi";
import { TbZoom } from "react-icons/tb";
import { MdFormatBold } from "react-icons/md";
import { FaItalic } from "react-icons/fa6";
import { FiUnderline } from "react-icons/fi";
import { BsTypeStrikethrough } from "react-icons/bs";
import { GrTextAlignLeft } from "react-icons/gr";
import { GrTextAlignRight } from "react-icons/gr";
import { GrTextAlignCenter } from "react-icons/gr";
import { MdFormatAlignJustify } from "react-icons/md";
import { MdFormatListBulleted } from "react-icons/md";
import { ImListNumbered } from "react-icons/im";
import { BsListNested } from "react-icons/bs";
import { IoChevronBackOutline } from "react-icons/io5";

// to save srs content to backend when user clicks save button in file menu or title bar
async function saveSRS(editor, projectId) {
  const html = editor.getHTML();
  await authFetch(`/api/projects/${projectId}/srs/html`, {
    method: "POST",
    body: JSON.stringify({ html }),
  });
}
// // font size extention for tiptap with pt unit and parsing from html
const FontSize = Extension.create({
  name: "fontSize",

  addOptions() {
    return {
      types: ["textStyle"],
    };
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (element) => element.style.fontSize.replace("pt", ""),
            renderHTML: (attributes) => {
              if (!attributes.fontSize) {
                return {};
              }
              return {
                style: `font-size: ${attributes.fontSize}pt`,
              };
            },
          },
        },
      },
    ];
  },

  addCommands() {
    return {
      setFontSize:
        (fontSize) =>
        ({ chain }) => {
          return chain().setMark("textStyle", { fontSize }).run();
        },
      unsetFontSize:
        () =>
        ({ chain }) => {
          return chain()
            .setMark("textStyle", { fontSize: null })
            .removeEmptyTextStyle()
            .run();
        },
    };
  },
});
//  hook for each menu dynamically to detect clicks outside and close the menu
function useClickOutside(ref, callback) {
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        callback();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [ref, callback]);
}

export default function EditorPage() {
  const { projectId } = useParams();
  const [fontFamily, setFontFamily] = useState("Arial");
  const [fontSize, setFontSize] = useState("10");
  const [zoom, setZoom] = useState(100);
  const [showFileMenu, setShowFileMenu] = useState(false);
  const [showEditMenu, setShowEditMenu] = useState(false);
  const [showViewMenu, setShowViewMenu] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const [charCount, setCharCount] = useState(0);
  const [pageCount, setPageCount] = useState(1);
  const [editorState, setEditorState] = useState(0); // Force re-render
  const fileMenuRef = useRef(null);
  const editMenuRef = useRef(null);
  const viewMenuRef = useRef(null);
  const [srsData, setSrsData] = useState(null);
  const [chatInput, setChatInput] = useState("");
  const [chatOpen, setChatOpen] = useState(false);

  const [editorReady, setEditorReady] = useState(false);

  const [titlePageData, setTitlePageData] = useState(null);

  const navigate = useNavigate();

  


  // Use hook for each menu dynamically
  useClickOutside(fileMenuRef, () => setShowFileMenu(false));
  useClickOutside(editMenuRef, () => setShowEditMenu(false));
  useClickOutside(viewMenuRef, () => setShowViewMenu(false));

  const PAGE_HEIGHT = 1056; // A4 page height in px
  const PAGE_WIDTH = 816; // A4 page width in px
  const PAGE_MARGIN = 55; // 1-inch margins (96px)

  // for autocomplete
  let typingTimer = useRef(null);
  const delay = 2000;

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3, 4, 5, 6] },
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      Underline,
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      Highlight.configure({ multicolor: true }),
      Color,
      TextStyle,
      FontFamily.configure({
        types: ["textStyle"],
      }),
      FontSize,
      // Add autocomplete plugin extention
      Extension.create({
        addProseMirrorPlugins() {
          return [autocompletePlugin()];
        },
      }),
    ],
    onUpdate: ({ editor }) => {
      updateCounts(editor);
      calculatePages();
      setEditorState((prev) => prev + 1);

      if (typingTimer.current) clearTimeout(typingTimer.current);
      // set new timer
      typingTimer.current = setTimeout(() => {
        triggerAutocomplete(editor); // this fires only if user stops typing for 2 seconds
      }, delay);

      // Optional: update word/char counts or other things
      updateCounts(editor);
    },
    onSelectionUpdate: () => {
      setEditorState((prev) => prev + 1);
    },
    onCreate({ editor }) {
      initContextMenu(editor, setChatInput, setChatOpen);
    },
  });

  useEffect(() => {
    if (editor) {
      updateCounts(editor);
      calculatePages();
    }
  }, [editor]);

  editor.view.dom.addEventListener("keydown", (event) => {
    handleAutocompleteKeydown(event, editor);
  });

  // updare editor content when srsData changes based on user template
  useEffect(() => {
    if (!editor) return;

    const interval = 2000;
    let timer = null;
    let cancelled = false;

    const fetchSRS = async () => {
      try {
        const res = await authFetch(`/api/projects/${projectId}/srs`);

        if (res.status === 404) {
          // SRS not ready yet — keep polling indefinitely
          if (!cancelled) timer = setTimeout(fetchSRS, interval);
          return;
        }

        if (!res.ok) throw new Error("Failed to fetch SRS");

        const data = await res.json();
        // Fetch template for font/style settings
        let template = null;
        try {
          const tRes = await authFetch(
            `/api/templates/forProject/${projectId}`,
          );
          if (tRes.ok) template = await tRes.json();
        } catch (e) {
          console.log("No template found, using default styles");
        }

        try {
          const tpRes = await authFetch(
            `/api/titlePage/${projectId}`,
          );
          if (tpRes.ok) {
            const tpData = await tpRes.json();
            setTitlePageData(tpData);
          }
        } catch (e) {
          console.log("Could not fetch title page data");
        }

        let html = "";
        if (data.mode === "html") {
          html = data.html;
        } else {
          html = buildSRSHtml(data.srs_json, template);
        }

        editor.commands.setContent(html, false);
        setEditorReady(true);
        console.log("SRS content loaded into editor");
      } catch (err) {
        console.error("Failed to fetch SRS:", err);
        // On network error, keep retrying
        if (!cancelled) timer = setTimeout(fetchSRS, interval);
      }
    };

    fetchSRS();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [editor, projectId]);

  // counts helper function to update word and character counts

  const updateCounts = (editorInstance) => {
    const text = editorInstance.getText();
    setCharCount(text.length);
    const words = text
      .trim()
      .split(/\s+/)
      .filter((w) => w.length > 0);
    setWordCount(words.length);
  }; // helper function to calculate how many pages we need based on content height and update pageCount state
  const calculatePages = () => {
    const editorElement = document.querySelector(
      ".document-editor .ProseMirror",
    );
    if (editorElement) {
      // Get actual content height
      const contentHeight = editorElement.scrollHeight;

      // Calculate how many fixed pages we need
      const pageContentHeight = PAGE_HEIGHT - 2 * PAGE_MARGIN; // Area for text
      const pagesNeeded = Math.max(
        1,
        Math.ceil(contentHeight / pageContentHeight),
      );

      setPageCount(pagesNeeded);
    }
  };

  // helper function for file menu "New" button to clear editor content with confirmation
  const newFile = () => {
    if (
      editor &&
      confirm(
        "Are you sure you want to create a new document? Any unsaved changes will be lost.",
      )
    ) {
      editor.commands.setContent("<p></p>", false);
      setShowFileMenu(false);
    }
  };
  // helper function for file menu "Save" button to save content to backend
  const saveDocument = () => {
    saveSRS(editor, projectId);
    setShowFileMenu(false);
  };

  // helper function for file menu "Download" button to download current content as pdf file
const downloadDocument = () => {
  if (!editor) return;
  setShowFileMenu(false);

  const titlePageEl = document.querySelector(".title-page-wrapper");
  const titlePageHtml = titlePageEl ? titlePageEl.outerHTML : "";

  const styles = Array.from(document.styleSheets)
    .map((sheet) => {
      try {
        return Array.from(sheet.cssRules)
          .map((rule) => rule.cssText)
          .join("\n");
      } catch (e) {
        return "";
      }
    })
    .join("\n");

  const iframe = document.createElement("iframe");
  iframe.style.display = "none";
  document.body.appendChild(iframe);

  const content = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>SRS Document</title>

      <style>
        ${styles}

        /* =========================
           PRINT FIXES
        ========================== */

        * {
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }

        /* ================= TABLE FIX ================= */
        table {
          width: 100% !important;
          border-collapse: collapse !important;
          table-layout: fixed !important;
        }

        th, td {
          border: 1px solid #ccc !important;
          padding: 3px !important;
          vertical-align: top !important;
          word-wrap: break-word !important;
          overflow-wrap: break-word !important;
        }

        th {
          background: #f0f0f0 !important;
        }

        tr {
          page-break-inside: avoid !important;
        }

        /* ================= LIST FIX ================= */
        ol {
          list-style-type: decimal !important;
          margin-left: 20px;
        }

        ol ol {
          margin-left: 20px;
        }

        ul {
          list-style-type: disc !important;
          margin-left: 20px;
        }

        li {
          margin-bottom: 4px;
        }

        /* ================= HIGHLIGHT FIX ================= */
        mark {
          background-color: exact !important;
          -webkit-print-color-adjust: exact;
          print-color-adjust: exact;
        }

        /* ================= TITLE PAGE ================= */
        .title-page-wrapper {
          width: 100% !important;
          height: 100vh !important;
          margin: 0 !important;
          padding: 52pt !important;
          box-sizing: border-box !important;
          page-break-after: always !important;
        }

        /* ================= BODY ================= */
        .srs-content {
          padding: 25pt !important;
        }

        /* ================= HIDE EDITOR UI ================= */
        .simulated-pages-div,
        .simulated-page,
        .simulated-page-background,
        .page-number-badge,
        .editor-page-container,
        .menu-bar-container,
        .toolbar-container,
        .status-bar-container,
        .title-page-editable:empty::before {
          display: none !important;
        }

        body {
          margin: 0 !important;
          padding: 0 !important;
          background: white !important;
        }

        @page {
          size: A4;
          margin-top: 22pt;
        }
      </style>
    </head>

    <body>
      ${titlePageHtml}
      <div class="srs-content">
        ${editor.getHTML()}
      </div>
    </body>
    </html>
  `;

  iframe.contentDocument.open();
  iframe.contentDocument.write(content);
  iframe.contentDocument.close();

  iframe.onload = () => {
    iframe.contentWindow.print();
    setTimeout(() => document.body.removeChild(iframe), 1000);
  };
};

  const handleFontSize = (size) => {
    setFontSize(size);
    if (!editor) return;
    editor.chain().focus().setFontSize(size).run();
  };

  const handleFontFamily = (family) => {
    setFontFamily(family);
    if (!editor) return;
    editor.chain().focus().setFontFamily(family).run();
  };

  const setHighlight = (color) => {
    if (!editor) return;
    editor.chain().focus().setHighlight({ color }).run();
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(50, prev - 10));
    setShowViewMenu(false);
  };

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(200, prev + 10));
    setShowViewMenu(false);
  };

  const handleResetZoom = () => {
    setZoom(100);
    setShowViewMenu(false);
  };

  if (!editor) {
    return <div>Loading editor...</div>;
  }

  return (
    <div className="editor-page-container">
      {/* Menu Bar */}
      <div className="menu-bar-container">
        <button className="back-btn-editor" onClick={() => navigate(-1)}>
          {" "}
          <IoChevronBackOutline /> Back
        </button>

        <div className="menu-bar-left-parent-div" ref={fileMenuRef}>
          <button
            className="left-menu-btn"
            onClick={() => {
              setShowFileMenu(!showFileMenu);
              setShowEditMenu(false);
              setShowViewMenu(false);
            }}
          >
            <FaRegFileAlt /> File
          </button>
          {showFileMenu && (
            <div className="parent-menu-btns">
              <button className="child-menu-btn" onClick={newFile}>
                New
              </button>
              <button className="child-menu-btn" onClick={saveDocument}>
                Save
              </button>
              <button className="child-menu-btn" onClick={downloadDocument}>
                Download
              </button>
            </div>
          )}
        </div>
        <div className="menu-bar-left-parent-div" ref={editMenuRef}>
          <button
            className="left-menu-btn"
            onClick={() => {
              setShowEditMenu(!showEditMenu);
              setShowFileMenu(false);
              setShowViewMenu(false);
            }}
          >
            <FiEdit3 /> Edit
          </button>
          {showEditMenu && (
            <div className="parent-menu-btns">
              <button
                className="child-menu-btn"
                onClick={() => {
                  editor.chain().focus().undo().run();
                  setShowEditMenu(false);
                }}
              >
                Undo
              </button>
              <button
                className="child-menu-btn"
                onClick={() => {
                  editor.chain().focus().redo().run();
                  setShowEditMenu(false);
                }}
              >
                Redo
              </button>
              <button
                className="child-menu-btn"
                onClick={() => {
                  editor.chain().focus().selectAll().run();
                  setShowEditMenu(false);
                }}
              >
                Select All
              </button>
            </div>
          )}
        </div>
        <div className="menu-bar-left-parent-div" ref={viewMenuRef}>
          <button
            className="left-menu-btn"
            onClick={() => {
              setShowViewMenu(!showViewMenu);
              setShowFileMenu(false);
              setShowEditMenu(false);
            }}
          >
            <TbZoom /> View
          </button>
          {showViewMenu && (
            <div className="parent-menu-btns">
              <button className="child-menu-btn" onClick={handleZoomOut}>
                Zoom Out
              </button>
              <button className="child-menu-btn" onClick={handleResetZoom}>
                Reset Zoom
              </button>
              <button className="child-menu-btn" onClick={handleZoomIn}>
                Zoom In
              </button>
            </div>
          )}
        </div>
        <div className="title-bar-div">
          <div
            className="title-box"
            contentEditable
            suppressContentEditableWarning
            spellCheck={false}
            onInput={(e) => {
              console.log("Title:", e.currentTarget.innerText);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.preventDefault();
            }}
            onBlur={(e) => {
              if (e.currentTarget.innerText.trim() === "") {
                e.currentTarget.innerText = "Untitled Document";
              }
            }}
          >
            Untitled Document
          </div>

          <div className="title-box-btn-container">
            <button className="title-box-btn" onClick={saveDocument}>
              <IoIosSave /> Save
            </button>
            <button className="title-box-btn" onClick={downloadDocument}>
              <BsDownload /> Download
            </button>
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="toolbar-container">
        {/* Undo/Redo */}
        <div className="undo-redo-div">
          <button
            className="undo-btn"
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            style={{
              opacity: editor.can().undo() ? 1 : 0.5,
            }}
            title="Undo"
          >
            ↶
          </button>
          <button
            className="undo-btn"
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            style={{
              opacity: editor.can().redo() ? 1 : 0.5,
            }}
            title="Redo"
          >
            ↷
          </button>
        </div>

        {/* Font Controls */}
        <div className="font-control-div">
          <select
            className="font-family-control font-control"
            value={fontFamily}
            onChange={(e) => handleFontFamily(e.target.value)}
            style={{ fontFamily }}
          >
            <option value="Arial" style={{ fontFamily: "Arial" }}>
              Arial
            </option>
            <option value="Segoe UI" style={{ fontFamily: "Segoe UI" }}>
              Segoe UI
            </option>
            <option
              value="Times New Roman"
              style={{ fontFamily: "Times New Roman" }}
            >
              Times New Roman
            </option>
            <option value="Courier New" style={{ fontFamily: "Courier New" }}>
              Courier New
            </option>
            <option value="Georgia" style={{ fontFamily: "Georgia" }}>
              Georgia
            </option>
            <option value="Verdana" style={{ fontFamily: "Verdana" }}>
              Verdana
            </option>
          </select>

          <select
            className="font-size-control font-control"
            value={fontSize}
            onChange={(e) => handleFontSize(e.target.value)}
          >
            {[8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72].map(
              (s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ),
            )}
          </select>
        </div>

        {/* Text Formatting */}
        <div className="text-format-parent-div">
          <button
            className="text-format-child-btn"
            onClick={() => editor.chain().focus().toggleBold().run()}
            style={{
              backgroundColor: editor.isActive("bold")
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Bold"
          >
            <MdFormatBold className="icon-sizes" />
          </button>
          <button
            className="text-format-child-btn"
            onClick={() => editor.chain().focus().toggleItalic().run()}
            style={{
              backgroundColor: editor.isActive("italic")
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Italic"
          >
            <FaItalic />
          </button>
          <button
            className="text-format-child-btn"
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            style={{
              backgroundColor: editor.isActive("underline")
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Underline"
          >
            <FiUnderline className="icon-sizes" />
          </button>
          <button
            className="text-format-child-btn"
            onClick={() => editor.chain().focus().toggleStrike().run()}
            style={{
              backgroundColor: editor.isActive("strike")
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Strikethrough"
          >
            <BsTypeStrikethrough className="icon-sizes" />
          </button>
        </div>

        {/* Colors */}
        <div className="colors-parent-div">
          <input
            className="colors-child-btn"
            type="color"
            onChange={(e) =>
              editor.chain().focus().setColor(e.target.value).run()
            }
            title="Text Color"
          />

          <input
            className="colors-child-btn"
            type="color"
            onChange={(e) => setHighlight(e.target.value)}
            title="Highlight Color"
          />
          <button
            className="colors-child-btn"
            onClick={() => editor.chain().focus().unsetHighlight().run()}
            title="Remove Highlight"
          >
            ✖
          </button>
        </div>

        {/* Alignment */}
        <div className="alignment-parent-div">
          <button
            className="alignment-child-btn"
            onClick={() => editor.chain().focus().setTextAlign("left").run()}
            style={{
              backgroundColor: editor.isActive({ textAlign: "left" })
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Align Left"
          >
            <GrTextAlignLeft />
          </button>
          <button
            className="alignment-child-btn"
            onClick={() => editor.chain().focus().setTextAlign("center").run()}
            style={{
              backgroundColor: editor.isActive({ textAlign: "center" })
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Align Center"
          >
            <GrTextAlignCenter />
          </button>
          <button
            className="alignment-child-btn"
            onClick={() => editor.chain().focus().setTextAlign("right").run()}
            style={{
              backgroundColor: editor.isActive({ textAlign: "right" })
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Align Right"
          >
            <GrTextAlignRight />
          </button>
          <button
            className="alignment-child-btn"
            onClick={() => editor.chain().focus().setTextAlign("justify").run()}
            style={{
              backgroundColor: editor.isActive({ textAlign: "justify" })
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Justify"
          >
            <MdFormatAlignJustify />
          </button>
        </div>

        {/* Lists */}
        <div className="list-parent-div">
          <button
            className="list-chid-btn"
            onClick={() => {
              if (editor.isActive("orderedList")) {
                editor.chain().focus().liftListItem("listItem").run();
                editor.chain().focus().toggleBulletList().run();
              } else {
                editor.chain().focus().toggleBulletList().run();
              }
            }}
            style={{
              backgroundColor: editor.isActive("bulletList")
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Bullet List"
          >
            <MdFormatListBulleted style={{ height: "26px", width: "20px" }} />
          </button>
          <button
            className="list-chid-btn"
            onClick={() => {
              if (editor.isActive("bulletList")) {
                editor.chain().focus().liftListItem("listItem").run();
                editor.chain().focus().toggleOrderedList().run();
              } else {
                editor.chain().focus().toggleOrderedList().run();
              }
            }}
            style={{
              backgroundColor: editor.isActive("orderedList")
                ? "rgb(247, 247, 250)"
                : "transparent",
            }}
            title="Numbered List"
          >
            <ImListNumbered />
          </button>
          <button
            className="list-chid-btn"
            onClick={() => {
              if (!editor) return;

              if (!editor.isActive("orderedList")) {
                editor.chain().focus().toggleOrderedList().run();
              } else {
                // Only sink if already a list item
                if (editor.isActive("listItem")) {
                  editor.chain().focus().sinkListItem("listItem").run();
                } else {
                  // If not inside a list item, create one first
                  editor.chain().focus().toggleOrderedList().run();
                  editor.chain().focus().sinkListItem("listItem").run();
                }
              }
            }}
            title="Nested Numbered List"
          >
            <BsListNested />
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="zoom-parent-div">
          <button className="undo-btn" onClick={handleZoomOut} title="Zoom Out">
            −
          </button>
          <span className="zoom-child-div">{zoom}%</span>
          <button className="undo-btn" onClick={handleZoomIn} title="Zoom In">
            +
          </button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="editor-area-container">
        <div
          style={{
             height: `${(pageCount * PAGE_HEIGHT)}px`,
    width: `${PAGE_WIDTH}px`,
    transform: `scale(${zoom / 100})`,
    transformOrigin: "top left",
    marginTop: "40px",
          }}
        >
          {/* This is the single container with simulated pages */}
          <div
            className="simulated-pages-div"
            style={{
              height: `${pageCount * PAGE_HEIGHT+PAGE_HEIGHT}px`,
              transform: `scale(${zoom / 100})`,
              transformOrigin: "top center",
            }}
          >
            {/* Visual representation of page margins */}
            <div
              className="simulated-page"
              style={{
                top: `${PAGE_MARGIN}px`,
                bottom: `${PAGE_MARGIN}px`,
                left: `${PAGE_MARGIN}px`,
                right: `${PAGE_MARGIN}px`,
              }}
            />

            {/* Simulated page backgrounds with repeating pattern */}
            <div
              className="simulated-page-background"
              style={{
                backgroundImage: `
    repeating-linear-gradient(
      to bottom,
      transparent,
      transparent ${PAGE_HEIGHT - 3.5}px,
      rgba(0, 0, 0, 0.05) ${PAGE_HEIGHT - 3.5}px,
      rgba(0, 0, 0, 0.05) ${PAGE_HEIGHT}px
    )
  `,
              }}
            />
            {editorReady && (
                <div
    style={{
      position: "absolute",
      top: 0,
      left: 0,
      width: `${PAGE_WIDTH}px`,
      height: `${PAGE_HEIGHT}px`,
      zIndex: 10,           // ✅ above ProseMirror (z-index: 2)
      background: "white",
    }}
    onMouseDown={(e) => e.stopPropagation()} // ✅ block ProseMirror from stealing clicks
  >
    
            <IeeeTitlePage
              projectId={projectId}
              titlePageData={titlePageData}
              pageHeight={PAGE_HEIGHT}
              pageMargin={PAGE_MARGIN}
              pageWidth={PAGE_WIDTH}
            />
              </div>

            )}

            {/* Actual editor content (pg2) */}
            <EditorContent
              editor={editor}
              className="document-editor editor-content-over-pages"
              style={{
                width: `${PAGE_WIDTH - 2 * PAGE_MARGIN}px`,
                minHeight: `${PAGE_HEIGHT - 2 * PAGE_MARGIN}px`,
                height: "auto",
                margin: `${PAGE_MARGIN}px`,
                marginTop: `${PAGE_MARGIN + PAGE_HEIGHT}px`, // extra space for title page
              }}
            />

            {/* Page number indicators */}
            {Array.from({ length: pageCount }).map((_, index) => (
              <div
                className="page-number-badge"
                key={index}
                style={{
                  bottom: `${PAGE_MARGIN / 2}px`,
                  right: `${PAGE_MARGIN - 50}px`,
                  top: `${
                    index * PAGE_HEIGHT + (PAGE_HEIGHT - PAGE_MARGIN / 2)
                  }px`,
                }}
              >
                {index + 1}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div className="status-bar-container">
        <div className="status-bar">
          <span>
            Page {pageCount} of {pageCount}
          </span>
          <span>{wordCount} words</span>
          <span>{charCount} characters</span>
        </div>
        <div className="status-bar">
          <span>English (US)</span>
        </div>
      </div>

      {/* chatbot */}
      <ChatbotPopup
        input={chatInput}
        setInput={setChatInput}
        open={chatOpen}
        setOpen={setChatOpen}
      />
      {/* Custom Context Menu for "Send to LLM" */}
      <div id="customMenu">
        <div id="sendToLLM">Send to LLM</div>
      </div>

      {/* Loading Indicator */}
      {!editorReady && (
        <div className="editor-loading">
          ⏳ Generating SRS document, please wait...
        </div>
      )}
    </div>
  );
}