const BASE_URL = "/api/bot/miniapp";

function getInitData(): string {
  return window.Telegram?.WebApp?.initData ?? "";
}

async function fetchWithAuth<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": getInitData(),
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

export interface UserData {
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  limit_count: number;
}

export interface BuyResult {
  status: string;
  message: string;
}

export async function getUser(): Promise<UserData> {
  return fetchWithAuth<UserData>("/user");
}

export async function buyPackage(amount: number): Promise<BuyResult> {
  return fetchWithAuth<BuyResult>("/buy", {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
}
