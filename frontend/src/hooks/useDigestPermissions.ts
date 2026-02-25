import { useEffect, useState } from 'react';
import { useAuth } from './useAuth';
import { getDigestAccessStatus } from '../lib/api';

type AccessStatus = 'loading' | 'admin' | 'approved' | 'pending' | 'rejected' | 'none';

export function useDigestPermissions() {
  const { user } = useAuth();
  const [accessStatus, setAccessStatus] = useState<AccessStatus>('loading');

  useEffect(() => {
    if (!user) {
      setAccessStatus('none');
      return;
    }
    getDigestAccessStatus()
      .then((status) => setAccessStatus(status as AccessStatus))
      .catch(() => setAccessStatus('none'));
  }, [user]);

  return {
    accessStatus,
    isAdmin: accessStatus === 'admin',
    hasAccess: accessStatus === 'admin' || accessStatus === 'approved',
  };
}
