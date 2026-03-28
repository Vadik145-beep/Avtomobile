import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { type UserData, getUser } from "../api";

export default function BalancePage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getUser()
      .then(setUser)
      .catch(() => setError("Не удалось загрузить данные"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="page">
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <p className="error-text">{error}</p>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="app-header">
        <span className="app-title">Авто-Лид</span>
      </header>

      <main className="page-content">
        <p className="section-label">Ваш баланс</p>

        <div className="balance-card">
          <span className="balance-number">{user?.limit_count ?? 0}</span>
          <span className="balance-unit">
            {pluralClients(user?.limit_count ?? 0)}
          </span>
        </div>

        <div className="btn-center">
          <button className="btn-primary" onClick={() => navigate("/buy")}>
            Пополнить баланс →
          </button>
        </div>
      </main>
    </div>
  );
}

function pluralClients(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "клиент";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "клиента";
  return "клиентов";
}
