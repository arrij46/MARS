import { useState, useEffect, useCallback } from "react";
import { FaPaperclip, FaXmark } from "react-icons/fa6";
import "../../style/elicitation.css";

export default function Popup({ onFileSelect }) {
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  useEffect(() => {
    const savedPreference = localStorage.getItem("dontShowPopup");
    if (savedPreference === "true") setDontShowAgain(true);
  }, []);

  const openPopup = useCallback(() => {
    if (dontShowAgain) openFileManager();
    else setIsPopupOpen(true);
  }, [dontShowAgain]);

  const closePopup = useCallback(() => setIsPopupOpen(false), []);

  const handleCheckboxChange = useCallback((e) => {
    const isChecked = e.target.checked;
    setDontShowAgain(isChecked);
    localStorage.setItem("dontShowPopup", isChecked.toString());
  }, []);

  const openFileManager = useCallback(() => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".pdf,.doc,.docx,.txt";
    fileInput.onchange = (event) => {
      const file = event.target.files[0];
      if (file) {
        console.log("Selected file:", file);
        if (onFileSelect) onFileSelect(file); // 🔥 send file to parent
      }
    };
    fileInput.click();
  }, [onFileSelect]);

  const handleSubmit = useCallback(() => {
    closePopup();
    openFileManager();
  }, [closePopup, openFileManager]);

  return (
    <div className="requirements-container">
      <button
        className="requirements-trigger-btn"
        onClick={openPopup}
        aria-label="Open requirements assistant"
      >
        <FaPaperclip className="requirement-popup-icon" />
      </button>

      {isPopupOpen && (
        <div
          className="requirements-popup-overlay"
          onClick={(e) => e.target === e.currentTarget && closePopup()}
        >
          <div className="requirements-popup-content">
            <div className="popup-header">
              <h2>Document Format</h2>
              <button className="popup-close-btn" onClick={closePopup}>
                <FaXmark />
              </button>
            </div>

            <div className="popup-body">
              <p>The uploaded document can be in the following format:</p>
              <ul>
                <li>PDF</li>
                <li>DOC / DOCX</li>
                <li>TXT</li>
              </ul>

              <div className="popup-checkbox-div">
                <input
                  type="checkbox"
                  checked={dontShowAgain}
                  onChange={handleCheckboxChange}
                />
                <label>Don't show this again</label>
              </div>

              <div className="popup-actions">
                <button className="upload-btn" onClick={handleSubmit}>
                  Choose File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}



// import { useState, useEffect, useCallback } from "react";
// import { FaCog, FaTimes } from "react-icons/fa";
// import { FaPaperclip } from "react-icons/fa6";

// import "../../style/elicitation.css";

// export default function Popup() {
//   const [isPopupOpen, setIsPopupOpen] = useState(false);
//   const [dontShowAgain, setDontShowAgain] = useState(false);

//   // Check localStorage on component mount
//   useEffect(() => {
//     const savedPreference = localStorage.getItem('dontShowPopup');
//     if (savedPreference === 'true') {
//       setDontShowAgain(true);
//     }
//   }, []);

//   const openPopup = useCallback(() => {
//     if (dontShowAgain) {
//       // If checkbox is checked, directly open file manager
// //      openFileManager();
//       setIsPopupOpen(true);
  
// } else {
//       // Otherwise show the popup
//       setIsPopupOpen(true);
//     }
//   }, [dontShowAgain]);

//   const closePopup = useCallback(() => setIsPopupOpen(false), []);

//   const handleCheckboxChange = useCallback((event) => {
//     const isChecked = event.target.checked;
//     setDontShowAgain(isChecked);
//     // Save preference to localStorage
//     localStorage.setItem('dontShowPopup', isChecked.toString());
//   }, []);

//   const openFileManager = useCallback(() => {
//     // Create a file input element to open file dialog
//     const fileInput = document.createElement('input');
//     fileInput.type = 'file';
//     fileInput.accept = '.pdf,.doc,.docx,.txt';
//     fileInput.multiple = false; // Set to true if you want multiple files
    
//     // Handle file selection
//     fileInput.onchange = (event) => {
//       const file = event.target.files[0];
//       if (file) {
//         console.log('Selected file:', file);
//         // Handle the file upload here
//         // You can add your file upload logic
//         alert(`File selected: ${file.name}`);
//       }
//     };
    
//     // Trigger file dialog
//     fileInput.click();
//   }, []);

//   const handleSubmit = useCallback(() => {
//     closePopup();
//     // Open file manager after closing popup
//     openFileManager();
//   }, [closePopup, openFileManager]);

//   // Handle ESC key and body scroll
//   useEffect(() => {
//     const handleEscape = (event) => {
//       if (event.keyCode === 27) closePopup();
//     };

//     if (isPopupOpen) {
//       document.addEventListener("keydown", handleEscape);
//       document.body.style.overflow = "hidden";
//     }

//     return () => {
//       document.removeEventListener("keydown", handleEscape);
//       document.body.style.overflow = "unset";
//     };
//   }, [isPopupOpen, closePopup]);

//   const handleBackdropClick = useCallback(
//     (event) => {
//       if (event.target === event.currentTarget) {
//         closePopup();
//       }
//     },
//     [closePopup]
//   );

//   return (
//     <div className="requirements-container">
//       {/* Your existing content */}
//       <button
//         className="requirements-trigger-btn"
//         onClick={openPopup}
//         aria-label="Open requirements assistant"
//       >
//         <FaPaperclip className="requirement-popup-icon" />
//       </button>
//       {/* Popup Modal - Only show if not skipped */}
//       {
//       isPopupOpen && (
//         <div
//           className="requirements-popup-overlay"
//           onClick={handleBackdropClick}
//           role="dialog"
//           aria-modal="true"
//           aria-labelledby="popup-title"
//         >
//           <div className="requirements-popup-content">
//             {/* Header */}
//             <div className="popup-header">
//               <h2 id="popup-title">Document Format</h2>
//               <button
//                 className="popup-close-btn"
//                 onClick={closePopup}
//                 aria-label="Close requirements assistant"
//               >
//                 <FaTimes />
//               </button>
//             </div>

//             {/* Body Content */}
//             <div className="popup-body">
//               <p>
//                 The uploaded document can be in the following format:
//               </p>
//                <ul>
//                   <li>PDF</li>
//                   <li>Word Document (DOC, DOCX)</li>
//                   <li>Text File (TXT)</li>
//                 </ul>
//               <p>
//                 Please ensure that the document contains a numbered
//                 list of requirements and no paragraph/headings.
//               </p>
              
//               <div className="popup-checkbox-div">
//                 <input 
//                   type="checkbox" 
//                   name="popup-checkbox" 
//                   id="popup-checkbox" 
//                   className="pop-checkbox"
//                   checked={dontShowAgain}
//                   onChange={handleCheckboxChange}
//                 />
//                 <label htmlFor="popup-checkbox">Don't show this again</label>
//               </div>

//               {/* Add a button to proceed to file upload */}
//               <div className="popup-actions">
//                 <button 
//                   className="upload-btn"
//                   onClick={handleSubmit}
//                 >
//                   Choose File
//                 </button>
//               </div>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }