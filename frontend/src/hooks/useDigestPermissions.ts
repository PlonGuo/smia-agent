import { useEffect, useMemo, useState } from 'react';
import { useAuth } from './useAuth';
import { getDigestAccessStatus } from '../lib/api';

type AccessStatus = 'loading' | 'admin' | 'approved' | 'pending' | 'rejected' | 'none';

export function useDigestPermissions() {
  const { user } = useAuth();
  const [fetchedStatus, setFetchedStatus] = useState<AccessStatus | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    getDigestAccessStatus()
      .then((status) => { if (!cancelled) setFetchedStatus(status as AccessStatus); })
      .catch(() => { if (!cancelled) setFetchedStatus('none'); });
    return () => { cancelled = true; };
  }, [user]);

  const accessStatus: AccessStatus = useMemo(() => {
    if (!user) return 'none';
    if (fetchedStatus === null) return 'loading';
    return fetchedStatus;
  }, [user, fetchedStatus]);

  return {
    accessStatus,
    isAdmin: accessStatus === 'admin',
    hasAccess: accessStatus === 'admin' || accessStatus === 'approved',
  };
}
