import client from './client';

export const authenticateWithPin = async (
  employeeId: number,
  pinHash: string,
  db: string
): Promise<{ uid: number; name: string; employee_id: number; session_id: string }> => {
  const response = await client.post('/api/security/mobile/auth/pin', {
    employee_id: employeeId,
    pin_hash: pinHash,
    db,
  });
  if (response.data && response.data.success) {
    return response.data.data;
  }
  throw new Error(response.data?.error || 'PIN authentication failed');
};

export const setPin = async (pinHash: string): Promise<void> => {
  const response = await client.post('/api/security/mobile/auth/pin/set', { pin_hash: pinHash });
  if (!response.data?.success) {
    throw new Error(response.data?.error || 'Failed to set PIN');
  }
};
