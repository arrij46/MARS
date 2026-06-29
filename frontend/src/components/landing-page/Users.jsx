const card_list = [
  {
    title: "Product Managers",
    content:
      "Transform stakeholder conversations into clear, actionable requirements without endless meetings.",
    icon: "/assets/icons/chart.svg",
  },
  {
    title: "Business Analysts",
    content:
      "Streamline requirement gathering with AI-powered elicitation and automated quality checks.",
    icon: "/assets/icons/people.svg",
  },
  {
    title: "Small Dev Teams",
    content:
      "Get complete, conflict-free specifications faster so you can focus on building great products.",
    icon: "/assets/icons/code.svg",
  },
  {
    title: "Startups",
    content:
      "Move from idea to development quickly with structured requirements that scale with your growth.",
    icon: "/assets/icons/rocket.svg",
  },
  {
    title: "Academic Projects",
    content:
      "Learn best practices in requirement engineering with guided conversations and automated feedback.",
    icon: "/assets/icons/hat.svg",
  }
];
import Card from "../Card";
export default function Users() {
  return (
    <div className="features user-types">
      <p className="title">
        Who is MARS for?
      </p>
      <p className="subtitle">
       Designed for teams and individuals who need clear, complete requirements
      </p>
      <div className="cards user-card">
        {card_list.map((element, index) => (
          <Card
            key={index} 
            title={element.title}
            content={element.content}
            className="img-user"
            icon={element.icon}
            class="card"
          />
        ))}
      </div>
    </div>
  );
}
