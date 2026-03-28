import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import PackageCard from "../components/PackageCard";

const PACKAGES = [
  { title: "Старт", amount: 10, price: 500, popular: false },
  { title: "Профи", amount: 50, price: 2000, popular: true },
  { title: "Максимум", amount: 100, price: 3500, popular: false },
];

export default function BuyPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    tg.BackButton.show();
    const handler = () => navigate("/");
    tg.BackButton.onClick(handler);

    return () => {
      tg.BackButton.offClick(handler);
      tg.BackButton.hide();
    };
  }, [navigate]);

  function handleSelect(_amount: number) {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.showPopup({
        title: "Оплата недоступна",
        message:
          "Оплата временно недоступна. Следите за обновлениями!\n\nПо вопросам обращайтесь к администратору.",
        buttons: [{ type: "ok" }],
      });
    } else {
      alert(
        "Оплата временно недоступна. По вопросам обращайтесь к администратору."
      );
    }
  }

  return (
    <div className="page">
      <header className="app-header app-header--back">
        <span className="app-title">Пополнить баланс</span>
      </header>

      <main className="page-content">
        {PACKAGES.map((pkg) => (
          <PackageCard
            key={pkg.amount}
            title={pkg.title}
            amount={pkg.amount}
            price={pkg.price}
            popular={pkg.popular}
            onSelect={handleSelect}
          />
        ))}

        <p className="stub-notice">
          Оплата скоро откроется.
          <br />
          По вопросам: @admin
        </p>
      </main>
    </div>
  );
}
