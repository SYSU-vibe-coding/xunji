import {
  categoryLabels,
  contactPreferenceLabels,
  custodyTypeLabels,
  foundStatusLabels,
  handoverMethodLabels,
  lostStatusLabels,
} from './labels';
import type {
  ContactPreference,
  CustodyType,
  FoundItemStatus,
  HandoverMethod,
  ItemCategory,
  LostItemStatus,
} from './enums';

export interface SelectOption<T extends string> {
  value: T;
  label: string;
}

function toOptions<T extends string>(map: Record<T, string>): SelectOption<T>[] {
  return (Object.entries(map) as [T, string][]).map(([value, label]) => ({ value, label }));
}

export const categoryOptions = toOptions<ItemCategory>(categoryLabels);
export const custodyOptions = toOptions<CustodyType>(custodyTypeLabels);
export const contactOptions = toOptions<ContactPreference>(contactPreferenceLabels);
export const handoverMethodOptions = toOptions<HandoverMethod>(handoverMethodLabels);
export const lostStatusOptions = toOptions<LostItemStatus>(lostStatusLabels);
export const foundStatusOptions = toOptions<FoundItemStatus>(foundStatusLabels);
