import { useState } from 'react';
import {
  Button,
} from '@chakra-ui/react';
import { createShareToken } from '../../lib/api';
import { toaster } from '../../lib/toaster';
import { Share2 } from 'lucide-react';

interface Props {
  digestId: string;
}

export default function ShareButton({ digestId }: Props) {
  const [loading, setLoading] = useState(false);

  const handleShare = async () => {
    setLoading(true);
    try {
      const data = await createShareToken(digestId);
      await navigator.clipboard.writeText(data.url);
      toaster.success({
        title: 'Share link copied!',
        description: 'Link expires in 7 days.',
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create share link';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      className="btn-silicone"
      variant="outline"
      size="sm"
      onClick={handleShare}
      loading={loading}
    >
      <Share2 size={14} />
      Share
    </Button>
  );
}
