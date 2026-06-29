import React, { useState } from "react";
import { authFetch } from "../../utils/api";
import "../../style/refinedRequirementsList.css";


// // Editable Requirement list component
//  function RequirementCard({ items, onUpdate }) {
//   const [editingIndex, setEditingIndex] = useState(null);
//   const [editingValue, setEditingValue] = useState("");

//   const handleEdit = (index) => {
//     setEditingIndex(index);
//     setEditingValue(items[index]);
//   };
// const handleSave = async () => {
//   const updatedItems = [...items];
//   updatedItems[editingIndex] = editingValue;

//   // Call the backend API
//   try {
//     const res = await authFetch("/api/update_requirement", {
//       method: "POST",
//       body: JSON.stringify({
//         index: editingIndex,
//         newText: editingValue,
//       }),
//     });

//     if (!res.ok) throw new Error("Failed to update requirement");

//     onUpdate(updatedItems); // update UI after backend confirms
//   } catch (err) {
//     console.error(err);
//     alert("Error updating requirement");
//   }

//   setEditingIndex(null);
// };


//   const handleCancel = () => setEditingIndex(null);

//   return (
//     <div className="nfr-box">
//       {items.map((req, index) => (
//         <div key={index} className="req-card small d-flex align-items-center">
//           {editingIndex === index ? (
//             <>
//               <input
//                 type="text"
//                 className="form-control form-control-sm me-3"
//                 value={editingValue}
//                 onChange={(e) => setEditingValue(e.target.value)}
//               />
//               <button className="btn btn-sm btn-success me-1" onClick={handleSave}>
//                 Save
//               </button>
//               <button className="btn btn-sm btn-secondary" onClick={handleCancel}>
//                 Cancel
//               </button>
//             </>
//           ) : (
//             <>
//               <span className="flex-grow-1">{req}</span>
//               <img
//                 className="pencil-icon ms-2"
//                 src="/assets/icons/pencil-black.svg"
//                 alt="Edit"
//                 style={{visibility:"hidden"}}
//                 onClick={() => handleEdit(index)}
//               />
//             </>
//           )}
//         </div>
//       ))}
//     </div>
//   );
// }

// // NFR Section component
//  function NFRSection({ title, items, setItems }) {
//     const [nfrOpen, setNfrOpen] = useState(true);

//   return (
//     <div>
//       <h5 className="fw-semibold mb-2 mt-3 d-flex align-items-cente nfr-container"   
//        onClick={() => setNfrOpen(!nfrOpen)}>
//         {title}
//         <div className="count-container">
//  <span className="count-circle ms-auto">{items.length}</span>
//             <span className="toggle-icon">{nfrOpen ? '▼' : '▶'}</span>
//         </div>
       
//       </h5>
//       {nfrOpen && <RequirementCard items={items} onUpdate={setItems} />}
//     </div>
//   );
// }

// export {RequirementCard, NFRSection};

// // import React from "react";
// // import "../../style/RefinedRequirementsList.css";
// // import React, { useState } from "react";
 

// // export default function RequirementCard({ items, onUpdate }) {
// //   const [editingIndex, setEditingIndex] = useState(null);
// //   const [editingValue, setEditingValue] = useState("");

// //   const handleEdit = (index) => {
// //     setEditingIndex(index);
// //     setEditingValue(items[index]);
// //   };

// //   const handleSave = () => {
// //     const updatedItems = [...items];
// //     updatedItems[editingIndex] = editingValue;
// //     onUpdate(updatedItems);
// //     setEditingIndex(null);
// //   };

// //   const handleCancel = () => {
// //     setEditingIndex(null);
// //   };

// //   return (
// //     <div className="nfr-box">
// //       {items.map((req, index) => (
// //         <div key={index} className="req-card small d-flex align-items-center">
// //           {editingIndex === index ? (
// //             <>
// //               <input
// //                 type="text"
// //                 className="form-control form-control-sm me-2"
// //                 value={editingValue}
// //                 onChange={(e) => setEditingValue(e.target.value)}
// //               />
// //               <button
// //                 className="btn btn-sm btn-success me-1"
// //                 onClick={handleSave}
// //               >
// //                 Save
// //               </button>
// //               <button
// //                 className="btn btn-sm btn-secondary"
// //                 onClick={handleCancel}
// //               >
// //                 Cancel
// //               </button>
// //             </>
// //           ) : (
// //             <>
// //               <span className="flex-grow-1">{req}</span>
// //               <img
// //                 className="pencil-icon ms-2"
// //                 src="/assets/icons/pencil-black.svg"
// //                 alt="Edit"
// //                 style={{ cursor: "pointer", width: "16px", height: "16px" }}
// //                 onClick={() => handleEdit(index)}
// //               />
// //             </>
// //           )}
// //         </div>
// //       ))}
// //     </div>
// //   );
// // }

// // export default function NFRSection({ title, items: initialItems }) {
// //   // Maintain local state for this section
// //   const [items, setItems] = useState(initialItems);

// //   return (
// //     <div>
// //       <h5 className="fw-semibold mb-2 mt-3 d-flex align-items-center">
// //         {title}
// //         <span className="count-circle ms-auto">{items.length}</span>
// //       </h5>

// //       {/* Pass onUpdate to RequirementCard */}
// //       <RequirementCard items={items} onUpdate={setItems} />
// //     </div>
// //   );
// // }

// // function RequirementCard({ items }) {
// //   return (
// //     <div className="nfr-box">
// //       {items.map((req, index) => (
// //         <div key={index} className="req-card small">
// //           {req}  <img className="pencil-icon" src="../../assets/icons/pencil-black.svg" onClick={editRequirement()}/>
// //         </div>
// //       ))}
// //     </div>
// //   );
// // }


// //  function NFRSection({ title, items }) {
// //   return (
// //     <div>
// //       <h5 className="fw-semibold mb-2 mt-3">
// //         {title}
// //         <span className="count-circle ms-auto">{items.length}</span>
// //       </h5>

// //       <RequirementCard items={items} />
// //     </div>
// //   );
// // }


export function RequirementCard({ items, onUpdate }) {
  const [editingIndex, setEditingIndex] = useState(null);
  const [editingValue, setEditingValue] = useState("");

  const handleEdit = (index) => {
    setEditingIndex(index);
    setEditingValue(items[index]);
  };

  const handleSave = async () => {
    const updatedItems = [...items];
    updatedItems[editingIndex] = editingValue;
    try {
      const res = await authFetch("/api/update_requirement", {
        method: "POST",
        body: JSON.stringify({ index: editingIndex, newText: editingValue }),
      });
      if (!res.ok) throw new Error("Failed to update requirement");
      onUpdate(updatedItems);
    } catch (err) {
      console.error(err);
      alert("Error updating requirement");
    }
    setEditingIndex(null);
  };

  const handleCancel = () => setEditingIndex(null);

    return (
    <div className="req-card-list">
      {items.map((req, index) => (
        <div key={index} className="req-card">
          <span className="req-index">#{String(index + 1).padStart(2, "0")}</span>
          <span className="req-text">{req}</span>
        </div>
      ))}
    </div>
  );
}

export function NFRSection({ title, items, setItems }) {
  const [open, setOpen] = useState(false);

 return (
    <div className="nfr-section">
      <div className="nfr-section-header" onClick={() => setOpen(!open)}>
        <span className="nfr-section-title">{title}</span>
        <div className="nfr-section-meta">
          <span className="count-pill">{items.length}</span>
          <span className="nfr-chevron">{open ? "▾" : "▸"}</span>
        </div>
      </div>
      {open && (
        <div className="nfr-section-body">
          <RequirementCard items={items} />
        </div>
      )}
    </div>
  );
}