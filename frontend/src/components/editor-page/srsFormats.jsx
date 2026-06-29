export const fontOptions = [
  "Inter",
  "Georgia",
  "Times New Roman",
  "Arial",
  "Roboto",
  "Merriweather",
  "Open Sans",
];
export const fontSizeOptions = [
  8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 48, 72,
];
export const defaultFontSizes = {
  Title: 32,
  "Heading 1": 24,
  "Heading 2": 20,
  "Heading 3": 18,
  "Heading 4": 16,
  "Heading 5": 14,
  "Heading 6": 12,
  Paragraph: 11,
};
export const fontSizeGrid = [
  ["Title", "Heading 1"],
  ["Heading 2", "Heading 3"],
  ["Heading 4", "Heading 5"],
  ["Heading 6", "Paragraph"],
];

export const srsTemplates = {
  
  "ISO/ICE/IEEE 29148": [
  {
    id: "29148-intro",
    heading: "1. Introduction",
    hasChildren: true,
    sub: [
      "1.1 Purpose",
      "1.2 Scope",
      "1.3 Product Perspective",
      "1.4 Product Functions",
      "1.5 User Characteristics",
      "1.6 Limitations",
      "1.7 Assumptions and Dependencies",
      "1.8 Definitions",
      "1.9 Acronyms and Abbreviations",
    ],
  },
  {
    id: "29148-reqs",
    heading: "2. Requirements",
    hasChildren: true,
    sub: [
      "2.1 External Interfaces",
      "2.2 Functions",
      "2.3 Usability Requirements",
      "2.4 Performance Requirements",
      "2.5 Logical Database Requirements",
      "2.6 Design Constraints",
      "2.7 Software System Attributes",
      "2.8 Supporting Information",
    ],
  },
  {
    id: "29148-verification",
    heading: "3. Verification (Structure only)",
    hasChildren: true,
    sub: [
      "3.1 Verification Approach",
      "3.2 Verification Methods",
      "3.3 Verification Criteria",
    ],
  },
  {
    id: "29148-appendices",
    heading: "4. Appendices",
    hasChildren: true,
    sub: [
      "4.1 Assumptions and Dependencies",
      "4.2 Acronyms and Abbreviations",
      "4.3 References",
    ],
  },
],
 "IEEE 830-1998": [
  {
    id: "ieee830-intro",
    heading: "1. Introduction",
    hasChildren: true,
    sub: [
      "1.1 Purpose",
      "1.2 Document Conventions",
      "1.3 Intended Audience and Reading Suggestions",
      "1.4 Project Scope",
      "1.5 References",
    ],
  },
  {
    id: "ieee830-overall",
    heading: "2. Overall Description",
    hasChildren: true,
    sub: [
      "2.1 Product Perspective",
      "2.2 Product Functions",
      "2.3 User Classes and Characteristics",
      "2.4 Operating Environment",
      "2.5 Design and Implementation Constraints",
      "2.6 User Documentation",
      "2.7 Assumptions and Dependencies",
    ],
  },
  {
    id: "ieee830-interfaces",
    heading: "3. External Interface Requirements",
    hasChildren: true,
    sub: [
      "3.1 User Interfaces",
      "3.2 Hardware Interfaces",
      "3.3 Software Interfaces",
      "3.4 Communications Interfaces",
    ],
  },
  {
    id: "ieee830-features",
    heading: "4. System Features",
    hasChildren: false,
    sub: [],
  },
  {
    id: "ieee830-nonfunctional",
    heading: "5. Other Nonfunctional Requirements",
    hasChildren: true,
    sub: [
      "5.1 Performance Requirements",
      "5.2 Safety Requirements",
      "5.3 Security Requirements",
      "5.4 Software Quality Attributes",
      "5.5 Business Rules",
    ],
  },
  {
    id: "ieee830-other",
    heading: "6. Other Requirements",
    hasChildren: false,
    sub: [],
  },
  {
    id: "ieee830-appendix-a",
    heading: "Appendix A: Glossary",
    hasChildren: false,
    sub: [],
  },
],
//   "IEEE 1233": [
//   {
//     id: "1233-intro",
//     heading: "1. Introduction",
//     hasChildren: true,
//     sub: [
//       "1.1 System Purpose",
//       "1.2 System Scope",
//       "1.3 System Overview",
//       "1.4 Definitions, Acronyms, Abbreviations",
//       "1.5 References",
//     ],
//   },
//   {
//     id: "1233-conops",
//     heading: "2. Operational Concept",
//     hasChildren: true,
//     sub: [
//       "2.1 Operational Concept Description",
//       "2.2 Mission Scenarios",
//       "2.3 Operational Environment",
//       "2.4 Support Environment",
//       "2.5 Operational Constraints",
//     ],
//   },
//   {
//     id: "1233-constraints",
//     heading: "3. System Constraints",
//     hasChildren: true,
//     sub: [
//       "3.1 Regulatory Constraints",
//       "3.2 Standards Compliance",
//       "3.3 Physical Constraints",
//       "3.4 Technology Constraints",
//     ],
//   },
//   {
//     id: "1233-capabilities",
//     heading: "4. System Capabilities",
//     hasChildren: true,
//     sub: [
//       "4.1 Required States and Modes",
//       "4.2 Capability Requirements",
//       "4.3 System Interfaces",
//       "4.4 Physical Characteristics",
//       "4.5 Environmental Conditions",
//     ],
//   },
//   {
//     id: "1233-qualitative",
//     heading: "5. System Quality Attributes",
//     hasChildren: true,
//     sub: [
//       "5.1 Reliability",
//       "5.2 Maintainability",
//       "5.3 Availability",
//       "5.4 Safety",
//       "5.5 Security",
//       "5.6 Portability",
//       "5.7 Usability",
//     ],
//   },
//   {
//     id: "1233-design",
//     heading: "6. Design and Construction Constraints",
//     hasChildren: true,
//     sub: [
//       "6.1 Design Standards",
//       "6.2 Construction Constraints",
//       "6.3 Personnel-Related Requirements",
//       "6.4 Training-Related Requirements",
//       "6.5 Logistics-Related Requirements",
//     ],
//   },
//   {
//     id: "1233-verification",
//     heading: "7. Verification(Structure only)",
//     hasChildren: true,
//     sub: [
//       "7.1 Verification Approach",
//       "7.2 Verification Constraints",
//     ],
//   },
//   {
//     id: "1233-scenarios",
//     heading: "8. System Documentation Requirements(Structure only)",
//     hasChildren: true,
//     sub: [
//       "8.1 User Documentation",
//       "8.2 Operator Documentation",
//       "8.3 Maintenance Documentation",
//     ],
//   },
//   {
//     id: "1233-appendix-a",
//     heading: "Appendix A: Glossary",
//     hasChildren: false,
//     sub: [],
//   },
//   {
//     id: "1233-appendix-b",
//     heading: "Appendix B: References(Structure only)",
//     hasChildren: false,
//     sub: [],
//   },
// ],
};
