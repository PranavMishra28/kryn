// Native OpenCode slot; permissions are still implemented by OpenCode.
import fs from 'node:fs';
import path from 'node:path';
import { createSignal } from 'solid-js';
import { permissionLabel } from './permission_display.mjs';
import { setupUpdates } from './update_notice.mjs';

export default {
  id: 'kryn.controls',
  setup(context) {
    const updates = setupUpdates(context);
    const launch = process.env.KRYN_PERMISSION_MODE;
    const file = path.join(process.env.XDG_CONFIG_HOME ?? '', 'opencode', 'cli.json');
    const read = () => {
      if (launch !== 'interactive') return permissionLabel(launch);
      try {
        return permissionLabel(launch, fs.readFileSync(file, 'utf8'));
      } catch (error) { return error.code === 'ENOENT' ? 'Ask' : 'Unknown'; }
    };
    const [mode, setMode] = createSignal(read());
    const timer = setInterval(() => setMode(read()), 500);
    const open = () => {
      if (launch !== 'interactive') context.ui.toast.show({
        message: 'This launch pins permissions. Relaunch with kryn --permissions interactive to change them here.',
        variant: 'info', duration: 6000 });
      context.keymap.dispatch('opencode.settings');
    };
    const removeSlot = context.ui.slot({ append: 'prompt.footer.status', render: () => (
      <box onMouseUp={open} flexShrink={0}>
        <text fg={context.theme.text.muted}> · Permissions: {mode()}</text>
      </box>
    ) });
    const removeCommand = context.ui.slot({ append: 'app', render: () => {
      context.keymap.layer(() => ({ mode: 'global', priority: 100, commands: [{
        id: 'kryn.permissions', title: 'KRYN: permission settings', group: 'KRYN',
        palette: true, slash: { name: 'permissions' }, run: open,
      }, {
        // Shadow the native updater as well as its slash alias: OpenCode stays pinned.
        id: 'opencode.update', title: 'KRYN: check for a verified update', group: 'KRYN',
        palette: true, slash: { name: 'update' }, run: updates.open,
      }, {
        id: 'session.share', title: 'KRYN: export this session locally', group: 'KRYN',
        palette: true, slash: { name: 'share' }, run: () => {
          context.ui.toast.show({ message: 'OpenCode V2 has no public share link. Opening a local session export; review it before sending.',
            variant: 'info', duration: 6000 });
          context.keymap.dispatch('session.export');
        },
      }] }));
      return null;
    } });
    return () => { updates.dispose(); clearInterval(timer); removeSlot(); removeCommand(); };
  },
};
