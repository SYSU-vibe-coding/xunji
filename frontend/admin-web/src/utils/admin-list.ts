export function queryValue(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

export function queryEnum<T extends string>(value: unknown, values: readonly T[]): T | '' {
  const normalized = queryValue(value);
  return values.includes(normalized as T) ? (normalized as T) : '';
}

export function queryPositiveInt(value: unknown, fallback = 1): number {
  const parsed = Number(queryValue(value));
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export function lastPage(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / pageSize));
}

export function createLatestRequestGuard() {
  let latestId = 0;
  return {
    next(): number {
      latestId += 1;
      return latestId;
    },
    isLatest(id: number): boolean {
      return id === latestId;
    },
  };
}
