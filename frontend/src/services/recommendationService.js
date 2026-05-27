/**
 * Recommendation Service
 *
 * Calls the Django REST API recommendation endpoints.
 * The backend uses a collaborative filtering model trained on
 * view history, likes, and watch-time data stored in the recommendations table.
 */
import axios from './axiosClient';

/**
 * Fetch personalized recommendations for a user.
 * @param {object} params
 * @param {string} params.userId
 * @param {string} [params.exclude]   - video ID to exclude (current video)
 * @param {number} [params.limit=8]
 */
export async function fetchRecommendations({ userId, exclude, limit = 8 }) {
  const { data } = await axios.get('/api/recommendations/', {
    params: { user: userId, exclude, limit },
  });
  return data;
}

/**
 * Record a recommendation impression (user saw the card).
 * Used to train the ranking model.
 */
export async function recordImpression(videoId, position) {
  return axios.post('/api/recommendations/impression/', { video_id: videoId, position });
}

/**
 * Record a recommendation click-through.
 */
export async function recordClickThrough(videoId, fromVideoId) {
  return axios.post('/api/recommendations/click/', {
    video_id: videoId,
    from_video_id: fromVideoId,
  });
}
