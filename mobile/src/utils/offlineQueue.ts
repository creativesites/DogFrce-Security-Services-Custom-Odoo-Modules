import AsyncStorage from '@react-native-async-storage/async-storage';

const QUEUE_KEY = 'deployguard_offline_queue';

// ── Queue item types ──────────────────────────────────────────────────────────

export interface QueuedMark {
  type: 'mark';
  id: string;
  recordId: number;
  presence: 'present' | 'absent' | 'awol' | 'not_marked';
  overrideReason?: string;
  checkIn?: string;
  checkOut?: string;
  timestamp: string;
}

export type QueuedAction = QueuedMark;

// ── Core queue operations ─────────────────────────────────────────────────────

export const getQueue = async (): Promise<QueuedAction[]> => {
  try {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    if (!raw) return [];
    const items = JSON.parse(raw) as any[];
    // Migrate legacy entries that have no `type` field
    return items.map((item) => (item.type ? item : { ...item, type: 'mark' }));
  } catch {
    return [];
  }
};

const saveQueue = async (queue: QueuedAction[]): Promise<void> => {
  try {
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  } catch (e) {
    console.warn('Queue save failed:', e);
  }
};

export const enqueuePresenceMark = async (
  mark: Omit<QueuedMark, 'id' | 'timestamp' | 'type'>
): Promise<void> => {
  const existing = await getQueue();
  // Replace any earlier pending mark for the same record
  const filtered = existing.filter(
    (item) => !(item.type === 'mark' && item.recordId === mark.recordId)
  );
  const newItem: QueuedMark = {
    ...mark,
    type: 'mark',
    id: `mark_${mark.recordId}_${Date.now()}`,
    timestamp: new Date().toISOString(),
  };
  await saveQueue([...filtered, newItem]);
};

export const removeFromQueue = async (id: string): Promise<void> => {
  const existing = await getQueue();
  await saveQueue(existing.filter((item) => item.id !== id));
};

export const clearQueue = async (): Promise<void> => {
  await AsyncStorage.removeItem(QUEUE_KEY);
};

export const getQueuedRecordIds = async (): Promise<Set<number>> => {
  const queue = await getQueue();
  return new Set(queue.filter((i) => i.type === 'mark').map((i) => i.recordId));
};

// ── Flush ─────────────────────────────────────────────────────────────────────

export interface FlushResult {
  synced: number;
  failed: number;
  remaining: number;
}

export const flushQueue = async (
  handlers: {
    mark: (item: QueuedMark) => Promise<void>;
  }
): Promise<FlushResult> => {
  const queue = await getQueue();
  let synced = 0;
  let failed = 0;

  for (const item of queue) {
    try {
      if (item.type === 'mark') await handlers.mark(item);
      await removeFromQueue(item.id);
      synced++;
    } catch {
      failed++;
    }
  }

  const remaining = (await getQueue()).length;
  return { synced, failed, remaining };
};
