import AsyncStorage from '@react-native-async-storage/async-storage';

const QUEUE_KEY = 'dogforce_offline_queue';

export interface QueuedMark {
  id: string;
  recordId: number;
  presence: 'present' | 'absent' | 'awol' | 'not_marked';
  overrideReason?: string;
  checkIn?: string;
  checkOut?: string;
  timestamp: string;
}

export const enqueuePresenceMark = async (mark: Omit<QueuedMark, 'id' | 'timestamp'>): Promise<void> => {
  try {
    const existing = await getQueue();
    const newItem: QueuedMark = {
      ...mark,
      id: `${mark.recordId}_${Date.now()}`,
      timestamp: new Date().toISOString(),
    };
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify([...existing, newItem]));
  } catch (e) {
    console.warn('Enqueue failed:', e);
  }
};

export const getQueue = async (): Promise<QueuedMark[]> => {
  try {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

export const removeFromQueue = async (id: string): Promise<void> => {
  try {
    const existing = await getQueue();
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(existing.filter(item => item.id !== id)));
  } catch (e) {
    console.warn('Queue remove failed:', e);
  }
};

export const flushQueue = async (markFn: (mark: QueuedMark) => Promise<void>): Promise<{ synced: number; failed: number }> => {
  const queue = await getQueue();
  let synced = 0;
  let failed = 0;
  for (const item of queue) {
    try {
      await markFn(item);
      await removeFromQueue(item.id);
      synced++;
    } catch {
      failed++;
    }
  }
  return { synced, failed };
};
