import re
from typing import List, Optional


class ArticleSummarizer:
    """
    Deterministic extractive summarizer for news articles.
    
    Extracts the key leading informative sentences (focusing on the lead statement,
    numerical data, key investments, or primary thesis) without requiring an LLM.
    """

    @classmethod
    def summarize(
        cls,
        title: str,
        content: Optional[str] = None,
        max_sentences: int = 2,
        max_length: int = 350,
    ) -> str:
        """
        Generate a concise, deterministic summary from article content or title.
        """
        if not content or not content.strip():
            # If no content is provided, return a cleaned title summary
            return title.strip()

        cleaned_content = re.sub(r"\s+", " ", content.strip())
        
        # Split into individual sentences
        raw_sentences = re.split(r"(?<=[.!?])\s+", cleaned_content)
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        if not sentences:
            return title.strip()

        # Score sentences based on journalistic importance:
        # 1. Lead sentence boost (journalistic inverted pyramid style)
        # 2. Presence of numbers/currencies/data (investments, metrics)
        # 3. Sentence length (avoid fragments or excessively long sentences)
        scored_sentences = []
        for idx, sentence in enumerate(sentences):
            score = 0.0
            
            # Position bias: first sentence is typically the news lead
            if idx == 0:
                score += 5.0
            elif idx == 1:
                score += 3.0
            else:
                score += 1.0

            # Data/financial indicators ($2 billion, 50%, etc.)
            if re.search(r"(\$|€|£|¥|\d+(?:\.\d+)?%|\b\d+\s*(?:billion|million|trillion|jobs|plants?)\b)", sentence, re.IGNORECASE):
                score += 3.0

            # Action/corporate keywords
            if re.search(r"\b(invest|invested|investment|announces?|expanded?|production|acquired|launched|opened)\b", sentence, re.IGNORECASE):
                score += 2.0

            scored_sentences.append((score, idx, sentence))

        # Select top sentences maintaining chronological order
        scored_sentences.sort(key=lambda x: (-x[0], x[1]))
        selected = scored_sentences[:max_sentences]
        # Sort back to chronological reading order
        selected.sort(key=lambda x: x[1])

        summary_text = " ".join(s[2] for s in selected)

        # Enforce maximum character length
        if len(summary_text) > max_length:
            summary_text = summary_text[:max_length].rsplit(" ", 1)[0] + "..."

        return summary_text

