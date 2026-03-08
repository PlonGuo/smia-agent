import { Helmet } from 'react-helmet-async';

interface SEOProps {
  title?: string;
  description?: string;
}

const defaults = {
  title: 'SmIA – Social Media Intelligence Agent',
  description:
    'AI-powered social media intelligence. Analyze trends across Reddit, YouTube, and Amazon with sentiment analysis, structured reports, and daily AI digests.',
};

export default function SEO({ title, description }: SEOProps) {
  const pageTitle = title ? `${title} | SmIA` : defaults.title;
  const pageDesc = description || defaults.description;

  return (
    <Helmet>
      <title>{pageTitle}</title>
      <meta name="description" content={pageDesc} />
      <meta property="og:title" content={pageTitle} />
      <meta property="og:description" content={pageDesc} />
    </Helmet>
  );
}
