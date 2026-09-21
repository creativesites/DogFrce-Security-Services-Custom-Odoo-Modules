import {
  isPermissionGranted,
  requestPermission,
  sendNotification,
} from "@tauri-apps/plugin-notification";

export interface DesktopNotificationPayload {
  title: string;
  body?: string;
  extra?: Record<string, unknown>;
}

/**
 * Dispatches an OS-level notification using Tauri's notification plugin.
 * Gracefully handles permission checking, requests, and non-Tauri browser environments.
 */
export async function notifyDesktop(payload: DesktopNotificationPayload): Promise<boolean> {
  try {
    let permissionGranted = await isPermissionGranted();
    if (!permissionGranted) {
      const permission = await requestPermission();
      permissionGranted = permission === "granted";
    }

    if (permissionGranted) {
      sendNotification({
        title: payload.title,
        body: payload.body || "",
      });
      return true;
    }
    return false;
  } catch (err) {
    // Fall back gracefully in browser / mock environments
    console.warn("Desktop notification unavailable:", err);
    return false;
  }
}
