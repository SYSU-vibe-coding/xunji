import { describe, expect, it } from 'vitest';

import {
  appendUniqueUrl,
  buildClaimAnswers,
  buildMyItemsQuery,
  buildSearchQuery,
  getMatchCounterpartKind,
  getNotificationTarget,
  parseVerifyQuestionDrafts,
  parseSearchQuery,
  parseMyItemsQuery,
} from './interaction';

describe('user interaction utils', () => {
  it('requires an answer for every claim question and trims valid answers', () => {
    const questions = [
      { id: 'q1', questionText: '颜色' },
      { id: 'q2', questionText: '标记' },
    ];

    expect(buildClaimAnswers(questions, { q1: ' 白色 ', q2: ' ' })).toBeNull();
    expect(buildClaimAnswers(questions, { q1: ' 白色 ', q2: '星星' })).toEqual([
      { questionId: 'q1', answerText: '白色' },
      { questionId: 'q2', answerText: '星星' },
    ]);
  });

  it('derives the aggregate match counterpart direction from item ids', () => {
    const match = {
      lostItemId: 'lost-1',
      foundItemId: 'found-1',
      counterpart: { id: 'lost-1' },
    } as Parameters<typeof getMatchCounterpartKind>[0];

    expect(getMatchCounterpartKind(match)).toBe('lost');
    match.counterpart.id = 'found-1';
    expect(getMatchCounterpartKind(match)).toBe('found');
  });

  it('maps runtime match and certification notifications to usable routes', () => {
    expect(getNotificationTarget('MATCH', 'match/1')).toBe('/matches?matchId=match%2F1');
    expect(getNotificationTarget('CERT', 'cert-1')).toBe('/profile/certification');
    expect(getNotificationTarget('CLAIM', 'claim-1')).toBe('/claims/claim-1');
    expect(getNotificationTarget('ANNOUNCEMENT', 'notice-1')).toBe('/announcements/notice-1');
  });

  it('validates search query values and serializes all active filters', () => {
    const state = parseSearchQuery({
      mode: 'LOST',
      keyword: ' 卡 ',
      category: 'CERT',
      location: '图书馆',
      eventTimeStart: '2026-07-01 00:00:00',
      eventTimeEnd: '2026-07-11 23:59:59',
      status: 'SEARCHING',
      sortBy: 'CREATED_ASC',
      page: '3',
    });

    expect(buildSearchQuery(state)).toEqual({
      mode: 'LOST',
      keyword: '卡',
      category: 'CERT',
      location: '图书馆',
      eventTimeStart: '2026-07-01 00:00:00',
      eventTimeEnd: '2026-07-11 23:59:59',
      status: 'SEARCHING',
      sortBy: 'CREATED_ASC',
      page: '3',
    });
    expect(parseSearchQuery({ mode: 'FOUND', status: 'SEARCHING', page: '-2' }).status).toBe('');
    expect(parseSearchQuery({ page: '2oops' }).page).toBe(1);
    expect(parseSearchQuery({ sortBy: 'EVENT_DESC' }).sortBy).toBe('EVENT_DESC');
  });

  it('ignores fully empty verification rows but reports each half-filled field', () => {
    expect(parseVerifyQuestionDrafts([
      { questionText: '', answerKeywords: '' },
      { questionText: '物品颜色', answerKeywords: '' },
      { questionText: '', answerKeywords: '白色' },
    ])).toEqual({
      questions: null,
      errors: {
        1: { answerKeywords: '填写了问题时，答案关键词不能为空' },
        2: { questionText: '填写了答案时，问题不能为空' },
      },
    });

    expect(parseVerifyQuestionDrafts([
      { questionText: '', answerKeywords: '' },
      { questionText: '物品颜色', answerKeywords: ' 白色，银色 ' },
    ])).toEqual({
      questions: [{ questionText: '物品颜色', answerKeywords: ['白色', '银色'] }],
      errors: {},
    });
  });

  it('merges parallel upload results without replacing prior completions', () => {
    const afterFirst = appendUniqueUrl([], 'first.jpg');
    const afterSecond = appendUniqueUrl(afterFirst, 'second.jpg');
    expect(afterSecond).toEqual(['first.jpg', 'second.jpg']);
    expect(appendUniqueUrl(afterSecond, 'first.jpg')).toEqual(afterSecond);
  });

  it('normalizes my-items tab/page and preserves an exact bizType plus id target', () => {
    expect(parseMyItemsQuery({ bizType: 'FOUND', id: 'found-1', page: '3' })).toEqual({
      tab: 'found',
      page: 3,
      targetId: 'found-1',
    });
    expect(parseMyItemsQuery({ tab: 'lost', page: 'bad' })).toEqual({
      tab: 'lost',
      page: 1,
      targetId: '',
    });
    expect(buildMyItemsQuery('found', 2, 'found-1')).toEqual({
      tab: 'found',
      page: '2',
      bizType: 'FOUND',
      id: 'found-1',
    });
  });
});
