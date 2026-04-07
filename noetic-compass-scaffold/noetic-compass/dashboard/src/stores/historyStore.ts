import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AssessmentRecord, WrapResult } from '../api/types';

const MAX_RECORDS = 100;

interface HistoryState {
  records: AssessmentRecord[];
  add: (text: string, result: WrapResult) => string;
  clear: () => void;
  getById: (id: string) => AssessmentRecord | undefined;
}

export const useHistoryStore = create<HistoryState>()(
  persist(
    (set, get) => ({
      records: [],
      add(text: string, result: WrapResult) {
        const id = crypto.randomUUID();
        const record: AssessmentRecord = {
          id,
          timestamp: Date.now(),
          text,
          result,
        };
        set((state) => ({
          records: [record, ...state.records].slice(0, MAX_RECORDS),
        }));
        return id;
      },
      clear() {
        set({ records: [] });
      },
      getById(id: string) {
        return get().records.find((r) => r.id === id);
      },
    }),
    { name: 'nc-history' },
  ),
);
