import { useEffect } from 'react';
import { supabase } from '../lib/supabase';
import type { RealtimePostgresChangesPayload } from '@supabase/supabase-js';

type ChangeEvent = 'INSERT' | 'UPDATE' | 'DELETE' | '*';

export function useRealtimeSubscription<T extends Record<string, unknown>>(
  table: string,
  event: ChangeEvent,
  callback: (payload: RealtimePostgresChangesPayload<T>) => void,
  filter?: string,
) {
  useEffect(() => {
    const channel = supabase
      .channel(`${table}-${event}-${filter || 'all'}`)
      .on(
        'postgres_changes',
        { event, schema: 'public', table, filter },
        callback
      )
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [table, event, filter, callback]);
}
