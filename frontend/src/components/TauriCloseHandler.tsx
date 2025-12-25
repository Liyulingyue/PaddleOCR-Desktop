import { useEffect } from 'react';
import { listen } from '@tauri-apps/api/event';

export function TauriCloseHandler() {
  useEffect(() => {
    let unlisten: () => void;

    (async () => {
      const _unlisten = await listen('tauri://close-requested', () => {
        // 简单提示用户正在退出并清理后端
        // 可以在这里触发一个更友好的 UI，比如 modal 或 loading 状态
        alert('应用正在退出，正在清理后台进程，请稍候...');
      });
      unlisten = () => _unlisten();
    })();

    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  return null;
}
