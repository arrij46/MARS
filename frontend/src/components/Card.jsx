export default function Card(props) {
  return (
    <div className={props.class}>
      <div className={props.className}>
        <img src={props.icon} alt={props.title} />
      </div>
      <h2>{props.title}</h2>
      <p>{props.content}</p>
     {props.value && <p className="prop-value" sc>{props.value}</p>}

    </div>
  );
}
