import type {
  ClaimAnswerInput,
  FoundItemStatus,
  ItemCategory,
  LostItemStatus,
  MatchSummary,
  SortBy,
  VerifyQuestionInput,
  VerifyQuestionOutput,
} from '@xunji/shared';

export function buildClaimAnswers(
  questions: VerifyQuestionOutput[],
  values: Record<string, string>,
): ClaimAnswerInput[] | null {
  const answers = questions.map((question) => ({
    questionId: question.id,
    answerText: (values[question.id] ?? '').trim(),
  }));
  return answers.every((answer) => answer.answerText.length > 0) ? answers : null;
}

export function getMatchCounterpartKind(match: MatchSummary): 'lost' | 'found' | null {
  if (match.counterpart.id === match.lostItemId) return 'lost';
  if (match.counterpart.id === match.foundItemId) return 'found';
  return null;
}

export function canInitiateClaim(creditScore: number | null | undefined): boolean {
  return typeof creditScore === 'number' && creditScore >= 30;
}

export function getNotificationTarget(
  relatedType: string | null,
  relatedId: string | null,
): string | null {
  if (relatedType === 'CERT') return '/profile/certification';
  if (relatedType === 'USER') return '/profile';
  if (!relatedId) return null;
  if (relatedType === 'CLAIM' || relatedType === 'CLAIM_PROOF') return `/claims/${relatedId}`;
  if (relatedType === 'FOUND') return `/items/found/${relatedId}`;
  if (relatedType === 'LOST') return `/items/lost/${relatedId}`;
  if (relatedType === 'MATCH') return `/matches?matchId=${encodeURIComponent(relatedId)}`;
  if (relatedType === 'ANNOUNCEMENT') return `/announcements/${relatedId}`;
  return null;
}

export type SearchMode = 'FOUND' | 'LOST';

export interface SearchState {
  mode: SearchMode;
  keyword: string;
  category: ItemCategory | '';
  location: string;
  eventTimeStart: string;
  eventTimeEnd: string;
  status: FoundItemStatus | LostItemStatus | '';
  sortBy: SortBy;
  page: number;
}

const ITEM_CATEGORIES = new Set<ItemCategory>([
  'CERT',
  'ELECTRONIC',
  'DAILY_USE',
  'BOOK',
  'OTHER',
]);
const FOUND_STATUSES = new Set<FoundItemStatus>(['PENDING', 'CLAIMING', 'RETURNED', 'CLOSED']);
const LOST_STATUSES = new Set<LostItemStatus>(['SEARCHING', 'FOUND', 'CLOSED']);

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

const DATE_TIME_VALUE = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;

export function parseSearchQuery(query: Record<string, unknown>): SearchState {
  const mode: SearchMode = query.mode === 'LOST' ? 'LOST' : 'FOUND';
  const categoryValue = stringValue(query.category) as ItemCategory;
  const statusValue = stringValue(query.status);
  const parsedPage = Number(stringValue(query.page));
  const eventTimeStart = stringValue(query.eventTimeStart);
  const eventTimeEnd = stringValue(query.eventTimeEnd);
  const hasValidEventRange = DATE_TIME_VALUE.test(eventTimeStart) &&
    DATE_TIME_VALUE.test(eventTimeEnd) &&
    eventTimeStart <= eventTimeEnd;
  const validStatus =
    mode === 'FOUND'
      ? FOUND_STATUSES.has(statusValue as FoundItemStatus)
      : LOST_STATUSES.has(statusValue as LostItemStatus);

  return {
    mode,
    keyword: stringValue(query.keyword),
    category: ITEM_CATEGORIES.has(categoryValue) ? categoryValue : '',
    location: stringValue(query.location),
    eventTimeStart: hasValidEventRange ? eventTimeStart : '',
    eventTimeEnd: hasValidEventRange ? eventTimeEnd : '',
    status: validStatus ? (statusValue as FoundItemStatus | LostItemStatus) : '',
    sortBy:
      query.sortBy === 'CREATED_ASC' ||
      query.sortBy === 'EVENT_DESC' ||
      query.sortBy === 'EVENT_ASC'
        ? query.sortBy
        : 'CREATED_DESC',
    page: Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1,
  };
}

export function buildSearchQuery(state: SearchState): Record<string, string> {
  const query: Record<string, string> = {
    mode: state.mode,
    sortBy: state.sortBy,
    page: String(state.page),
  };
  if (state.keyword.trim()) query.keyword = state.keyword.trim();
  if (state.category) query.category = state.category;
  if (state.location.trim()) query.location = state.location.trim();
  if (state.eventTimeStart && state.eventTimeEnd) {
    query.eventTimeStart = state.eventTimeStart;
    query.eventTimeEnd = state.eventTimeEnd;
  }
  if (state.status) query.status = state.status;
  return query;
}

export function appendUniqueUrl(urls: readonly string[], url: string): string[] {
  return urls.includes(url) ? [...urls] : [...urls, url];
}

export type MyItemsTab = 'lost' | 'found';

export function parseMyItemsQuery(query: Record<string, unknown>): {
  tab: MyItemsTab;
  page: number;
  targetId: string;
} {
  const bizType = stringValue(query.bizType).toUpperCase();
  const tab: MyItemsTab = bizType === 'FOUND' || query.tab === 'found' ? 'found' : 'lost';
  const parsedPage = Number(stringValue(query.page));
  return {
    tab,
    page: Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1,
    targetId: stringValue(query.id),
  };
}

export function buildMyItemsQuery(tab: MyItemsTab, page: number, targetId = ''): Record<string, string> {
  const query = { tab, page: String(page) };
  return targetId
    ? { ...query, bizType: tab === 'lost' ? 'LOST' : 'FOUND', id: targetId }
    : query;
}

export interface VerifyQuestionDraft {
  questionText: string;
  answerKeywords: string;
}

export interface VerifyQuestionFieldErrors {
  questionText?: string;
  answerKeywords?: string;
}

export function parseVerifyQuestionDrafts(rows: VerifyQuestionDraft[]): {
  questions: VerifyQuestionInput[] | null;
  errors: Record<number, VerifyQuestionFieldErrors>;
} {
  const questions: VerifyQuestionInput[] = [];
  const errors: Record<number, VerifyQuestionFieldErrors> = {};

  rows.forEach((row, index) => {
    const questionText = row.questionText.trim();
    const rawKeywords = row.answerKeywords.trim();
    if (!questionText && !rawKeywords) return;

    const rowErrors: VerifyQuestionFieldErrors = {};
    if (!questionText) rowErrors.questionText = '填写了答案时，问题不能为空';
    if (!rawKeywords) rowErrors.answerKeywords = '填写了问题时，答案关键词不能为空';
    const answerKeywords = rawKeywords
      .split(/[,，]/)
      .map((keyword) => keyword.trim())
      .filter(Boolean);
    if (rawKeywords && !answerKeywords.length) rowErrors.answerKeywords = '请填写有效的答案关键词';
    if (answerKeywords.length > 10) rowErrors.answerKeywords = '每个问题最多填写 10 个答案关键词';
    if (answerKeywords.some((keyword) => keyword.length > 20)) {
      rowErrors.answerKeywords = '每个答案关键词不超过 20 字';
    }
    if (Object.keys(rowErrors).length) {
      errors[index] = rowErrors;
      return;
    }
    questions.push({ questionText, answerKeywords });
  });

  return { questions: Object.keys(errors).length ? null : questions, errors };
}
