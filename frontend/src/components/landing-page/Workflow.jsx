const list = [
  {
    title: "Start Chat",
    content: "Begin with natural conversation",
    icon: "/assets/icons/chat2.svg",
  },
  {
    title: "Elicit",
    content: "AI guides requirement discovery",
    icon: "/assets/icons/search.svg",
  },
  {
    title: "Catagorization",
    content: "Catagorize the requirements",
    icon: "/assets/icons/thumbs-up.svg",
  },
  {
    title: "QA Check",
    content: "Automated quality analysis",
    icon: "/assets/icons/check.svg",
  },
  {
    title: "Refine & Validate",
    content: "Review the refined requirements",
    icon: "/assets/icons/thumbs-up.svg",
  },
  {
    title: "Generate Stories",
    content: "Create user stories automatically",
    icon: "/assets/icons/story.svg",
  },
  {
    title: "SRS Document",
    content: "Edit document as needed",
    icon: "/assets/icons/file.svg",
  },
  {
    title: "Export SRS",
    content: "Download complete specification",
    icon: "/assets/icons/download.svg",
  },
];
import Card from "../Card";
export default function Workflow() {
  return (
    <div className="features workflow" id="workflow">
      <p className="title">Streamlined Workflow in 8 Simple Steps</p>
      <p className="subtitle">
    From the initial conversation to the final specification, MARS guides you through a
    process that ensures clarity, quality, and completeness.
      </p>
      <div className="workflow-steps">
        {list.map((element, index) => (
          <Card
            key={index}
            title={element.title}
            content={element.content}
            className="img-workflow"
            icon={element.icon}
            class="workflow-card"
            value={index + 1}
          />
        ))}
      </div>
    </div>
  );
}
