# ML learning path

| Step | Purpose | Expected input | Expected output | Dependencies | File |
| --- | --- | --- | --- | --- | --- |
| 1. Preprocessing | Produce prepared text | Raw ticket text | Prepared text | None | `ml/src/preprocessing/text.py` |
| 2. Tokenization | Expose text units | Prepared text | Token list | Preprocessing | `ml/src/preprocessing/tokenization.py` |
| 3. Vocabulary | Define the representation's terms | Tokenized documents | Term-to-index mapping | Tokenization | `ml/src/representations/vocabulary.py` |
| 4. Bag of Words | Represent documents numerically | Tokenized documents and vocabulary | Document feature matrix | Vocabulary | `ml/src/representations/bow.py` |
| 5. Class priors | Represent category prevalence | Training labels | Category probability mapping | Labeled dataset | `ml/src/training/priors.py` |
| 6. Conditional probabilities | Represent category-dependent feature statistics | Features and labels | Conditional probability parameters | Bag of Words, labels | `ml/src/training/probabilities.py` |
| 7. Laplace smoothing | Support estimation for sparse observations | Counts and configuration | Adjusted estimates | Count data | `ml/src/training/smoothing.py` |
| 8. Naive Bayes fit | Prepare classifier state | Training texts and labels | Fitted classifier state | Steps 1–7 | `ml/src/models/naive_bayes.py` |
| 9. Naive Bayes prediction | Assign categories and confidence | New texts and fitted state | Categories and probability mappings | Naive Bayes fit | `ml/src/models/naive_bayes.py` |
| 10. Evaluation | Measure classifier behavior | Actual and predicted labels | Accuracy, precision, recall, F1 | Predictions and actual labels | `ml/src/evaluation/metrics.py` |
| 11. TF-IDF | Explore another document representation | Tokenized documents and vocabulary | Document feature matrix | Preprocessing, tokenization, vocabulary | `ml/src/representations/tfidf.py` |
| 12. Embeddings | Explore word or document vectors | Tokenized documents | Vector representations | Preprocessing, tokenization | `ml/src/representations/embeddings.py` |
| 13. Neural network | Provide a neural classifier | Training texts and labels; new texts | Fitted state, categories, probabilities | Embeddings, evaluation | `ml/src/models/neural_network.py` |
| 14. RNN | Explore sequential classification | Training texts and labels; new texts | Fitted state, categories, probabilities | Sequential representation, evaluation | `ml/src/models/rnn.py` |
| 15. Attention | Extend sequential classification | Sequence representations, context, labels | Contextual representations and classifier outputs | RNN | `ml/src/models/attention_components.py`; `ml/src/models/attention.py` |
| 16. Transformer | Explore Transformer classification | Training texts and labels; new texts | Fitted state, categories, probabilities | Attention, self-attention, evaluation | `ml/src/models/transformer.py`; `ml/src/models/self_attention.py` |

| Component | Purpose | Expected input | Expected output | Dependencies | File |
| --- | --- | --- | --- | --- | --- |
| Cosine similarity (Experiment 02 companion) | Compare vector representations | Two vectors | Scalar similarity | Vector representations | `ml/src/representations/similarity.py` |
| Sequential representation (Experiment 04) | Represent ordered text | Tokens and vocabulary | Sequential features | Vocabulary | `ml/src/representations/sequences.py` |
| Shared classifier contract | Connect student models to the application | Texts, labels, artifact paths | State, predictions, probabilities, artifacts | Model implementation | `ml/src/models/base.py` |
