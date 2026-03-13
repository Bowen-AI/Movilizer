"""
Analytics processor for the Movilizer system.
Collects, processes, and analyzes viewing patterns to improve content generation.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class AnalyticsProcessor:
    """Processes analytics events and generates insights."""

    def __init__(self, data_dir: Path = None):
        """Initialize analytics processor.

        Args:
            data_dir: Directory to store analytics data
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent.parent / 'website' / 'public' / 'data'

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.events_file = self.data_dir / 'analytics_events.jsonl'
        self.insights_file = self.data_dir / 'analytics_insights.json'
        self.aggregates_file = self.data_dir / 'analytics_aggregates.json'

        # Initialize files if needed
        if not self.events_file.exists():
            self.events_file.touch()

        if not self.insights_file.exists():
            self._save_insights({})

        if not self.aggregates_file.exists():
            self._save_aggregates({})

    def record_event(
        self,
        event_type: str,
        movie_id: str,
        user_id: str = "anonymous",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an analytics event.

        Args:
            event_type: Type of event (view, click, complete, share, etc.)
            movie_id: ID of the movie
            user_id: ID of the user (anonymous if not provided)
            metadata: Additional event metadata
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'movie_id': movie_id,
            'user_id': user_id,
            'metadata': metadata or {},
        }

        # Append to events log (JSONL format)
        with open(self.events_file, 'a') as f:
            f.write(json.dumps(event) + '\n')

    def process_events(self) -> Dict[str, Any]:
        """Process analytics events and update aggregates.

        Returns:
            Dictionary with processing results
        """
        if not self.events_file.exists() or self.events_file.stat().st_size == 0:
            return {'events_processed': 0, 'new_aggregates': {}}

        # Read all events
        events = []
        try:
            with open(self.events_file, 'r') as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as e:
            print(f"Error reading events: {e}")
            return {'events_processed': 0, 'error': str(e)}

        # Process events
        aggregates = self._aggregate_events(events)

        # Save aggregates
        self._save_aggregates(aggregates)

        return {
            'events_processed': len(events),
            'new_aggregates': aggregates,
        }

    def _aggregate_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate events by movie and type.

        Args:
            events: List of event records

        Returns:
            Aggregated data
        """
        aggregates = {
            'by_movie': {},
            'by_event_type': {},
            'by_genre': {},
            'top_movies': [],
            'engagement_rate': 0.0,
        }

        views_count = 0
        completes_count = 0

        for event in events:
            movie_id = event.get('movie_id')
            event_type = event.get('event_type')

            # By movie
            if movie_id not in aggregates['by_movie']:
                aggregates['by_movie'][movie_id] = {
                    'total_views': 0,
                    'completions': 0,
                    'clicks': 0,
                    'shares': 0,
                }

            if event_type == 'view':
                aggregates['by_movie'][movie_id]['total_views'] += 1
                views_count += 1
            elif event_type == 'complete':
                aggregates['by_movie'][movie_id]['completions'] += 1
                completes_count += 1
            elif event_type == 'click':
                aggregates['by_movie'][movie_id]['clicks'] += 1
            elif event_type == 'share':
                aggregates['by_movie'][movie_id]['shares'] += 1

            # By event type
            if event_type not in aggregates['by_event_type']:
                aggregates['by_event_type'][event_type] = 0
            aggregates['by_event_type'][event_type] += 1

        # Calculate top movies
        if aggregates['by_movie']:
            top = sorted(
                aggregates['by_movie'].items(),
                key=lambda x: x[1]['total_views'],
                reverse=True,
            )[:10]
            aggregates['top_movies'] = [
                {'movie_id': m[0], 'stats': m[1]} for m in top
            ]

        # Calculate engagement rate
        if views_count > 0:
            aggregates['engagement_rate'] = completes_count / views_count

        aggregates['last_updated'] = datetime.utcnow().isoformat()
        return aggregates

    def generate_insights(self) -> Dict[str, Any]:
        """Generate insights from aggregated data.

        Returns:
            Dictionary with insights and recommendations
        """
        try:
            with open(self.aggregates_file, 'r') as f:
                aggregates = json.load(f)
        except Exception:
            return {}

        insights = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_views': sum(
                m['total_views']
                for m in aggregates.get('by_movie', {}).values()
            ),
            'total_completions': sum(
                m['completions']
                for m in aggregates.get('by_movie', {}).values()
            ),
            'average_completion_rate': aggregates.get('engagement_rate', 0),
            'top_performing_movies': aggregates.get('top_movies', [])[:5],
            'trending_patterns': self._identify_trends(aggregates),
            'improvement_suggestions': self._generate_suggestions(aggregates),
        }

        # Save insights
        self._save_insights(insights)

        return insights

    def _identify_trends(self, aggregates: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify trending patterns in viewing behavior.

        Args:
            aggregates: Aggregated event data

        Returns:
            List of trend insights
        """
        trends = []

        # High completion rate movies
        by_movie = aggregates.get('by_movie', {})
        high_completion = [
            {'movie_id': m_id, 'completion_rate': m['completions'] / max(m['total_views'], 1)}
            for m_id, m in by_movie.items()
            if m['total_views'] > 0
        ]

        if high_completion:
            high_completion.sort(key=lambda x: x['completion_rate'], reverse=True)
            trends.append({
                'pattern': 'high_completion_rate',
                'movies': high_completion[:3],
                'insight': 'These movies have high viewer retention',
            })

        # Shareable content
        most_shared = sorted(
            [(m_id, m['shares']) for m_id, m in by_movie.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        if most_shared and most_shared[0][1] > 0:
            trends.append({
                'pattern': 'highly_shareable',
                'top_movie': most_shared[0][0],
                'share_count': most_shared[0][1],
                'insight': 'This movie has high social sharing potential',
            })

        return trends

    def _generate_suggestions(self, aggregates: Dict[str, Any]) -> List[str]:
        """Generate suggestions for improving content generation.

        Args:
            aggregates: Aggregated event data

        Returns:
            List of suggestion strings
        """
        suggestions = []

        engagement = aggregates.get('engagement_rate', 0)
        if engagement < 0.5:
            suggestions.append("Completion rate is low. Consider shorter movies or more engaging narratives.")

        by_movie = aggregates.get('by_movie', {})
        if by_movie:
            avg_views = sum(m['total_views'] for m in by_movie.values()) / len(by_movie)
            low_performers = [
                m_id for m_id, m in by_movie.items()
                if m['total_views'] < avg_views * 0.5 and m['total_views'] > 0
            ]

            if low_performers:
                suggestions.append(
                    f"Consider revisiting narratives for underperforming movies: {len(low_performers)} movies have below-average views."
                )

        return suggestions

    def feed_back_to_story(self) -> Dict[str, Any]:
        """Generate feedback to improve future story generation.

        Returns:
            Dictionary with feedback and metrics
        """
        try:
            with open(self.insights_file, 'r') as f:
                insights = json.load(f)
        except Exception:
            return {}

        feedback = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_engagement': insights.get('average_completion_rate', 0),
            'high_performers': [
                m['movie_id']
                for m in insights.get('top_performing_movies', [])[:3]
            ],
            'recommendations': insights.get('improvement_suggestions', []),
            'trends': insights.get('trending_patterns', []),
            'action_items': self._prioritize_action_items(insights),
        }

        return feedback

    def _prioritize_action_items(self, insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritize action items based on insights.

        Args:
            insights: Generated insights

        Returns:
            Prioritized list of action items
        """
        items = []

        engagement = insights.get('average_completion_rate', 0)
        if engagement < 0.4:
            items.append({
                'priority': 'high',
                'action': 'Improve narrative pacing',
                'reason': 'Low completion rate indicates viewers are dropping off early',
            })

        if not insights.get('high_performers'):
            items.append({
                'priority': 'high',
                'action': 'Analyze successful movie patterns',
                'reason': 'Need to identify what makes top movies successful',
            })

        if insights.get('trending_patterns'):
            items.append({
                'priority': 'medium',
                'action': 'Capitalize on trending patterns',
                'reason': f"{len(insights['trending_patterns'])} relevant trends identified",
            })

        return items

    def _save_insights(self, insights: Dict[str, Any]) -> None:
        """Save insights to file."""
        with open(self.insights_file, 'w') as f:
            json.dump(insights, f, indent=2)

    def _save_aggregates(self, aggregates: Dict[str, Any]) -> None:
        """Save aggregates to file."""
        with open(self.aggregates_file, 'w') as f:
            json.dump(aggregates, f, indent=2)

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get a summary of current analytics.

        Returns:
            Analytics summary
        """
        try:
            with open(self.aggregates_file, 'r') as f:
                aggregates = json.load(f)
        except Exception:
            aggregates = {}

        try:
            with open(self.insights_file, 'r') as f:
                insights = json.load(f)
        except Exception:
            insights = {}

        return {
            'aggregates': aggregates,
            'insights': insights,
        }
