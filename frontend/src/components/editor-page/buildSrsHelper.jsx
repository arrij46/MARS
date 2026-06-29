function cleanHeading(key) {
  return key
    .replace(/^\d+(_\d+)*__?/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

function cleanSubKey(key) {
  return key
    .replace(/^\d+(_\d+)*_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

export default function buildSRSHtml(srsJson, template = null) {
  const fontStyle = template?.fontStyle || "Arial";
  const fontSizes = template?.fontSizes || {};
  const h1Size = fontSizes["Heading 1"] || 24;
  const h2Size = fontSizes["Heading 2"] || 20;
  const h3Size = fontSizes["Heading 3"] || 16;
  const h4Size = fontSizes["Heading 4"] || 14;
  const pSize  = fontSizes["Paragraph"] || 12;

  let html = "";

  if (srsJson.title) {
    html += `<h1 style="font-family:${fontStyle};font-size:${h1Size}pt;">${srsJson.title}</h1>`;
  }

  const sections = srsJson.sections || {};

  html += `<ol>`;

  Object.entries(sections).forEach(([secKey, secValue]) => {
    const secHeading = cleanHeading(secKey);

    html += `<li>`;
    html += `<strong style="font-family:${fontStyle};font-size:${h2Size}pt;display:block;margin-bottom:6pt;">${secHeading}</strong>`;

    // ── String section (e.g. Appendix Glossary)
    if (typeof secValue === "string") {
      if (secValue) {
        const isGlossary = secKey.toLowerCase().includes("glossary");
        if (isGlossary) {
          const terms = secValue.split(/\n/).map(t => t.trim()).filter(Boolean);
          html += `<ul style="font-family:${fontStyle};font-size:${pSize}pt;margin-top:6pt;">`;
          terms.forEach((line) => {
            const colonIdx = line.indexOf(":");
            if (colonIdx !== -1) {
              const term = line.substring(0, colonIdx).trim();
              const def  = line.substring(colonIdx + 1).trim();
              html += `<li><p><strong>${term}:</strong> ${def}</p></li>`;
            } else {
              html += `<li><p>${line}</p></li>`;
            }
          });
          html += `</ul>`;
        } else {
          html += `<p style="font-family:${fontStyle};font-size:${pSize}pt;">${secValue}</p>`;
        }
      }
      html += `</li>`;
      return;
    }

    if (typeof secValue === "object" && secValue !== null) {

      // ── Features section: subsections have functional_requirements
      const isFeatureSection = Object.values(secValue).some(
        (v) => typeof v === "object" && v !== null && "functional_requirements" in v
      );

      // ── NFR top-level section: subsections have nonfunctional_requirements
      const isNFRSection = Object.values(secValue).some(
        (v) => typeof v === "object" && v !== null && "nonfunctional_requirements" in v
      );

      if (isFeatureSection) {
        html += `<ol>`;
        Object.entries(secValue).forEach(([featureKey, feature]) => {
          if (typeof feature !== "object" || feature === null) return;
          const featureHeading = cleanSubKey(featureKey);

          html += `<li>`;
          html += `<strong style="font-family:${fontStyle};font-size:${h3Size}pt;display:block;margin-bottom:4pt;">${featureHeading}</strong>`;

          if (feature.description) {
            html += `<p style="font-family:${fontStyle};font-size:${pSize}pt;">${feature.description}</p>`;
          }
          if (feature.functional_overview?.length > 0) {
            html += `<ul style="font-family:${fontStyle};font-size:${pSize}pt;">`;
            feature.functional_overview.forEach((point) => {
              html += `<li>${point}</li>`;
            });
            html += `</ul>`;
          }
          if (feature.functional_requirements?.length > 0) {
            html += `<p style="font-family:${fontStyle};font-size:${h4Size}pt;font-weight:bold;margin-top:8pt;">Requirements</p>`;
            html += `<ul style="font-family:${fontStyle};font-size:${pSize}pt;">`;
            feature.functional_requirements.forEach((req) => {
              html += `<li><strong>${req.id}</strong>&nbsp;&nbsp;${req.text}</li>`;
            });
            html += `</ul>`;
          }
          html += `</li>`;
        });
        html += `</ol>`;

      } else if (isNFRSection) {
        // ── NFR section: each subsection has description + nonfunctional_requirements
        html += `<ol>`;
        Object.entries(secValue).forEach(([subKey, subValue]) => {
          if (!subValue || (typeof subValue === "object" && Object.keys(subValue).length === 0)) return;

          const subHeading = cleanSubKey(subKey);
          html += `<li>`;
          html += `<strong style="font-family:${fontStyle};font-size:${h3Size}pt;display:block;margin-bottom:4pt;">${subHeading}</strong>`;

          if (typeof subValue === "string") {
            // Plain string NFR subsection (edge case)
            html += `<p style="font-family:${fontStyle};font-size:${pSize}pt;">${subValue}</p>`;

          } else if (typeof subValue === "object") {
            // Description paragraph
            if (subValue.description) {
              html += `<p style="font-family:${fontStyle};font-size:${pSize}pt;">${subValue.description}</p>`;
            }

            // nonfunctional_requirements list
            const nfrs = subValue.nonfunctional_requirements;
            if (Array.isArray(nfrs) && nfrs.length > 0) {
              html += `<p style="font-family:${fontStyle};font-size:${h4Size}pt;font-weight:bold;margin-top:8pt;">Requirements</p>`;
              html += `<ul style="font-family:${fontStyle};font-size:${pSize}pt;">`;
              nfrs.forEach((req) => {
                if (typeof req === "string") {
                  html += `<li>${req}</li>`;
                } else if (req?.id && req?.text) {
                  html += `<li><strong>${req.id}</strong>&nbsp;&nbsp;${req.text}</li>`;
                }
              });
              html += `</ul>`;
            } else if (Array.isArray(nfrs) && nfrs.length === 0) {
              html += `<p style="font-family:${fontStyle};font-size:${pSize}pt;color:#888888;font-style:italic;">No specific requirements identified.</p>`;
            }
          }

          html += `</li>`;
        });
        html += `</ol>`;

      } else {
        // ── Regular subsections (Introduction, Overall Description, etc.)
        const hasContent = Object.values(secValue).some(
          (v) => v && !(typeof v === "object" && Object.keys(v).length === 0)
        );

        if (hasContent) {
          html += `<ol>`;
          Object.entries(secValue).forEach(([subKey, subValue]) => {
            if (!subValue || (typeof subValue === "object" && Object.keys(subValue).length === 0)) return;

            const subHeading = cleanSubKey(subKey);
            html += `<li>`;
            html += `<strong style="font-family:${fontStyle};font-size:${h3Size}pt;display:block;margin-bottom:4pt;">${subHeading}</strong>`;

            if (typeof subValue === "string") {
              html += `<p style="font-family:${fontStyle};font-size:${pSize}pt;">${subValue}</p>`;

            } else if (Array.isArray(subValue)) {
              html += `<ul style="font-family:${fontStyle};font-size:${pSize}pt;">`;
              subValue.forEach((item) => {
                if (typeof item === "string") html += `<li>${item}</li>`;
                else if (item?.id && item?.text) html += `<li><strong>${item.id}</strong>&nbsp;&nbsp;${item.text}</li>`;
              });
              html += `</ul>`;

            } else if (typeof subValue === "object") {
              // ISO 29148 style — features nested inside subsection
              const isNestedFeatures = Object.values(subValue).some(
                (v) => typeof v === "object" && v !== null && "functional_requirements" in v
              );
              // NFR subsection nested inside a generic section (e.g. Section 6)
              const isNestedNFR = subValue.nonfunctional_requirements !== undefined;

              if (isNestedFeatures) {
                html += `<ol>`;
                Object.entries(subValue).forEach(([nestedKey, nestedFeature]) => {
                  if (typeof nestedFeature !== "object" || nestedFeature === null) return;
                  const nestedHeading = cleanSubKey(nestedKey);

                  html += `<li>`;
                  html += `<strong style="font-family:${fontStyle};font-size:${h4Size}pt;display:block;margin-bottom:4pt;">${nestedHeading}</strong>`;
                  if (nestedFeature.description) {
                    html += `<p style="font-family:${fontStyle};font-size:${pSize}pt;">${nestedFeature.description}</p>`;
                  }
                  if (nestedFeature.functional_overview?.length > 0) {
                    html += `<ul style="font-family:${fontStyle};font-size:${pSize}pt;">`;
                    nestedFeature.functional_overview.forEach((point) => {
                      html += `<li>${point}</li>`;
                    });
                    html += `</ul>`;
                  }
                  if (nestedFeature.functional_requirements?.length > 0) {
                    html += `<p style="font-family:${fontStyle};font-size:${h4Size}pt;font-weight:bold;margin-top:8pt;">Requirements</p>`;
                    html += `<ul style="font-family:${fontStyle};font-size:${pSize}pt;">`;
                    nestedFeature.functional_requirements.forEach((req) => {
                      html += `<li><strong>${req.id}</strong>&nbsp;&nbsp;${req.text}</li>`;
                    });
                    html += `</ul>`;
                  }
                  html += `</li>`;
                });
                html += `</ol>`;

              } else if (isNestedNFR) {
                // e.g. Section 6 Other Requirements has description + nonfunctional_requirements
                if (subValue.description) {
                  html += `<p style="font-family:${fontStyle};font-size:${pSize}pt;">${subValue.description}</p>`;
                }
                const nfrs = subValue.nonfunctional_requirements;
                if (Array.isArray(nfrs) && nfrs.length > 0) {
                  html += `<p style="font-family:${fontStyle};font-size:${h4Size}pt;font-weight:bold;margin-top:8pt;">Requirements</p>`;
                  html += `<ul style="font-family:${fontStyle};font-size:${pSize}pt;">`;
                  nfrs.forEach((req) => {
                    if (typeof req === "string") html += `<li>${req}</li>`;
                    else if (req?.id && req?.text) html += `<li><strong>${req.id}</strong>&nbsp;&nbsp;${req.text}</li>`;
                  });
                  html += `</ul>`;
                }
              }
            }

            html += `</li>`;
          });
          html += `</ol>`;
        }
      }
    }

    html += `</li>`;
  });

  // ── RTM Appendix
  const rtmData = Array.isArray(srsJson?.Appendix_RTM) ? srsJson.Appendix_RTM : [];

  if (rtmData.length > 0) {
    html += `<li>`;
    html += `<strong style="font-family:${fontStyle};font-size:${h2Size}pt;display:block;margin-bottom:10pt;">
      Appendix B – Requirements Traceability Matrix
    </strong>`;

    const grouped = {};
    rtmData.forEach(entry => {
      const key = (entry.feature || "Uncategorized").replace(/_/g, " ");
      if (!grouped[key]) grouped[key] = { section: entry.srs_section || "", reqs: [] };
      grouped[key].reqs.push(entry);
    });

    let counter = 1;

    Object.entries(grouped)
      .sort(([, a], [, b]) => {
        const typeA = a.reqs[0]?.type === "Non-Functional" ? 1 : 0;
        const typeB = b.reqs[0]?.type === "Non-Functional" ? 1 : 0;
        return typeA - typeB;
      })
      .forEach(([feature, { section, reqs }]) => {
        html += `<p style="font-family:${fontStyle};font-size:${h3Size}pt;margin-top:14pt;margin-bottom:2pt;">
          </br><strong>SRS Section ${section}:</strong> ${feature}
        </p>`;

        reqs.forEach(entry => {
          const origins = Array.isArray(entry.origin) ? entry.origin.join(", ") : entry.origin ? String(entry.origin): "—";
          const type      = entry.type    || "—";
          const subtype   = entry.subtype || "—";
          const parentTxt = entry.parent_text || "—";

          html += `
            <table style="width:100%;border-collapse:collapse;margin-bottom:8pt;font-family:${fontStyle};">
              <tr>
                <td style="width:28pt;vertical-align:top;padding:4pt 6pt 4pt 0pt;">
                  <p style="font-size:${pSize}pt;font-weight:bold;color:#999999;margin:0;"># ${counter++}</p>
                </td>
                <td style="vertical-align:top;padding:4pt 0pt;border-top:0.5pt solid #dddddd;">
                  <p style="font-size:${pSize}pt;font-weight:bold;margin:0 0 3pt 0;">${entry.id}</p>
                  <p style="font-size:${pSize}pt;margin:0 0 5pt 0;line-height:1.5;">${entry.text || ""}</p>
                  ${entry.parent_req_id ? `
                  <p style="font-size:${pSize - 1}pt;color:#555555;margin:0 0 5pt 14pt;font-style:italic;">
                    <strong style="font-style:normal;">Derived from (Parent): </br>${entry.parent_req_id}</strong> — ${parentTxt}
                  </p>` : ""}
                  <p style="font-size:${pSize - 1}pt;color:#666666;margin:0;">
                    <strong>Origin:</strong> ${origins}&nbsp;&nbsp;&nbsp;
                    <strong>Type:</strong> ${type}&nbsp;&nbsp;&nbsp;
                    <strong>Subtype:</strong> ${subtype}&nbsp;&nbsp;&nbsp;
                    ${!entry.parent_req_id ? `<strong>Parent:</strong> None` : ""}
                  </p>
                </td>
              </tr>
            </table>
          `;
        });
      });

    html += `</li>`;
  }

  html += `</ol>`;
  return html;
}