import { useEffect, useState } from "react";
import { fetchHealth, HealthReport } from "../api/client";

export function useHealth(intervalMs = 10000) {
  const [health, setHealth] = useState<HealthReport | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      const h = await fetchHealth();
      if (alive) {
        setHealth(h);
        setChecked(true);
      }
    };
    poll();
    const id = setInterval(poll, intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [intervalMs]);

  return { health, checked };
}
