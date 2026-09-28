export function getCurrentWindow() {
  return { isMaximized: async () => true, onResized: async () => () => {} };
}
