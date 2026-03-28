import { useEffect } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import BalancePage from "./pages/BalancePage";
import BuyPage from "./pages/BuyPage";

declare global {
  interface Window {
    Telegram: {
      WebApp: {
        ready: () => void;
        expand: () => void;
        close: () => void;
        requestFullscreen: () => void;
        exitFullscreen: () => void;
        setHeaderColor: (color: string) => void;
        setBackgroundColor: (color: string) => void;
        isFullscreen: boolean;
        safeAreaInset: { top: number; bottom: number; left: number; right: number };
        contentSafeAreaInset: { top: number; bottom: number; left: number; right: number };
        onEvent: (event: string, handler: () => void) => void;
        offEvent: (event: string, handler: () => void) => void;
        disableVerticalSwipes: () => void;
        lockOrientation: () => void;
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
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    tg.ready();
    tg.expand();
    tg.setHeaderColor?.('#6C5CE7');
    tg.setBackgroundColor?.('#F0F2FF');
    tg.disableVerticalSwipes?.();
    tg.requestFullscreen?.();
    tg.lockOrientation?.();
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
