interface PackageCardProps {
  title: string;
  amount: number;
  price: number;
  popular?: boolean;
  onSelect: (amount: number) => void;
}

export default function PackageCard({
  title,
  amount,
  price,
  popular = false,
  onSelect,
}: PackageCardProps) {
  return (
    <div className={`package-card${popular ? " package-card--popular" : ""}`}>
      {popular && <span className="popular-badge">🔥 Популярный</span>}

      <div className="package-card__header">
        <span className="package-card__title">{title}</span>
        <span className="package-card__price">
          {price.toLocaleString("ru-RU")} ₽
        </span>
      </div>

      <div className="package-card__footer">
        <span className="package-card__amount">{amount} клиентов</span>
        <button
          className="btn-select"
          onClick={() => onSelect(amount)}
        >
          Выбрать
        </button>
      </div>
    </div>
  );
}
