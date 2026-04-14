import { create } from 'zustand';
import { persist, createJSONStorage, type StateStorage } from 'zustand/middleware';
import type { AssessmentRecord, WrapResult } from '../api/types';

const MAX_RECORDS = 100;

/**
 * IndexedDB-backed storage adapter for Zustand persist.
 * Prevents the 5MB localStorage quota from silently breaking
 * history persistence when assessment records accumulate.
 * Falls back to localStorage when IndexedDB is unavailable (SSR, tests).
 */
function createStorage() {
  if (typeof indexedDB === 'undefined') {
    return createJSONStorage(() => localStorage);
  }
  // Lazy-import idb-keyval only when IndexedDB is available
  const idbPromise = import('idb-keyval');
  const storage: StateStorage = {
    getItem: async (name: string) => {
      const { get } = await idbPromise;
      const value = await get<string>(name);
      return value ?? null;
    },
    setItem: async (name: string, value: string) => {
      const { set } = await idbPromise;
      await set(name, value);
    },
    removeItem: async (name: string) => {
      const { del } = await idbPromise;
      await del(name);
    },
  };
  return createJSONStorage(() => storage);
}

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
    { name: 'nc-history', storage: createStorage() },
  ),
);
