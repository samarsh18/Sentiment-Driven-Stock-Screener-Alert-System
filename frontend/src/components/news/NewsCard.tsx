import React from 'react';
import { NewsRecordResponse } from '../../api/types';
import { formatDate } from '../../lib/utils';
import { ExternalLink, Newspaper } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  news: NewsRecordResponse;
}

export const NewsCard: React.FC<Props> = ({ news }) => {
  return (
    <div className="bg-surface border border-surface-border p-4 rounded-xl space-y-2 hover:border-gray-700 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Link
            to={`/stocks/${news.symbol}`}
            className="font-mono text-xs font-bold text-accent-blue bg-accent-blue/10 px-2 py-0.5 rounded border border-accent-blue/20 hover:bg-accent-blue/20 transition-colors"
          >
            {news.symbol}
          </Link>
          <span className="text-[11px] text-gray-400 flex items-center">
            <Newspaper className="w-3 h-3 mr-1" />
            {news.source}
          </span>
        </div>
        <span className="text-[11px] text-gray-500 font-mono">{formatDate(news.published_at)}</span>
      </div>

      <h4 className="text-sm font-semibold text-white leading-snug line-clamp-2">{news.title}</h4>
      <p className="text-xs text-gray-400 line-clamp-3 leading-relaxed">{news.content}</p>

      {news.url && (
        <div className="pt-1 flex items-center justify-end">
          <a
            href={news.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center text-[11px] font-semibold text-accent-blue hover:underline"
          >
            Read Article
            <ExternalLink className="w-3 h-3 ml-1" />
          </a>
        </div>
      )}
    </div>
  );
};
