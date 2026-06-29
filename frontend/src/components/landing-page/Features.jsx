const card_list = [
  {
    title: "Conversational Elicitation",
    content:
      "Natural language conversations that guide you through comprehensive requirement gathering with intelligent follow-up questions.",
    icon: "/assets/icons/chat.svg",
  },
  {
    title: "Automated QA",
    content:
      "Advanced algorithms detect duplicates, and conflicts in your requirements automatically, ensuring quality and consistency.",
    icon: "/assets/icons/shield.svg",
  },
  {
    title: "Smart Classification",
    content:
      "Automatically categorizes requirements into functional and non-functional types, organizing your specifications for optimal clarity.",
    icon: "/assets/icons/tags.svg",
  },
  {
    title: "User Stories",
    content:
      "Generates well-structured user stories from requirements with acceptance criteria, making development planning effortless.",
    icon: "/assets/icons/book.svg",
  },
  {
    title: "Editable SRS",
    content:
      "Real-time  editing of Software Requirements Specifications with version control.",
    icon: "/assets/icons/pencil.svg",
  },
  {
    title: "Exportable Document",
    content: "Exportable SRS document available in pdf and markdown format.",
    icon: "/assets/icons/pdf.svg",
  },
];

import Card from "../Card";
export default function Features() {
  return (
    <div className="features" id="features">
      <p className="title">
        Powerful Features for Modern Requirements Engineering
      </p>
      <p className="subtitle">
        MARS combines AI-powered conversation with intelligent analysis to
        streamline your entire requirements process from initial gathering to
        final documentation.
      </p>
      <div className="cards">
        {card_list.map((element, index) => (
          <Card
            key={index} // always add a key when rendering lists
            title={element.title}
            content={element.content}
            className="img-feature"
            icon={element.icon}
            class="card"
          />
        ))}
      </div>
    </div>
  );
}
