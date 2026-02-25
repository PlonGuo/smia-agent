import {
  Button,
} from '@chakra-ui/react';
import { toaster } from '../../lib/toaster';
import { Download } from 'lucide-react';

interface DigestItem {
  title: string;
  url: string;
  source: string;
  category: string;
  importance: number;
  why_it_matters: string;
}

interface Props {
  digest: {
    digest_date: string;
    executive_summary?: string;
    items?: DigestItem[];
    top_highlights?: string[];
    trending_keywords?: string[];
  };
}

function digestToMarkdown(digest: Props['digest']): string {
  const lines: string[] = [];

  lines.push(`# AI Daily Digest - ${digest.digest_date}`);
  lines.push('');

  if (digest.executive_summary) {
    lines.push('## Executive Summary');
    lines.push(digest.executive_summary);
    lines.push('');
  }

  if (digest.top_highlights && digest.top_highlights.length > 0) {
    lines.push('## Top Highlights');
    digest.top_highlights.forEach((h, i) => {
      lines.push(`${i + 1}. ${h}`);
    });
    lines.push('');
  }

  if (digest.trending_keywords && digest.trending_keywords.length > 0) {
    lines.push(`**Trending:** ${digest.trending_keywords.join(', ')}`);
    lines.push('');
  }

  if (digest.items && digest.items.length > 0) {
    // Group by category
    const grouped: Record<string, DigestItem[]> = {};
    for (const item of digest.items) {
      const cat = item.category || 'Other';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(item);
    }

    for (const [category, items] of Object.entries(grouped)) {
      lines.push(`## ${category}`);
      lines.push('');
      for (const item of items) {
        const stars = '★'.repeat(item.importance);
        lines.push(`### [${item.title}](${item.url}) ${stars}`);
        lines.push(`> ${item.why_it_matters}`);
        lines.push(`- Source: ${item.source}`);
        lines.push('');
      }
    }
  }

  return lines.join('\n');
}

export default function ExportButton({ digest }: Props) {
  const handleExport = () => {
    try {
      const markdown = digestToMarkdown(digest);
      const blob = new Blob([markdown], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ai-digest-${digest.digest_date}.md`;
      a.click();
      URL.revokeObjectURL(url);
      toaster.success({ title: 'Digest exported as Markdown' });
    } catch {
      toaster.error({ title: 'Export failed' });
    }
  };

  return (
    <Button
      className="btn-silicone"
      variant="outline"
      size="sm"
      onClick={handleExport}
    >
      <Download size={14} />
      Export
    </Button>
  );
}
