import re
from typing import Dict, List, Optional, Tuple


class ArticleClassifier:
    """
    Deterministic rule-based category classifier for news articles.
    
    Category definitions:
    - Automotive: Electric vehicles, automotive manufacturing, vehicle transport.
    - Technology: AI, cloud, software, chips, digital platforms.
    - Healthcare: Pharmaceuticals, biotech, clinical, medical devices.
    - Finance: Capital markets, banking, fintech, investment, revenue.
    - Energy: Renewables, oil, gas, power grid, utilities.
    - Business: Default category for corporate investments, mergers, and commerce.
    """

    CATEGORIES_TAXONOMY: Dict[str, Dict[str, int]] = {
        "Automotive": {
            "electric vehicle": 5,
            "electric vehicles": 5,
            "ev": 4,
            "vehicle": 3,
            "vehicles": 3,
            "automotive": 4,
            "automobile": 4,
            "car": 3,
            "cars": 3,
            "truck": 3,
            "trucks": 3,
            "battery plant": 4,
            "vehicle plant": 5,
            "vehicle production": 4,
            "assembly plant": 4,
        },
        "Technology": {
            "artificial intelligence": 5,
            "ai": 3,
            "machine learning": 4,
            "software": 3,
            "cloud": 3,
            "semiconductor": 4,
            "chips": 3,
            "cybersecurity": 4,
            "saas": 4,
            "algorithm": 3,
            "hardware": 3,
        },
        "Healthcare": {
            "healthcare": 4,
            "pharmaceutical": 4,
            "biotech": 4,
            "clinical trial": 5,
            "vaccine": 4,
            "hospital": 3,
            "medicine": 3,
            "medical": 3,
            "patient": 3,
            "drug": 3,
        },
        "Finance": {
            "banking": 3,
            "fintech": 4,
            "stock": 3,
            "shares": 3,
            "dividend": 3,
            "cryptocurrency": 4,
            "crypto": 3,
            "credit": 2,
            "ipo": 4,
            "lending": 3,
        },
        "Energy": {
            "renewable energy": 5,
            "solar": 4,
            "wind power": 4,
            "oil": 3,
            "gas": 3,
            "nuclear": 4,
            "pipeline": 3,
            "clean energy": 4,
            "grid": 3,
        },
        "Business": {
            "investment": 3,
            "invest": 2,
            "acquisition": 4,
            "merger": 4,
            "revenue": 3,
            "earnings": 3,
            "profit": 3,
            "expansion": 2,
            "corporate": 2,
            "jobs": 2,
        },
    }

    @classmethod
    def classify(cls, title: str, content: Optional[str] = None) -> str:
        """
        Classify an article into a deterministic category based on title and content keywords.
        Title matches are weighted 2.5x higher than content matches.
        """
        category, _ = cls.classify_with_scores(title=title, content=content)
        return category

    @classmethod
    def classify_with_scores(
        cls, title: str, content: Optional[str] = None
    ) -> Tuple[str, Dict[str, float]]:
        scores: Dict[str, float] = {cat: 0.0 for cat in cls.CATEGORIES_TAXONOMY}
        normalized_title = (title or "").lower()
        normalized_content = (content or "").lower()

        for category, keyword_weights in cls.CATEGORIES_TAXONOMY.items():
            for keyword, weight in keyword_weights.items():
                pattern = r"\b" + re.escape(keyword) + r"\b"
                
                # Title matches with 2.5x multiplier
                title_matches = len(re.findall(pattern, normalized_title))
                scores[category] += title_matches * (weight * 2.5)

                # Content matches with 1.0x multiplier
                if normalized_content:
                    content_matches = len(re.findall(pattern, normalized_content))
                    scores[category] += content_matches * (weight * 1.0)

        # Find the category with maximum score
        best_category = max(scores, key=lambda c: scores[c])

        # If highest score is 0 or very low, fallback to Business if corporate indicators present, else General
        if scores[best_category] <= 0:
            return "Business", scores

        return best_category, scores

