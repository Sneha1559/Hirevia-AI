
import re
from collections import defaultdict

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from utils.llm_client import ask_groq


class HybridRetriever:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.documents = []
        self.embeddings = None
        self.bm25 = None

    @staticmethod
    def tokenize(text):
        return re.findall(r"\b[a-zA-Z0-9+#.]+\b", text.lower())

    def fit(self, documents):
        """Build dense semantic and BM25 sparse indexes."""
        self.documents = [
            doc.strip()
            for doc in documents
            if isinstance(doc, str) and doc.strip()
        ]

        if not self.documents:
            raise ValueError("Provide at least one non-empty document.")

        self.embeddings = self.model.encode(
            self.documents,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        tokenized_docs = [self.tokenize(doc) for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_docs)

    def generate_queries(self, query, num_queries=3):
        """Generate alternative queries using Groq."""
        prompt = f"""
Generate {num_queries} alternative search queries for this requirement.
Use relevant synonyms and technical terms without changing the meaning.
Return only the alternative queries, one per line, without numbering.

Requirement: {query}
"""
        try:
            response = ask_groq(prompt)
            alternatives = []

            for line in response.splitlines():
                line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line)
                line = line.strip()

                if line and line.lower() != query.lower():
                    if line.lower() not in [q.lower() for q in alternatives]:
                        alternatives.append(line)

            return [query] + alternatives[:num_queries]

        except Exception:
            return [query]

    def retrieve(self, query, top_k=5, use_multi_query=True):
        """Retrieve evidence using dense, BM25, and RRF rankings."""
        if self.bm25 is None or self.embeddings is None:
            raise ValueError("Call fit(documents) before retrieve().")

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        queries = (
            self.generate_queries(query)
            if use_multi_query
            else [query]
        )

        rrf_scores = defaultdict(float)
        dense_scores_by_doc = defaultdict(float)
        bm25_scores_by_doc = defaultdict(float)
        dense_best_rank = {}
        bm25_best_rank = {}

        rank_constant = 60

        for current_query in queries:
            query_embedding = self.model.encode(
                [current_query],
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            # Dense semantic similarity.
            dense_scores = (
                query_embedding @ self.embeddings.T
            )[0]

            dense_ranking = np.argsort(-dense_scores)

            # Sparse keyword relevance.
            sparse_scores = self.bm25.get_scores(
                self.tokenize(current_query)
            )
            sparse_ranking = np.argsort(-sparse_scores)

            for index, score in enumerate(dense_scores):
                index = int(index)
                dense_scores_by_doc[index] = max(
                    dense_scores_by_doc[index], float(score)
                )

            for index, score in enumerate(sparse_scores):
                index = int(index)
                bm25_scores_by_doc[index] = max(
                    bm25_scores_by_doc[index], float(score)
                )

            for ranking_name, ranking in (
                ("dense", dense_ranking),
                ("bm25", sparse_ranking),
            ):
                best_ranks = (
                    dense_best_rank
                    if ranking_name == "dense"
                    else bm25_best_rank
                )

                for rank, index in enumerate(ranking, start=1):
                    index = int(index)
                    rrf_scores[index] += 1.0 / (
                        rank_constant + rank
                    )

                    if (
                        index not in best_ranks
                        or rank < best_ranks[index]
                    ):
                        best_ranks[index] = rank

        ranked_indices = sorted(
            rrf_scores,
            key=rrf_scores.get,
            reverse=True,
        )[:top_k]

        return [
            {
                "text": self.documents[index],
                # Backwards-compatible score field: this is RRF, not cosine.
                "score": round(rrf_scores[index], 6),
                "rrf_score": round(rrf_scores[index], 6),
                "dense_score": round(
                    dense_scores_by_doc[index], 6
                ),
                "bm25_score": round(
                    bm25_scores_by_doc[index], 6
                ),
                "dense_rank": dense_best_rank.get(index),
                "bm25_rank": bm25_best_rank.get(index),
                "queries_used": len(queries),
            }
            for index in ranked_indices
        ]
