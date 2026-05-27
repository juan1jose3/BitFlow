/**
 * Recommendation Engine Component
 *
 * Fetches personalized video recommendations from the Django REST API.
 * Uses collaborative filtering scores stored in the recommendations table.
 * Results are cached in React Query for 5 minutes to avoid redundant requests.
 */
import { useQuery } from 'react-query';
import { motion } from 'framer-motion';
import { fetchRecommendations } from '../services/recommendationService';
import VideoCard from './VideoCard';
import SkeletonCard from './SkeletonCard';

const STALE_TIME = 5 * 60 * 1000; // 5 minutes

export default function RecommendationEngine({ userId, currentVideoId, limit = 8 }) {
  const { data, isLoading, isError } = useQuery(
    ['recommendations', userId, currentVideoId],
    () => fetchRecommendations({ userId, exclude: currentVideoId, limit }),
    {
      staleTime: STALE_TIME,
      enabled: !!userId,
      retry: 2,
    }
  );

  if (isLoading) {
    return (
      <div className="recommendations-grid">
        {Array.from({ length: limit }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (isError || !data?.results?.length) {
    return null;
  }

  return (
    <section className="recommendations">
      <h2 className="recommendations__title">Recommended for you</h2>
      <div className="recommendations-grid">
        {data.results.map((video, i) => (
          <motion.div
            key={video.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <VideoCard video={video} score={video.score} />
          </motion.div>
        ))}
      </div>
    </section>
  );
}
