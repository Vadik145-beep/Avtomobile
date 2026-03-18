import { useEffect } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import BalancePage from "./pages/BalancePage";
import BuyPage from "./pages/BuyPage";

declare global {
  interface Window {
    Telegram: {
      WebApp: {
        ready: () => void;
        close: () => void;
        BackButton: {
          show: () => void;
          hide: () => void;
          onClick: (fn: () => void) => void;
          offClick: (fn: () => void) => void;
        };
        showPopup: (params: {
          title?: string;
          message: string;
          buttons?: Array<{ type: string; text?: string }>;
        }) => void;
        initData: string;
        colorScheme: "light" | "dark";
      };
    };
  }
}

export default function App() {
  useEffect(() => {
    window.Telegram?.WebApp?.ready();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<BalancePage />} />
        <Route path="/buy" element={<BuyPage />} />
      </Routes>
    </BrowserRouter>
  );
}
