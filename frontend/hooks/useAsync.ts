"use client";

import { useState } from "react";

export function useAsync<T>() {
  const [value, setValue] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return { value, setValue, loading, setLoading, error, setError };
}
